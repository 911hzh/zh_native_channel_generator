from __future__ import annotations

import os
from pathlib import Path

from .common import (
    DartField,
    HandlerClass,
    MessageClass,
    WebGeneratorConfig,
    _parse_platform_handler_file,
    _write_file,
    log_step,
)

DEFAULT_METHOD_CHANNEL_NAME = "zh_native_channel"


def generate_web(
    config: WebGeneratorConfig,
    messages: list[MessageClass],
) -> list[HandlerClass]:
    """生成 Web 运行时文件、消息类型和注册代码。"""

    log_step("Web 脚本开始执行")
    log_step(
        "Web 扫描 handler: "
        + ", ".join(path.as_posix() for path in config.handler_scan_paths)
    )
    handlers = _scan_web_handlers(config.handler_scan_paths)
    log_step(f"Web 已扫描到 {len(handlers)} 个 handler")
    log_step(f"Web 清理旧生成产物: {config.output_root}")
    _reset_web_output_root(
        config.output_root,
        config.generated_messages_output_path,
        config.generated_registrations_output_path,
    )
    log_step(f"Web 写入运行时文件: {config.output_root}")
    _write_web_runtime_files(config.output_root, config)
    log_step(f"Web 写入消息文件: {config.generated_messages_output_path}")
    _write_web_messages(config.generated_messages_output_path, messages)
    log_step(f"Web 写入注册文件: {config.generated_registrations_output_path}")
    _write_web_generated_registrations(
        config.generated_registrations_output_path,
        config.output_root,
        config.generated_messages_output_path,
        config.handler_scan_paths,
        messages,
        handlers,
    )
    log_step("Web 脚本执行完成")
    return handlers


def clean_web_generated(config: WebGeneratorConfig) -> list[Path]:
    """删除配置指定位置的 Web 生成产物，并返回实际删除的路径。"""

    return _delete_web_generated_outputs(
        config.output_root,
        config.generated_messages_output_path,
        config.generated_registrations_output_path,
    )


def _reset_web_output_root(
    output_root: Path,
    generated_messages_output_path: Path,
    generated_registrations_output_path: Path,
) -> None:
    """写入新产物前删除旧的 Web 生成文件。"""

    _delete_web_generated_outputs(
        output_root,
        generated_messages_output_path,
        generated_registrations_output_path,
    )
    generated_messages_output_path.mkdir(parents=True, exist_ok=True)


def _delete_web_generated_outputs(
    output_root: Path,
    generated_messages_output_path: Path,
    generated_registrations_output_path: Path,
) -> list[Path]:
    """删除旧的 Web 生成文件，保留用户配置的输出目录。"""

    deleted_paths: list[Path] = []
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
            deleted_paths.append(generated_file)

    generated_registrations_file = (
        generated_registrations_output_path / "GeneratedChannelRegistrations.ts"
    )
    if generated_registrations_file.exists():
        generated_registrations_file.unlink()
        deleted_paths.append(generated_registrations_file)

    if generated_messages_output_path.exists():
        for generated_message_file in sorted(generated_messages_output_path.glob("*.ts")):
            if generated_message_file.is_file():
                generated_message_file.unlink()
                deleted_paths.append(generated_message_file)

    return deleted_paths

def _scan_web_handlers(scan_paths: list[Path]) -> list[HandlerClass]:
    """扫描 TypeScript 和 JavaScript 文件中的平台 handler 注解。"""

    handlers: list[HandlerClass] = []
    seen_files: set[Path] = set()
    for scan_path in scan_paths:
        if not scan_path.exists():
            scan_path.mkdir(parents=True, exist_ok=True)

        for web_file in sorted([*scan_path.rglob("*.ts"), *scan_path.rglob("*.js")]):
            resolved_web_file = web_file.resolve()
            if resolved_web_file in seen_files:
                continue
            seen_files.add(resolved_web_file)
            handlers.extend(_parse_platform_handler_file(web_file))
    return sorted(handlers, key=lambda item: item.channel_name)

def _write_web_runtime_files(output_root: Path, config: WebGeneratorConfig) -> None:
    """写入生成消息代码需要的 Web 共享运行时辅助文件。"""

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
        _web_method_channel_msg_manager(config.global_name),
    )
    _write_file(
        output_root / "index.ts",
        _web_index(output_root, config.generated_registrations_output_path),
    )

