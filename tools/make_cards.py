#!/usr/bin/env python3
"""레포 카드 SVG 를 그린다.

GitHub 은 마크다운 안에서 CSS 를 걷어내지만 SVG 파일 안에서는 CSS 도 애니메이션도
동작한다. 그래서 카드를 통째로 SVG 로 그리고 <img> 로 건다.

글자는 path 로 굽는다 (textpath 참고) — 보는 사람 컴퓨터에 도트 폰트가 없어도
같은 모양으로 나온다.

폭 기준은 415 = (846 - 16) / 2. 846 은 프로필 리드미가 실제로 차지하는 폭으로,
2열로 놓았을 때 축소 없이 1:1 로 떨어지게 잡은 값이다. 축소되면 도트가 픽셀
격자에서 어긋나 뭉개진다.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import textpath as T

ROOT = pathlib.Path(__file__).parent.parent
ICONS = ROOT / "assets" / "icons"
OUT = ROOT / "assets" / "cards"

W, H = 415, 132
PAD = 18

# GitHub 언어 색
LANG_COLOR = {
    "Rust": "#dea584", "Python": "#3572A5", "Dart": "#00B4AB",
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Shell": "#89e051",
    "Go": "#00ADD8", "C#": "#178600", "HTML": "#e34c26", "CSS": "#563d7c",
}

STYLE = """
  .bg{fill:#ffffff;stroke:#d0d7de}
  .name{fill:#0969da} .desc{fill:#656d76} .meta{fill:#656d76} .ico{fill:#1f2328}
  @media (prefers-color-scheme: dark){
    .bg{fill:#0d1117;stroke:#30363d}
    .name{fill:#4493f8} .desc{fill:#8b949e} .meta{fill:#8b949e} .ico{fill:#e6edf3}
  }
  .beat{animation:b 4s ease-in-out infinite}
  @keyframes b{0%,100%{opacity:.25}50%{opacity:.9}}
"""


def icon_path(name):
    """픽셀 아이콘에서 path 데이터만 꺼낸다."""
    svg = (ICONS / f"{name}-dark.svg").read_text()
    m = re.search(r'd="([^"]+)"', svg)
    if not m:
        raise ValueError(f"{name}: path 없음")
    return m.group(1)


def wrap(text, size, max_w, weight="regular", limit=2):
    """폭에 맞춰 줄바꿈. 마지막 줄이 넘치면 말줄임."""
    if not text:
        return []
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if T.measure(trial, size, weight) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) == limit:
                break
    if cur and len(lines) < limit:
        lines.append(cur)
    if len(lines) == limit and len(" ".join(lines)) < len(text):
        while lines[-1] and T.measure(lines[-1] + "...", size, weight) > max_w:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "..."
    return lines


def card(repo):
    accent = LANG_COLOR.get(repo.get("lang"), "#8b949e")
    ip = icon_path(repo["icon"])
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
        f'height="{H}" role="img" aria-label="{repo["name"]}">',
        f"<style>{STYLE}</style>",
        f'<rect class="bg" x=".5" y=".5" width="{W-1}" height="{H-1}" rx="8" stroke-width="1"/>',
        # 왼쪽 액센트 띠 — 언어 색
        f'<rect x="0" y="8" width="3" height="{H-16}" rx="1.5" fill="{accent}"/>',
        f'<g transform="translate({PAD},{PAD+2}) scale(0.92)"><path class="ico" d="{ip}"/></g>',
        T.text(repo["name"], PAD + 30, PAD + 17, 16, cls="name"),
    ]
    for i, line in enumerate(wrap(repo.get("desc", ""), 11, W - PAD * 2 - 6, "regular")):
        s.append(T.text(line, PAD, 62 + i * 17, 11, cls="desc", weight="regular"))

    # 하단 메타 — 언어 점 + 언어명 + 별
    y = H - PAD - 2
    if repo.get("lang"):
        s.append(f'<circle cx="{PAD+5}" cy="{y-4}" r="5" fill="{accent}"/>')
        s.append(T.text(repo["lang"], PAD + 16, y, 11, cls="meta", weight="regular"))
        x = PAD + 22 + T.measure(repo["lang"], 11, "regular")
    else:
        x = PAD
    if repo.get("stars"):
        star = ("M8 1l2 4.5 4.9.4-3.7 3.2 1.1 4.8L8 11.4 3.7 13.9l1.1-4.8"
                "L1.1 5.9l4.9-.4z")
        s.append(f'<g transform="translate({x},{y-13}) scale(0.72)">'
                 f'<path fill="{accent}" d="{star}"/></g>')
        s.append(T.text(str(repo["stars"]), x + 15, y, 11, cls="meta", weight="regular"))

    s.append(f'<rect class="beat" x="{W-PAD-4}" y="{PAD-6}" width="6" height="6" fill="{accent}"/>')
    s.append("</svg>")
    return "\n".join(s)


def main():
    repos = json.loads((pathlib.Path(__file__).parent / "cards.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    for r in repos:
        p = OUT / f"{r['name']}.svg"
        p.write_text(card(r))
        print(f"  {p.relative_to(ROOT)}  {p.stat().st_size:>6}B")
    print(f"\n{len(repos)}장 · 카드 {W}x{H} · 2열 기준 폭 {W*2+16}px")


if __name__ == "__main__":
    main()
