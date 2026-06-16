from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .common import (
    DartField,
    DartModelClass,
    HandlerClass,
    IOSGeneratorConfig,
    MessageClass,
    _generic_inner_type,
    _header,
    _map_value_type,
    _strip_nullable_type,
    _write_file,
    log_step,
)


def generate_ios(config: IOSGeneratorConfig, messages: list[MessageClass]) -> list[HandlerClass]:
    """生成 iOS 消息类型、注册代码和 Xcode 源文件条目。"""

    log_step("iOS 脚本开始执行")
    log_step(
        "iOS 扫描 handler: "
        + ", ".join(path.as_posix() for path in config.handler_scan_paths)
    )
    handlers = _scan_ios_handlers(config.handler_scan_paths)
    log_step(f"iOS 已扫描到 {len(handlers)} 个 handler")
    log_step(f"iOS 清理旧生成产物: {config.output_root}")
    _reset_output_root(
        config.output_root,
        config.generated_messages_output_path,
        config.generated_registrations_output_path,
    )
    log_step(f"iOS 写入消息文件: {config.generated_messages_output_path}")
    _write_messages(config.generated_messages_output_path, messages)
    log_step(f"iOS 写入注册文件: {config.generated_registrations_output_path}")
    _write_generated_registrations(
        config.generated_registrations_output_path,
        messages,
        handlers,
    )
    log_step("iOS 同步 Xcode Sources")
    _sync_xcode_sources(
        config.output_root,
        config.generated_messages_output_path,
        config.generated_registrations_output_path,
        handlers,
        config.xcode_project_path,
    )
    log_step("iOS 脚本执行完成")
    return handlers


def clean_ios_generated(config: IOSGeneratorConfig) -> list[Path]:
    """删除配置指定位置的 iOS 生成产物，并返回实际删除的路径。"""

    return _delete_generated_outputs(
        config.output_root,
        config.generated_messages_output_path,
        config.generated_registrations_output_path,
    )


def _reset_output_root(
    output_root: Path,
    generated_messages_output_path: Path,
    generated_registrations_output_path: Path,
) -> None:
    """写入新产物前删除旧的 iOS 生成文件。"""

    _delete_generated_outputs(
        output_root,
        generated_messages_output_path,
        generated_registrations_output_path,
    )
    generated_messages_output_path.mkdir(parents=True, exist_ok=True)


def _delete_generated_outputs(
    output_root: Path,
    generated_messages_output_path: Path,
    generated_registrations_output_path: Path,
) -> list[Path]:
    """删除旧的 iOS 生成文件，保留用户配置的输出目录。"""

    deleted_paths: list[Path] = []
    generated_files = [
        "ChannelBaseMsg.g.swift",
        "ChannelBaseHandler.g.swift",
        "ChannelBaseMsgRegister.g.swift",
        "ChannelHandlerRegister.g.swift",
        "MethodChannelMsgManager.g.swift",
        "ChannelMsgMapCoder.g.swift",
        "GeneratedChannelRegistrations.g.swift",
    ]
    for file_name in generated_files:
        generated_file = output_root / file_name
        if generated_file.exists():
            generated_file.unlink()
            deleted_paths.append(generated_file)

    generated_registrations_file = (
        generated_registrations_output_path / "GeneratedChannelRegistrations.g.swift"
    )
    if generated_registrations_file.exists():
        generated_registrations_file.unlink()
        deleted_paths.append(generated_registrations_file)

    if generated_messages_output_path.exists():
        for generated_message_file in sorted(
            generated_messages_output_path.glob("*.g.swift")
        ):
            if generated_message_file.is_file():
                generated_message_file.unlink()
                deleted_paths.append(generated_message_file)

    return deleted_paths

def _scan_ios_handlers(scan_paths: list[Path]) -> list[HandlerClass]:
    """扫描 Swift 文件中的 PlatformChannelHandler 注解。"""

    handlers: list[HandlerClass] = []
    seen_files: set[Path] = set()
    for scan_path in scan_paths:
        if not scan_path.exists():
            scan_path.mkdir(parents=True, exist_ok=True)

        for swift_file in sorted(scan_path.rglob("*.swift")):
            resolved_swift_file = swift_file.resolve()
            if resolved_swift_file in seen_files:
                continue
            seen_files.add(resolved_swift_file)
            handlers.extend(_parse_ios_handler_file(swift_file))
    return sorted(handlers, key=lambda item: item.channel_name)

