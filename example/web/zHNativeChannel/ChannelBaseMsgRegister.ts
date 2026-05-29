// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

import { ChannelBaseMsg, ChannelMap } from './ChannelBaseMsg';
import { ChannelMsgError } from './ChannelMsgError';
import { registerGeneratedChannelMessages } from './GeneratedChannelRegistrations';

export type CreateChannelBaseMsgClosure = (map: ChannelMap) => ChannelBaseMsg;

export class ChannelBaseMsgRegister {
  private readonly channelMap = new Map<string, CreateChannelBaseMsgClosure>();

  constructor() {
    registerGeneratedChannelMessages(this);
  }

  registerChannel(channelName: string, closure: CreateChannelBaseMsgClosure): void {
    this.channelMap.set(channelName, closure);
  }

  getChannel(channelName: string, params: ChannelMap): ChannelBaseMsg {
    const factory = this.channelMap.get(channelName);
    if (!factory) {
      throw new ChannelMsgError(`Missing message factory: ${channelName}`);
    }
    return factory(params);
  }
}
