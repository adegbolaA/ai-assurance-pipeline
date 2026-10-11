#!/usr/bin/env python3
"""Assemble the release evidence package from gate results.

Output (evidence/<version>/):
  evidence.json  machine-readable: every gate's result, control mappings, artifact hashes
  report.md      human-readable control evidence summary for an assessor
  poam.md        open AI findings from evals/known-findings.yaml

The directory is signed with cosign sign-blob in the release workflow.

Usage: build_evidence.py --version 1.2.3 --results gate-results --out evidence
"""

import argparse
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate_status(name: str, path: Path) -> tuple[str, dict]:
    if not path.is_file():
        return "missing", {}
    if path.suffix == ".xml":
        suite = ET.parse(path).getroot()
        suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
        failed = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
        detail = {k: suite.get(k) for k in ("tests", "failures", "errors", "skipped")}
        return ("pass" if failed == 0 else "fail"), detail
    doc = json.loads(path.read_text(encoding="utf-8"))
    if name == "policy":  # conftest --output json: list of per-file results
        failures = [f["msg"] for r in doc for f in (r.get("failures") or [])]
        return ("pass" if not failures else "fail"), {"failures": failures}
    if name == "code-policy":  # semgrep --json
        errs = [r["check_id"] for r in doc.get("results", [])]
        return ("pass" if not errs else "fail"), {"findings": errs}
    if name == "evals":
        detail = {k: doc.get(k) for k in ("backend", "accuracy_rate", "tests_total", "tests_passed", "open_findings", "resolved_findings", "blocking")}
        return ("pass" if doc.get("passed") else "fail"), detail
    if "passed" in doc:
        return ("pass" if doc["passed"] else "fail"), {k: v for k, v in doc.items() if k not in ("sources", "results")}
    return "recorded", doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--results", type=Path, default=Path("gate-results"))
    ap.add_argument("--out", type=Path, default=Path("evidence"))
    ap.add_argument("--controls", type=Path, default=Path("controls/control-map.yaml"))
    ap.add_argument("--system", type=Path, default=Path("ai-system.yaml"))
    ap.add_argument("--findings", type=Path, default=Path("evals/known-findings.yaml"))
    args = ap.parse_args()

    controls = yaml.safe_load(args.controls.read_text())
    system = yaml.safe_load(args.system.read_text())
    findings = yaml.safe_load(args.findings.read_text())["findings"]
    out = args.out / args.version
    out.mkdir(parents=True, exist_ok=True)

    gates = {}
    for name, g in controls["gates"].items():
        path = Path(g["evidence"])
        status, detail = gate_status(name, path)
        gates[name] = {
            "name": g["name"],
            "status": status,
            "evidence_file": g["evidence"],
            "evidence_sha256": sha256(path) if path.is_file() else None,
            "detail": detail,
            "controls": {k: v for k, v in g.items() if k not in ("name", "evidence")},
        }

    evals = gates.get("evals", {}).get("detail", {})
    open_ids = set(evals.get("open_findings") or [])
    # LAB-04 is verified by pytest (xfail strict) rather than promptfoo.
    open_ids |= {f["id"] for f in findings if f.get("tested_by")}

    evidence = {
        "system": system["system"],
        "models": system["models"],
        "release": {
            "version": args.version,
            "commit": os.environ.get("GITHUB_SHA"),
            "workflow_run": f"{os.environ.get('GITHUB_SERVER_URL')}/{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/{os.environ.get('GITHUB_RUN_ID')}"
            if os.environ.get("GITHUB_RUN_ID")
            else None,
            "image": os.environ.get("IMAGE_REF"),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "gates": gates,
        "poam": [dict(f, status="open" if f["id"] in open_ids else "pending-closure") for f in findings],
        "poam_controls": controls["poam"],
    }
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2, default=str))

    s = system["system"]
    lines = [
        f"# AI control evidence — {s['name']} {args.version}",
        "",
        f"| | |\n|---|---|\n| System | `{s['id']}` |\n| Owner | {s['owner']} |\n| Risk tier | **{s['risk_tier']}** |"
        f"\n| Use case | {s['use_case']} |\n| Models | {', '.join('`' + m['id'] + '`' for m in system['models'])} |"
        f"\n| Eval backend | {evals.get('backend', 'n/a')} |\n| Image | `{evidence['release']['image'] or 'n/a'}` |",
        "",
        "## Gate results",
        "",
        "| Gate | Status | NIST AI RMF | OWASP LLM | NIST 800-53 |",
        "|---|---|---|---|---|",
    ]
    for g in gates.values():
        c = g["controls"]
        lines.append(
            f"| {g['name']} | {g['status'].upper()} | {', '.join(c.get('nist_ai_rmf', []))} "
            f"| {', '.join(x.split()[0] for x in c.get('owasp_llm', []))} | {', '.join(c.get('nist_800_53', []))} |"
        )
    lines += ["", "Full mappings (AI 600-1, MITRE ATLAS, OMB M-25-21) and artifact hashes are in `evidence.json`.", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")

    poam = [
        f"# POA&M — {s['name']} {args.version}",
        "",
        "| ID | Weakness | OWASP LLM | Severity | Milestone | Owner | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in evidence["poam"]:
        poam.append(
            f"| {f['id']} | {f['title']} | {f['owasp_llm']} | {f['severity']} | {f['milestone']} | {f['owner']} | {f['status']} |"
        )
    (out / "poam.md").write_text("\n".join(poam) + "\n", encoding="utf-8")

    failed = [n for n, g in gates.items() if g["status"] in ("fail", "missing") and n not in ("signing", "human-approval")]
    print(f"evidence -> {out}  ({len(gates)} gates, {len(evidence['poam'])} POA&M items)")
    for n in failed:
        print(f"::warning::gate {n} is {gates[n]['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
