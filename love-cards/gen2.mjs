import { writeFileSync, mkdirSync } from 'fs';
const DIR = '/tmp/claude-0/-home-user-panamera-studio/9251327f-591d-5432-8854-c8addc799376/scratchpad/memes2';
mkdirSync(DIR, { recursive: true });
const W = 1080, H = 1080;
const OL = '#3a2b26';       // warm outline
const round = n => Math.round(n * 10) / 10;

// ---------- defs (shadows, grain, body shading) ----------
function defs(t) {
  const [c0, c1, c2] = t.bg;
  const a = t.accent;
  return `<defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.3" y2="1">
      <stop offset="0" stop-color="${c0}"/><stop offset="0.55" stop-color="${c1}"/><stop offset="1" stop-color="${c2}"/>
    </linearGradient>
    <radialGradient id="frogG" cx="0.36" cy="0.30" r="0.9">
      <stop offset="0" stop-color="#b4e88a"/><stop offset="0.55" stop-color="#8fd06a"/><stop offset="1" stop-color="#5fa845"/>
    </radialGradient>
    <radialGradient id="frogBelly" cx="0.5" cy="0.35" r="0.8">
      <stop offset="0" stop-color="#e6f7cf"/><stop offset="1" stop-color="#bfe89a"/>
    </radialGradient>
    <radialGradient id="chickG" cx="0.36" cy="0.28" r="0.95">
      <stop offset="0" stop-color="#ffe9a0"/><stop offset="0.5" stop-color="#ffd23f"/><stop offset="1" stop-color="#f2ab1e"/>
    </radialGradient>
    <radialGradient id="blushP" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#ff8fa6" stop-opacity="0.85"/><stop offset="1" stop-color="#ff8fa6" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="blushG" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#f28f8f" stop-opacity="0.8"/><stop offset="1" stop-color="#f28f8f" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="lightA" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="${a}" stop-opacity="0.55"/><stop offset="1" stop-color="${a}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="lightB" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#ffffff" stop-opacity="${t.night ? 0.16 : 0.7}"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vign" cx="0.5" cy="0.46" r="0.72">
      <stop offset="0.6" stop-color="#000000" stop-opacity="0"/><stop offset="1" stop-color="${t.night ? '#0a0820' : '#5a3a2a'}" stop-opacity="${t.night ? 0.5 : 0.14}"/>
    </radialGradient>
    <filter id="soft" x="-40%" y="-40%" width="180%" height="180%">
      <feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#2a1c14" flood-opacity="0.20"/>
    </filter>
    <filter id="softS" x="-60%" y="-60%" width="220%" height="220%">
      <feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#2a1c14" flood-opacity="0.18"/>
    </filter>
    <filter id="txtSh" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="${t.night ? '#00000066' : '#ffffffcc'}" flood-opacity="1"/>
    </filter>
    <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 ${t.night ? 0.07 : 0.05} 0"/></filter>
    <filter id="blur20"><feGaussianBlur stdDeviation="20"/></filter>
  </defs>`;
}

// soft contact shadow on the ground
const ground = (x, y, rx, ry = 26) =>
  `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="#2a1c14" opacity="0.16" filter="url(#blur20)"/>`;

// ---------- helpers ----------
const heart = (x, y, s, c, rot = 0, op = 1) =>
  `<path transform="translate(${x} ${y}) rotate(${rot}) scale(${s})" opacity="${op}" d="M0 6 q-11 -16 -25 -5 q-11 10 25 33 q36 -23 25 -33 q-14 -11 -25 5 z" fill="${c}"/>`;
const star4 = (x, y, s, c, op = 1) =>
  `<path transform="translate(${x} ${y}) scale(${s})" opacity="${op}" d="M0 -16 q3 12 16 15 q-13 3 -16 15 q-3 -12 -16 -15 q13 -3 16 -15 z" fill="${c}"/>`;
const dot = (x, y, r, c, op = 1) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${c}" opacity="${op}"/>`;
const note = (x, y, s, c) =>
  `<g transform="translate(${x} ${y}) scale(${s})" filter="url(#softS)"><rect x="-3" y="-26" width="7" height="30" rx="3.5" fill="${c}"/><ellipse cx="-9" cy="4" rx="12" ry="8.5" fill="${c}"/><path d="M4 -26 q17 2 15 17 q-7 -9 -15 -7 z" fill="${c}"/></g>`;
