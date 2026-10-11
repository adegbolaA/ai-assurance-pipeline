# Unit tests for the policy gate — run with `conftest verify --policy policy`.
# Each test proves one rule fires (negative control) so a passing gate means
# the rules ran, not that they silently matched nothing.
package main

import rego.v1

good_system := {
	"system": {
		"id": "s",
		"owner": "o",
		"use_case": "u",
		"risk_tier": "high-impact",
		"impact_assessment": "docs/ia.md",
		"human_oversight": {"approver_team": "board"},
	},
	"models": [{"id": "m1", "provider": "aws-bedrock", "region": "us-east-1"}],
	"data_sources": [{"path": "d", "contains_pii": false}],
}

good_registry := {"models": [{
	"id": "m1",
	"provider": "aws-bedrock",
	"status": "approved",
	"owner": "o",
	"approved_by": "board",
	"max_risk_tier": "high-impact",
	"model_card": "c.md",
	"review_by": "2099-01-01",
}]}

providers := {"aws-bedrock": {"regions": ["us-east-1"]}}

inputs(sys, reg) := [
	{"path": "ai-system.yaml", "contents": sys},
	{"path": "models/registry.yaml", "contents": reg},
]

run(sys, reg) := result if {
	result := deny with input as inputs(sys, reg)
		with data.approved_providers as providers
		with data.today as "2026-10-10"
}

test_compliant_system_passes if {
	count(run(good_system, good_registry)) == 0
}

test_unregistered_model_denied if {
	sys := json.patch(good_system, [{"op": "replace", "path": "/models/0/id", "value": "rogue-model"}])
	some msg in run(sys, good_registry)
	contains(msg, "not in models/registry.yaml")
}

test_unapproved_model_denied if {
	reg := json.patch(good_registry, [{"op": "replace", "path": "/models/0/status", "value": "pending"}])
	some msg in run(good_system, reg)
	contains(msg, "not approved")
}

test_unapproved_provider_denied if {
	sys := json.patch(good_system, [{"op": "replace", "path": "/models/0/provider", "value": "random-saas"}])
	reg := json.patch(good_registry, [{"op": "replace", "path": "/models/0/provider", "value": "random-saas"}])
	some msg in run(sys, reg)
	contains(msg, "not an approved AI provider")
}

test_unapproved_region_denied if {
	sys := json.patch(good_system, [{"op": "replace", "path": "/models/0/region", "value": "eu-west-1"}])
	some msg in run(sys, good_registry)
	contains(msg, "not approved in region")
}

test_model_not_cleared_for_tier_denied if {
	reg := json.patch(good_registry, [{"op": "replace", "path": "/models/0/max_risk_tier", "value": "moderate"}])
	some msg in run(good_system, reg)
	contains(msg, "is cleared up to moderate")
}

test_expired_approval_denied if {
	reg := json.patch(good_registry, [{"op": "replace", "path": "/models/0/review_by", "value": "2026-01-01"}])
	some msg in run(good_system, reg)
	contains(msg, "approval expired")
}

test_high_impact_without_oversight_denied if {
	sys := json.patch(good_system, [{"op": "remove", "path": "/system/human_oversight"}])
	some msg in run(sys, good_registry)
	contains(msg, "approver_team")
}

test_missing_risk_tier_denied if {
	sys := json.patch(good_system, [{"op": "remove", "path": "/system/risk_tier"}])
	some msg in run(sys, good_registry)
	contains(msg, "system.risk_tier is required")
}

test_pii_without_handling_denied if {
	sys := json.patch(good_system, [{"op": "replace", "path": "/data_sources/0/contains_pii", "value": true}])
	some msg in run(sys, good_registry)
	contains(msg, "declares no pii_handling")
}
