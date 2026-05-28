from __future__ import annotations

import os
import shutil
from pathlib import Path

from .common import (
    DartField,
    HandlerClass,
    MessageClass,
    WebGeneratorConfig,
    _parse_platform_handler_file,
    _write_file,
)


def generate_web(
    config: WebGeneratorConfig,
    messages: list[MessageClass],
) -> list[HandlerClass]:
    handlers = _scan_web_handlers(config.handler_scan_path)
    _reset_web_output_root(config.output_root, config.generated_registrations_output_path)
    _write_web_runtime_files(config.output_root, config)
    _write_web_messages(config.output_root, messages)
    _write_web_generated_registrations(
        config.generated_registrations_output_path,
        config.output_root,
        config.handler_scan_path,
        messages,
        handlers,
    )
    return handlers


def _reset_web_output_root(
    output_root: Path,
    generated_registrations_output_path: Path,
) -> None:
    generated_files = [
        "ChannelBaseMsg.ts",
        "ChannelBaseHandler.ts",
        "ChannelMsgError.ts",
        "ChannelBaseMsgRegister.ts",
        "ChannelHandlerRegister.ts",
        "MethodChannelMsgManager.ts",
        "GeneratedChannelRegistrations.ts",
        "index.ts",
    ]
    for file_name in generated_files:
        generated_file = output_root / file_name
        if generated_file.exists():
            generated_file.unlink()

    generated_registrations_file = (
        generated_registrations_output_path / "GeneratedChannelRegistrations.ts"
    )
    if generated_registrations_file.exists():
        generated_registrations_file.unlink()

    generated_msgs = output_root / "msgs"
    if generated_msgs.exists():
        shutil.rmtree(generated_msgs)
    generated_msgs.mkdir(parents=True, exist_ok=True)

def _scan_web_handlers(scan_path: Path) -> list[HandlerClass]:
    if not scan_path.exists():
        scan_path.mkdir(parents=True, exist_ok=True)

    handlers: list[HandlerClass] = []
    for web_file in sorted([*scan_path.rglob("*.ts"), *scan_path.rglob("*.js")]):
        handlers.extend(_parse_platform_handler_file(web_file))
    return sorted(handlers, key=lambda item: item.channel_name)

def _write_web_runtime_files(output_root: Path, config: WebGeneratorConfig) -> None:
    generated_registrations_import = _web_relative_import(
        output_root,
        config.generated_registrations_output_path / "GeneratedChannelRegistrations",
    )
    _write_file(output_root / "ChannelMsgError.ts", _web_platform_channel_msg_error())
    _write_file(output_root / "ChannelBaseMsg.ts", _web_platform_channel_base_msg())
    _write_file(
        output_root / "ChannelBaseHandler.ts",
        _web_platform_channel_base_handler(),
    )
    _write_file(
        output_root / "ChannelBaseMsgRegister.ts",
        _web_channel_base_msg_register(generated_registrations_import),
    )
    _write_file(
        output_root / "ChannelHandlerRegister.ts",
        _web_channel_handler_register(generated_registrations_import),
    )
    _write_file(
        output_root / "MethodChannelMsgManager.ts",
        _web_method_channel_msg_manager(config.global_name, config.method_channel_name),
    )
    _write_file(
        output_root / "index.ts",
        _web_index(output_root, config.generated_registrations_output_path),
    )

def _write_web_messages(output_root: Path, messages: list[MessageClass]) -> None:
    for message in messages:
        _write_file(
            output_root / "msgs" / f"{message.class_name}.ts",
            _web_message_typescript(message),
        )

def _write_web_generated_registrations(
    output_path: Path,
    output_root: Path,
    handler_scan_path: Path,
    messages: list[MessageClass],
    handlers: list[HandlerClass],
) -> None:
    lines = _web_header() + [
        "import { ChannelBaseMsgRegister } from "
        f"'{_web_relative_import(output_path, output_root / 'ChannelBaseMsgRegister')}';",
        "import { ChannelHandlerRegister } from "
        f"'{_web_relative_import(output_path, output_root / 'ChannelHandlerRegister')}';",
    ]

    for message in messages:
        lines.append(
            f"import {{ {message.class_name} }} from "
            f"'{_web_relative_import(output_path, output_root / 'msgs' / message.class_name)}';"
        )
    for handler in handlers:
        handler_import = _web_handler_import(
            output_path,
            output_root,
            handler_scan_path,
            handler,
        )
        if handler_import is not None:
            lines.append(handler_import)

    lines.extend(
        [
            "",
            "export function registerGeneratedChannelMessages(register: ChannelBaseMsgRegister): void {",
        ]
    )
    for message in messages:
        lines.append(
            f"  register.registerChannel('{message.channel_name}', "
            f"(map) => {message.class_name}.fromMap(map));"
        )

    lines.extend(
        [
            "}",
            "",
            "export function registerGeneratedChannelHandlers(register: ChannelHandlerRegister): void {",
        ]
    )
    if handlers:
        for handler in handlers:
            lines.append(
                f"  register.registerChannel('{handler.channel_name}', new {handler.class_name}());"
            )
    else:
        lines.append("  // Register handwritten Web handlers here.")

    lines.append("}")
    _write_file(
        output_path / "GeneratedChannelRegistrations.ts",
        "\n".join(lines) + "\n",
    )

