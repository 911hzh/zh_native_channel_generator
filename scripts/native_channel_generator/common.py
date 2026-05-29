from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_NAME = "zh_native_channel_config.json"
DEFAULT_DART_OUTPUT_DIRECTORY = "lib/base/zHNativeChannel"
DEFAULT_DART_MESSAGE_SCAN_PATH = "lib/base/zHNativeChannel/msgs"
DEFAULT_DART_HANDLER_SCAN_PATH = "lib/base/zHNativeChannel/handlers"
DEFAULT_DART_REGISTER_FILE_NAME = "ChannelGeneratedRegister.g.dart"
DEFAULT_IOS_OUTPUT_DIRECTORY = "ios/Runner/zHNativeChannel"
DEFAULT_ANDROID_OUTPUT_DIRECTORY = (
    "android/app/src/main/kotlin/com/example/zh_native_channel_example/zHNativeChannel"
)
DEFAULT_ANDROID_PACKAGE_NAME = "com.example.zh_native_channel_example.zHNativeChannel"
DEFAULT_WEB_OUTPUT_DIRECTORY = "web/zHNativeChannel"


@dataclass(frozen=True)
class DartField:
    """描述 channel 消息中可生成的平台字段。"""

    name: str
    dart_type: str
    nullable: bool

@dataclass(frozen=True)
class MessageClass:
    """描述 Dart @ChannelMsg 类及其平台侧元数据。"""

    class_name: str
    swift_name: str
    channel_name: str
    fields: list[DartField]

@dataclass(frozen=True)
class HandlerClass:
    """描述与 channel 名称匹配的手写平台 handler。"""

    class_name: str
    channel_name: str
    file_path: Path | None = None
    package_name: str | None = None

@dataclass(frozen=True)
class IOSGeneratorConfig:
    """保存 iOS 生成器使用的已解析路径。"""

    handler_scan_paths: list[Path]
    output_root: Path
    generated_messages_output_path: Path
    generated_registrations_output_path: Path
    xcode_project_path: Path | None

@dataclass(frozen=True)
class AndroidGeneratorConfig:
    """保存 Android 生成器使用的已解析路径和 package 信息。"""

    handler_scan_paths: list[Path]
    output_root: Path
    generated_messages_output_path: Path
    generated_registrations_output_path: Path
    package_name: str

@dataclass(frozen=True)
class WebGeneratorConfig:
    """保存 Web 生成器使用的已解析路径和浏览器桥接信息。"""

    handler_scan_paths: list[Path]
    output_root: Path
    generated_messages_output_path: Path
    generated_registrations_output_path: Path
    global_name: str

def _read_config(config_path: Path) -> dict:
    """读取并校验 JSON 配置根对象。"""

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Config root must be a JSON object.")
    return config