const cup = (lid) => `
  <path d="M-27 -6 L27 -6 L20 62 L-20 62 Z" fill="#fff6ea" stroke="${OL}" stroke-width="6"/>
  <path d="M-24 -6 L-19 60 L-8 60 L-13 -6 Z" fill="#ffffff" opacity="0.5"/>
  <rect x="-32" y="-21" width="64" height="19" rx="7" fill="${lid}" stroke="${OL}" stroke-width="6"/>
  <rect x="-7" y="-40" width="15" height="20" rx="5" fill="${lid}" stroke="${OL}" stroke-width="5"/>`;

// ---------- characters (v2, shaded) ----------
function frog(x, y, s = 1, { arm = 'none', armLid = '#6b4a30', flip = false, sleepy = true, browAngry = false } = {}) {
  const f = flip ? -1 : 1;
  return `<g transform="translate(${x} ${y}) scale(${s * f} ${s})" filter="url(#soft)">
    <ellipse cx="-60" cy="112" rx="36" ry="18" fill="#7bbf5a" stroke="${OL}" stroke-width="6"/>
    <ellipse cx="58" cy="114" rx="32" ry="17" fill="#7bbf5a" stroke="${OL}" stroke-width="6"/>
    <path d="M-128 60 q-40 4 -52 46 q-6 24 20 26 q24 0 26 -26 q2 -30 18 -38 z" fill="#7fc258" stroke="${OL}" stroke-width="6"/>
    <ellipse cx="0" cy="14" rx="126" ry="112" fill="url(#frogG)" stroke="${OL}" stroke-width="7"/>
    <path d="M-96 -60 q60 -36 150 6" fill="none" stroke="#ffffff" stroke-width="14" stroke-linecap="round" opacity="0.35"/>
    <ellipse cx="0" cy="34" rx="82" ry="74" fill="url(#frogBelly)" opacity="0.9"/>
    <ellipse cx="-86" cy="18" rx="26" ry="17" fill="url(#blushG)"/>
    <ellipse cx="86" cy="18" rx="26" ry="17" fill="url(#blushG)"/>
    ${sleepy
      ? `<path d="M-68 -28 q19 17 38 0" fill="none" stroke="${OL}" stroke-width="7" stroke-linecap="round"/>
         <path d="M30 -28 q19 17 38 0" fill="none" stroke="${OL}" stroke-width="7" stroke-linecap="round"/>`
      : `<g><ellipse cx="-48" cy="-22" rx="12" ry="14" fill="#fff"/><circle cx="-45" cy="-19" r="8" fill="${OL}"/><circle cx="-42" cy="-23" r="3" fill="#fff"/>
         <ellipse cx="48" cy="-22" rx="12" ry="14" fill="#fff"/><circle cx="45" cy="-19" r="8" fill="${OL}"/><circle cx="48" cy="-23" r="3" fill="#fff"/></g>`}
    ${browAngry ? `<path d="M-66 -46 l34 12 M66 -46 l-34 12" stroke="${OL}" stroke-width="7" stroke-linecap="round"/>` : ''}
    <path d="M-32 16 q32 30 64 0" fill="#7a3a28" stroke="${OL}" stroke-width="5"/>
    <path d="M-72 14 q-8 68 72 90 q80 -22 72 -90 q-36 32 -72 32 q-36 0 -72 -32 z" fill="#3a2a20" stroke="${OL}" stroke-width="5"/>
    <path d="M-40 60 q0 40 40 58 q-6 -34 -6 -58 z" fill="#4a3628" opacity="0.6"/>
    ${arm === 'cup' ? `
      <path d="M96 6 q64 -6 100 -32" fill="none" stroke="#7fc258" stroke-width="26" stroke-linecap="round"/>
      <path d="M96 6 q64 -6 100 -32" fill="none" stroke="${OL}" stroke-width="26" stroke-linecap="round" opacity="0" />
      <g transform="translate(204 -20) rotate(8)" filter="url(#softS)">${cup(armLid)}</g>` : ''}
    ${arm === 'up' ? `<path d="M100 -8 q56 -30 78 -70" fill="none" stroke="#7fc258" stroke-width="26" stroke-linecap="round"/><circle cx="178" cy="-78" r="15" fill="#7fc258" stroke="${OL}" stroke-width="5"/>` : ''}
  </g>`;
}

