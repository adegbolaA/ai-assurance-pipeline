#!/usr/bin/env python3
"""Data governance gate — scan every declared data source for PII with Presidio.

Reads data_sources from ai-system.yaml so the scan covers exactly what the
system says it uses. A source declared contains_pii: false must scan clean.

Usage: pii_scan.py ai-system.yaml -o gate-results/pii.json
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

# High-precision entity types. PERSON/LOCATION are left out on purpose: on
# policy prose they mostly flag program and place names, and a noisy gate gets
# ignored.
ENTITIES = [
    "US_SSN",
    "US_ITIN",
    "US_PASSPORT",
    "US_DRIVER_LICENSE",
    "US_BANK_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
]
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".jsonl", ".csv"}


def build_analyzer():
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    nlp = NlpEngineProvider(
        nlp_configuration={"nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]}
    ).create_engine()
    return AnalyzerEngine(nlp_engine=nlp, supported_languages=["en"])


def scan_text(analyzer, text: str, threshold: float) -> list[dict]:
    hits = analyzer.analyze(text=text, entities=ENTITIES, language="en", score_threshold=threshold)
    return [{"entity": h.entity_type, "score": round(h.score, 2), "start": h.start, "end": h.end} for h in hits]


def iter_files(root: Path):
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in TEXT_SUFFIXES:
            yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("system", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--threshold", type=float, default=0.6)
    args = ap.parse_args()

    sources = yaml.safe_load(args.system.read_text())["data_sources"]
    analyzer = build_analyzer()
    report = {"entities": ENTITIES, "threshold": args.threshold, "sources": [], "passed": True}

    for src in sources:
        findings = []
        files = list(iter_files(Path(src["path"])))
        for f in files:
            for hit in scan_text(analyzer, f.read_text(encoding="utf-8"), args.threshold):
                # Record type and location only — never the matched value.
                findings.append({"file": str(f), **hit})
        violates = bool(findings) and not src.get("contains_pii", False)
        report["sources"].append(
            {
                "path": src["path"],
                "declared_pii": src.get("contains_pii", False),
                "files_scanned": len(files),
                "findings": findings,
            }
        )
        if violates:
            report["passed"] = False
            for h in findings:
                print(f"::error file={h['file']}::{h['entity']} (score {h['score']}) in a source declared PII-free")
        print(f"{src['path']}: {len(files)} files, {len(findings)} findings")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
