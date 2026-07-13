# Evaluation Contracts

`routing-cases.json` checks semantic ownership and reference-routing specification drift. `expected_refs` is the exact allowed reference set at the routing checkpoint encoded by each prompt; every unlisted reference is implicitly forbidden, while `forbidden_refs` records the explicit negative partition for dedicated skills and highlights important review boundaries. Fixed `train` and `validation` splits cover every skill and non-activation cases. Re-evaluate routing when repository or runtime evidence adds a stack signal; the Kafka evidence cases demonstrate this second checkpoint. `review-routing-policy.json` pins the review route union and requires case coverage for every route. These contracts do not test model behavior or actual load traces.

`behavior-cases.json` contains raw prompts plus a parent-side rubric. For a forward test, give a fresh agent only the named skill directory and `prompt`; do not expose `must` or `must_not`. Score the returned answer afterward for evidence restraint, non-overlap, and unsafe-action avoidance. A behavior case passing once is a smoke test, not a statistical quality claim.

For `repository-fixture` cases, copy the declared `fixture_path` to a fresh temporary workspace and run the agent there. Preserve both trees for grading, then bind the actual file changes to the result with the standard-library capture tool:

```text
python scripts/capture_behavior_artifact.py --case-id <case-id> --fixture <fixture-path> --workspace <workspace-path> --output <manifest.json>
```

The independent grader receives the raw response, fixture, resulting workspace, and manifest. Copy `workspace_diff_sha256` and `changed_paths` from the manifest into the result record. A `with-skill` repository-fixture run is invalid when `changed_paths` is empty; a baseline run may record an empty diff. Keep manifests and workspaces outside Git and do not expose them to later generation runs.

The behavior suite includes Korean prompts for evidence restraint, threat modeling, upgrade ambiguity, and bounded implementation. A Korean prompt declares `response_language: ko` and includes a Korean-response rubric item. Keep at least two such cases so localized output behavior does not silently fall out of the contract.

Host runtimes differ in discovery and activation. Test semantic routing and named selection separately, and record host behavior as an observation rather than a portable skill guarantee.

The 0.1.0 pre-release used 12 fresh Codex/GPT-5 tasks as a one-pass route-label classification smoke: eight single-skill requests, two non-activation requests, and two evidence-first handoffs. All 12 self-reported the intended label after the expected label was withheld; three fresh checks after the final description edit also matched. The compact [observation record](route-label-smoke-2026-07-12.json) preserves the expected and observed labels. This is useful rename and boundary evidence, but it is not a host activation trace, a repeated statistical evaluation, or a portable accuracy guarantee.

## Observed Model Routing

Installed skills expose their `name` and `description` metadata to a supporting host. A host may choose a matching skill implicitly; exact-name invocation remains the deterministic option when a task is ambiguous or the workflow is high risk. This repository has eight peer skills and no umbrella dispatcher skill.

Export prompts without leaking expected routes:

```text
python scripts/score_routing_results.py --emit-prompts dist/routing-prompts.jsonl
```

Run each prompt three times in a fresh task with all eight skills installed. Record the skill selected by the host's trace or skill-activation signal, not a textual guess in the model answer. Use `null` when no skill was selected:

```json
{"case_id":"broad-review","run_id":"run-1","selected_skill":"spring-engineering-review","host":"codex","host_version":"record-version","model":"record-model","skill_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","observation_kind":"host-activation-trace","trace_id":"host-trace-1"}
{"case_id":"ordinary-spring-question","run_id":"run-1","selected_skill":null,"host":"codex","host_version":"record-version","model":"record-model","skill_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","observation_kind":"host-activation-trace","trace_id":"host-trace-2"}
```

`selected_skill` is the initial owner used for routing accuracy. Record later peer-skill transitions in the optional `handoff_skills` array. Store one JSON object per line, then score the run:

```text
python scripts/score_routing_results.py dist/routing-results.jsonl --expected-runs 3 --strict --json-report dist/routing-report.json
```

The report measures per-run and per-case accuracy, train/validation and channel results, false activations, missed activations, and wrong-skill selections. A case passes when more than half of its runs select the expected route. `--strict` is the release gate and requires the canonical case suite plus at least three complete, traced runs per case; it cannot be combined with `--allow-partial`, which is only for a deliberately sampled smoke test. The release target is 100% exact-name selection, at least 90% validation accuracy, at most 5% false activation, and at most 10% missed activation; report these as observations for the recorded host, model, and commit rather than portable guarantees. Live model calls and credentials are intentionally outside required CI.

For output evaluation, run each `behavior-cases.json` prompt without exposing its rubric. Store raw outputs outside Git, record their SHA-256 hashes, and have an independent grader produce a JSONL manifest. Score three with-skill runs and one without-skill baseline per case:

```json
{"case_id":"review-web-security","run_id":"with-1","condition":"with-skill","host":"codex","host_version":"record-version","model":"record-model","skill_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","trace_id":"unique-generation-trace","output_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","grader_kind":"independent-model","must_results":["pass"],"must_not_results":["pass"]}
```

Repository-fixture results additionally bind a non-empty workspace change:

```json
{"case_id":"korean-existing-application-fix","run_id":"with-1","condition":"with-skill","host":"codex","host_version":"record-version","model":"record-model","skill_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","trace_id":"unique-generation-trace","output_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","workspace_diff_sha256":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","changed_paths":["src/main/java/com/example/orders/OrderBatchService.java","src/test/java/com/example/orders/OrderBatchServiceTest.java"],"grader_kind":"independent-model","must_results":["pass"],"must_not_results":["pass"]}
```

```text
python scripts/score_behavior_results.py dist/behavior-results.jsonl --strict --json-report dist/behavior-report.json
```

Only `with-skill` runs contribute to the release score; `without-skill` is a separately reported comparison baseline. The release gate requires the canonical rubric suite, at least 95% global and 90% per-skill `must` pass rates, zero failed or unclear `must_not` grades, and no `must` criterion that is non-passing in a majority of repeated runs. Custom case files remain available for non-strict experiments. A grader result is evidence only for the recorded output, host, model, commit, and rubric; it is not a deterministic unit test.

`source-publisher-policy.json` is the default-deny registry for URLs in `*sources.md`. Direct publisher/project/standards documentation and explicitly classified supporting authorities are separate lists; GitHub links additionally require an approved project owner.

`spring-project-lifecycle.json` binds active and Attic claims to exact consumer text and exact official project links. Offline validation checks the consumer bindings; the scheduled online check parses project anchors on the official Spring projects page. Source review dates use the UTC calendar date so local and CI freshness decisions agree.

Run `python scripts/validate_behavior_cases.py` to validate case structure and skill coverage.
