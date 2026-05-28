// ignore_for_file: file_names, depend_on_referenced_packages

import 'package:build/build.dart';
import 'package:glob/glob.dart';

Builder channelRegisterBuilder(BuilderOptions options) =>
    ChannelRegisterBuilder(options);

class ChannelRegisterBuilder implements Builder {
  final List<String> scanGlobs;
  final String methodChannelName;
  final String basePath;
  final String registerPath;

  ChannelRegisterBuilder(BuilderOptions options)
    : scanGlobs = _readScanGlobs(options),
      methodChannelName = _readMethodChannelName(options),
      basePath = _readBasePath(options),
      registerPath = _readRegisterPath(options);

  @override
  Map<String, List<String>> get buildExtensions => {
    r'$lib$': [
      _buildExtensionPath(_registerOutputPath()),
      _buildExtensionPath(_managerOutputPath()),
    ],
  };

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
    final managerOutput = AssetId(
      buildStep.inputId.package,
      _managerOutputPath(),
    );

    await buildStep.writeAsString(
      registerOutput,
      _buildRegisterOutput(messages, handlers),
    );
    await buildStep.writeAsString(
      managerOutput,
      _buildManagerOutput(buildStep.inputId.package),
    );
  }

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

  String _buildRegisterOutput(
    List<_ChannelEntry> messages,
    List<_ChannelEntry> handlers,
  ) {
    final buffer = StringBuffer()
      ..writeln('// GENERATED CODE - DO NOT MODIFY BY HAND')
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
      ..writeln(
        'ZHNativeChannel createGeneratedChannel(String methodChannelName) {',
      )
      ..writeln('  final channel = ZHNativeChannel(methodChannelName);')
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

  String _buildManagerOutput(String packageName) {
    final escapedMethodChannelName = _escapeDartString(methodChannelName);
    return '''
// GENERATED CODE - DO NOT MODIFY BY HAND

// ************************************************************************
// ChannelRegisterBuilder
// ************************************************************************

import 'package:zh_native_channel/zh_native_channel.dart';

class ZHNativeChannelManager {
  static final ZHNativeChannelManager _instance = ZHNativeChannelManager._();

  ZHNativeChannelManager._() {
    channel = ZHNativeChannel('$escapedMethodChannelName');
  }

  Future<ChannelBaseMsg> invoke(ChannelBaseMsg msg) async {
    return channel.invokeMethod(msg);
  }

  static ZHNativeChannelManager get instance => _instance;

  late final ZHNativeChannel channel;
}
''';
  }

  String _registerOutputPath() {
    return _resolveGeneratedPath(registerPath);
  }

  String _managerOutputPath() {
    return _resolveGeneratedPath('ZHNativeChannelManager.g.dart');
  }

  String _buildExtensionPath(String assetPath) {
    return _stripLibPrefix(assetPath);
  }

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

  String _packageImportFor(String packageName, String assetPath) {
    final pathInLib = assetPath.substring('lib/'.length);
    return 'package:$packageName/$pathInLib';
  }

  int _compareEntries(_ChannelEntry left, _ChannelEntry right) {
    final channelCompare = left.channelName.compareTo(right.channelName);
    if (channelCompare != 0) {
      return channelCompare;
    }
    return left.className.compareTo(right.className);
  }
}

List<String> _readScanGlobs(BuilderOptions options) {
  final rawGlobs = options.config['scan_globs'];
  if (rawGlobs is List && rawGlobs.every((item) => item is String)) {
    return rawGlobs.cast<String>();
  }
  return const ['lib/**.dart'];
}

String _readMethodChannelName(BuilderOptions options) {
  final rawName = options.config['method_channel_name'];
  if (rawName is String && rawName.trim().isNotEmpty) {
    return rawName.trim();
  }
  return 'zh_native_channel';
}

String _readBasePath(BuilderOptions options) {
  final rawBasePath = options.config['basePath'] ?? options.config['base_path'];
  if (rawBasePath is String && rawBasePath.trim().isNotEmpty) {
    return rawBasePath.trim();
  }
  return 'lib/base/zHNativeChannel';
}

String _readRegisterPath(BuilderOptions options) {
  final rawRegisterPath = options.config['register_path'];
  if (rawRegisterPath is String && rawRegisterPath.trim().isNotEmpty) {
    return rawRegisterPath.trim();
  }
  return 'ChannelGeneratedRegister.g.dart';
}

String _escapeDartString(String value) {
  return value.replaceAll(r'\', r'\\').replaceAll("'", r"\'");
}

String _normalizePath(String value) {
  return value
      .trim()
      .replaceAll('\\', '/')
      .replaceAll(RegExp(r'/+'), '/')
      .replaceAll(RegExp(r'^/+|/+$'), '');
}

String _ensureLibPrefix(String value) {
  final normalized = _normalizePath(value);
  if (normalized == 'lib' || normalized.startsWith('lib/')) {
    return normalized;
  }
  return 'lib/$normalized';
}

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

class _ChannelEntry {
  final String annotationName;
  final String channelName;
  final String className;
  final String importUri;

  const _ChannelEntry({
    required this.annotationName,
    required this.channelName,
    required this.className,
    required this.importUri,
  });
}
