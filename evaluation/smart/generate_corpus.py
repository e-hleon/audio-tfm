"""Generate a tiny deterministic PCM corpus and interval manifest for VAD work."""
from __future__ import annotations
import argparse, json, math, random, wave
from pathlib import Path

RATE = 16_000
def write_wav(path: Path, samples: list[int]) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(RATE)
        out.writeframes(b"".join(int(max(-32768, min(32767, s))).to_bytes(2, "little", signed=True) for s in samples))

def generate(output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True); rng = random.Random(20260906); rows = []
    cases = [("silence", [("silence", 1.0)]), ("noise", [("noise", 1.0)]), ("speech-like", [("silence", .4), ("speech", 1.2), ("silence", .4), ("speech", .8)])]
    for name, blocks in cases:
        samples=[]; intervals=[]; cursor=0
        for kind, seconds in blocks:
            n=int(seconds*RATE)
            if kind == "silence": block=[0]*n
            elif kind == "noise": block=[rng.randint(-2500,2500) for _ in range(n)]
            else: block=[int(7000*math.sin(2*math.pi*220*(i/RATE))) for i in range(n)]
            samples.extend(block)
            if kind == "speech": intervals.append([cursor/RATE, (cursor+n)/RATE])
            cursor += n
        file=output/f"{name}.wav"; write_wav(file, samples); rows.append({"audio": str(file), "ground_truth_intervals": intervals})
    manifest=output/"manifest.json"; manifest.write_text(json.dumps({"sample_rate":RATE,"frame_ms":20,"tolerance_ms":100,"cases":rows},indent=2),encoding="utf-8"); return manifest

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,default=Path(".evaluation-cache/smart")); print(generate(parser.parse_args().output))
