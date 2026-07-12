# Spring Engineering Skills

A vendor-neutral, evidence-driven suite of focused Agent Skills for Spring engineering. Each directory under `skills/` is an independent, portable skill with only skill-local references and scripts.

## Skills

| Skill | Job | Primary output |
| --- | --- | --- |
| `spring-evidence-collector` | Read-only, redacted repository inventory | Deterministic `spring-evidence/1` JSON |
| `spring-upgrade-planner` | Spring/Java/build-tool migration planning | Compatibility gates and staged upgrade plan |
| `spring-best-practice-review` | Broad or focused static Spring review | Evidence-ranked findings and remediation |
| `spring-performance-investigator` | Runtime performance diagnosis | Ranked hypotheses, confirmed bottlenecks, and controlled experiments |
| `spring-security-threat-modeler` | Trust-boundary and abuse-path analysis | Threat register and testable security acceptance criteria |
| `spring-test-gap-planner` | Risk-to-test evidence analysis | Prioritized test-gap matrix |
| `spring-modulith-auditor` | Application-module boundary audit | Dependency violations and refactor stages |

Each skill owns a distinct depth and output. The broad review flags static design risks; the dedicated skills own evidence collection, upgrade-plan creation, runtime diagnosis, threat models, test backlogs, and module graphs.

## Layout

```text
skills/<skill-name>/
  SKILL.md
  references/
  scripts/              # only when deterministic automation helps
evals/
scripts/
tests/
```

No plugin manifest, marketplace metadata, host-specific agent metadata, or generated vendor package is part of the source contract.

## Use

Select a skill through the host's supported skill mechanism or request it by exact name. Discovery and invocation syntax are host concerns and are intentionally not encoded in these skills.

```text
Use spring-evidence-collector to collect a safe inventory of this repository.
Use spring-upgrade-planner to plan a Spring Boot 3.5 to 4.1 upgrade.
Use spring-best-practice-review to review this service for production readiness.
```

To install one skill, copy its complete `skills/<skill-name>/` directory into a skill location supported by the target host. Do not split its `SKILL.md`, `references/`, or `scripts/` across locations.

## Python runtime

The deterministic scripts require Python 3.12 or newer. They use only the standard library.

## Evidence collector

Static collection never runs a build or network request and never emits configuration values:

```text
python skills/spring-evidence-collector/scripts/collect_evidence.py <repository> --output evidence.json
python skills/spring-evidence-collector/scripts/validate_evidence.py evidence.json
```

Maven inheritance/profiles and executable Gradle logic require effective or resolved reports produced in a separately controlled environment. Static declarations remain `declared` or `inferred`.

## Upgrade planner

Create a deterministic draft from evidence and an exact target:

```text
python skills/spring-upgrade-planner/scripts/build_plan_skeleton.py evidence.json --target 4.1.0 --output upgrade-plan.json
python skills/spring-upgrade-planner/scripts/validate_upgrade_plan.py upgrade-plan.json
```

The plan stays `draft` until official support, compatibility, migration, verification, rollback, and content-addressed source evidence are attached. `latest` is not inferred without pinned metadata, and downgrades require explicit opt-in.

## Validation

```text
python scripts/validate_all.py
```

This vendor-neutral command checks skill structure and source policy, routing and behavior contracts, all unit tests, and offline links. Run the individual scripts under `scripts/` when isolating a failure.

External sources can be checked separately:

```text
python scripts/check_links.py --online --json-report dist/link-report.json
```

## Source policy

Re-check version-sensitive claims. Prefer official Spring and dependency documentation, release notes, migration guides, BOMs, specifications, and project repositories; use canonical research or major engineering publications as supporting material. Do not use a blog post as the sole source for framework semantics.

The repository structure follows the [Agent Skills specification](https://agentskills.io/specification). Technical source maps live inside each skill so the skill remains portable. Behavior prompts and blind forward-test scoring rules are documented in [evals/README.md](evals/README.md).

## Migration from the former single skill

- The broad review moved from root `SKILL.md` to `skills/spring-best-practice-review/`.
- Specialized workflows moved into sibling skill directories under `skills/`.
- Host-specific plugin, marketplace, and agent metadata are intentionally unsupported.
