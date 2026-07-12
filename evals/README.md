# Evaluation Contracts

`routing-cases.json` checks semantic ownership and reference-routing specification drift. For review cases, `expected_refs` is the exact allowed reference union derived from `review_routes`; every unlisted review reference is implicitly forbidden, while `forbidden_refs` highlights important negative boundaries. `review-routing-policy.json` pins the route union and requires case coverage for every route. Non-review cases use `expected_refs` as required additive loads. These contracts do not test model behavior or actual load traces.

`behavior-cases.json` contains raw prompts plus a parent-side rubric. For a forward test, give a fresh agent only the named skill directory and `prompt`; do not expose `must` or `must_not`. Score the returned answer afterward for evidence restraint, non-overlap, and unsafe-action avoidance. A behavior case passing once is a smoke test, not a statistical quality claim.

Host runtimes differ in discovery and activation. Test semantic routing and named selection separately, and record host behavior as an observation rather than a portable skill guarantee.

Run `python scripts/validate_behavior_cases.py` to validate case structure and skill coverage.
