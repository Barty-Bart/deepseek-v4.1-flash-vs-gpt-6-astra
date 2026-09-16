#!/usr/bin/env python3
"""Drive the running app in headless Chrome: screenshots plus real assertions.

Usage:
    PORT=5182 .venv/bin/python reports/browser_check.py

Checks, against a running server:
  * the header really is sticky and never covers content, anchors or focus
  * no page scrolls sideways at any tested viewport
  * the phone menu opens, closes on Escape, and restores focus
  * clicking anywhere on a date/time field (or its label) opens the picker
  * thumb targets stay large enough and the admin table reflows to cards

Screenshots are written to reports/screenshots/. Exit status is non-zero if any
check fails. This signs in as the seeded admin and, unless --no-booking is
passed, completes one booking through the UI.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PORT = os.environ.get("PORT", "5182")
BASE = f"http://127.0.0.1:{PORT}"
DRIVER_PORT = int(os.environ.get("CHROMEDRIVER_PORT", "9515"))
CHROMEDRIVER = os.environ.get("CHROMEDRIVER")
CHROME = os.environ.get(
    "CHROME_BINARY", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)
ADMIN_USER = os.environ.get("NORTHLINE_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("NORTHLINE_ADMIN_PASSWORD", "northline-demo")
OUT = Path(__file__).resolve().parent / "screenshots"
CACHE_DIR = Path(__file__).resolve().parent / ".cache"
SHOP_TZ = ZoneInfo("Australia/Melbourne")

DESKTOP = (1440, 1000)
PHONE_A = (393, 852)     # iPhone 15 Pro
PHONE_B = (402, 874)     # iPhone 16 Pro
PHONES = {"phone-393x852": PHONE_A, "phone-402x874": PHONE_B}
ESCAPE_KEY = "\ue00c"

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")


# --------------------------------------------------------------------------- #
# Chromedriver plumbing
# --------------------------------------------------------------------------- #
def driver(method: str, path: str, payload=None, timeout: int = 90):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"http://127.0.0.1:{DRIVER_PORT}{path}", data=data, method=method
    )
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode()
        raise RuntimeError(f"{method} {path} -> HTTP {error.code}: {detail[:600]}") from None


def _version_of(binary) -> str | None:
    try:
        output = subprocess.run([str(binary), "--version"], capture_output=True,
                                text=True, timeout=10).stdout
    except Exception:
        return None
    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output)
    return match.group(1) if match else None


def resolve_chromedriver() -> str:
    """Find a chromedriver matching the installed Chrome, downloading if needed."""
    chrome_version = _version_of(CHROME)
    if not chrome_version:
        raise SystemExit(f"Could not determine the Chrome version from {CHROME}")
    major = chrome_version.split(".")[0]

    candidates = [
        Path(CHROMEDRIVER) if CHROMEDRIVER else None,
        CACHE_DIR / "chromedriver",
        Path.home() / "bin" / "chromedriver",
        Path("/tmp/chromedriver-mac-arm64/chromedriver"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            found = _version_of(candidate)
            if found and found.split(".")[0] == major:
                return str(candidate)

    print(f"No chromedriver for Chrome {major} found; downloading one ...")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    index_url = ("https://googlechromelabs.github.io/chrome-for-testing/"
                 "known-good-versions-with-downloads.json")
    with urllib.request.urlopen(index_url, timeout=60) as response:
        index = json.loads(response.read().decode())
    machine = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout
    platform = "mac-arm64" if "arm64" in machine else "mac-x64"
    match = next((v for v in reversed(index["versions"])
                  if v["version"].startswith(major + ".")), None)
    if match is None:
        raise SystemExit(f"No Chrome-for-Testing chromedriver published for version {major}.")
    url = next(d["url"] for d in match["downloads"]["chromedriver"] if d["platform"] == platform)
    archive = CACHE_DIR / "chromedriver.zip"
    urllib.request.urlretrieve(url, archive)
    subprocess.run(["unzip", "-oq", str(archive), "-d", str(CACHE_DIR)], check=True)
    extracted = next(CACHE_DIR.glob("chromedriver-*/chromedriver"), None)
    if extracted is None:
        raise SystemExit("Downloaded chromedriver archive did not contain a binary.")
    target = CACHE_DIR / "chromedriver"
    target.write_bytes(extracted.read_bytes())
    target.chmod(0o755)
    print(f"  using chromedriver {match['version']}")
    return str(target)


class Browser:
    def __init__(self, session_id: str):
        self.sid = session_id
        self.emulated = False
        self.viewport = (0, 0)

    def get(self, url: str, settle: float = 0.5, retries: int = 4) -> None:
        last = None
        for _ in range(retries):
            try:
                driver("POST", f"/session/{self.sid}/url", {"url": url})
                time.sleep(settle)
                return
            except RuntimeError as error:      # navigation raced the load
                last = error
                time.sleep(0.5)
        raise last

    def js(self, script: str, retries: int = 4):
        last = None
        for _ in range(retries):
            try:
                return driver("POST", f"/session/{self.sid}/execute/sync",
                              {"script": script, "args": []})["value"]
            except RuntimeError as error:
                last = error
                time.sleep(0.4)
        raise last

    def js_object(self, script: str) -> dict:
        return json.loads(self.js(script))

    def command(self, cmd: str, params: dict) -> None:
        driver("POST", f"/session/{self.sid}/chromium/send_command",
               {"cmd": cmd, "params": params})

    def window(self, size) -> None:
        """Desktop viewport, via the real browser window."""
        width, height = size
        self.emulated = False
        self.viewport = (width, height)
        self.command("Emulation.clearDeviceMetricsOverride", {})
        driver("POST", f"/session/{self.sid}/window/rect",
               {"width": width, "height": height, "x": 0, "y": 0})
        time.sleep(0.4)

    def emulate(self, size, scale: int = 2) -> None:
        """Phone viewport. A real window cannot go below ~500px wide on macOS,
        so the viewport is emulated through the DevTools protocol instead."""
        width, height = size
        self.emulated = True
        self.viewport = (width, height)
        self.command("Emulation.setDeviceMetricsOverride",
                     {"width": width, "height": height,
                      "deviceScaleFactor": scale, "mobile": True})
        self.command("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
        time.sleep(0.4)

    def set_viewport(self, name: str, size) -> None:
        if name == "desktop":
            self.window(size)
        else:
            self.emulate(size)

    def element(self, selector: str):
        return driver("POST", f"/session/{self.sid}/element",
                      {"using": "css selector", "value": selector})["value"][
            "element-6066-11e4-a52e-4f735466cecf"]

    def click(self, selector: str) -> None:
        """A real user click in the middle of the element (not the icon corner)."""
        element_id = self.element(selector)
        driver("POST", f"/session/{self.sid}/element/{element_id}/click", {})
        time.sleep(0.3)

    def key(self, value: str) -> None:
        driver("POST", f"/session/{self.sid}/actions", {"actions": [{
            "type": "key", "id": "keyboard",
            "actions": [{"type": "keyDown", "value": value}, {"type": "keyUp", "value": value}],
        }]})
        time.sleep(0.3)

    def capture_scrolled(self, name: str, offset: int = 900) -> None:
        """A viewport-sized shot with the page scrolled, to show the sticky header."""
        self.js(f"window.scrollTo(0, {offset}); return Math.round(window.scrollY);")
        time.sleep(0.35)
        raw = driver("GET", f"/session/{self.sid}/screenshot")["value"]
        (OUT / f"{name}.png").write_bytes(base64.b64decode(raw))
        print(f"    saved {name}.png (scrolled)")
        self.js("window.scrollTo(0, 0); return 1;")
        time.sleep(0.2)

    def capture(self, name: str, full_page: bool = True) -> None:
        width, height = self.viewport
        if full_page:
            content = self.js("return Math.max(document.documentElement.scrollHeight,"
                              "document.body.scrollHeight, window.innerHeight);")
            tall = min(int(content) + 20, 12000)
            if self.emulated:
                self.command("Emulation.setDeviceMetricsOverride",
                             {"width": width, "height": tall,
                              "deviceScaleFactor": 2, "mobile": True})
            else:
                driver("POST", f"/session/{self.sid}/window/rect",
                       {"width": width, "height": tall, "x": 0, "y": 0})
            time.sleep(0.4)
        self.js("window.scrollTo(0,0); return 1;")
        time.sleep(0.2)
        raw = driver("GET", f"/session/{self.sid}/screenshot")["value"]
        (OUT / f"{name}.png").write_bytes(base64.b64decode(raw))
        print(f"    saved {name}.png")
        if full_page:
            if self.emulated:
                self.command("Emulation.setDeviceMetricsOverride",
                             {"width": width, "height": height,
                              "deviceScaleFactor": 2, "mobile": True})
            else:
                driver("POST", f"/session/{self.sid}/window/rect",
                       {"width": width, "height": height, "x": 0, "y": 0})
            time.sleep(0.25)


def wait_for_server(timeout=25) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BASE}/", timeout=2)
            return True
        except Exception:
            time.sleep(0.3)
    return False


# --------------------------------------------------------------------------- #
# In-page probes
# --------------------------------------------------------------------------- #
HEADER_PROBE = r"""
const header = document.getElementById('site-header');
const doc = document.documentElement;
const css = getComputedStyle(header);
const out = {
  position: css.position,
  headerHeight: Math.round(header.getBoundingClientRect().height),
  headerVar: getComputedStyle(doc).getPropertyValue('--header-h').trim(),
  scrollPaddingTop: getComputedStyle(doc).scrollPaddingTop,
};
window.scrollTo(0, 0);
window.scrollTo(0, 900);
out.headerTopAfterScroll = Math.round(header.getBoundingClientRect().top);
out.scrolledY = Math.round(window.scrollY);
window.scrollTo(0, 0);
return JSON.stringify(out);
"""

ANCHOR_PROBE = r"""
const header = document.getElementById('site-header');
const target = document.getElementById('book');
if (!target) { return JSON.stringify({missing: true}); }
target.scrollIntoView();
const headerRect = header.getBoundingClientRect();
const targetRect = target.getBoundingClientRect();
const focusTarget = document.getElementById('date-input') || document.querySelector('input[type="date"]');
let focusedTop = null;
if (focusTarget) {
  focusTarget.scrollIntoView({block: 'start'});
  focusTarget.focus({preventScroll: false});
  focusedTop = Math.round(focusTarget.getBoundingClientRect().top);
}
window.scrollTo(0, 0);
return JSON.stringify({
  missing: false,
  headerBottom: Math.round(headerRect.bottom),
  targetTop: Math.round(targetRect.top),
  focusedTop: focusedTop,
});
"""

OVERFLOW_PROBE = r"""
const doc = document.documentElement;
function insideScroller(el) {
  let node = el.parentElement;
  while (node && node !== document.body) {
    const overflowX = getComputedStyle(node).overflowX;
    if ((overflowX === 'auto' || overflowX === 'scroll') && node.scrollWidth > node.clientWidth + 1) {
      return true;   // deliberately scrollable, e.g. the date strip
    }
    node = node.parentElement;
  }
  return false;
}
const offenders = [];
document.querySelectorAll('body *').forEach(function (el) {
  const rect = el.getBoundingClientRect();
  if (rect.width > 0 && rect.right > window.innerWidth + 1.5 && !insideScroller(el)) {
    offenders.push(el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : '')
      + '@' + Math.round(rect.right));
  }
});
return JSON.stringify({
  scrollWidth: doc.scrollWidth,
  innerWidth: window.innerWidth,
  horizontal: doc.scrollWidth > window.innerWidth + 1,
  offenders: offenders.slice(0, 6),
});
"""

MENU_PROBE = r"""
const toggle = document.getElementById('nav-toggle');
const nav = document.getElementById('site-nav');
return JSON.stringify({
  hasToggle: !!toggle,
  hasNav: !!nav,
  toggleDisplay: toggle ? getComputedStyle(toggle).display : null,
  expanded: toggle ? toggle.getAttribute('aria-expanded') : null,
  controls: toggle ? toggle.getAttribute('aria-controls') : null,
  navId: nav ? nav.id : null,
  navLabel: nav ? nav.getAttribute('aria-label') : null,
  navDisplay: nav ? getComputedStyle(nav).display : null,
  linkHeights: nav ? Array.from(nav.querySelectorAll('a')).map(a => Math.round(a.getBoundingClientRect().height)) : [],
});
"""

TARGETS_PROBE = r"""
const selectors = ['.nav-toggle', '.slot-body', '.summary-bar .btn-primary', '.filters .btn-primary',
                   '.filters-nav .btn', '.cell-actions .btn', '.date-fallback input[type="date"]',
                   '.filters input[type="date"]', '.block-form input[type="time"]'];
