// 방문자 수를 캐릭터 칸으로 그린다.
//
// 자릿수 하나가 캐릭터 한 명이다 (moe-counter 방식). 그림은 sprites.json 에
// base64 로 구워 두고 여기서는 문자열만 조립한다 — 서버가 요청마다 부르므로
// 이미지 처리도 폰트 파싱도 하지 않는다.
//
// 그림을 data URI 로 박는 이유는 GitHub 때문이다. SVG 를 <img> 로 걸면 바깥
// 파일 참조가 막히지만 같은 문서 안의 data URI 는 그대로 그려진다.
//
// 한 칸은 동작 한 벌(4~6프레임)이 도는 애니메이션이다. 프레임은 가로 띠 한 장에
// 이어 붙여 두고 창문을 고정한 채 띠를 옆으로 민다. 같은 자릿수가 두 번 나와도
// 그림은 <defs> 에 한 번만 박고 <use> 로 부른다 — 안 그러면 base64 가 통째로
// 두 번 들어간다.
//
// 동작이 작은 칸은 위아래로 띄운다(sprites.json 의 bob). 생성기가 실루엣으로
// 재 둔 값이고, 팔다리가 거의 안 움직이는 동작은 프레임이 넘어가도 멈춘 것처럼
// 보이기 때문이다. 띄우는 것도 정수 px 다 — 반 픽셀로 흐르면 도트가 번진다.

import sprites from "./sprites.json" with { type: "json" };

const PAL = {
  light: { sky0: "#e8f4fb", sky1: "#c8e6f7", card: "#ffffff", edge: "#bcdcef",
           ground: "#b8dcf0", num: "#1479c9", lbl: "#5d7f95", cloud: "#ffffff" },
  dark: { sky0: "#14202c", sky1: "#1d3a52", card: "#0f1b26", edge: "#2b4257",
          ground: "#2a4a63", num: "#58b6f8", lbl: "#8badc4", cloud: "#243849" },
};

const CELL = 76;          // 칸 폭 — 제일 넓은 동작(스파키 도발 67px)이 여유 있게 들어간다
const GAP = 4;
const PAD = 10;
const TOP = 6;            // 카드 위변과 제일 큰 캐릭터 머리 사이
const GROUND = 7;         // 발밑 바닥 띠 두께
const DOT = 3;            // 자릿수 도트 한 칸
const NUM_BOX = 5 * DOT + 5;
const LBL = 9;
const H_CHAR = sprites.h;
const CELL_H = TOP + H_CHAR + GROUND + NUM_BOX;

// 자릿수는 3x5 도트로 직접 그린다. Pixelify Sans 의 5 는 윗변이 말려 8·S 와
// 안 갈린다 — 굵기를 바꿔도 같아서 글자 대신 도트를 찍는다.
const DIGITS = [
  "111101101101111", "010110010010111", "111001111100111", "111001111001111",
  "101101111001001", "111100111001111", "111100111101111", "111001010010010",
  "111101111101111", "111101111001111",
];

function digit(ch, x, y) {
  const bits = DIGITS[Number(ch)];
  const out = [];
  for (let r = 0; r < 5; r++) {
    let c = 0;
    while (c < 3) {
      if (bits[r * 3 + c] !== "1") { c++; continue; }
      let n = 1;                              // 가로로 이어진 칸은 한 사각형으로
      while (c + n < 3 && bits[r * 3 + c + n] === "1") n++;
      out.push(`<rect x="${x + c * DOT}" y="${y + r * DOT}" width="${n * DOT}" height="${DOT}"/>`);
      c += n;
    }
  }
  return out.join("");
}

/**
 * @param {number} count 방문자 수
 * @param {string} label 아래 붙일 말 (없으면 생략)
 */
