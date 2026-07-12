from __future__ import annotations

import copy
import importlib.util
import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module(
    "spring_upgrade_builder",
    ROOT / "skills" / "spring-upgrade-planner" / "scripts" / "build_plan_skeleton.py",
)
validator = load_module(
    "spring_upgrade_validator",
    ROOT / "skills" / "spring-upgrade-planner" / "scripts" / "validate_upgrade_plan.py",
)


class UpgradePlannerTests(unittest.TestCase):
    def test_python_runtime_floor_is_enforced(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Python 3.12"):
            validator.require_supported_python((3, 11))
        builder.require_supported_python((3, 12))

    def test_invalid_static_execution_flags_are_rejected(self) -> None:
        evidence = {
            "schema_version": "spring-evidence/1", "repository": {"root": "."},
            "collection": {"mode": "static", "network_used": True, "build_executed": True},
            "projects": [], "facts": [], "conflicts": [], "gaps": [],
            "redaction": {"configuration_values_omitted": True, "environment_read": False},
        }
        self.assertTrue(any("execution flags" in error for error in builder.validate_evidence_input(evidence)))
        evidence["password"] = "actual-secret-value"
        self.assertTrue(any("unknown top-level" in error for error in builder.validate_evidence_input(evidence)))
        evidence.pop("password")
        evidence["collection"]["collector_version"] = ""
        self.assertTrue(any("collector_version" in error for error in builder.validate_evidence_input(evidence)))

    def test_unknown_fact_metadata_is_rejected(self) -> None:
        fact = self.fact(
            project_id="project:.", kind="platform.version", name="spring-boot", value="3.5.2",
            certainty="declared", source={"type": "file", "path": "pom.xml"}, password="actual-secret",
        )
        evidence = {
            "schema_version": "spring-evidence/1", "repository": {"root": "."},
            "collection": {"collector_version": "test", "mode": "static", "network_used": False, "build_executed": False},
            "projects": [], "facts": [fact], "conflicts": [], "gaps": [],
            "redaction": {"configuration_values_omitted": True, "environment_read": False},
        }
        self.assertTrue(any("invalid fields" in error for error in builder.validate_evidence_input(evidence)))
        evidence["facts"] = []
        evidence["conflicts"] = [{"project_id": "project:.", "kind": "platform.version", "name": "spring-boot", "values": [], "fact_ids": [{}]}]
        self.assertTrue(any("conflicts" in error for error in builder.validate_evidence_input(evidence)))

    def test_empty_source_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = self.evidence_file(root, [])
            with self.assertRaisesRegex(ValueError, "source ids"):
                builder.build(evidence, "4.1.0", False, [""], False)

    def test_extreme_version_is_a_validation_error_not_an_exception(self) -> None:
        plan = {"schema_version": "spring-upgrade-plan/2", "status": "draft", "target": {"spring_boot": "9" * 5000 + ".0.0"}}
        errors = validator.validate(plan)
        self.assertTrue(errors)

    def test_non_string_input_source_id_is_rejected_without_crashing(self) -> None:
        plan = {"schema_version": "spring-upgrade-plan/2", "status": "draft", "input": {"evidence_sha256": "a" * 64, "source_snapshot_ids": [{}]}}
        self.assertTrue(validator.validate(plan))

    def test_official_locator_rejects_query_and_fragment(self) -> None:
        for suffix in ("?access_token=secret", "#fragment"):
            self.assertFalse(validator.valid_locator("https://spring.io/support-policy" + suffix))

    def test_snapshot_paths_are_portable_across_filesystems(self) -> None:
        self.assertTrue(validator.valid_snapshot_path("sources/support.snapshot"))
        for path in ("source.snapshot:ads", "CON", "NUL", "sources/file. ", "sources/file."):
            with self.subTest(path=path):
                self.assertFalse(validator.valid_snapshot_path(path))

    def test_malformed_ipv6_locator_is_a_validation_error_not_an_exception(self) -> None:
        for locator in ("https://[/", "https://[::1"):
            with self.subTest(locator=locator):
                self.assertFalse(validator.valid_locator(locator))
                plan = {
                    "schema_version": "spring-upgrade-plan/2", "status": "ready",
                    "input": {"evidence_sha256": "a" * 64, "target": "4.1.0", "source_snapshot_ids": ["source:x"]},
                    "current": {"spring_boot": "4.0.0", "spring_cloud": None, "evidence_ids": []},
                    "target": {"spring_boot": "4.1.0", "spring_cloud": None, "prerelease_allowed": False},
                    "policy": {"allow_downgrade": False},
                    "compatibility_gates": [], "hops": [], "automation": [],
                    "rollout": {"canary_signals": []}, "unresolved": [],
                    "source_ledger": [{
                        "id": "source:x", "kind": "pinned-source-copy", "locator": locator,
                        "publisher": "spring", "checked_version": "4.1.0", "checked_spring_cloud": None,
                        "subject": "spring-boot", "subject_version": "4.1.0",
                        "scope": "target-support", "applies_from": None, "applies_to": None,
                        "snapshot_path": "source.snapshot", "sha256": "a" * 64, "capture": None,
                    }],
                }
                errors = validator.validate(plan, Path.cwd())
                self.assertTrue(any("official publisher metadata" in error for error in errors))

    def test_unhashable_json_field_types_return_errors_instead_of_crashing(self) -> None:
        self.assertIsInstance(validator.validate({"status": []}), list)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = self.evidence_file(root, [])
            base = builder.build(evidence, "4.1.0", False, ["source:x"])
            mutations = (
                lambda plan: plan["source_ledger"][0].update(scope=[]),
                lambda plan: plan["source_ledger"][0].update(publisher={}),
                lambda plan: plan["compatibility_gates"][0].update(status=[]),
            )
            for mutate in mutations:
                plan = copy.deepcopy(base)
                mutate(plan)
                self.assertIsInstance(validator.validate(plan, root), list)

    def test_non_list_gate_source_ids_return_errors_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = self.evidence_file(root, [])
            plan = builder.build(evidence, "4.1.0", False, ["source:x"])
            plan["status"] = "ready"
            gate = next(item for item in plan["compatibility_gates"] if item["id"] == "gate:target-support")
            gate.update(status="pass", source_ids=1)

            errors = validator.validate(plan, root)

            self.assertTrue(any("gate source_ids are invalid: gate:target-support" in error for error in errors))

    def test_scope_aware_github_paths_allow_curated_official_release_notes(self) -> None:
        self.assertTrue(
            validator.approved_publisher_path(
                "spring-github", "github.com",
                "/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes",
                "release-notes",
            )
        )
        for path in (
            "/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes",
            "/spring-cloud/spring-cloud-release/wiki/Spring-Cloud-2025.1-Release-Notes",
            "/spring-projects/spring-boot/wiki/Unrelated",
        ):
            self.assertFalse(validator.approved_publisher_path("spring-github", "github.com", path, "release-notes"))

    def test_all_publishers_default_deny_unrelated_paths(self) -> None:
        self.assertTrue(
            validator.approved_publisher_path(
                "spring", "docs.spring.io", "/spring-boot/system-requirements.html", "system-requirements"
            )
        )
        self.assertFalse(
            validator.approved_publisher_path("spring", "spring.io", "/blog/upgrade-opinion", "target-support")
        )
        self.assertFalse(
            validator.approved_publisher_path("oracle", "docs.oracle.com", "/en/java/javase/25/docs/api/java.base/java/lang/String.html", "system-requirements")
        )
        allowed = (
            ("spring", "docs.spring.io", "/spring-boot/4.1/upgrading.html", "spring-upgrade-guide"),
            ("spring", "docs.spring.io", "/spring-boot/4.1/reference/using/build-systems.html", "build-system-guide"),
            ("oracle", "docs.oracle.com", "/en/java/javase/25/migrate/", "java-migration"),
            ("oracle", "www.oracle.com", "/java/technologies/java-se-support-roadmap.html", "java-migration"),
            ("openjdk", "openjdk.org", "/projects/jdk/25/", "java-migration"),
            ("maven", "maven.apache.org", "/docs/3.9.11/release-notes.html", "maven-reference"),
            ("gradle", "docs.gradle.org", "/9.1.0/release-notes.html", "gradle-reference"),
            ("openrewrite", "docs.openrewrite.org", "/recipes/java/spring", "rewrite-recipe"),
            ("openrewrite", "docs.openrewrite.org", "/reference/rewrite-maven-plugin", "automation-guide"),
            ("openrewrite", "docs.openrewrite.org", "/reference/gradle-plugin-configuration", "automation-guide"),
        )
        for publisher, host, path, scope in allowed:
            with self.subTest(publisher=publisher, scope=scope):
                self.assertTrue(validator.approved_publisher_path(publisher, host, path, scope))

    def test_locator_version_must_match_hop_target_line(self) -> None:
        self.assertTrue(
            validator.locator_matches_applicability(
                "/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes",
                "release-notes",
                "4.1.0",
            )
        )
        self.assertFalse(
            validator.locator_matches_applicability(
                "/spring-projects/spring-boot/wiki/Spring-Boot-2.0-Release-Notes",
                "release-notes",
                "4.1.0",
            )
        )

    def test_capture_manifest_is_bound_to_allowlisted_final_locator_and_hash(self) -> None:
        locator = "https://spring.io/support-policy"
        digest = "a" * 64
        check_time = datetime(2026, 7, 13, tzinfo=UTC)
        capture = {
            "method": "controlled-fetch", "captured_at": "2026-07-12T00:00:00Z",
            "captured_by": "test", "final_locator": "https://spring.io/support-policy/", "response_sha256": digest,
        }
        self.assertTrue(validator.valid_capture(capture, locator, "spring", "target-support", digest, now=check_time))
        capture["captured_at"] = "2026-99-99T99:99:99Z"
        self.assertFalse(validator.valid_capture(capture, locator, "spring", "target-support", digest, now=check_time))
        capture["captured_at"] = "2099-01-01T00:00:00Z"
        self.assertFalse(validator.valid_capture(capture, locator, "spring", "target-support", digest, now=check_time))
        capture["captured_at"] = "2020-01-01T00:00:00Z"
        self.assertFalse(validator.valid_capture(capture, locator, "spring", "target-support", digest, now=check_time))
        capture["captured_at"] = "2026-07-12T00:00:00Z"
        capture["final_locator"] = "https://spring.io/blog/unrelated"
        self.assertFalse(validator.valid_capture(capture, locator, "spring", "target-support", digest, now=check_time))
        wiki = "https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes"
        capture.update(
            captured_at="2020-01-01T00:00:00Z",
            final_locator=wiki,
        )
        self.assertFalse(
            validator.valid_capture(capture, wiki, "spring-github", "release-notes", digest, now=check_time)
        )

    def test_subject_version_is_bound_to_versioned_vendor_locator(self) -> None:
        self.assertTrue(validator.locator_matches_subject_version("/en/java/javase/25/migrate/", "java", "25"))
        self.assertFalse(validator.locator_matches_subject_version("/en/java/javase/17/migrate/", "java", "25"))
        self.assertTrue(validator.locator_matches_subject_version("/9.1.0/release-notes.html", "gradle", "9.1.0"))
        self.assertFalse(validator.locator_matches_subject_version("/8.14.3/release-notes.html", "gradle", "9.1.0"))
        self.assertTrue(validator.locator_matches_subject_version("/docs/3.9.11/release-notes.html", "maven", "3.9.11"))
        self.assertFalse(validator.locator_matches_subject_version("/docs/3.9.10/release-notes.html", "maven", "3.9.11"))
        self.assertIsNone(validator.SCOPE_SUBJECT.get("unknown-scope"))

    def fact(self, **values: object) -> dict[str, object]:
        fact = dict(values)
        fact["id"] = builder.expected_fact_id(fact)
        return fact

    def evidence_file(self, root: Path, facts: list[dict[str, object]]) -> Path:
        path = root / "evidence.json"
        data = {
            "schema_version": "spring-evidence/1",
            "repository": {"root": "."},
            "collection": {"collector_version": "test", "mode": "static", "network_used": False, "build_executed": False},
            "projects": [],
            "facts": facts,
            "conflicts": [],
            "gaps": [],
            "redaction": {"configuration_values_omitted": True, "environment_read": False},
        }
        path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        return path

    def test_draft_uses_strongest_boot_fact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.evidence_file(Path(directory), [
                self.fact(project_id="project:.", kind="platform.version", name="spring-boot", value="3.5.1", certainty="declared", source={"type": "file", "path": "pom.xml"}),
                self.fact(project_id="project:.", kind="platform.version", name="spring-boot", value="3.5.2", certainty="resolved", source={"type": "file", "path": "resolved.json"}),
            ])
            plan = builder.build(path, "4.1.0", False, ["source:boot-4.1"])
        self.assertEqual(plan["current"]["spring_boot"], "3.5.2")

    def test_builder_preserves_current_and_target_cloud_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.evidence_file(root, [
                self.fact(project_id="project:.", kind="platform.version", name="spring-boot", value="3.5.2", certainty="resolved", source={"type": "file", "path": "resolved.json"}),
                self.fact(project_id="project:.", kind="platform.version", name="spring-cloud.version", value="2025.0.1", certainty="resolved", source={"type": "file", "path": "pom.xml"}),
            ])
            plan = builder.build(
                path, "4.1.0", False, [], False,
                "2025.1.2", False, "25", "3.9.11", None,
            )
        self.assertEqual(plan["current"]["spring_cloud"], "2025.0.1")
        self.assertEqual(plan["current"]["spring_cloud_usage"], "used")
        self.assertTrue(plan["current"]["spring_cloud_evidence_ids"])
        self.assertEqual(plan["target"]["spring_cloud_usage"], "used")
        self.assertEqual(plan["target"]["build_tool"], "maven")
        self.assertEqual(plan["status"], "draft")
        self.assertEqual(validator.validate(plan), [])

    def test_conflicting_strongest_facts_block_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.evidence_file(Path(directory), [
                self.fact(project_id="project:.", kind="platform.version", name="spring-boot", value="3.4.0", certainty="effective", source={"type": "file", "path": "effective-a.xml"}),
                self.fact(project_id="project:.", kind="platform.version", name="spring-boot", value="3.5.0", certainty="effective", source={"type": "file", "path": "effective-b.xml"}),
            ])
            plan = builder.build(path, "4.1.0", False, ["source:boot-4.1"])
        self.assertEqual(plan["status"], "blocked")
        self.assertTrue(plan["unresolved"])

    def test_ready_plan_requires_sources_verification_and_rollback(self) -> None:
        plan = {
            "schema_version": "spring-upgrade-plan/2", "status": "ready",
            "compatibility_gates": [{"id": "gate:java", "status": "pass", "source_ids": []}],
            "hops": [{"id": "hop:one", "source_ids": [], "changes": [], "verification": [], "rollback": []}],
            "unresolved": [],
        }
        errors = validator.validate(plan)
        self.assertTrue(any("source_ids" in error for error in errors))
        self.assertTrue(any("verification" in error for error in errors))
        self.assertTrue(any("rollback" in error for error in errors))

    def test_invalid_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.evidence_file(Path(directory), [])
            with self.assertRaisesRegex(ValueError, "exact Spring Boot version"):
                builder.build(path, "banana", False, [])

    def test_unresolved_current_version_blocks_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.evidence_file(Path(directory), [
                self.fact(project_id="project:.", kind="platform.version", name="spring-boot", value="${boot.version}", certainty="inferred", source={"type": "file", "path": "pom.xml"})
            ])
            plan = builder.build(path, "4.1.0", False, [])
        self.assertEqual(plan["status"], "blocked")

    def test_major_upgrade_includes_official_bridge_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.evidence_file(Path(directory), [
                self.fact(project_id="project:.", kind="platform.version", name="spring-boot", value="3.4.2", certainty="declared", source={"type": "file", "path": "pom.xml"})
            ])
            plan = builder.build(path, "4.1.0", False, [])
        self.assertIn("gate:major-bridge", {gate["id"] for gate in plan["compatibility_gates"]})
        self.assertEqual(plan["hops"][0]["to"], "latest-3.5.x-from-pinned-source")

    def test_fully_sourced_ready_plan_can_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.evidence_file(root, [
                self.fact(project_id="project:.", kind="platform.version", name="spring-boot", value="3.5.2", certainty="resolved", source={"type": "file", "path": "resolved.json"})
            ])
            source_specs = {
                "source:support": ("target-support", "https://spring.io/support-policy", "spring", None, None),
                "source:requirements": ("system-requirements", "https://docs.spring.io/spring-boot/4.1/system-requirements.html", "spring", None, None),
                "source:cloud": ("spring-cloud-compatibility", "https://spring.io/projects/spring-cloud", "spring", None, None),
                "source:java": ("java-migration", "https://docs.oracle.com/en/java/javase/25/migrate/", "oracle", None, None),
                "source:maven": ("maven-reference", "https://maven.apache.org/docs/3.9.11/release-notes.html", "maven", None, None),
                "source:migration-4.0": ("migration-guide", "https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide", "spring-github", "3.5.2", "4.0.5"),
                "source:release-4.1": ("release-notes", "https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes", "spring-github", "4.0.5", "4.1.0"),
            }
            plan = builder.build(
                path, "4.1.0", False, list(source_specs), False,
                "2025.1.2", False, "25", "3.9.11", None,
            )
            plan["status"] = "ready"
            plan["unresolved"] = []
            plan["current"].update(
                spring_cloud=None,
                spring_cloud_usage="not-used",
                spring_cloud_evidence_ids=["evidence:no-spring-cloud"],
            )
            validation_time = datetime(2026, 7, 12, 12, 0, 0, tzinfo=UTC)
            for source in plan["source_ledger"]:
                scope, locator, publisher, applies_from, applies_to = source_specs[source["id"]]
                snapshot = root / f"{source['id'].replace(':', '-')}.snapshot"
                snapshot.write_text(f"snapshot for {source['id']}", encoding="utf-8")
                digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
                final_locator = locator
                if source["id"] == "source:support":
                    final_locator = "https://spring.io/support-policy/"
                elif source["id"] == "source:requirements":
                    final_locator = "https://docs.spring.io/spring-boot/system-requirements.html"
                elif source["id"] == "source:cloud":
                    final_locator = "https://spring.io/projects/spring-cloud/"
                if scope == "spring-cloud-compatibility":
                    subject, subject_version = "spring-cloud", "2025.1.2"
                elif scope == "java-migration":
                    subject, subject_version = "java", "25"
                elif scope == "maven-reference":
                    subject, subject_version = "maven", "3.9.11"
                else:
                    subject, subject_version = "spring-boot", (applies_to or "4.1.0")
                source.update(
                    kind="pinned-source-copy", locator=locator, publisher=publisher,
                    checked_version=applies_to or "4.1.0", scope=scope,
                    applies_from=applies_from, applies_to=applies_to, snapshot_path=snapshot.name,
                    sha256=digest,
                    checked_spring_cloud="2025.1.2" if scope == "spring-cloud-compatibility" else None,
                    subject=subject, subject_version=subject_version,
                    capture={
                        "method": "controlled-fetch", "captured_at": "2026-07-12T00:00:00Z",
                        "captured_by": "test-fixture", "final_locator": final_locator,
                        "response_sha256": digest,
                    },
                )
            for gate in plan["compatibility_gates"]:
                gate["status"] = "pass"
            plan["hops"][0]["to"] = "4.0.5"
            plan["hops"][1]["from"] = "4.0.5"
            for hop in plan["hops"]:
                hop["changes"] = ["Apply reviewed compatibility changes."]
                hop["verification"] = ["Run the approved test and canary gates."]
                hop["rollback"] = ["Roll back before irreversible data changes."]
            plan["rollout"] = {"canary_signals": ["error and latency SLO"], "rollback_trigger": "SLO regression"}
            def validate_ready() -> list[str]:
                return validator.validate(plan, root, now=validation_time)

            self.assertEqual(validate_ready(), [])
            java_gate = next(gate for gate in plan["compatibility_gates"] if gate["id"] == "gate:java-build-tools")
            java_gate["source_ids"].remove("source:java")
            self.assertTrue(any("subject-bound sources" in error for error in validate_ready()))
            java_gate["source_ids"].append("source:java")
            java_gate["source_ids"].sort()
            release_source = next(source for source in plan["source_ledger"] if source["id"] == "source:release-4.1")
            original_applicability = (release_source["applies_from"], release_source["applies_to"], release_source["checked_version"])
            release_source.update(applies_from="3.5.2", applies_to="4.0.5", checked_version="4.0.5")
            self.assertTrue(any("applicable migration/release" in error for error in validate_ready()))
            release_source.update(
                applies_from=original_applicability[0], applies_to=original_applicability[1], checked_version=original_applicability[2]
            )
            original_locator = plan["source_ledger"][0]["locator"]
            plan["source_ledger"][0]["locator"] = "https://evil.example/fake"
            self.assertTrue(any("publisher/host mismatch" in error for error in validate_ready()))
            plan["source_ledger"][0]["locator"] = original_locator
            cloud_source = next(source for source in plan["source_ledger"] if source["id"] == "source:cloud")
            cloud_original = (cloud_source["locator"], cloud_source["publisher"], cloud_source["capture"]["final_locator"])
            cloud_source.update(
                locator="https://github.com/spring-cloud/spring-cloud-release/wiki/Supported-Versions",
                publisher="spring-github",
            )
            cloud_source["capture"]["final_locator"] = cloud_source["locator"]
            self.assertEqual(validate_ready(), [])
            cloud_source["scope"] = "migration-guide"
            self.assertTrue(any("approved publisher paths" in error for error in validate_ready()))
            cloud_source["scope"] = "spring-cloud-compatibility"
            cloud_source["locator"] = "https://github.com/not-spring/forged-guide"
            self.assertTrue(any("approved publisher paths" in error for error in validate_ready()))
            for forged_locator in (
                "https://github.com/spring-cloud/../not-spring/forged-guide",
                "https://github.com/spring-cloud/%2e%2e/not-spring/forged-guide",
                "https://github.com/spring-projects/spring-boot/issues/123",
                "https://github.com/spring-projects/spring-boot/wiki/Unrelated-Page",
                "https://attacker@github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide",
                "https://github.com:444/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide",
            ):
                with self.subTest(forged_locator=forged_locator):
                    cloud_source["locator"] = forged_locator
                    self.assertTrue(validate_ready())
            cloud_source.update(locator=cloud_original[0], publisher=cloud_original[1])
            cloud_source["capture"]["final_locator"] = cloud_original[2]
            migration_source = next(source for source in plan["source_ledger"] if source["id"] == "source:migration-4.0")
            migration_source["scope"] = "release-notes"
            self.assertTrue(any("approved publisher paths" in error for error in validate_ready()))
            migration_source["scope"] = "migration-guide"
            release_source["locator"] = "https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.0-Release-Notes"
            release_source["capture"]["final_locator"] = release_source["locator"]
            self.assertTrue(any("locator version" in error for error in validate_ready()))
            release_source["locator"] = source_specs["source:release-4.1"][1]
            release_source["capture"]["final_locator"] = release_source["locator"]
            release_source["capture"]["final_locator"] = "https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.0-Release-Notes"
            self.assertTrue(any("locator version" in error for error in validate_ready()))
            release_source["capture"]["final_locator"] = release_source["locator"]
            plan["target"]["spring_cloud"] = "2025.1.1"
            plan["target"]["spring_cloud_usage"] = "used"
            cloud_source["checked_spring_cloud"] = "2025.1.1"
            cloud_source["subject_version"] = "2025.1.1"
            self.assertTrue(any("2025.1.2" in error for error in validate_ready()))
            plan["target"]["spring_cloud"] = "2024.0.9"
            cloud_source["checked_spring_cloud"] = "2024.0.9"
            cloud_source["subject_version"] = "2024.0.9"
            self.assertTrue(any("2025.1.2" in error for error in validate_ready()))
            plan["target"]["spring_cloud"] = "2025.1.2"
            cloud_source["checked_spring_cloud"] = "2025.1.2"
            cloud_source["subject_version"] = "2025.1.2"
            requirements_source = next(source for source in plan["source_ledger"] if source["id"] == "source:requirements")
            requirements_source["locator"] = "https://docs.spring.io/spring-boot/3.5/system-requirements.html"
            self.assertTrue(any("locator line" in error for error in validate_ready()))
            requirements_source["locator"] = source_specs["source:requirements"][1]
            plan["source_ledger"][0]["sha256"] = "b" * 64
            self.assertTrue(any("hash mismatch" in error for error in validate_ready()))

    def test_ready_plan_rejects_duplicated_snapshot_identity(self) -> None:
        source = {
            "id": "source:a", "kind": "pinned-source-copy", "locator": "https://spring.io/support-policy",
            "publisher": "spring", "checked_version": "4.1.0", "scope": "target-support",
            "checked_spring_cloud": None, "subject": "spring-boot", "subject_version": "4.1.0",
            "applies_from": None, "applies_to": None,
            "snapshot_path": "source.snapshot", "sha256": "a" * 64,
            "capture": {
                "method": "controlled-fetch", "captured_at": "2026-07-12T00:00:00Z",
                "captured_by": "test-fixture", "final_locator": "https://spring.io/support-policy",
                "response_sha256": "a" * 64,
            },
        }
        duplicate = dict(
            source, id="source:b", locator="https://spring.io/support-policy#other",
            snapshot_path="renamed.snapshot", applies_from="3.5.2", applies_to="4.0.5",
            scope="migration-guide", checked_version="4.0.5",
        )
        plan = {
            "schema_version": "spring-upgrade-plan/2", "status": "ready",
            "input": {"evidence_sha256": "a" * 64, "target": "4.1.0", "source_snapshot_ids": ["source:a", "source:b"]},
            "current": {"spring_boot": "3.5.2", "spring_cloud": None, "evidence_ids": []},
            "target": {"spring_boot": "4.1.0", "spring_cloud": None, "prerelease_allowed": False}, "policy": {"allow_downgrade": False},
            "compatibility_gates": [{"id": gate, "status": "unknown", "rationale": "pending", "source_ids": [], "evidence_ids": []} for gate in ("gate:target-support", "gate:java-build-tools", "gate:spring-cloud")],
            "hops": [{"id": "hop:1", "from": "3.5.2", "to": "4.1.0", "rationale": "pending", "source_ids": [], "changes": [], "verification": [], "rollback": []}],
            "automation": [], "rollout": {"canary_signals": [], "rollback_trigger": None},
            "unresolved": [], "source_ledger": [source, duplicate],
        }
        errors = validator.validate(plan)
        self.assertTrue(any("locator is duplicated" in error or "snapshot identity is duplicated" in error for error in errors))

    def test_ready_plan_rejects_unknown_source_reference(self) -> None:
        plan = {
            "schema_version": "spring-upgrade-plan/2", "status": "ready",
            "input": {"evidence_sha256": "a" * 64, "target": "4.1.0", "source_snapshot_ids": []},
            "current": {"spring_boot": "3.5.2", "evidence_ids": ["fact:x"]},
            "target": {"spring_boot": "4.1.0", "prerelease_allowed": False},
            "policy": {"allow_downgrade": False},
            "compatibility_gates": [
                {"id": gate, "status": "pass", "rationale": "checked", "source_ids": ["missing"]}
                for gate in ("gate:target-support", "gate:java-build-tools", "gate:spring-cloud")
            ],
            "hops": [{"id": "hop:1", "from": "3.5.2", "to": "4.1.0", "rationale": "checked", "source_ids": ["missing"], "changes": ["change"], "verification": ["test"], "rollback": ["rollback"]}],
            "automation": [], "rollout": {"canary_signals": ["SLO"], "rollback_trigger": "regression"},
            "unresolved": [], "source_ledger": [],
        }
        self.assertTrue(any("unknown sources" in error or "invalid source references" in error for error in validator.validate(plan)))

    def test_downgrade_requires_explicit_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.evidence_file(Path(directory), [
                self.fact(project_id="project:.", kind="platform.version", name="spring-boot", value="4.1.0", certainty="resolved", source={"type": "file", "path": "resolved.json"})
            ])
            with self.assertRaisesRegex(ValueError, "allow-downgrade"):
                builder.build(path, "4.0.7", False, [])

    def test_prerelease_flag_must_match_target(self) -> None:
        plan = {
            "schema_version": "spring-upgrade-plan/2", "status": "draft",
            "input": {"evidence_sha256": "a" * 64, "target": "4.2.0-RC1", "source_snapshot_ids": []},
            "current": {"spring_boot": "4.1.0", "evidence_ids": []},
            "target": {"spring_boot": "4.2.0-RC1", "prerelease_allowed": False},
            "policy": {"allow_downgrade": False},
            "compatibility_gates": [
                {"id": gate, "status": "unknown", "rationale": "pending", "source_ids": [], "evidence_ids": []}
                for gate in ("gate:target-support", "gate:java-build-tools", "gate:spring-cloud")
            ],
            "hops": [{"id": "hop:1", "from": "4.1.0", "to": "4.2.0-RC1", "rationale": "pending", "source_ids": [], "changes": [], "verification": [], "rollback": []}],
            "automation": [], "rollout": {"canary_signals": [], "rollback_trigger": None},
            "unresolved": ["sources pending"], "source_ledger": [],
        }
        self.assertTrue(any("prerelease target" in error for error in validator.validate(plan)))

    def test_draft_requires_current_spring_boot_schema_field(self) -> None:
        plan = {
            "schema_version": "spring-upgrade-plan/2", "status": "draft",
            "input": {"evidence_sha256": "a" * 64, "target": "4.1.0", "source_snapshot_ids": []},
            "current": {"evidence_ids": []},
            "target": {"spring_boot": "4.1.0", "prerelease_allowed": False},
            "policy": {"allow_downgrade": False},
            "compatibility_gates": [
                {"id": gate, "status": "unknown", "rationale": "pending", "source_ids": [], "evidence_ids": []}
                for gate in ("gate:target-support", "gate:java-build-tools", "gate:spring-cloud")
            ],
            "hops": [{"id": "hop:1", "from": "3.5.2", "to": "4.1.0", "rationale": "pending", "source_ids": [], "changes": [], "verification": [], "rollback": []}],
            "automation": [], "rollout": {"canary_signals": [], "rollback_trigger": None},
            "unresolved": ["current pending"], "source_ledger": [],
        }
        self.assertTrue(any("current state is invalid" in error for error in validator.validate(plan)))

    def test_draft_source_ledger_requires_schema_fields(self) -> None:
        plan = {
            "schema_version": "spring-upgrade-plan/2", "status": "draft",
            "input": {"evidence_sha256": "a" * 64, "target": "4.1.0", "source_snapshot_ids": ["source:x"]},
            "current": {"spring_boot": "3.5.2", "evidence_ids": []},
            "target": {"spring_boot": "4.1.0", "prerelease_allowed": False},
            "policy": {"allow_downgrade": False},
            "compatibility_gates": [
                {"id": gate, "status": "unknown", "rationale": "pending", "source_ids": [], "evidence_ids": []}
                for gate in ("gate:target-support", "gate:java-build-tools", "gate:spring-cloud")
            ],
            "hops": [{"id": "hop:1", "from": "3.5.2", "to": "4.1.0", "rationale": "pending", "source_ids": [], "changes": [], "verification": [], "rollback": []}],
            "automation": [], "rollout": {"canary_signals": [], "rollback_trigger": None},
            "unresolved": ["sources pending"], "source_ledger": [{"id": "source:x"}],
        }
        self.assertTrue(any("missing required schema fields" in error for error in validator.validate(plan)))


if __name__ == "__main__":
    unittest.main()
