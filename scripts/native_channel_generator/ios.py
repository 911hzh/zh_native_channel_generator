from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .common import (
    DartField,
    HandlerClass,
    IOSGeneratorConfig,
    MessageClass,
    _header,
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
    additions = [
        _xcode_source_addition(source, project_root, swift_file)
        for swift_file in swift_files
    ]
    additions = [addition for addition in additions if addition is not None]
    if not additions:
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

def _escape_swift_string(value: str) -> str:
    """转义生成 Swift 源码中的字符串字面量。"""

    return value.replace("\\", "\\\\").replace('"', '\\"')

def _message_swift(message: MessageClass) -> str:
    """为单个 Dart 消息渲染 Swift ChannelBaseMsg 实现。"""

    lines = _header() + [
        "import Foundation",
        "import zh_native_channel",
        "",
        f"struct {message.swift_name}: Codable, ChannelBaseMsg {{",
        f'    var channelName: String {{ "{_escape_swift_string(message.channel_name)}" }}',
    ]

    for field in message.fields:
        lines.append(f"    let {field.name}: {_swift_type(field)}")

    if not message.fields:
        lines.append("")
        lines.append("    init() {}")

    lines.append("}")
    return "\n".join(lines) + "\n"

def _swift_type(field: DartField) -> str:
    """将支持的 Dart 字段类型映射为 Swift 类型。"""

    type_map = {
        "String": "String",
        "int": "Int",
        "double": "Double",
        "num": "Double",
        "bool": "Bool",
        "Map<String, dynamic>": "[String: Any]",
    }
    if field.dart_type.startswith("List<"):
        swift_type = "[Any]"
    else:
        swift_type = type_map.get(field.dart_type, "Any")
    return f"{swift_type}?" if field.nullable else swift_type
