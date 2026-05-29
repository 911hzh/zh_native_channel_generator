// 自动生成代码，请勿手动修改

// ************************************************************************
// ChannelRegisterBuilder
// ************************************************************************

import 'package:zh_native_channel/zh_native_channel.dart';
import 'package:zh_native_channel_generator_example/base/zHNativeChannel/msgs/ping_msg.dart';

void initializeGeneratedChannels(ZHNativeChannel channel) {
  channel.initializeRegisters((msgRegister, handlerRegister) {
    registerGeneratedChannels(
      msgRegister: msgRegister,
      handlerRegister: handlerRegister,
    );
  });
}

ZHNativeChannel createGeneratedChannel() {
  final channel = ZHNativeChannel.instance;
  initializeGeneratedChannels(channel);
  return channel;
}

void registerGeneratedChannels({
  required ChannelBaseMsgRegister msgRegister,
  required ChannelHandlerRegister handlerRegister,
}) {
  registerGeneratedChannelMessages(msgRegister);
  registerGeneratedChannelHandlers(handlerRegister);
}

void registerGeneratedChannelMessages(ChannelBaseMsgRegister register) {
  register.registerChannel('PingMsg', PingMsg.fromMap);
}

void registerGeneratedChannelHandlers(ChannelHandlerRegister register) {
}