function chick(x, y, s = 1, { wing = 'none', wingLid = '#c85a7a', flip = false, mood = 'happy' } = {}) {
  const f = flip ? -1 : 1;
  const eyes = mood === 'angry'
    ? `<path d="M-60 20 l32 12 M60 20 l-32 12" stroke="${OL}" stroke-width="6.5" stroke-linecap="round"/>
       <circle cx="-44" cy="34" r="7.5" fill="${OL}"/><circle cx="44" cy="34" r="7.5" fill="${OL}"/>`
    : mood === 'love'
      ? `${heart(-45, 30, 0.72, '#e0455a')}${heart(45, 30, 0.72, '#e0455a')}`
      : `<g><ellipse cx="-45" cy="30" rx="11" ry="13" fill="#fff"/><circle cx="-43" cy="33" r="7.5" fill="${OL}"/><circle cx="-40" cy="29" r="2.6" fill="#fff"/>
         <ellipse cx="45" cy="30" rx="11" ry="13" fill="#fff"/><circle cx="47" cy="33" r="7.5" fill="${OL}"/><circle cx="50" cy="29" r="2.6" fill="#fff"/></g>`;
  return `<g transform="translate(${x} ${y}) scale(${s * f} ${s})" filter="url(#soft)">
    <path d="M-30 120 l0 34 M-30 154 l-16 12 M-30 154 l0 18 M-30 154 l16 12" stroke="#e08a2a" stroke-width="7.5" fill="none" stroke-linecap="round"/>
    <path d="M40 120 l0 34 M40 154 l-16 12 M40 154 l0 18 M40 154 l16 12" stroke="#e08a2a" stroke-width="7.5" fill="none" stroke-linecap="round"/>
    <ellipse cx="0" cy="32" rx="108" ry="114" fill="url(#chickG)" stroke="${OL}" stroke-width="7"/>
    <path d="M-92 -30 q56 -40 150 10" fill="none" stroke="#fff" stroke-width="14" stroke-linecap="round" opacity="0.4"/>
    <path d="M-24 -82 q-10 -36 14 -50 q-2 24 11 32 q15 -20 36 -20 q-11 20 -4 32 q19 -6 32 6 q-28 9 -39 13 q-31 9 -50 -15 z" fill="#f2dfa2" stroke="${OL}" stroke-width="5"/>
    <path d="M-14 -84 q-4 -22 8 -34" fill="none" stroke="#d9c184" stroke-width="3"/>
    <ellipse cx="-72" cy="54" rx="24" ry="16" fill="url(#blushP)"/>
    <ellipse cx="72" cy="54" rx="24" ry="16" fill="url(#blushP)"/>
    <path d="M-92 40 q-42 20 -22 78 q10 22 30 12 q-24 -40 -6 -84 z" fill="#f7bf2e" stroke="${OL}" stroke-width="6"/>
    ${eyes}
    <g stroke="#1c1c1c" stroke-width="7" fill="#cfe8ff" fill-opacity="0.28">
      <rect x="-82" y="0" width="68" height="54" rx="14"/>
      <rect x="14" y="0" width="68" height="54" rx="14"/>
    </g>
    <path d="M-74 8 l18 0 M20 8 l18 0" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity="0.7"/>
    <g stroke="#1c1c1c" stroke-width="7" fill="none"><path d="M-14 18 q14 -8 28 0"/><path d="M-82 16 l-18 -6"/><path d="M82 16 l18 -6"/></g>
    <path d="M-10 66 l20 0 l-10 13 z" fill="#f4a63c" stroke="${OL}" stroke-width="3"/>
    <path d="M-17 82 q17 8 34 0 q-6 17 -17 17 q-11 0 -17 -17 z" fill="#e0455a" stroke="#b83545" stroke-width="3"/>
    <path d="M-8 84 q8 4 16 0" stroke="#ff96a6" stroke-width="3" fill="none" opacity="0.7"/>
    ${wing === 'cup' ? `<g transform="translate(-120 100) rotate(-10)" filter="url(#softS)">${cup(wingLid)}</g>` : ''}
    ${wing === 'up' ? `<path d="M78 34 q46 -8 70 -42" fill="none" stroke="#f7bf2e" stroke-width="26" stroke-linecap="round"/><circle cx="148" cy="-8" r="14" fill="#f7bf2e" stroke="${OL}" stroke-width="5"/>` : ''}
  </g>`;
}

const moon = (x, y, s) => `<g transform="translate(${x} ${y}) scale(${s})" filter="url(#softS)"><path d="M0 -40 a40 40 0 1 0 30 70 a52 52 0 1 1 -30 -70 z" fill="#ffe98a" stroke="#e9cf5c" stroke-width="3"/><circle cx="-6" cy="-8" r="5" fill="#f0d873"/><circle cx="8" cy="14" r="4" fill="#f0d873"/></g>`;

