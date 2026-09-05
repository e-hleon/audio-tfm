"""Calcula métricas del selector a partir de etiquetas, sin audio privado."""
import argparse
import json
from pathlib import Path


def run(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    voice = {"tp": 0, "fp": 0, "fn": 0}; speaker = {"genuine_accepted": 0, "genuine_rejected": 0, "impostor_accepted": 0, "impostor_rejected": 0}
    for row in rows:
        expected, detected = bool(row["expected_voice"]), bool(row["detected_voice"])
        if expected and detected: voice["tp"] += 1
        elif not expected and detected: voice["fp"] += 1
        elif expected and not detected: voice["fn"] += 1
        if "expected_user" in row and "accepted_user" in row:
            key = ("genuine_" if row["expected_user"] else "impostor_") + ("accepted" if row["accepted_user"] else "rejected")
            speaker[key] += 1
    precision = voice["tp"] / (voice["tp"] + voice["fp"]) if voice["tp"] + voice["fp"] else 0.0
    recall = voice["tp"] / (voice["tp"] + voice["fn"]) if voice["tp"] + voice["fn"] else 0.0
    return {"segments": len(rows), "vad": {**voice, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}, "speaker": speaker, "note": "Requiere audio etiquetado; no es una cifra de esta ejecución."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--segments", type=Path, required=True); args = parser.parse_args(); print(json.dumps(run(args.segments), indent=2))