def _parse_ios_handler_file(swift_file: Path) -> list[HandlerClass]:
    """解析单个 Swift 文件中的注解 handler 类或结构体声明。"""

    source = swift_file.read_text(encoding="utf-8")
    pattern = re.compile(
        r"//\s*PlatformChannelHandler(?:\(\s*(?:\"(?P<key>[^\"]+)\"|'(?P<single_key>[^']+)')?\s*\))?"
        r"\s*\n\s*(?:final\s+)?(?:class|struct)\s+(?P<class_name>[A-Za-z_]\w*)",
        re.MULTILINE,
    )

    handlers: list[HandlerClass] = []
    for match in pattern.finditer(source):
        explicit_key = match.group("key") or match.group("single_key")
        class_name = match.group("class_name")
        if not explicit_key:
            raise ValueError(
                f"// PlatformChannelHandler on {class_name} in {swift_file} must provide a key."
            )
        handlers.append(
            HandlerClass(
                class_name=class_name,
                channel_name=explicit_key,
                file_path=swift_file,
                package_name=None,
            )
        )
    return handlers

def _write_messages(output_path: Path, messages: list[MessageClass]) -> None:
    """将生成的 Swift 消息结构体写入配置指定目录。"""

    for message in messages:
        _write_file(
            output_path / f"{message.swift_name}.g.swift",
            _message_swift(message),
        )

def _write_generated_registrations(
    output_path: Path,
    messages: list[MessageClass],
    handlers: list[HandlerClass],
) -> None:
    """写入用于连接消息和 handler 的 Swift 注册文件。"""

    lines = _header() + [
        "import Foundation",
        "import zh_native_channel",
        "",
        "enum GeneratedChannelRegistrations {",
        "    static func registerAll() {",
        "        MethodChannelMsgManager.shared.registerMessages(registerMessages)",
        "        MethodChannelMsgManager.shared.registerHandlers(registerHandlers)",
        "    }",
        "",
        "    static func registerMessages(_ register: ChannelBaseMsgRegister) {",
    ]

    for message in messages:
        lines.append(
            f'        register.registerChannel("{message.channel_name}") '
            f"{{ try {message.swift_name}(map: $0) }}"
        )

    lines.extend(
        [
            "    }",
            "",
            "    static func registerHandlers(_ register: ChannelHandlerRegister) {",
        ]
    )

    if handlers:
        for handler in handlers:
            lines.append(
                f'        register.registerChannel("{handler.channel_name}", handler: {handler.class_name}())'
            )
    else:
        lines.append("        // 在这里注册手写的 iOS handler。")

    lines.extend(["    }", "}"])
    _write_file(
        output_path / "GeneratedChannelRegistrations.g.swift",
        "\n".join(lines) + "\n",
    )

