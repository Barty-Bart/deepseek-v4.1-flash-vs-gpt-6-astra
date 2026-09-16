"""Structural guards for the sticky header, phone menu and picker hooks.

These assert the markup and CSS the layout work depends on, so the pieces the
browser check exercises cannot silently disappear.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import ADMIN_PASS, ADMIN_USER, csrf_from, login

CSS = (Path(__file__).resolve().parents[1] / "northline" / "static" / "css" / "app.css").read_text()
JS = (Path(__file__).resolve().parents[1] / "northline" / "static" / "js" / "app.js").read_text()

PAGES = ["/", "/book", "/manage", "/admin/login"]


def input_tag(body: str, control_id: str) -> str:
    """The whole <input ...> tag carrying this id (attribute order is not fixed)."""
    for tag in re.findall(r"<input[^>]*>", body):
        if f'id="{control_id}"' in tag:
            return tag
    raise AssertionError(f"no input with id={control_id}")


@pytest.mark.parametrize("url", PAGES)
def test_every_page_carries_the_menu_button_and_nav(client, url):
    body = client.get(url).get_data(as_text=True)
    assert 'id="site-header"' in body
    toggle = re.search(r'<button[^>]*id="nav-toggle"[^>]*>', body)
    assert toggle, f"no menu button on {url}"
    markup = toggle.group(0)
    assert 'aria-expanded="false"' in markup
    assert 'aria-controls="site-nav"' in markup
    assert 'type="button"' in markup
    assert 'id="site-nav"' in body


def test_nav_is_usable_without_javascript(client):
    body = client.get("/").get_data(as_text=True)
    # The collapsed state is applied by CSS only when JS marked the document.
    assert "classList.add('js')" in body
    assert "html:not(.js) .site-nav" in CSS
    assert "html:not(.js) .nav-toggle" in CSS


def test_stylesheet_makes_the_header_sticky_and_offsets_anchors():
    assert re.search(r"\.site-header\s*\{[^}]*position:\s*sticky", CSS)
    assert "top: 0" in CSS
    assert "scroll-padding-top: calc(var(--header-h" in CSS
    assert "scroll-margin-top: calc(var(--header-h" in CSS
    assert "z-index: 40" in CSS


def test_stylesheet_reflows_the_admin_table_into_cards_on_phones():
    assert "--header-h" in JS
    phone = CSS[CSS.index("@media (max-width: 560px)"):]
    assert "grid-template-areas" in phone
    assert ".data-table thead { display: none; }" in phone
    assert ".cell-time" in phone and ".cell-actions" in phone


def test_customer_booking_exposes_a_real_date_field(client):
    body = client.get("/book?service=1&barber=1&date=2026-09-16").get_data(as_text=True)
    assert 'type="date"' in input_tag(body, "date-input")
    # Slot choice stays a fixed set of radios — never a free-form time box.
    slots = re.findall(r'name="time" value="(\d\d:\d\d)"', body)
    assert slots, "no slots rendered"
    assert 'name="time" type="text"' not in body
    assert not re.search(r'<input[^>]*name="time"[^>]*type="(?:text|number)"', body)


def test_admin_fields_are_native_date_and_time_inputs(admin_client):
    body = admin_client.get("/admin/?date=2026-09-16").get_data(as_text=True)
    for control, kind in [("f-date", "date"), ("b-date", "date"),
                          ("b-start", "time"), ("b-end", "time")]:
        assert f'type="{kind}"' in input_tag(body, control), control
    # The fields the picker JS binds to include their labels.
    assert 'for="b-start"' in body and 'for="f-date"' in body


def test_admin_table_exposes_card_reflow_hooks(admin_client):
    body = admin_client.get("/admin/?date=2026-09-16&barber=1").get_data(as_text=True)
    for hook in ["cell-time", "cell-barber", "cell-customer", "cell-service",
                 "cell-status", "cell-actions"]:
        assert hook in body, hook
    # Explicit roles keep the table semantics when the cells are laid out as cards.
    assert 'role="table"' in body and 'role="rowgroup"' in body
    assert 'role="rowheader"' in body and 'role="cell"' in body


def test_admin_day_stepper_is_grouped_for_small_screens(admin_client):
    body = admin_client.get("/admin/?date=2026-09-16").get_data(as_text=True)
    assert 'class="filters-nav"' in body
    assert "Prev" in body and "Next" in body
