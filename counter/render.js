// 방문자 수를 도트 숫자 SVG 로 그린다.
//
// 서버가 요청마다 호출하므로 의존성 없이 문자열만 조립한다.
// 글자는 digits.json 에 미리 구워 둔 path 를 쓴다 — 서버에서 폰트를 파싱하지 않는다.

import digits from "./digits.json" with { type: "json" };

const PAL = {
  light: { bg: "#e8f4fb", cell: "#ffffff", edge: "#bcdcef", num: "#1479c9", lbl: "#5d7f95" },
  dark: { bg: "#14202c", cell: "#0f1b26", edge: "#2b4257", num: "#58b6f8", lbl: "#8badc4" },
};

const CELL_W = 30, CELL_H = 42, GAP = 4, PAD = 8, SIZE = 22, LBL = 9;

function glyph(ch, x, y, size, cls) {
  const g = digits.glyphs[ch];
  if (!g) return { svg: "", w: 0 };
  const k = size / digits.upm;
  return {
    svg: `<g transform="translate(${x.toFixed(1)},${y.toFixed(1)}) scale(${k.toFixed(5)},${(-k).toFixed(5)})" class="${cls}"><path d="${g.d}"/></g>`,
    w: g.w * k,
  };
}

function textWidth(s, size) {
  let w = 0;
  for (const ch of s) w += (digits.glyphs[ch]?.w ?? 0) * (size / digits.upm);
  return w;
}

/**
 * @param {number} count 방문자 수
 * @param {string} label 아래 붙일 말 (없으면 생략)
 */
export function render(count, label = "visitors") {
  const s = String(Math.max(0, Math.floor(count)));
  const n = s.length;
  const W = PAD * 2 + n * CELL_W + (n - 1) * GAP;
  const H = PAD * 2 + CELL_H + (label ? LBL + 6 : 0);

  const css = [];
  for (const [mode, p] of Object.entries(PAL)) {
    const sel = mode === "light" ? "" : "@media (prefers-color-scheme: dark){";
    const end = mode === "light" ? "" : "}";
    css.push(
      `${sel}.bg{fill:${p.bg}}.cell{fill:${p.cell};stroke:${p.edge}}` +
        `.num{fill:${p.num}}.lbl{fill:${p.lbl}}.cloud{fill:${p.cell}}${end}`
    );
  }
  // 구름이 뒤로 천천히 흐른다 — 칸 안에서만 보이도록 잘라낸다
  css.push(`.drift{animation:d 14s linear infinite}`);
  css.push(`@keyframes d{from{transform:translateX(0)}to{transform:translateX(${W}px)}}`);
  css.push(`@media (prefers-reduced-motion:reduce){.drift{animation:none}}`);

  const parts = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${count} ${label}">`,
    `<style>${css.join("")}</style>`,
    `<defs><clipPath id="c"><rect x="0" y="0" width="${W}" height="${H}" rx="6"/></clipPath></defs>`,
    `<rect class="bg" width="${W}" height="${H}" rx="6"/>`,
    `<g clip-path="url(#c)" opacity=".5"><g class="drift">`,
  ];
  // 구름 — 위치를 숫자에서 뽑아 매번 같은 자리에 두되 수마다 조금씩 다르게
  for (let i = 0; i < 3; i++) {
    const cx = -W * 0.4 + i * W * 0.45;
    const cy = 6 + ((count + i * 7) % Math.max(1, H - 20));
    parts.push(
      `<g class="cloud" transform="translate(${cx.toFixed(0)},${cy.toFixed(0)})">` +
        `<rect x="0" y="4" width="26" height="6" rx="3"/><rect x="6" y="0" width="14" height="6" rx="3"/></g>`
    );
  }
  parts.push(`</g></g>`);

  for (let i = 0; i < n; i++) {
    const x = PAD + i * (CELL_W + GAP);
    parts.push(
      `<rect class="cell" x="${x + 0.5}" y="${PAD + 0.5}" width="${CELL_W - 1}" height="${CELL_H - 1}" rx="4" stroke-width="1"/>`
    );
    const gw = textWidth(s[i], SIZE);
    parts.push(glyph(s[i], x + (CELL_W - gw) / 2, PAD + CELL_H / 2 + SIZE * 0.36, SIZE, "num").svg);
  }

  if (label) {
    const lw = textWidth(label, LBL);
    // 라벨은 글자가 digits.json 에 없을 수 있어(영문) path 대신 text 로 둔다
    parts.push(
      `<text class="lbl" x="${W / 2}" y="${H - 5}" font-size="${LBL}" text-anchor="middle" ` +
        `font-family="ui-monospace,SFMono-Regular,Menlo,monospace">${label}</text>`
    );
    void lw;
  }
  parts.push(`</svg>`);
  return parts.join("");
}
