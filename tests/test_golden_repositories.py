from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "repositories"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collector = load_module(
    "golden_spring_evidence_collector",
    ROOT / "skills" / "spring-evidence-collector" / "scripts" / "collect_evidence.py",
)
validator = load_module(
    "golden_spring_evidence_validator",
    ROOT / "skills" / "spring-evidence-collector" / "scripts" / "validate_evidence.py",
)


class GoldenRepositoryTests(unittest.TestCase):
    def collect(self, fixture: str) -> dict:
        result = collector.collect(FIXTURES / fixture, 1000, 1_000_000)
        self.assertEqual(result["schema_version"], "spring-evidence/1")
        self.assertFalse(result["collection"]["network_used"])
        self.assertFalse(result["collection"]["build_executed"])
        self.assertEqual(result["gaps"], [])
        self.assertEqual(result["conflicts"], [])
        self.assertEqual(validator.validate(result), [])
        return result

    def test_maven_boot3_reactor(self) -> None:
        result = self.collect("maven-boot3-reactor")
        projects = {project["id"]: project for project in result["projects"]}
        self.assertEqual(set(projects), {"project:.", "project:app", "project:library"})
        self.assertEqual(projects["project:."]["module_ids"], ["project:app", "project:library"])
        self.assertTrue(any(
            fact["kind"] == "platform.version"
            and fact["name"] == "spring-boot"
            and fact["value"] == "3.5.16"
            for fact in result["facts"]
        ))
        self.assertTrue(any(
            fact["kind"] == "language.version"
            and fact["name"] == "java.version"
            and fact["value"] == "21"
            for fact in result["facts"]
        ))

    def test_gradle_groovy_boot3_multi_project(self) -> None:
        result = self.collect("gradle-groovy-boot3")
        projects = {project["id"]: project for project in result["projects"]}
        self.assertEqual(set(projects), {"project:.", "project:app", "project:library"})
        self.assertEqual(projects["project:."]["module_ids"], ["project:app", "project:library"])
        self.assertTrue(any(
            fact["kind"] == "platform.version"
            and fact["project_id"] == "project:app"
            and fact["value"] == "3.5.16"
            for fact in result["facts"]
        ))
        self.assertTrue(any(
            fact["kind"] == "dependency.declared"
            and fact["name"] == "org.springframework.boot:spring-boot-starter-web"
            for fact in result["facts"]
        ))

    def test_gradle_kotlin_boot4_multi_project(self) -> None:
        result = self.collect("gradle-kotlin-boot4")
        projects = {project["id"]: project for project in result["projects"]}
        self.assertEqual(set(projects), {"project:.", "project:app", "project:library"})
        self.assertEqual(projects["project:."]["module_ids"], ["project:app", "project:library"])
        self.assertTrue(any(
            fact["kind"] == "platform.version"
            and fact["name"] == "spring-boot"
            and fact["project_id"] == "project:app"
            and fact["value"] == "4.1.0"
            and fact.get("declaration_role") == "applied-version-catalog"
            for fact in result["facts"]
        ))
        self.assertTrue(any(
            fact["kind"] == "plugin.version"
            and fact["name"] == "org.jetbrains.kotlin.jvm"
            and fact["value"] == "2.3.21"
            for fact in result["facts"]
        ))
        self.assertTrue(any(
            fact["kind"] == "plugin.version"
            and fact["name"] == "io.spring.dependency-management"
            and fact["value"] == "1.1.7"
            for fact in result["facts"]
        ))
        self.assertTrue(any(
            fact["kind"] == "build-tool.version"
            and fact["name"] == "gradle-wrapper"
            and fact["value"] == "8.14.3"
            for fact in result["facts"]
        ))
        self.assertTrue(any(
            fact["kind"] == "dependency.declared"
            and fact["name"] == "org.springframework.boot:spring-boot-starter-webmvc"
            for fact in result["facts"]
        ))
        self.assertTrue(any(
            fact["kind"] == "code.signal"
            and fact["name"] == "@RestController"
            and fact["project_id"] == "project:app"
            and fact["source"]["path"].endswith("Application.kt")
            for fact in result["facts"]
        ))

    def test_nested_fixture_facts_belong_to_the_nearest_project(self) -> None:
        result = collector.collect(FIXTURES, 1000, 1_000_000)
        self.assertEqual(validator.validate(result), [])
        kotlin_source = next(
            fact for fact in result["facts"]
            if fact["kind"] == "code.signal"
            and fact["source"]["path"].endswith("gradle-kotlin-boot4/app/src/main/kotlin/com/example/app/Application.kt")
        )
        wrapper = next(
            fact for fact in result["facts"]
            if fact["kind"] == "build-tool.version" and fact["name"] == "gradle-wrapper"
        )
        self.assertEqual(kotlin_source["project_id"], "project:gradle-kotlin-boot4/app")
        self.assertEqual(wrapper["project_id"], "project:gradle-kotlin-boot4")


if __name__ == "__main__":
    unittest.main()
