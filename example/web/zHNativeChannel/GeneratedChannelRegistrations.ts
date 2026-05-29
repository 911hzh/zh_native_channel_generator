// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

import { ChannelBaseMsgRegister } from './ChannelBaseMsgRegister';
import { ChannelHandlerRegister } from './ChannelHandlerRegister';
import { PingMsg } from './msgs/PingMsg';
import { PingMsgHandler } from './handlers/PingMsgHandler';

export function registerGeneratedChannelMessages(register: ChannelBaseMsgRegister): void {
  register.registerChannel('PingMsg', (map) => PingMsg.fromMap(map));
}

export function registerGeneratedChannelHandlers(register: ChannelHandlerRegister): void {
  register.registerChannel('PingMsg', new PingMsgHandler());
}
