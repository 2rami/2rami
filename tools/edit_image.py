#!/usr/bin/env python3
"""참조 이미지를 놓고 그림을 뽑는다 (형태 유지).

말로만 묘사하면 원본에서 멀어진다 — 곡선이나 인상은 문장으로 옮겨지지 않는다.
참조를 넣으면 실루엣과 색이 원본에 붙어 있는다.

주의 둘:
- 이 엔드포인트는 dev 에만 있다. live 는 404 다.
- 업로드가 크면 본문 없는 413 이 즉시 떨어진다. 참조는 512px·100KB 이하로 보낸다.
  결과물 해상도(size)와 참조 해상도는 무관하다.
"""
import base64
import concurrent.futures as cf
import io
import json
import pathlib
import sys
import time

import requests

HOST = "https://dev-asmr-v2.sionic.im"
KEY_FILE = pathlib.Path.home() / ".config" / "opengateway-dev.key"
MODEL = "openai/gpt-image-2"
OUT = pathlib.Path(__file__).parent.parent / "assets" / "gen"
MAX_REF_PX = 512
MAX_REF_KB = 100


def shrink(path, bg=(168, 216, 240)):
    """참조를 512px·100KB 안으로 줄인다. 그라데이션이 있으면 PNG 가 안 줄어드니 JPEG 로.

    투명 배경은 반드시 채워서 보낸다. JPEG 는 알파가 없어 그냥 변환하면 투명한
    자리가 검정이 되고, 그 검정이 참조로 들어가 어두운 그림이 나온다.
    기본값은 연한 하늘색 — 배경을 하늘로 이어 그리게 하는 편이 자연스럽다.
    """
    from PIL import Image
    src = Image.open(path)
    if src.mode in ("RGBA", "LA", "P"):
        src = src.convert("RGBA")
        im = Image.new("RGB", src.size, bg)
        im.paste(src, mask=src.split()[-1])
    else:
        im = src.convert("RGB")
    if max(im.size) > MAX_REF_PX:
        im.thumbnail((MAX_REF_PX, MAX_REF_PX), Image.LANCZOS)
    for q in (85, 75, 65, 55):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q)
        if buf.tell() <= MAX_REF_KB * 1024:
            return buf.getvalue(), f"{im.size[0]}x{im.size[1]} q{q} {buf.tell()//1024}KB"
    return buf.getvalue(), f"{im.size[0]}x{im.size[1]} q55 {buf.tell()//1024}KB(상한초과)"


def edit(name, ref_bytes, prompt, size, quality):
    t0 = time.time()
    try:
        r = requests.post(
            f"{HOST}/v1/images/edits",
            headers={"Authorization": "Bearer " + KEY_FILE.read_text().strip()},
            files={"image": ("ref.jpg", ref_bytes, "image/jpeg")},   # filename·MIME 없으면 400
            data={"model": MODEL, "prompt": prompt, "size": size,
                  "n": "1", "quality": quality},                      # input_fidelity 는 보내지 말 것
            timeout=600,
        )
    except Exception as e:
        return name, None, repr(e)
    if r.status_code != 200:
        return name, None, f"HTTP {r.status_code} {r.text[:160] or '(본문 없음 — 413이면 참조가 큼)'}"
    b64 = r.json().get("data", [{}])[0].get("b64_json")
    if not b64:
        return name, None, f"이미지 없음: {r.text[:160]}"
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.png"
    p.write_bytes(base64.b64decode(b64))
    return name, p, f"{time.time()-t0:.0f}초 · {p.stat().st_size//1024}KB"


def main():
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
    ref_cache = {}
    for s in spec:
        rp = s["ref"]
        if rp not in ref_cache:
            ref_cache[rp] = shrink(rp)
            print(f"  참조 {pathlib.Path(rp).name}: {ref_cache[rp][1]}")
    with cf.ThreadPoolExecutor(max_workers=min(4, len(spec))) as ex:
        futs = [ex.submit(edit, s["name"], ref_cache[s["ref"]][0], s["prompt"],
                          s.get("size", "1536x1024"), s.get("quality", "medium"))
                for s in spec]
        for f in cf.as_completed(futs):
            name, path, note = f.result()
            print(f"  {'OK  ' if path else '실패'} {name:<22} {note}", flush=True)


if __name__ == "__main__":
    main()
