from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "skills" / "spring-engineering-review" / "references"


class ModernSpringGuidanceTests(unittest.TestCase):
    def test_boot_4_migration_gate_is_evidence_scoped(self) -> None:
        migration = (REVIEW / "migration-rules.md").read_text(encoding="utf-8")
        for value in (
            "Spring Boot 4 Gate",
            "repository evidence",
            "Jackson 3",
            "Undertow",
            "Servlet 6.1",
            "Kotlin 2.2+",
            "GraalVM 25+",
            "TestRestTemplate",
        ):
            self.assertIn(value, migration)
        self.assertIn("only when", migration)

    def test_batch_6_rules_preserve_one_shot_exception(self) -> None:
        batch = (REVIEW / "spring-batch-rules.md").read_text(encoding="utf-8")
        for value in ("ResourcelessJobRepository", "restart metadata", "concurrent execution", "JDBC", "MongoDB"):
            self.assertIn(value, batch)
        self.assertIn("Do not require a database repository for every", batch)

    def test_spring_ai_execution_model_is_explicit(self) -> None:
        ai = (REVIEW / "spring-ai-rules.md").read_text(encoding="utf-8")
        for value in ("RestClient", "WebClient", "event-loop", "tool calling", "advisor", "Micrometer observation"):
            self.assertIn(value, ai)
        self.assertIn("community-driven, work-in-progress", ai)

    def test_aot_kubernetes_and_kotlin_boundaries_are_pinned(self) -> None:
        operations = (REVIEW / "architecture-operations-rules.md").read_text(encoding="utf-8")
        for value in (
            "build-time-fixed classpath and bean graph",
            "precise `@Bean` return types",
            "JVM AOT initialization tests",
            "immutable digest",
            "allowPrivilegeEscalation: false",
            "seccomp",
            "main server port",
            "`kotlin-jpa` preset only for JPA entities",
            "generic no-arg plugin only when a specific non-JPA framework",
            "`suspend` alone does not make blocking work non-blocking",
        ):
            self.assertIn(value, operations)

    def test_primary_sources_cover_new_guidance(self) -> None:
        operations = (REVIEW / "operations-sources.md").read_text(encoding="utf-8")
        specialized = (REVIEW / "specialized-sources.md").read_text(encoding="utf-8")
        for value in (
            "https://docs.spring.io/spring-boot/reference/packaging/aot.html",
            "https://docs.spring.io/spring-framework/reference/languages/kotlin/requirements.html",
            "https://kotlinlang.org/docs/all-open-plugin.html",
            "https://kubernetes.io/docs/concepts/security/pod-security-standards/",
        ):
            self.assertIn(value, operations)
        for value in (
            "mcp-security.html",
            "Spring-Batch-6.0-Migration-Guide",
            "configuring-repository.html",
        ):
            self.assertIn(value, specialized)

    def test_project_lifecycle_claims_match_consumers(self) -> None:
        skill = (ROOT / "skills" / "spring-engineering-review" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        specialized = (REVIEW / "specialized-sources.md").read_text(encoding="utf-8")
        test_sources = (
            ROOT / "skills" / "spring-test-gap-planner" / "references" / "official-sources.md"
        ).read_text(encoding="utf-8")
        catalog = json.loads(
            (ROOT / "evals" / "spring-project-lifecycle.json").read_text(encoding="utf-8")
        )
        statuses = {claim["project_name"]: claim["status"] for claim in catalog["claims"]}
        self.assertEqual(statuses["Spring Shell"], "active")
        self.assertEqual(statuses["Spring Web Flow"], "active")
        self.assertEqual(statuses["Spring Cloud Contract"], "attic")
        self.assertIn("Spring Shell as an active", skill)
        self.assertIn("Spring Web Flow as an active", skill)
        self.assertIn("Spring Shell project page (active project)", specialized)
        self.assertIn("Spring Web Flow project page (active project)", specialized)
        self.assertIn("Spring Cloud Contract", test_sources)
        self.assertIn("Projects in the Attic", test_sources)
        self.assertNotIn("Spring Web Flow or other Attic projects", skill)

    def test_kotlin_publisher_is_official_without_broadening_unknown_publishers(self) -> None:
        policy = json.loads((ROOT / "evals" / "source-publisher-policy.json").read_text(encoding="utf-8"))
        self.assertIn("kotlinlang.org", policy["official_publishers"])
        self.assertNotIn("medium.com", policy["official_publishers"])

    def test_review_references_remain_bounded(self) -> None:
        for path in REVIEW.glob("*.md"):
            with self.subTest(path=path.name):
                self.assertLessEqual(len(path.read_text(encoding="utf-8").splitlines()), 100)


if __name__ == "__main__":
    unittest.main()