// ---------- text with soft panel ----------
function textBlock(lines, yStart, fs, fill, lh) {
  lh = lh || fs * 1.26;
  return lines.map((ln, i) =>
    `<text x="540" y="${yStart + i * lh}" font-family="Comfortaa" font-weight="700" font-size="${fs}" fill="${fill}" text-anchor="middle" filter="url(#txtSh)" letter-spacing="0.5">${ln}</text>`
  ).join('\n');
}

// ---------- THEMES (same personalized concepts) ----------
const T = [];
T.push({ id: '01-hru', bg: ['#ffeef5', '#ffd9e8', '#ffc2dd'], accent: '#ff9ec4', textFill: '#8a2f56',
  top: ['Я БЫ С ТОБОЙ ХРЮКАЛ БЫ', 'И ХРЮКАЛ, ХРЮ И ХРЮ'], bot: ['ХРЮ БЫ И ХРЮ БЫ,', 'И ХРЮ БЫ, И ХРЮ'], fs: 50,
  deco: () => [heart(150, 300, 2.4, '#ff8fb4', -12, .95), heart(930, 320, 1.9, '#ff6fa0', 10, .95), heart(880, 660, 1.5, '#ffa7c6', 6, .9), heart(175, 660, 1.4, '#ff8fb4', -8, .9), star4(775, 250, 1.6, '#ffd36e'), dot(120, 470, 9, '#ffb0cd'), dot(965, 520, 7, '#ff8fb4'), `<text x="250" y="470" font-family="Comfortaa" font-size="34" font-weight="700" fill="#ff7aa8" transform="rotate(-10 250 470)" opacity="0.85">хрю</text>`, `<text x="828" y="470" font-family="Comfortaa" font-size="30" font-weight="700" fill="#ff7aa8" transform="rotate(8 828 470)" opacity="0.85">хрю-хрю</text>`].join(''),
  scene: () => ground(360, 712, 118) + ground(720, 720, 108) + frog(360, 590, 1, {}) + chick(720, 600, 1, { mood: 'love' }) + heart(540, 555, 1.9, '#ff5f92') });

T.push({ id: '02-cars', bg: ['#fff4dc', '#ffe4bd', '#ffd098'], accent: '#ffb15a', textFill: '#8a5316',
  top: ['ТЫ МАШИНКИ ПРОДАЁШЬ', 'КАК ПИРОЖКИ, КАК ПИРОЖКИ'], bot: ['А Я ТОБОЮ ЛЮБОВАЛСЯ БЫ', 'И ЛЮБОВАЛСЯ, ЛЮБОВАЛСЯ'], fs: 47,
  deco: () => [star4(160, 260, 1.5, '#ffd36e'), star4(742, 220, 1.2, '#ff9f5a'), dot(150, 470, 9, '#ffbf85'), heart(940, 620, 1.4, '#ff9f7a'), car(230, 300, 0.72, '#ff8f5a'), car(835, 285, 0.62, '#5aa7ff')].join(''),
  scene: () => ground(345, 720, 116) + ground(715, 718, 112) + frog(345, 600, 0.95, { arm: 'up' }) + chick(715, 595, 1, { wing: 'up' }) + car(715, 782, 0.66, '#ff6f61') });

T.push({ id: '03-oblik', bg: ['#f3e8ff', '#ffe1ea', '#ffd0dd'], accent: '#c79bff', textFill: '#5a3a7a',
  top: ['ДАЖЕ КОГДА ТЫ ТЕРЯЕШЬ', 'ЧЕЛОВЕЧЕСКИЙ ОБЛИК —'], bot: ['Я БЫ ТЕБЯ ЛЮБИЛ И ЛЮБИЛ,', 'И ЛЮБИЛ БЫ, И ЛЮБИЛ'], fs: 46,
  deco: () => [heart(210, 320, 2.0, '#ff8fb4', -10, .9), heart(890, 700, 1.5, '#ffa7c6', 8, .9), star4(180, 560, 1.5, '#c9a7ff'), star4(760, 250, 1.4, '#ffd36e'), `<text x="812" y="455" font-family="Comfortaa" font-size="40" font-weight="700" fill="#c94f4f" transform="rotate(10 812 455)">грр!</text>`, `<path d="M842 470 l24 -7 M848 452 l20 11" stroke="#c94f4f" stroke-width="6" stroke-linecap="round"/>`].join(''),
  scene: () => ground(360, 720, 116) + ground(725, 716, 110) + frog(360, 600, 1, { arm: 'up', sleepy: false }) + chick(725, 590, 1, { mood: 'angry' }) + heart(540, 545, 1.7, '#ff6f9a') });

