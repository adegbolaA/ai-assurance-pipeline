#!/usr/bin/env python3
"""Generate a CycloneDX 1.6 ML-BOM for the AI system.

Lists the application, every model it uses (with its model card and registry
approval), and every data source with a SHA-256 per file — so the release
records exactly which model and which data shipped together.

Usage: build_mlbom.py ai-system.yaml models/registry.yaml --version 1.2.3 -o ai-system.mlbom.json
"""

import argparse
import hashlib
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def props(**kv) -> list[dict]:
    return [{"name": f"aigg:{k}", "value": str(v)} for k, v in kv.items() if v is not None]


def model_component(m: dict, entry: dict) -> dict:
    card = Path(entry["model_card"])
    if not card.is_file():
        sys.exit(f"model card {card} for {m['id']} does not exist")
    return {
        "type": "machine-learning-model",
        "bom-ref": f"model:{m['id']}",
        "name": entry.get("name", m["id"]),
        "version": m["id"],
        "supplier": {"name": entry["provider"]},
        "licenses": [{"license": {"name": entry["license"]}}] if entry.get("license") else [],
        "externalReferences": [
            {"type": "documentation", "url": str(card), "hashes": [{"alg": "SHA-256", "content": sha256(card)}]}
        ],
        "modelCard": {
            "modelParameters": {"task": "text-generation"},
            "considerations": {
                "useCases": [entry.get("intended_use", "")],
                "technicalLimitations": [entry.get("out_of_scope", "")],
            },
        },
        "properties": props(
            provider=m["provider"],
            region=m.get("region"),
            hosting=entry.get("hosting"),
            registry_status=entry["status"],
            approved_by=entry.get("approved_by"),
            approved_on=entry.get("approved_on"),
            review_by=entry.get("review_by"),
            max_risk_tier=entry.get("max_risk_tier"),
        ),
    }


def data_component(src: dict) -> dict:
    root = Path(src["path"])
    files = sorted(p for p in root.rglob("*") if p.is_file()) if root.is_dir() else [root]
    return {
        "type": "data",
        "bom-ref": f"data:{src['path']}",
        "name": src["path"],
        "data": [
            {
                "type": "dataset",
                "name": src["path"],
                "classification": src.get("classification", "unclassified"),
                "contents": {"attachment": {"content": "\n".join(f"{sha256(f)}  {f.as_posix()}" for f in files)}},
            }
        ],
        "properties": props(contains_pii=src.get("contains_pii", False), files=len(files)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("system", type=Path)
    ap.add_argument("registry", type=Path)
    ap.add_argument("--version", required=True)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()

    system = yaml.safe_load(args.system.read_text())
    registry = {m["id"]: m for m in yaml.safe_load(args.registry.read_text())["models"]}
    s = system["system"]

    models = [model_component(m, registry[m["id"]]) for m in system["models"]]
    datasets = [data_component(d) for d in system["data_sources"]]
    app_ref = f"app:{s['id']}"

    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "component": {
                "type": "application",
                "bom-ref": app_ref,
                "name": s["id"],
                "version": args.version,
                "description": s.get("description", "").strip(),
                "properties": props(owner=s["owner"], use_case=s["use_case"], risk_tier=s["risk_tier"]),
            },
        },
        "components": models + datasets,
        "dependencies": [{"ref": app_ref, "dependsOn": [c["bom-ref"] for c in models + datasets]}],
    }
    args.output.write_text(json.dumps(bom, indent=2))
    print(f"ML-BOM: {len(models)} model(s), {len(datasets)} data source(s) -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
