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
    handlers = _scan_android_handlers(config.handler_scan_path)
    _reset_android_output_root(
        config.output_root,
        config.generated_registrations_output_path,
    )
    _write_android_runtime_files(config.output_root, config)
    _write_android_messages(
        config.output_root,
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
    generated_registrations_output_path: Path,
) -> None:
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

    generated_msgs = output_root / "msgs"
    if generated_msgs.exists():
        shutil.rmtree(generated_msgs)
    generated_msgs.mkdir(parents=True, exist_ok=True)

def _scan_android_handlers(scan_path: Path) -> list[HandlerClass]:
    if not scan_path.exists():
        scan_path.mkdir(parents=True, exist_ok=True)

    handlers: list[HandlerClass] = []
    for kotlin_file in sorted(scan_path.rglob("*.kt")):
        handlers.extend(_parse_android_handler_file(kotlin_file))
    return sorted(handlers, key=lambda item: item.channel_name)

def _parse_android_handler_file(kotlin_file: Path) -> list[HandlerClass]:
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

def _write_android_runtime_files(
    output_root: Path,
    config: AndroidGeneratorConfig,
) -> None:
    package_name = config.package_name
    _write_file(
        output_root / "ChannelMsgException.g.kt",
        _android_platform_channel_msg_exception(package_name),
    )
    _write_file(
        output_root / "ChannelBaseMsg.g.kt",
        _android_platform_channel_base_msg(package_name),
    )
    _write_file(
        output_root / "ChannelBaseHandler.g.kt",
        _android_platform_channel_base_handler(package_name),
    )
    _write_file(
        output_root / "ChannelBaseMsgRegister.g.kt",
        _android_channel_base_msg_register(package_name),
    )
    _write_file(
        output_root / "ChannelHandlerRegister.g.kt",
        _android_channel_handler_register(package_name),
    )
    _write_file(
        output_root / "MethodChannelMsgManager.g.kt",
        _android_method_channel_msg_manager(package_name, config.method_channel_name),
    )

def _write_android_messages(
    output_root: Path,
    package_name: str,
    messages: list[MessageClass],
) -> None:
    for message in messages:
        _write_file(
            output_root / "msgs" / f"{message.class_name}.g.kt",
            _android_message_kotlin(package_name, message),
        )

def _write_android_generated_registrations(
    output_path: Path,
    output_root: Path,
    package_name: str,
    messages: list[MessageClass],
    handlers: list[HandlerClass],
) -> None:
    lines = _android_header(package_name)
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
        lines.append("        // Register handwritten Android handlers here.")

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
    return [
        "// GENERATED CODE - DO NOT MODIFY BY HAND",
        "// Generated by zh_native_channel_generator/scripts/generate_native_channel.py",
        "",
        f"package {package_name}",
    ]

def _android_platform_channel_msg_exception(package_name: str) -> str:
    lines = _android_header(package_name) + [
        "",
        "class ChannelMsgException(message: String) : Exception(message)",
    ]
    return "\n".join(lines) + "\n"

