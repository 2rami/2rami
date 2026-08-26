#!/usr/bin/env python3
"""픽셀 아이콘에 도트 애니메이션을 입혀 다시 내보낸다.

원본(assets/icons)은 건드리지 않고 assets/icons-anim 으로 따로 쓴다.

움직임은 반드시 정수 픽셀 단위여야 한다. 0.5px 씩 부드럽게 움직이면 도트가
격자에서 벗어나 흐릿하게 번지고, 픽셀 아트로 보이지 않는다. 그래서 steps() 로
끊어 1px 씩 점프시킨다.

다크/라이트는 원본처럼 파일 두 벌(-dark, -light)로 유지한다. SVG 안에서
prefers-color-scheme 을 쓸 수도 있지만, README 쪽 <picture> 구조를 그대로
두는 편이 갈아끼우기 쉽다.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent.parent
SRC = ROOT / "assets" / "icons"
OUT = ROOT / "assets" / "icons-anim"

# 아이콘별 움직임 — (keyframes 본문, 주기)
MOVES = {
    "bob":   ("0%,50%{transform:translateY(0)}50.01%,100%{transform:translateY(1px)}", "1.4s"),
    "sway":  ("0%,50%{transform:translateX(0)}50.01%,100%{transform:translateX(1px)}", "1.8s"),
    "pulse": ("0%,60%{opacity:1}60.01%,100%{opacity:.45}", "1.6s"),
    "tick":  ("0%,25%{transform:translateY(0)}25.01%,50%{transform:translateY(-1px)}"
              "50.01%,100%{transform:translateY(0)}", "2.2s"),
}

# 어느 아이콘에 어떤 움직임을 줄지
PLAN = {
    "layout": "bob", "code": "sway", "git-branch": "tick",
    "message-processing": "pulse", "user": "bob", "zap": "pulse",
    "server": "pulse", "gamepad": "tick", "device-laptop": "bob",
    "heart": "tick", "chat": "pulse", "command": "sway",
}


def animate(path_d, fill, move):
    body, dur = MOVES[move]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
        f"<style>.a{{animation:m {dur} steps(1) infinite;transform-origin:center}}"
        f"@keyframes m{{{body}}}"
        "@media (prefers-reduced-motion:reduce){.a{animation:none}}</style>"
        f'<path class="a" d="{path_d}" fill="{fill}"/>'
        "</svg>"
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for name, move in sorted(PLAN.items()):
        for tone, fill in (("dark", "#000"), ("light", "#fff")):
            src = SRC / f"{name}-{tone}.svg"
            if not src.exists():
                print(f"  없음: {src.name}", file=sys.stderr)
                continue
            m = re.search(r'd="([^"]+)"', src.read_text())
            if not m:
                print(f"  path 없음: {src.name}", file=sys.stderr)
                continue
            (OUT / f"{name}-{tone}.svg").write_text(animate(m.group(1), fill, move))
            n += 1
    print(f"  {n}장 -> {OUT.relative_to(ROOT)}  (움직임 {len(set(PLAN.values()))}종)")


if __name__ == "__main__":
    main()
