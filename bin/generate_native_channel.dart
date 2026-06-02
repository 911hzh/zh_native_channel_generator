import 'dart:convert';
import 'dart:io';

/// 通过 Dart executable 暴露原有 Python 生成脚本。
///
/// 宿主项目可以使用 `dart run zh_native_channel_generator:generate_native_channel`
/// 执行生成逻辑，不需要知道 generator 包在本机磁盘上的具体路径。
Future<void> main(List<String> arguments) async {
  final packageRoot = await _resolvePackageRoot('zh_native_channel_generator');
  final scriptPath = packageRoot.uri
      .resolve('scripts/generate_native_channel.py')
      .toFilePath();

  final process = await Process.start('python3', [
    scriptPath,
    ...arguments,
  ], mode: ProcessStartMode.inheritStdio);
  final exitCode = await process.exitCode;
  if (exitCode != 0) {
    exit(exitCode);
  }
}

/// 从当前项目的 package_config.json 中解析 generator 包路径。
///
/// `dart run` 会把 executable 包装到 Pub 缓存目录，不能依赖 `Platform.script`
/// 反推源码位置；package_config 才是宿主项目实际依赖解析后的来源。
Future<Directory> _resolvePackageRoot(String packageName) async {
  final packageConfig = _findPackageConfig(Directory.current);
  final packageConfigJson =
      jsonDecode(await packageConfig.readAsString()) as Map<String, Object?>;
  final packages = packageConfigJson['packages'];
  if (packages is! List<Object?>) {
    throw StateError('Invalid package_config.json: missing packages list.');
  }

  for (final package in packages) {
    if (package is! Map<String, Object?> || package['name'] != packageName) {
      continue;
    }
    final rootUriText = package['rootUri'];
    if (rootUriText is! String || rootUriText.isEmpty) {
      throw StateError('Invalid rootUri for package $packageName.');
    }
    final rootUri = packageConfig.uri.resolve(rootUriText);
    return Directory.fromUri(rootUri);
  }

  throw StateError(
    'Package $packageName not found. Please run `dart pub get` first.',
  );
}

/// 从当前目录向上查找最近的 `.dart_tool/package_config.json`。
File _findPackageConfig(Directory start) {
  var directory = start.absolute;
  while (true) {
    final packageConfig = File.fromUri(
      directory.uri.resolve('.dart_tool/package_config.json'),
    );
    if (packageConfig.existsSync()) {
      return packageConfig;
    }

    final parent = directory.parent;
    if (parent.path == directory.path) {
      throw StateError(
        'Cannot find .dart_tool/package_config.json. Please run `dart pub get` first.',
      );
    }
    directory = parent;
  }
}
