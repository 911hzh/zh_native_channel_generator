from __future__ import annotations

import re
import shutil
from pathlib import Path

from .common import (
    AndroidGeneratorConfig,
    DartField,
    HandlerClass,
    MessageClass,
    _parse_platform_handler_file,
    _write_file,
)


def generate_android(
    config: AndroidGeneratorConfig,
    messages: list[MessageClass],
) -> list[HandlerClass]:
    """生成 Android 消息类型和注册胶水代码。"""

    handlers = _scan_android_handlers(config.handler_scan_paths)
    _reset_android_output_root(
        config.output_root,
        config.generated_messages_output_path,
        config.generated_registrations_output_path,
    )
    _write_android_messages(
        config.generated_messages_output_path,
        config.package_name,
        messages,
    )
    _write_android_generated_registrations(
        config.generated_registrations_output_path,
        config.output_root,
        config.package_name,
        messages,
        handlers,
    )
    return handlers


def _reset_android_output_root(
    output_root: Path,
    generated_messages_output_path: Path,
    generated_registrations_output_path: Path,
) -> None:
    """写入新产物前删除旧的 Android 生成文件。"""

    generated_files = [
        "ChannelBaseMsg.g.kt",
        "ChannelBaseHandler.g.kt",
        "ChannelMsgException.g.kt",
        "ChannelBaseMsgRegister.g.kt",
        "ChannelHandlerRegister.g.kt",
        "MethodChannelMsgManager.g.kt",
        "GeneratedChannelRegistrations.g.kt",
        "ChannelBaseMsg.kt",
        "ChannelBaseHandler.kt",
        "ChannelMsgException.kt",
        "ChannelBaseMsgRegister.kt",
        "ChannelHandlerRegister.kt",
        "MethodChannelMsgManager.kt",
        "GeneratedChannelRegistrations.kt",
    ]
    for file_name in generated_files:
        generated_file = output_root / file_name
        if generated_file.exists():
            generated_file.unlink()

    generated_registrations_file = (
        generated_registrations_output_path / "GeneratedChannelRegistrations.g.kt"
    )
    if generated_registrations_file.exists():
        generated_registrations_file.unlink()

    generated_msgs = generated_messages_output_path
    if generated_msgs.exists():
        shutil.rmtree(generated_msgs)
    generated_msgs.mkdir(parents=True, exist_ok=True)

def _scan_android_handlers(scan_paths: list[Path]) -> list[HandlerClass]:
    """扫描 Kotlin handler 文件中的 PlatformChannelHandler 注解。"""

    handlers: list[HandlerClass] = []
    seen_files: set[Path] = set()
    for scan_path in scan_paths:
        if not scan_path.exists():
            scan_path.mkdir(parents=True, exist_ok=True)

        for kotlin_file in sorted(scan_path.rglob("*.kt")):
            resolved_kotlin_file = kotlin_file.resolve()
            if resolved_kotlin_file in seen_files:
                continue
            seen_files.add(resolved_kotlin_file)
            handlers.extend(_parse_android_handler_file(kotlin_file))
    return sorted(handlers, key=lambda item: item.channel_name)

def _parse_android_handler_file(kotlin_file: Path) -> list[HandlerClass]:
    """解析单个 Kotlin 文件，并为每个 handler 绑定 package 名称。"""

    handlers = _parse_platform_handler_file(kotlin_file)
    if not handlers:
        return handlers

    source = kotlin_file.read_text(encoding="utf-8")
    package_match = re.search(
        r"^\s*package\s+(?P<package>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*$",
        source,
        re.MULTILINE,
    )
    if package_match is None:
        class_names = ", ".join(handler.class_name for handler in handlers)
        raise ValueError(
            f"Android handler {class_names} in {kotlin_file} must declare a package."
        )

    package_name = package_match.group("package")
    return [
        HandlerClass(
            class_name=handler.class_name,
            channel_name=handler.channel_name,
            file_path=handler.file_path,
            package_name=package_name,
        )
        for handler in handlers
    ]

def _write_android_messages(
    output_path: Path,
    package_name: str,
    messages: list[MessageClass],
) -> None:
    """将生成的 Kotlin 消息类写入配置指定目录。"""

    for message in messages:
        _write_file(
            output_path / f"{message.class_name}.g.kt",
            _android_message_kotlin(package_name, message),
        )

