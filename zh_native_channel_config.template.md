# zh_native_channel_config 模板

下面是 `zh_native_channel_config.json` 的推荐结构。JSON 模板里不写注释，字段说明放在模板后面。

```json
{
  "dart": {
    "defaultOutputDirectory": "lib/base/zHNativeChannel",
    "messageScanPath": [
      "lib/base/zHNativeChannel/msgs"
    ],
    "handlerScanPath": [
      "lib/base/zHNativeChannel/handlers"
    ],
    "generatedChannelRegisterOutputPath": "lib/base/zHNativeChannel/ChannelGeneratedRegister.g.dart"
  },
  "platforms": {
    "ios": {
      "defaultOutputDirectory": "ios/Runner/zHNativeChannel",
      "scanHandlerPath": [
        "ios/Runner/zHNativeChannel/handler_ios"
      ],
      "msgsOutputPath": "ios/Runner/zHNativeChannel/msgs",
      "generatedChannelRegistrationsOutputPath": "ios/Runner/zHNativeChannel",
      "xcodeProjectPath": "ios/Runner.xcodeproj/project.pbxproj"
    },
    "android": {
      "defaultOutputDirectory": "android/app/src/main/kotlin/com/example/zh_native_channel_example/zHNativeChannel",
      "scanHandlerPath": [
        "android/app/src/main/kotlin/com/example/zh_native_channel_example/zHNativeChannel/handlers"
      ],
      "msgsOutputPath": "android/app/src/main/kotlin/com/example/zh_native_channel_example/zHNativeChannel/msgs",
      "generatedChannelRegistrationsOutputPath": "android/app/src/main/kotlin/com/example/zh_native_channel_example/zHNativeChannel",
      "packageName": "com.example.zh_native_channel_example.zHNativeChannel"
    },
    "web": {
      "defaultOutputDirectory": "web/zHNativeChannel",
      "scanHandlerPath": [
        "web/zHNativeChannel/handlers"
      ],
      "msgsOutputPath": "web/zHNativeChannel/msgs",
      "generatedChannelRegistrationsOutputPath": "web/zHNativeChannel",
      "globalName": "ZHNativeChannel"
    }
  }
}
```

## 字段说明

### dart

- `dart.defaultOutputDirectory`
  - 作用：Dart 注解生成代码的默认输出目录。
  - 是否可不传：可以。
  - 默认值：`lib/base/zHNativeChannel`。

- `dart.messageScanPath`
  - 作用：扫描 Dart `@ChannelMsg` 消息类的位置。Python 原生生成脚本会用它生成 Swift、Kotlin、TypeScript 的 msg 类型；同步 `build.yaml` 时也会把它加入 build_runner 的扫描范围。
  - 类型：字符串或字符串数组。
  - 是否可不传：可以。
  - 默认行为：Python 原生生成脚本默认扫描配置文件所在项目根目录；同步 `build.yaml` 时默认扫描 `lib/**.dart`。

- `dart.handlerScanPath`
  - 作用：扫描 Dart `@ChannelHandlerFor` handler 类的位置。这个字段用于同步 `build.yaml`，让 build_runner 生成 Dart 侧 handler 注册代码。
  - 类型：字符串或字符串数组。
  - 是否可不传：可以。
  - 默认行为：如果 `messageScanPath` 和 `handlerScanPath` 都不传，同步 `build.yaml` 时默认扫描 `lib/**.dart`。

- `dart.generatedChannelRegisterOutputPath`
  - 作用：Dart 侧注册文件输出路径，用于生成 `ChannelGeneratedRegister.g.dart`。
  - 是否可不传：可以。
  - 默认行为：默认输出到 `defaultOutputDirectory/ChannelGeneratedRegister.g.dart`。
  - 说明：脚本会根据这个字段同步 `build.yaml` 里的 `basePath` 和 `register_path`，再由 `build_runner` 生成对应文件。

### iOS

- `platforms.ios.defaultOutputDirectory`
  - 作用：iOS 生成代码的默认根目录。
  - 是否可不传：可以。
  - 默认值：`ios/Runner/zHNativeChannel`。

- `platforms.ios.scanHandlerPath`
  - 作用：iOS 原生 handler 扫描目录。
  - 类型：字符串或字符串数组。
  - 是否可不传：可以。
  - 默认行为：扫描配置文件所在项目根目录。

- `platforms.ios.msgsOutputPath`
  - 作用：iOS msg 文件输出目录，例如 `PingMsg.g.swift`。
  - 是否可不传：可以。
  - 默认行为：输出到 `defaultOutputDirectory/msgs`。

- `platforms.ios.generatedChannelRegistrationsOutputPath`
  - 作用：iOS 注册文件输出目录，用于生成 `GeneratedChannelRegistrations.g.swift`。
  - 是否可不传：可以。
  - 默认行为：输出到 `defaultOutputDirectory`。

- `platforms.ios.xcodeProjectPath`
  - 作用：iOS Xcode 工程文件路径，用于自动把生成的 Swift 文件加入 Runner target。
  - 是否可不传：可以。
  - 默认行为：从 `defaultOutputDirectory` 向上查找 `Runner.xcodeproj/project.pbxproj`。

### Android

- `platforms.android.defaultOutputDirectory`
  - 作用：Android 生成代码的默认根目录。
  - 是否可不传：可以。
  - 默认值：`android/app/src/main/kotlin/com/example/zh_native_channel_example/zHNativeChannel`。

- `platforms.android.scanHandlerPath`
  - 作用：Android Kotlin handler 扫描目录。
  - 类型：字符串或字符串数组。
  - 是否可不传：可以。
  - 默认行为：扫描配置文件所在项目根目录。

- `platforms.android.msgsOutputPath`
  - 作用：Android msg 文件输出目录，例如 `PingMsg.g.kt`。
  - 是否可不传：可以。
  - 默认行为：输出到 `defaultOutputDirectory/msgs`。

- `platforms.android.generatedChannelRegistrationsOutputPath`
  - 作用：Android 注册文件输出目录，用于生成 `GeneratedChannelRegistrations.g.kt`。
  - 是否可不传：可以。
  - 默认行为：输出到 `defaultOutputDirectory`。

- `platforms.android.packageName`
  - 作用：Android 生成 Kotlin 文件使用的 package。
  - 是否可不传：不建议。
  - 默认行为：不做自动推导，建议作为 Android 必填项。

### Web

- `platforms.web.defaultOutputDirectory`
  - 作用：Web 生成代码的默认根目录，Web runtime 文件会输出到这里。
  - 是否可不传：可以。
  - 默认值：`web/zHNativeChannel`。

- `platforms.web.scanHandlerPath`
  - 作用：Web handler 扫描目录，支持 `.ts` 和 `.js`。
  - 类型：字符串或字符串数组。
  - 是否可不传：可以。
  - 默认行为：扫描配置文件所在项目根目录。

- `platforms.web.msgsOutputPath`
  - 作用：Web msg 文件输出目录，例如 `PingMsg.ts`。
  - 是否可不传：可以。
  - 默认行为：输出到 `defaultOutputDirectory/msgs`。

- `platforms.web.generatedChannelRegistrationsOutputPath`
  - 作用：Web 注册文件输出目录，用于生成 `GeneratedChannelRegistrations.ts`。
  - 是否可不传：可以。
  - 默认行为：输出到 `defaultOutputDirectory`。

- `platforms.web.globalName`
  - 作用：Web 端挂到 `globalThis` 上的全局对象名。
  - 是否可不传：可以。
  - 默认值：`ZHNativeChannel`。
