#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from native_channel_generator.android import generate_android
from native_channel_generator.common import (
    DEFAULT_CONFIG_NAME,
    DEFAULT_DART_HANDLER_SCAN_PATH,
    DEFAULT_DART_MESSAGE_SCAN_PATH,
    DEFAULT_DART_OUTPUT_DIRECTORY,
    DEFAULT_DART_REGISTER_FILE_NAME,
    _read_android_config,
    _read_config,
    _read_ios_config,
    _read_optional_config_string_list,
    _read_web_config,
    _resolve_config_path,
    _scan_messages,
)
from native_channel_generator.ios import generate_ios
from native_channel_generator.web import generate_web


def main() -> int:
    """运行同步构建配置并生成平台代码的命令行入口。"""

    parser = argparse.ArgumentParser(
        description="Generate zh_native_channel platform code.",
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=DEFAULT_CONFIG_NAME,
        help=f"Path to config JSON. Defaults to {DEFAULT_CONFIG_NAME}.",
    )
    parser.add_argument(
        "--platform",
        choices=("all", "ios", "android", "web"),
        default="all",
        help="Generate all platforms or a single platform.",
    )
    parser.add_argument(
        "--sync-build-config-only",
        action="store_true",
        help="Only sync build.yaml from config JSON and exit.",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = _read_config(config_path)
    config_root = config_path.parent
    _ensure_makefile(config_root, config_path)
    did_sync_build_yaml = _sync_build_yaml(config_root, config)

    if args.sync_build_config_only:
        if did_sync_build_yaml:
            print(f"Synced build.yaml from {config_path}")
        else:
            print(
                f"Skipped build.yaml sync because {config_root / 'pubspec.yaml'} does not exist."
            )
        return 0

    messages = _scan_messages(_read_message_scan_paths(config, config_root))

    if args.platform in ("all", "ios"):
        ios_config = _read_ios_config(config, config_root)
        if ios_config is None:
            if args.platform == "ios":
                raise ValueError("Missing platforms.ios config.")
        else:
            ios_handlers = generate_ios(ios_config, messages)
            print(
                f"Generated {len(messages)} message type(s) and "
                f"{len(ios_handlers)} iOS handler registration(s): "
                f"{ios_config.output_root}"
            )

    if args.platform in ("all", "android"):
        android_config = _read_android_config(config, config_root)
        if android_config is None:
            if args.platform == "android":
                raise ValueError("Missing platforms.android config.")
        else:
            android_handlers = generate_android(android_config, messages)
            print(
                f"Generated {len(messages)} message type(s) and "
                f"{len(android_handlers)} Android handler registration(s): "
                f"{android_config.output_root}"
            )

    if args.platform in ("all", "web"):
        web_config = _read_web_config(config, config_root)
        if web_config is None:
            if args.platform == "web":
                raise ValueError("Missing platforms.web config.")
        else:
            web_handlers = generate_web(web_config, messages)
            print(
                f"Generated {len(messages)} message type(s) and "
                f"{len(web_handlers)} Web handler registration(s): "
                f"{web_config.output_root}"
            )

    return 0


def _read_message_scan_paths(config: dict, config_root: Path) -> list[Path]:
    """从新版或旧版配置字段中解析 Dart 消息扫描路径。"""

    scan_paths = _read_optional_config_string_list(
        config,
        ("dart", "messageScanPath"),
        legacy_key="packageMessageScanPath",
    )
    if scan_paths is None:
        return [config_root]
    return [_resolve_config_path(path, config_root) for path in scan_paths]


def _ensure_makefile(config_root: Path, config_path: Path) -> None:
    """创建或更新由生成器管理的 Makefile 命令块。"""

    makefile_path = config_root / "Makefile"
    script_path = Path(__file__).resolve()
    relative_script_path = _make_relative_path(script_path, config_root)
    relative_config_path = _make_relative_path(config_path, config_root)

    block_start = "# >>> zh_native_channel_generator"
    block_end = "# <<< zh_native_channel_generator"
    native_targets = f"""PYTHON ?= python3
ZH_NATIVE_CHANNEL_GENERATOR ?= {relative_script_path}
ZH_NATIVE_CHANNEL_CONFIG ?= {relative_config_path}

.PHONY: build-runner-sync-config build-runner-build create-platformcode-all create-platformcode-ios create-platformcode-android create-platformcode-web gen

build-runner-sync-config:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --sync-build-config-only

build-runner-build: build-runner-sync-config
\t@if [ ! -f pubspec.yaml ]; then echo "当前目录没有 pubspec.yaml，跳过 build_runner。"; else dart run build_runner build; fi

gen:
\t$(MAKE) build-runner-build
\t$(MAKE) create-platformcode-all

create-platformcode-all:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform all

create-platformcode-ios:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform ios

create-platformcode-android:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform android

create-platformcode-web:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform web
"""
    block = f"""{block_start}
{native_targets}{block_end}
"""
    standalone_makefile = f"""{block_start}
PYTHON ?= python3
ZH_NATIVE_CHANNEL_GENERATOR ?= {relative_script_path}
ZH_NATIVE_CHANNEL_CONFIG ?= {relative_config_path}

.PHONY: build-runner-sync-config build-runner-build create-platformcode-all create-platformcode-ios create-platformcode-android create-platformcode-web gen

build-runner-sync-config:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --sync-build-config-only

build-runner-build: build-runner-sync-config
\t@if [ ! -f pubspec.yaml ]; then echo "当前目录没有 pubspec.yaml，跳过 build_runner。"; else dart run build_runner build; fi

gen:
\t$(MAKE) build-runner-build
\t$(MAKE) create-platformcode-all

create-platformcode-all:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform all

create-platformcode-ios:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform ios

create-platformcode-android:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform android

create-platformcode-web:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform web
{block_end}
"""

    if not makefile_path.exists():
        makefile_path.write_text(standalone_makefile, encoding="utf-8")
        return

    content = makefile_path.read_text(encoding="utf-8")
    if block_start in content and block_end in content:
        before, rest = content.split(block_start, 1)
        _, after = rest.split(block_end, 1)
        makefile_path.write_text(before.rstrip() + "\n\n" + block + after, encoding="utf-8")
        return

    makefile_path.write_text(content.rstrip() + "\n\n" + block, encoding="utf-8")


def _sync_build_yaml(config_root: Path, config: dict) -> bool:
    """根据 JSON 配置同步写入 build.yaml。"""

    pubspec_path = config_root / "pubspec.yaml"
    if not pubspec_path.exists():
        return False

    dart_config = _read_dart_build_config(config, config_root)
    build_yaml_path = config_root / "build.yaml"
    scan_globs = dart_config["scan_globs"]
    options = {
        "basePath": dart_config["basePath"],
        "register_path": dart_config["register_path"],
    }

    lines = [
        "targets:",
        "  $default:",
        "    builders:",
        "      zh_native_channel_generator|channel_register_builder:",
        "        enabled: true",
        "        options:",
        "          scan_globs:",
    ]
    lines.extend(f"            - {item}" for item in scan_globs)
    lines.extend(
        [
            f"          basePath: {options['basePath']}",
            f"          register_path: {options['register_path']}",
            "",
        ]
    )
    build_yaml_path.write_text("\n".join(lines), encoding="utf-8")
    return True


def _read_dart_build_config(config: dict, config_root: Path) -> dict:
    """读取用于同步 build.yaml 的 Dart 生成配置。"""

    default_output_directory = _read_dart_default_output_directory(config)
    register_output_path = _read_dart_register_output_path(
        config,
        default_output_directory,
    )
    scan_globs = _read_dart_scan_globs(config, config_root)
    base_path, register_path = _split_dart_register_output_path(register_output_path)

    return {
        "scan_globs": scan_globs,
        "basePath": base_path,
        "register_path": register_path,
    }


def _read_dart_default_output_directory(config: dict) -> str:
    """读取 Dart 侧生成文件默认输出目录。"""

    dart_config = config.get("dart")
    if isinstance(dart_config, dict):
        value = dart_config.get("defaultOutputDirectory")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return DEFAULT_DART_OUTPUT_DIRECTORY


def _read_dart_register_output_path(config: dict, default_output_directory: str) -> str:
    """读取 Dart 侧注册文件输出路径。"""

    dart_config = config.get("dart")
    if isinstance(dart_config, dict):
        value = dart_config.get("generatedChannelRegisterOutputPath")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"{default_output_directory.rstrip('/')}/{DEFAULT_DART_REGISTER_FILE_NAME}"


def _read_dart_scan_globs(config: dict, config_root: Path) -> list[str]:
    """读取 Dart build_runner 扫描范围并转换成 glob。"""

    scan_paths: list[str] = []
    message_scan_paths = _read_optional_config_string_list(
        config,
        ("dart", "messageScanPath"),
        legacy_key="packageMessageScanPath",
    )
    handler_scan_paths = _read_optional_config_string_list(
        config,
        ("dart", "handlerScanPath"),
    )

    if message_scan_paths is None and handler_scan_paths is None:
        return ["lib/**.dart"]

    scan_paths.extend(message_scan_paths or [DEFAULT_DART_MESSAGE_SCAN_PATH])
    scan_paths.extend(handler_scan_paths or [DEFAULT_DART_HANDLER_SCAN_PATH])

    globs: list[str] = []
    for scan_path in scan_paths:
        normalized = _normalize_config_path_for_build_yaml(scan_path, config_root)
        glob = f"{normalized.rstrip('/')}/**.dart"
        if glob not in globs:
            globs.append(glob)
    return globs


def _split_dart_register_output_path(register_output_path: str) -> tuple[str, str]:
    """将 Dart 注册输出路径拆成 build.yaml 使用的 basePath 和 register_path。"""

    normalized = register_output_path.strip().replace("\\", "/").strip("/")
    if not normalized:
        normalized = f"{DEFAULT_DART_OUTPUT_DIRECTORY}/{DEFAULT_DART_REGISTER_FILE_NAME}"
    path = Path(normalized)
    parent = path.parent.as_posix()
    file_name = path.name
    if parent == ".":
        parent = DEFAULT_DART_OUTPUT_DIRECTORY
    return parent, file_name


def _normalize_config_path_for_build_yaml(path: str, config_root: Path) -> str:
    """将配置路径转换成 build.yaml 可以使用的项目相对路径。"""

    raw_path = Path(path)
    if raw_path.is_absolute():
        try:
            return raw_path.relative_to(config_root).as_posix()
        except ValueError:
            return raw_path.as_posix()
    return Path(path).as_posix()


def _read_pubspec_dart_config(pubspec_path: Path) -> dict | None:
    """从 pubspec.yaml 读取 zh_native_channel_generator.dart 配置。"""

    lines = pubspec_path.read_text(encoding="utf-8").splitlines()
    section = _read_yaml_object(lines, "zh_native_channel_generator")
    dart_section = section.get("dart")
    if not isinstance(dart_section, dict):
        return None

    scan_globs = dart_section.get("scan_globs")
    if not isinstance(scan_globs, list) or not all(isinstance(item, str) for item in scan_globs):
        raise ValueError(
            "pubspec.yaml zh_native_channel_generator.dart.scan_globs must be a string list."
        )

    return {
        "scan_globs": scan_globs,
        "basePath": _read_pubspec_string(
            dart_section,
            "basePath",
            "lib/base/zHNativeChannel",
        ),
        "register_path": _read_pubspec_string(
            dart_section,
            "register_path",
            "ChannelGeneratedRegister.g.dart",
        ),
    }


def _read_pubspec_string(section: dict, key: str, default: str) -> str:
    """从 pubspec 生成器配置段读取非空字符串。"""

    value = section.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"pubspec.yaml zh_native_channel_generator.dart.{key} must be a non-empty string."
        )
    return value.strip()


