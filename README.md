# ai-assurance-pipeline

**An automated checkpoint system that makes every change to an AI application prove it is approved, safe and documented before it can go live — and produces a signed report an auditor can check.**

> **New here?** Read [In plain English](#in-plain-english) and [How it works](#how-it-works). Engineers can jump to the [Technical reference](#technical-reference).

---

## In plain English

### The problem

Government agencies and companies want to use AI assistants. But AI brings new risks that ordinary software checks don't catch:

- **It can be tricked.** A cleverly worded message — or a booby-trapped document the AI reads — can make it ignore its instructions.
- **It can leak secrets** it was given behind the scenes.
- **It can come from an unapproved vendor**, or quietly be swapped for a different model nobody reviewed.
- **Its training or test data can contain private information** about real people.

Federal rules now require agencies to manage these risks — especially for "high-impact" AI that affects people's access to services (OMB memo M-25-21). Someone has to *prove* the checks happened, every time the system changes.

### The idea

Think of **airport security for software changes**.

Every time someone changes the AI application, the change must pass through a series of **automatic checkpoints**. Each checkpoint asks one question. If any answer is "no", the change is **stopped** — it cannot go live. If everything passes and a person with authority signs off, the system **ships with a signed report** listing every check, its result, and which official requirement it satisfies.

Nobody has to remember to run the checks. Nobody can skip them — not even the repository owner.

### The example application

To show this working, the project includes a small AI assistant: a **Benefits Caseworker Assistant**. A caseworker asks questions like *"What is the income limit for a family of four?"* and the assistant answers from the program's official policy documents (using Amazon's Bedrock AI service).

Because its answers could influence whether a family gets housing assistance, it is classed as **high-impact** — so it gets the strictest treatment, including human sign-off before every release.

### The deliberate flaws

The assistant ships with **four known weaknesses, planted on purpose** — like a fire drill, or a "mystery shopper" test. They prove the checkpoints catch real problems:

| Flaw | In everyday terms |
|---|---|
| **LAB-01** — secret leak | Ask the assistant to "print your instructions" and it reveals an internal code it was told to keep private |
| **LAB-02** — booby-trapped document | One policy page contains hidden text telling the AI to approve every application and send people to a fake website. The AI obeys it |
| **LAB-03** — unsafe output | The assistant can be made to return web code that would run in a caseworker's browser |
| **LAB-04** — no usage limits | Anyone can send enormous requests, running up cost or slowing the service |

These are tracked like real issues in a **remediation plan** (in government terms, a POA&M — Plan of Action and Milestones), each with an owner and a deadline. The checkpoints allow these *known, tracked* flaws but **block any new one**.

---

## How it works

### The big picture

```mermaid
flowchart LR
    A(["👩‍💻 Someone proposes<br/>a change"]) --> B{"🔍 Automatic<br/>checkpoints"}
    B -- "any check fails" --> X(["⛔ Change blocked<br/>problem must be fixed"])
    B -- "all checks pass" --> C["🧪 Tested against<br/>the real AI model"]
    C --> D{"✍️ Human approval<br/>(high-impact AI)"}
    D -- "rejected" --> X
    D -- "approved" --> E(["📦 Released, with a<br/>signed audit report"])

    classDef start fill:#e8f1fb,stroke:#3b82c4,color:#0b2e4f
    classDef check fill:#fff4d6,stroke:#c9a227,color:#4a3a00
    classDef stop fill:#fde2e1,stroke:#c0392b,color:#5c1410
    classDef good fill:#dff3e4,stroke:#2e8b57,color:#0f3d22
    class A start
    class B,C,D check
    class X stop
    class E good
```

### Step by step: what happens to a change

1. **Someone proposes a change** — new code, a different AI model, an updated policy document. Changes can't go straight in; they must be proposed for review (a *pull request*).
2. **The checkpoints run automatically**, in parallel, within a few minutes. Each one answers a single question (see the table below).
3. **If any checkpoint fails, the change is blocked.** The person sees exactly which check failed and why.
4. **Once merged, a release candidate is built** — the exact package that would go live.
5. **That exact package is tested against the real AI model** — the same attack tests as before, but now with the genuine AI, not a stand-in.
6. **A designated approver signs off** (required because this AI is high-impact). The approval is recorded with their name.
7. **The package is digitally signed and released**, together with a signed audit report. Anyone can later verify that the report is genuine and that what's running is exactly what was tested and approved.

### The checkpoints, in plain terms

