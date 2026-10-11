# AI governance policy gate.
#
# Evaluated with:
#   conftest test --combine ai-system.yaml models/registry.yaml \
#     --policy policy --data policy/data
#
# --combine passes every file as one input array of {path, contents}, so the
# system declaration can be checked against the registry in a single query.
# Package is `main` so conftest evaluates it without --namespace.
package main

import rego.v1

system_doc := [f.contents | some f in input; endswith(f.path, "ai-system.yaml")][0]

registry := {m.id: m | some f in input; endswith(f.path, "registry.yaml"); some m in f.contents.models}

risk_rank := {"low": 1, "moderate": 2, "high-impact": 3}

required_system_fields := {"id", "owner", "use_case", "risk_tier"}

required_registry_fields := {"owner", "status", "approved_by", "max_risk_tier", "model_card", "review_by"}

# ── Inventory: the system itself is registered with an owner and risk tier ────

deny contains msg if {
	some field in required_system_fields
	not system_doc.system[field]
	msg := sprintf("ai-system.yaml: system.%s is required", [field])
}

deny contains msg if {
	tier := system_doc.system.risk_tier
	not risk_rank[tier]
	msg := sprintf("ai-system.yaml: risk_tier %q must be one of %v", [tier, object.keys(risk_rank)])
}

# ── Registration: every model in use is in the registry and approved ──────────

deny contains msg if {
	some m in system_doc.models
	not registry[m.id]
	msg := sprintf("model %q is not in models/registry.yaml — register it before use", [m.id])
}

deny contains msg if {
	some m in system_doc.models
	entry := registry[m.id]
	entry.status != "approved"
	msg := sprintf("model %q has registry status %q, not approved", [m.id, entry.status])
}

deny contains msg if {
	some id, entry in registry
	some field in required_registry_fields
	not entry[field]
	msg := sprintf("registry entry %q is missing %s", [id, field])
}

deny contains msg if {
	some m in system_doc.models
	entry := registry[m.id]
	risk_rank[system_doc.system.risk_tier] > risk_rank[entry.max_risk_tier]
	msg := sprintf(
		"model %q is cleared up to %s but the system is %s",
		[m.id, entry.max_risk_tier, system_doc.system.risk_tier],
	)
}

deny contains msg if {
	some m in system_doc.models
	entry := registry[m.id]
	entry.provider != m.provider
	msg := sprintf("model %q: system says provider %q, registry says %q", [m.id, m.provider, entry.provider])
}

# Registry approvals expire; today is injected by CI via --data (policy/data/today.yaml).
deny contains msg if {
	some m in system_doc.models
	entry := registry[m.id]
	data.today > sprintf("%v", [entry.review_by])
	msg := sprintf("model %q registry approval expired on %v — re-review required", [m.id, entry.review_by])
}

# ── Provider allowlist: only authorized providers and regions ─────────────────

deny contains msg if {
	some m in system_doc.models
	not data.approved_providers[m.provider]
	msg := sprintf("provider %q is not an approved AI provider", [m.provider])
}

deny contains msg if {
	some m in system_doc.models
	allowed := data.approved_providers[m.provider].regions
	not m.region in allowed
	msg := sprintf("provider %q is not approved in region %q", [m.provider, m.region])
}

# ── High-impact AI (OMB M-25-21): impact assessment and human oversight ───────

deny contains msg if {
	system_doc.system.risk_tier == "high-impact"
	not system_doc.system.impact_assessment
	msg := "high-impact system must reference an AI impact assessment"
}

deny contains msg if {
	system_doc.system.risk_tier == "high-impact"
	not system_doc.system.human_oversight.approver_team
	msg := "high-impact system must name a human_oversight.approver_team"
}

# ── Data governance: declared data must be PII-free unless explicitly handled ─

deny contains msg if {
	some d in system_doc.data_sources
	d.contains_pii == true
	not d.pii_handling
	msg := sprintf("data source %q contains PII but declares no pii_handling", [d.path])
}
