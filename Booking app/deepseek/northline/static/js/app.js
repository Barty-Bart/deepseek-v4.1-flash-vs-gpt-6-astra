/* Northline Barber — small progressive enhancements. Everything works without JS. */
(function () {
  "use strict";

  var root = document.documentElement;

  /* ------------------------------------------------------------------ *
   * Sticky header: keep the anchor/focus offset in step with its height,
   * including when the phone menu expands it.
   * ------------------------------------------------------------------ */
  var header = document.getElementById("site-header");

  function syncHeaderHeight() {
    if (!header) { return; }
    var height = Math.round(header.getBoundingClientRect().height);
    if (height > 0) {
      root.style.setProperty("--header-h", height + "px");
    }
  }

  syncHeaderHeight();
  window.addEventListener("resize", syncHeaderHeight, { passive: true });
  window.addEventListener("orientationchange", syncHeaderHeight);
  if (header && typeof ResizeObserver === "function") {
    new ResizeObserver(syncHeaderHeight).observe(header);
  }
  // Web fonts or a late layout shift can change the height after load.
  window.addEventListener("load", syncHeaderHeight);

  /* ------------------------------------------------------------------ *
   * Phone navigation: a disclosure menu with real open/close state.
   * ------------------------------------------------------------------ */
  var navToggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("site-nav");
  var phoneNav = window.matchMedia("(max-width: 720px)");

  function navIsOpen() {
    return navToggle.getAttribute("aria-expanded") === "true";
  }

  function setNav(open) {
    navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    nav.dataset.open = open ? "true" : "false";
    syncHeaderHeight();
  }

  if (navToggle && nav) {
    navToggle.addEventListener("click", function () {
      setNav(!navIsOpen());
    });

    // Escape closes the menu and hands focus back to the button.
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && navIsOpen()) {
        setNav(false);
        navToggle.focus();
      }
    });

    // A tap outside the header closes it too.
    document.addEventListener("click", function (event) {
      if (!navIsOpen()) { return; }
      if (header.contains(event.target)) { return; }
      setNav(false);
    });

    // Following a link closes the menu (keeps state sane on same-page links).
    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) { setNav(false); }
    });

    // If the viewport becomes a desktop one, drop the collapsed state.
    var onBreakpoint = function () { setNav(false); };
    if (typeof phoneNav.addEventListener === "function") {
      phoneNav.addEventListener("change", onBreakpoint);
    } else if (typeof phoneNav.addListener === "function") {
      phoneNav.addListener(onBreakpoint);
    }
    setNav(false);
  }

  /* ------------------------------------------------------------------ *
   * Date and time fields: opening the picker from a click anywhere on the
   * field, not just on the small calendar/clock icon.
   * ------------------------------------------------------------------ */
  var PICKER_TYPES = ["date", "time", "datetime-local", "month", "week"];

  function isPickerField(element) {
    return element instanceof HTMLInputElement &&
      PICKER_TYPES.indexOf(element.type) !== -1;
  }

  function openPicker(input) {
    if (input.disabled || input.readOnly) { return; }
    if (typeof input.showPicker === "function") {
      try {
        // Per spec this is a no-op when the picker is already showing, so
        // clicking the calendar icon does not close it again.
        input.showPicker();
        return;
      } catch (err) {
        /* NotAllowedError, or an unsupported type: use the fallback below. */
      }
    }
    // Fallback for browsers without showPicker(): focus the field so the
    // browser's own affordance (or an on-screen picker) is right there, and
    // select the text so manual entry is one keystroke away.
    if (document.activeElement !== input) {
      input.focus({ preventScroll: true });
    }
    if (typeof input.select === "function") { input.select(); }
  }

  document.addEventListener("click", function (event) {
    if (event.defaultPrevented) { return; }
    var target = event.target;

    if (isPickerField(target)) {
      openPicker(target);
      return;
    }

    // Clicking the field's <label> counts as clicking the field.
    var label = target.closest ? target.closest("label[for]") : null;
    if (label) {
      var control = document.getElementById(label.getAttribute("for"));
      if (isPickerField(control)) { openPicker(control); }
    }
  });

  // Keyboard users get the picker on Enter/Space without losing manual typing
  // (typing and the arrow keys are left entirely to the browser).
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" && event.key !== " ") { return; }
    if (!isPickerField(event.target)) { return; }
    if (event.target.type === "time") { return; }  // typing a time uses the arrows
    event.preventDefault();
    openPicker(event.target);
  });

  /* ------------------------------------------------------------------ *
   * Customer booking form
   * ------------------------------------------------------------------ */
  var dateForm = document.querySelector("form.date-form");
  if (dateForm) {
    dateForm.addEventListener("change", function (event) {
      if (event.target.matches("[data-autosubmit-input]") && event.target.value) {
        dateForm.submit();
      }
    });
    // Keep the two date controls in sync before the form is submitted by the button.
    dateForm.addEventListener("submit", function () {
      var chip = dateForm.querySelector('input[name="date"][type="radio"]:checked');
      var input = dateForm.querySelector("#date-input");
      if (chip && input && chip.value !== input.value) {
        input.removeAttribute("name");
      } else if (chip && input) {
        chip.removeAttribute("name");
      }
    });
  }

  // Pick the first slot when the customer arrives with nothing chosen.
  var slotForm = document.querySelector("form.booking-form .slot-grid");
  if (slotForm && !slotForm.querySelector("input:checked")) {
    var first = slotForm.querySelector("input[data-first]");
    if (first) { first.checked = true; }
  }

  /* ------------------------------------------------------------------ *
   * Shared interactions
   * ------------------------------------------------------------------ */
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll("[data-copy]").forEach(function (button) {
    button.addEventListener("click", function () {
      var field = document.querySelector(button.getAttribute("data-copy"));
      if (!field) { return; }
      field.select();
      var done = function () {
        var original = button.textContent;
        button.textContent = "Copied";
        window.setTimeout(function () { button.textContent = original; }, 1800);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(field.value).then(done, done);
      } else {
        try { document.execCommand("copy"); done(); } catch (err) { /* leave selection visible */ }
      }
    });
  });

  // Move focus to the error summary after a rejected submission.
  var summary = document.getElementById("error-summary");
  if (summary) { summary.focus(); }
})();
