from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]


def validation_commands(python: str = sys.executable) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return (
        ("skill structure", (python, "scripts/validate_skill_structure.py")),
        ("source policy", (python, "scripts/validate_source_policy.py")),
        ("routing contract", (python, "scripts/validate_routing_contract.py")),
        ("behavior contract", (python, "scripts/validate_behavior_cases.py")),
        ("Spring Cloud compatibility policy", (python, "scripts/check_spring_cloud_policy.py")),
        ("Spring Initializr metadata contract", (python, "scripts/check_spring_initializr_policy.py")),
        ("Spring project lifecycle", (python, "scripts/check_spring_project_lifecycle.py")),
        ("unit tests", (python, "-m", "unittest", "discover", "-s", "tests", "-v")),
        ("offline links", (python, "scripts/check_links.py", "--offline")),
    )


def run(commands: Sequence[tuple[str, Sequence[str]]], root: Path = ROOT) -> int:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for label, command in commands:
        print(f"==> {label}", flush=True)
        completed = subprocess.run(tuple(command), cwd=root, env=environment, check=False)
        if completed.returncode != 0:
            print(f"FAILED: {label} (exit {completed.returncode})", file=sys.stderr)
            return completed.returncode
    print("All vendor-neutral skill validations passed.")
    return 0


def main() -> int:
    return run(validation_commands())


if __name__ == "__main__":
    raise SystemExit(main())
