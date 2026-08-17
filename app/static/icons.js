/* CertHub — Modo CAIXA: ícones de marca, favicon e troca de emoji→ícone.
   Só usado quando data-accent="caixa"; carregado antes de app.js/login.html. */
"use strict";

/* elemento "X" da CAIXA — geometria extraída da marca oficial (arquivo CAIXA_chapada,
   letra X do wordmark isolada). Cores fixas, sem alteração por tema (manual de marca).
   Variante negativa (branco+laranja) pra uso sobre fundo azul institucional/escuro
   — sidebar e tela de login. */
const CAIXA_X_ICON = `<svg viewBox="0 0 125.1 87.2" xmlns="http://www.w3.org/2000/svg">
  <polygon points="0,87.2 37.9,87.2 79.4,45.7 41.5,45.7" fill="#F39200"/>
  <polygon points="87.2,0 70.8,16.4 83.6,41.5 125.1,0" fill="#F39200"/>
  <polygon points="24.6,0 62.4,0 83.6,41.5 45.7,41.5" fill="#FFFFFF"/>
  <polygon points="54.3,70.8 79.4,45.7 100.5,87.2 62.7,87.2" fill="#FFFFFF"/>
</svg>`;
/* variante positiva (azul+laranja) — pro favicon, que roda sobre o chrome
   claro do navegador, não sobre o azul institucional. */
const CAIXA_X_ICON_POSITIVA = `<svg viewBox="0 0 4409 3075" xmlns="http://www.w3.org/2000/svg">
  <polygon points="0,3075 1335,3075 2798,1612 1463,1612" fill="#F79633"/>
  <polygon points="3075,0 2496,579 2946,1463 4409,0" fill="#F79633"/>
  <polygon points="866,0 2201,0 2946,1463 1612,1463" fill="#006CB5"/>
  <polygon points="1913,2496 2798,1612 3543,3075 2208,3075" fill="#006CB5"/>
</svg>`;
/* wordmark completo "CAIXA" oficial (variante negativa/branco+laranja, sem
   volume, sem conceito adicional) — usado na tela de login com Modo CAIXA ativo. */
const CAIXA_WORDMARK = `<svg viewBox="0 0 566.9 425.2" xmlns="http://www.w3.org/2000/svg">
  <polygon points="283.9,255.8 321.8,255.8 363.3,214.3 325.4,214.3" fill="#F39200"/>
  <polygon points="371.1,168.6 354.7,185 367.5,210.1 409,168.6" fill="#F39200"/>
  <polygon points="264.9,168.6 296.5,168.6 282.7,255.8 251.1,255.8" fill="#FFFFFF"/>
  <path d="M208.6,224.3l-1.6-16c-0.4-3.8-0.2-9.4-0.1-13.5h-1.3l-10.9,29.5h13.6H208.6z M182.4,255.8h-33.5l44.1-87.2h35l17.3,87.2h-33.5l-1.2-10.9h-24L182.4,255.8z" fill="#FFFFFF"/>
  <polygon points="308.5,168.6 346.3,168.6 367.5,210.1 329.6,210.1" fill="#FFFFFF"/>
  <path d="M445.3,224.3l-1.6-16c-0.3-3.8-0.2-9.4-0.1-13.5h-1.3l-10.9,29.5H445H445.3z M419,255.8h-33.4l44.1-87.2h35l17.3,87.2h-33.5l-1.2-10.9h-24L419,255.8z" fill="#FFFFFF"/>
  <path d="M153.8,204c-4.3-4.7-10-8.8-17.2-8.8c-9.5,0-18.4,7.5-19.9,17c-1.5,9.6,5.5,17,15,17c7.3,0,13.5-3.1,19.4-8.1l-6.1,32.6c-5.5,2.4-17.4,3.4-23.1,3.4c-24.8,0-41.2-19.3-37.3-44.1c4-25.5,27.2-45.8,52.8-45.8c7.2,0,14.4,1.3,20.7,3.6L153.8,204z" fill="#FFFFFF"/>
  <polygon points="338.2,239.4 363.3,214.3 384.4,255.8 346.6,255.8" fill="#FFFFFF"/>
</svg>`;
const BRAND_ICON_DEFAULT = "🔐";

const DEFAULT_FAVICON_HREF =
  "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔐</text></svg>";
const CAIXA_FAVICON_HREF = "data:image/svg+xml," + encodeURIComponent(CAIXA_X_ICON_POSITIVA);

/* ---- conjunto de ícones de linha (estilo Lucide, MIT) ---- */
function svgIcon(inner) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;
}

