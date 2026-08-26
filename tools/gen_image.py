#!/usr/bin/env python3
"""OpenGateway 로 리드미용 그림을 뽑는다.

키는 인자로 받지 않고 파일에서 읽는다 — 명령줄에 적으면 셸 히스토리와 프로세스
목록에 남는다.

한 장에 2분 넘게 걸리므로 여러 장은 스레드로 동시에 던진다. 순차로 돌리면
네 장에 10분이 넘는다.
"""
import base64
import concurrent.futures as cf
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

HOST = "https://apis.opengateway.ai"
KEY_FILE = pathlib.Path.home() / ".config" / "opengateway.key"
MODEL = "openai/gpt-image-2"          # 2026-08-11 지시: OG 이미지 기본 모델
OUT = pathlib.Path(__file__).parent.parent / "assets" / "gen"


def key():
    if not KEY_FILE.exists():
        sys.exit(f"키 없음: {KEY_FILE}")
    return KEY_FILE.read_text().strip()


def generate(name, prompt, size="1536x1024", quality="high"):
    body = json.dumps({
        "model": MODEL, "prompt": prompt,
        "size": size, "n": 1, "quality": quality,
    }).encode()
    req = urllib.request.Request(
        f"{HOST}/v1/images/generations", data=body,
        headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        return name, None, f"HTTP {e.code} {e.read()[:200].decode(errors='replace')}"
    except Exception as e:
        return name, None, repr(e)

    item = payload.get("data", [{}])[0]
    b64 = item.get("b64_json")
    if not b64:
        return name, None, f"이미지 없음: {str(payload)[:200]}"
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.png"
    p.write_bytes(base64.b64decode(b64))
    return name, p, f"{time.time()-t0:.0f}초 · {p.stat().st_size//1024}KB"


def main():
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
    with cf.ThreadPoolExecutor(max_workers=min(4, len(spec))) as ex:
        futs = [ex.submit(generate, s["name"], s["prompt"],
                          s.get("size", "1536x1024"), s.get("quality", "high"))
                for s in spec]
        for f in cf.as_completed(futs):
            name, path, note = f.result()
            mark = "OK  " if path else "실패"
            print(f"  {mark} {name:<22} {note}", flush=True)


if __name__ == "__main__":
    main()
