# zh_native_channel_generator

`zh_native_channel_generator` 是配合 `zh_native_channel` 使用的代码生成包，用来减少 Flutter 和原生平台之间 MethodChannel 通信时的重复注册、消息解析和平台胶水代码。

它当前包含两部分生成能力：

- Dart 侧通过 `build_runner` 扫描 `@ChannelMsg` 和 `@ChannelHandlerFor`，生成 Dart 消息注册代码和 `ZHNativeChannelManager`。
- 原生侧通过脚本扫描 Dart 消息定义和原生 `// PlatformChannelHandler("xxx")` 标记，生成到宿主原生项目里的 iOS、Android、Web 消息类型和注册代码；基础运行时代码由 `zh_native_channel` 插件内置。

## 能做什么

当前版本支持：

- 扫描 Dart `@ChannelMsg`，在宿主原生项目的用户配置路径下生成平台可解析的消息 model。
- 扫描 Dart `@ChannelHandlerFor`，生成 Dart 侧 handler 注册代码。
- 扫描原生代码里的 `// PlatformChannelHandler("LocationMsg")`，生成原生 handler 注册代码。
- 插件内置的原生 `MethodChannelMsgManager` 支持 `invoke`，可以从原生侧主动发送消息到 Dart，并把返回值解析回对应的 `ChannelBaseMsg`。
- 生成 iOS Swift 代码。
- 生成 Android Kotlin 代码。
- 生成 Web TypeScript 代码。
- 通过 JSON 配置 Dart 消息扫描目录、各平台动态代码输出目录和 handler 扫描目录；MethodChannel 名称由插件统一维护。
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

最低成本示例：

```json
{
  "dart": {},
  "platforms": {
    "ios": {},
    "android": {},
    "web": {}
  }
}
```

上面的配置会使用默认扫描目录和输出目录。需要自定义目录、Android package、iOS Xcode 工程路径或 Web 全局对象名时，再补充对应字段。

说明：

- `dart.defaultOutputDirectory`：Dart 注解生成代码的默认输出目录，默认是 `lib/base/zHNativeChannel`。
- `dart.messageScanPath`：Dart `@ChannelMsg` 消息扫描目录，支持字符串或数组。Python 原生生成脚本用它生成 Swift、Kotlin、TypeScript 的 msg 类型；同步 `build.yaml` 时也会加入 build_runner 扫描范围。不传时 Python 扫描配置文件所在项目根目录，build_runner 扫描 `lib/**.dart`。
- `dart.handlerScanPath`：Dart `@ChannelHandlerFor` handler 扫描目录，支持字符串或数组，用于同步 `build.yaml`。
- `dart.generatedChannelRegisterOutputPath`：Dart 侧注册文件输出路径，默认输出到 `dart.defaultOutputDirectory/ChannelGeneratedRegister.g.dart`。
- MethodChannel 名称固定由 `zh_native_channel` 插件维护，业务工程不再需要配置。
- `platforms.<platform>.defaultOutputDirectory`：当前平台生成代码的默认根目录。iOS 默认 `ios/Runner/zHNativeChannel`，Android 默认 `android/app/src/main/kotlin/com/example/zh_native_channel_example/zHNativeChannel`，Web 默认 `web/zHNativeChannel`。
- `platforms.<platform>.scanHandlerPath`：原生 handler 扫描目录，支持字符串或数组。没有配置时，会扫描配置文件所在的整个项目目录。
- `platforms.<platform>.msgsOutputPath`：当前平台 msg 文件输出目录。没配置时默认输出到 `defaultOutputDirectory/msgs`。
- `platforms.<platform>.generatedChannelRegistrationsOutputPath`：当前平台 `GeneratedChannelRegistrations` 注册文件输出目录。没配置时默认输出到 `defaultOutputDirectory`。
- `platforms.android.packageName`：Android 生成代码使用的 Kotlin package。
- `platforms.ios.xcodeProjectPath`：iOS Xcode project 文件路径。不配置时会尝试从输出目录向上查找 `Runner.xcodeproj/project.pbxproj`。
- `platforms.web.globalName`：Web 全局 manager 名称，默认是 `ZHNativeChannel`。

所有字段都可以不传；不传时会使用默认路径和默认扫描规则。Android 的 `packageName` 也有默认值，但真实业务工程建议显式配置。

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
import zh_native_channel

// PlatformChannelHandler("LocationMsg")
final class LocationMsgHandlers: ChannelBaseHandler {
    // ...
}
```

Android 示例：

```kotlin
import com.example.zh_native_channel.ChannelBaseHandler

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

`create-platformcode-all` 会生成配置文件里已经声明的平台；如果只声明了 iOS，就只生成 iOS。单独执行某个平台目标时，该平台配置必须存在。

iOS/Android 生成完成后，在业务工程启动阶段调用生成的注册入口，把业务消息和 handler 注入插件内置 manager：

```swift
GeneratedChannelRegistrations.registerAll()
```

```kotlin
GeneratedChannelRegistrations.registerAll()
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
- iOS handler 需要 `import zh_native_channel`，Android handler 需要 import 插件提供的 `ChannelBaseHandler`、`ChannelBaseMsg` 等基础类型。
- iOS/Android 动态 msg 和 `GeneratedChannelRegistrations` 生成在宿主原生项目；插件内只维护基础协议、注册表和 manager。
- 当前版本优先覆盖消息模型和注册代码生成，复杂嵌套 model 支持后续再扩展。
