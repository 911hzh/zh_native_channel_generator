// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

import { ChannelBaseMsg, ChannelMap } from '../ChannelBaseMsg';
import { ChannelMsgError } from '../ChannelMsgError';

export class NestedMsg implements ChannelBaseMsg {
  readonly channelName = 'NestedMsg';
  constructor(
    readonly user: unknown,
    readonly users: unknown[],
    readonly userMap: unknown,
    readonly meta: unknown | null
  ) {}

  toMap(): ChannelMap {
    return {
      user: this.user,
      users: this.users,
      userMap: this.userMap,
      meta: this.meta
    };
  }

  static fromMap(map: ChannelMap): NestedMsg {
    const user = ((map['user'] as unknown | null | undefined) ?? (() => { throw new ChannelMsgError('Field user is missing.'); })());
    const users = ((map['users'] as unknown[] | null | undefined) ?? (() => { throw new ChannelMsgError('Field users is missing.'); })());
    const userMap = ((map['userMap'] as unknown | null | undefined) ?? (() => { throw new ChannelMsgError('Field userMap is missing.'); })());
    const meta = map['meta'] == null ? null : (map['meta'] as unknown);
    return new NestedMsg(user, users, userMap, meta);
  }
}