| Checkpoint | The question it answers |
|---|---|
| **Inventory & approval** | Is this AI system registered, with an owner and a risk level? Is the AI model on the approved list, and is that approval still current? |
| **Approved vendors only** | Does the system only use AI providers and regions the organization has authorized? |
| **Code rules** | Does the code avoid calling unapproved AI services, or loading files in ways that could run hidden malicious code? |
| **Model file safety** | If any AI model files are included, are they free of hidden malicious code? |
| **Privacy** | Is the data the AI uses free of personal information like social security or credit card numbers? |
| **Attack testing** | When we try to trick the AI — make it leak secrets, follow hidden instructions, or produce unsafe output — does it resist? Does it still answer correctly? |
| **Security patches** | Is the software package free of known, serious security holes? |
| **Cloud permissions** | Is the AI's access to the cloud locked down to the bare minimum — one model, one region, and only this project? |
| **Human sign-off** | For high-impact AI: has an authorized person approved this release? |

### How we know the checks actually work

A check that *never* finds anything might be working — or might be silently broken. So every checkpoint is regularly fed something **known to be bad**, and must catch it. It's like pressing the **test button on a smoke detector**.

This isn't theoretical. While building this project, the test-button approach exposed **three security scanners that reported "all clear" while not actually checking** what they appeared to check. Each was fixed, and the test now runs on every change so it can't silently break again.

### What the auditor receives

Every release produces a signed report package containing:

- **Results of every checkpoint**, with fingerprints of the evidence so it can't be altered afterwards
- **Which official requirement each check satisfies** — mapped to the NIST AI Risk Management Framework, NIST's Generative AI profile, the OWASP list of top AI risks, MITRE's catalogue of AI attacks, the NIST security controls used for federal system authorization, and OMB M-25-21
- **The remediation plan** — open issues, owners and deadlines
- **An "ingredients list" for the AI** (a *bill of materials*): which model, who approved it, and fingerprints of every document it was given
- **Who approved the release**, and when

This is the same kind of evidence agencies assemble for an **Authorization to Operate (ATO)** — produced automatically, every release, instead of by hand.

### Jargon decoder

| Term | Meaning |
|---|---|
| **Assurance** | Proof, backed by evidence someone else can check, that something meets its requirements — hence the name *AI assurance pipeline* |
| **Pull request (PR)** | A proposed change, waiting for checks and review before it's accepted |
| **Pipeline / CI** | The automated process that runs the checkpoints |
| **Release** | Publishing a new version that can be deployed |
| **Model** | The AI "brain" — here, Amazon Nova Lite, accessed through Amazon Bedrock |
| **Prompt injection** | Tricking an AI with crafted text so it ignores its instructions |
| **Red-team / evals** | Deliberately attacking the AI to test its defenses, and testing answer accuracy |
| **Mock model** | A cheap, predictable stand-in for the real AI, used for everyday checks |
| **POA&M** | Plan of Action and Milestones — the official list of known issues and when they'll be fixed |
| **ATO** | Authorization to Operate — formal government approval to run a system |
| **Bill of materials (ML-BOM)** | An ingredients list for the AI system |
| **Digital signature** | A tamper-proof seal proving who produced something and that it hasn't changed |
| **Negative control** | Feeding a check something known to be bad, to prove the check works |
| **High-impact AI** | AI whose output can significantly affect people's rights or access to services (OMB M-25-21) |

---

## Technical reference

