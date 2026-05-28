from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_NAME = "zh_native_channel_config.json"


@dataclass(frozen=True)
class DartField:
    name: str
    dart_type: str
    nullable: bool

@dataclass(frozen=True)
class MessageClass:
    class_name: str
    swift_name: str
    channel_name: str
    fields: list[DartField]

@dataclass(frozen=True)
class HandlerClass:
    class_name: str
    channel_name: str
    file_path: Path | None = None
    package_name: str | None = None

@dataclass(frozen=True)
class IOSGeneratorConfig:
    message_scan_path: Path
    handler_scan_path: Path
    output_root: Path
    generated_registrations_output_path: Path
    method_channel_name: str
    xcode_project_path: Path | None

@dataclass(frozen=True)
class AndroidGeneratorConfig:
    handler_scan_path: Path
    output_root: Path
    generated_registrations_output_path: Path
    package_name: str
    method_channel_name: str

@dataclass(frozen=True)
class WebGeneratorConfig:
    handler_scan_path: Path
    output_root: Path
    generated_registrations_output_path: Path
    global_name: str
    method_channel_name: str

def _read_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Config root must be a JSON object.")
    return config

def _read_ios_config(config: dict, config_root: Path) -> IOSGeneratorConfig:
    package_message_scan_path = _read_config_string(
        config,
        ("common", "packageMessageScanPath"),
        legacy_key="packageMessageScanPath",
    )
    method_channel_name = _read_config_string(
        config,
        ("common", "methodChannelName"),
        legacy_key="methodChannelName",
        default="ZHNativeChannel",
    )
    handler_scan_path = _read_optional_config_string(
        config,
        ("platforms", "ios", "handlerScanPath"),
        legacy_key="handlerIOSScanPath",
    )
    output_root = _read_config_string(
        config,
        ("platforms", "ios", "outputRoot"),
        legacy_key="outputRoot",
    )
    xcode_project_path = _read_optional_config_string(
        config,
        ("platforms", "ios", "xcodeProjectPath"),
        legacy_key="xcodeProjectPath",
    )

    resolved_output_root = _resolve_config_path(output_root, config_root)
    resolved_xcode_project_path = (
        _resolve_config_path(xcode_project_path, config_root)
        if xcode_project_path is not None
        else _guess_xcode_project_path(resolved_output_root)
    )

    resolved_handler_scan_path = _resolve_optional_config_path(
        handler_scan_path,
        config_root,
    )

    return IOSGeneratorConfig(
        message_scan_path=_resolve_config_path(package_message_scan_path, config_root),
        handler_scan_path=resolved_handler_scan_path,
        output_root=resolved_output_root,
        generated_registrations_output_path=_read_generated_registrations_output_path(
            config,
            "ios",
            handler_scan_path,
            resolved_handler_scan_path,
            config_root,
        ),
        method_channel_name=method_channel_name,
        xcode_project_path=resolved_xcode_project_path,
    )

def _read_android_config(
    config: dict,
    config_root: Path,
) -> AndroidGeneratorConfig | None:
    android_config = _read_optional_platform_config(config, "android")
    if android_config is None:
        return None

    handler_scan_path = _read_optional_config_string(
        config,
        ("platforms", "android", "handlerScanPath"),
    )
    output_root = _read_config_string(config, ("platforms", "android", "outputRoot"))
    package_name = _read_config_string(config, ("platforms", "android", "packageName"))
    method_channel_name = _read_config_string(
        config,
        ("common", "methodChannelName"),
        legacy_key="methodChannelName",
        default="ZHNativeChannel",
    )

    resolved_handler_scan_path = _resolve_optional_config_path(
        handler_scan_path,
        config_root,
    )

    return AndroidGeneratorConfig(
        handler_scan_path=resolved_handler_scan_path,
        output_root=_resolve_config_path(output_root, config_root),
        generated_registrations_output_path=_read_generated_registrations_output_path(
            config,
            "android",
            handler_scan_path,
            resolved_handler_scan_path,
            config_root,
        ),
        package_name=package_name,
        method_channel_name=method_channel_name,
    )

def _read_web_config(config: dict, config_root: Path) -> WebGeneratorConfig | None:
    web_config = _read_optional_platform_config(config, "web")
    if web_config is None:
        return None

    handler_scan_path = _read_optional_config_string(
        config,
        ("platforms", "web", "handlerScanPath"),
    )
    output_root = _read_config_string(config, ("platforms", "web", "outputRoot"))
    global_name = _read_config_string(
        config,
        ("platforms", "web", "globalName"),
        default="ZHNativeChannel",
    )
    method_channel_name = _read_config_string(
        config,
        ("common", "methodChannelName"),
        legacy_key="methodChannelName",
        default="ZHNativeChannel",
    )

    resolved_handler_scan_path = _resolve_optional_config_path(
        handler_scan_path,
        config_root,
    )

    return WebGeneratorConfig(
        handler_scan_path=resolved_handler_scan_path,
        output_root=_resolve_config_path(output_root, config_root),
        generated_registrations_output_path=_read_generated_registrations_output_path(
            config,
            "web",
            handler_scan_path,
            resolved_handler_scan_path,
            config_root,
        ),
        global_name=global_name,
        method_channel_name=method_channel_name,
    )

def _read_optional_platform_config(config: dict, platform: str) -> dict | None:
    platforms = config.get("platforms")
    if not isinstance(platforms, dict):
        return None
    platform_config = platforms.get(platform)
    if not isinstance(platform_config, dict) or not platform_config:
        return None
    return platform_config

