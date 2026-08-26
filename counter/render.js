// 방문자 수를 캐릭터 칸으로 그린다.
//
// 자릿수 하나가 캐릭터 한 명이다 (moe-counter 방식). 그림은 sprites.json 에
// base64 로 구워 두고 여기서는 문자열만 조립한다 — 서버가 요청마다 부르므로
// 이미지 처리도 폰트 파싱도 하지 않는다.
//
// 그림을 data URI 로 박는 이유는 GitHub 때문이다. SVG 를 <img> 로 걸면 바깥
// 파일 참조가 막히지만 같은 문서 안의 data URI 는 그대로 그려진다.
//
// 자릿수는 캐릭터가 손에 든 카드 위에 적힌다. 카드는 **그림에 같이 그려져
// 있다** — 전에는 벡터로 얹고 양옆에 살색 네모를 붙여 손인 척했는데, 캐릭터가
// 실제로 카드를 쥔 그림을 새로 뽑았으므로 그럴 필요가 없어졌다. 카드가 어디
// 있는지는 생성기가 재서 sprites.json 에 적어 둔다.
//
// 칸 폭은 캐릭터마다 다르다. 제일 넓은 캐릭터에 맞춰 고정하면 좁은 캐릭터
// 양옆이 휑하게 비어 한 명씩 상자에 갇힌 것처럼 보인다. 원본도 캐릭터를 제
// 폭 그대로 붙여 세운다.
//
// 한 칸은 세 프레임이다(기본·눈감기·미소). 프레임은 가로 띠 한 장에 이어 붙여
// 두고 창문을 고정한 채 띠를 옆으로 민다. 같은 자릿수가 두 번 나와도 그림은
// <defs> 에 한 번만 박고 <use> 로 부른다 — 안 그러면 base64 가 통째로 두 번
// 들어간다.
//
// 프레임 간격은 고르지 않다. 눈은 오래 뜨고 있다가 잠깐 감는 것이라 steps(3)
// 으로 균등하게 돌리면 계속 껌뻑이는 인형이 된다. 그래서 키프레임 위치를
// 직접 잡고 step-end 로 끊는다 — 구간마다 값이 그대로 유지된다.

import sprites from "./sprites.json" with { type: "json" };

const PAL = {
  light: { sky0: "#e8f4fb", sky1: "#c8e6f7", ground: "#b8dcf0", lbl: "#5d7f95",
           cloud: "#ffffff", cop: .8 },
  dark: { sky0: "#14202c", sky1: "#1d3a52", ground: "#2a4a63", lbl: "#8badc4",
          cloud: "#243849", cop: .55 },
};

const GAP = 2;
const PAD = 8;
const TOP = 3;            // 캐릭터 머리와 칸 위변 사이
const GROUND = 6;         // 발밑 바닥 띠 두께
const BOT = 3;
const PDOT = 3;           // 카드 위 숫자의 도트 한 칸
const DW = 5, DH = 7;     // 숫자 도트 격자
const LBL = 9;
const INK = "#12293a";    // 카드는 그림에 흰색으로 박혀 있어 명암 모드와 무관하다
const H_CHAR = sprites.h;
const CELL_H = TOP + H_CHAR + GROUND + BOT;

// 프레임 순서와 머무는 시간(ms). 0 기본 · 1 눈감기 · 2 미소.
const SEQ = [0, 1, 0, 2];
const DUR = [900, 140, 900, 420];
const CYCLE = DUR.reduce((a, b) => a + b, 0);

// 자릿수는 5x7 도트로 직접 그린다. Pixelify Sans 의 5 는 윗변이 말려 8·S 와
// 안 갈린다 — 굵기를 바꿔도 같아서 글자 대신 도트를 찍는다.
const DIGITS = [
  "01110" + "10001" + "10011" + "10101" + "11001" + "10001" + "01110",
  "00100" + "01100" + "00100" + "00100" + "00100" + "00100" + "01110",
  "01110" + "10001" + "00001" + "00010" + "00100" + "01000" + "11111",
  "11111" + "00010" + "00100" + "00010" + "00001" + "10001" + "01110",
  "00010" + "00110" + "01010" + "10010" + "11111" + "00010" + "00010",
  "11111" + "10000" + "11110" + "00001" + "00001" + "10001" + "01110",
  "00110" + "01000" + "10000" + "11110" + "10001" + "10001" + "01110",
  "11111" + "00001" + "00010" + "00100" + "01000" + "01000" + "01000",
  "01110" + "10001" + "10001" + "01110" + "10001" + "10001" + "01110",
  "01110" + "10001" + "10001" + "01111" + "00001" + "00010" + "01100",
];

