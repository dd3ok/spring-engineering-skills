from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = "spring-evidence/1"
EXCLUDED_DIRECTORIES = {
    ".git", ".gradle", ".idea", ".mvn-cache", ".pytest_cache", ".settings", ".vscode", "__pycache__",
    "build", "dist", "node_modules", "out", "target", "vendor",
}
SECRET_SUFFIXES = {".env", ".jks", ".key", ".keystore", ".p12", ".pfx", ".pem"}
SECRET_NAMES = {"credentials", "id_rsa", "id_ed25519", "secrets", "settings.xml"}
SECRET_DIRECTORY_NAMES = {".secrets", "credential", "credentials", "private-keys", "secret", "secrets"}
SECRET_PATH_TERM = re.compile(
    r"(?i)(?:^|[._-])(?:secret|secrets|credential|credentials|password|passwords|passwd|"
    r"token|tokens|api[._-]?key|access[._-]?key|private[._-]?key)(?:[._-]|$)"
)
SOURCE_SUFFIXES = {".java", ".kt", ".kts"}
CONFIG_SUFFIXES = {".properties", ".yaml", ".yml"}
SOURCE_SIGNALS = (
    "@RestController", "@Controller", "@Transactional", "@Scheduled", "@KafkaListener",
    "@RabbitListener", "@Entity", "@Repository", "SecurityFilterChain", "WebClient",
    "RestClient", "RedisTemplate", "ApplicationModules", "@ApplicationModule",
)
TEST_SIGNALS = (
    "@SpringBootTest", "@WebMvcTest", "@WebFluxTest", "@DataJpaTest", "@JdbcTest",
    "@JsonTest", "@ApplicationModuleTest", "@Testcontainers", "@ServiceConnection", "@Test",
)
PROPERTY_LINE = re.compile(r"^\s*([^#!\s][^=:\s]*)\s*[:=]")
YAML_KEY = re.compile(r"^(\s*)([A-Za-z0-9_.-]+)\s*:")
GRADLE_DEPENDENCY = re.compile(
    r"(?m)^\s*(implementation|api|compileOnly|runtimeOnly|testImplementation|testRuntimeOnly)"
    r"\s*\(?\s*[\"']([^\"']+)[\"']"
)
GRADLE_PLUGIN = re.compile(
    r"(?:id\s*\(\s*[\"']([^\"']+)[\"']\s*\)|id\s+[\"']([^\"']+)[\"'])"
    r"\s*\.?\s*(?:version\s+[\"']([^\"']+)[\"']|version\s*\(\s*[\"']([^\"']+)[\"']\s*\))"
    r"\s*(?:(?:\.?\s*apply\s+(false|true))|(?:\.?\s*apply\s*\(\s*(false|true)\s*\)))?"
)
GRADLE_KOTLIN_PLUGIN = re.compile(
    r"kotlin\s*\(\s*[\"']([^\"']+)[\"']\s*\)"
    r"\s*\.?\s*(?:version\s+[\"']([^\"']+)[\"']|version\s*\(\s*[\"']([^\"']+)[\"']\s*\))"
    r"\s*(?:(?:\.?\s*apply\s+(false|true))|(?:\.?\s*apply\s*\(\s*(false|true)\s*\)))?"
)
GRADLE_PLUGIN_APPLICATION = re.compile(
    r"(?:id\s*\(\s*[\"']([^\"']+)[\"']\s*\)|id\s+[\"']([^\"']+)[\"'])"
    r"(?!\s*\.?\s*version\b)"
    r"\s*(?:(?:\.?\s*apply\s+(false|true))|(?:\.?\s*apply\s*\(\s*(false|true)\s*\)))?"
)
GRADLE_PLUGIN_ALIAS = re.compile(
    r"\balias\(\s*libs\.plugins\.([A-Za-z0-9_.-]+)\s*\)"
    r"\s*(?:(?:\.?\s*apply\s+(false|true))|(?:\.?\s*apply\s*\(\s*(false|true)\s*\)))?"
)
GRADLE_INCLUDE_START = re.compile(r"^\s*include\b(?!Build\b|Flat\b)\s*(.*)$")
GRADLE_STRING = re.compile(r"[\"']([^\"']+)[\"']")
VERSION_LITERAL = re.compile(r"^\d+\.\d+\.\d+(?:-(?:SNAPSHOT|M\d+|RC\d+))?$", re.IGNORECASE)
MIN_PYTHON = (3, 12)


