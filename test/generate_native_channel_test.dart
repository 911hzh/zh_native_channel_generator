import 'dart:convert';
import 'dart:io';

import 'package:test/test.dart';

/// 针对 example fixture 工程运行集成式生成测试。
void main() {
  final repositoryRoot = Directory.current.absolute;
  final generatorScript = File(
    '${repositoryRoot.path}/scripts/generate_native_channel.py',
  );
  final fixtureRoot = Directory('${repositoryRoot.path}/example');

  // 验证重新生成前会先清理旧产物。
  test('generates native files after deleting previous outputs', () async {
    _logStep('复制 example fixture 到临时沙盒');
    final sandbox = await _copyFixtureToTemp(fixtureRoot);
    addTearDown(() {
      if (sandbox.existsSync()) {
        sandbox.deleteSync(recursive: true);
      }
    });

    final staleIosMessage = File(
      '${sandbox.path}/ios/Runner/zHNativeChannel/msgs/PingMsg.g.swift',
    );
    final staleAndroidMessage = File(
      '${sandbox.path}/android/app/src/main/kotlin/com/example/'
      'zh_native_channel_generator_example/zHNativeChannel/msgs/PingMsg.g.kt',
    );
    final staleWebMessage = File(
      '${sandbox.path}/web/zHNativeChannel/msgs/PingMsg.ts',
    );
    _logStep('写入 iOS、Android 和 Web 旧产物，模拟需要被清理的生成文件');
    staleIosMessage.createSync(recursive: true);
    staleIosMessage.writeAsStringSync('stale ios');
    staleAndroidMessage.createSync(recursive: true);
    staleAndroidMessage.writeAsStringSync('stale android');
    staleWebMessage.createSync(recursive: true);
    staleWebMessage.writeAsStringSync('stale web');

    _logStep('删除默认生成目录，确认旧产物已经被移除');
    _deleteDefaultGeneratedOutputs(sandbox);

    expect(staleIosMessage.existsSync(), isFalse);
    expect(staleAndroidMessage.existsSync(), isFalse);
    expect(staleWebMessage.existsSync(), isFalse);

    _logStep('执行 Python 生成脚本，生成所有平台代码');
    final result = await Process.run('python3', [
      generatorScript.path,
      '${sandbox.path}/zh_native_channel_config.json',
      '--platform',
      'all',
    ]);

    expect(result.exitCode, 0, reason: '${result.stdout}\n${result.stderr}');

    _logStep('校验 iOS、Android 和 Web 消息文件、注册文件内容');
    final iosMessage = File(
      '${sandbox.path}/ios/Runner/zHNativeChannel/msgs/PingMsg.g.swift',
    );
    final iosRegister = File(
      '${sandbox.path}/ios/Runner/zHNativeChannel/GeneratedChannelRegistrations.g.swift',
    );
    final androidMessage = File(
      '${sandbox.path}/android/app/src/main/kotlin/com/example/'
      'zh_native_channel_generator_example/zHNativeChannel/msgs/PingMsg.g.kt',
    );
    final androidRegister = File(
      '${sandbox.path}/android/app/src/main/kotlin/com/example/'
      'zh_native_channel_generator_example/zHNativeChannel/GeneratedChannelRegistrations.g.kt',
    );
    final webMessage = File(
      '${sandbox.path}/web/zHNativeChannel/msgs/PingMsg.ts',
    );
    final webRegister = File(
      '${sandbox.path}/web/zHNativeChannel/GeneratedChannelRegistrations.ts',
    );

    final iosMessageSource = iosMessage.readAsStringSync();
    final androidMessageSource = androidMessage.readAsStringSync();
    expect(iosMessageSource, contains('struct PingMsg'));
    expect(iosMessageSource, isNot(contains('channelName')));
    expect(iosRegister.readAsStringSync(), contains('PingMsgHandler()'));
    expect(androidMessageSource, contains('data class PingMsg'));
    expect(androidMessageSource, isNot(contains('channelName')));
    expect(androidRegister.readAsStringSync(), contains('PingMsgHandler()'));
    expect(webMessage.readAsStringSync(), contains('export class PingMsg'));
    expect(webRegister.readAsStringSync(), contains('new PingMsgHandler()'));
  });

  // 验证平台级配置可以覆盖默认输出目录。
  test('respects custom output paths from config', () async {
    _logStep('复制 example fixture 到临时沙盒');
    final sandbox = await _copyFixtureToTemp(fixtureRoot);
    addTearDown(() {
      if (sandbox.existsSync()) {
        sandbox.deleteSync(recursive: true);
      }
    });

    final configFile = File('${sandbox.path}/custom_config.json');
    _logStep('写入自定义配置，覆盖 iOS、Android 和 Web 的输出路径');
    configFile.writeAsStringSync(
      jsonEncode({
        'dart': {
          'messageScanPath': ['${sandbox.path}/lib/base/zHNativeChannel/msgs'],
        },
        'platforms': {
          'ios': {
            'scanHandlerPath': [
              '${sandbox.path}/ios/Runner/zHNativeChannel/handler_ios',
            ],
            'defaultOutputDirectory': '${sandbox.path}/custom/iosGenerated',
            'msgsOutputPath': '${sandbox.path}/custom/iosMessages',
            'generatedChannelRegistrationsOutputPath':
                '${sandbox.path}/custom/iosRegistrations',
          },
          'android': {
            'scanHandlerPath': [
              '${sandbox.path}/android/app/src/main/kotlin/com/example/zh_native_channel_generator_example/zHNativeChannel/handlers',
            ],
            'defaultOutputDirectory': '${sandbox.path}/custom/androidGenerated',
            'msgsOutputPath': '${sandbox.path}/custom/androidMessages',
            'generatedChannelRegistrationsOutputPath':
                '${sandbox.path}/custom/androidRegistrations',
            'packageName': 'com.example.custom.channel',
          },
          'web': {
            'scanHandlerPath': ['${sandbox.path}/web/zHNativeChannel/handlers'],
            'defaultOutputDirectory': '${sandbox.path}/custom/webRuntime',
            'msgsOutputPath': '${sandbox.path}/custom/webMessages',
            'generatedChannelRegistrationsOutputPath':
                '${sandbox.path}/custom/webRegistrations',
            'globalName': 'ZHNativeChannel',
          },
        },
      }),
    );

    _logStep('使用自定义配置执行所有平台生成');
    final result = await Process.run('python3', [
      generatorScript.path,
      configFile.path,
      '--platform',
      'all',
    ]);

    expect(result.exitCode, 0, reason: '${result.stdout}\n${result.stderr}');

    _logStep('校验生成文件落在自定义目录，并使用自定义 Android package');
    final iosMessage = File(
      '${sandbox.path}/custom/iosMessages/PingMsg.g.swift',
    );
    final iosRegister = File(
      '${sandbox.path}/custom/iosRegistrations/GeneratedChannelRegistrations.g.swift',
    );
    final androidMessage = File(
      '${sandbox.path}/custom/androidMessages/PingMsg.g.kt',
    );
    final androidRegister = File(
      '${sandbox.path}/custom/androidRegistrations/GeneratedChannelRegistrations.g.kt',
    );
    final webMessage = File('${sandbox.path}/custom/webMessages/PingMsg.ts');
    final webRegister = File(
      '${sandbox.path}/custom/webRegistrations/GeneratedChannelRegistrations.ts',
    );

    expect(iosMessage.existsSync(), isTrue);
    expect(iosRegister.existsSync(), isTrue);
    expect(androidMessage.existsSync(), isTrue);
    expect(androidRegister.existsSync(), isTrue);
    expect(webMessage.existsSync(), isTrue);
    expect(webRegister.existsSync(), isTrue);
    expect(
      androidMessage.readAsStringSync(),
      contains('package com.example.custom.channel.msgs'),
    );
  });

  // 验证清理命令会读取 Dart 配置，而不是删除固定路径。
  test('clean generated deletes configured Dart register file', () async {
    _logStep('复制 example fixture 到临时沙盒');
    final sandbox = await _copyFixtureToTemp(fixtureRoot);
    addTearDown(() {
      if (sandbox.existsSync()) {
        sandbox.deleteSync(recursive: true);
      }
    });

    final configuredRegister = File(
      '${sandbox.path}/custom/dart/CustomChannelRegister.g.dart',
    );
    final defaultRegister = File(
      '${sandbox.path}/lib/base/zHNativeChannel/ChannelGeneratedRegister.g.dart',
    );
    configuredRegister.createSync(recursive: true);
    configuredRegister.writeAsStringSync('configured generated file');
    defaultRegister.createSync(recursive: true);
    defaultRegister.writeAsStringSync('default generated file');

    final configFile = File('${sandbox.path}/custom_dart_clean_config.json');
    _logStep('写入自定义 Dart 注册文件输出路径');
    configFile.writeAsStringSync(
      jsonEncode({
        'dart': {
          'messageScanPath': ['${sandbox.path}/lib/base/zHNativeChannel/msgs'],
          'generatedChannelRegisterOutputPath': configuredRegister.path,
        },
      }),
    );

    _logStep('只执行清理命令，验证删除配置路径');
    final result = await Process.run('python3', [
      generatorScript.path,
      configFile.path,
      '--clean-generated-only',
    ]);

    expect(result.exitCode, 0, reason: '${result.stdout}\n${result.stderr}');
    expect(configuredRegister.existsSync(), isFalse);
    expect(defaultRegister.existsSync(), isTrue);
  });

  // 验证清理命令会同时删除 iOS、Android 和 Web 的生成产物。
  test('clean generated deletes native generated outputs', () async {
    _logStep('复制 example fixture 到临时沙盒');
    final sandbox = await _copyFixtureToTemp(fixtureRoot);
    addTearDown(() {
      if (sandbox.existsSync()) {
        sandbox.deleteSync(recursive: true);
      }
    });

    final iosMessage = Directory(
      '${sandbox.path}/ios/Runner/zHNativeChannel/msgs',
    );
    final iosGeneratedMessage = File('${iosMessage.path}/PingMsg.g.swift');
    final iosHandwrittenMessage = File('${iosMessage.path}/Handwritten.swift');
    final iosRegister = File(
      '${sandbox.path}/ios/Runner/zHNativeChannel/GeneratedChannelRegistrations.g.swift',
    );
    final androidMessage = Directory(
      '${sandbox.path}/android/app/src/main/kotlin/com/example/'
      'zh_native_channel_generator_example/zHNativeChannel/msgs',
    );
    final androidGeneratedMessage = File('${androidMessage.path}/PingMsg.g.kt');
    final androidHandwrittenMessage = File(
      '${androidMessage.path}/Handwritten.kt',
    );
    final androidRegister = File(
      '${sandbox.path}/android/app/src/main/kotlin/com/example/'
      'zh_native_channel_generator_example/zHNativeChannel/GeneratedChannelRegistrations.g.kt',
    );
    final webMessage = Directory('${sandbox.path}/web/zHNativeChannel/msgs');
    final webGeneratedMessage = File('${webMessage.path}/PingMsg.ts');
    final webRegister = File(
      '${sandbox.path}/web/zHNativeChannel/GeneratedChannelRegistrations.ts',
    );
    final webRuntime = File('${sandbox.path}/web/zHNativeChannel/index.ts');

    _logStep('写入 iOS、Android 和 Web 生成产物，模拟待清理文件');
    iosMessage.createSync(recursive: true);
    iosGeneratedMessage.writeAsStringSync('stale ios');
    iosHandwrittenMessage.writeAsStringSync('handwritten ios');
    iosRegister.createSync(recursive: true);
    iosRegister.writeAsStringSync('stale ios register');
    androidMessage.createSync(recursive: true);
    androidGeneratedMessage.writeAsStringSync('stale android');
    androidHandwrittenMessage.writeAsStringSync('handwritten android');
    androidRegister.createSync(recursive: true);
    androidRegister.writeAsStringSync('stale android register');
    webMessage.createSync(recursive: true);
    webGeneratedMessage.writeAsStringSync('stale web');
    webRegister.createSync(recursive: true);
    webRegister.writeAsStringSync('stale web register');
    webRuntime.createSync(recursive: true);
    webRuntime.writeAsStringSync('stale web runtime');

    _logStep('只执行清理命令，验证原生生成产物被删除');
    final result = await Process.run('python3', [
      generatorScript.path,
      '${sandbox.path}/zh_native_channel_config.json',
      '--clean-generated-only',
    ]);

    expect(result.exitCode, 0, reason: '${result.stdout}\n${result.stderr}');
    expect(iosMessage.existsSync(), isTrue);
    expect(iosGeneratedMessage.existsSync(), isFalse);
    expect(iosHandwrittenMessage.existsSync(), isTrue);
    expect(iosRegister.existsSync(), isFalse);
    expect(androidMessage.existsSync(), isTrue);
    expect(androidGeneratedMessage.existsSync(), isFalse);
    expect(androidHandwrittenMessage.existsSync(), isTrue);
    expect(androidRegister.existsSync(), isFalse);
    expect(webMessage.existsSync(), isTrue);
    expect(webGeneratedMessage.existsSync(), isFalse);
    expect(webRegister.existsSync(), isFalse);
    expect(webRuntime.existsSync(), isFalse);
  });

  // 验证最小配置可以全部走默认路径和默认扫描规则。
  test('minimal config uses default paths and project-wide scans', () async {
    _logStep('复制 example fixture 到临时沙盒');
    final sandbox = await _copyFixtureToTemp(fixtureRoot);
    addTearDown(() {
      if (sandbox.existsSync()) {
        sandbox.deleteSync(recursive: true);
      }
    });

    _logStep('清理默认生成产物，准备验证最小配置的默认输出路径');
    _deleteDefaultGeneratedOutputs(sandbox);

    final minimalConfigFile = File('${sandbox.path}/minimal_config.json');
    _logStep('写入只声明平台开关的最小配置');
    minimalConfigFile.writeAsStringSync(
      jsonEncode({
        'platforms': {
          'ios': <String, Object?>{},
          'android': <String, Object?>{},
          'web': <String, Object?>{},
        },
      }),
    );

    _logStep('使用最小配置执行所有平台生成');
    final result = await Process.run('python3', [
      generatorScript.path,
      minimalConfigFile.path,
      '--platform',
      'all',
    ]);

    expect(result.exitCode, 0, reason: '${result.stdout}\n${result.stderr}');

    _logStep('校验默认路径已生成消息文件和注册文件');
    expect(
      File(
        '${sandbox.path}/ios/Runner/zHNativeChannel/msgs/PingMsg.g.swift',
      ).existsSync(),
      isTrue,
    );
    final androidMessage = File(
      '${sandbox.path}/android/app/src/main/kotlin/com/example/'
      'zh_native_channel_example/zHNativeChannel/msgs/PingMsg.g.kt',
    );
    expect(androidMessage.existsSync(), isTrue);
    expect(
      androidMessage.readAsStringSync(),
      contains(
        'package com.example.zh_native_channel_example.zHNativeChannel.msgs',
      ),
    );
    expect(
      File('${sandbox.path}/web/zHNativeChannel/msgs/PingMsg.ts').existsSync(),
      isTrue,
    );
  });

  // 验证 handler 扫描路径支持数组，并且可以从多个目录注册 handler。
  test('supports multiple handler scan paths', () async {
    _logStep('复制 example fixture 到临时沙盒');
    final sandbox = await _copyFixtureToTemp(fixtureRoot);
    addTearDown(() {
      if (sandbox.existsSync()) {
        sandbox.deleteSync(recursive: true);
      }
    });

    _logStep('复制 iOS handler 到额外目录，模拟多个 handler 扫描路径');
    final extraIosHandler = File(
      '${sandbox.path}/ios/Runner/ExtraHandlers/ExtraPingMsgHandler.swift',
    );
    extraIosHandler.createSync(recursive: true);
    extraIosHandler.writeAsStringSync(
      File(
        '${sandbox.path}/ios/Runner/zHNativeChannel/handler_ios/PingMsgHandler.swift',
      ).readAsStringSync().replaceAll('PingMsgHandler', 'ExtraPingMsgHandler'),
    );

    final configFile = File('${sandbox.path}/multi_scan_config.json');
    _logStep('写入 iOS 多 scanHandlerPath 配置');
    configFile.writeAsStringSync(
      jsonEncode({
        'dart': {
          'messageScanPath': ['${sandbox.path}/lib/base/zHNativeChannel/msgs'],
        },
        'platforms': {
          'ios': {
            'defaultOutputDirectory':
                '${sandbox.path}/ios/Runner/zHNativeChannel',
            'scanHandlerPath': [
              '${sandbox.path}/ios/Runner/zHNativeChannel/handler_ios',
              '${sandbox.path}/ios/Runner/ExtraHandlers',
            ],
            'msgsOutputPath': '${sandbox.path}/ios/Runner/zHNativeChannel/msgs',
            'generatedChannelRegistrationsOutputPath':
                '${sandbox.path}/ios/Runner/zHNativeChannel',
          },
        },
      }),
    );

    _logStep('只执行 iOS 生成，验证两个扫描目录都会参与注册');
    final result = await Process.run('python3', [
      generatorScript.path,
      configFile.path,
      '--platform',
      'ios',
    ]);

    expect(result.exitCode, 0, reason: '${result.stdout}\n${result.stderr}');

    _logStep('校验注册文件包含两个 handler');
    final iosRegister = File(
      '${sandbox.path}/ios/Runner/zHNativeChannel/GeneratedChannelRegistrations.g.swift',
    ).readAsStringSync();
    expect(iosRegister, contains('PingMsgHandler()'));
    expect(iosRegister, contains('ExtraPingMsgHandler()'));
  });

  // 验证只生成单个平台时不会写入其他平台产物。
  test('single-platform generation only writes that platform', () async {
    _logStep('复制 example fixture 到临时沙盒');
    final sandbox = await _copyFixtureToTemp(fixtureRoot);
    addTearDown(() {
      if (sandbox.existsSync()) {
        sandbox.deleteSync(recursive: true);
      }
    });

    _logStep('清理沙盒中的默认生成产物，避免 fixture 已有文件影响单平台断言');
    _deleteDefaultGeneratedOutputs(sandbox);

    _logStep('只执行 iOS 平台生成');
    final result = await Process.run('python3', [
      generatorScript.path,
      '${sandbox.path}/zh_native_channel_config.json',
      '--platform',
      'ios',
    ]);

    expect(result.exitCode, 0, reason: '${result.stdout}\n${result.stderr}');
    _logStep('校验 iOS 文件已生成，Android 文件未生成');
    expect(
      File(
        '${sandbox.path}/ios/Runner/zHNativeChannel/msgs/PingMsg.g.swift',
      ).existsSync(),
      isTrue,
    );
    expect(
      File(
        '${sandbox.path}/android/app/src/main/kotlin/com/example/'
        'zh_native_channel_generator_example/zHNativeChannel/msgs/PingMsg.g.kt',
      ).existsSync(),
      isFalse,
    );
  });
}