T.push({ id: '04-stroyka', bg: ['#e2edf8', '#cfe0f0', '#b6cfe8'], accent: '#8fbce0', textFill: '#264a68',
  top: ['ДОЖДЬ ИДЁТ ПЯТЫЕ СУТКИ,', 'А Я БЫ СТРОИЛ И СТРОИЛ —'], bot: ['ЛИШЬ БЫ ДОМОЙ К ТЕБЕ,', 'ДА К ТЕБЕ, ДА К ТЕБЕ'], fs: 46,
  deco: () => { const xs = [130, 250, 380, 620, 760, 900, 990, 320, 690, 850]; const drops = xs.map((x, i) => rain(x, 250 + (i % 4) * 55, 1.2 + (i % 3) * 0.25, '#7fb0d8')); return [`<g filter="url(#softS)"><ellipse cx="540" cy="150" rx="128" ry="50" fill="#f0f6fc"/><ellipse cx="436" cy="162" rx="74" ry="38" fill="#f0f6fc"/><ellipse cx="644" cy="164" rx="74" ry="38" fill="#f0f6fc"/></g>`, ...drops].join(''); },
  scene: () => ground(360, 726, 112) + ground(730, 724, 110) + `<g filter="url(#softS)" transform="translate(540 470)"><rect x="-48" y="-10" width="96" height="72" rx="6" fill="#ffe3c0" stroke="#264a68" stroke-width="5"/><path d="M-60 -10 l60 -46 l60 46 z" fill="#e07a5a" stroke="#264a68" stroke-width="5"/><rect x="-14" y="22" width="28" height="40" rx="4" fill="#8b5a3c" stroke="#264a68" stroke-width="4"/></g>` + frog(360, 612, 0.95, { arm: 'up', sleepy: false }) + `<g transform="translate(300 432)" filter="url(#softS)"><path d="M-72 0 q72 -74 144 0 z" fill="#ff6f61" stroke="#264a68" stroke-width="5"/><path d="M0 0 l0 150" stroke="#264a68" stroke-width="6"/></g>` + chick(732, 606, 0.95, { wing: 'cup', wingLid: '#6b4a30' }) });

T.push({ id: '05-noch', bg: ['#241d4a', '#352c63', '#4c3f7e'], accent: '#8a7bd8', textFill: '#fdf3df', night: true,
  top: ['СПИ, МАЛЮТКА, НЕ СХОДИ С УМА —'], bot: ['Я БЫ НЕРВЫ ТВОИ БЕРЁГ БЫ', 'И БЕРЁГ БЫ, И БЕРЁГ'], fs: 45,
  deco: () => { const pts = [[140, 210], [300, 155], [470, 230], [640, 165], [820, 215], [955, 305], [180, 370], [905, 440], [250, 480], [790, 570], [120, 560], [560, 300]]; const st = pts.map((p, i) => star4(p[0], p[1], 0.9 + (i % 3) * 0.5, '#ffe98a', 0.9)); st.push(moon(905, 220, 1.5)); st.push(`<text x="470" y="300" font-family="Comfortaa" font-size="42" font-weight="700" fill="#c8bdf0" opacity="0.9">z z Z</text>`); return st.join(''); },
  scene: () => ground(370, 754, 112, 24) + ground(720, 770, 100, 22) + frog(370, 640, 0.95, { arm: 'up' }) + chick(720, 660, 0.9, {}) + heart(545, 600, 1.6, '#ff8fb4') });

T.push({ id: '06-dieta', bg: ['#fff2f0', '#ffdede', '#ffc7ce'], accent: '#ff9aa6', textFill: '#8a2f3f',
  top: ['ОДНУ ЛОЖЕЧКУ — РАССАСЫВАЕШЬ,', 'А Я КОРМИЛ БЫ И КОРМИЛ:'], bot: ['ТВОРОГ, ПРОТЕИН, ДА ЯГОДЫ,', 'И КОРМИЛ БЫ, И КОРМИЛ'], fs: 44,
  deco: () => [...[[180, 300], [905, 305], [852, 520], [150, 520]].map(p => `<g transform="translate(${p[0]} ${p[1]})" filter="url(#softS)"><path d="M0 -14 q27 -6 27 19 q0 31 -27 41 q-27 -10 -27 -41 q0 -25 27 -19 z" fill="#e8455a" stroke="#8a2f3f" stroke-width="4"/><path d="M-15 -14 q15 -11 30 0 q-15 -2 -30 0z" fill="#5aa74a" stroke="#3e7a34" stroke-width="3"/><circle cx="-7" cy="6" r="2.3" fill="#ffe08a"/><circle cx="8" cy="11" r="2.3" fill="#ffe08a"/><circle cx="0" cy="21" r="2.3" fill="#ffe08a"/></g>`), heart(760, 250, 1.5, '#ff7aa0'), dot(120, 420, 8, '#ff9fb0')].join(''),
  scene: () => ground(355, 720, 114) + ground(720, 716, 112) + frog(355, 600, 0.95, { arm: 'up', sleepy: false }) + chick(720, 595, 1, { wing: 'up' }) + `<g transform="translate(540 640) rotate(20)" filter="url(#softS)"><ellipse cx="0" cy="0" rx="23" ry="16" fill="#eef2f6" stroke="${OL}" stroke-width="4"/><ellipse cx="-4" cy="-3" rx="10" ry="6" fill="#fff"/><rect x="-4" y="11" width="8" height="72" rx="4" fill="#eef2f6" stroke="${OL}" stroke-width="4"/></g>` });