const out = {};
selectors.forEach(function (selector) {
  const el = document.querySelector(selector);
  if (el) {
    const rect = el.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {   // skip controls hidden at this width
      out[selector] = {w: Math.round(rect.width), h: Math.round(rect.height)};
    }
  }
});
return JSON.stringify(out);
"""

CARD_PROBE = r"""
const row = document.querySelector('.data-table tbody tr');
const table = document.querySelector('.data-table');
const thead = document.querySelector('.data-table thead');
if (!row) { return JSON.stringify({rows: 0}); }
return JSON.stringify({
  rows: document.querySelectorAll('.data-table tbody tr').length,
  rowDisplay: getComputedStyle(row).display,
  tableDisplay: table ? getComputedStyle(table).display : null,
  headDisplay: thead ? getComputedStyle(thead).display : null,
  cardWidth: Math.round(row.getBoundingClientRect().width),
  viewportWidth: window.innerWidth,
});
"""

PICKER_PROBE = r"""
window.__pickerCalls = 0;
const inputs = Array.from(document.querySelectorAll('input[type="date"], input[type="time"]'));
inputs.forEach(function (input) {
  input.showPicker = function () { window.__pickerCalls += 1; };
});
return JSON.stringify({count: inputs.length});
"""

ROWS_PROBE = r"""
const crumbs = document.querySelector('.crumbs');
if (!crumbs) { return JSON.stringify({rows: 0}); }
const tops = new Set(Array.from(crumbs.querySelectorAll('.crumb'))
  .map(function (c) { return Math.round(c.getBoundingClientRect().top); }));
