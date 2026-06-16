from __future__ import annotations

import re
from pathlib import Path

from .common import (
    AndroidGeneratorConfig,
    DartField,
    DartModelClass,
    HandlerClass,
    MessageClass,
    _generic_inner_type,
    _map_value_type,
    _parse_platform_handler_file,
    _strip_nullable_type,
    _write_file,
    log_step,
)


def generate_android(
    config: AndroidGeneratorConfig,
    messages: list[MessageClass],
) -> list[HandlerClass]:
    """生成 Android 消息类型和注册胶水代码。"""

    log_step("Android 脚本开始执行")
    log_step(
        "Android 扫描 handler: "
        + ", ".join(path.as_posix() for path in config.handler_scan_paths)
    )
    handlers = _scan_android_handlers(config.handler_scan_paths)
    log_step(f"Android 已扫描到 {len(handlers)} 个 handler")
    log_step(f"Android 清理旧生成产物: {config.output_root}")
    _reset_android_output_root(
        config.output_root,
        config.generated_messages_output_path,
        config.generated_registrations_output_path,
    )
    log_step(f"Android 写入消息文件: {config.generated_messages_output_path}")
    _write_android_messages(
        config.generated_messages_output_path,
        config.package_name,
        messages,
    )
    log_step(f"Android 写入注册文件: {config.generated_registrations_output_path}")
    _write_android_generated_registrations(
        config.generated_registrations_output_path,
        config.output_root,
        config.package_name,
        messages,
        handlers,
    )
    log_step("Android 脚本执行完成")
    return handlers


def clean_android_generated(config: AndroidGeneratorConfig) -> list[Path]:
    """删除配置指定位置的 Android 生成产物，并返回实际删除的路径。"""

    return _delete_android_generated_outputs(
        config.output_root,
        config.generated_messages_output_path,
        config.generated_registrations_output_path,
    )


def _reset_android_output_root(
    output_root: Path,
    generated_messages_output_path: Path,
    generated_registrations_output_path: Path,
) -> None:
    """写入新产物前删除旧的 Android 生成文件。"""

    _delete_android_generated_outputs(
        output_root,
        generated_messages_output_path,
        generated_registrations_output_path,
    )
    generated_messages_output_path.mkdir(parents=True, exist_ok=True)


def _delete_android_generated_outputs(
    output_root: Path,
    generated_messages_output_path: Path,
    generated_registrations_output_path: Path,
) -> list[Path]:
    """删除旧的 Android 生成文件，保留用户配置的输出目录。"""

    deleted_paths: list[Path] = []
    generated_files = [
        "ChannelBaseMsg.g.kt",
        "ChannelBaseHandler.g.kt",
        "ChannelMsgException.g.kt",
        "ChannelBaseMsgRegister.g.kt",
        "ChannelHandlerRegister.g.kt",
        "MethodChannelMsgManager.g.kt",
        "GeneratedChannelRegistrations.g.kt",
    ]
    for file_name in generated_files:
        generated_file = output_root / file_name
        if generated_file.exists():
            generated_file.unlink()
            deleted_paths.append(generated_file)

    generated_registrations_file = (
        generated_registrations_output_path / "GeneratedChannelRegistrations.g.kt"
    )
    if generated_registrations_file.exists():
        generated_registrations_file.unlink()
        deleted_paths.append(generated_registrations_file)

    if generated_messages_output_path.exists():
        for generated_message_file in sorted(
            generated_messages_output_path.glob("*.g.kt")
        ):
            if generated_message_file.is_file():
                generated_message_file.unlink()
                deleted_paths.append(generated_message_file)

    return deleted_paths

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

    model_names = {model.class_name for model in message.nested_models}
    lines = _android_header(f"{package_name}.msgs") + [
        "",
        "import com.example.zh_native_channel.ChannelBaseMsg",
        "import com.example.zh_native_channel.ChannelMsgException",
    ]
    if _needs_kotlin_map_helper(message):
        lines.append("import com.example.zh_native_channel.ChannelMsgMapCoder")
    lines.append("")

    for model in message.nested_models:
        lines.extend(
            _kotlin_data_class(
                model.class_name,
                model.fields,
                model_names,
                implements_channel_base_msg=False,
            )
        )
        lines.append("")

    lines.extend(
        _kotlin_data_class(
            message.class_name,
            message.fields,
            model_names,
            implements_channel_base_msg=True,
        )
    )

    return "\n".join(lines) + "\n"

