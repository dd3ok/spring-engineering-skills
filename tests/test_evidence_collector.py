from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collector = load_module(
    "spring_evidence_collector",
    ROOT / "skills" / "spring-evidence-collector" / "scripts" / "collect_evidence.py",
)
validator = load_module(
    "spring_evidence_validator",
    ROOT / "skills" / "spring-evidence-collector" / "scripts" / "validate_evidence.py",
)


class EvidenceCollectorTests(unittest.TestCase):
    def test_python_runtime_floor_is_enforced(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Python 3.12"):
            collector.require_supported_python((3, 11))
        validator.require_supported_python((3, 12))

    def fixture(self, root: Path) -> None:
        (root / "pom.xml").write_text(
            """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId><version>3.5.2</version></parent>
  <properties><java.version>21</java.version></properties>
  <dependencies><dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency></dependencies>
</project>\n""",
            encoding="utf-8",
        )
        resources = root / "src" / "main" / "resources"
        resources.mkdir(parents=True)
        (resources / "application.yml").write_text(
            "spring:\n  datasource:\n    url: jdbc:postgresql://secret-host/db\n    password: never-emit-me\n",
            encoding="utf-8",
        )
        source = root / "src" / "main" / "java" / "Example.java"
        source.parent.mkdir(parents=True)
        source.write_text("@RestController class Example {}\n", encoding="utf-8")
        (root / ".env").write_text("TOKEN=never-emit-token\n", encoding="utf-8")
        secret_directory = root / "ops" / "secrets"
        secret_directory.mkdir(parents=True)
        (secret_directory / "application.yml").write_text("token: nested-never-emit\n", encoding="utf-8")

    def test_static_collection_is_deterministic_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            first = collector.collect(root, 1000, 1_000_000)
            second = collector.collect(root, 1000, 1_000_000)
        self.assertEqual(
            json.dumps(first, sort_keys=True, ensure_ascii=False),
            json.dumps(second, sort_keys=True, ensure_ascii=False),
        )
        rendered = json.dumps(first, ensure_ascii=False)
        self.assertNotIn("never-emit", rendered)
        self.assertNotIn("secret-host", rendered)
        self.assertNotIn("nested-never-emit", rendered)
        self.assertIn("spring.datasource.password", rendered)
        self.assertEqual(validator.validate(first), [])
        self.assertTrue(any(fact["name"] == "spring-boot" and fact["value"] == "3.5.2" for fact in first["facts"]))

    def test_secret_named_configuration_files_are_never_opened(self) -> None:
        secret_names = (
            "token.properties", "access-token.yml", "api_key.yaml", "passwords.properties",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in secret_names:
                (root / name).write_text("repository-token=never-read\n", encoding="utf-8")
            (root / "Token.java").write_text("@RestController class Token {}\n", encoding="utf-8")
            with mock.patch.object(collector, "read_text", wraps=collector.read_text) as read_text:
                result = collector.collect(root, 100, 100_000)

        opened = {call.args[0].name for call in read_text.call_args_list}
        self.assertTrue(opened.isdisjoint(secret_names))
        self.assertIn("Token.java", opened)
        self.assertEqual(
            {item["path"] for item in result["excluded"]},
            set(secret_names),
        )

    def test_domain_named_module_is_not_mistaken_for_a_secret_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module = root / "token-service"
            source = module / "src" / "main" / "java" / "Api.java"
            source.parent.mkdir(parents=True)
            (module / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")
            source.write_text("@RestController class Api {}\n", encoding="utf-8")

            result = collector.collect(root, 100, 100_000)

        self.assertTrue(any(project["id"] == "project:token-service" for project in result["projects"]))
        self.assertFalse(any(item["path"].startswith("token-service/") for item in result["excluded"]))

    def test_xml_entity_declaration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text(
                '<!DOCTYPE project [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><project>&xxe;</project>',
                encoding="utf-8",
            )
            result = collector.collect(root, 100, 100_000)
        self.assertTrue(any(gap["kind"] == "unsafe-xml-declaration" for gap in result["gaps"]))
        self.assertEqual(result["facts"], [])

    def test_malformed_evidence_json_reports_an_error_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence_path = Path(directory) / "broken.json"
            evidence_path.write_text('{"schema_version":', encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "skills" / "spring-evidence-collector" / "scripts" / "validate_evidence.py"),
                    str(evidence_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR: cannot read valid UTF-8 evidence JSON", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_maven_module_parent_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text("<project><modules><module>../../outside</module></modules></project>", encoding="utf-8")
            result = collector.collect(root, 100, 100_000)
        self.assertEqual(result["projects"][0]["module_ids"], [])
        self.assertTrue(any(gap["kind"] == "invalid-module-path" for gap in result["gaps"]))
        self.assertEqual(validator.validate(result), [])

    def test_unknown_secret_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            result = collector.collect(root, 100, 100_000)
        result["password"] = "actual-secret-value"
        self.assertTrue(any("unknown top-level" in error for error in validator.validate(result)))

    def test_static_evidence_rejects_resolved_certainty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            result = collector.collect(root, 100, 100_000)
        fact = result["facts"][0]
        fact["certainty"] = "resolved"
        fact["id"] = validator.expected_fact_id(fact)
        self.assertTrue(any("resolved/effective certainty" in error for error in validator.validate(result)))

    def test_imported_resolved_evidence_requires_complete_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            result = collector.collect(root, 100, 100_000)
        result["collection"]["mode"] = "imported-resolved"
        self.assertTrue(any("complete provenance" in error for error in validator.validate(result)))
        result["collection"]["provenance"] = {
            "producer": "test", "tool": "resolved-report", "tool_version": "1.0",
            "command_or_settings": "controlled fixture", "collected_at": "2026-07-12T00:00:00Z",
            "environment_id": "isolated-test", "project_identity": "project:.",
            "sanitization": {
                "status": "sanitized", "configuration_values_omitted": True,
                "determinative_fields_preserved": True,
            },
        }
        self.assertEqual(validator.validate(result), [])
        provenance = result["collection"]["provenance"]
        provenance["collected_at"] = "9999-99-99T99:99:99Z"
        self.assertTrue(any("complete provenance" in error for error in validator.validate(result)))
        provenance["collected_at"] = "2999-01-01T00:00:00Z"
        self.assertTrue(any("complete provenance" in error for error in validator.validate(result)))
        provenance["collected_at"] = "2026-07-12T00:00:00Z"
        provenance["command_or_settings"] = "tool --password actual-secret-value"
        self.assertTrue(any("complete provenance" in error for error in validator.validate(result)))
        provenance["command_or_settings"] = "report --token=actual-value"
        self.assertTrue(any("complete provenance" in error for error in validator.validate(result)))
        provenance["command_or_settings"] = 'curl -H "Authorization: Bearer <redacted>" https://example.invalid'
        self.assertEqual(validator.validate(result), [])
        provenance["command_or_settings"] = 'curl -H "Authorization: Bearer actual-token" https://example.invalid'
        self.assertTrue(any("complete provenance" in error for error in validator.validate(result)))
        provenance["command_or_settings"] = "controlled fixture"
        provenance["sanitization"] = {
            "status": "raw", "configuration_values_omitted": False,
            "determinative_fields_preserved": True,
        }
        self.assertTrue(any("complete provenance" in error for error in validator.validate(result)))

    def test_unhashable_evidence_fields_return_errors_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            result = collector.collect(root, 100, 100_000)
            result["collection"]["mode"] = []
            path = root / "malformed-evidence.json"
            path.write_text(json.dumps(result), encoding="utf-8")
            errors = validator.validate(result)
            process = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "skills" / "spring-evidence-collector" / "scripts" / "validate_evidence.py"),
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertTrue(errors)
        self.assertEqual(process.returncode, 1)
        self.assertNotIn("Traceback", process.stderr)

    def test_secret_in_optional_fact_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            result = collector.collect(root, 100, 100_000)
        fact = result["facts"][0]
        fact["declaration_role"] = {"password": "actual-secret"}
        fact["id"] = validator.expected_fact_id(fact)
        self.assertTrue(any("invalid declaration_role" in error for error in validator.validate(result)))

    def test_non_string_conflict_fact_id_is_rejected_without_crashing(self) -> None:
        data = {
            "schema_version": "spring-evidence/1", "repository": {"root": "."},
            "collection": {"collector_version": "test", "mode": "static", "network_used": False, "build_executed": False},
            "projects": [], "facts": [],
            "conflicts": [{"project_id": "project:.", "kind": "platform.version", "name": "spring-boot", "values": [], "fact_ids": [{}]}],
            "gaps": [], "redaction": {"configuration_values_omitted": True, "environment_read": False},
        }
        self.assertTrue(validator.validate(data))

    def test_invalid_source_lines_do_not_crash_canonical_sort(self) -> None:
        facts = []
        for marker in ("a", "b"):
            fact = {"project_id": "project:.", "kind": "code.signal", "name": marker, "value": "present", "certainty": "declared", "source": {"type": "file", "path": "A.java", "line": {marker: 1}}}
            fact["id"] = validator.expected_fact_id(fact)
            facts.append(fact)
        data = {"schema_version": "spring-evidence/1", "repository": {"root": "."}, "collection": {"collector_version": "test", "mode": "static", "network_used": False, "build_executed": False}, "projects": [], "facts": facts, "conflicts": [], "gaps": [], "redaction": {"configuration_values_omitted": True, "environment_read": False}}
        self.assertTrue(validator.validate(data))

    def test_config_value_is_rejected_by_semantic_validator(self) -> None:
        fact = {
            "project_id": "project:.", "kind": "config.key", "name": "password",
            "value": "secret", "certainty": "declared", "source": {"type": "file", "path": "application.yml"},
        }
        fact["id"] = validator.expected_fact_id(fact)
        data = {
            "schema_version": "spring-evidence/1",
            "repository": {"root": "."},
            "collection": {"mode": "static", "network_used": False, "build_executed": False},
            "projects": [],
            "conflicts": [],
            "gaps": [],
            "redaction": {"configuration_values_omitted": True, "environment_read": False},
            "facts": [fact],
        }
        self.assertTrue(any("key/signal fact" in error for error in validator.validate(data)))

    def test_duplicate_maven_declarations_remain_distinct_and_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text(
                """<project><modelVersion>4.0.0</modelVersion>
<dependencyManagement><dependencies><dependency><groupId>com.example</groupId><artifactId>demo</artifactId><version>1.0</version></dependency></dependencies></dependencyManagement>
<dependencies><dependency><groupId>com.example</groupId><artifactId>demo</artifactId><version>1.0</version></dependency></dependencies>
</project>""",
                encoding="utf-8",
            )
            result = collector.collect(root, 100, 100_000)
        dependencies = [fact for fact in result["facts"] if fact["kind"] == "dependency.declared"]
        self.assertEqual({fact["declaration_role"] for fact in dependencies}, {"direct", "dependency-management"})
        self.assertEqual(len({fact["id"] for fact in dependencies}), 2)
        self.assertEqual(validator.validate(result), [])

    def test_resolved_path_outside_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as root_directory, tempfile.TemporaryDirectory() as outside_directory:
            root = Path(root_directory).resolve()
            outside = Path(outside_directory).resolve()
            self.assertFalse(collector.resolves_within(outside, root))

    def test_parent_traversal_source_path_is_rejected(self) -> None:
        fact = {
            "project_id": "project:.", "kind": "dependency.declared", "name": "com.example:demo",
            "value": "1.0.0", "certainty": "declared", "source": {"type": "file", "path": "../outside"},
        }
        fact["id"] = validator.expected_fact_id(fact)
        data = {
            "schema_version": "spring-evidence/1", "repository": {"root": "."},
            "collection": {"collector_version": "test", "mode": "static", "network_used": False, "build_executed": False},
            "projects": [], "facts": [fact], "conflicts": [], "gaps": [],
            "redaction": {"configuration_values_omitted": True, "environment_read": False},
        }
        self.assertTrue(any("canonical relative" in error for error in validator.validate(data)))

    def test_gradle_version_catalog_is_collected_without_executing_gradle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "gradle" / "libs.versions.toml"
            catalog.parent.mkdir()
            catalog.write_text(
                '[versions]\nboot = "4.1.0"\n[libraries]\nweb = { module = "org.springframework.boot:spring-boot-starter-web", version.ref = "boot" }\n[plugins]\nboot = { id = "org.springframework.boot", version.ref = "boot" }\n',
                encoding="utf-8",
            )
            (root / "build.gradle.kts").write_text(
                "plugins { alias(libs.plugins.boot) }\n",
                encoding="utf-8",
            )
            result = collector.collect(root, 100, 100_000)
        self.assertTrue(any(fact["name"] == "org.springframework.boot:spring-boot-starter-web" and fact["value"] == "4.1.0" for fact in result["facts"]))
        self.assertTrue(any(fact["kind"] == "plugin.version" and fact["name"] == "org.springframework.boot" for fact in result["facts"]))
        self.assertTrue(any(fact["kind"] == "platform.version" and fact["name"] == "spring-boot" and fact["value"] == "4.1.0" for fact in result["facts"]))

    def test_gradle_settings_declares_static_module_topology(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "settings.gradle.kts").write_text(
                'include(":app", ":lib", ":services:api")\n', encoding="utf-8",
            )
            (root / "build.gradle.kts").write_text("plugins { java }\n", encoding="utf-8")
            app = root / "app"
            app.mkdir()
            (app / "build.gradle.kts").write_text("plugins { java }\n", encoding="utf-8")

            result = collector.collect(root, 100, 100_000)

        projects = {project["id"]: project for project in result["projects"]}
        self.assertEqual(
            projects["project:."]["module_ids"],
            ["project:app", "project:lib", "project:services/api"],
        )
        self.assertTrue({"project:app", "project:lib", "project:services/api"} <= set(projects))
        self.assertEqual(validator.validate(result), [])

    def test_dynamic_gradle_topology_is_reported_as_a_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "settings.gradle").write_text("include projectNames\n", encoding="utf-8")
            (root / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")

            result = collector.collect(root, 100, 100_000)

        self.assertTrue(any(gap["kind"] == "unresolved-gradle-module-include" for gap in result["gaps"]))

    def test_gradle_composite_and_multiline_includes_are_not_conflated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "settings.gradle").write_text(
                "include ':app',\n ':lib'\nincludeBuild('build-logic')\n",
                encoding="utf-8",
            )
            (root / "build.gradle").write_text("plugins { id 'java' }\n", encoding="utf-8")

            result = collector.collect(root, 100, 100_000)

        root_project = next(project for project in result["projects"] if project["id"] == "project:.")
        self.assertEqual(root_project["module_ids"], ["project:app", "project:lib"])
        self.assertFalse(any(project["id"] == "project:build-logic" for project in result["projects"]))
        self.assertTrue(any(gap["kind"] == "unresolved-gradle-composite-build" for gap in result["gaps"]))

    def test_unused_catalog_plugin_is_not_promoted_to_platform(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "gradle" / "libs.versions.toml"
            catalog.parent.mkdir()
            catalog.write_text(
                '[versions]\nboot = "9.9.9"\n[plugins]\nboot = { id = "org.springframework.boot", version.ref = "boot" }\n',
                encoding="utf-8",
            )
            (root / "build.gradle.kts").write_text("plugins { java }\n", encoding="utf-8")
            result = collector.collect(root, 100, 100_000)
        self.assertFalse(any(fact["kind"] == "platform.version" and fact["value"] == "9.9.9" for fact in result["facts"]))

    def test_commented_or_apply_false_alias_is_not_promoted(self) -> None:
        for build_text in (
            "plugins { /* alias(libs.plugins.boot) */ java }\n",
            "plugins { alias(libs.plugins.boot) apply false }\n",
        ):
            with self.subTest(build_text=build_text), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                catalog = root / "gradle" / "libs.versions.toml"
                catalog.parent.mkdir()
                catalog.write_text(
                    '[versions]\nboot = "9.9.9"\n[plugins]\nboot = { id = "org.springframework.boot", version.ref = "boot" }\n',
                    encoding="utf-8",
                )
                (root / "build.gradle.kts").write_text(build_text, encoding="utf-8")
                result = collector.collect(root, 100, 100_000)
            self.assertFalse(any(fact["kind"] == "platform.version" and fact["value"] == "9.9.9" for fact in result["facts"]))

    def test_maven_plugin_roles_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text(
                """<project><modelVersion>4.0.0</modelVersion><build>
<pluginManagement><plugins><plugin><groupId>com.example</groupId><artifactId>tool</artifactId><version>1.0.0</version></plugin></plugins></pluginManagement>
<plugins><plugin><groupId>com.example</groupId><artifactId>tool</artifactId><version>1.0.0</version></plugin></plugins>
</build></project>""",
                encoding="utf-8",
            )
            result = collector.collect(root, 100, 100_000)
        plugins = [fact for fact in result["facts"] if fact["kind"] == "plugin.version"]
        self.assertEqual({fact["declaration_role"] for fact in plugins}, {"direct", "plugin-management"})


if __name__ == "__main__":
    unittest.main()
