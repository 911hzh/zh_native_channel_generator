// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

export type ChannelMap = Record<string, unknown>;

export interface ChannelBaseMsg {
  readonly channelName: string;
  toMap(): ChannelMap;
}
