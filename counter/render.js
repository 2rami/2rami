// 방문자 수를 캐릭터 칸으로 그린다.
//
// 자릿수 하나가 캐릭터 한 명이다 (moe-counter 방식). 그림은 sprites.json 에
// base64 로 구워 두고 여기서는 문자열만 조립한다 — 서버가 요청마다 부르므로
// 이미지 처리도 폰트 파싱도 하지 않는다.
//
// 그림을 data URI 로 박는 이유는 GitHub 때문이다. SVG 를 <img> 로 걸면 바깥
// 파일 참조가 막히지만 같은 문서 안의 data URI 는 그대로 그려진다.
//
// 자릿수는 캐릭터가 **손에 든 카드** 위에 적힌다 (moe-counter 의 original 테마를
// 패러디한 것 — 거기서도 캐릭터가 번호판을 몸 앞에 들고 있다). 카드는 벡터로
// 그려 캐릭터 위에 얹는다. 그림 자체는 포즈가 고정돼 있어 손 모양을 바꿀 수
// 없으므로, 카드 양옆에 그 캐릭터의 살색으로 손을 하나씩 붙여 쥔 것처럼 보이게
// 한다. 살색은 생성기가 얼굴에서 뽑아 sprites.json 에 적어 둔다.
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
  light: { sky0: "#e8f4fb", sky1: "#c8e6f7", ground: "#b8dcf0", lbl: "#5d7f95", cloud: "#ffffff", cop: .8,
           plate: "#ffffff", pedge: "#7fa9c2", pnum: "#14303f" },
  dark: { sky0: "#14202c", sky1: "#1d3a52", ground: "#2a4a63", lbl: "#8badc4", cloud: "#243849", cop: .55,
          plate: "#e4eef5", pedge: "#4d7086", pnum: "#12293a" },
};

const CELL = 70;          // 칸 폭 — 제일 넓은 동작(스파키 도발 67px)이 들어간다
const GAP = 2;
const PAD = 10;
const TOP = 6;            // 카드 위변과 제일 큰 캐릭터 머리 사이
const GROUND = 7;         // 발밑 바닥 띠 두께
const BOT = 5;            // 바닥 띠와 칸 아래변 사이 — 없으면 발이 테두리에 닿는다
const PLATE_W = 34;       // 캐릭터가 든 카드
const PLATE_H = 28;
const PDOT = 3;           // 카드 위 숫자의 도트 한 칸
const DW = 5, DH = 7;     // 숫자 도트 격자
const LBL = 9;
const H_CHAR = sprites.h;
const CELL_H = TOP + H_CHAR + GROUND + BOT;

// 자릿수는 5x7 도트로 직접 그린다. Pixelify Sans 의 5 는 윗변이 말려 8·S 와
// 안 갈린다 — 굵기를 바꿔도 같아서 글자 대신 도트를 찍는다. 카드 위 숫자가
// 이제 칸의 주인공이라 3x5 로는 가늘어서 격자를 키웠다.
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
  const W = PAD * 2 + n * CELL + (n - 1) * GAP;
  const H = PAD * 2 + CELL_H + (label ? LBL + 5 : 0);

  const css = [];
  for (const [mode, p] of Object.entries(PAL)) {
    const open = mode === "light" ? "" : "@media (prefers-color-scheme:dark){";
    const end = mode === "light" ? "" : "}";
    css.push(
      `${open}.sky0{stop-color:${p.sky0}}.sky1{stop-color:${p.sky1}}` +
        `.gnd{fill:${p.ground}}` +
        `.lbl{fill:${p.lbl}}.plate{fill:${p.plate};stroke:${p.pedge}}` +
        `.pnum{fill:${p.pnum}}` +
        `.cloud{fill:${p.cloud};opacity:${p.cop}}${end}`
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

  for (let i = 0; i < n; i++) {
    const d = Number(s[i]);
    const sl = sprites.slots[d];
    const x = PAD + i * (CELL + GAP);
    const y = PAD;
    // 키가 제각각이라 발을 바닥에 맞춘다. 위로 남는 자리는 그냥 여백이 된다.
    const cx = x + Math.round((CELL - sl.w) / 2);
    const cy = y + TOP + (H_CHAR - sl.h);
    const delay = ((i * 137) % 700) / 1000;   // 열이 한꺼번에 움직이면 기계처럼 보인다
    const cell =
      `<svg x="${cx}" y="${cy}" width="${sl.w}" height="${sl.h}" ` +
      `viewBox="0 0 ${sl.w} ${sl.h}">` +
      `<g class="a${d}" style="animation-delay:${delay}s"><use href="#c${d}"/></g></svg>`;

    // 든 카드 — 몸통 앞. 손은 카드 밑으로 3px 들어가 있어 쥔 것처럼 보인다.
    const px = x + Math.round((CELL - PLATE_W) / 2);
    const py = cy + Math.round(sl.h * 0.56) - Math.round(PLATE_H / 2);
    const hy = py + Math.round(PLATE_H * 0.34);
    const skin = sl.skin || "#f4e6e1";
    const plate =
      `<rect x="${px + 1}" y="${py + 2}" width="${PLATE_W}" height="${PLATE_H}" rx="2" ` +
        `fill="#000" fill-opacity=".16"/>` +
      `<g fill="${skin}"><rect x="${px - 5}" y="${hy}" width="9" height="9" rx="2.5"/>` +
        `<rect x="${px + PLATE_W - 4}" y="${hy}" width="9" height="9" rx="2.5"/></g>` +
      `<rect class="plate" x="${px + 0.5}" y="${py + 0.5}" width="${PLATE_W - 1}" ` +
        `height="${PLATE_H - 1}" rx="2" stroke-width="1"/>` +
      `<g class="pnum">${digit(s[i], px + Math.round((PLATE_W - DW * PDOT) / 2),
        py + Math.round((PLATE_H - DH * PDOT) / 2))}</g>`;

    const bob = sl.bob || 0;
    const body = cell + plate;    // 카드는 캐릭터가 든 것이라 같이 떠야 한다
    parts.push(
      bob
        ? `<g class="b${bob}" style="animation-delay:${(delay / 2).toFixed(3)}s">${body}</g>`
        : body
    );
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