T.push({ id: '07-music', bg: ['#efe4ff', '#e2d0ff', '#d0b8ff'], accent: '#a77fe6', textFill: '#4a2f7a',
  top: ['ТЫ МНЕ МУЗЫКУ ШЛЁШЬ И ШЛЁШЬ,', 'СЮСИЙ МУЗИКУ, ХРЮ —'], bot: ['А Я БЫ СЛУШАЛ И СЛУШАЛ,', 'И СЛУШАЛ БЫ, И СЛУШАЛ'], fs: 44,
  deco: () => [note(210, 300, 1.9, '#8a5fd6'), note(880, 280, 1.6, '#a77fe6'), note(835, 520, 1.3, '#8a5fd6'), note(168, 520, 1.2, '#a77fe6'), `<g stroke="#a77fe6" stroke-width="9" stroke-linecap="round">${[0, 1, 2, 3, 4, 5, 6].map(i => `<line x1="${430 + i * 30}" y1="${470 - (i % 3) * 20}" x2="${430 + i * 30}" y2="${470 + (i % 3) * 20}"/>`).join('')}</g>`, dot(128, 400, 8, '#c3a7f0')].join(''),
  scene: () => ground(360, 726, 116) + ground(725, 722, 112) + frog(360, 605, 1, { arm: 'up' }) + `<g transform="translate(300 545)" stroke="${OL}" stroke-width="7" fill="#5a3a7a" filter="url(#softS)"><path d="M-94 -6 a94 94 0 0 1 188 0" fill="none"/><rect x="-110" y="-8" width="32" height="48" rx="11"/><rect x="78" y="-8" width="32" height="48" rx="11"/></g>` + chick(725, 600, 1, { wing: 'up', mood: 'love' }) });

T.push({ id: '08-ai', bg: ['#e2f0ff', '#d0e6ff', '#b8d6ff'], accent: '#6aa9f0', textFill: '#1f466e',
  top: ['Я ВСЁ ПРОГНАЛ БЫ ЧЕРЕЗ ИИ,', 'И СНОВА, И ОПЯТЬ, И ВНОВЬ —'], bot: ['НО УМНЕЙ ВСЕХ НЕЙРОСЕТЕЙ', 'ТЫ ОДНА, ХРЮ, ТЫ ОДНА'], fs: 44,
  deco: () => [star4(180, 300, 1.8, '#5aa7ff'), star4(900, 280, 1.5, '#7fc0ff'), star4(842, 520, 1.2, '#5aa7ff'), `<g stroke="#5aa7ff" stroke-width="7" stroke-linecap="round"><line x1="150" y1="468" x2="150" y2="512"/><line x1="128" y1="490" x2="172" y2="490"/></g>`, `<g stroke="#7fc0ff" stroke-width="7" stroke-linecap="round"><line x1="952" y1="418" x2="952" y2="458"/><line x1="932" y1="438" x2="972" y2="438"/></g>`, dot(250, 240, 6, '#9fceff'), dot(760, 220, 6, '#9fceff')].join(''),
  scene: () => ground(360, 726, 114) + ground(730, 720, 110) + frog(360, 605, 0.95, { arm: 'up', sleepy: false }) + `<g transform="translate(402 694)" filter="url(#softS)"><rect x="-62" y="-46" width="124" height="82" rx="9" fill="#2b2b40" stroke="#1c1c1c" stroke-width="5"/><rect x="-51" y="-38" width="102" height="66" rx="4" fill="#7fd3ff"/><path d="M-72 36 l144 0 l15 17 l-174 0 z" fill="#c7c7d6" stroke="#1c1c1c" stroke-width="5"/><text x="0" y="4" font-family="Comfortaa" font-size="30" fill="#1c2b40" text-anchor="middle" font-weight="700">AI</text></g>` + chick(730, 600, 1, {}) + heart(545, 560, 1.5, '#ff8fb4') });

