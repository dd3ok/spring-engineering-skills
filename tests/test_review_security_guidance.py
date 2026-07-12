from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "skills" / "spring-engineering-review" / "references"


class ReviewSecurityGuidanceTests(unittest.TestCase):
    def assert_contains_all(self, relative_path: str, required: tuple[str, ...]) -> None:
        text = (REFERENCES / relative_path).read_text(encoding="utf-8")
        for value in required:
            with self.subTest(file=relative_path, value=value):
                self.assertIn(value, text)

    def test_kafka_security_boundaries_are_pinned(self) -> None:
        self.assert_contains_all(
            "kafka-rules.md",
            (
                "controller",
                "hostname verification",
                "SASL/PLAIN",
                "allow.everyone.if.no.acl.found",
                "`super.users`",
                "bypasses authorizer checks",
                "forwarded administrative requests",
                "`KafkaPrincipalSerde`",
            ),
        )

    def test_rabbitmq_and_pulsar_security_boundaries_are_pinned(self) -> None:
        self.assert_contains_all(
            "messaging-rules.md",
            (
                "default `guest`",
                "virtual host",
                "Pulsar security is not on by default",
                "proxy-to-broker",
                "BookKeeper/storage",
                "Functions/IO",
            ),
        )

    def test_postgresql_tenant_security_boundaries_are_pinned(self) -> None:
        self.assert_contains_all(
            "postgresql-rules.md",
            (
                "ordered first-match",
                "`scram-sha-256`",
                "deprecated MD5",
                "`sslmode=require`",
                "`SECURITY DEFINER`",
                "`pg_temp` last",
                "`BYPASSRLS`",
                "always bypass policies",
                "Table owners normally bypass",
                "permissive-policy OR",
                "`WITH CHECK`",
                "`TRUNCATE`",
            ),
        )

    def test_security_rules_have_official_sources(self) -> None:
        self.assert_contains_all(
            "messaging-sources.md",
            (
                "kafka.apache.org/43/security/authorization-and-acls/",
                "rabbitmq.com/docs/access-control",
                "pulsar.apache.org/docs/4.1.x/security-overview/",
            ),
        )
        self.assert_contains_all(
            "data-sources.md",
            (
                "postgresql.org/docs/current/ddl-rowsecurity.html",
                "postgresql.org/docs/current/auth-password.html",
                "jdbc.postgresql.org/documentation/ssl/",
            ),
        )

    def test_test_gap_sources_mark_fixed_broker_versions_as_examples(self) -> None:
        text = (
            ROOT
            / "skills"
            / "spring-test-gap-planner"
            / "references"
            / "official-sources.md"
        ).read_text(encoding="utf-8")
        self.assertIn("reviewed examples, not compatibility defaults", text)
        self.assertIn("deployed broker/client line", text)

    def test_specialized_and_jvm_source_ownership_is_not_leaked(self) -> None:
        self.assert_contains_all(
            "specialized-sources.md",
            ("reference/io/grpc.html", "spring-session/reference", "spring-ldap/reference"),
        )
        self.assert_contains_all(
            "operations-sources.md",
            ("java/javase/21/core/virtual-threads.html",),
        )
        spring_core = (REFERENCES / "spring-core-sources.md").read_text(encoding="utf-8")
        messaging = (REFERENCES / "messaging-sources.md").read_text(encoding="utf-8")
        self.assertNotIn("reference/io/grpc.html", spring_core)
        self.assertNotIn("spring-session/reference", spring_core)
        self.assertNotIn("java/javase/21/core/virtual-threads.html", messaging)


if __name__ == "__main__":
    unittest.main()
