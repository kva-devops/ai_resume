from __future__ import annotations

import json
import sys
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.db import DEFAULT_PROMPT, connect, get_prompt
from backend.services import compute_result, evaluate


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "Test CV"
OUT = ROOT / "benchmark" / "v3_current_gpt4o_mini.json"
RUBRIC = json.loads((ROOT / "benchmark" / "rubric.json").read_text(encoding="utf-8"))
CRITERIA = RUBRIC["criteria"]


def current_prompt():
    v3 = ROOT / "benchmark" / "improved_system_prompt_v3.txt"
    if v3.exists():
        return v3.read_text(encoding="utf-8")
    try:
        with connect() as db:
            return get_prompt(db)["value"]
    except Exception:
        return DEFAULT_PROMPT


def extract(path: Path):
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def main():
    files = sorted(PDF_DIR.glob("*.pdf"))[:25]
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    done = {row["file"]: row for row in previous}
    prompt = current_prompt()
    for index, path in enumerate(files, 1):
        if path.name in done and done[path.name].get("status") == "done":
            print(f"[{index}/{len(files)}] cached {path.name}", flush=True)
            continue
        try:
            content = extract(path)
            evaluation, mode = evaluate(content, CRITERIA, prompt)
            evaluation = compute_result(evaluation, CRITERIA)
            done[path.name] = {
                "file": path.name,
                "candidate_id": path.stem,
                "status": "done",
                "mode": mode,
                **evaluation,
            }
            print(f"[{index}/{len(files)}] done {path.name} score={evaluation['score']}", flush=True)
        except Exception as exc:
            done[path.name] = {"file": path.name, "candidate_id": path.stem, "status": "error", "error": str(exc)}
            print(f"[{index}/{len(files)}] error {path.name}: {exc}", flush=True)
        OUT.write_text(json.dumps([done[name] for name in sorted(done)], ensure_ascii=False, indent=2), encoding="utf-8")
    results = [done[path.name] for path in files if path.name in done]
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(files), "results": len(results), "done": sum(r.get("status") == "done" for r in results), "errors": sum(r.get("status") == "error" for r in results)}))


if __name__ == "__main__":
    main()