def _read_yaml_object(lines: list[str], root_key: str) -> dict:
    """解析当前包 pubspec 配置需要的有限 YAML 子集。"""

    root_index = None
    for index, line in enumerate(lines):
        if line.strip() == f"{root_key}:" and _indent_width(line) == 0:
            root_index = index
            break

    if root_index is None:
        return {}

    result: dict = {}
    stack: list[tuple[int, dict | list]] = [(0, result)]
    index = root_index + 1
    while index < len(lines):
        raw_line = lines[index]
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue

        indent = _indent_width(raw_line)
        if indent == 0:
            break

        while stack and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        if stripped.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Invalid list item in {root_key}: {raw_line}")
            parent.append(stripped[2:].strip())
            index += 1
            continue

        key, _, raw_value = stripped.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            index += 1
            continue

        if raw_value:
            if not isinstance(parent, dict):
                raise ValueError(f"Invalid mapping item in {root_key}: {raw_line}")
            parent[key] = raw_value.strip("'\"")
            index += 1
            continue

        next_container: dict | list = {}
        next_index = _next_content_line_index(lines, index + 1)
        if next_index is not None and lines[next_index].strip().startswith("- "):
            next_container = []
        if not isinstance(parent, dict):
            raise ValueError(f"Invalid nested item in {root_key}: {raw_line}")
        parent[key] = next_container
        stack.append((indent, next_container))
        index += 1

    return result


def _next_content_line_index(lines: list[str], start: int) -> int | None:
    """返回从 start 开始的下一条非空、非注释行索引。"""

    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("#"):
            return index
    return None


def _indent_width(value: str) -> int:
    """统计 YAML 行的前导空格数量。"""

    return len(value) - len(value.lstrip(" "))


def _make_relative_path(path: Path, root: Path) -> str:
    """返回用于 Makefile 变量的 POSIX 风格相对路径。"""

    return Path(os.path.relpath(path, root)).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
