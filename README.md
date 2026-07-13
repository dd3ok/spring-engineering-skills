# Spring Engineering Skills

Focused, vendor-neutral [Agent Skills](https://agentskills.io/specification) for evidence-led Spring and Spring Boot engineering. The suite covers Spring best-practice reviews, repository evidence, upgrades, performance, security, testing, and Modulith boundaries without bundling everything into one oversized skill.

Current release: **0.2.0 (public beta)** · [한국어](README.ko.md) · [Changelog](CHANGELOG.md)

## Why this suite

- **Focused ownership** — each skill owns one workflow and one primary output.
- **Evidence before conclusions** — findings separate observed facts, inferences, and unresolved gaps.
- **Version-aware guidance** — compatibility and migration claims require exact targets and reviewed sources.
- **Progressive disclosure** — agents load the core workflow first and only the references needed for the task.
- **Safe automation** — deterministic scripts are bounded, standard-library only, and do not silently execute repository builds.

## Choose a skill

| Skill | Use it for | Primary output |
| --- | --- | --- |
| [`spring-engineering-review`](skills/spring-engineering-review/) | Static Spring/Spring Boot code, configuration, dependency, architecture, security, data, messaging, and production-readiness reviews | Evidence-ranked findings and remediations |
| [`spring-evidence-collector`](skills/spring-evidence-collector/) | Read-only, redacted inventory of build files, versions, configuration keys, modules, source/test signals, and deployment artifacts | Deterministic `spring-evidence/1` JSON |
| [`spring-upgrade-planner`](skills/spring-upgrade-planner/) | Evidence-backed Spring Boot, Spring Cloud, Java/Kotlin, Maven, and Gradle migration planning | Staged `spring-upgrade-plan/2` with gates and rollback |
| [`spring-performance-investigator`](skills/spring-performance-investigator/) | Diagnosis from JFR, metrics, traces, profiles, logs, and controlled experiments | Ranked hypotheses and confirmed bottlenecks |
| [`spring-security-threat-modeler`](skills/spring-security-threat-modeler/) | Trust boundaries, abuse paths, and security controls across HTTP, reactive, messaging, data, management, and outbound surfaces | Threat register and testable acceptance criteria |
| [`spring-test-gap-planner`](skills/spring-test-gap-planner/) | Mapping operational risks and change signals to missing tests | Prioritized test-gap matrix |
| [`spring-modulith-auditor`](skills/spring-modulith-auditor/) | Application-module boundaries, cycles, exposed internals, events, module tests, and observability | Boundary violations and staged refactoring plan |

The skills are peers, not a dispatcher hierarchy. Install the skills you need; a compatible host may select one from its `name` and `description`. Use the exact skill name when the request is ambiguous or deterministic selection matters.

## How outputs work

All seven skills return structured results in the agent's normal response. Activating a skill does not by itself authorize writing a file to the workspace.

Only two skills additionally define canonical, versioned JSON artifacts and bundled validators:

- `spring-evidence-collector` can save portable, redacted repository facts as `spring-evidence/1` so another review or plan can reuse the same verified input.
- `spring-upgrade-planner` can save `spring-upgrade-plan/2` so evidence binding, stages, compatibility gates, verification, and rollback can be checked consistently.

The other five skills produce context-dependent findings, hypotheses, threat models, test matrices, or audit results. A fixed file schema would make those workflows unnecessarily rigid. They can still save Markdown or JSON when requested, but no canonical artifact is created by default.

## Quick start

Clone the repository:

```text
git clone https://github.com/dd3ok/spring-engineering-skills.git
```

Install a skill by copying its complete `skills/<skill-name>/` directory to a skill location supported by your host. Keep its `SKILL.md`, `LICENSE`, `references/`, and optional `scripts/` together. To install the full suite, copy all seven skill directories.

Example requests:

```text
Use spring-engineering-review to review this Spring Boot service for production readiness.
Use spring-evidence-collector to create a redacted static inventory of this repository.
Use spring-upgrade-planner to plan an evidence-backed upgrade from Spring Boot 3.5 to 4.1.
Use spring-performance-investigator to analyze these JFR and Micrometer artifacts.
```

Ordinary Spring questions, isolated code fixes, CVE lookups, and unconstrained architecture brainstorming should not activate this suite automatically.

## Evidence-first workflow

For repository-wide reviews or upgrades, start with a static evidence pack:

```text
python skills/spring-evidence-collector/scripts/collect_evidence.py <repository> --output evidence.json
python skills/spring-evidence-collector/scripts/validate_evidence.py evidence.json
```

The collector does not run Maven or Gradle, resolve dependencies, access the network, or emit configuration values. Executable build logic and effective dependency state require separately authorized evidence from a controlled environment.

When a saved handoff is requested, the collector and planner create separate, machine-readable JSON artifacts:

| File | Created by | Purpose |
| --- | --- | --- |
| `evidence.json` | `spring-evidence-collector` | Records the repository facts available to later reviews or plans. |
| `upgrade-plan.json` | `spring-upgrade-planner` | Builds a staged upgrade draft from `evidence.json` and an exact target version. |

The planner reads but does not replace the evidence file. These artifacts are not prose reports, and neither file is written merely because a skill was selected. An agent can summarize them into Markdown when requested.

Create and validate an upgrade-plan draft from evidence:

```text
python skills/spring-upgrade-planner/scripts/build_plan_skeleton.py evidence.json --target 4.1.0 --output upgrade-plan.json
python skills/spring-upgrade-planner/scripts/validate_upgrade_plan.py upgrade-plan.json
```

Targets must be exact. Plans remain `draft` until compatibility, migration, verification, rollback, freshness, and content-addressed source evidence satisfy the ready-state contract.

## Validate the repository

Deterministic scripts require Python 3.12 or newer and use only the standard library.

```text
python scripts/validate_all.py
```

This checks skill structure, paths and references, source policy, routing and behavior contracts, schemas, unit tests, golden repository fixtures, and offline links. CI also runs Ruff and a Windows junction smoke test.

Network-dependent freshness checks are intentionally separate from required pull-request validation:

```text
python scripts/check_spring_cloud_policy.py --online
python scripts/check_links.py --online --json-report dist/link-report.json
```

Routing cases verify the repository contract, not a host's actual activation behavior. Repeated host-trace and blind behavior evaluation are documented in [`evals/README.md`](evals/README.md).

## Repository layout

```text
skills/       independently installable skills
evals/        routing, behavior, and source-policy contracts
scripts/      repository-wide validators and scorers
tests/        unit, adversarial, portability, and golden-fixture tests
```

Detailed Spring rules, schemas, and source maps stay inside the skill that owns them. The portable source tree contains no plugin manifest, marketplace package, or host-specific agent configuration.

## Compatibility

| Contract | Current value |
| --- | --- |
| Suite release | `0.2.0` (public beta) |
| Skill format | [Agent Skills specification](https://agentskills.io/specification) |
| Deterministic scripts | Python 3.12+ |
| Evidence artifact | `spring-evidence/1` |
| Upgrade-plan artifact | `spring-upgrade-plan/2` |
| Routing report | `spring-routing-eval/2` |

Before `1.0.0`, justified breaking changes to skill names or schemas increment the minor version; compatible fixes increment the patch version. See the [changelog](CHANGELOG.md) for release details.

## Contributing

Keep `SKILL.md` concise and procedural. Put detailed rules and sources in focused `references/` files, and add scripts only where deterministic behavior materially improves safety or repeatability. New routes, schemas, source publishers, and failure modes require corresponding contract or regression tests.

Run before opening a pull request:

```text
python scripts/validate_all.py
python -m ruff check scripts tests skills
```

## License

Licensed under the [Apache License 2.0](LICENSE). Each independently distributable skill carries the same license file.
