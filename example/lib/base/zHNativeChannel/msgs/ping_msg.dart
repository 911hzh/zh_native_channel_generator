import 'package:zh_native_channel/zh_native_channel.dart';

/// 生成器集成测试使用的示例 channel 消息。
@ChannelMsg()
class PingMsg extends ChannelBaseMsg {
  final String text;

  /// 创建携带文本负载的 ping 消息。
  PingMsg({required this.text});

  /// 从 MethodChannel 收到的 map 中还原 ping 消息。
  static PingMsg fromMap(Map<String, dynamic> map) {
    return PingMsg(text: map['text'] as String? ?? '');
  }

  /// 将当前消息序列化为 MethodChannel 负载 map。
  @override
  Map<String, dynamic> toMap() {
    return {'text': text};
  }
}