export function render(count, label = "visitors") {
  const s = String(Math.max(0, Math.floor(count)));
  const n = s.length;
  const W = PAD * 2 + n * CELL + (n - 1) * GAP;
  const H = PAD * 2 + CELL_H + (label ? LBL + 5 : 0);

  const css = [];
  for (const [mode, p] of Object.entries(PAL)) {
    const open = mode === "light" ? "" : "@media (prefers-color-scheme:dark){";
    const end = mode === "light" ? "" : "}";
    css.push(
      `${open}.sky0{stop-color:${p.sky0}}.sky1{stop-color:${p.sky1}}` +
        `.card{fill:${p.card};stroke:${p.edge}}.gnd{fill:${p.ground}}` +
        `.num{fill:${p.num}}.lbl{fill:${p.lbl}}.cloud{fill:${p.cloud}}${end}`
    );
  }

  // 쓰인 자릿수만 <defs> 에 굽는다. 띠를 한 칸씩 미는 것이 곧 프레임 넘김이라
  // steps(n) 으로 끊는다 — 중간값이 보이면 두 프레임이 겹쳐 흐려진다.
  const used = [...new Set(s)].map(Number).sort();
  const defs = [];
  for (const d of used) {
    const sl = sprites.slots[d];
    defs.push(
      `<image id="c${d}" width="${sl.w * sl.n}" height="${sl.h}" ` +
        `href="data:image/png;base64,${sl.png}"/>`
    );
    css.push(`@keyframes k${d}{from{transform:translateX(0)}to{transform:translateX(${-sl.w * sl.n}px)}}`);
    css.push(`.a${d}{animation:k${d} ${((sl.n * sl.dur) / 1000).toFixed(2)}s steps(${sl.n}) infinite}`);
  }
  // 쓰인 부유 세기만 굽는다. 오르내리는 중간값이 보이면 도트가 흐려지므로
  // steps(1) 로 칸마다 딱 끊는다 — 키프레임이 여럿이라 구간마다 값이 바뀐다.
  const bobs = [...new Set(used.map((d) => sprites.slots[d].bob || 0))].filter(Boolean);
  for (const b of bobs) {
    const seq = b === 1 ? [0, -1] : [0, -1, -2, -1];
    const kf = seq
      .map((v, i) => `${((i / seq.length) * 100).toFixed(0)}%{transform:translateY(${v}px)}`)
      .join("");
    css.push(`@keyframes b${b}{${kf}}`);
    css.push(`.b${b}{animation:b${b} ${b === 1 ? "2.2" : "2.8"}s steps(1) infinite}`);
  }
  css.push(`.drift{animation:d 22s linear infinite}`);
  css.push(`@keyframes d{from{transform:translateX(${-Math.round(W * 0.5)}px)}to{transform:translateX(${W}px)}}`);
  css.push(`@media (prefers-reduced-motion:reduce){[class^=a],[class^=b],.drift{animation:none}}`);
  css.push(`image{image-rendering:pixelated}`);

  const parts = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" ` +
      `height="${H}" role="img" aria-label="${count} ${label}">`,
    `<style>${css.join("")}</style>`,
    `<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">` +
      `<stop offset="0" class="sky0"/><stop offset="1" class="sky1"/></linearGradient>` +
      `<clipPath id="cc"><rect x="0" y="0" width="${W}" height="${H}" rx="8"/></clipPath>` +
      defs.join("") + `</defs>`,
    `<rect width="${W}" height="${H}" rx="8" fill="url(#sky)"/>`,
    `<g clip-path="url(#cc)" opacity=".55"><g class="drift">`,
  ];
  // 구름 — 자리는 수에서 뽑아 같은 수면 늘 같은 그림이 나오게 한다
  for (let i = 0; i < 4; i++) {
    const cx = i * Math.round(W * 0.42);
    const cy = 8 + ((count * 7 + i * 23) % Math.max(1, H - 46));
    parts.push(
      `<g class="cloud" transform="translate(${cx},${cy})">` +
        `<rect x="0" y="5" width="30" height="7" rx="3.5"/>` +
        `<rect x="8" y="0" width="16" height="7" rx="3.5"/></g>`
    );
  }
  parts.push(`</g></g>`);

  for (let i = 0; i < n; i++) {
    const d = Number(s[i]);
    const sl = sprites.slots[d];
    const x = PAD + i * (CELL + GAP);
    const y = PAD;
    parts.push(
      `<rect class="card" x="${x + 0.5}" y="${y + 0.5}" width="${CELL - 1}" ` +
        `height="${CELL_H - 1}" rx="6" stroke-width="1" fill-opacity=".62"/>`
    );
    // 발밑 바닥 — 캐릭터가 공중에 뜨지 않게 딛는 자리를 준다
    const gy = y + TOP + H_CHAR + GROUND - 4;
    parts.push(`<rect class="gnd" x="${x + 5}" y="${gy}" width="${CELL - 10}" height="3" rx="1.5"/>`);

    // 키가 제각각이라 발을 바닥에 맞춘다. 위로 남는 자리는 그냥 여백이 된다.
    const cx = x + Math.round((CELL - sl.w) / 2);
    const cy = y + TOP + (H_CHAR - sl.h);
    const delay = ((i * 137) % 700) / 1000;   // 열이 한꺼번에 움직이면 기계처럼 보인다
    const cell =
      `<svg x="${cx}" y="${cy}" width="${sl.w}" height="${sl.h}" ` +
      `viewBox="0 0 ${sl.w} ${sl.h}">` +
      `<g class="a${d}" style="animation-delay:${delay}s"><use href="#c${d}"/></g></svg>`;
    const bob = sl.bob || 0;
    parts.push(
      bob
        ? `<g class="b${bob}" style="animation-delay:${(delay / 2).toFixed(3)}s">${cell}</g>`
        : cell
    );

    const nx = x + Math.round((CELL - 3 * DOT) / 2);
    parts.push(`<g class="num">${digit(s[i], nx, y + CELL_H - NUM_BOX + 1)}</g>`);
  }

  if (label) {
    parts.push(
      `<text class="lbl" x="${W - PAD}" y="${H - 5}" font-size="${LBL}" text-anchor="end" ` +
        `font-family="ui-monospace,SFMono-Regular,Menlo,monospace">${label}</text>`
    );
  }
  parts.push(`</svg>`);
  return parts.join("");
}