def _kotlin_data_class(
    class_name: str,
    fields: list[DartField],
    model_names: set[str],
    *,
    implements_channel_base_msg: bool,
) -> list[str]:
    """渲染 Kotlin data class，可用于消息或同文件嵌套 model。"""

    lines = [f"data class {class_name}("]
    for index, field in enumerate(fields):
        suffix = "," if index < len(fields) - 1 else ""
        lines.append(f"    val {field.name}: {_kotlin_type(field, model_names)}{suffix}")

    inheritance = " : ChannelBaseMsg" if implements_channel_base_msg else ""
    to_map_override = "override " if implements_channel_base_msg else ""

    lines.extend(
        [
            f"){inheritance} {{",
            f"    {to_map_override}fun toMap(): Map<String, Any?> {{",
            "        return mapOf(",
        ]
    )

    for index, field in enumerate(fields):
        suffix = "," if index < len(fields) - 1 else ""
        lines.append(
            f'            "{field.name}" to {_kotlin_to_map_value(field, model_names)}{suffix}'
        )

    lines.extend(
        [
            "        )",
            "    }",
            "",
            "    companion object {",
            f"        fun fromMap(map: Map<String, Any?>): {class_name} {{",
            f"            return {class_name}(",
        ]
    )

    for index, field in enumerate(fields):
        suffix = "," if index < len(fields) - 1 else ""
        lines.append(
            f"                {field.name} = {_kotlin_value_reader(field, model_names)}{suffix}"
        )

    lines.extend(["            )", "        }", "    }", "}"])
    return lines

def _kotlin_type(field: DartField, model_names: set[str]) -> str:
    """将支持的 Dart 字段类型映射为 Kotlin 类型。"""

    kotlin_type = _kotlin_type_name(field.dart_type, model_names)
    return f"{kotlin_type}?" if field.nullable else kotlin_type

def _kotlin_type_name(dart_type: str, model_names: set[str]) -> str:
    """将 Dart 类型文本映射为 Kotlin 类型文本。"""

    type_map = {
        "String": "String",
        "int": "Int",
        "double": "Double",
        "num": "Double",
        "bool": "Boolean",
        "Map<String, dynamic>": "Map<String, Any?>",
        "dynamic": "Any?",
    }

    normalized_type = _strip_nullable_type(dart_type)
    if normalized_type in type_map:
        return type_map[normalized_type]
    if normalized_type in model_names:
        return normalized_type

    list_inner = _generic_inner_type(normalized_type, "List")
    if list_inner is not None:
        return f"List<{_kotlin_type_name(list_inner, model_names)}>"

    map_value = _map_value_type(normalized_type)
    if map_value is not None:
        return f"Map<String, {_kotlin_type_name(map_value, model_names)}>"

    return normalized_type

def _kotlin_value_reader(field: DartField, model_names: set[str]) -> str:
    """渲染从 map 读取并校验单个字段的 Kotlin 代码。"""

    value = f'map["{field.name}"]'
    non_null_reader = _kotlin_non_null_value_reader(field, model_names, value)
    if field.nullable:
        return _kotlin_nullable_value_reader(field, model_names, value)

    return non_null_reader

def _kotlin_non_null_value_reader(
    field: DartField,
    model_names: set[str],
    value: str,
) -> str:
    """渲染非空字段读取表达式。"""

    normalized_type = _strip_nullable_type(field.dart_type)
    error = (
        f'ChannelMsgException("Field {field.name} is missing or has invalid type.")'
    )
    fallback = _kotlin_default_value(field)
    fallback_or_error = fallback if fallback is not None else f"throw {error}"
    if normalized_type == "int":
        return f"({value} as? Number)?.toInt() ?: {fallback_or_error}"
    if normalized_type in ("double", "num"):
        return f"({value} as? Number)?.toDouble() ?: {fallback_or_error}"
    if normalized_type in model_names:
        return f"{normalized_type}.fromMap(ChannelMsgMapCoder.requireStringAnyMap({value}, \"{field.name}\"))"

    list_inner = _generic_inner_type(normalized_type, "List")
    if list_inner is not None:
        return _kotlin_list_reader(field, model_names, value, nullable=False)

    map_value = _map_value_type(normalized_type)
    if map_value is not None:
        return _kotlin_map_reader(field, model_names, value, nullable=False)

    return f"{value} as? {_kotlin_type(field, model_names)} ?: {fallback_or_error}"

