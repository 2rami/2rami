"""섹션 제목을 아이콘과 글자가 한 몸인 그림 한 장으로 굽는다.

마크다운 `###` 와 `<img>` 아이콘을 나란히 두면 둘이 서로 다른 상자에 앉는다.
글자는 GitHub 기본 서체로 렌더되어 도트 서체와 어긋나고, 아이콘은 float 로
빠져 글자와 세로가 안 맞는다(실측: 24 를 지정해도 44x24 로 나온다). 한 장에
같이 그리면 두 문제가 같이 없어진다 — 좌표가 하나의 격자 안에 있으니까.
"""
import pathlib
import re

import textpath as T

ROOT = pathlib.Path(__file__).parent.parent
ICON = ROOT / "assets" / "icons"
OUT = ROOT / "assets" / "heads"

H = 30
ISZ = 20                      # 아이콘 변 — 글자보다 살짝 커야 머리글로 읽힌다
GAP = 9
FS = 19

STYLE = (".ic{fill:#2b4257}.tx{fill:#1479c9}"
         "@media (prefers-color-scheme:dark){.ic{fill:#cfe6f5}.tx{fill:#58b6f8}}")

# 아이콘마다 결이 다르다. 세로로 통통 튀는 것과 좌우로 흔들리는 것을 섞으면
# 네 제목이 한꺼번에 같은 박자로 뛰지 않는다.
MOVES = {
    "bob":  ("0%,50%{transform:translateY(0)}50.01%,100%{transform:translateY(1px)}", "1.4s"),
    "sway": ("0%,50%{transform:translateX(0)}50.01%,100%{transform:translateX(1px)}", "1.8s"),
    "tick": ("0%,25%{transform:translateY(0)}25.01%,50%{transform:translateY(-1px)}"
             "50.01%,100%{transform:translateY(0)}", "2.2s"),
    "pulse": ("0%,60%{opacity:1}60.01%,100%{opacity:.45}", "1.6s"),
}

HEADS = [
    ("build",   "layout",             "What I Build", "bob"),
    ("tech",    "code",               "Tech Stack",   "sway"),
    ("contrib", "git-branch",         "Contribution", "tick"),
    ("connect", "message-processing", "Connect",      "pulse"),
]


def shapes(slug):
    """원본 아이콘에서 도형만 꺼낸다. 색은 여기서 다시 입히므로 fill 은 버린다."""
    s = (ICON / f"{slug}-dark.svg").read_text()
    body = re.sub(r'\s*fill="[^"]*"', "", s[s.index(">") + 1:s.rindex("</svg>")])
    return body.strip()


def head(slug, ico, label, move):
    kf, dur = MOVES[move]
    tw = T.measure(label, FS, "bold")
    tx = ISZ + GAP
    w = round(tx + tw)
    k = ISZ / 24
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {H}" '
            f'width="{w}" height="{H}" role="img" aria-label="{label}">'
            f'<style>{STYLE}@keyframes m{{{kf}}}'
            f'.mv{{animation:m {dur} steps(1,end) infinite}}'
            f'@media (prefers-reduced-motion:reduce){{.mv{{animation:none}}}}</style>'
            f'<g class="ic mv" transform="translate(0,{(H - ISZ) / 2:.1f}) scale({k:.4f})">'
            f'{shapes(ico)}</g>'
            + T.text(label, tx, H / 2 + FS * .36, FS, weight="bold", cls="tx")
            + "</svg>"), w


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, ico, label, move in HEADS:
        svg, w = head(name, ico, label, move)
        (OUT / f"{name}.svg").write_text(svg)
        print(f"  {name}.svg  {w}x{H}  «{label}»")


if __name__ == "__main__":
    main()