def _read_ios_config(config: dict, config_root: Path) -> IOSGeneratorConfig | None:
    """读取 iOS 配置块，并兼容旧版顶层配置。"""

    ios_config = _read_optional_platform_config(config, "ios")
    has_legacy_output_root = _read_optional_config_string(
        config,
        ("outputRoot",),
        legacy_key="outputRoot",
    )
    if ios_config is None and has_legacy_output_root is None:
        return None

    output_root = _read_config_string(
        config,
        ("platforms", "ios", "defaultOutputDirectory"),
        legacy_key="outputRoot",
        default=DEFAULT_IOS_OUTPUT_DIRECTORY,
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

    resolved_handler_scan_paths = _read_platform_scan_paths(
        config,
        "ios",
        config_root,
        legacy_key="handlerIOSScanPath",
    )

    return IOSGeneratorConfig(
        handler_scan_paths=resolved_handler_scan_paths,
        output_root=resolved_output_root,
        generated_messages_output_path=_read_generated_messages_output_path(
            config,
            "ios",
            resolved_output_root,
            config_root,
        ),
        generated_registrations_output_path=_read_generated_registrations_output_path(
            config,
            "ios",
            resolved_output_root,
            config_root,
        ),
        xcode_project_path=resolved_xcode_project_path,
    )

def _read_android_config(
    config: dict,
    config_root: Path,
) -> AndroidGeneratorConfig | None:
    """在启用 Android 生成时读取 Android 配置块。"""

    android_config = _read_optional_platform_config(config, "android")
    if android_config is None:
        return None

    output_root = _read_config_string(
        config,
        ("platforms", "android", "defaultOutputDirectory"),
        legacy_key="outputRoot",
        default=DEFAULT_ANDROID_OUTPUT_DIRECTORY,
    )
    package_name = _read_config_string(
        config,
        ("platforms", "android", "packageName"),
        default=DEFAULT_ANDROID_PACKAGE_NAME,
    )
    resolved_output_root = _resolve_config_path(output_root, config_root)

    return AndroidGeneratorConfig(
        handler_scan_paths=_read_platform_scan_paths(
            config,
            "android",
            config_root,
        ),
        output_root=resolved_output_root,
        generated_messages_output_path=_read_generated_messages_output_path(
            config,
            "android",
            resolved_output_root,
            config_root,
        ),
        generated_registrations_output_path=_read_generated_registrations_output_path(
            config,
            "android",
            resolved_output_root,
            config_root,
        ),
        package_name=package_name,
    )

def _read_web_config(config: dict, config_root: Path) -> WebGeneratorConfig | None:
    """在启用 Web 生成时读取 Web 配置块。"""

    web_config = _read_optional_platform_config(config, "web")
    if web_config is None:
        return None

    output_root = _read_config_string(
        config,
        ("platforms", "web", "defaultOutputDirectory"),
        legacy_key="outputRoot",
        default=DEFAULT_WEB_OUTPUT_DIRECTORY,
    )
    global_name = _read_config_string(
        config,
        ("platforms", "web", "globalName"),
        default="ZHNativeChannel",
    )
    resolved_output_root = _resolve_config_path(output_root, config_root)

    return WebGeneratorConfig(
        handler_scan_paths=_read_platform_scan_paths(
            config,
            "web",
            config_root,
        ),
        output_root=resolved_output_root,
        generated_messages_output_path=_read_generated_messages_output_path(
            config,
            "web",
            resolved_output_root,
            config_root,
        ),
        generated_registrations_output_path=_read_generated_registrations_output_path(
            config,
            "web",
            resolved_output_root,
            config_root,
        ),
        global_name=global_name,
    )

def _read_optional_platform_config(config: dict, platform: str) -> dict | None:
    """返回存在且非空的平台配置块。"""

    platforms = config.get("platforms")
    if not isinstance(platforms, dict):
        return None
    if platform not in platforms:
        return None
    platform_config = platforms.get(platform)
    if not isinstance(platform_config, dict):
        return None
    return platform_config

def _read_config_string(
    config: dict,
    path: tuple[str, ...],
    *,
    legacy_key: str | None = None,
    default: str | None = None,
) -> str:
    """读取必填字符串配置，并支持旧版字段兜底。"""

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
    """从嵌套配置或旧版位置读取可选字符串配置。"""

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
        legacy_common = config.get("common")
        if isinstance(legacy_common, dict):
            legacy_common_value = legacy_common.get(legacy_key)
            if isinstance(legacy_common_value, str) and legacy_common_value.strip():
                return legacy_common_value.strip()

    return None

def _read_optional_config_value(
    config: dict,
    path: tuple[str, ...],
    *,
    legacy_key: str | None = None,
) -> object | None:
    """从嵌套配置或旧版位置读取任意类型的可选配置。"""

    current: object = config
    for key in path:
        if not isinstance(current, dict) or key not in current:
            current = None
            break
        current = current[key]

    if current is not None:
        return current

    if legacy_key is not None:
        if legacy_key in config:
            return config[legacy_key]
        legacy_common = config.get("common")
        if isinstance(legacy_common, dict) and legacy_key in legacy_common:
            return legacy_common[legacy_key]

    return None

def _read_optional_config_string_list(
    config: dict,
    path: tuple[str, ...],
    *,
    legacy_key: str | None = None,
) -> list[str] | None:
    """读取字符串或字符串数组形式的可选配置。"""

    value = _read_optional_config_value(config, path, legacy_key=legacy_key)
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list) and all(
        isinstance(item, str) and item.strip() for item in value
    ):
        return [item.strip() for item in value]
    path_text = ".".join(path)
    raise ValueError(f"Config field '{path_text}' must be a string or string list.")

def _resolve_config_path(path: str, config_root: Path) -> Path:
    """将配置路径解析为相对于配置文件目录的路径。"""

    output_path = Path(path)
    if output_path.is_absolute():
        return output_path
    return config_root / output_path

def _resolve_optional_config_path(path: str | None, config_root: Path) -> Path:
    """解析可选路径；未配置时默认使用配置根目录。"""

    if path is None:
        return config_root
    return _resolve_config_path(path, config_root)

