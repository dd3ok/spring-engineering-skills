from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_skill_structure  # noqa: E402
import skill_utils  # noqa: E402


class SkillStructureTests(unittest.TestCase):
    def test_repository_structure_is_valid(self) -> None:
        self.assertEqual(validate_skill_structure.validate_structure(), [])

    def test_vendor_specific_distribution_metadata_is_absent(self) -> None:
        errors: list[str] = []
        validate_skill_structure.validate_vendor_neutral(ROOT, errors)
        self.assertEqual(errors, [])
        for skill in (ROOT / "skills").iterdir():
            if skill.is_dir():
                self.assertFalse((skill / "agents").exists())

    def test_python_runtime_floor_is_enforced(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Python 3.12"):
            skill_utils.require_supported_python((3, 11))
        skill_utils.require_supported_python((3, 12))

    def test_script_skills_declare_runtime_compatibility(self) -> None:
        for name in ("spring-evidence-collector", "spring-upgrade-planner"):
            frontmatter, _ = skill_utils.parse_frontmatter(ROOT / "skills" / name / "SKILL.md")
            self.assertIn("Python 3.12", frontmatter.get("description", ""))

    def test_descriptions_are_imperative_and_expose_artifact_ownership(self) -> None:
        descriptions: dict[str, str] = {}
        for skill in (ROOT / "skills").iterdir():
            if skill.is_dir():
                frontmatter, _ = skill_utils.parse_frontmatter(skill / "SKILL.md")
                description = frontmatter.get("description", "")
                self.assertTrue(description.startswith("Use this skill when"), skill.name)
                self.assertLessEqual(len(description), 1024)
                descriptions[skill.name] = description
        self.assertIn("spring-evidence/1", descriptions["spring-evidence-collector"])
        self.assertIn("spring-upgrade-plan/2", descriptions["spring-upgrade-planner"])

    def test_orphan_skill_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skills = root / "skills"
            (skills / "orphan").mkdir(parents=True)
            with patch.object(validate_skill_structure, "ROOT", root), patch.object(validate_skill_structure, "SKILLS_ROOT", skills), patch.object(skill_utils, "ROOT", root), patch.object(skill_utils, "SKILLS_ROOT", skills):
                errors = validate_skill_structure.validate_structure()
        self.assertTrue(any("missing SKILL.md" in error for error in errors))

    def test_bare_runtime_resource_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory)
            (skill / "references").mkdir()
            (skill / "references" / "rules.md").write_text("# Rules\n", encoding="utf-8")
            (skill / "SKILL.md").write_text("Load `rules.md`.\n", encoding="utf-8")
            errors: list[str] = []
            validate_skill_structure.validate_resource_references(skill, errors)
        self.assertTrue(any("skill-root-relative path" in error for error in errors))

    def test_bare_script_name_is_rejected_regardless_of_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory)
            (skill / "scripts").mkdir()
            (skill / "scripts" / "tool.py").write_text("", encoding="utf-8")
            (skill / "SKILL.md").write_text("Run `tool.py`.\n", encoding="utf-8")
            errors: list[str] = []
            validate_skill_structure.validate_resource_references(skill, errors)
        self.assertTrue(any("skill-root-relative path" in error for error in errors))

    def test_bare_runtime_name_in_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory)
            (skill / "references").mkdir()
            (skill / "references" / "rules.md").write_text("Use `other.md`.\n", encoding="utf-8")
            (skill / "references" / "other.md").write_text("# Other\n", encoding="utf-8")
            (skill / "SKILL.md").write_text(
                "Load `references/rules.md` and `references/other.md`.\n", encoding="utf-8"
            )
            errors: list[str] = []
            validate_skill_structure.validate_resource_references(skill, errors)
        self.assertTrue(any("skill-root-relative path" in error for error in errors))

    def test_missing_and_escaping_runtime_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skill"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "Load `references/missing.md` and `references/../outside.md`.\n", encoding="utf-8"
            )
            (root / "outside.md").write_text("# Outside\n", encoding="utf-8")
            errors: list[str] = []
            validate_skill_structure.validate_resource_references(skill, errors)
        self.assertEqual(sum("invalid runtime resource path" in error for error in errors), 2)

    def test_orphan_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory)
            (skill / "references").mkdir()
            (skill / "references" / "loaded.md").write_text("# Loaded\n", encoding="utf-8")
            (skill / "references" / "orphan.md").write_text("# Orphan\n", encoding="utf-8")
            (skill / "SKILL.md").write_text("Load `references/loaded.md`.\n", encoding="utf-8")
            errors: list[str] = []
            validate_skill_structure.validate_resource_references(skill, errors)
        self.assertTrue(any("linked directly from SKILL.md" in error for error in errors))

    def test_command_runtime_path_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory)
            (skill / "scripts").mkdir()
            (skill / "SKILL.md").write_text("Run `python scripts/missing.py --check`.\n", encoding="utf-8")
            errors: list[str] = []
            validate_skill_structure.validate_resource_references(skill, errors)
        self.assertTrue(any("invalid runtime resource path" in error for error in errors))

    def test_dot_prefixed_runtime_path_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory)
            (skill / "scripts").mkdir()
            (skill / "SKILL.md").write_text("Run `python ./scripts/missing.py --check`.\n", encoding="utf-8")
            errors: list[str] = []
            validate_skill_structure.validate_resource_references(skill, errors)
        self.assertTrue(any("invalid runtime resource path" in error for error in errors))

    def test_runtime_path_case_is_checked_lexically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory)
            (skill / "scripts").mkdir()
            (skill / "scripts" / "tool.py").write_text("", encoding="utf-8")
            (skill / "SKILL.md").write_text("Run `scripts/TOOL.py`.\n", encoding="utf-8")
            errors: list[str] = []
            validate_skill_structure.validate_resource_references(skill, errors)
        self.assertTrue(any("invalid runtime resource path" in error for error in errors))

    def test_percent_encoded_markdown_resource_path_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory)
            (skill / "references").mkdir()
            (skill / "references" / "my rules.md").write_text("# Rules\n", encoding="utf-8")
            (skill / "SKILL.md").write_text(
                "Load [rules](<references/my%20rules.md>).\n", encoding="utf-8"
            )
            errors: list[str] = []
            validate_skill_structure.validate_resource_references(skill, errors)
        self.assertEqual(errors, [])

    def test_absolute_and_parent_runtime_paths_are_rejected(self) -> None:
        for token in ("/scripts/missing.py", "../scripts/missing.py"):
            with self.subTest(token=token), tempfile.TemporaryDirectory() as directory:
                skill = Path(directory)
                (skill / "scripts").mkdir()
                (skill / "SKILL.md").write_text(f"Run `{token}`.\n", encoding="utf-8")
                errors: list[str] = []
                validate_skill_structure.validate_resource_references(skill, errors)
            self.assertTrue(any("invalid runtime resource path" in error for error in errors))

    def test_quoted_command_runtime_path_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory)
            (skill / "scripts").mkdir()
            (skill / "scripts" / "tool.py").write_text("", encoding="utf-8")
            (skill / "SKILL.md").write_text('Run `python "scripts/tool.py"`.\n', encoding="utf-8")
            errors: list[str] = []
            validate_skill_structure.validate_resource_references(skill, errors)
        self.assertEqual(errors, [])

    def test_high_risk_evidence_execution_contract_is_pinned(self) -> None:
        skill = (ROOT / "skills" / "spring-evidence-collector" / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "skills" / "spring-evidence-collector" / "references" / "evidence-contract.md").read_text(encoding="utf-8")
        self.assertIn("separate high-risk workflow", skill)
        self.assertIn("not separate authorization", skill)
        for required in ("verified project wrapper", "disposable isolation", "no production credentials", "deny-by-default network", "no arbitrary or custom tasks"):
            self.assertIn(required, skill)
        for required in (
            "not separate authorization",
            "fresh explicit authorization",
            "execute untrusted code",
            "disposable isolation",
            "deny-by-default network",
            "Never recommend arbitrary or custom tasks",
        ):
            self.assertIn(required, contract)
        self.assertIn("A supplied checksum can preserve artifact identity but does not establish trust", contract)
        self.assertIn("eligible for `effective` or `resolved` only when", contract)
        self.assertIn("Otherwise keep the fact `inferred` and record a provenance gap", contract)
        self.assertIn("certainty labels describe evidence derivation, not truth or safety", contract)

    def test_saved_artifacts_require_an_explicit_user_request(self) -> None:
        collector = (ROOT / "skills" / "spring-evidence-collector" / "SKILL.md").read_text(encoding="utf-8")
        planner = (ROOT / "skills" / "spring-upgrade-planner" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Use `--output <path>` only when the user asked for an artifact", collector)
        self.assertIn("Use `--output <path>` only when the user asks for a saved artifact", planner)
        self.assertIn("otherwise keep the generated JSON on stdout", planner)

    def test_runtime_artifact_handling_contract_is_pinned(self) -> None:
        skill = (ROOT / "skills" / "spring-performance-investigator" / "SKILL.md").read_text(encoding="utf-8")
        playbook = (ROOT / "skills" / "spring-performance-investigator" / "references" / "investigation-playbook.md").read_text(encoding="utf-8")
        self.assertIn("Before opening a dump or profile", skill)
        self.assertIn("confirm authorization and handling location", skill)
        self.assertIn("never an exact production value", skill)
        self.assertIn("Do not require the user to paste raw sensitive contents into chat", skill)
        for required in ("authorization, origin", "tool/version/flags", "sanitization status", "a checksum establishes identity, not trust"):
            self.assertIn(required, playbook)


if __name__ == "__main__":
    unittest.main()
