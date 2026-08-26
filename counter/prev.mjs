// 미리보기 — 서버 없이 SVG 를 뽑아 브라우저로 눈으로 본다.
// 라이트/다크는 파일을 두 벌 만들어 가른다. 브라우저 테마를 바꿔 가며
// 보면 한쪽만 확인하게 되고, prefers-color-scheme 는 iframe 마다 못 바꾼다.
import { render } from "./render.js";
import { writeFileSync, mkdirSync } from "node:fs";

const out = process.argv[2];
if (!out) { console.error("쓰는 법: node prev.mjs <출력폴더>"); process.exit(1); }
mkdirSync(out, { recursive: true });

const SETS = { a: 1234, b: 5678, c: 90, cmp: 5850 };

for (const [k, v] of Object.entries(SETS)) {
  const svg = render(v);
  // 다크 블록을 늘 켜진 것으로 바꾼다 — 조건을 지우면 라이트 값이 뒤에서 덮는다
  writeFileSync(`${out}/p-${k}-light.svg`, svg.replace("@media (prefers-color-scheme:dark){", "@media (zzz:dark){"));
  writeFileSync(`${out}/p-${k}-dark.svg`, svg.replace("@media (prefers-color-scheme:dark){", "@media all{"));
}
console.log(Object.keys(SETS).length * 2, "장 —", out);