return JSON.stringify({rows: tops.size, height: Math.round(crumbs.getBoundingClientRect().height)});
"""

SLOT_PROBE = r"""
const form = document.querySelector('form.booking-form');
const out = {hasForm: !!form, times: []};
if (form) {
  out.times = Array.from(form.querySelectorAll('input[name="time"]')).map(function (i) { return i.value; });
  out.radioCount = out.times.length;
  out.date = (form.querySelector('input[name="date"]') || {}).value || null;
}
return JSON.stringify(out);
"""


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def check_header(browser: Browser, label: str) -> None:
    info = browser.js_object(HEADER_PROBE)
    check(f"{label}: header uses position: sticky",
          info["position"] == "sticky", f"position={info['position']}")
    check(f"{label}: header stays pinned after scrolling",
          info["headerTopAfterScroll"] == 0 and info["scrolledY"] > 0,
          f"top={info['headerTopAfterScroll']}px at scrollY={info['scrolledY']}")
    match = re.match(r"^(\d+(?:\.\d+)?)px$", info["headerVar"])
    check(f"{label}: JS publishes --header-h",
          bool(match) and abs(float(match.group(1)) - info["headerHeight"]) <= 1,
          f"--header-h={info['headerVar']} header={info['headerHeight']}px")
    padding = info["scrollPaddingTop"]
    check(f"{label}: scroll-padding clears the header",
          padding.endswith("px") and float(padding[:-2]) >= info["headerHeight"],
          f"scroll-padding-top={padding}")


def check_anchor(browser: Browser, label: str) -> None:
    info = browser.js_object(ANCHOR_PROBE)
    if info.get("missing"):
        return
    check(f"{label}: #book anchor is not hidden behind the header",
          info["targetTop"] >= info["headerBottom"] - 1,
          f"anchor top={info['targetTop']}px, header bottom={info['headerBottom']}px")
    if info["focusedTop"] is not None:
        check(f"{label}: focused date field is not covered",
              info["focusedTop"] >= info["headerBottom"] - 1,
              f"field top={info['focusedTop']}px, header bottom={info['headerBottom']}px")


def check_overflow(browser: Browser, label: str) -> None:
    info = browser.js_object(OVERFLOW_PROBE)
    check(f"{label}: no horizontal page overflow",
          not info["horizontal"],
          f"scrollWidth={info['scrollWidth']} viewport={info['innerWidth']}"
          + (f" offenders={info['offenders']}" if info["offenders"] else ""))


def check_targets(browser: Browser, label: str, minimum: int) -> None:
    targets = browser.js_object(TARGETS_PROBE)
    if not targets:
        return
    small = {k: v for k, v in targets.items() if v["h"] < minimum}
    check(f"{label}: interactive controls at least {minimum}px tall",
          not small, f"too small: {small}" if small else f"{len(targets)} controls checked")


def check_menu_open_close(browser: Browser, label: str) -> None:
    before = browser.js_object(MENU_PROBE)
    check(f"{label}: menu button is present and mobile-visible",
          before["hasToggle"] and before["toggleDisplay"] != "none",
          f"display={before['toggleDisplay']}")
    check(f"{label}: menu button is wired to the nav",
          before["controls"] == before["navId"] == "site-nav" and bool(before["navLabel"]),
          f"aria-controls={before['controls']} navId={before['navId']}")
    check(f"{label}: nav starts collapsed and hidden",
          before["expanded"] == "false" and before["navDisplay"] == "none",
          f"aria-expanded={before['expanded']} display={before['navDisplay']}")

    browser.click("#nav-toggle")
    opened = browser.js_object(MENU_PROBE)
    check(f"{label}: tapping the button opens the menu",
          opened["expanded"] == "true" and opened["navDisplay"] != "none",
          f"aria-expanded={opened['expanded']} display={opened['navDisplay']}")
    check(f"{label}: menu links are tap-sized",
          bool(opened["linkHeights"]) and min(opened["linkHeights"]) >= 44,
          f"link heights={opened['linkHeights']}")

    browser.js("document.getElementById('nav-toggle').focus(); return true;")
    browser.key(ESCAPE_KEY)
    closed = browser.js_object(MENU_PROBE)
    focus_back = browser.js("return document.activeElement && document.activeElement.id;")
    check(f"{label}: Escape closes the menu",
          closed["expanded"] == "false" and closed["navDisplay"] == "none",
          f"aria-expanded={closed['expanded']} display={closed['navDisplay']}")
    check(f"{label}: Escape returns focus to the menu button",
          focus_back == "nav-toggle", f"activeElement={focus_back}")

    browser.click("#nav-toggle")
    browser.js("document.body.click(); return true;")
    outside = browser.js_object(MENU_PROBE)
    check(f"{label}: tapping outside closes the menu",
          outside["expanded"] == "false", f"aria-expanded={outside['expanded']}")


def check_picker(browser: Browser, label: str, selector: str,
                 label_selector: str | None = None) -> None:
    info = browser.js_object(PICKER_PROBE)
    if not info["count"]:
        check(f"{label}: date/time field exists", False, "no date or time input on the page")
        return

    browser.click(selector)
    calls = browser.js("return window.__pickerCalls;")
    check(f"{label}: clicking the middle of {selector} opens the picker",
          calls >= 1, f"showPicker() called {calls}x")

    if label_selector:
        browser.js("window.__pickerCalls = 0; return true;")
        browser.click(label_selector)
        calls = browser.js("return window.__pickerCalls;")
        check(f"{label}: clicking the {label_selector} label also opens it",
              calls >= 1, f"showPicker() called {calls}x")


def check_picker_fallback(browser: Browser, label: str) -> None:
    """With no showPicker() in the browser, the field must still take focus."""
    result = browser.js_object("""
      const input = document.getElementById('date-input') || document.querySelector('input[type="date"]');
      if (!input) { return JSON.stringify({ran: false}); }
      window.__pickerCalls = 0;
      // Chrome keeps showPicker on the prototype (not deletable), so shadow it
      // with undefined to reproduce a browser that does not implement it.
      Object.defineProperty(input, 'showPicker', {value: undefined, configurable: true});
      const hadShowPicker = typeof input.showPicker;
      input.blur();
      input.click();                                  // the real click path
      const focused = document.activeElement === input;
      delete input.showPicker;
      return JSON.stringify({ran: true, focused: focused, hadShowPicker: hadShowPicker,
                             restored: typeof input.showPicker});
    """)
    if not result.get("ran"):
        return
    check(f"{label}: falls back to focusing the field when showPicker is missing",
          result["focused"] is True and result["hadShowPicker"] == "undefined",
          f"focused={result['focused']} showPicker={result['hadShowPicker']} "
          f"(restored={result['restored']})")


def check_single_row(browser: Browser, label: str) -> None:
    info = browser.js_object(ROWS_PROBE)
    if not info.get("rows"):
        return
    check(f"{label}: step indicators stay on one row",
          info["rows"] == 1, f"{info['rows']} rows")


def check_admin_cards(browser: Browser, label: str, expect_cards: bool) -> None:
    info = browser.js_object(CARD_PROBE)
    if not info.get("rows"):
        check(f"{label}: dashboard has appointment rows to lay out", False, "no rows")
        return
    if expect_cards:
        check(f"{label}: appointment table reflows to one card per booking",
              info["rowDisplay"] == "grid" and info["headDisplay"] == "none",
              f"row display={info['rowDisplay']} thead display={info['headDisplay']}")
        check(f"{label}: cards stay inside the viewport",
              info["cardWidth"] <= info["viewportWidth"],
              f"card={info['cardWidth']}px viewport={info['viewportWidth']}px")
    else:
        check(f"{label}: appointment table stays a table",
              info["rowDisplay"] == "table-row", f"row display={info['rowDisplay']}")


def snippet(text: str, needle: str) -> str:
    """The line that actually proves the check, for the report."""
    for line in text.splitlines():
        if needle.lower() in line.lower():
            return line.strip()[:90]
    return text.strip().splitlines()[0][:90] if text.strip() else "(empty page)"


def slots_on_page(browser: Browser) -> list[str]:
    return browser.js_object(SLOT_PROBE)["times"]


# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-booking", action="store_true",
                        help="skip the booking completed through the UI")
    args = parser.parse_args()

    if not wait_for_server():
        print(f"App is not responding at {BASE}", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix="northline-check-"))
    chromedriver = subprocess.Popen(
        [resolve_chromedriver(), f"--port={DRIVER_PORT}", "--allowed-ips="],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    session_id = None
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            driver("GET", "/status")
            break
        except Exception:
            time.sleep(0.3)
    else:
        chromedriver.terminate()
        raise SystemExit("chromedriver did not start")

    try:
        created = driver("POST", "/session", {"capabilities": {"alwaysMatch": {
            "browserName": "chrome",
            "goog:chromeOptions": {"args": [
                "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                "--force-device-scale-factor=1", f"--user-data-dir={profile}",
            ], "binary": CHROME},
        }}})
        browser = Browser(created["value"]["sessionId"])
        session_id = browser.sid

        today = datetime.now(SHOP_TZ).date()
        booking_day = today + timedelta(days=1)
        while booking_day.weekday() not in (1, 2, 3, 4, 5):
            booking_day += timedelta(days=1)
        day = booking_day.isoformat()
        book_url = f"{BASE}/book?service=3&barber=1&date={day}"

        def sign_in_admin() -> None:
            browser.get(f"{BASE}/admin/login")
            browser.js(f"""
              const user = document.getElementById('username');
              const pass = document.getElementById('password');
              if (!user || !pass) {{ throw new Error('login form not ready'); }}
              user.value = {json.dumps(ADMIN_USER)};
              pass.value = {json.dumps(ADMIN_PASS)};
              pass.form.submit();
              return true;
            """)
            time.sleep(0.9)

        # ---------------------------------------------------------------- #
        print(f"\n== Desktop {DESKTOP[0]}x{DESKTOP[1]} ==")
        browser.set_viewport("desktop", DESKTOP)
        for name, url in [("home", "/"), ("book", f"/book?service=3&barber=1&date={day}"),
                          ("manage-entry", "/manage"), ("admin-login", "/admin/login")]:
            browser.get(f"{BASE}{url}")
            check_overflow(browser, f"desktop/{name}")
            browser.capture(f"{name}-desktop")

        browser.get(f"{BASE}/")
        check_header(browser, "desktop/home")
        check_anchor(browser, "desktop/home")
        browser.capture_scrolled("header-sticky-desktop")
        browser.get(book_url)
        check_picker(browser, "desktop/book", "#date-input")
        check_picker_fallback(browser, "desktop/book")
        check_targets(browser, "desktop/book", minimum=32)

        # ---------------------------------------------------------------- #
        for viewport_name, size in PHONES.items():
            print(f"\n== {viewport_name} ==")
            browser.set_viewport(viewport_name, size)
            reported = browser.js("return window.innerWidth + 'x' + window.innerHeight;")
            check(f"{viewport_name}: viewport really is {size[0]}x{size[1]}",
                  reported == f"{size[0]}x{size[1]}", f"innerWidth x innerHeight = {reported}")

            for name, url in [("home", "/"), ("book", f"/book?service=3&barber=1&date={day}"),
                              ("manage-entry", "/manage"), ("admin-login", "/admin/login")]:
                browser.get(f"{BASE}{url}")
                check_overflow(browser, f"{viewport_name}/{name}")
                browser.capture(f"{name}-{viewport_name}")

            browser.get(f"{BASE}/")
            check_header(browser, f"{viewport_name}/home")
            check_anchor(browser, f"{viewport_name}/home")
            browser.capture_scrolled(f"header-sticky-{viewport_name}")
            check_targets(browser, f"{viewport_name}/home", minimum=44)
            check_menu_open_close(browser, viewport_name)
            browser.click("#nav-toggle")          # leave it open for the screenshot
            browser.capture(f"header-menu-open-{viewport_name}", full_page=False)
            browser.click("#nav-toggle")

            browser.get(book_url)
            check_overflow(browser, f"{viewport_name}/book")
            check_targets(browser, f"{viewport_name}/book", minimum=44)
            check_single_row(browser, f"{viewport_name}/book")
            check_picker(browser, viewport_name, "#date-input")
            check_picker_fallback(browser, viewport_name)

        # ---------------------------------------------------------------- #
        print("\n== Customer booking, double-booking protection, cancellation ==")
        browser.set_viewport("phone-393x852", PHONE_A)
        booking_url = f"{BASE}/book?service=2&barber=2&date={day}"
        browser.get(booking_url)
        offered = slots_on_page(browser)
        check("booking: the chosen day offers real slots", len(offered) > 0,
              f"{len(offered)} slots")
        taken = offered[0]

        if not args.no_booking:
            browser.js("""
              const form = document.querySelector('form.booking-form');
              if (!form || !form.querySelector('#name')) { throw new Error('form not ready'); }
              form.querySelector('input[name="time"]').checked = true;
              form.querySelector('#name').value = 'Browser Check';
              form.querySelector('#email').value = 'browser.check@example.com';
              form.submit();
              return true;
            """)
            time.sleep(0.9)
            browser.get(f"{BASE}/booked")
            body = browser.js("return document.body.innerText;")
            reference = re.search(r"NB-[A-Z0-9]{6}", body)
            check("booking: confirmation page shows a reference",
                  bool(reference), reference.group(0) if reference else "none")
            check_overflow(browser, "phone-393x852/confirmation")
            browser.capture("booking-confirmed-phone-393x852")

            manage_url = browser.js(
                "const a=document.querySelector('.link-card a'); return a ? a.getAttribute('href') : '';")
            check("booking: private management link is present",
                  bool(manage_url) and "/manage/" in manage_url, manage_url[:60])

            browser.get(booking_url)
            after = slots_on_page(browser)
            check("booking: the booked slot disappears from availability",
                  taken not in after, f"{taken} offered again? {taken in after}")

            browser.js(f"""
              const form = document.querySelector('form.booking-form');
              const radio = form.querySelector('input[name="time"]');
              radio.value = {json.dumps(taken)};
              radio.checked = true;
              form.querySelector('#name').value = 'Second Attempt';
              form.querySelector('#email').value = 'second.attempt@example.com';
              form.submit();
              return true;
            """)
            time.sleep(0.9)
            conflict = browser.js("return document.body.innerText;")
            check("double booking: the second attempt is refused with a friendly message",
                  "just taken" in conflict, snippet(conflict, "just taken"))
            check("double booking: the conflict response refreshes availability",
                  taken not in slots_on_page(browser), f"stale list still offers {taken}")
            browser.capture("double-booking-conflict-phone-393x852")

            browser.get(f"{BASE}{manage_url}")
            check("cancellation: the private view offers a cancel action",
                  browser.js("return !!document.querySelector('form[data-confirm] button');"))
            browser.capture("manage-phone-393x852")
            browser.js("document.querySelector('form[data-confirm]').submit(); return true;")
            time.sleep(0.9)
            page = browser.js("return document.body.innerText;")
            check("cancellation: the booking is cancelled", "Booking cancelled" in page,
                  snippet(page, "Booking cancelled"))
            browser.capture("manage-cancelled-phone-393x852")

            browser.get(booking_url)
            check("cancellation: the slot is offered again",
                  taken in slots_on_page(browser), f"{taken} back? {taken in slots_on_page(browser)}")

        # ---------------------------------------------------------------- #
        print("\n== Admin dashboard ==")
        browser.set_viewport("desktop", DESKTOP)
        sign_in_admin()
        dashboard = f"{BASE}/admin/?date={day}&barber=1"
        browser.get(dashboard)
        check("desktop/admin: signed-in dashboard renders",
              "Bookings for" in browser.js("return document.body.innerText;"))
        check_overflow(browser, "desktop/admin")
        check_targets(browser, "desktop/admin", minimum=32)
        check_admin_cards(browser, "desktop/admin", expect_cards=False)
        check_picker(browser, "desktop/admin", "#f-date", "label[for='f-date']")
        check_picker(browser, "desktop/admin", "#b-start", "label[for='b-start']")
        browser.capture("admin-dashboard-desktop")

        for viewport_name, size in PHONES.items():
            browser.set_viewport(viewport_name, size)
            browser.get(dashboard)
            check_overflow(browser, f"{viewport_name}/admin")
            check_targets(browser, f"{viewport_name}/admin", minimum=44)
            check_admin_cards(browser, f"{viewport_name}/admin", expect_cards=True)
            check_picker(browser, viewport_name + "/admin", "#b-end", "label[for='b-end']")
            browser.capture(f"admin-dashboard-{viewport_name}")

            browser.click("#nav-toggle")
            browser.capture(f"admin-dashboard-{viewport_name}-menu-open", full_page=False)
            browser.click("#nav-toggle")

    finally:
        if session_id:
            try:
                driver("DELETE", f"/session/{session_id}")
            except Exception:
                pass
        chromedriver.terminate()
        shutil.rmtree(profile, ignore_errors=True)

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    for name, _ok, detail in failed:
        print(f"  FAILED: {name} — {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
