# Evaluation Contracts

`routing-cases.json` checks semantic ownership and reference-routing specification drift. `expected_refs` is the exact allowed reference set at the routing checkpoint encoded by each prompt; every unlisted reference is implicitly forbidden, while `forbidden_refs` records the explicit negative partition for dedicated skills and highlights important review boundaries. Re-evaluate routing when repository or runtime evidence adds a stack signal; the Kafka evidence cases demonstrate this second checkpoint. `review-routing-policy.json` pins the review route union and requires case coverage for every route. These contracts do not test model behavior or actual load traces.

`behavior-cases.json` contains raw prompts plus a parent-side rubric. For a forward test, give a fresh agent only the named skill directory and `prompt`; do not expose `must` or `must_not`. Score the returned answer afterward for evidence restraint, non-overlap, and unsafe-action avoidance. A behavior case passing once is a smoke test, not a statistical quality claim.

Host runtimes differ in discovery and activation. Test semantic routing and named selection separately, and record host behavior as an observation rather than a portable skill guarantee.

## Observed Model Routing

Installed skills expose their `name` and `description` metadata to a supporting host. A host may choose a matching skill implicitly; exact-name invocation remains the deterministic option when a task is ambiguous or the workflow is high risk. This repository has seven peer skills and no umbrella dispatcher skill.

Export prompts without leaking expected routes:

```text
python scripts/score_routing_results.py --emit-prompts dist/routing-prompts.jsonl
```

Run each prompt in a fresh task with all seven skills installed. Record the skill selected by the host's trace or skill-activation signal, not a textual guess in the model answer. Use `null` when no skill was selected:

```json
{"case_id":"broad-review","selected_skill":"spring-best-practice-review","host":"codex","model":"record-the-observed-model"}
{"case_id":"ordinary-spring-question","selected_skill":null,"host":"codex","model":"record-the-observed-model"}
{"case_id":"korean-compound-evidence-first","selected_skill":"spring-evidence-collector","handoff_skills":["spring-best-practice-review"],"host":"codex","model":"record-the-observed-model"}
```

`selected_skill` is the initial owner used for routing accuracy. Record later peer-skill transitions in the optional `handoff_skills` array. Store one JSON object per line, then score the run:

```text
python scripts/score_routing_results.py dist/routing-results.jsonl --json-report dist/routing-report.json
```

The report measures overall and per-channel accuracy, false activations, missed activations, and wrong-skill selections. Add `--strict` only when every mismatch should produce a failing exit code. Add `--allow-partial` for a deliberately sampled smoke test. Live model calls and credentials are intentionally outside the required CI path.

`source-publisher-policy.json` is the default-deny registry for URLs in `*sources.md`. Direct publisher/project/standards documentation and explicitly classified supporting authorities are separate lists; GitHub links additionally require an approved project owner.

Run `python scripts/validate_behavior_cases.py` to validate case structure and skill coverage.
