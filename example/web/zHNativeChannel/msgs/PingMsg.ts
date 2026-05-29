// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

import { ChannelBaseMsg, ChannelMap } from '../ChannelBaseMsg';
import { ChannelMsgError } from '../ChannelMsgError';

export class PingMsg implements ChannelBaseMsg {
  readonly channelName = 'PingMsg';
  constructor(
    readonly text: string
  ) {}

  toMap(): ChannelMap {
    return {
      text: this.text
    };
  }

  static fromMap(map: ChannelMap): PingMsg {
    const text = ((map['text'] as string | null | undefined) ?? (() => { throw new ChannelMsgError('Field text is missing.'); })());
    return new PingMsg(text);
  }
}
