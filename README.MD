# zh_native_channel_generator

`zh_native_channel_generator` 是配合 `zh_native_channel` 使用的代码生成包，用来减少 Flutter 和原生平台之间 MethodChannel 通信时的重复注册、消息解析和平台胶水代码。

它当前包含两部分生成能力：

- Dart 侧通过 `build_runner` 扫描 `@ChannelMsg` 和 `@ChannelHandlerFor`，生成 Dart 消息注册代码和 `ZHNativeChannelManager`。
- 原生侧通过脚本扫描 Dart 消息定义和原生 `// PlatformChannelHandler("xxx")` 标记，生成 iOS、Android、Web 对应的消息类型、注册代码和运行时辅助代码。

## 能做什么

当前版本支持：

- 扫描 Dart `@ChannelMsg`，生成原生平台可解析的消息 model。
- 扫描 Dart `@ChannelHandlerFor`，生成 Dart 侧 handler 注册代码。
- 扫描原生代码里的 `// PlatformChannelHandler("LocationMsg")`，生成原生 handler 注册代码。
- 生成的原生 `MethodChannelMsgManager` 支持 `invoke`，可以从原生侧主动发送消息到 Dart，并把返回值解析回对应的 `ChannelBaseMsg`。
- 生成 iOS Swift 代码。
- 生成 Android Kotlin 代码。
- 生成 Web TypeScript 代码。
- 通过 JSON 配置各平台的输出目录、handler 扫描目录和 MethodChannel 名称。
- 通过 `Makefile` 拆分执行 Dart build_runner 和原生平台代码生成。

当前字段类型支持范围：

- `String`
- `int`
- `double`
- `num`
- `bool`
- `Map<String, dynamic>`
- `List<...>`

第一版暂不完整支持自定义 model 的递归嵌套生成。如果 `@ChannelMsg` 内部字段使用自定义 class，原生代码生成还需要后续扩展 Dart 解析、平台类型映射和递归序列化逻辑。

## 配置文件

默认配置文件名是：

```bash
zh_native_channel_config.json
```

示例：

```json
{
  "common": {
    "packageMessageScanPath": "lib/base/zHNativeChannel/msgs",
    "methodChannelName": "ZHNativeChannel"
  },
  "platforms": {
    "ios": {
      "handlerScanPath": "ios/Runner/zHNativeChannel/handler_ios",
      "generatedChannelRegistrationsOutputPath": "ios/Runner/zHNativeChannel",
      "outputRoot": "ios/Runner/zHNativeChannel",
      "xcodeProjectPath": "ios/Runner.xcodeproj/project.pbxproj"
    },
    "android": {
      "handlerScanPath": "android/app/src/main/kotlin/com/example/app/zHNativeChannel/handlers",
      "generatedChannelRegistrationsOutputPath": "android/app/src/main/kotlin/com/example/app/zHNativeChannel",
      "outputRoot": "android/app/src/main/kotlin/com/example/app/zHNativeChannel",
      "packageName": "com.example.app.zHNativeChannel"
    },
    "web": {
      "handlerScanPath": "web/zHNativeChannel/handlers",
      "generatedChannelRegistrationsOutputPath": "web/zHNativeChannel",
      "outputRoot": "web/zHNativeChannel",
      "globalName": "ZHNativeChannel"
    }
  }
}
```

说明：

- `common.packageMessageScanPath`：Dart `@ChannelMsg` 消息扫描目录。
- `common.methodChannelName`：MethodChannel 名称，默认是 `ZHNativeChannel`。
- `common.generatedChannelRegistrationsOutputPath`：`GeneratedChannelRegistrations` 注册文件的统一默认输出目录。只有在多个平台确实共用同一个输出目录时才建议配置；一般按平台配置更清晰。
- `platforms.<platform>.handlerScanPath`：原生 handler 扫描目录。没有配置时，会扫描配置文件所在的整个项目目录。
- `platforms.<platform>.outputRoot`：原生生成代码输出目录。
- `platforms.<platform>.generatedChannelRegistrationsOutputPath`：当前平台 `GeneratedChannelRegistrations` 注册文件输出目录。没配置时优先使用 `common.generatedChannelRegistrationsOutputPath`；如果也没配置，则默认输出到 `handlerScanPath` 的父目录。若 `handlerScanPath` 也没配置，则输出到配置文件所在的项目根目录。
- `platforms.android.packageName`：Android 生成代码使用的 Kotlin package。
- `platforms.ios.xcodeProjectPath`：iOS Xcode project 文件路径。不配置时会尝试从输出目录向上查找 `Runner.xcodeproj/project.pbxproj`。
- `platforms.web.globalName`：Web 全局 manager 名称，默认是 `ZHNativeChannel`。

## Dart 侧使用

在 Dart 消息类上标记 `@ChannelMsg`：

```dart
@ChannelMsg('LocationMsg')
class LocationMsg {
  final double latitude;
  final double longitude;

  LocationMsg({
    required this.latitude,
    required this.longitude,
  });
}
```

在 Dart handler 上标记 `@ChannelHandlerFor`：

```dart
@ChannelHandlerFor('LocationMsg')
class LocationHandler extends ChannelBaseHandler<LocationMsg> {
  @override
  Future<ChannelBaseMsg> handle(LocationMsg msg) async {
    return msg;
  }
}
```

运行 Dart 侧生成：

```bash
make build-runner-build
```

这个目标会先同步 `build.yaml`，然后执行：

```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

## 原生侧使用

在原生 handler 类上添加注释标记：

```swift
// PlatformChannelHandler("LocationMsg")
final class LocationMsgHandlers: ChannelBaseHandler {
    // ...
}
```

Android 示例：

```kotlin
// PlatformChannelHandler("LocationMsg")
class LocationMsgHandlers : ChannelBaseHandler {
    // ...
}
```

Web 示例：

```typescript
// PlatformChannelHandler("LocationMsg")
export class LocationMsgHandlers implements ChannelBaseHandler {
  // ...
}
```

生成原生平台代码：

```bash
make create-platformcode-all
```

也可以按平台单独生成：

```bash
make create-platformcode-ios
make create-platformcode-android
make create-platformcode-web
```

## Makefile 命令

当前提供的命令分为两组。

Dart build_runner：

```bash
make build-runner-sync-config
make build-runner-build
```

原生平台代码生成：

```bash
make create-platformcode-all
make create-platformcode-ios
make create-platformcode-android
make create-platformcode-web
```

`build-runner-*` 和 `create-platformcode-*` 是独立流程。外部工程如果已经执行过 build_runner，可以只执行 `create-platformcode-*` 生成原生代码。

## 生成流程建议

常见完整流程：

```bash
make build-runner-build
make create-platformcode-all
```

如果外部工程已经单独执行过 build_runner：

```bash
make create-platformcode-all
```

如果只想更新 Dart build 配置：

```bash
make build-runner-sync-config
```

## 注意事项

- 生成文件属于自动产物，不建议手动修改。
- 原生 handler 的 `PlatformChannelHandler` 标记必须提供 channel name。
- Android handler 文件需要声明 `package`。
- 如果没有配置 `handlerScanPath`，原生 handler 会从整个项目目录扫描，项目较大时建议显式配置扫描目录。
- 当前版本优先覆盖基础消息通信代码生成，复杂嵌套 model 支持后续再扩展。