def _read_config_string(
    config: dict,
    path: tuple[str, ...],
    *,
    legacy_key: str | None = None,
    default: str | None = None,
) -> str:
    value = _read_optional_config_string(config, path, legacy_key=legacy_key)
    if value is not None:
        return value
    if default is not None:
        return default
    path_text = ".".join(path)
    legacy_text = f" or legacy field '{legacy_key}'" if legacy_key else ""
    raise ValueError(
        f"Config field '{path_text}'{legacy_text} must be a non-empty string."
    )

def _read_optional_config_string(
    config: dict,
    path: tuple[str, ...],
    *,
    legacy_key: str | None = None,
) -> str | None:
    current: object = config
    for key in path:
        if not isinstance(current, dict) or key not in current:
            current = None
            break
        current = current[key]

    if isinstance(current, str) and current.strip():
        return current.strip()

    if legacy_key is not None:
        legacy_value = config.get(legacy_key)
        if isinstance(legacy_value, str) and legacy_value.strip():
            return legacy_value.strip()

    return None

def _resolve_config_path(path: str, config_root: Path) -> Path:
    output_path = Path(path)
    if output_path.is_absolute():
        return output_path
    return config_root / output_path

def _resolve_optional_config_path(path: str | None, config_root: Path) -> Path:
    if path is None:
        return config_root
    return _resolve_config_path(path, config_root)

def _read_generated_registrations_output_path(
    config: dict,
    platform: str,
    handler_scan_path: str | None,
    resolved_handler_scan_path: Path,
    config_root: Path,
) -> Path:
    output_path = _read_optional_config_string(
        config,
        ("platforms", platform, "generatedChannelRegistrationsOutputPath"),
    )
    if output_path is None:
        output_path = _read_optional_config_string(
            config,
            ("common", "generatedChannelRegistrationsOutputPath"),
        )
    if output_path is not None:
        return _resolve_config_path(output_path, config_root)
    if handler_scan_path is None:
        return config_root
    return resolved_handler_scan_path.parent

def _guess_xcode_project_path(output_root: Path) -> Path | None:
    for parent in [output_root, *output_root.parents]:
        runner_project = parent / "Runner.xcodeproj" / "project.pbxproj"
        if runner_project.exists():
            return runner_project
    return None

def _scan_messages(scan_path: Path) -> list[MessageClass]:
    if not scan_path.exists():
        scan_path.mkdir(parents=True, exist_ok=True)

    messages: list[MessageClass] = []
    for dart_file in sorted(scan_path.rglob("*.dart")):
        if dart_file.name.endswith(".g.dart"):
            continue
        messages.extend(_parse_message_file(dart_file))
    return sorted(messages, key=lambda item: item.swift_name)

def _parse_message_file(dart_file: Path) -> list[MessageClass]:
    source = dart_file.read_text(encoding="utf-8")
    results: list[MessageClass] = []

    for class_name, annotations, body in _iter_annotated_classes(source):
        channel_msg = _read_annotation_value(annotations, "ChannelMsg")
        if channel_msg is None:
            continue

        channel_name = channel_msg or class_name
        results.append(
            MessageClass(
                class_name=class_name,
                swift_name=class_name,
                channel_name=channel_name,
                fields=_parse_fields(body),
            )
        )
    return results

def _parse_platform_handler_file(source_file: Path) -> list[HandlerClass]:
    source = source_file.read_text(encoding="utf-8")
    pattern = re.compile(
        r"//\s*PlatformChannelHandler(?:\(\s*(?:\"(?P<key>[^\"]+)\"|'(?P<single_key>[^']+)')?\s*\))?"
        r"\s*\n\s*(?:export\s+)?(?:final\s+)?(?:class|object|struct|function)\s+"
        r"(?P<class_name>[A-Za-z_]\w*)",
        re.MULTILINE,
    )

    handlers: list[HandlerClass] = []
    for match in pattern.finditer(source):
        explicit_key = match.group("key") or match.group("single_key")
        class_name = match.group("class_name")
        if not explicit_key:
            raise ValueError(
                f"// PlatformChannelHandler on {class_name} in {source_file} must provide a key."
            )
        handlers.append(
            HandlerClass(
                class_name=class_name,
                channel_name=explicit_key,
                file_path=source_file,
                package_name=None,
            )
        )
    return handlers

def _iter_annotated_classes(source: str) -> list[tuple[str, str, str]]:
    pattern = re.compile(
        r"(?P<annotations>(?:\s*@[^\n]+\n)+)\s*class\s+(?P<class_name>[A-Za-z_]\w*)"
        r"[^{]*\{(?P<body>.*?)\n\}",
        re.DOTALL,
    )
    return [
        (match.group("class_name"), match.group("annotations"), match.group("body"))
        for match in pattern.finditer(source)
    ]

def _read_annotation_value(annotations: str, annotation_name: str) -> str | None:
    annotation = re.search(
        rf"@{annotation_name}(?:\s*\(\s*(?:['\"](?P<value>[^'\"]+)['\"])?\s*\))?",
        annotations,
    )
    if annotation is None:
        return None
    return annotation.group("value") or ""

def _parse_fields(class_body: str) -> list[DartField]:
    fields: list[DartField] = []
    field_pattern = re.compile(
        r"^\s*(?:final\s+)?(?P<type>String|int|double|num|bool|Map<String,\s*dynamic>|List<[^>]+>)"
        r"(?P<nullable>\?)?\s+(?P<name>[A-Za-z_]\w*)\s*;",
        re.MULTILINE,
    )

    for match in field_pattern.finditer(class_body):
        fields.append(
            DartField(
                name=match.group("name"),
                dart_type=match.group("type"),
                nullable=match.group("nullable") == "?",
            )
        )
    return fields

def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def _header() -> list[str]:
    return [
        "// GENERATED CODE - DO NOT MODIFY BY HAND",
        "// Generated by zh_native_channel_generator/scripts/generate_native_channel.py",
        "",
    ]