def _write_web_messages(output_path: Path, messages: list[MessageClass]) -> None:
    """将生成的 TypeScript 消息类写入配置指定目录。"""

    for message in messages:
        _write_file(
            output_path / f"{message.class_name}.ts",
            _web_message_typescript(message),
        )

def _write_web_generated_registrations(
    output_path: Path,
    output_root: Path,
    generated_messages_output_path: Path,
    handler_scan_paths: list[Path],
    messages: list[MessageClass],
    handlers: list[HandlerClass],
) -> None:
    """写入用于连接消息和 handler 的 TypeScript 注册文件。"""

    lines = _web_header() + [
        "import { ChannelBaseMsgRegister } from "
        f"'{_web_relative_import(output_path, output_root / 'ChannelBaseMsgRegister')}';",
        "import { ChannelHandlerRegister } from "
        f"'{_web_relative_import(output_path, output_root / 'ChannelHandlerRegister')}';",
    ]

    for message in messages:
        lines.append(
            f"import {{ {message.class_name} }} from "
            f"'{_web_relative_import(output_path, generated_messages_output_path / message.class_name)}';"
        )
    for handler in handlers:
        handler_import = _web_handler_import(
            output_path,
            output_root,
            handler_scan_paths,
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
        lines.append("  // 在这里注册手写的 Web handler。")

    lines.append("}")
    _write_file(
        output_path / "GeneratedChannelRegistrations.ts",
        "\n".join(lines) + "\n",
    )

def _web_handler_import(
    output_path: Path,
    output_root: Path,
    handler_scan_paths: list[Path],
    handler: HandlerClass,
) -> str | None:
    """为扫描到的 Web handler 文件生成相对 import。"""

    if handler.file_path is None:
        return None
    try:
        relative_path = handler.file_path.resolve().relative_to(output_root.resolve())
        import_path = _web_relative_import(
            output_path,
            output_root / relative_path.with_suffix(""),
        )
    except ValueError:
        for handler_scan_path in handler_scan_paths:
            try:
                relative_path = handler.file_path.resolve().relative_to(
                    handler_scan_path.resolve()
                )
            except ValueError:
                continue
            import_path = _web_relative_import(
                output_path,
                handler_scan_path / relative_path.with_suffix(""),
            )
            break
        else:
            return None
    return f"import {{ {handler.class_name} }} from '{import_path}';"

def _web_relative_import(from_dir: Path, target_without_suffix: Path) -> str:
    """返回不带文件后缀的 TypeScript 相对 import 路径。"""

    relative_path = Path(
        os.path.relpath(target_without_suffix, from_dir)
    ).as_posix()
    if not relative_path.startswith("."):
        return f"./{relative_path}"
    return relative_path

def _web_header() -> list[str]:
    """返回生成 TypeScript 文件的标准头部。"""

    return [
        "// 自动生成代码，请勿手动修改",
        "// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成",
        "",
    ]

def _web_platform_channel_msg_error() -> str:
    """渲染生成的 ChannelMsgError TypeScript 源码。"""

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
    """渲染生成的 ChannelBaseMsg TypeScript 源码。"""

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
    """渲染生成的 ChannelBaseHandler TypeScript 源码。"""

    lines = _web_header() + [
        "import { ChannelBaseMsg } from './ChannelBaseMsg';",
        "",
        "export interface ChannelBaseHandler {",
        "  handle(message: ChannelBaseMsg): ChannelBaseMsg | Promise<ChannelBaseMsg>;",
        "}",
    ]
    return "\n".join(lines) + "\n"

def _web_channel_base_msg_register(generated_registrations_import: str) -> str:
    """渲染 Web 消息工厂注册表 TypeScript 源码。"""

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
    """渲染 Web handler 注册表 TypeScript 源码。"""

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

def _web_method_channel_msg_manager(global_name: str) -> str:
    """渲染面向浏览器的 MethodChannelMsgManager TypeScript 源码。"""

    escaped_global_name = _escape_typescript_string(global_name)
    escaped_method_channel_name = _escape_typescript_string(DEFAULT_METHOD_CHANNEL_NAME)
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
    """为单个 Dart 消息渲染 TypeScript ChannelBaseMsg 实现。"""

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
    """渲染生成的 Web barrel 导出文件。"""

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
    """将支持的 Dart 字段类型映射为 TypeScript 类型。"""

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
    """渲染从 channel map 读取单个字段的 TypeScript 代码。"""

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
    """转义生成 TypeScript 源码中的字符串字面量。"""

    return value.replace("\\", "\\\\").replace("'", "\\'")