const ICON_PATHS = {
  sun: `<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>`,
  moon: `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/>`,
  "panel-left": `<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/>`,
  "panel-compact": `<rect x="3" y="3" width="18" height="18" rx="2"/><rect x="3" y="3" width="6" height="18" rx="1" fill="currentColor" stroke="none"/>`,
  "panel-top": `<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/>`,
  play: `<polygon points="6 3 20 12 6 21 6 3"/>`,
  edit: `<path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/>`,
  x: `<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>`,
  upload: `<path d="M12 3v12"/><path d="m7 8 5-5 5 5"/><path d="M5 21h14"/>`,
  settings: `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>`,
  globe: `<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10Z"/>`,
  dice: `<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.2" fill="currentColor" stroke="none"/><circle cx="16" cy="8" r="1.2" fill="currentColor" stroke="none"/><circle cx="8" cy="16" r="1.2" fill="currentColor" stroke="none"/><circle cx="16" cy="16" r="1.2" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none"/>`,
  tag: `<path d="M12 2H2v10l9.29 9.29a1 1 0 0 0 1.41 0l8.59-8.59a1 1 0 0 0 0-1.41Z"/><circle cx="7" cy="7" r="1.5" fill="currentColor" stroke="none"/>`,
  eye: `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z"/><circle cx="12" cy="12" r="3"/>`,
  save: `<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8"/><path d="M7 3v5h8"/>`,
  "clipboard-list": `<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><line x1="8" y1="11" x2="16" y2="11"/><line x1="8" y1="15" x2="14" y2="15"/>`,
  "file-text": `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/>`,
  "file-edit": `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h8"/><path d="M14 2v6h6"/><path d="m16 16.5 5-5a1.5 1.5 0 0 0-2.12-2.12l-5 5V17h2.62Z"/>`,
  radio: `<circle cx="12" cy="12" r="2"/><path d="M8.5 8.5a5 5 0 0 0 0 7"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M5.5 5.5a9 9 0 0 0 0 13"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/>`,
  "file-down": `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M12 12v6"/><path d="m9.5 15.5 2.5 2.5 2.5-2.5"/>`,
  mail: `<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/>`,
  "refresh-cw": `<path d="M21 12a9 9 0 0 1-15.5 6.3L3 16"/><path d="M3 12a9 9 0 0 1 15.5-6.3L21 8"/><path d="M21 3v5h-5"/><path d="M3 21v-5h5"/>`,
  search: `<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>`,
  "search-check": `<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><path d="m8.5 11 1.5 1.5L13.5 9" stroke-width="1.5"/>`,
  lock: `<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>`,
  link: `<path d="M9 17H7a5 5 0 0 1 0-10h2"/><path d="M15 7h2a5 5 0 0 1 0 10h-2"/><line x1="8" y1="12" x2="16" y2="12"/>`,
  key: `<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/>`,
  wrench: `<path d="M14.7 6.3a4 4 0 1 0-5.4 5.4L2 19l3 3 7.3-7.3a4 4 0 0 0 5.4-5.4l-2.85 2.85-2.15-.7-.7-2.15Z"/>`,
  clock: `<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16.5 14.5"/>`,
  archive: `<rect x="2" y="3" width="20" height="5" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><line x1="10" y1="13" x2="14" y2="13"/>`,
  send: `<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>`,
  ban: `<circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>`,
  bot: `<rect x="3" y="8" width="18" height="12" rx="2"/><circle cx="8.5" cy="14" r="1.5" fill="currentColor" stroke="none"/><circle cx="15.5" cy="14" r="1.5" fill="currentColor" stroke="none"/><path d="M12 8V4"/><circle cx="12" cy="3" r="1" fill="currentColor" stroke="none"/>`,
  "book-open": `<path d="M2 4h7a2 2 0 0 1 2 2v14a1.5 1.5 0 0 0-1.5-1.5H2Z"/><path d="M22 4h-7a2 2 0 0 0-2 2v14a1.5 1.5 0 0 1 1.5-1.5H22Z"/>`,
  "layout-dashboard": `<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>`,
  columns: `<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/>`,
  "shield-check": `<path d="M12 2 3 6v6c0 5.5 3.8 9.7 9 11 5.2-1.3 9-5.5 9-11V6Z"/><path d="m9 12 2 2 4-4" stroke-width="1.8"/>`,
  users: `<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>`,
  palette: `<circle cx="13.5" cy="6.5" r="1.5" fill="currentColor" stroke="none"/><circle cx="17.5" cy="10.5" r="1.5" fill="currentColor" stroke="none"/><circle cx="8.5" cy="7.5" r="1.5" fill="currentColor" stroke="none"/><circle cx="6.5" cy="12.5" r="1.5" fill="currentColor" stroke="none"/><path d="M12 2a10 10 0 0 0 0 20c1.1 0 2-1 2-2 0-.5-.2-1-.5-1.3-.3-.4-.5-.8-.5-1.3 0-1 .9-2 2-2h2.3A4.7 4.7 0 0 0 22 10.7 9 9 0 0 0 12 2Z"/>`,
  "log-out": `<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>`,
  "chevrons-left": `<polyline points="11 17 6 12 11 7"/><polyline points="18 17 13 12 18 7"/>`,
  "chevrons-right": `<polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/>`,
};

/* mapa emoji → ícone de linha, restrito a elementos de interface fixos
   (nav lateral usa NAV_ICONS, abaixo). Nunca inclui emojis de toast/texto livre. */