def _android_platform_channel_base_msg(package_name: str) -> str:
    lines = _android_header(package_name) + [
        "",
        "interface ChannelBaseMsg {",
        "    val channelName: String",
        "    fun toMap(): Map<String, Any?>",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _android_platform_channel_base_handler(package_name: str) -> str:
    lines = _android_header(package_name) + [
        "",
        "interface ChannelBaseHandler {",
        "    fun handle(message: ChannelBaseMsg): ChannelBaseMsg",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _android_channel_base_msg_register(package_name: str) -> str:
    lines = _android_header(package_name) + [
        "",
        "class ChannelBaseMsgRegister {",
        "    private val channelMap = mutableMapOf<String, (Map<String, Any?>) -> ChannelBaseMsg>()",
        "",
        "    init {",
        "        GeneratedChannelRegistrations.registerMessages(this)",
        "    }",
        "",
        "    fun registerChannel(channelName: String, factory: (Map<String, Any?>) -> ChannelBaseMsg) {",
        "        channelMap[channelName] = factory",
        "    }",
        "",
        "    fun getChannel(channelName: String, params: Map<String, Any?>): ChannelBaseMsg {",
        "        val factory = channelMap[channelName]",
        "            ?: throw ChannelMsgException(\"Missing message factory: $channelName\")",
        "        return factory(params)",
        "    }",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _android_channel_handler_register(package_name: str) -> str:
    lines = _android_header(package_name) + [
        "",
        "class ChannelHandlerRegister {",
        "    private val container = mutableMapOf<String, ChannelBaseHandler>()",
        "",
        "    init {",
        "        GeneratedChannelRegistrations.registerHandlers(this)",
        "    }",
        "",
        "    fun registerChannel(channelName: String, handler: ChannelBaseHandler) {",
        "        container[channelName] = handler",
        "    }",
        "",
        "    fun getChannelHandler(channelName: String): ChannelBaseHandler {",
        "        return container[channelName]",
        "            ?: throw ChannelMsgException(\"Missing handler: $channelName\")",
        "    }",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _android_method_channel_msg_manager(
    package_name: str,
    method_channel_name: str,
) -> str:
    escaped_channel_name = _escape_kotlin_string(method_channel_name)
    lines = _android_header(package_name) + [
        "",
        "import io.flutter.plugin.common.BinaryMessenger",
        "import io.flutter.plugin.common.MethodCall",
        "import io.flutter.plugin.common.MethodChannel",
        "",
        "object MethodChannelMsgManager : MethodChannel.MethodCallHandler {",
        "    private val msgRegister: ChannelBaseMsgRegister = ChannelBaseMsgRegister()",
        "    private val handlerRegister: ChannelHandlerRegister = ChannelHandlerRegister()",
        "    private var methodChannel: MethodChannel? = null",
        "",
        "    fun configureBinaryMessenger(",
        "        binaryMessenger: BinaryMessenger,",
        f'        channelName: String = "{escaped_channel_name}"',
        "    ) {",
        "        dispose()",
        "        methodChannel = MethodChannel(binaryMessenger, channelName).also { channel ->",
        "            channel.setMethodCallHandler(this)",
        "        }",
        "    }",
        "",
        "    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {",
        "        try {",
        "            result.success(handle(call))",
        "        } catch (error: Throwable) {",
        "            result.error(\"channel-error\", error.message, null)",
        "        }",
        "    }",
        "",
        "    fun dispose() {",
        "        methodChannel?.setMethodCallHandler(null)",
        "        methodChannel = null",
        "    }",
        "",
        "    fun invoke(message: ChannelBaseMsg, callback: (ChannelBaseMsg?, Throwable?) -> Unit) {",
        "        val channel = methodChannel",
        "        if (channel == null) {",
        "            callback(null, ChannelMsgException(\"MethodChannel is not configured.\"))",
        "            return",
        "        }",
        "",
        "        val methodName = message.channelName",
        "        val params = message.toMap().toMutableMap()",
        "        params[\"@:\"] = methodName",
        "        channel.invokeMethod(methodName, params, object : MethodChannel.Result {",
        "            override fun success(result: Any?) {",
        "                try {",
        "                    val resultMap = toStringAnyMap(result)",
        "                    callback(msgRegister.getChannel(methodName, resultMap), null)",
        "                } catch (error: Throwable) {",
        "                    callback(null, error)",
        "                }",
        "            }",
        "",
        "            override fun error(errorCode: String, errorMessage: String?, errorDetails: Any?) {",
        "                callback(null, ChannelMsgException(errorMessage ?: errorCode))",
        "            }",
        "",
        "            override fun notImplemented() {",
        "                callback(null, ChannelMsgException(\"Method $methodName is not implemented.\"))",
        "            }",
        "        })",
        "    }",
        "",
        "    private fun handle(call: MethodCall): Map<String, Any?> {",
        "        val params = call.arguments as? Map<*, *> ?: emptyMap<String, Any?>()",
        "        val typedParams = params.entries.associate { it.key.toString() to it.value }",
        "        val channelName = typedParams[\"@:\"] as? String ?: call.method",
        "        val message = msgRegister.getChannel(channelName, typedParams)",
        "        val handler = handlerRegister.getChannelHandler(channelName)",
        "        val response = handler.handle(message)",
        "        return response.toMap() + mapOf(\"@:\" to channelName)",
        "    }",
        "",
        "    private fun toStringAnyMap(value: Any?): Map<String, Any?> {",
        "        val map = value as? Map<*, *>",
        "            ?: throw ChannelMsgException(\"Method result must be a map.\")",
        "        return map.entries.associate { entry ->",
        "            val key = entry.key as? String",
        "                ?: throw ChannelMsgException(\"Method result map key must be a String.\")",
        "            key to entry.value",
        "        }",
        "    }",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _android_message_kotlin(package_name: str, message: MessageClass) -> str:
    lines = _android_header(f"{package_name}.msgs") + [
        "",
        f"import {package_name}.ChannelBaseMsg",
        f"import {package_name}.ChannelMsgException",
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
    return value.replace("\\", "\\\\").replace('"', '\\"')