def _write_android_generated_registrations(
    output_path: Path,
    output_root: Path,
    package_name: str,
    messages: list[MessageClass],
    handlers: list[HandlerClass],
) -> None:
    """写入用于连接消息和 handler 的 Kotlin 注册文件。"""

    lines = _android_header(package_name)
    lines.extend(
        [
            "import com.example.zh_native_channel.ChannelBaseMsgRegister",
            "import com.example.zh_native_channel.ChannelHandlerRegister",
            "import com.example.zh_native_channel.MethodChannelMsgManager",
        ]
    )
    for message in messages:
        lines.append(f"import {package_name}.msgs.{message.class_name}")
    for handler in handlers:
        handler_import = _android_handler_import(
            package_name,
            output_root,
            handler,
        )
        if handler_import is not None:
            lines.append(handler_import)

    lines.extend(
        [
            "",
            "object GeneratedChannelRegistrations {",
            "    fun registerAll() {",
            "        MethodChannelMsgManager.registerMessages(::registerMessages)",
            "        MethodChannelMsgManager.registerHandlers(::registerHandlers)",
            "    }",
            "",
            "    fun registerMessages(register: ChannelBaseMsgRegister) {",
        ]
    )

    for message in messages:
        lines.append(
            f'        register.registerChannel("{message.channel_name}") '
            f"{{ {message.class_name}.fromMap(it) }}"
        )

    lines.extend(["    }", "", "    fun registerHandlers(register: ChannelHandlerRegister) {"])
    if handlers:
        for handler in handlers:
            lines.append(
                f'        register.registerChannel("{handler.channel_name}", {handler.class_name}())'
            )
    else:
        lines.append("        // 在这里注册手写的 Android handler。")

    lines.extend(["    }", "}"])
    _write_file(
        output_path / "GeneratedChannelRegistrations.g.kt",
        "\n".join(lines) + "\n",
    )

def _android_handler_import(
    package_name: str,
    output_root: Path,
    handler: HandlerClass,
) -> str | None:
    """当 handler 位于注册文件 package 外时生成 import。"""

    if handler.package_name is not None:
        if handler.package_name == package_name:
            return None
        return f"import {handler.package_name}.{handler.class_name}"

    if handler.file_path is None:
        return None
    try:
        relative_parent = handler.file_path.resolve().parent.relative_to(
            output_root.resolve()
        )
    except ValueError:
        return None
    if relative_parent == Path("."):
        return None
    package_suffix = ".".join(relative_parent.parts)
    return f"import {package_name}.{package_suffix}.{handler.class_name}"

def _android_header(package_name: str) -> list[str]:
    """返回生成 Kotlin 文件的头部和 package 声明。"""

    return [
        "// 自动生成代码，请勿手动修改",
        "// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成",
        "",
        f"package {package_name}",
    ]

def _android_message_kotlin(package_name: str, message: MessageClass) -> str:
    """为单个 Dart 消息渲染 Kotlin ChannelBaseMsg 实现。"""

    lines = _android_header(f"{package_name}.msgs") + [
        "",
        "import com.example.zh_native_channel.ChannelBaseMsg",
        "import com.example.zh_native_channel.ChannelMsgException",
        "",
        f"data class {message.class_name}(",
    ]

    for index, field in enumerate(message.fields):
        suffix = "," if index < len(message.fields) - 1 else ""
        lines.append(f"    val {field.name}: {_kotlin_type(field)}{suffix}")

    lines.extend(
        [
            ") : ChannelBaseMsg {",
            f'    override val channelName: String = "{_escape_kotlin_string(message.channel_name)}"',
            "",
            "    override fun toMap(): Map<String, Any?> {",
            "        return mapOf(",
        ]
    )

    for index, field in enumerate(message.fields):
        suffix = "," if index < len(message.fields) - 1 else ""
        lines.append(f'            "{field.name}" to {field.name}{suffix}')

    lines.extend(
        [
            "        )",
            "    }",
            "",
            "    companion object {",
            f"        fun fromMap(map: Map<String, Any?>): {message.class_name} {{",
            f"            return {message.class_name}(",
        ]
    )

    for index, field in enumerate(message.fields):
        suffix = "," if index < len(message.fields) - 1 else ""
        lines.append(f"                {field.name} = {_kotlin_value_reader(field)}{suffix}")

    lines.extend(["            )", "        }", "    }", "}"])
    return "\n".join(lines) + "\n"

def _kotlin_type(field: DartField) -> str:
    """将支持的 Dart 字段类型映射为 Kotlin 类型。"""

    type_map = {
        "String": "String",
        "int": "Int",
        "double": "Double",
        "num": "Double",
        "bool": "Boolean",
        "Map<String, dynamic>": "Map<String, Any?>",
    }
    if field.dart_type.startswith("List<"):
        kotlin_type = "List<Any?>"
    else:
        kotlin_type = type_map.get(field.dart_type, "Any")
    return f"{kotlin_type}?" if field.nullable else kotlin_type

def _kotlin_value_reader(field: DartField) -> str:
    """渲染从 map 读取并校验单个字段的 Kotlin 代码。"""

    value = f'map["{field.name}"]'
    if field.nullable:
        if field.dart_type == "int":
            return f"({value} as? Number)?.toInt()"
        if field.dart_type in ("double", "num"):
            return f"({value} as? Number)?.toDouble()"
        return f"{value} as? {_kotlin_type(field).rstrip('?')}"

    error = (
        f'ChannelMsgException("Field {field.name} is missing or has invalid type.")'
    )
    if field.dart_type == "int":
        return f"({value} as? Number)?.toInt() ?: throw {error}"
    if field.dart_type in ("double", "num"):
        return f"({value} as? Number)?.toDouble() ?: throw {error}"
    return f"{value} as? {_kotlin_type(field)} ?: throw {error}"

def _escape_kotlin_string(value: str) -> str:
    """转义生成 Kotlin 源码中的字符串字面量。"""

    return value.replace("\\", "\\\\").replace('"', '\\"')
