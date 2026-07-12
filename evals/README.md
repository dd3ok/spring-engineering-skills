# Evaluation Contracts

`routing-cases.json` checks semantic ownership and reference-routing specification drift. `expected_refs` is the exact allowed reference set at the routing checkpoint encoded by each prompt; every unlisted reference is implicitly forbidden, while `forbidden_refs` records the explicit negative partition for dedicated skills and highlights important review boundaries. Re-evaluate routing when repository or runtime evidence adds a stack signal; the Kafka evidence cases demonstrate this second checkpoint. `review-routing-policy.json` pins the review route union and requires case coverage for every route. These contracts do not test model behavior or actual load traces.

`behavior-cases.json` contains raw prompts plus a parent-side rubric. For a forward test, give a fresh agent only the named skill directory and `prompt`; do not expose `must` or `must_not`. Score the returned answer afterward for evidence restraint, non-overlap, and unsafe-action avoidance. A behavior case passing once is a smoke test, not a statistical quality claim.

Host runtimes differ in discovery and activation. Test semantic routing and named selection separately, and record host behavior as an observation rather than a portable skill guarantee.

`source-publisher-policy.json` is the default-deny registry for URLs in `*sources.md`. Direct publisher/project/standards documentation and explicitly classified supporting authorities are separate lists; GitHub links additionally require an approved project owner.

Run `python scripts/validate_behavior_cases.py` to validate case structure and skill coverage.
