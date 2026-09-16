// Inline SVG icon set for the HUD, drawn in the familiar RTS command-card style.
// Every icon is authored here so the game ships with no image files.

const S = (body, vb = 32) =>
  `<svg viewBox="0 0 ${vb} ${vb}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${body}</svg>`;

const RES = {
  food: S(`
    <path d="M16 29V13" stroke="#8a6a1f" stroke-width="1.8" fill="none"/>
    <path d="M16 17c-4-1.4-5.5-5.5-5.5-8.5 4.2 0 6.8 2.8 6.8 6.7z" fill="#e9c447" stroke="#8a6a1f" stroke-width="1.2"/>
    <path d="M16 17c4-1.4 5.5-5.5 5.5-8.5-4.2 0-6.8 2.8-6.8 6.7z" fill="#f0d76a" stroke="#8a6a1f" stroke-width="1.2"/>
    <path d="M16 24c-4-1.4-5.5-5.5-5.5-8.5 4.2 0 6.8 2.8 6.8 6.7z" fill="#e9c447" stroke="#8a6a1f" stroke-width="1.2"/>
    <path d="M16 24c4-1.4 5.5-5.5 5.5-8.5-4.2 0-6.8 2.8-6.8 6.7z" fill="#f0d76a" stroke="#8a6a1f" stroke-width="1.2"/>
    <path d="M16 29c1.8-3 4.2-4 6.5-4.6" stroke="#8a6a1f" stroke-width="1.4" fill="none"/>`),
  wood: S(`
    <rect x="3" y="17" width="26" height="9" rx="4.5" fill="#8a6a41" stroke="#4f3a21" stroke-width="1.3"/>
    <ellipse cx="7.5" cy="21.5" rx="4" ry="4.5" fill="#c9a978" stroke="#4f3a21" stroke-width="1.3"/>
    <circle cx="7.5" cy="21.5" r="1.6" fill="#8a6a41"/>
    <rect x="6" y="7" width="23" height="9" rx="4.5" fill="#9c7c4e" stroke="#4f3a21" stroke-width="1.3"/>
    <ellipse cx="10.5" cy="11.5" rx="4" ry="4.5" fill="#dcc094" stroke="#4f3a21" stroke-width="1.3"/>
    <circle cx="10.5" cy="11.5" r="1.6" fill="#9c7c4e"/>`),
  gold: S(`
    <ellipse cx="16" cy="24" rx="11" ry="4.6" fill="#a8801f"/>
    <ellipse cx="16" cy="21" rx="11" ry="4.6" fill="#e2c14a" stroke="#7d5f16" stroke-width="1.2"/>
    <ellipse cx="16" cy="16" rx="9.5" ry="4.2" fill="#f0d76a" stroke="#7d5f16" stroke-width="1.2"/>
    <ellipse cx="16" cy="11" rx="7" ry="3.4" fill="#f8e9a4" stroke="#7d5f16" stroke-width="1.2"/>
    <ellipse cx="13" cy="10.4" rx="2.2" ry="1" fill="#fffbe4"/>`),
  pop: S(`
    <path d="M4 15 16 5l12 10" fill="#c8483d" stroke="#7f2a24" stroke-width="1.3" stroke-linejoin="round"/>
    <rect x="8" y="15" width="16" height="12" fill="#e0d3b4" stroke="#8a7a5a" stroke-width="1.3"/>
    <circle cx="16" cy="20" r="2.8" fill="#e8c39a"/>
    <path d="M11.4 27c0-2.9 2.1-4.4 4.6-4.4S20.6 24.1 20.6 27z" fill="#4d7fd6"/>`),
};