def _sync_xcode_sources(
    output_root: Path,
    generated_messages_output_path: Path,
    generated_registrations_output_path: Path,
    handlers: list[HandlerClass],
    xcode_project_path: Path | None,
) -> None:
    """在可行时将生成文件和 handler 文件加入 Runner target。"""

    if xcode_project_path is None or not xcode_project_path.exists():
        return

    handler_files = {
        handler.file_path
        for handler in handlers
        if handler.file_path is not None
    }
    swift_files = sorted(
        {
            *output_root.rglob("*.swift"),
            *generated_messages_output_path.rglob("*.swift"),
            generated_registrations_output_path / "GeneratedChannelRegistrations.g.swift",
            *handler_files,
        }
    )
    if not swift_files:
        return

    project_root = xcode_project_path.parent.parent
    source = xcode_project_path.read_text(encoding="utf-8")
    source, did_remove_stale_sources = _remove_stale_generated_xcode_sources(
        source,
        {"ChannelMsgMapCoder.g.swift"},
    )
    additions = [
        _xcode_source_addition(source, project_root, swift_file)
        for swift_file in swift_files
    ]
    additions = [addition for addition in additions if addition is not None]
    if not additions:
        if did_remove_stale_sources:
            xcode_project_path.write_text(source, encoding="utf-8")
        return

    source_build_phase_id = _find_runner_sources_build_phase_id(source)
    build_file_entries = "".join(addition["build_file"] for addition in additions)
    file_reference_entries = "".join(
        addition["file_reference"] for addition in additions
    )
    source_file_entries = "".join(addition["source_file"] for addition in additions)

    source = source.replace(
        "/* End PBXBuildFile section */",
        f"{build_file_entries}/* End PBXBuildFile section */",
        1,
    )
    source = source.replace(
        "/* End PBXFileReference section */",
        f"{file_reference_entries}/* End PBXFileReference section */",
        1,
    )

    source_phase_pattern = re.compile(
        rf"(?P<head>\t\t{re.escape(source_build_phase_id)} /\* Sources \*/ = \{{.*?"
        rf"\n\t\t\tfiles = \(\n)(?P<body>.*?)(?P<tail>\t\t\t\);\n)",
        re.DOTALL,
    )
    source, replace_count = source_phase_pattern.subn(
        lambda match: (
            f"{match.group('head')}{match.group('body')}"
            f"{source_file_entries}{match.group('tail')}"
        ),
        source,
        count=1,
    )
    if replace_count == 0:
        raise ValueError("Could not update Runner Sources build phase in Xcode project.")

    xcode_project_path.write_text(source, encoding="utf-8")

def _remove_stale_generated_xcode_sources(
    project_source: str,
    file_names: set[str],
) -> tuple[str, bool]:
    """移除旧版本 generator 加入 Xcode 的已废弃生成文件引用。"""

    original_source = project_source
    for file_name in file_names:
        project_source = "\n".join(
            line
            for line in project_source.splitlines()
            if f"/* {file_name}" not in line and file_name not in line
        )
        project_source += "\n"
    return project_source, project_source != original_source

def _xcode_source_addition(
    project_source: str,
    project_root: Path,
    swift_file: Path,
) -> dict[str, str] | None:
    """为尚未加入工程的 Swift 文件构建 pbxproj 片段。"""

    file_name = swift_file.name
    if f"/* {file_name} in Sources */" in project_source:
        return None

    try:
        relative_path = swift_file.resolve().relative_to(project_root.resolve())
    except ValueError:
        return None

    relative_path_text = relative_path.as_posix()
    if relative_path_text in project_source or file_name in project_source:
        return None

    file_ref_id = _xcode_id(f"file:{relative_path_text}")
    build_file_id = _xcode_id(f"build:{relative_path_text}")
    if file_ref_id in project_source or build_file_id in project_source:
        return None

    return {
        "build_file": (
            f"\t\t{build_file_id} /* {file_name} in Sources */ = "
            f"{{isa = PBXBuildFile; fileRef = {file_ref_id} /* {file_name} */; }};\n"
        ),
        "file_reference": (
            f"\t\t{file_ref_id} /* {file_name} */ = "
            "{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; "
            f'path = "{relative_path_text}"; sourceTree = SOURCE_ROOT; }};\n'
        ),
        "source_file": f"\t\t\t\t{build_file_id} /* {file_name} in Sources */,\n",
    }

def _find_runner_sources_build_phase_id(project_source: str) -> str:
    """在 pbxproj 中查找 Runner target 的 Sources build phase id。"""

    native_targets = re.finditer(
        r"\n\t\t[0-9A-F]{24} /\* [^*]+ \*/ = \{"
        r"\n\t\t\tisa = PBXNativeTarget;"
        r"(?P<body>.*?)\n\t\t\};",
        project_source,
        re.DOTALL,
    )

    runner_target_body: str | None = None
    for native_target in native_targets:
        body = native_target.group("body")
        if re.search(r"\n\t\t\tname = Runner;\n", body):
            runner_target_body = body
            break

    if runner_target_body is None:
        raise ValueError("Could not find Runner target in Xcode project.")

    build_phases = re.search(
        r"\n\t\t\tbuildPhases = \(\n(?P<build_phases>.*?)\n\t\t\t\);",
        runner_target_body,
        re.DOTALL,
    )
    if build_phases is None:
        raise ValueError("Could not find Runner build phases in Xcode project.")

    sources_phase = re.search(
        r"\t\t\t\t(?P<id>[0-9A-F]{24}) /\* Sources \*/,",
        build_phases.group("build_phases"),
    )
    if sources_phase is None:
        raise ValueError("Could not find Runner Sources build phase in Xcode project.")

    return sources_phase.group("id")

