#!/usr/bin/env python3
"""숫자 0~9 를 도트 폰트 path 로 구워 JSON 으로 내보낸다.

카운터 SVG 는 서버가 요청마다 새로 그려야 하므로 파이썬이 아니라 JS 에서 조립한다.
폰트 파일을 서버로 들고 가 매번 파싱하는 대신, 글자 모양을 미리 path 로 뽑아
JSON 한 덩이로 넘긴다 — 서버는 문자열만 이어 붙이면 된다.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import textpath as T

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "counter" / "digits.json"

CHARS = "0123456789,"


def main():
    _, gs, cmap, upm = T._font("bold")
    glyphs = {}
    for ch in CHARS:
        d, adv = T._glyph(ch, "bold")
        glyphs[ch] = {"d": d, "w": adv}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"upm": upm, "glyphs": glyphs}, separators=(",", ":")))
    print(f"  {OUT.relative_to(ROOT)}  {OUT.stat().st_size // 1024}KB  "
          f"({len(CHARS)}자, upm={upm})")


if __name__ == "__main__":
    main()