def require_supported_python(version=None) -> None:
    actual = version or sys.version_info
    if tuple(actual[:2]) < MIN_PYTHON:
        raise RuntimeError("Python 3.12 or newer is required for junction-safe evidence collection")


require_supported_python()


def posix(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    return "." if not relative.parts else relative.as_posix()


def project_id_for_path(path: Path, root: Path, project_roots: list[Path]) -> str:
    for candidate in project_roots:
        try:
            path.relative_to(candidate)
            return "project:" + posix(candidate, root)
        except ValueError:
            continue
    return "project:."


def absolute_from_posix(root: Path, value: str) -> Path:
    return root if value == "." else root.joinpath(*PurePosixPath(value).parts)


def nearest_ancestor(path: Path, candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        try:
            path.relative_to(candidate)
            return candidate
        except ValueError:
            continue
    return None


def is_link_or_junction(path: Path) -> bool:
    try:
        return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())
    except OSError:
        return True


def resolves_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def is_secret_path(path: Path, root: Path | None = None) -> bool:
    name = path.name.casefold()
    scoped = path
    if root is not None:
        try:
            scoped = path.relative_to(root)
        except ValueError:
            return True
    sensitive_parts = [part.casefold() for part in scoped.parts]
    return (
        name in SECRET_NAMES
        or name == ".env"
        or name.startswith(".env.")
        or path.suffix.casefold() in SECRET_SUFFIXES
        or any(
            part in SECRET_DIRECTORY_NAMES
            for part in sensitive_parts[:-1]
        )
        or (
            path.suffix.casefold() not in SOURCE_SUFFIXES
            and SECRET_PATH_TERM.search(name) is not None
        )
    )


def discover_files(root: Path, max_files: int) -> tuple[list[Path], list[dict[str, str]]]:
    files: list[Path] = []
    gaps: list[dict[str, str]] = []
    for current, directories, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in sorted(directories):
            candidate = current_path / name
            if name.casefold() in EXCLUDED_DIRECTORIES:
                continue
            if is_link_or_junction(candidate) or not resolves_within(candidate, root):
                gaps.append({"kind": "link-or-boundary-skipped", "path": posix(candidate, root)})
                continue
            kept.append(name)
        directories[:] = kept
        for name in sorted(names):
            candidate = current_path / name
            if is_link_or_junction(candidate) or not resolves_within(candidate, root):
                gaps.append({"kind": "link-or-boundary-skipped", "path": posix(candidate, root)})
                continue
            files.append(candidate)
            if len(files) >= max_files:
                gaps.append({"kind": "file-limit-reached", "path": posix(current_path, root)})
                return files, gaps
    return files, gaps


def read_text(path: Path, root: Path, max_bytes: int, gaps: list[dict[str, str]]) -> str | None:
    if is_link_or_junction(path) or not resolves_within(path, root):
        gaps.append({"kind": "link-or-boundary-skipped", "path": posix(path, root)})
        return None
    if is_secret_path(path, root):
        gaps.append({"kind": "secret-path-skipped", "path": posix(path, root)})
        return None
    try:
        size = path.stat().st_size
        if size > max_bytes:
            gaps.append({"kind": "file-too-large", "path": posix(path, root)})
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        gaps.append({"kind": "unreadable-or-binary", "path": posix(path, root)})
        return None


def fact_id(fact: dict[str, Any]) -> str:
    payload = json.dumps(fact, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "fact:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def add_fact(facts: list[dict[str, Any]], *, kind: str, name: str, value: str, certainty: str,
             project_id: str, path: str, line: int | None = None, **metadata: str) -> None:
    source: dict[str, Any] = {"type": "file", "path": path}
    if line is not None:
        source["line"] = line
    fact: dict[str, Any] = {
        "project_id": project_id, "kind": kind, "name": name, "value": value,
        "certainty": certainty, "source": source,
    }
    fact.update(metadata)
    fact["id"] = fact_id(fact)
    facts.append(fact)


def xml_text(element: ET.Element | None, name: str, namespace: str) -> str | None:
    if element is None:
        return None
    child = element.find(f"{namespace}{name}")
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def parse_pom(path: Path, root: Path, text: str, facts: list[dict[str, Any]], gaps: list[dict[str, str]]) -> dict[str, Any] | None:
    label = posix(path, root)
    if re.search(r"<!DOCTYPE|<!ENTITY", text, re.IGNORECASE):
        gaps.append({"kind": "unsafe-xml-declaration", "path": label})
        return None
    try:
        model = ET.fromstring(text)
    except ET.ParseError:
        gaps.append({"kind": "invalid-pom", "path": label})
        return None
    namespace = ""
    if model.tag.startswith("{"):
        namespace = model.tag[: model.tag.index("}") + 1]
    project_id = "project:" + str(Path(label).parent).replace("\\", "/")
    module_paths = [item.text.strip() for item in model.findall(f"{namespace}modules/{namespace}module") if item.text]
    parent = model.find(f"{namespace}parent")
    parent_group = xml_text(parent, "groupId", namespace)
    parent_artifact = xml_text(parent, "artifactId", namespace)
    parent_version = xml_text(parent, "version", namespace)
    if parent_group == "org.springframework.boot" and parent_artifact == "spring-boot-starter-parent" and parent_version:
        certainty = "inferred" if "${" in parent_version else "declared"
        add_fact(facts, kind="platform.version", name="spring-boot", value=parent_version,
                 certainty=certainty, project_id=project_id, path=label)
    properties = model.find(f"{namespace}properties")
    if properties is not None:
        for child in list(properties):
            key = child.tag.split("}")[-1]
            value = (child.text or "").strip()
            if not value:
                continue
            if key in {"java.version", "maven.compiler.release", "kotlin.version", "spring-cloud.version", "spring-boot.version"}:
                kind = "language.version" if key in {"java.version", "maven.compiler.release", "kotlin.version"} else "platform.version"
                add_fact(facts, kind=kind, name=key, value=value, certainty="declared",
                         project_id=project_id, path=label)
    def record_dependency(dependency: ET.Element, role: str) -> None:
        group = xml_text(dependency, "groupId", namespace)
        artifact = xml_text(dependency, "artifactId", namespace)
        version = xml_text(dependency, "version", namespace) or "managed-or-unresolved"
        if group and artifact:
            certainty = "inferred" if version == "managed-or-unresolved" or "${" in version else "declared"
            add_fact(facts, kind="dependency.declared", name=f"{group}:{artifact}", value=version,
                     certainty=certainty, project_id=project_id, path=label,
                     declaration_role=role, scope=xml_text(dependency, "scope", namespace) or "compile")

    dependencies = model.find(f"{namespace}dependencies")
    if dependencies is not None:
        for dependency in dependencies.findall(f"{namespace}dependency"):
            record_dependency(dependency, "direct")
    managed = model.find(f"{namespace}dependencyManagement/{namespace}dependencies")
    if managed is not None:
        for dependency in managed.findall(f"{namespace}dependency"):
            record_dependency(dependency, "dependency-management")
    for profile in model.findall(f"{namespace}profiles/{namespace}profile"):
        profile_id = xml_text(profile, "id", namespace) or "unnamed"
        profile_dependencies = profile.find(f"{namespace}dependencies")
        if profile_dependencies is not None:
            for dependency in profile_dependencies.findall(f"{namespace}dependency"):
                record_dependency(dependency, f"profile:{profile_id}")
    def record_plugin(plugin: ET.Element, role: str) -> None:
        group = xml_text(plugin, "groupId", namespace) or "org.apache.maven.plugins"
        artifact = xml_text(plugin, "artifactId", namespace)
        version = xml_text(plugin, "version", namespace) or "managed-or-unresolved"
        if artifact:
            add_fact(facts, kind="plugin.version", name=f"{group}:{artifact}", value=version,
                     certainty="inferred" if "${" in version or version == "managed-or-unresolved" else "declared",
                     project_id=project_id, path=label, declaration_role=role)

    plugins = model.find(f"{namespace}build/{namespace}plugins")
    if plugins is not None:
        for plugin in plugins.findall(f"{namespace}plugin"):
            record_plugin(plugin, "direct")
    managed_plugins = model.find(f"{namespace}build/{namespace}pluginManagement/{namespace}plugins")
    if managed_plugins is not None:
        for plugin in managed_plugins.findall(f"{namespace}plugin"):
            record_plugin(plugin, "plugin-management")
    for profile in model.findall(f"{namespace}profiles/{namespace}profile"):
        profile_id = xml_text(profile, "id", namespace) or "unnamed"
        profile_plugins = profile.find(f"{namespace}build/{namespace}plugins")
        if profile_plugins is not None:
            for plugin in profile_plugins.findall(f"{namespace}plugin"):
                record_plugin(plugin, f"profile:{profile_id}")
    module_ids: list[str] = []
    parent = PurePosixPath(Path(label).parent.as_posix())
    for module in module_paths:
        module_path = PurePosixPath(module)
        if not module or "\\" in module or module_path.is_absolute() or ".." in module_path.parts or module_path.as_posix() != module:
            gaps.append({"kind": "invalid-module-path", "path": label})
            continue
        module_ids.append("project:" + (parent / module_path).as_posix())
    return {"id": project_id, "path": str(Path(label).parent).replace("\\", "/"), "build_system": "maven", "descriptor": label, "module_ids": module_ids}


def strip_gradle_comments(text: str) -> str:
    characters = list(text)
    index = 0
    quote: str | None = None
    while index < len(characters):
        current = characters[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = None
            index += 1
            continue
        if current in {"'", '"'}:
            quote = current
            index += 1
            continue
        if current == "/" and index + 1 < len(characters) and characters[index + 1] == "/":
            characters[index] = characters[index + 1] = " "
            index += 2
            while index < len(characters) and characters[index] not in {"\r", "\n"}:
                characters[index] = " "
                index += 1
            continue
        if current == "/" and index + 1 < len(characters) and characters[index + 1] == "*":
            characters[index] = characters[index + 1] = " "
            index += 2
            while index + 1 < len(characters) and not (characters[index] == "*" and characters[index + 1] == "/"):
                if characters[index] not in {"\r", "\n"}:
                    characters[index] = " "
                index += 1
            if index + 1 < len(characters):
                characters[index] = characters[index + 1] = " "
                index += 2
            continue
        index += 1
    return "".join(characters)


def gradle_plugin_blocks(text: str) -> list[tuple[int, str]]:
    blocks: list[tuple[int, str]] = []
    for match in re.finditer(r"\bplugins\s*\{", text):
        start = match.end()
        index = start
        depth = 1
        quote: str | None = None
        while index < len(text) and depth:
            current = text[index]
            if quote:
                if current == "\\":
                    index += 2
                    continue
                if current == quote:
                    quote = None
            elif current in {"'", '"'}:
                quote = current
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
            index += 1
        if depth == 0:
            blocks.append((start, text[start : index - 1]))
    return blocks


def parse_gradle(
    path: Path,
    root: Path,
    text: str,
    facts: list[dict[str, Any]],
    plugin_applications: list[dict[str, Any]],
) -> dict[str, Any]:
    label = posix(path, root)
    project_id = "project:" + str(Path(label).parent).replace("\\", "/")
    sanitized = strip_gradle_comments(text)
    for match in GRADLE_DEPENDENCY.finditer(sanitized):
        configuration, coordinate = match.groups()
        parts = coordinate.split(":")
        name = ":".join(parts[:2]) if len(parts) >= 2 else coordinate
        value = parts[2] if len(parts) >= 3 else "unresolved"
        add_fact(facts, kind="dependency.declared", name=name, value=value, certainty="inferred",
                 project_id=project_id, path=label, line=sanitized.count("\n", 0, match.start()) + 1,
                 declaration_role="gradle-heuristic", scope=configuration)
    for block_start, block in gradle_plugin_blocks(sanitized):
        for match in GRADLE_PLUGIN.finditer(block):
            plugin = match.group(1) or match.group(2)
            version = match.group(3) or match.group(4)
            apply_state = match.group(5) or match.group(6)
            line = sanitized.count("\n", 0, block_start + match.start()) + 1
            role = "gradle-plugin-block:apply-false" if apply_state == "false" else "gradle-plugin-block"
            add_fact(facts, kind="plugin.version", name=plugin, value=version, certainty="inferred",
                     project_id=project_id, path=label, line=line, declaration_role=role)
            if plugin == "org.springframework.boot" and apply_state != "false":
                add_fact(facts, kind="platform.version", name="spring-boot", value=version, certainty="inferred",
                         project_id=project_id, path=label, line=line, declaration_role="gradle-plugin-block")
        for match in GRADLE_KOTLIN_PLUGIN.finditer(block):
            plugin = f"org.jetbrains.kotlin.{match.group(1)}"
            version = match.group(2) or match.group(3)
            line = sanitized.count("\n", 0, block_start + match.start()) + 1
            add_fact(facts, kind="plugin.version", name=plugin, value=version, certainty="inferred",
                     project_id=project_id, path=label, line=line, declaration_role="gradle-kotlin-plugin-block")
        for match in GRADLE_PLUGIN_APPLICATION.finditer(block):
            if (match.group(3) or match.group(4)) == "false":
                continue
            plugin_applications.append({
                "project_id": project_id,
                "plugin": match.group(1) or match.group(2),
                "path": label,
                "line": sanitized.count("\n", 0, block_start + match.start()) + 1,
            })
        for match in GRADLE_PLUGIN_ALIAS.finditer(block):
            if (match.group(2) or match.group(3)) == "false":
                continue
            alias = match.group(1).replace("-", ".").replace("_", ".")
            add_fact(facts, kind="plugin.alias.applied", name=alias, value="present", certainty="inferred",
                     project_id=project_id, path=label,
                     line=sanitized.count("\n", 0, block_start + match.start()) + 1)
    return {"id": project_id, "path": str(Path(label).parent).replace("\\", "/"), "build_system": "gradle", "descriptor": label, "module_ids": []}


def parse_gradle_settings(
    path: Path, root: Path, text: str, gaps: list[dict[str, str]]
) -> tuple[str, list[str]]:
    label = posix(path, root)
    parent = PurePosixPath(Path(label).parent.as_posix())
    sanitized = strip_gradle_comments(text)
    module_ids: set[str] = set()
    lines = sanitized.splitlines()
    index = 0
    while index < len(lines):
        match = GRADLE_INCLUDE_START.match(lines[index])
        if match is None:
            index += 1
            continue
        arguments = match.group(1).strip()
        if arguments.startswith("("):
            depth = arguments.count("(") - arguments.count(")")
            while depth > 0 and index + 1 < len(lines):
                index += 1
                continuation = lines[index].strip()
                arguments += "\n" + continuation
                depth += continuation.count("(") - continuation.count(")")
            if depth != 0 or not arguments.endswith(")"):
                gaps.append({"kind": "unresolved-gradle-module-include", "path": label})
                index += 1
                continue
            arguments = arguments[1:-1]
        else:
            while arguments.rstrip().endswith(",") and index + 1 < len(lines):
                index += 1
                arguments += "\n" + lines[index].strip()
        literals = GRADLE_STRING.findall(arguments or "")
        remainder = GRADLE_STRING.sub("", arguments or "")
        if not literals or remainder.strip(" \t\r\n,"):
            gaps.append({"kind": "unresolved-gradle-module-include", "path": label})
            index += 1
            continue
        for literal in literals:
            logical = literal.removeprefix(":").replace(":", "/")
            module = PurePosixPath(logical)
            if (
                not logical
                or "\\" in logical
                or module.is_absolute()
                or ".." in module.parts
                or module.as_posix() != logical
            ):
                gaps.append({"kind": "invalid-module-path", "path": label})
                continue
            module_ids.add("project:" + (parent / module).as_posix())
        index += 1
    if re.search(r"(?m)^\s*includeBuild\b", sanitized):
        gaps.append({"kind": "unresolved-gradle-composite-build", "path": label})
    if re.search(r"(?m)^\s*includeFlat\b", sanitized):
        gaps.append({"kind": "unresolved-gradle-flat-include", "path": label})
    if re.search(r"\.projectDir\s*=", sanitized):
        gaps.append({"kind": "unresolved-gradle-projectdir-remap", "path": label})
    project_path = parent.as_posix()
    return project_path, sorted(module_ids)


def catalog_version(value: object, versions: dict[str, object]) -> tuple[str, str]:
    if isinstance(value, str):
        return value, "declared"
    if isinstance(value, dict):
        reference = value.get("ref")
        if isinstance(reference, str):
            resolved = versions.get(reference)
            if isinstance(resolved, str):
                return resolved, "declared"
            if isinstance(resolved, dict):
                for key in ("strictly", "require", "prefer"):
                    if isinstance(resolved.get(key), str):
                        return str(resolved[key]), "declared"
            return f"unresolved-ref:{reference}", "inferred"
        for key in ("strictly", "require", "prefer"):
            if isinstance(value.get(key), str):
                return str(value[key]), "declared"
    return "unresolved", "inferred"


def parse_version_catalog(
    path: Path,
    root: Path,
    text: str,
    facts: list[dict[str, Any]],
    gaps: list[dict[str, str]],
    project_id: str,
) -> None:
    label = posix(path, root)
    try:
        catalog = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        gaps.append({"kind": "invalid-version-catalog", "path": label})
        return
    versions = catalog.get("versions", {})
    if not isinstance(versions, dict):
        versions = {}
    for alias, value in sorted(versions.items()):
        version, certainty = catalog_version(value, versions)
        add_fact(facts, kind="catalog.version", name=str(alias), value=version, certainty=certainty,
                 project_id=project_id, path=label, declaration_role="version-catalog")
    libraries = catalog.get("libraries", {})
    if isinstance(libraries, dict):
        for alias, value in sorted(libraries.items()):
            coordinate: str | None = None
            version_value: object = None
            if isinstance(value, str):
                parts = value.split(":")
                if len(parts) >= 2:
                    coordinate = ":".join(parts[:2])
                    version_value = parts[2] if len(parts) >= 3 else None
            elif isinstance(value, dict):
                if isinstance(value.get("module"), str):
                    coordinate = str(value["module"])
                elif isinstance(value.get("group"), str) and isinstance(value.get("name"), str):
                    coordinate = f"{value['group']}:{value['name']}"
                version_value = value.get("version")
            if coordinate:
                version, certainty = catalog_version(version_value, versions)
                add_fact(facts, kind="dependency.declared", name=coordinate, value=version, certainty=certainty,
                         project_id=project_id, path=label, declaration_role="version-catalog", scope=f"alias:{alias}")
    plugins = catalog.get("plugins", {})
    if isinstance(plugins, dict):
        for alias, value in sorted(plugins.items()):
            if not isinstance(value, dict) or not isinstance(value.get("id"), str):
                continue
            version, certainty = catalog_version(value.get("version"), versions)
            normalized_alias = str(alias).replace("-", ".").replace("_", ".")
            add_fact(facts, kind="plugin.version", name=str(value["id"]), value=version, certainty=certainty,
                     project_id=project_id, path=label, declaration_role="version-catalog", scope=f"alias:{normalized_alias}")


def config_keys(path: Path, text: str) -> list[tuple[str, int]]:
    if path.suffix == ".properties":
        return [(match.group(1), number) for number, line in enumerate(text.splitlines(), 1) if (match := PROPERTY_LINE.match(line))]
    stack: list[tuple[int, str]] = []
    result: list[tuple[str, int]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith(("#", "-")):
            continue
        match = YAML_KEY.match(line)
        if not match:
            continue
        indent = len(match.group(1).replace("\t", "    "))
        key = match.group(2)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, key))
        result.append((".".join(item[1] for item in stack), number))
    return result


def collect(root: Path, max_files: int, max_file_bytes: int) -> dict[str, Any]:
    files, gaps = discover_files(root, max_files)
    settings_text: dict[Path, str | None] = {}
    gradle_settings: list[tuple[str, str, list[str]]] = []
    for path in files:
        if path.name not in {"settings.gradle", "settings.gradle.kts"}:
            continue
        text = read_text(path, root, max_file_bytes, gaps)
        settings_text[path] = text
        if text is not None:
            project_path, module_ids = parse_gradle_settings(path, root, text, gaps)
            gradle_settings.append((posix(path, root), project_path, module_ids))
    descriptor_roots = {
        path.parent for path in files if path.name in {"pom.xml", "build.gradle", "build.gradle.kts"}
    }
    settings_project_roots = {
        absolute_from_posix(root, project_path)
        for _, project_path, _ in gradle_settings
    }
    settings_module_roots = {
        absolute_from_posix(root, module_id.removeprefix("project:"))
        for _, _, module_ids in gradle_settings
        for module_id in module_ids
    }
    project_roots = sorted(
        descriptor_roots | settings_project_roots | settings_module_roots,
        key=lambda path: (-len(path.relative_to(root).parts), posix(path, root)),
    )
    gradle_descriptor_roots = {
        path.parent for path in files if path.name in {"build.gradle", "build.gradle.kts"}
    }
    standalone_gradle_roots = {
        path for path in gradle_descriptor_roots
        if nearest_ancestor(path, sorted(
            settings_project_roots,
            key=lambda item: (-len(item.relative_to(root).parts), posix(item, root)),
        )) is None
    }
    gradle_build_roots = sorted(
        settings_project_roots | standalone_gradle_roots,
        key=lambda path: (-len(path.relative_to(root).parts), posix(path, root)),
    )
    facts: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    deployment: list[str] = []
    excluded: list[dict[str, str]] = []
    gradle_plugin_applications: list[dict[str, Any]] = []
    for path in files:
        label = posix(path, root)
        if is_secret_path(path, root):
            excluded.append({"path": label, "reason": "secret-like path"})
            continue
        name = path.name
        suffix = path.suffix.casefold()
        relevant = name == "pom.xml" or name in {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "gradle-wrapper.properties", "libs.versions.toml"} or suffix in CONFIG_SUFFIXES or suffix in SOURCE_SUFFIXES
        if name in {"Dockerfile", "compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml", "Chart.yaml"} or any(part in {"k8s", "kubernetes", "helm"} for part in path.parts):
            deployment.append(label)
            add_fact(facts, kind="deployment.signal", name=name, value="present", certainty="declared",
                     project_id=project_id_for_path(path, root, project_roots), path=label)
        if not relevant:
            continue
        text = settings_text[path] if path in settings_text else read_text(path, root, max_file_bytes, gaps)
        if text is None:
            continue
        if name == "pom.xml":
            project = parse_pom(path, root, text, facts, gaps)
            if project:
                projects.append(project)
        elif name in {"build.gradle", "build.gradle.kts"}:
            projects.append(parse_gradle(path, root, text, facts, gradle_plugin_applications))
        elif name in {"settings.gradle", "settings.gradle.kts"}:
            pass
        elif name == "gradle-wrapper.properties":
            match = re.search(r"gradle-([0-9][^-/]*)-(?:bin|all)\.zip", text)
            if match:
                add_fact(facts, kind="build-tool.version", name="gradle-wrapper", value=match.group(1),
                         certainty="declared", project_id=project_id_for_path(path, root, project_roots), path=label)
        elif name == "libs.versions.toml":
            parse_version_catalog(
                path, root, text, facts, gaps, project_id_for_path(path, root, project_roots)
            )
        elif suffix in CONFIG_SUFFIXES and (name.startswith("application") or name.startswith("bootstrap")):
            for key, line in config_keys(path, text):
                add_fact(facts, kind="config.key", name=key, value="present", certainty="declared",
                         project_id=project_id_for_path(path, root, project_roots), path=label, line=line)
        elif suffix in SOURCE_SUFFIXES:
            test_path = any(part in {"test", "testFixtures", "integrationTest"} for part in path.parts)
            for token in TEST_SIGNALS if test_path else SOURCE_SIGNALS:
                for match in re.finditer(re.escape(token), text):
                    add_fact(facts, kind="test.signal" if test_path else "code.signal", name=token,
                             value="present", certainty="declared",
                             project_id=project_id_for_path(path, root, project_roots), path=label,
                             line=text.count("\n", 0, match.start()) + 1)
    for descriptor, project_path, module_ids in gradle_settings:
        matching = [project for project in projects if project["build_system"] == "gradle" and project["path"] == project_path]
        if matching:
            for project in matching:
                project["module_ids"] = module_ids
        else:
            projects.append({
                "id": "project:" + project_path,
                "path": project_path,
                "build_system": "gradle",
                "descriptor": descriptor,
                "module_ids": module_ids,
            })
        existing_ids = {project["id"] for project in projects}
        for module_id in module_ids:
            if module_id not in existing_ids:
                projects.append({
                    "id": module_id,
                    "path": module_id.removeprefix("project:"),
                    "build_system": "gradle",
                    "descriptor": descriptor,
                    "module_ids": [],
                })
                existing_ids.add(module_id)
    unique_projects = {project["id"] + "|" + project["descriptor"]: project for project in projects}
    if not unique_projects:
        gaps.append({"kind": "no-build-descriptor", "path": "."})
    applied_aliases = [fact for fact in facts if fact["kind"] == "plugin.alias.applied"]
    catalog_boot_plugins = [
        fact for fact in facts
        if fact["kind"] == "plugin.version"
        and fact["name"] == "org.springframework.boot"
        and fact.get("declaration_role") == "version-catalog"
        and VERSION_LITERAL.fullmatch(fact["value"])
    ]
    for applied in applied_aliases:
        for catalog in catalog_boot_plugins:
            applied_root = nearest_ancestor(
                absolute_from_posix(root, applied["source"]["path"]), gradle_build_roots
            )
            catalog_root = nearest_ancestor(
                absolute_from_posix(root, catalog["source"]["path"]), gradle_build_roots
            )
            if applied_root == catalog_root and catalog.get("scope") == f"alias:{applied['name']}":
                add_fact(
                    facts, kind="platform.version", name="spring-boot", value=catalog["value"], certainty="inferred",
                    project_id=applied["project_id"], path=applied["source"]["path"],
                    line=applied["source"].get("line"), declaration_role="applied-version-catalog",
                    catalog_source=catalog["source"]["path"],
                )
    direct_boot_declarations = [
        fact for fact in facts
        if fact["kind"] == "plugin.version"
        and fact["name"] == "org.springframework.boot"
        and fact.get("declaration_role") == "gradle-plugin-block:apply-false"
        and VERSION_LITERAL.fullmatch(fact["value"])
    ]
    for applied in gradle_plugin_applications:
        if applied["plugin"] != "org.springframework.boot":
            continue
        application_parent = PurePosixPath(applied["path"]).parent
        application_root = nearest_ancestor(
            absolute_from_posix(root, applied["path"]), gradle_build_roots
        )
        candidates = [
            fact for fact in direct_boot_declarations
            if PurePosixPath(fact["source"]["path"]).parent in application_parent.parents
            and nearest_ancestor(
                absolute_from_posix(root, fact["source"]["path"]), gradle_build_roots
            ) == application_root
        ]
        if not candidates:
            continue
        nearest_depth = max(len(PurePosixPath(fact["source"]["path"]).parent.parts) for fact in candidates)
        for declaration in candidates:
            declaration_parent = PurePosixPath(declaration["source"]["path"]).parent
            if len(declaration_parent.parts) != nearest_depth:
                continue
            add_fact(
                facts, kind="platform.version", name="spring-boot", value=declaration["value"],
                certainty="inferred", project_id=applied["project_id"], path=applied["path"],
                line=applied["line"], declaration_role="applied-root-plugin-declaration",
                scope=f"declared-at:{declaration['source']['path']}",
            )
    unique_facts: dict[str, dict[str, Any]] = {}
    for fact in facts:
        existing = unique_facts.get(fact["id"])
        if existing is not None and existing != fact:
            gaps.append({"kind": "fact-id-collision", "path": fact["source"]["path"]})
            continue
        unique_facts[fact["id"]] = fact
    facts = sorted(
        unique_facts.values(),
        key=lambda item: (item["kind"], item["name"], item["source"]["path"], item["source"].get("line", 0), item["value"], item["id"]),
    )
    version_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for fact in facts:
        if fact["kind"] in {"build-tool.version", "language.version", "platform.version", "plugin.version"}:
            normalized_name = "spring-boot" if fact["name"] == "spring-boot.version" else fact["name"]
            version_groups.setdefault((fact["project_id"], fact["kind"], normalized_name), []).append(fact)
    conflicts = [
        {
            "project_id": key[0], "kind": key[1], "name": key[2],
            "values": sorted({item["value"] for item in items}),
            "fact_ids": sorted(item["id"] for item in items),
        }
        for key, items in sorted(version_groups.items())
        if len({item["value"] for item in items}) > 1
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": {"root": "."},
        "collection": {
            "collector_version": "0.1.0", "mode": "static", "network_used": False,
            "build_executed": False, "provenance": None,
        },
        "projects": sorted(unique_projects.values(), key=lambda item: (item["path"], item["descriptor"])),
        "facts": facts,
        "conflicts": conflicts,
        "gaps": sorted(gaps, key=lambda item: (item["kind"], item["path"])),
        "redaction": {"configuration_values_omitted": True, "environment_read": False},
        "excluded": sorted(excluded, key=lambda item: item["path"]),
        "deployment_paths": sorted(set(deployment)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect deterministic, redacted Spring repository evidence.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-files", type=int, default=50_000)
    parser.add_argument("--max-file-bytes", type=int, default=2_097_152)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"repository root is not a directory: {root}")
    result = collect(root, args.max_files, args.max_file_bytes)
    rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