const BUILD = {
  towncenter: S(`
    <path d="M5 14 16 5l11 9" fill="#4d7fd6" stroke="#25406e" stroke-width="1.4" stroke-linejoin="round"/>
    <rect x="7" y="14" width="18" height="13" fill="#d8caa6" stroke="#8a7a58" stroke-width="1.4"/>
    <rect x="14" y="19" width="4" height="8" fill="#43331f"/>
    <rect x="9" y="17" width="3.5" height="3.5" fill="#f4d68f"/>
    <rect x="19.5" y="17" width="3.5" height="3.5" fill="#f4d68f"/>
    <path d="M16 5V1h7l-2 2 2 2h-7" fill="#4d7fd6" stroke="#25406e" stroke-width="1"/>`),
  house: S(`
    <path d="M4 15 16 5l12 10" fill="#4d7fd6" stroke="#25406e" stroke-width="1.4" stroke-linejoin="round"/>
    <rect x="7" y="15" width="18" height="12" fill="#e2d6b4" stroke="#8a7a58" stroke-width="1.4"/>
    <path d="M13 27v-6a3 3 0 0 1 6 0v6z" fill="#4a3927"/>
    <rect x="20" y="18" width="4" height="4" fill="#f2d18a"/>`),
  farm: S(`
    <rect x="4" y="7" width="24" height="18" rx="2" fill="#836b42" stroke="#5a4526" stroke-width="1.6"/>
    <path d="M7 12h18M7 16h18M7 20h18" stroke="#7fae57" stroke-width="2.6"/>
    <path d="M7 10.6h18M7 14.6h18M7 18.6h18" stroke="#a5d178" stroke-width="1"/>
    <path d="M4 7h24" stroke="#8a6a41" stroke-width="3"/>`),
  barracks: S(`
    <rect x="6" y="9" width="20" height="18" fill="#b3a68a" stroke="#5f5748" stroke-width="1.4"/>
    <rect x="6" y="6" width="5" height="4" fill="#6e6552"/>
    <rect x="14" y="6" width="5" height="4" fill="#6e6552"/>
    <rect x="22" y="6" width="5" height="4" fill="#6e6552"/>
    <rect x="13" y="18" width="7" height="9" rx="2" fill="#3a2c1c"/>
    <path d="M8 12l12 10M20 12L8 22" stroke="#ded9cc" stroke-width="2"/>
    <path d="M22 9h6v6z" fill="#4d7fd6"/>`),
  watchtower: S(`
    <rect x="9" y="10" width="14" height="18" fill="#cdc2a3" stroke="#6f6550" stroke-width="1.4"/>
    <rect x="7" y="6" width="5" height="5" fill="#8a7f65" stroke="#6f6550"/>
    <rect x="14" y="6" width="5" height="5" fill="#8a7f65" stroke="#6f6550"/>
    <rect x="21" y="6" width="5" height="5" fill="#8a7f65" stroke="#6f6550"/>
    <rect x="15" y="14" width="2.5" height="6" fill="#2f2a1e"/>
    <rect x="15" y="22" width="2.5" height="5" fill="#2f2a1e"/>
    <path d="M24 5V0h7l-2.2 2.4L31 5z" fill="#4d7fd6" stroke="#25406e" stroke-width="0.8"/>`),
};

const UNIT = {
  villager: S(`
    <circle cx="16" cy="9" r="4.6" fill="#e8c39a" stroke="#b08c66" stroke-width="1.2"/>
    <path d="M10.6 8.4a5.4 5.4 0 0 1 10.8 0z" fill="#8fb4f0"/>
    <path d="M11 15h10l1.6 10H9.4z" fill="#4d7fd6" stroke="#2f5695" stroke-width="1.2"/>
    <rect x="10.4" y="19.4" width="11.2" height="2.4" fill="#e7d9b6"/>
    <path d="M22 17l4 8" stroke="#7a5a33" stroke-width="2.4"/>
    <rect x="24" y="23" width="5" height="4" rx="1" fill="#9a9a9a"/>`),
  soldier: S(`
    <circle cx="15" cy="9" r="4.4" fill="#e8c39a"/>
    <path d="M9.6 8.6a5.4 5.4 0 0 1 10.8 0z" fill="#c9ced6" stroke="#8b929c" stroke-width="1.1"/>
    <rect x="9" y="14" width="13" height="11" rx="3" fill="#4d7fd6" stroke="#2f5695" stroke-width="1.2"/>
    <rect x="5" y="13" width="5" height="11" rx="2" fill="#cdb27a" stroke="#8f7a45" stroke-width="1.1"/>
    <rect x="6.4" y="16" width="2" height="5" fill="#2f5695"/>
    <path d="M24 6l3 20" stroke="#8a6a41" stroke-width="2.4"/>
    <path d="M23 6h6l-3-5z" fill="#d8dde3"/>`),
  archer: S(`
    <circle cx="15" cy="9" r="4.2" fill="#e8c39a"/>
    <path d="M9.8 8.6a5.2 5.2 0 0 1 10.4 0z" fill="#6f8f52"/>
    <rect x="9" y="14" width="13" height="11" rx="3" fill="#6f8f52" stroke="#4b6335" stroke-width="1.2"/>
    <rect x="9" y="20" width="13" height="3.4" fill="#2f5695"/>
    <path d="M26 8a11 11 0 0 0 0 18" fill="none" stroke="#8a6a41" stroke-width="2.2"/>
    <path d="M26 8v18" stroke="#efe9d8" stroke-width="1"/>
    <path d="M21 12l6 5-6 5" stroke="#6b4a26" stroke-width="2" fill="none"/>`),
  knight: S(`
    <circle cx="15" cy="9" r="4.4" fill="#e8c39a"/>
    <path d="M9.6 8.6a5.4 5.4 0 0 1 10.8 0z" fill="#dde2ea" stroke="#8b929c" stroke-width="1.1"/>
    <circle cx="15" cy="3.6" r="2.2" fill="#4d7fd6"/>
    <rect x="8" y="14" width="14" height="12" rx="3" fill="#4d7fd6" stroke="#2f5695" stroke-width="1.2"/>
    <rect x="9.4" y="15.4" width="4" height="9" rx="1.6" fill="rgba(255,255,255,0.28)"/>
    <rect x="4" y="13" width="5.4" height="12" rx="2" fill="#cdb27a" stroke="#8f7a45" stroke-width="1.1"/>
    <rect x="5.6" y="16" width="2.2" height="6" fill="#2f5695"/>
    <path d="M23 3l4 22" stroke="#8a6a41" stroke-width="2.6"/>
    <path d="M22 4h7l-3.5-4z" fill="#e6ecf4"/>`),
};