T.push({ id: '09-koni', bg: ['#eaf7db', '#d7efc0', '#bfe4a0'], accent: '#9fd66f', textFill: '#3c6b2c',
  top: ['КУПИЛ БЫ Я ТЕБЕ КОНЯ —', 'БЕЛОГО, ГОЛУБОГЛАЗОГО,'], bot: ['И КАТАЛ БЫ ТЕБЯ, И КАТАЛ,', 'И КАТАЛ БЫ, И КАТАЛ'], fs: 45,
  deco: () => [`<g filter="url(#softS)"><circle cx="915" cy="220" r="48" fill="#ffe07a" stroke="#f0c94c" stroke-width="4"/>${[0, 1, 2, 3, 4, 5, 6, 7].map(i => { const a = i * Math.PI / 4; return `<line x1="${round(915 + Math.cos(a) * 58)}" y1="${round(220 + Math.sin(a) * 58)}" x2="${round(915 + Math.cos(a) * 78)}" y2="${round(220 + Math.sin(a) * 78)}" stroke="#ffcf5c" stroke-width="7" stroke-linecap="round"/>`; }).join('')}</g>`, heart(200, 300, 1.5, '#ff9fb0'), star4(320, 250, 1.4, '#ffe07a'), ...[[180, 700], [905, 720]].map(p => `<g transform="translate(${p[0]} ${p[1]})" filter="url(#softS)">${[0, 1, 2, 3, 4].map(i => { const a = i * 2 * Math.PI / 5; return `<circle cx="${round(Math.cos(a) * 13)}" cy="${round(Math.sin(a) * 13)}" r="9" fill="#ff9fc0"/>`; }).join('')}<circle r="8" fill="#ffd36e"/></g>`)].join(''),
  scene: () => ground(560, 782, 172, 30) + horse(560, 648, 1.2) + chick(560, 508, 0.5, { mood: 'love' }) + frog(210, 676, 0.78, { arm: 'up', sleepy: false }) });

T.push({ id: '10-kino', bg: ['#fbe9d2', '#f6d6b0', '#eec090'], accent: '#f0a86a', textFill: '#6b3f1e',
  top: ['МЫ КИНО СМОТРЕЛИ Б И СМОТРЕЛИ,', 'ФУТБОЛ ДА СЕРИАЛЫ,'], bot: ['ГРЫЗЛИ МОРКОВКУ ПОД МАТЧ,', 'И ГРЫЗЛИ БЫ, И ГРЫЗЛИ'], fs: 44,
  deco: () => [`<g transform="translate(540 345)" filter="url(#softS)"><rect x="-124" y="-58" width="248" height="120" rx="14" fill="#2b2b3f" stroke="#6b3f1e" stroke-width="6"/><rect x="-113" y="-47" width="226" height="98" rx="8" fill="#3d6fb0"/><circle cx="0" cy="2" r="27" fill="#ffffff" fill-opacity="0.92"/><path d="M-10 -12 l0 26 l22 -13 z" fill="#3d6fb0"/></g>`, pop(180, 500, 1.5, '#fff2cf'), pop(905, 500, 1.4, '#fff2cf'), pop(140, 640, 1.2, '#fff2cf'), pop(945, 630, 1.2, '#fff2cf'), star4(240, 470, 1.4, '#ffd36e'), heart(820, 470, 1.4, '#ff9f7a')].join(''),
  scene: () => `<g filter="url(#softS)" transform="translate(540 752)"><rect x="-312" y="-26" width="624" height="96" rx="26" fill="#c96f5a" stroke="#6b3f1e" stroke-width="7"/><rect x="-312" y="-58" width="286" height="60" rx="20" fill="#d98a72" stroke="#6b3f1e" stroke-width="7"/><rect x="26" y="-58" width="286" height="60" rx="20" fill="#d98a72" stroke="#6b3f1e" stroke-width="7"/></g>` + frog(352, 616, 0.8, { arm: 'up' }) + chick(712, 620, 0.8, { wing: 'up' }) + `<g transform="translate(540 636) rotate(18)" filter="url(#softS)"><path d="M0 -50 l21 74 q-21 16 -42 0 z" fill="#ff8f3a" stroke="#6b3f1e" stroke-width="4"/><path d="M0 -50 q-12 -21 -25 -21 q9 14 7 21 M0 -50 q0 -25 7 -29 q3 16 -2 29 M0 -50 q12 -19 25 -17 q-10 13 -20 17" fill="#5aa74a" stroke="#3e7a34" stroke-width="3"/></g>` });