def _web_handler_import(
    output_path: Path,
    output_root: Path,
    handler_scan_path: Path,
    handler: HandlerClass,
) -> str | None:
    if handler.file_path is None:
        return None
    try:
        relative_path = handler.file_path.resolve().relative_to(output_root.resolve())
        import_path = _web_relative_import(
            output_path,
            output_root / relative_path.with_suffix(""),
        )
    except ValueError:
        try:
            relative_path = handler.file_path.resolve().relative_to(
                handler_scan_path.resolve()
            )
        except ValueError:
            return None
        import_path = _web_relative_import(
            output_path,
            handler_scan_path / relative_path.with_suffix(""),
        )
    return f"import {{ {handler.class_name} }} from '{import_path}';"

def _web_relative_import(from_dir: Path, target_without_suffix: Path) -> str:
    relative_path = Path(
        os.path.relpath(target_without_suffix, from_dir)
    ).as_posix()
    if not relative_path.startswith("."):
        return f"./{relative_path}"
    return relative_path

def _web_header() -> list[str]:
    return [
        "// GENERATED CODE - DO NOT MODIFY BY HAND",
        "// Generated by zh_native_channel_generator/scripts/generate_native_channel.py",
        "",
    ]

def _web_platform_channel_msg_error() -> str:
    lines = _web_header() + [
        "export class ChannelMsgError extends Error {",
        "  constructor(message: string) {",
        "    super(message);",
        "    this.name = 'ChannelMsgError';",
        "  }",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _web_platform_channel_base_msg() -> str:
    lines = _web_header() + [
        "export type ChannelMap = Record<string, unknown>;",
        "",
        "export interface ChannelBaseMsg {",
        "  readonly channelName: string;",
        "  toMap(): ChannelMap;",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _web_platform_channel_base_handler() -> str:
    lines = _web_header() + [
        "import { ChannelBaseMsg } from './ChannelBaseMsg';",
        "",
        "export interface ChannelBaseHandler {",
        "  handle(message: ChannelBaseMsg): ChannelBaseMsg | Promise<ChannelBaseMsg>;",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _web_channel_base_msg_register(generated_registrations_import: str) -> str:
    lines = _web_header() + [
        "import { ChannelBaseMsg, ChannelMap } from './ChannelBaseMsg';",
        "import { ChannelMsgError } from './ChannelMsgError';",
        "import { registerGeneratedChannelMessages } from "
        f"'{generated_registrations_import}';",
        "",
        "export type CreateChannelBaseMsgClosure = (map: ChannelMap) => ChannelBaseMsg;",
        "",
        "export class ChannelBaseMsgRegister {",
        "  private readonly channelMap = new Map<string, CreateChannelBaseMsgClosure>();",
        "",
        "  constructor() {",
        "    registerGeneratedChannelMessages(this);",
        "  }",
        "",
        "  registerChannel(channelName: string, closure: CreateChannelBaseMsgClosure): void {",
        "    this.channelMap.set(channelName, closure);",
        "  }",
        "",
        "  getChannel(channelName: string, params: ChannelMap): ChannelBaseMsg {",
        "    const factory = this.channelMap.get(channelName);",
        "    if (!factory) {",
        "      throw new ChannelMsgError(`Missing message factory: ${channelName}`);",
        "    }",
        "    return factory(params);",
        "  }",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _web_channel_handler_register(generated_registrations_import: str) -> str:
    lines = _web_header() + [
        "import { ChannelBaseHandler } from './ChannelBaseHandler';",
        "import { ChannelMsgError } from './ChannelMsgError';",
        "import { registerGeneratedChannelHandlers } from "
        f"'{generated_registrations_import}';",
        "",
        "export class ChannelHandlerRegister {",
        "  private readonly container = new Map<string, ChannelBaseHandler>();",
        "",
        "  constructor() {",
        "    registerGeneratedChannelHandlers(this);",
        "  }",
        "",
        "  registerChannel(channelName: string, handler: ChannelBaseHandler): void {",
        "    this.container.set(channelName, handler);",
        "  }",
        "",
        "  getChannelHandler(channelName: string): ChannelBaseHandler {",
        "    const handler = this.container.get(channelName);",
        "    if (!handler) {",
        "      throw new ChannelMsgError(`Missing handler: ${channelName}`);",
        "    }",
        "    return handler;",
        "  }",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _web_method_channel_msg_manager(global_name: str, method_channel_name: str) -> str:
    escaped_global_name = _escape_typescript_string(global_name)
    escaped_method_channel_name = _escape_typescript_string(method_channel_name)
    lines = _web_header() + [
        "import { ChannelBaseMsgRegister } from './ChannelBaseMsgRegister';",
        "import { ChannelHandlerRegister } from './ChannelHandlerRegister';",
        "import { ChannelBaseMsg, ChannelMap } from './ChannelBaseMsg';",
        "",
        "export class MethodChannelMsgManager {",
        f"  readonly channelName = '{escaped_method_channel_name}';",
        "",
        "  constructor(",
        "    private readonly msgRegister = new ChannelBaseMsgRegister(),",
        "    private readonly handlerRegister = new ChannelHandlerRegister(),",
        "  ) {}",
        "",
        "  async invoke(message: ChannelBaseMsg): Promise<ChannelBaseMsg> {",
        "    const methodName = message.channelName;",
        "    const params = { ...message.toMap(), '@:': methodName };",
        "    const result = await this.handle(methodName, params);",
        "    return this.msgRegister.getChannel(methodName, result);",
        "  }",
        "",
        "  async handle(method: string, params: ChannelMap = {}): Promise<ChannelMap> {",
        "    const channelName = typeof params['@:'] === 'string' ? params['@:'] : method;",
        "    const message = this.msgRegister.getChannel(channelName, params);",
        "    const handler = this.handlerRegister.getChannelHandler(channelName);",
        "    const response = await handler.handle(message);",
        "    return { ...response.toMap(), '@:': channelName };",
        "  }",
        "}",
        "",
        "export function registerWebChannelBridge(globalName = "
        f"'{escaped_global_name}'): MethodChannelMsgManager {{",
        "  const manager = new MethodChannelMsgManager();",
        "  const target = globalThis as typeof globalThis & Record<string, unknown>;",
        "  target[globalName] = manager;",
        "  return manager;",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _web_message_typescript(message: MessageClass) -> str:
    lines = _web_header() + [
        "import { ChannelBaseMsg, ChannelMap } from '../ChannelBaseMsg';",
        "import { ChannelMsgError } from '../ChannelMsgError';",
        "",
        f"export class {message.class_name} implements ChannelBaseMsg {{",
        f"  readonly channelName = '{_escape_typescript_string(message.channel_name)}';",
    ]

    if message.fields:
        lines.append("  constructor(")
        for index, field in enumerate(message.fields):
            suffix = "," if index < len(message.fields) - 1 else ""
            lines.append(
                f"    readonly {field.name}: {_typescript_type(field)}{suffix}"
            )
        lines.append("  ) {}")
    else:
        lines.append("  constructor() {}")

    lines.extend(["", "  toMap(): ChannelMap {", "    return {"])
    for index, field in enumerate(message.fields):
        suffix = "," if index < len(message.fields) - 1 else ""
        lines.append(f"      {field.name}: this.{field.name}{suffix}")

    lines.extend(["    };", "  }", "", f"  static fromMap(map: ChannelMap): {message.class_name} {{"])
    for field in message.fields:
        lines.append(f"    const {field.name} = {_typescript_value_reader(field)};")

    constructor_args = ", ".join(field.name for field in message.fields)
    lines.extend([f"    return new {message.class_name}({constructor_args});", "  }", "}"])
    return "\n".join(lines) + "\n"

def _web_index(output_root: Path, generated_registrations_output_path: Path) -> str:
    generated_registrations_import = _web_relative_import(
        output_root,
        generated_registrations_output_path / "GeneratedChannelRegistrations",
    )
    lines = _web_header() + [
        "export * from './ChannelBaseMsg';",
        "export * from './ChannelBaseHandler';",
        "export * from './ChannelMsgError';",
        "export * from './ChannelBaseMsgRegister';",
        "export * from './ChannelHandlerRegister';",
        "export * from './MethodChannelMsgManager';",
        f"export * from '{generated_registrations_import}';",
    ]
    return "\n".join(lines) + "\n"

def _typescript_type(field: DartField) -> str:
    type_map = {
        "String": "string",
        "int": "number",
        "double": "number",
        "num": "number",
        "bool": "boolean",
        "Map<String, dynamic>": "Record<string, unknown>",
    }
    if field.dart_type.startswith("List<"):
        typescript_type = "unknown[]"
    else:
        typescript_type = type_map.get(field.dart_type, "unknown")
    return f"{typescript_type} | null" if field.nullable else typescript_type

def _typescript_value_reader(field: DartField) -> str:
    value = f"map['{field.name}']"
    if field.nullable:
        return f"{value} == null ? null : ({value} as {_typescript_type(field).replace(' | null', '')})"
    typescript_type = _typescript_type(field)
    return (
        f"(({value} as {typescript_type} | null | undefined) ?? "
        f"(() => {{ throw new ChannelMsgError('Field {field.name} is missing.'); }})()"
        ")"
    )

def _escape_typescript_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")
