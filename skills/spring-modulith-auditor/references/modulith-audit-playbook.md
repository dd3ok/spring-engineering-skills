# Modulith Audit Playbook

## Boundary checks

- Candidate modules align with business capabilities and a stable root package.
- Record the application root, additional packages, fully qualified module names, and the default, explicit, or custom module-detection strategy before building the graph.
- Public APIs are intentional; internal packages are not imported across modules.
- Module dependency graph is acyclic or every exception has an explicit migration plan.
- Distinguish closed modules from `ApplicationModule.Type.OPEN`; open modules relax internal-access enforcement and cycle verification, so a generic package graph is not equivalent to `ApplicationModules` output.
- Allowed dependencies and named interfaces reflect actual contracts.
- Data ownership is clear; cross-module writes and cross-aggregate transactions are justified.
- Events have owners, schemas, compatibility rules, idempotency, ordering, failure recovery, and observability.
- Module tests cover exposed behavior and permitted collaborators without silently booting the entire application.

## Spring Modulith evidence

When the dependency is present, prefer executable evidence from `ApplicationModules.of(...).verify()` or `detectViolations()` in a test. Verification checks module cycles, access through API packages, and configured allowed dependencies. Record module-detection customization, open/closed module semantics, custom verification options, and ignored violations; ensure test discovery matches production discovery.

The event publication registry can make transactional listener publication durable, but it is not an exactly-once guarantee. Listener idempotency, unfinished publications, retry/resubmission policy, ordering, cleanup, storage growth, and version compatibility remain operational concerns.

Runtime verification is opt-in. Assess startup-failure impact before enabling it outside tests.

## Refactor order

1. Document current modules and exceptions.
2. Add verification tests without broad behavior changes.
3. Seal internal APIs and introduce explicit interfaces.
4. Break cycles with ownership changes or stable contracts.
5. Change data/event boundaries with compatibility and rollout plans.
