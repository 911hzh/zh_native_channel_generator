# 更新日志

## 0.0.5

- 补充最小 `zh_native_channel_config.json` 示例，说明 `dart`、`ios`、`android` 可使用空对象走默认路径。
- 明确平台配置对象可以为空，生成器会使用默认扫描目录和输出目录。
- 说明何时需要显式配置扫描路径、输出路径、Android package 或 iOS Xcode 工程路径。

## 0.0.1

- 首次发布 `zh_native_channel_generator`。
- 支持根据 `@ChannelMsg` 和 `@ChannelHandlerFor` 生成 Dart 注册代码。
- 支持生成 iOS Swift、Android Kotlin 和 Web TypeScript 平台代码。
- 支持通过 `zh_native_channel_config.json` 配置扫描路径和输出路径。