function digit(ch, x, y) {
  const bits = DIGITS[Number(ch)];
  const out = [];
  for (let r = 0; r < DH; r++) {
    let c = 0;
    while (c < DW) {
      if (bits[r * DW + c] !== "1") { c++; continue; }
      let n = 1;                              // 가로로 이어진 칸은 한 사각형으로
      while (c + n < DW && bits[r * DW + c + n] === "1") n++;
      out.push(`<rect x="${x + c * PDOT}" y="${y + r * PDOT}" width="${n * PDOT}" height="${PDOT}"/>`);
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
  const cells = [...s].map((c) => sprites.slots[Number(c)]);
  const W = PAD * 2 + cells.reduce((a, sl) => a + sl.w, 0) + (n - 1) * GAP;
  const H = PAD * 2 + CELL_H + (label ? LBL + 5 : 0);

  const css = [];
  for (const [mode, p] of Object.entries(PAL)) {
    const open = mode === "light" ? "" : "@media (prefers-color-scheme:dark){";
    const end = mode === "light" ? "" : "}";
    css.push(
      `${open}.sky0{stop-color:${p.sky0}}.sky1{stop-color:${p.sky1}}` +
        `.gnd{fill:${p.ground}}.lbl{fill:${p.lbl}}` +
        `.cloud{fill:${p.cloud};opacity:${p.cop}}${end}`
    );
  }

  // 쓰인 자릿수만 <defs> 에 굽는다.
  const used = [...new Set(s)].map(Number).sort();
  const defs = [];
  for (const d of used) {
    const sl = sprites.slots[d];
    defs.push(
      `<image id="c${d}" width="${sl.w * sl.n}" height="${sl.h}" ` +
        `href="data:image/png;base64,${sl.png}"/>`
    );
    let t = 0;
    const kf = SEQ.map((f, i) => {
      const at = ((t / CYCLE) * 100).toFixed(2);
      t += DUR[i];
      return `${at}%{transform:translateX(${-f * sl.w}px)}`;
    }).join("");
    css.push(`@keyframes k${d}{${kf}}`);
    css.push(`.a${d}{animation:k${d} ${(CYCLE / 1000).toFixed(2)}s step-end infinite}`);
  }
  css.push(`.drift{animation:d 22s linear infinite}`);
  css.push(`@keyframes d{from{transform:translateX(${-Math.round(W * 0.5)}px)}to{transform:translateX(${W}px)}}`);
  css.push(`@media (prefers-reduced-motion:reduce){[class^=a],.drift{animation:none}}`);
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
    `<g clip-path="url(#cc)"><g class="drift">`,
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

  parts.push(
    `<rect class="gnd" x="${PAD}" y="${PAD + TOP + H_CHAR + GROUND - 4}" ` +
      `width="${W - PAD * 2}" height="3" rx="1.5"/>`
  );

  let x = PAD;
  for (let i = 0; i < n; i++) {
    const d = Number(s[i]);
    const sl = cells[i];
    const cy = PAD + TOP + (H_CHAR - sl.h);   // 키가 달라도 발은 바닥에 맞춘다
    // 열이 한꺼번에 깜빡이면 기계처럼 보인다. 음수로 밀어 첫 화면부터 어긋나게.
    const delay = -((i * 613) % CYCLE) / 1000;
    parts.push(
      `<svg x="${x}" y="${cy}" width="${sl.w}" height="${sl.h}" ` +
      `viewBox="0 0 ${sl.w} ${sl.h}">` +
      `<g class="a${d}" style="animation-delay:${delay.toFixed(3)}s"><use href="#c${d}"/></g></svg>`
    );

    // 숫자는 그림 속 카드 자리에 그대로 찍는다
    const [kx, ky, kw, kh] = sl.card;
    parts.push(
      `<g fill="${INK}">${digit(s[i],
        x + kx + Math.round((kw - DW * PDOT) / 2),
        cy + ky + Math.round((kh - DH * PDOT) / 2))}</g>`
    );
    x += sl.w + GAP;
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
