(() => {
  'use strict';
  document.documentElement.classList.add('enhanced');
  const form = document.getElementById('booking-form');
  if (form) {
    const dateInput = document.getElementById('date-picker');
    const slots = document.getElementById('time-slots');
    const message = document.getElementById('availability-message');
    const submit = document.getElementById('book-button');
    let controller;
    let requestId = 0;
    const setText = (id, value) => { const element = document.getElementById(id); if (element) element.textContent = value; };
    const formattedDate = (value, options) => new Intl.DateTimeFormat('en-AU', options).format(new Date(value + 'T12:00:00'));
    function syncSummary() {
      const service = form.querySelector('[name="service"]:checked');
      const barber = form.querySelector('[name="staff"]:checked');
      const slot = form.querySelector('[name="slot"]:checked');
      setText('summary-service', service.dataset.name);
      setText('summary-price', '$' + service.dataset.price);
      setText('summary-total', '$' + service.dataset.price);
      setText('summary-barber', barber.dataset.name);
      setText('summary-duration', service.dataset.duration + ' minutes');
      setText('mobile-service', service.dataset.name);
      setText('mobile-duration', service.dataset.duration + ' min');
      const mobilePrice = document.getElementById('mobile-price');
      mobilePrice.replaceChildren(document.createTextNode('$' + service.dataset.price + ' '));
      const currency = document.createElement('small'); currency.textContent = 'AUD'; mobilePrice.append(currency);
      if (dateInput.value) {
        setText('summary-date', formattedDate(dateInput.value, { weekday: 'short', day: 'numeric', month: 'short' }));
        setText('selected-date-label', formattedDate(dateInput.value, { weekday: 'long', day: 'numeric', month: 'long' }));
      }
      setText('summary-time', slot ? slot.nextElementSibling.textContent + ' · Melbourne time' : 'Choose a time that suits you');
      document.querySelectorAll('.date-chip').forEach(chip => {
        const selected = chip.dataset.date === dateInput.value;
        chip.classList.toggle('selected', selected);
        chip.setAttribute('aria-pressed', String(selected));
      });
    }
    async function refreshAvailability() {
      const id = ++requestId;
      if (controller) controller.abort();
      controller = new AbortController();
      slots.querySelectorAll('label').forEach(label => label.remove());
      slots.setAttribute('aria-busy', 'true');
      submit.disabled = true;
      message.hidden = false;
      message.classList.remove('is-error');
      message.textContent = 'Finding a little time for you…';
      syncSummary();
      const query = new URLSearchParams({ service: form.querySelector('[name="service"]:checked').value,
        staff: form.querySelector('[name="staff"]:checked').value, date: dateInput.value });
      try {
        const response = await fetch('/api/availability?' + query, { signal: controller.signal, headers: { Accept: 'application/json' } });
        const data = await response.json();
        if (id !== requestId) return;
        if (!response.ok) throw new Error(data.error || 'We couldn’t load the diary. Try another date or refresh this page.');
        for (const slot of data.slots) {
          const label = document.createElement('label'); label.className = 'time-option';
          const input = document.createElement('input'); input.type = 'radio'; input.name = 'slot'; input.value = slot.value; input.required = true;
          const span = document.createElement('span'); span.textContent = slot.label;
          label.append(input, span); slots.append(label);
        }
        message.hidden = data.slots.length > 0;
        const day = new Date(dateInput.value + 'T12:00:00').getDay();
        message.textContent = [0, 1].includes(day) ? 'A little time off. We’re closed on Sundays and Mondays. Choose Tuesday to Saturday.' : 'No times left for this day. Try another date or barber.';
        submit.disabled = data.slots.length === 0;
      } catch (error) {
        if (error.name === 'AbortError' || id !== requestId) return;
        message.hidden = false;
        message.classList.add('is-error');
        message.textContent = error instanceof TypeError ? 'We couldn’t reach the diary. Check your connection, then choose a date to try again.' : error.message;
      } finally {
        if (id === requestId) slots.removeAttribute('aria-busy');
      }
    }
    form.addEventListener('change', event => {
      if (['service', 'staff', 'date'].includes(event.target.name)) refreshAvailability();
      if (event.target.name === 'slot') syncSummary();
    });
    document.querySelectorAll('.date-chip').forEach(chip => chip.addEventListener('click', () => {
      dateInput.value = chip.dataset.date;
      refreshAvailability();
    }));
    form.addEventListener('submit', event => {
      if (event.submitter && event.submitter.classList.contains('refresh-times')) return;
      if (!form.querySelector('[name="slot"]:checked')) {
        event.preventDefault();
        message.hidden = false;
        message.textContent = 'Choose an available start time before confirming.';
        slots.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      submit.disabled = true;
      submit.textContent = 'Saving your appointment…';
    });
    window.addEventListener('pageshow', event => { if (event.persisted) refreshAvailability(); });
    syncSummary();
    submit.disabled = !slots.querySelector('[name="slot"]');
    const selected = document.querySelector('.date-chip.selected');
    if (selected) document.querySelector('.date-rail').scrollLeft = Math.max(0, selected.offsetLeft - selected.parentElement.offsetLeft - 12);
  }
  const errorSummary = document.querySelector('.error-summary[tabindex]');
  if (errorSummary) errorSummary.focus();
  const copyButton = document.getElementById('copy-link');
  if (copyButton) copyButton.addEventListener('click', async () => {
    const input = document.getElementById('private-link');
    const status = document.getElementById('copy-status');
    try {
      await navigator.clipboard.writeText(input.value);
      copyButton.textContent = 'Copied';
      status.textContent = 'Private link copied. Save it somewhere safe.';
    } catch {
      input.focus(); input.select();
      status.textContent = 'Select and copy the link above to save it.';
    }
  });
  document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  }));
})();
