#!/usr/bin/env python3
"""캐릭터를 도트 스프라이트로 다시 뽑는다.

원본 러닝 그림을 그냥 줄이는 방식은 버렸다. 팔다리가 사방으로 뻗고 소품(메카·총·
늑대)이 붙어 있어 세로 38px 로 줄이면 형체가 덩어리로 뭉친다 — 축소 필터를
LANCZOS·BOX·블러+BOX 로 바꿔 가며 나란히 놓고 확인했고 셋 다 마찬가지였다
(2026-08-27 지적 「왤케 깨지냐 캐릭터 도트가」).

그래서 원본을 참조로 주고 도트로 다시 그리게 한다. 참조 없이 말로만 묘사하면
딴사람이 나온다 — 형태가 정해진 대상엔 참조가 답이다.

참조는 512px JPEG 로 줄여 보낸다. 그보다 크면 413 으로 즉시 거부되고, 투명 배경은
흰색에 합성해야 한다(그냥 RGB 로 바꾸면 투명이 검게 되고 결과물까지 어두워진다).

한 장에 러닝 4프레임을 가로로 나란히 요청한다. 프레임을 따로 뽑으면 프레임마다
캐릭터가 미묘하게 달라져 애니메이션이 떨린다.
"""
import base64
import concurrent.futures as cf
import io
import pathlib
import sys
import time

import requests
from PIL import Image

HOST = "https://apis.opengateway.ai"
KEY_FILE = pathlib.Path.home() / ".config" / "opengateway.key"
MODEL = "openai/gpt-image-2"
SRC = pathlib.Path(__file__).parent / "runners-src"
OUT = pathlib.Path(__file__).parent / "runners-dot"
NAMES = ["norma", "sparkle", "kei", "aria", "nangongyu", "sunna"]

PROMPT = (
    "Redraw this exact character as a pixel-art sprite sheet for a retro game. "
    "Four frames of a side-view running cycle, laid out left to right, evenly "
    "spaced, all frames the same size and standing on the same baseline. "
    "Chunky visible square pixels, roughly 48 pixels tall per character, flat "
    "limited palette, hard edges, no anti-aliasing, no gradients, no outline glow. "
    "Keep the character's hair colour, eye colour, outfit colours and silhouette "
    "recognisable. Full body from head to feet in every frame. "
    "Plain solid white background, no shadow, no text, no frame borders, no grid."
)


def ref_bytes(path):
    """참조를 512px JPEG 로. 투명은 흰색에 합성한다."""
    im = Image.open(path).convert("RGBA")
    s = 512 / max(im.width, im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))),
                   Image.LANCZOS)
    flat = Image.new("RGB", im.size, (255, 255, 255))
    flat.paste(im, (0, 0), im)
    buf = io.BytesIO()
    flat.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def one(name):
    t0 = time.time()
    try:
        r = requests.post(
            f"{HOST}/v1/images/edits",
            headers={"Authorization": "Bearer " + KEY_FILE.read_text().strip()},
            files={"image": ("ref.jpg", ref_bytes(SRC / f"{name}-a.png"), "image/jpeg")},
            data={"model": MODEL, "prompt": PROMPT, "size": "1536x1024",
                  "n": "1", "quality": "high"},
            timeout=600)
    except Exception as e:
        return name, f"{e!r}"
    if r.status_code != 200:
        return name, f"HTTP {r.status_code} {r.text[:160]}"
    b64 = r.json().get("data", [{}])[0].get("b64_json")
    if not b64:
        return name, "이미지 없음"
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.png"
    p.write_bytes(base64.b64decode(b64))
    return name, f"{time.time()-t0:.0f}초 · {p.stat().st_size//1024}KB"


if __name__ == "__main__":
    if not KEY_FILE.exists():
        sys.exit(f"키 없음: {KEY_FILE}")
    with cf.ThreadPoolExecutor(6) as ex:
        for name, msg in ex.map(one, NAMES):
            print(f"  {name:10s} {msg}", flush=True)
