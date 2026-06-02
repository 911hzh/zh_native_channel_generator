# 更新日志

## 0.0.6

- 支持 `@ChannelMsg` 字段引用同文件内的自定义嵌套 model。
- 支持 iOS Swift 和 Android Kotlin 在同一个消息生成文件中生成嵌套 model 类型。
- 支持 iOS Swift 和 Android Kotlin 对嵌套 model、`List<Model>`、`Map<String, Model>` 和可空嵌套 model 的平台侧转换。
- 支持读取 Dart 字段初始化和构造参数默认值，并同步生成 iOS / Android 的缺省解析逻辑。
- 改为调用 `zh_native_channel` runtime 中的公共 Map 解码辅助能力，避免每个消息文件重复生成 helper。
- 增加嵌套 model 生成测试和 example fixture。

## 0.0.5

- 补充最小 `zh_native_channel_config.json` 示例，说明 `dart`、`ios`、`android` 可使用空对象走默认路径。
- 明确平台配置对象可以为空，生成器会使用默认扫描目录和输出目录。
- 说明何时需要显式配置扫描路径、输出路径、Android package 或 iOS Xcode 工程路径。

## 0.0.1

- 首次发布 `zh_native_channel_generator`。
- 支持根据 `@ChannelMsg` 和 `@ChannelHandlerFor` 生成 Dart 注册代码。
- 支持生成 iOS Swift、Android Kotlin 和 Web TypeScript 平台代码。
- 支持通过 `zh_native_channel_config.json` 配置扫描路径和输出路径。
