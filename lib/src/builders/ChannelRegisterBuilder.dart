// ignore_for_file: file_names, depend_on_referenced_packages

import 'package:build/build.dart';
import 'package:glob/glob.dart';

/// 创建用于写入 channel 注册代码的 build_runner Builder。
Builder channelRegisterBuilder(BuilderOptions options) =>
    ChannelRegisterBuilder(options);

/// 扫描带注解的 Dart 类，并生成 channel 注册入口。
class ChannelRegisterBuilder implements Builder {
  final List<String> scanGlobs;
  final String basePath;
  final String registerPath;

  /// 读取用于控制扫描范围和输出位置的 Builder 配置。
  ChannelRegisterBuilder(BuilderOptions options)
    : scanGlobs = _readScanGlobs(options),
      basePath = _readBasePath(options),
      registerPath = _readRegisterPath(options);

  /// 声明从 package lib 根节点生成的单个输出文件。
  @override
  Map<String, List<String>> get buildExtensions => {
    r'$lib$': [_buildExtensionPath(_registerOutputPath())],
  };

  /// 查找所有消息和 handler 注解，并写入注册代码。
  @override
  Future<void> build(BuildStep buildStep) async {
    final messages = <_ChannelEntry>[];
    final handlers = <_ChannelEntry>[];

    for (final scanGlob in scanGlobs) {
      final dartFiles = buildStep.findAssets(Glob(scanGlob));
      await for (final asset in dartFiles) {
        if (asset.path.endsWith('.g.dart')) {
          continue;
        }

        final source = await buildStep.readAsString(asset);
        final importUri = _packageImportFor(
          buildStep.inputId.package,
          asset.path,
        );

        for (final entry in _findAnnotatedClasses(source, importUri)) {
          switch (entry.annotationName) {
            case 'ChannelMsg':
              messages.add(entry);
            case 'ChannelHandlerFor':
              handlers.add(entry);
          }
        }
      }
    }

    messages.sort(_compareEntries);
    handlers.sort(_compareEntries);

    final registerOutput = AssetId(
      buildStep.inputId.package,
      _registerOutputPath(),
    );

    await buildStep.writeAsString(
      registerOutput,
      _buildRegisterOutput(messages, handlers),
    );
  }

  /// 从源码文本中提取 channel 注解，不做 import 解析。
  Iterable<_ChannelEntry> _findAnnotatedClasses(
    String source,
    String importUri,
  ) sync* {
    final annotationPattern = RegExp(
      r"""@(ChannelMsg|ChannelHandlerFor)(?:\s*\(\s*(?:['"]([^'"]+)['"])?\s*\))?"""
      r"""(?:(?:\s*\n\s*@[^\n]+)*)\s*\n\s*class\s+([A-Za-z_]\w*)""",
      multiLine: true,
    );

    for (final match in annotationPattern.allMatches(source)) {
      final annotationName = match.group(1)!;
      final className = match.group(3)!;
      final explicitChannelName = match.group(2);

      if (annotationName == 'ChannelHandlerFor' &&
          explicitChannelName == null) {
        throw StateError(
          '@ChannelHandlerFor on $className must provide a channel name.',
        );
      }

      yield _ChannelEntry(
        annotationName: annotationName,
        channelName: explicitChannelName ?? className,
        className: className,
        importUri: importUri,
      );
    }
  }

  /// 构建用于注册消息和 handler 的 Dart 源码。
  String _buildRegisterOutput(
    List<_ChannelEntry> messages,
    List<_ChannelEntry> handlers,
  ) {
    final buffer = StringBuffer()
      ..writeln('// 自动生成代码，请勿手动修改')
      ..writeln()
      ..writeln(
        '// ************************************************************************',
      )
      ..writeln('// ChannelRegisterBuilder')
      ..writeln(
        '// ************************************************************************',
      )
      ..writeln();

    final imports = {
      'package:zh_native_channel/zh_native_channel.dart',
      ...messages.map((entry) => entry.importUri),
      ...handlers.map((entry) => entry.importUri),
    }.toList()..sort();

    for (final import in imports) {
      buffer.writeln("import '$import';");
    }

    if (imports.isNotEmpty) {
      buffer.writeln();
    }

    buffer
      ..writeln('void initializeGeneratedChannels(ZHNativeChannel channel) {')
      ..writeln(
        '  channel.initializeRegisters((msgRegister, handlerRegister) {',
      )
      ..writeln('    registerGeneratedChannels(')
      ..writeln('      msgRegister: msgRegister,')
      ..writeln('      handlerRegister: handlerRegister,')
      ..writeln('    );')
      ..writeln('  });')
      ..writeln('}')
      ..writeln();

    buffer
      ..writeln('ZHNativeChannel createGeneratedChannel() {')
      ..writeln('  final channel = ZHNativeChannel.instance;')
      ..writeln('  initializeGeneratedChannels(channel);')
      ..writeln('  return channel;')
      ..writeln('}')
      ..writeln();

    buffer
      ..writeln('void registerGeneratedChannels({')
      ..writeln('  required ChannelBaseMsgRegister msgRegister,')
      ..writeln('  required ChannelHandlerRegister handlerRegister,')
      ..writeln('}) {')
      ..writeln('  registerGeneratedChannelMessages(msgRegister);')
      ..writeln('  registerGeneratedChannelHandlers(handlerRegister);')
      ..writeln('}')
      ..writeln();

    buffer.writeln(
      'void registerGeneratedChannelMessages(ChannelBaseMsgRegister register) {',
    );
    for (final message in messages) {
      buffer.writeln(
        "  register.registerChannel('${message.channelName}', ${message.className}.fromMap);",
      );
    }
    buffer
      ..writeln('}')
      ..writeln()
      ..writeln(
        'void registerGeneratedChannelHandlers(ChannelHandlerRegister register) {',
      );
    for (final handler in handlers) {
      buffer.writeln(
        "  register.registerChannel('${handler.channelName}', ${handler.className}());",
      );
    }
    buffer.writeln('}');

    return buffer.toString();
  }