def _xcode_id(seed: str) -> str:
    """创建确定性的 24 位 Xcode 风格对象 id。"""

    return hashlib.sha1(seed.encode("utf-8")).hexdigest().upper()[:24]

def _message_swift(message: MessageClass) -> str:
    """为单个 Dart 消息渲染 Swift ChannelBaseMsg 实现。"""

    model_names = {model.class_name for model in message.nested_models}
    lines = _header() + [
        "import Foundation",
        "import zh_native_channel",
        "",
    ]

    for model in message.nested_models:
        lines.extend(_model_swift(model, model_names))
        lines.append("")

    lines.extend(_swift_data_struct(message.swift_name, message.fields, model_names, "Codable, ChannelBaseMsg"))

    return "\n".join(lines) + "\n"

def _model_swift(model: DartModelClass, model_names: set[str]) -> list[str]:
    """渲染消息文件内的嵌套 Swift model。"""

    return _swift_data_struct(model.class_name, model.fields, model_names, "Codable")

def _swift_data_struct(
    class_name: str,
    fields: list[DartField],
    model_names: set[str],
    conformance: str,
) -> list[str]:
    """渲染 Swift struct，包含成员初始化和 Map 初始化。"""

    lines = [f"struct {class_name}: {conformance} {{"]
    for field in fields:
        lines.append(f"    let {field.name}: {_swift_type(field)}")

    if not fields:
        lines.append("")
        lines.append("    init() {}")

    if fields:
        params = ", ".join(f"{field.name}: {_swift_type(field)}" for field in fields)
        lines.extend(["", f"    init({params}) {{"])
        for field in fields:
            lines.append(f"        self.{field.name} = {field.name}")
        lines.append("    }")

        lines.extend(["", "    init(map: [String: Any]) throws {"])
        for field in fields:
            lines.append(
                f"        self.{field.name} = {_swift_value_reader(field, model_names)}"
            )
        lines.append("    }")

    lines.append("}")
    return lines

def _swift_type(field: DartField) -> str:
    """将支持的 Dart 字段类型映射为 Swift 类型。"""

    swift_type = _swift_type_name(field.dart_type)
    return f"{swift_type}?" if field.nullable else swift_type

def _swift_type_name(dart_type: str) -> str:
    """将 Dart 类型文本映射为 Swift 类型文本。"""

    type_map = {
        "String": "String",
        "int": "Int",
        "double": "Double",
        "num": "Double",
        "bool": "Bool",
        "dynamic": "Any",
        "Map<String, dynamic>": "[String: Any]",
    }

    normalized_type = _strip_nullable_type(dart_type)
    if normalized_type in type_map:
        return type_map[normalized_type]

    list_inner = _generic_inner_type(normalized_type, "List")
    if list_inner is not None:
        return f"[{_swift_type_name(list_inner)}]"

    map_value = _map_value_type(normalized_type)
    if map_value is not None:
        return f"[String: {_swift_type_name(map_value)}]"

    return normalized_type