const EMOJI_ICONS = {
  "🌞": svgIcon(ICON_PATHS.sun),
  "🌙": svgIcon(ICON_PATHS.moon),
  "◧": svgIcon(ICON_PATHS["panel-left"]),
  "▮": svgIcon(ICON_PATHS["panel-compact"]),
  "⬒": svgIcon(ICON_PATHS["panel-top"]),
  "▶": svgIcon(ICON_PATHS.play),
  "✏️": svgIcon(ICON_PATHS.edit),
  "✕": svgIcon(ICON_PATHS.x),
  "⬆": svgIcon(ICON_PATHS.upload),
  "⚙️": svgIcon(ICON_PATHS.settings),
  "🌐": svgIcon(ICON_PATHS.globe),
  "🎲": svgIcon(ICON_PATHS.dice),
  "🏷️": svgIcon(ICON_PATHS.tag),
  "👁️": svgIcon(ICON_PATHS.eye),
  "💾": svgIcon(ICON_PATHS.save),
  "📋": svgIcon(ICON_PATHS["clipboard-list"]),
  "📜": svgIcon(ICON_PATHS["file-text"]),
  "📝": svgIcon(ICON_PATHS["file-edit"]),
  "📡": svgIcon(ICON_PATHS.radio),
  "📥": svgIcon(ICON_PATHS["file-down"]),
  "📩": svgIcon(ICON_PATHS.mail),
  "🔄": svgIcon(ICON_PATHS["refresh-cw"]),
  "🔍": svgIcon(ICON_PATHS.search),
  "🔒": svgIcon(ICON_PATHS.lock),
  "🔗": svgIcon(ICON_PATHS.link),
  "🔧": svgIcon(ICON_PATHS.wrench),
  "🕘": svgIcon(ICON_PATHS.clock),
  "🕵️": svgIcon(ICON_PATHS["search-check"]),
  "🗄️": svgIcon(ICON_PATHS.archive),
  "🚀": svgIcon(ICON_PATHS.send),
  "🚫": svgIcon(ICON_PATHS.ban),
  "🤖": svgIcon(ICON_PATHS.bot),
  "📖": svgIcon(ICON_PATHS["book-open"]),
  "☀️": svgIcon(ICON_PATHS.sun),
  "🚪": svgIcon(ICON_PATHS["log-out"]),
  "⇤": svgIcon(ICON_PATHS["chevrons-left"]),
  "⇥": svgIcon(ICON_PATHS["chevrons-right"]),
};

/* mapa data-view → ícone de linha, para os itens de #nav (aplicado por applyAccent,
   não por applyIconSkin — estrutura fixa e conhecida, sem heurística de texto) */
const NAV_ICONS = {
  dashboard: svgIcon(ICON_PATHS["layout-dashboard"]),
  monitor: svgIcon(ICON_PATHS.radio),
  geracao: svgIcon(ICON_PATHS["clipboard-list"]),
  instalacao: svgIcon(ICON_PATHS.wrench),
  revogacao: svgIcon(ICON_PATHS.ban),
  historico: svgIcon(ICON_PATHS.archive),
  kanban: svgIcon(ICON_PATHS.columns),
  csr: svgIcon(ICON_PATHS["file-edit"]),
  hsm: svgIcon(ICON_PATHS["shield-check"]),
  decoder: svgIcon(ICON_PATHS.search),
  certs: svgIcon(ICON_PATHS["file-text"]),
  validate: svgIcon(ICON_PATHS.link),
  passwords: svgIcon(ICON_PATHS.key),
  docs: svgIcon(ICON_PATHS["book-open"]),
  users: svgIcon(ICON_PATHS.users),
  auditoria: svgIcon(ICON_PATHS["search-check"]),
  appearance: svgIcon(ICON_PATHS.palette),
  settings: svgIcon(ICON_PATHS.settings),
};

/* seletor fixo de elementos elegíveis à troca de ícone — nunca inclui .toast,
   .user-name, nem células de tabela de dados (ver contracts/caixa-icon-skin.md) */
const ICON_SKIN_SELECTORS =
  ".btn, .badge, .view-title, .tab-btn, .rtab-btn, .subtab-btn, .opt-icon, .wizard-step, .stat-label";

/**
 * Troca, dentro de `root`, o emoji líder do primeiro nó de texto de cada
 * elemento elegível por seu ícone de linha correspondente — só quando o
 * Modo CAIXA está ativo. Nunca varre o documento inteiro, nunca toca
 * texto livre/dinâmico fora do seletor fixo.
 */
function applyIconSkin(root) {
  if (!root || document.documentElement.dataset.accent !== "caixa") return;
  root.querySelectorAll(ICON_SKIN_SELECTORS).forEach(el => {
    const node = [...el.childNodes].find(n => n.nodeType === 3 && n.textContent.trim());
    if (!node) return;
    const text = node.textContent;
    const emoji = Object.keys(EMOJI_ICONS).find(e => text.trimStart().startsWith(e));
    if (!emoji) return;
    node.textContent = text.replace(emoji, "");
    el.insertAdjacentHTML("afterbegin", EMOJI_ICONS[emoji]);
  });
}