def _resolve_config_paths(paths: list[str], config_root: Path) -> list[Path]:
    """将多个配置路径解析为绝对或项目相对路径。"""

    return [_resolve_config_path(path, config_root) for path in paths]

def _read_platform_scan_paths(
    config: dict,
    platform: str,
    config_root: Path,
    *,
    legacy_key: str | None = None,
) -> list[Path]:
    """读取平台 handler 扫描目录，未配置时扫描项目根目录。"""

    scan_paths = _read_optional_config_string_list(
        config,
        ("platforms", platform, "scanHandlerPath"),
        legacy_key=legacy_key,
    )
    if scan_paths is None:
        scan_paths = _read_optional_config_string_list(
            config,
            ("platforms", platform, "handlerScanPath"),
            legacy_key=legacy_key,
        )
    if scan_paths is None:
        return [config_root]
    return _resolve_config_paths(scan_paths, config_root)

def _read_generated_registrations_output_path(
    config: dict,
    platform: str,
    default_output_directory: Path,
    config_root: Path,
) -> Path:
    """解析平台注册文件应该写入的位置。"""

    output_path = _read_optional_config_string(
        config,
        ("platforms", platform, "generatedChannelRegistrationsOutputPath"),
    )
    if output_path is None:
        output_path = _read_optional_config_string(
            config,
            ("common", "generatedChannelRegistrationsOutputPath"),
        )
    if output_path is None:
        output_path = _read_optional_config_string(
            config,
            ("generatedChannelRegistrationsOutputPath",),
        )
    if output_path is not None:
        return _resolve_config_path(output_path, config_root)
    return default_output_directory

def _read_generated_messages_output_path(
    config: dict,
    platform: str,
    output_root: Path,
    config_root: Path,
) -> Path:
    """解析平台消息文件应该写入的位置。"""

    output_path = _read_optional_config_string(
        config,
        ("platforms", platform, "msgsOutputPath"),
    )
    if output_path is None:
        output_path = _read_optional_config_string(
            config,
            ("platforms", platform, "generatedMessagesOutputPath"),
        )
    if output_path is None:
        output_path = _read_optional_config_string(
            config,
            ("common", "generatedMessagesOutputPath"),
        )
    if output_path is None:
        output_path = _read_optional_config_string(
            config,
            ("generatedMessagesOutputPath",),
        )
    if output_path is not None:
        return _resolve_config_path(output_path, config_root)
    return output_root / "msgs"

def _guess_xcode_project_path(output_root: Path) -> Path | None:
    """从输出目录向上查找 Runner Xcode 工程。"""

    for parent in [output_root, *output_root.parents]:
        runner_project = parent / "Runner.xcodeproj" / "project.pbxproj"
        if runner_project.exists():
            return runner_project
    return None

def _scan_messages(scan_paths: list[Path]) -> list[MessageClass]:
    """扫描 Dart 文件中的 @ChannelMsg 类，并返回稳定排序结果。"""

    messages: list[MessageClass] = []
    seen_files: set[Path] = set()
    for scan_path in scan_paths:
        if not scan_path.exists():
            scan_path.mkdir(parents=True, exist_ok=True)

        for dart_file in sorted(scan_path.rglob("*.dart")):
            resolved_dart_file = dart_file.resolve()
            if resolved_dart_file in seen_files:
                continue
            seen_files.add(resolved_dart_file)
            if dart_file.name.endswith(".g.dart"):
                continue
            messages.extend(_parse_message_file(dart_file))
    return sorted(messages, key=lambda item: item.swift_name)

def _parse_message_file(dart_file: Path) -> list[MessageClass]:
    """解析单个 Dart 源文件中的可支持 channel 消息类。"""

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
    """解析平台源码文件中的 PlatformChannelHandler 注解。"""

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
    """返回带注解的 Dart 类、注解文本和类体。"""

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
    """从 Dart 注解块中读取可选字符串参数。"""

    annotation = re.search(
        rf"@{annotation_name}(?:\s*\(\s*(?:['\"](?P<value>[^'\"]+)['\"])?\s*\))?",
        annotations,
    )
    if annotation is None:
        return None
    return annotation.group("value") or ""

def _parse_fields(class_body: str) -> list[DartField]:
    """从 Dart 类体中提取支持的 final 字段声明。"""

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
    """创建父目录并写入 UTF-8 生成内容。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def _header() -> list[str]:
    """返回平台生成文件的标准头部。"""

    return [
        "// 自动生成代码，请勿手动修改",
        "// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成",
        "",
    ]