def _kotlin_nullable_value_reader(
    field: DartField,
    model_names: set[str],
    value: str,
) -> str:
    """渲染可空字段读取表达式。"""

    normalized_type = _strip_nullable_type(field.dart_type)
    if normalized_type == "int":
        return f"({value} as? Number)?.toInt()"
    if normalized_type in ("double", "num"):
        return f"({value} as? Number)?.toDouble()"
    if normalized_type in model_names:
        return f"{value}?.let {{ {normalized_type}.fromMap(ChannelMsgMapCoder.requireStringAnyMap(it, \"{field.name}\")) }}"

    list_inner = _generic_inner_type(normalized_type, "List")
    if list_inner is not None:
        return _kotlin_list_reader(field, model_names, value, nullable=True)

    map_value = _map_value_type(normalized_type)
    if map_value is not None:
        return _kotlin_map_reader(field, model_names, value, nullable=True)

    return f"{value} as? {_kotlin_type(field, model_names).rstrip('?')}"

def _kotlin_list_reader(
    field: DartField,
    model_names: set[str],
    value: str,
    *,
    nullable: bool,
) -> str:
    """渲染 List 字段读取表达式。"""

    normalized_type = _strip_nullable_type(field.dart_type)
    list_inner = _generic_inner_type(normalized_type, "List")
    error = (
        f'ChannelMsgException("Field {field.name} is missing or has invalid type.")'
    )
    if list_inner is None:
        return f"{value} as? {_kotlin_type(field, model_names)}"

    list_value = f"({value} as? List<*>)"
    if list_inner in model_names:
        expression = (
            f"{list_value}?.map {{ item -> "
            f"{list_inner}.fromMap(ChannelMsgMapCoder.requireStringAnyMap(item, \"{field.name}\")) }}"
        )
    else:
        expression = f"{value} as? {_kotlin_type(field, model_names).rstrip('?')}"
    return expression if nullable else f"{expression} ?: throw {error}"

def _kotlin_map_reader(
    field: DartField,
    model_names: set[str],
    value: str,
    *,
    nullable: bool,
) -> str:
    """渲染 Map<String, T> 字段读取表达式。"""

    normalized_type = _strip_nullable_type(field.dart_type)
    map_value = _map_value_type(normalized_type)
    error = (
        f'ChannelMsgException("Field {field.name} is missing or has invalid type.")'
    )
    if map_value in model_names:
        expression = (
            f"({value} as? Map<*, *>)?.map {{ entry -> "
            f"val key = entry.key as? String ?: throw {error}; "
            f"key to {map_value}.fromMap(ChannelMsgMapCoder.requireStringAnyMap(entry.value, \"{field.name}\")) "
            "}?.toMap()"
        )
    else:
        expression = f"{value} as? {_kotlin_type(field, model_names).rstrip('?')}"
    return expression if nullable else f"{expression} ?: throw {error}"

def _kotlin_to_map_value(field: DartField, model_names: set[str]) -> str:
    """渲染字段写入 Map 时的表达式。"""

    normalized_type = _strip_nullable_type(field.dart_type)
    value = field.name
    if normalized_type in model_names:
        return f"{value}?.toMap()" if field.nullable else f"{value}.toMap()"

    list_inner = _generic_inner_type(normalized_type, "List")
    if list_inner in model_names:
        return (
            f"{value}?.map {{ it.toMap() }}" if field.nullable else f"{value}.map {{ it.toMap() }}"
        )

    map_value = _map_value_type(normalized_type)
    if map_value in model_names:
        return (
            f"{value}?.mapValues {{ it.value.toMap() }}"
            if field.nullable
            else f"{value}.mapValues {{ it.value.toMap() }}"
        )

    return value

def _needs_kotlin_map_helper(message: MessageClass) -> bool:
    """判断当前消息文件是否需要嵌套 Map 读取辅助函数。"""

    if not message.nested_models:
        return False
    model_names = {model.class_name for model in message.nested_models}
    all_fields = [*message.fields]
    for model in message.nested_models:
        all_fields.extend(model.fields)
    return any(_field_references_model(field, model_names) for field in all_fields)

def _field_references_model(field: DartField, model_names: set[str]) -> bool:
    """判断字段是否引用了同文件 model。"""

    normalized_type = _strip_nullable_type(field.dart_type)
    if normalized_type in model_names:
        return True
    list_inner = _generic_inner_type(normalized_type, "List")
    if list_inner in model_names:
        return True
    map_value = _map_value_type(normalized_type)
    return map_value in model_names

def _kotlin_default_value(field: DartField) -> str | None:
    """将 Dart 字段默认值映射为 Kotlin 字面量。"""

    if field.default_value is None:
        return None
    value = field.default_value
    if value == "null":
        return "null" if field.nullable else None
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
