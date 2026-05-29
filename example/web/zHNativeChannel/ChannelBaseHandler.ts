// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

import { ChannelBaseMsg } from './ChannelBaseMsg';

export interface ChannelBaseHandler {
  handle(message: ChannelBaseMsg): ChannelBaseMsg | Promise<ChannelBaseMsg>;
}
