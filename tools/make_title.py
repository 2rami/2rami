"""히어로 왼쪽 — 이름과 소개를 한 장에 담는다.

전에는 이 자리가 셋으로 쪼개져 있었다. 이름은 남의 타이핑 서비스가 그린 그림,
소개는 마크다운 <pre>, 그 둘의 서체가 서로 달랐다. 이름 그림이 389px 에서
끊겨 터미널이 시작하는 589px 까지 200px 가 비었다(2026-08-27 지적: "끝단이나
그리드좀 맞춰봐"). 한 장으로 합치면 폭도 서체도 한 번에 맞고, 바깥 서비스가
죽어도 안 깨진다.

585 는 오른쪽 터미널(257)과 마크다운이 그림 사이에 넣는 4px 를 빼고 남는 폭이다.
높이도 터미널과 같은 188 로 맞춰 두 덩이의 아랫변이 한 줄에 선다.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import textpath as T

OUT = HERE.parent / "assets" / "title.svg"

W, H = 585, 188
NAME = "2rami"
NFS = 72                      # 이름 — 소개글의 네 배라야 머리로 읽힌다
NY = 56
BFS = 18
LINES = [                     # None 은 문단 사이 빈 줄
    "Designer + AI-Assisted Developer",
    "South Korea",
    None,
    "Building a terminal, discord bots, slack agents and games",
    "Design student who codes with Claude",
]
LH = 24
BY = 92

STYLE = (".nm{fill:#1479c9}.ds{fill:#5d7f95}.cur{fill:#1479c9}"
         "@media (prefers-color-scheme:dark){.nm{fill:#58b6f8}"
         ".ds{fill:#8badc4}.cur{fill:#58b6f8}}")

# 글자가 하나씩 찍히고 커서가 깜빡인다. 한 번 찍히면 그대로 둔다 — 프로필을
# 볼 때마다 이름이 다시 지워졌다 써지면 읽는 사람이 기다리게 된다.
STEP = 0.16


def main():
    parts, x = [], 0.0
    for i, ch in enumerate(NAME):
        g = T.text(ch, x, NY, NFS, weight="bold", cls="nm")
        parts.append(f'<g style="opacity:0;animation:tp .01s {STEP * i + .2:.2f}s '
                     f'forwards">{g}</g>')
        x += T.measure(ch, NFS, "bold")

    cur_at = STEP * len(NAME) + .2
    parts.append(f'<rect class="cur" x="{x + 6:.0f}" y="{NY - NFS * .72:.0f}" '
                 f'width="{NFS * .46:.0f}" height="{NFS * .78:.0f}" '
                 f'style="animation:bl 1.06s {cur_at:.2f}s step-end infinite"/>')

    y = BY
    for s in LINES:
        if s is None:
            y += LH * .55
            continue
        parts.append(T.text(s, 0, y, BFS, weight="bold", cls="ds"))
        y += LH

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}" role="img" '
           f'aria-label="{NAME} — Designer and AI-Assisted Developer">'
           f'<style>{STYLE}'
           f'@keyframes tp{{to{{opacity:1}}}}'
           f'@keyframes bl{{0%,50%{{opacity:1}}50.01%,100%{{opacity:0}}}}'
           f'@media (prefers-reduced-motion:reduce){{'
           f'[style*=animation]{{animation:none!important;opacity:1!important}}}}'
           f'</style>' + "".join(parts) + "</svg>")
    OUT.write_text(svg)
    print(f"  title.svg  {W}x{H}  이름폭 {x:.0f} · 아래끝 {y - LH:.0f}")


if __name__ == "__main__":
    main()