def _swift_value_reader(field: DartField, model_names: set[str]) -> str:
    """渲染 Swift 从 map 读取字段的表达式。"""

    value = f'map["{field.name}"]'
    normalized_type = _strip_nullable_type(field.dart_type)

    if field.nullable:
        if normalized_type in model_names:
            return (
                f'ChannelMsgMapCoder.isNull({value}) ? nil : try {normalized_type}(map: '
                f'ChannelMsgMapCoder.requireStringAnyMap({value}, fieldName: "{field.name}"))'
            )
        return _swift_optional_value_reader(field, model_names, value)

    fallback = _swift_default_value(field)
    if normalized_type == "String":
        if fallback is not None:
            return f"({value} as? String) ?? {fallback}"
        return f'try (({value} as? String) ?? ChannelMsgMapCoder.missingField("{field.name}"))'
    if normalized_type == "int":
        if fallback is not None:
            return f"ChannelMsgMapCoder.readInt({value}) ?? {fallback}"
        return f'try (ChannelMsgMapCoder.readInt({value}) ?? ChannelMsgMapCoder.missingField("{field.name}"))'
    if normalized_type in ("double", "num"):
        if fallback is not None:
            return f"ChannelMsgMapCoder.readDouble({value}) ?? {fallback}"
        return f'try (ChannelMsgMapCoder.readDouble({value}) ?? ChannelMsgMapCoder.missingField("{field.name}"))'
    if normalized_type == "bool":
        if fallback is not None:
            return f"({value} as? Bool) ?? {fallback}"
        return f'try (({value} as? Bool) ?? ChannelMsgMapCoder.missingField("{field.name}"))'
    if normalized_type in model_names:
        return f'try {normalized_type}(map: try ChannelMsgMapCoder.requireStringAnyMap({value}, fieldName: "{field.name}"))'

    list_inner = _generic_inner_type(normalized_type, "List")
    if list_inner in model_names:
        return (
            f'try ChannelMsgMapCoder.requireArray({value}, fieldName: "{field.name}").map {{ '
            f'try {list_inner}(map: try ChannelMsgMapCoder.requireStringAnyMap($0, fieldName: "{field.name}")) }}'
        )

    map_value = _map_value_type(normalized_type)
    if map_value in model_names:
        return (
            "try Dictionary(uniqueKeysWithValues: "
            f'ChannelMsgMapCoder.requireStringAnyMap({value}, fieldName: "{field.name}").map {{ key, value in '
            f'(key, try {map_value}(map: try ChannelMsgMapCoder.requireStringAnyMap(value, fieldName: "{field.name}"))) }})'
        )

    if fallback is not None:
        return f"({value} as? {_swift_type(field)}) ?? {fallback}"
    return f'try (({value} as? {_swift_type(field)}) ?? ChannelMsgMapCoder.missingField("{field.name}"))'

def _swift_optional_value_reader(
    field: DartField,
    model_names: set[str],
    value: str,
) -> str:
    """渲染 Swift 可空字段读取表达式。"""

    normalized_type = _strip_nullable_type(field.dart_type)
    if normalized_type == "String":
        return f"{value} as? String"
    if normalized_type == "int":
        return f"ChannelMsgMapCoder.readInt({value})"
    if normalized_type in ("double", "num"):
        return f"ChannelMsgMapCoder.readDouble({value})"
    if normalized_type == "bool":
        return f"{value} as? Bool"

    list_inner = _generic_inner_type(normalized_type, "List")
    if list_inner in model_names:
        return (
            f'ChannelMsgMapCoder.isNull({value}) ? nil : try ChannelMsgMapCoder.requireArray({value}, fieldName: "{field.name}").map {{ '
            f'try {list_inner}(map: try ChannelMsgMapCoder.requireStringAnyMap($0, fieldName: "{field.name}")) }}'
        )

    map_value = _map_value_type(normalized_type)
    if map_value in model_names:
        return (
            f'ChannelMsgMapCoder.isNull({value}) ? nil : try Dictionary(uniqueKeysWithValues: '
            f'ChannelMsgMapCoder.requireStringAnyMap({value}, fieldName: "{field.name}").map {{ key, value in '
            f'(key, try {map_value}(map: try ChannelMsgMapCoder.requireStringAnyMap(value, fieldName: "{field.name}"))) }})'
        )

    return f"{value} as? {_swift_type(field).rstrip('?')}"

def _swift_default_value(field: DartField) -> str | None:
    """将 Dart 字段默认值映射为 Swift 字面量。"""

    if field.default_value is None:
        return None
    value = field.default_value
    if value == "null":
        return "nil" if field.nullable else None
    if value in ("true", "false"):
        return value
    if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        return value
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        escaped = value[1:-1].replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return None