  /// 将配置的注册文件路径解析为 package asset 路径。
  String _registerOutputPath() {
    return _resolveGeneratedPath(registerPath);
  }

  /// 将 package asset 路径转换为 build_extensions 需要的相对路径。
  String _buildExtensionPath(String assetPath) {
    return _stripLibPrefix(assetPath);
  }

  /// 将相对生成路径解析到配置的 lib 基础目录下。
  String _resolveGeneratedPath(String path) {
    final normalizedPath = _normalizePath(path);
    if (normalizedPath == 'lib' || normalizedPath.startsWith('lib/')) {
      return normalizedPath;
    }

    final normalizedBasePath = _normalizePath(basePath);
    if (normalizedBasePath.isEmpty) {
      return _ensureLibPrefix(normalizedPath);
    }
    return _ensureLibPrefix('$normalizedBasePath/$normalizedPath');
  }

  /// 将 lib asset 路径转换为 package import URI。
  String _packageImportFor(String packageName, String assetPath) {
    final pathInLib = assetPath.substring('lib/'.length);
    return 'package:$packageName/$pathInLib';
  }

  /// 按 channel 名和类名排序，保证生成内容稳定。
  int _compareEntries(_ChannelEntry left, _ChannelEntry right) {
    final channelCompare = left.channelName.compareTo(right.channelName);
    if (channelCompare != 0) {
      return channelCompare;
    }
    return left.className.compareTo(right.className);
  }
}

/// 读取 Builder 需要扫描的 channel 注解文件 glob。
List<String> _readScanGlobs(BuilderOptions options) {
  final rawGlobs = options.config['scan_globs'];
  if (rawGlobs is List && rawGlobs.every((item) => item is String)) {
    return rawGlobs.cast<String>();
  }
  return const ['lib/**.dart'];
}

/// 读取生成 Dart 文件使用的基础输出目录。
String _readBasePath(BuilderOptions options) {
  final rawBasePath = options.config['basePath'] ?? options.config['base_path'];
  if (rawBasePath is String && rawBasePath.trim().isNotEmpty) {
    return rawBasePath.trim();
  }
  return 'lib/base/zHNativeChannel';
}

/// 读取生成注册文件的文件名或路径。
String _readRegisterPath(BuilderOptions options) {
  final rawRegisterPath = options.config['register_path'];
  if (rawRegisterPath is String && rawRegisterPath.trim().isNotEmpty) {
    return rawRegisterPath.trim();
  }
  return 'ChannelGeneratedRegister.g.dart';
}

/// 将用户配置路径规范化为使用斜杠分隔的相对路径。
String _normalizePath(String value) {
  return value
      .trim()
      .replaceAll('\\', '/')
      .replaceAll(RegExp(r'/+'), '/')
      .replaceAll(RegExp(r'^/+|/+$'), '');
}

/// 确保 asset 路径以 `lib` 为根目录。
String _ensureLibPrefix(String value) {
  final normalized = _normalizePath(value);
  if (normalized == 'lib' || normalized.startsWith('lib/')) {
    return normalized;
  }
  return 'lib/$normalized';
}

/// 移除 `lib/` 前缀，用于声明 build extension。
String _stripLibPrefix(String value) {
  final normalized = _normalizePath(value);
  if (normalized == 'lib') {
    return '';
  }
  if (normalized.startsWith('lib/')) {
    return normalized.substring('lib/'.length);
  }
  return normalized;
}

/// 描述一个需要写入注册代码的注解类。
class _ChannelEntry {
  final String annotationName;
  final String channelName;
  final String className;
  final String importUri;

  /// 创建用于生成输出的不可变注册条目。
  const _ChannelEntry({
    required this.annotationName,
    required this.channelName,
    required this.className,
    required this.importUri,
  });
}
