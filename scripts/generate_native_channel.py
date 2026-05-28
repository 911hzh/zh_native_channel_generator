#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from native_channel_generator.android import generate_android
from native_channel_generator.common import (
    DEFAULT_CONFIG_NAME,
    _read_android_config,
    _read_config,
    _read_ios_config,
    _read_web_config,
    _resolve_config_path,
    _scan_messages,
)
from native_channel_generator.ios import generate_ios
from native_channel_generator.web import generate_web


def main() -> int:
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
        help="Only sync build.yaml from pubspec.yaml and exit.",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = _read_config(config_path)
    config_root = config_path.parent
    _ensure_makefile(config_root, config_path)
    _sync_build_yaml(config_root)

    if args.sync_build_config_only:
        print(f"Synced build.yaml from {config_root / 'pubspec.yaml'}")
        return 0

    messages = _scan_messages(_read_message_scan_path(config, config_root))

    if args.platform in ("all", "ios"):
        ios_config = _read_ios_config(config, config_root)
        ios_handlers = generate_ios(ios_config, messages)
        print(
            f"Generated {len(messages)} message type(s) and "
            f"{len(ios_handlers)} iOS handler registration(s): "
            f"{ios_config.output_root}"
        )

    if args.platform in ("all", "android"):
        android_config = _read_android_config(config, config_root)
        if android_config is None:
            raise ValueError("Missing platforms.android config.")
        android_handlers = generate_android(android_config, messages)
        print(
            f"Generated {len(messages)} message type(s) and "
            f"{len(android_handlers)} Android handler registration(s): "
            f"{android_config.output_root}"
        )

    if args.platform in ("all", "web"):
        web_config = _read_web_config(config, config_root)
        if web_config is None:
            raise ValueError("Missing platforms.web config.")
        web_handlers = generate_web(web_config, messages)
        print(
            f"Generated {len(messages)} message type(s) and "
            f"{len(web_handlers)} Web handler registration(s): "
            f"{web_config.output_root}"
        )

    return 0


def _read_message_scan_path(config: dict, config_root: Path) -> Path:
    common = config.get("common")
    if not isinstance(common, dict):
        raise ValueError("Config field 'common' must be an object.")

    package_message_scan_path = common.get("packageMessageScanPath")
    if not isinstance(package_message_scan_path, str) or not package_message_scan_path:
        raise ValueError(
            "Config field 'common.packageMessageScanPath' must be a non-empty string."
        )

    return _resolve_config_path(package_message_scan_path, config_root)


def _ensure_makefile(config_root: Path, config_path: Path) -> None:
    makefile_path = config_root / "Makefile"
    script_path = Path(__file__).resolve()
    relative_script_path = _make_relative_path(script_path, config_root)
    relative_config_path = _make_relative_path(config_path, config_root)

    block_start = "# >>> zh_native_channel_generator"
    block_end = "# <<< zh_native_channel_generator"
    native_targets = f"""PYTHON ?= python3
ZH_NATIVE_CHANNEL_GENERATOR ?= {relative_script_path}
ZH_NATIVE_CHANNEL_CONFIG ?= {relative_config_path}

.PHONY: gen-build-runner-sync-config gen-build-runner-run gen-create-all gen-create-ios gen-create-android gen-create-web

gen-build-runner-sync-config:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --sync-build-config-only

gen-build-runner-run:
\tflutter pub run build_runner build --delete-conflicting-outputs

gen-create-all:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform all

gen-create-ios:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform ios

gen-create-android:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform android

gen-create-web:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform web
"""
    block = f"""{block_start}
{native_targets}{block_end}
"""
    standalone_makefile = f"""{block_start}
PYTHON ?= python3
ZH_NATIVE_CHANNEL_GENERATOR ?= {relative_script_path}
ZH_NATIVE_CHANNEL_CONFIG ?= {relative_config_path}

.PHONY: gen-build-runner-sync-config gen-build-runner-run gen-create-all gen-create-ios gen-create-android gen-create-web

gen-build-runner-sync-config:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --sync-build-config-only

gen-build-runner-run:
\tflutter pub run build_runner build --delete-conflicting-outputs

gen:
\t$(MAKE) gen-build-runner-sync-config
\t$(MAKE) gen-build-runner-run
\t$(MAKE) gen-create-all

gen-create-all:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform all

gen-create-ios:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform ios

gen-create-android:
\t$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform android

gen-create-web:
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


def _sync_build_yaml(config_root: Path) -> None:
    pubspec_path = config_root / "pubspec.yaml"
    if not pubspec_path.exists():
        return

    dart_config = _read_pubspec_dart_config(pubspec_path)
    if dart_config is None:
        return

    build_yaml_path = config_root / "build.yaml"
    scan_globs = dart_config["scan_globs"]
    options = {
        "method_channel_name": dart_config["method_channel_name"],
        "basePath": dart_config["basePath"],
        "register_path": dart_config["register_path"],
    }

    lines = [
        "targets:",
        "  $default:",
        "    builders:",
        "      source_gen:combining_builder:",
        "        generate_for:",
        "          exclude:",
        "            - lib/base/pigeons/**.dart",
        "      zh_native_channel_generator|channel_register_builder:",
        "        enabled: true",
        "        options:",
        "          scan_globs:",
    ]
    lines.extend(f"            - {item}" for item in scan_globs)
    lines.extend(
        [
            f"          method_channel_name: {options['method_channel_name']}",
            f"          basePath: {options['basePath']}",
            f"          register_path: {options['register_path']}",
            "",
        ]
    )
    build_yaml_path.write_text("\n".join(lines), encoding="utf-8")


def _read_pubspec_dart_config(pubspec_path: Path) -> dict | None:
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
        "method_channel_name": _read_pubspec_string(
            dart_section,
            "method_channel_name",
            "ZHNativeChannel",
        ),
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
    value = section.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"pubspec.yaml zh_native_channel_generator.dart.{key} must be a non-empty string."
        )
    return value.strip()


def _read_yaml_object(lines: list[str], root_key: str) -> dict:
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
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("#"):
            return index
    return None


def _indent_width(value: str) -> int:
    return len(value) - len(value.lstrip(" "))


def _make_relative_path(path: Path, root: Path) -> str:
    return Path(os.path.relpath(path, root)).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