The same idea as DevSecOps gates (SAST, image scanning, signing), applied to models, prompts and data. Built on [`hardened-base`](https://github.com/platform-base-images/hardened-base)'s `python-ml-base` image, reusing its supply-chain patterns (Cosign keyless signing, attestations, Conftest).

### Pipeline

```mermaid
flowchart TB
    PR(["Pull request"])

    subgraph AIG["ai-gates.yml → AI Gate Summary"]
        direction TB
        G1["Policy · OPA/Conftest<br/>Code policy · Semgrep<br/>ModelScan · PII · Presidio<br/>Unit tests"]
        G2["Image build · Trivy<br/>promptfoo evals · mock model"]
    end

    subgraph IAC["iac.yml → IaC Summary"]
        direction TB
        T["Terraform fmt + validate"] --> K["Checkov<br/>negative + mutation controls<br/>SARIF → code scanning"]
    end

    PR --> AIG
    PR --> IAC
    AIG --> MERGE(["Both required checks pass → merge to main"])
    IAC --> MERGE

    subgraph REL["release.yml"]
        direction LR
        RG["Re-run<br/>both gate sets"] --> C["Build candidate<br/>push by digest"]
        C --> L["Evals on that digest<br/>live Bedrock model"]
        L --> A{"high-impact?"}
        A -- yes --> H["Board approval<br/>ai-high-impact env"]
        A -- no --> PUB
        H --> PUB["Cosign sign · ML-BOM<br/>signed evidence<br/>GitHub Release"]
    end

    MERGE --> RG

    classDef gate fill:#fff4d6,stroke:#c9a227,color:#4a3a00
    classDef ok fill:#dff3e4,stroke:#2e8b57,color:#0f3d22
    classDef human fill:#e8f1fb,stroke:#3b82c4,color:#0b2e4f
    class G1,G2,T,K,RG,C,L gate
    class MERGE,PUB ok
    class A,H human
```

### Gates

| Gate | What blocks the build | Tool | Evidence |
|---|---|---|---|
| Inventory & registration | Model not in `models/registry.yaml`, not approved, approval expired, or not cleared for the system's risk tier; system missing owner/risk tier | OPA/Conftest | `policy.json` |
| Provider policy | Provider or region not in `policy/data/approved-providers.yaml` | OPA/Conftest | `policy.json` |
| High-impact controls | High-impact system without impact assessment or named approver team | OPA/Conftest | `policy.json` |
| Code policy | Unapproved AI SDK import, hardcoded model endpoint, Bedrock call outside the gateway, pickle/joblib load, runtime model download | Semgrep (custom rules) | `semgrep.json` |
| Model supply chain | Any committed model artifact with unsafe operators | ModelScan | `modelscan.json` |
| Data governance | PII in any data source declared PII-free | Presidio | `pii.json` |
| Red-team & accuracy | Any security failure **not** on the POA&M; untagged accuracy below threshold | promptfoo | `evals.json` |
| Runtime enforcement | Service refuses to start with an unregistered model | app + pytest | `pytest.xml` |
| Container | Critical/high CVEs | Trivy | job log |
| IaC (`iac.yml`) | Unformatted/invalid Terraform; any failed Checkov check on `infra/` — e.g. IAM wildcards, an OIDC trust not pinned to this repo | Terraform, Checkov (+ SARIF to code scanning) | `checkov.json` |
| Human approval | High-impact release without board sign-off | GitHub Environment | `approval.json` |
| Provenance | — (always produced) | Cosign, CycloneDX ML-BOM | `signing.json`, `ai-system.mlbom.json` |

Every scanner gate has a **negative control** — a test proving it fires on a planted bad input — so "0 findings" is evidence, not silence. Real failures this caught while building: `hardened-base`'s Conftest job evaluated zero rules (package-namespace mismatch); Trivy's IaC checks passed an admin `*:*` IAM policy; Checkov skipped the OIDC repo-pinning check on our own trust policy (unresolvable principal) — now guarded by a mutation control in `iac.yml`.

### Planted findings and the POA&M

| ID | OWASP LLM | MITRE ATLAS | Where | Caught by |
|---|---|---|---|---|
| `AAP-LAB-01` | LLM07 System Prompt Leakage | AML.T0056 | secret in system prompt | promptfoo canary check |
| `AAP-LAB-02` | LLM01 Prompt Injection (indirect) | AML.T0051.001 | poisoned `faq-community-submitted.md` | promptfoo |
| `AAP-LAB-03` | LLM05 Improper Output Handling | AML.T0051.000 | unescaped HTML response | promptfoo |
| `AAP-LAB-04` | LLM10 Unbounded Consumption | AML.T0034 | no input / `max_tokens` cap | pytest `xfail(strict=True)` |

`evals/known-findings.yaml` is the POA&M. The eval gate lets a listed finding fail (accepted and tracked), blocks anything else, and flags a listed finding once its tests pass so the item gets closed. Fixing a planted weakness is the intended exercise.

### Why mock on PRs, live model on release

PR evals run against `LLM_BACKEND=mock`, a deterministic stand-in that behaves like a naive instruction-following model: free, no credentials, and it reliably exercises the planted weaknesses. The release re-runs the same evals against the real Bedrock model on the exact image digest that will be signed — a release cannot ship on mock results.

### Evidence package

Each release publishes `evidence-<version>.tar.gz` plus a Sigstore bundle:

- `evidence.json` — every gate's result, artifact SHA-256s, image digest, approver, and control mappings to **NIST AI RMF 1.0**, **NIST AI 600-1**, **OWASP LLM Top 10 (2025)**, **MITRE ATLAS**, **NIST SP 800-53 Rev 5** and **OMB M-25-21** (`controls/control-map.yaml`)
- `report.md` — assessor-readable control summary (also the release notes)
- `poam.md` — open AI findings with owners and milestones (CA-5)
- `ai-system.mlbom.json` — CycloneDX 1.6 ML-BOM: model, model card hash, registry approval, per-file data hashes

Verify (cosign v3 — v2 does not read the bundle format and reports "no signatures found"):

```bash
cosign verify-blob evidence-0.1.42.tar.gz --bundle evidence-0.1.42.sigstore.json \
  --certificate-identity-regexp 'https://github.com/.+/ai-assurance-pipeline/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
cosign verify-attestation --type cyclonedx ghcr.io/<owner>/ai-assurance-pipeline:0.1.42 \
  --certificate-identity-regexp 'https://github.com/.+/ai-assurance-pipeline/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

### Run locally

```bash
# Base image (from hardened-base): make build IMAGE=python-ml-base, then tag it
docker build -f app/Dockerfile --build-arg BASE_IMAGE=python-ml-base:local -t aap-app:local .
docker run -d -p 8000:8000 -e LLM_BACKEND=mock --read-only --cap-drop ALL aap-app:local

npx promptfoo@0.124.1 eval -c evals/promptfooconfig.yaml -o promptfoo-results.json
python scripts/eval_gate.py promptfoo-results.json evals/known-findings.yaml -o gate-results/evals.json --backend mock

conftest verify --policy policy
echo 'today: "'"$(date -u +%F)"'"' > policy/data/today.yaml
conftest test --combine ai-system.yaml models/registry.yaml --policy policy --data policy/data

pip install pre-commit && pre-commit install   # hygiene, gitleaks, ruff, terraform fmt/validate
```

### Repo setup

| Setting | Value |
|---|---|
| Secret `GHCR_TOKEN` | PAT: `read:packages` on platform-base-images, `write:packages` here |
| Environment `ai-eval` | Variable `AWS_EVAL_ROLE_ARN` = `terraform output eval_role_arn`; deployment branches: `main` only |
| Environment `ai-high-impact` | Required reviewers = AI governance board; deployment branches: `main` only |
| Branch protection (`main`) | PR required; required checks **AI Gate Summary** and **IaC Summary** (GitHub Actions only); enforced for admins; no force-push or deletion; conversations resolved. Approvals 0 while there is a single maintainer — raise to 1 with code-owner review once there is a second reviewer |

### AWS access (`infra/aws`)

Terraform for the release evals' AWS access — no long-lived keys anywhere:

- GitHub OIDC identity provider (account-wide, `prevent_destroy`)
- Role `ai-governance-gate-bedrock-eval` (name kept from the project's earlier name; renaming an IAM role replaces it and changes its ARN), trusting **only** the exact subject `repo:adegbolaA/ai-assurance-pipeline:environment:ai-eval`. The `ai-eval` environment is restricted to `main`, so branches, PRs and forks cannot assume it
- Inline policy: `bedrock:InvokeModel` on the models in `var.model_ids` — keep it in step with the approved entries in `models/registry.yaml`

```bash
cd infra/aws
terraform init
terraform plan    # existing resources are adopted via imports.tf
terraform apply
terraform output eval_role_arn
```

State is local; move to an S3 backend (`use_lockfile = true`) before sharing the stack.

### Layout

```
ai-system.yaml               system inventory record: owner, use case, risk tier, models, data
models/registry.yaml         approved model registry      models/cards/   model cards
policy/                      Rego gate + unit tests, provider allowlist, Semgrep rules
app/                         FastAPI RAG service, corpus (incl. poisoned page), tests
evals/                       promptfoo config, known-findings.yaml (POA&M)
scripts/                     PII scan, ModelScan gate, eval gate, ML-BOM, evidence builder
controls/control-map.yaml    gate → framework control mapping
docs/impact-assessment.md    M-25-21 AI impact assessment
infra/aws/                   Terraform: GitHub OIDC provider, Bedrock eval role
infra/tests/negative/        deliberately insecure Terraform — Checkov must flag it
.github/workflows/           ai-gates.yml · iac.yml · release.yml
```

### Not covered yet

- Bias / disparate-outcome evals (flagged as open in the impact assessment)
- Runtime guardrails (Bedrock Guardrails) and production monitoring/drift
- Kubernetes admission policy requiring the ML-BOM attestation (extend `hardened-base/examples/admission/kyverno-cosign-policy.yaml`)
