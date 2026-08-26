// 방문자 카운터 — 수를 세는 곳과 그리는 곳을 나눈다.
//
// 세는 것은 abacus(무가입 공개 카운터)에 맡기고 여기서는 그림만 그린다.
// 직접 저장하려면 DB 가 붙고 계정이 하나 더 늘어나는데, 프로필 조회수는
// 틀려도 잃을 것이 없는 값이라 그만한 값을 안 한다.
//
// GitHub 은 README 의 이미지를 제 프록시(camo)로 받아 캐시한다. 캐시가
// 걸리면 수가 안 늘어 보이므로 캐시를 끄고 내려보낸다 — 그래도 camo 가
// 얼마간 붙들고 있어서 실제 갱신은 몇 분 단위다.
import { render } from "../counter/render.js";

const API = "https://abacus.jasoncameron.dev";

export const config = { runtime: "nodejs" };

export default async function handler(req, res) {
  const url = new URL(req.url, `https://${req.headers.host}`);
  const ns = (url.searchParams.get("ns") || "2rami").replace(/[^\w-]/g, "").slice(0, 40);
  const key = (url.searchParams.get("key") || "profile").replace(/[^\w-]/g, "").slice(0, 40);
  const label = (url.searchParams.get("label") ?? "visitors").replace(/[^\w \-.]/g, "").slice(0, 24);
  // 세지 않고 지금 값만 볼 때 (미리보기·디버그)
  const peek = url.searchParams.get("peek") === "1";

  let count = 0;
  try {
    const r = await fetch(`${API}/${peek ? "get" : "hit"}/${ns}/${key}`, {
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(4000),
    });
    if (r.ok) count = Number((await r.json()).value) || 0;
  } catch {
    // 카운터가 죽어도 그림은 나가야 한다 — 0 으로 그린다
  }

  res.setHeader("content-type", "image/svg+xml; charset=utf-8");
  res.setHeader("cache-control", "no-cache, no-store, must-revalidate, max-age=0");
  res.status(200).send(render(count, label));
}