const MISC = {
  stop: S(`<rect x="9" y="9" width="14" height="14" rx="3" fill="#c8593f" stroke="#8a3524" stroke-width="1.5"/>
    <rect x="13" y="13" width="6" height="6" fill="#f2d0c4"/>`),
  age: S(`
    <path d="M4 22l4-11 5 6 3-9 3 9 5-6 4 11z" fill="#f0d76a" stroke="#a8801f" stroke-width="1.3" stroke-linejoin="round"/>
    <rect x="4" y="22" width="24" height="4" rx="1.6" fill="#d8b25c" stroke="#a8801f" stroke-width="1.2"/>
    <circle cx="16" cy="8" r="1.8" fill="#fff6cf"/>`),
  build: S(`<path d="M6 26V14l10-8 10 8v12z" fill="none" stroke="#d8b25c" stroke-width="2.2" stroke-linejoin="round"/>
    <path d="M13 26v-7h6v7" fill="none" stroke="#d8b25c" stroke-width="2.2"/>`),
  research: S(`<path d="M6 24h20v4H6z" fill="#8a6a41"/>
    <path d="M8 24V12h16v12" fill="none" stroke="#d8b25c" stroke-width="2"/>
    <path d="M12 12V6h8v6" fill="none" stroke="#d8b25c" stroke-width="2"/>
    <circle cx="16" cy="18" r="3" fill="#f0d76a"/>`),
  cancel: S(`<path d="M8 8l16 16M24 8L8 24" stroke="#c8593f" stroke-width="3.2" stroke-linecap="round"/>`),
  camera: S(`<circle cx="16" cy="16" r="10" fill="none" stroke="#d8b25c" stroke-width="2.2"/>
    <circle cx="16" cy="16" r="3.4" fill="#d8b25c"/>
    <path d="M16 2v5M16 25v5M2 16h5M25 16h5" stroke="#d8b25c" stroke-width="2.2"/>`),
  sword: S(`<path d="M20 4l8 8-14 14-4-4z" fill="#dde2ea" stroke="#8b929c" stroke-width="1.3"/>
    <path d="M6 26l4-4 4 4-4 4z" fill="#8a6a41"/>`),
};

// Formations: small diagrams of dots.
function formationIcon(id) {
  const dot = (x, y) => `<circle cx="${x}" cy="${y}" r="2.9" fill="#d8b25c"/>`;
  let body = '';
  if (id === 'line') {
    for (let i = 0; i < 5; i++) body += dot(5 + i * 5.5, 16);
  } else if (id === 'box') {
    for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) body += dot(8 + c * 8, 8 + r * 8);
  } else if (id === 'staggered') {
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 3; c++) body += dot(7 + c * 8 + (r % 2 ? 4 : 0), 8 + r * 8);
    }
  } else {
    for (let i = 0; i < 3; i++) {
      body += dot(6 + i * 3, 12 + i * 5);
      body += dot(26 - i * 3, 12 + i * 5);
    }
  }
  return S(body);
}

const FORMS = { line: formationIcon('line'), box: formationIcon('box'), staggered: formationIcon('staggered'), flank: formationIcon('flank') };

/** Returns an inline SVG string for the named icon. */
export function icon(name) {
  return RES[name] || BUILD[name] || UNIT[name] || MISC[name] || FORMS[name] || '';
}

export const ICONS = { RES, BUILD, UNIT, MISC, FORMS };
