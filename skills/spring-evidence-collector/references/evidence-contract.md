# Evidence Contract

## Trust and provenance

- Assign every fact a source path and collection method.
- Use certainty in descending order: `resolved`, `effective`, `declared`, `inferred`. Static collection emits only `declared` and `inferred`. An imported report is eligible for `effective` or `resolved` only when the user identifies an authorized producer and controlled environment; producer, tool/version, exact command/settings, collection time/time zone, environment and project identity, sanitization, and fact-level source locator are complete; and sanitization did not remove the field that determines the fact. Otherwise keep the fact `inferred` and record a provenance gap.
- Use `effective` only for a build-tool report that evaluated the applicable project, profiles, and configuration. Use `resolved` only for a completed dependency/runtime resolution whose scope and environment match the claimed fact. These certainty labels describe evidence derivation, not truth or safety; conflicting facts remain conflicts.
- `static` collection permits only `declared` and `inferred` facts and has null imported provenance. `imported-resolved` requires producer, tool/version, a credential-free sanitized command or settings template, a valid non-future UTC collection time, environment and project identity, and structured sanitization metadata with `status: sanitized`, `configuration_values_omitted: true`, and `determinative_fields_preserved: true` before an `effective` or `resolved` fact is accepted. Never place a raw credential, tokenized URL, or control character in provenance. Confirmed Spring Cloud non-use is a `platform.usage / spring-cloud / not-used` fact with `effective` or `resolved` certainty; absence from a static scan is only unknown.
- Preserve uncertainty. Static parsing cannot reproduce Maven inheritance, active profiles, Gradle configuration logic, dependency substitution, or runtime property precedence.
- A version-catalog entry is a declaration, not proof of use. Emit a Spring Boot platform hint only when a matching, uncommented `alias(libs.plugins...)` application without `apply false` is observed in a project `plugins` block, and keep that hint `inferred`.
- A Maven build-plugin version is not the Spring Boot runtime/BOM version. Keep plugin declarations separate from platform evidence.

## Minimum schema

The JSON Schema selected by `SKILL.md` owns the interoperability shape. The bundled semantic validator remains authoritative for redaction, provenance, and cross-field invariants that JSON Schema cannot express.

- `schema_version`: collector output contract version.
- `repository.root`: always `.`; output never embeds the host absolute path.
- `collection`: collector version, mode, and explicit network/build-execution flags.
- `projects`: build-system, descriptor, and module topology.
- `facts`: stable-hash facts with project, kind, name, value, certainty, and relative source locator.
- `conflicts`: incompatible version facts preserved with their fact IDs.
- `gaps`: skipped or unresolved evidence with a reason and relative path.
- `redaction`: configuration-value omission and environment-read flags.

## Redaction

Never emit property values. Skip likely secret-bearing files and linked/junction paths entirely. A key name may be evidence, but its value is not required for repository topology. Actuator `/env` and `/configprops` can expose sensitive data and are outside default static collection.

## Follow-up evidence

Build wrappers, build files, plugins, dependency resolution, and even reporting tasks can execute untrusted code. A request that initially asks for both collection and execution is not separate authorization. First show an execution plan with the exact wrapper command and arguments, working directory, purpose, wrapper-integrity check, disposable isolation, removed credentials/environment, isolated user/build homes, deny-by-default network and any narrowly required exception, filesystem limits, timeout, output limit, and redaction. Execute only after fresh explicit authorization for that exact plan. Never recommend arbitrary or custom tasks; if the controls cannot be met, ask for a sanitized report generated in a controlled environment.

Candidate reports, to recommend rather than silently execute, are:

- Maven Wrapper: `./mvnw help:effective-pom` and `./mvnw dependency:tree`.
- Gradle Wrapper: `./gradlew dependencies`, scoped `dependencyInsight`, and relevant build-environment reports.
- Spring Boot: sanitized conditions/configuration reports in an access-controlled environment.

Treat imported reports as untrusted. Record their producer, tool and version, collection time and time zone, environment identity, command or settings, and sanitization status when available; otherwise report the missing provenance as a gap. A supplied checksum can preserve artifact identity but does not establish trust.