/// 将 example fixture 复制到临时沙盒，避免测试修改源码目录。
Future<Directory> _copyFixtureToTemp(Directory fixtureRoot) async {
  final sandbox = await Directory.systemTemp.createTemp(
    'zh_native_channel_generator_test_',
  );
  await _copyDirectory(fixtureRoot, sandbox);
  return sandbox;
}

/// 递归复制目录树，并保留相对文件名。
Future<void> _copyDirectory(Directory source, Directory target) async {
  await for (final entity in source.list(recursive: false)) {
    final name = entity.path.split(Platform.pathSeparator).last;
    final targetPath = '${target.path}/$name';
    if (entity is Directory) {
      final childTarget = Directory(targetPath)..createSync(recursive: true);
      await _copyDirectory(entity, childTarget);
    } else if (entity is File) {
      await entity.copy(targetPath);
    }
  }
}

/// 删除默认生成产物，便于测试断言重新生成行为。
void _deleteDefaultGeneratedOutputs(Directory root) {
  final paths = [
    '${root.path}/ios/Runner/zHNativeChannel/msgs',
    '${root.path}/ios/Runner/zHNativeChannel/GeneratedChannelRegistrations.g.swift',
    '${root.path}/android/app/src/main/kotlin/com/example/'
        'zh_native_channel_generator_example/zHNativeChannel/msgs',
    '${root.path}/android/app/src/main/kotlin/com/example/'
        'zh_native_channel_generator_example/zHNativeChannel/GeneratedChannelRegistrations.g.kt',
    '${root.path}/web/zHNativeChannel/msgs',
    '${root.path}/web/zHNativeChannel/GeneratedChannelRegistrations.ts',
  ];

  for (final path in paths) {
    final type = FileSystemEntity.typeSync(path);
    if (type == FileSystemEntityType.directory) {
      Directory(path).deleteSync(recursive: true);
    } else if (type == FileSystemEntityType.file) {
      File(path).deleteSync();
    }
  }
}

/// 输出测试步骤日志，方便观察每一步正在验证什么。
void _logStep(String message) {
  // ignore: avoid_print
  print('[测试步骤] $message');
}
