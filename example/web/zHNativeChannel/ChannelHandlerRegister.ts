// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

import { ChannelBaseHandler } from './ChannelBaseHandler';
import { ChannelMsgError } from './ChannelMsgError';
import { registerGeneratedChannelHandlers } from './GeneratedChannelRegistrations';

export class ChannelHandlerRegister {
  private readonly container = new Map<string, ChannelBaseHandler>();

  constructor() {
    registerGeneratedChannelHandlers(this);
  }

  registerChannel(channelName: string, handler: ChannelBaseHandler): void {
    this.container.set(channelName, handler);
  }

  getChannelHandler(channelName: string): ChannelBaseHandler {
    const handler = this.container.get(channelName);
    if (!handler) {
      throw new ChannelMsgError(`Missing handler: ${channelName}`);
    }
    return handler;
  }
}
