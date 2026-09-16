/* Shared progressive controls. Native date/time inputs remain editable. */
(() => {
  'use strict';
  document.documentElement.classList.add('enhanced');
  const header = document.querySelector('.site-header');
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.getElementById('primary-navigation');
  const phone = window.matchMedia('(max-width: 760px)');

  function measureHeader() {
    document.documentElement.style.setProperty('--header-height', `${Math.ceil(header.getBoundingClientRect().height)}px`);
  }
  function setMenu(open, restoreFocus = false) {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    toggle.querySelector('.menu-label').textContent = open ? 'Close' : 'Menu';
    nav.classList.toggle('is-open', open);
    measureHeader();
    if (restoreFocus) toggle.focus({ preventScroll: true });
  }
  toggle.addEventListener('click', () => {
    // Safari does not normally focus buttons after a pointer activation.
    // Put keyboard navigation at the disclosure that was just opened.
    toggle.focus({ preventScroll: true });
    setMenu(toggle.getAttribute('aria-expanded') !== 'true');
  });
  header.addEventListener('keydown', event => {
    if (event.key !== 'Tab' || toggle.getAttribute('aria-expanded') !== 'true') return;
    const controls = [toggle, ...nav.querySelectorAll('a, button')];
    const index = controls.indexOf(document.activeElement);
    const next = index + (event.shiftKey ? -1 : 1);
    if (index >= 0 && next >= 0 && next < controls.length) {
      event.preventDefault();
      controls[next].focus();
    }
    // At either end, normal Tab navigation leaves the disclosure; no focus trap.
  });
  toggle.addEventListener('keydown', event => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setMenu(true);
      nav.querySelector('a, button').focus();
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      event.preventDefault();
      setMenu(false, true);
    }
  });
  document.addEventListener('click', event => {
    if (!header.contains(event.target)) setMenu(false);
  });
  nav.addEventListener('click', event => {
    if (event.target.closest('a')) setMenu(false);
  });
  phone.addEventListener('change', () => {
    const returnFocus = phone.matches && nav.contains(document.activeElement);
    setMenu(false, returnFocus);
  });
  if ('ResizeObserver' in window) new ResizeObserver(measureHeader).observe(header);
  window.addEventListener('resize', measureHeader);
  measureHeader();

  // Browser focus scrolling is inconsistent around sticky headers, especially on
  // reverse tab navigation. Adjust only when the actual focused control is hidden.
  function revealFocus() {
    const focused = document.activeElement;
    if (!focused || focused === document.body || header.contains(focused) || focused.closest('dialog')) return;
    const target = focused.matches('input[type="radio"]') ? focused.parentElement : focused;
    const bounds = target.getBoundingClientRect();
    const top = header.getBoundingClientRect().bottom + 12;
    const bottom = window.visualViewport ? window.visualViewport.offsetTop + window.visualViewport.height : window.innerHeight;
    if (bounds.top < top) window.scrollBy({ top: bounds.top - top, behavior: 'instant' });
    else if (bounds.bottom > bottom - 12 && bounds.height < bottom - top - 24) {
      window.scrollBy({ top: bounds.bottom - bottom + 12, behavior: 'instant' });
    }
  }
  document.addEventListener('focusin', event => {
    if (!header.contains(event.target)) setMenu(false);
    requestAnimationFrame(revealFocus);
  });
  if (window.visualViewport) window.visualViewport.addEventListener('resize', () => requestAnimationFrame(revealFocus));

  const dialog = document.getElementById('field-picker');
  const content = document.getElementById('picker-content');
  const heading = document.getElementById('picker-title');
  const help = document.getElementById('picker-help');
  let activeInput;
  let displayedMonth;
  const dateValue = day => `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
  const asDate = value => value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(value + 'T12:00:00') : null;
  const sameMonth = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();
  const monthName = day => new Intl.DateTimeFormat('en-AU', { month: 'long', year: 'numeric' }).format(day);
  const fullDate = day => new Intl.DateTimeFormat('en-AU', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(day);
  // Some WebKit versions expose showPicker for dates/times without opening UI.
  // Use the same accessible selector directly on that engine rather than relying
  // on a successful return value to mean that a native popup actually appeared.
  const webKitPicker = /AppleWebKit/.test(navigator.userAgent) && !/(Chrome|Chromium|Edg|OPR)\//.test(navigator.userAgent);

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function button(text, label, action) {
    const node = element('button', '', text);
    node.type = 'button';
    if (label) node.setAttribute('aria-label', label);
    node.addEventListener('click', action);
    return node;
  }
  function allowedDate(day) {
    const value = dateValue(day);
    const closed = (activeInput.dataset.closedDays || '').split(',').filter(Boolean).map(Number);
    return (!activeInput.min || value >= activeInput.min) && (!activeInput.max || value <= activeInput.max) && !closed.includes(day.getDay());
  }
  function closePicker() {
    if (typeof dialog.close === 'function') dialog.close();
    else {
      dialog.removeAttribute('open');
      activeInput?.focus({ preventScroll: true });
    }
  }
  function commit(value) {
    const input = activeInput;
    input.value = value;
    closePicker();
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  function drawCalendar(focusValue, controlToFocus) {
    content.replaceChildren();
    const minimum = asDate(activeInput.min) || new Date(1900, 0, 1, 12);
    const maximum = asDate(activeInput.max) || new Date(2100, 11, 31, 12);
    const bar = element('div', 'picker-month-bar');
    const previous = button('‹', 'Previous month', () => changeMonth(-1));
    const next = button('›', 'Next month', () => changeMonth(1));
    previous.disabled = displayedMonth <= new Date(minimum.getFullYear(), minimum.getMonth(), 1, 12);
    next.disabled = displayedMonth >= new Date(maximum.getFullYear(), maximum.getMonth(), 1, 12);
    const title = element('span', 'picker-month-title', monthName(displayedMonth));
    title.setAttribute('aria-live', 'polite');
    bar.append(previous, title, next);

    const selectors = element('div', 'picker-month-selects');
    const monthLabel = element('label', '', 'Month');
    const monthSelect = element('select'); monthSelect.id = 'picker-month'; monthLabel.htmlFor = monthSelect.id;
    for (let month = 0; month < 12; month++) {
      const option = element('option', '', new Intl.DateTimeFormat('en-AU', { month: 'long' }).format(new Date(2026, month, 1)));
      option.value = String(month);
      const last = new Date(displayedMonth.getFullYear(), month + 1, 0, 12);
      const first = new Date(displayedMonth.getFullYear(), month, 1, 12);
      option.disabled = last < minimum || first > maximum;
      monthSelect.append(option);
    }
    monthSelect.value = String(displayedMonth.getMonth());
    monthSelect.addEventListener('change', () => {
      displayedMonth = new Date(displayedMonth.getFullYear(), Number(monthSelect.value), 1, 12);
      drawCalendar(null, 'picker-month');
    });
    monthLabel.append(monthSelect);
    const yearLabel = element('label', '', 'Year');
    const yearSelect = element('select'); yearSelect.id = 'picker-year'; yearLabel.htmlFor = yearSelect.id;
    for (let year = minimum.getFullYear(); year <= maximum.getFullYear(); year++) {
      const option = element('option', '', String(year)); option.value = String(year); yearSelect.append(option);
    }
    yearSelect.value = String(displayedMonth.getFullYear());
    yearSelect.addEventListener('change', () => {
      let value = new Date(Number(yearSelect.value), displayedMonth.getMonth(), 1, 12);
      if (value < minimum) value = minimum;
      if (value > maximum) value = maximum;
      displayedMonth = new Date(value.getFullYear(), value.getMonth(), 1, 12);
      drawCalendar(null, 'picker-year');
    });
    yearLabel.append(yearSelect); selectors.append(monthLabel, yearLabel);
    const weekdays = element('div', 'picker-weekdays'); weekdays.setAttribute('aria-hidden', 'true');
    ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].forEach(day => weekdays.append(element('span', '', day)));
    const grid = element('div', 'picker-days'); grid.setAttribute('role', 'group'); grid.setAttribute('aria-label', 'Calendar dates');
    const blanks = (displayedMonth.getDay() + 6) % 7;
    for (let i = 0; i < blanks; i++) grid.append(element('span'));
    const count = new Date(displayedMonth.getFullYear(), displayedMonth.getMonth() + 1, 0).getDate();
    for (let day = 1; day <= count; day++) {
      const date = new Date(displayedMonth.getFullYear(), displayedMonth.getMonth(), day, 12);
      const value = dateValue(date);
      const dayButton = button(String(day), fullDate(date), () => commit(value));
      dayButton.dataset.date = value;
      dayButton.disabled = !allowedDate(date);
      dayButton.setAttribute('aria-pressed', String(value === activeInput.value));
      dayButton.tabIndex = -1;
      grid.append(dayButton);
    }
    grid.addEventListener('keydown', event => {
      if (!event.target.dataset.date) return;
      let day = asDate(event.target.dataset.date);
      const weekOffset = (day.getDay() + 6) % 7;
      const deltas = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7, Home: -weekOffset, End: 6 - weekOffset };
      if (!(event.key in deltas) && !['PageUp', 'PageDown'].includes(event.key)) return;
      event.preventDefault();
      if (event.key === 'PageUp' || event.key === 'PageDown') {
        const targetMonth = day.getMonth() + (event.key === 'PageUp' ? -1 : 1);
        const lastDay = new Date(day.getFullYear(), targetMonth + 1, 0).getDate();
        day = new Date(day.getFullYear(), targetMonth, Math.min(day.getDate(), lastDay), 12);
      } else day.setDate(day.getDate() + deltas[event.key]);
      const direction = ['ArrowLeft', 'ArrowUp', 'Home', 'PageUp'].includes(event.key) ? -1 : 1;
      while (day >= minimum && day <= maximum && !allowedDate(day)) day.setDate(day.getDate() + direction);
      if (!allowedDate(day)) return;
      displayedMonth = new Date(day.getFullYear(), day.getMonth(), 1, 12);
      drawCalendar(dateValue(day));
    });
    content.append(bar, selectors, weekdays, grid);
    const focusButton = Array.from(grid.querySelectorAll('button:not(:disabled)')).find(node => node.dataset.date === (focusValue || activeInput.value)) || grid.querySelector('button:not(:disabled)');
    if (focusButton) focusButton.tabIndex = 0;
    if (controlToFocus) document.getElementById(controlToFocus).focus();
    else if (dialog.open && focusValue) focusButton?.focus();

    function changeMonth(delta) {
      displayedMonth = new Date(displayedMonth.getFullYear(), displayedMonth.getMonth() + delta, 1, 12);
      drawCalendar();
      const candidates = content.querySelectorAll('.picker-month-bar button');
      const target = delta < 0 ? candidates[0] : candidates[1];
      (target.disabled ? content.querySelector('#picker-month') : target).focus();
    }
  }
  function drawTimes() {
    content.replaceChildren();
    const toMinutes = value => { const [hours, minutes] = value.split(':').map(Number); return hours * 60 + minutes; };
    const min = toMinutes(activeInput.min || '00:00');
    const max = toMinutes(activeInput.max || '23:45');
    const step = Math.max(1, Number(activeInput.step || 900) / 60);
    const grid = element('div', 'picker-times'); grid.setAttribute('role', 'group'); grid.setAttribute('aria-label', 'Times in Melbourne');
    for (let minute = min; minute <= max; minute += step) {
      const hour = Math.floor(minute / 60);
      const value = `${String(hour).padStart(2, '0')}:${String(minute % 60).padStart(2, '0')}`;
      const label = `${hour % 12 || 12}:${String(minute % 60).padStart(2, '0')} ${hour < 12 ? 'am' : 'pm'}`;
      const choice = button(label, null, () => commit(value));
      choice.dataset.time = value;
      choice.setAttribute('aria-pressed', String(value === activeInput.value));
      grid.append(choice);
    }
    content.append(grid);
  }
  function openAlternative(input) {
    activeInput = input;
    heading.textContent = input.type === 'date' ? 'Choose a date' : `Choose ${input.dataset.pickerLabel.toLowerCase()}`;
    help.textContent = input.type === 'date' ? (input.dataset.closedDays ? 'Tuesday–Saturday, within the dates shown. Use arrow keys to move between days.' : 'Choose a day to view the diary. Use the month and year controls for other dates.') : 'Choose a time in 15-minute intervals. All times are in Melbourne.';
    if (input.type === 'date') {
      let day = asDate(input.value) || asDate(input.min) || new Date();
      if (input.min && dateValue(day) < input.min) day = asDate(input.min);
      if (input.max && dateValue(day) > input.max) day = asDate(input.max);
      displayedMonth = new Date(day.getFullYear(), day.getMonth(), 1, 12);
      drawCalendar();
    } else drawTimes();
    if (!dialog.open) {
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else dialog.setAttribute('open', '');
    }
    (content.querySelector('[aria-pressed="true"]:not(:disabled)') || content.querySelector('.picker-days button:not(:disabled), .picker-times button') || dialog.querySelector('.picker-close')).focus();
  }
  function openNative(input, event) {
    if (input.disabled || input.readOnly) return;
    // Called directly during click/keyboard activation, never after an await.
    event.preventDefault();
    input.focus({ preventScroll: true });
    if (webKitPicker) {
      openAlternative(input);
      return;
    }
    try {
      if (typeof input.showPicker !== 'function') throw new Error('Native picker unavailable');
      input.showPicker();
    } catch {
      openAlternative(input);
    }
  }
  document.querySelectorAll('input[type="date"], input[type="time"]').forEach(input => {
    input.closest('.picker-field')?.classList.add('picker-ready');
    input.addEventListener('click', event => openNative(input, event));
    input.addEventListener('keydown', event => {
      if ((event.altKey && event.key === 'ArrowDown') || event.key === 'F4') openNative(input, event);
    });
  });
  document.querySelectorAll('[data-picker-for]').forEach(control => {
    control.hidden = false;
    control.addEventListener('click', () => openAlternative(document.getElementById(control.dataset.pickerFor)));
  });
  dialog.querySelector('.picker-close').addEventListener('click', closePicker);
  dialog.addEventListener('close', () => activeInput?.focus({ preventScroll: true }));
  dialog.addEventListener('click', event => {
    const box = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) closePicker();
  });
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); closePicker(); }
    if (event.key === 'Tab') {
      const controls = Array.from(dialog.querySelectorAll('button:not(:disabled), select, [tabindex="0"]')).filter(node => node.tabIndex >= 0);
      if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls.at(-1)?.focus(); }
      else if (!event.shiftKey && document.activeElement === controls.at(-1)) { event.preventDefault(); controls[0]?.focus(); }
    }
  });
  const blockStaff = document.getElementById('block-staff');
  if (blockStaff) {
    const updateHours = () => {
      const opening = String(blockStaff.selectedOptions[0].dataset.startHour).padStart(2, '0') + ':00';
      document.getElementById('block-start').min = opening;
      document.getElementById('block-end').min = opening;
    };
    blockStaff.addEventListener('change', updateHours);
    updateHours();
  }
})();