// extra prop fns used above
function car(x, y, s, body) { return `<g transform="translate(${x} ${y}) scale(${s})" filter="url(#softS)"><path d="M-60 10 q6 -34 34 -36 l30 0 q26 2 40 34 l14 4 q10 3 10 14 l0 8 q0 6 -8 6 l-166 0 q-8 0 -8 -6 l0 -8 q0 -11 12 -14 z" fill="${body}" stroke="${OL}" stroke-width="6"/><path d="M-22 -22 l24 0 q18 2 28 24 l-52 0 z" fill="#dff1ff" stroke="${OL}" stroke-width="4"/><path d="M-26 -22 l0 24 l-22 0 q6 -20 22 -24 z" fill="#dff1ff" stroke="${OL}" stroke-width="4"/><circle cx="-40" cy="30" r="17" fill="#2b2320"/><circle cx="-40" cy="30" r="7" fill="#c9c9c9"/><circle cx="42" cy="30" r="17" fill="#2b2320"/><circle cx="42" cy="30" r="7" fill="#c9c9c9"/></g>`; }
function rain(x, y, s, c) { return `<path transform="translate(${x} ${y}) scale(${s})" d="M0 -14 q10 14 10 22 a10 10 0 0 1 -20 0 q0 -8 10 -22 z" fill="${c}" opacity="0.85"/>`; }
function pop(x, y, s, c) { return `<g transform="translate(${x} ${y}) scale(${s})" filter="url(#softS)"><circle cx="-6" cy="0" r="7" fill="${c}"/><circle cx="6" cy="-3" r="7" fill="${c}"/><circle cx="2" cy="7" r="7" fill="${c}"/></g>`; }
function horse(x, y, s) { return `<g transform="translate(${x} ${y}) scale(${s})" filter="url(#soft)"><ellipse cx="0" cy="0" rx="88" ry="58" fill="#fbf6ee" stroke="${OL}" stroke-width="6"/><path d="M-70 -30 q40 -30 150 20" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round" opacity="0.5"/><path d="M60 -20 q40 -20 44 -66 q2 -18 -14 -22 q-6 30 -30 44 q-20 12 -20 40 z" fill="#fbf6ee" stroke="${OL}" stroke-width="6"/><path d="M78 -84 q-6 -20 6 -34 q10 14 8 30 z" fill="#fbf6ee" stroke="${OL}" stroke-width="5"/><path d="M96 -80 q14 -14 30 -12 q-8 14 -22 22 z" fill="#fbf6ee" stroke="${OL}" stroke-width="5"/><path d="M56 -74 q-18 20 -12 74 q14 -8 18 -30 q4 24 10 34 q10 -14 6 -40 q10 16 14 22 q4 -30 -14 -52 z" fill="#dcae6a" stroke="${OL}" stroke-width="4"/><circle cx="96" cy="-58" r="8" fill="#6fc4e8"/><circle cx="99" cy="-61" r="3" fill="#fff"/><path d="M118 -60 l16 4 l-14 8 z" fill="#f4a63c" stroke="${OL}" stroke-width="3"/><path d="M-56 40 l-6 46 M-20 52 l0 44 M28 52 l4 44 M62 36 l10 44" stroke="${OL}" stroke-width="12" stroke-linecap="round"/><path d="M-86 -8 q-40 6 -50 60 q18 -14 24 -26 q-6 22 2 34 q14 -14 14 -34 q6 14 12 18 q6 -30 -16 -52 z" fill="#dcae6a" stroke="${OL}" stroke-width="4"/></g>`; }

// ---------- assemble ----------
function build(t) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  ${defs(t)}
  <rect width="${W}" height="${H}" fill="url(#bg)"/>
  <ellipse cx="270" cy="330" rx="420" ry="360" fill="url(#lightA)"/>
  <ellipse cx="820" cy="640" rx="380" ry="340" fill="url(#lightB)"/>
  ${t.deco()}
  ${t.scene()}
  <rect width="${W}" height="${H}" fill="url(#vign)"/>
  <rect width="${W}" height="${H}" filter="url(#grain)" opacity="0.55"/>
  ${textBlock(t.top.filter(Boolean), 150, t.fs, t.textFill)}
  ${textBlock(t.bot, 908, t.fs, t.textFill)}
</svg>`;
  writeFileSync(`${DIR}/${t.id}.svg`, svg);
  return `${t.id}.svg`;
}
console.log('WROTE:', T.map(build).join(' '));
