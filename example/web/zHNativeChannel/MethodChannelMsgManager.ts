// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

import { ChannelBaseMsgRegister } from './ChannelBaseMsgRegister';
import { ChannelHandlerRegister } from './ChannelHandlerRegister';
import { ChannelBaseMsg, ChannelMap } from './ChannelBaseMsg';

export class MethodChannelMsgManager {
  readonly channelName = 'zh_native_channel';

  constructor(
    private readonly msgRegister = new ChannelBaseMsgRegister(),
    private readonly handlerRegister = new ChannelHandlerRegister(),
  ) {}

  async invoke(message: ChannelBaseMsg): Promise<ChannelBaseMsg> {
    const methodName = message.channelName;
    const params = { ...message.toMap(), '@:': methodName };
    const result = await this.handle(methodName, params);
    return this.msgRegister.getChannel(methodName, result);
  }

  async handle(method: string, params: ChannelMap = {}): Promise<ChannelMap> {
    const channelName = typeof params['@:'] === 'string' ? params['@:'] : method;
    const message = this.msgRegister.getChannel(channelName, params);
    const handler = this.handlerRegister.getChannelHandler(channelName);
    const response = await handler.handle(message);
    return { ...response.toMap(), '@:': channelName };
  }
}

export function registerWebChannelBridge(globalName = 'ZHNativeChannel'): MethodChannelMsgManager {
  const manager = new MethodChannelMsgManager();
  const target = globalThis as typeof globalThis & Record<string, unknown>;
  target[globalName] = manager;
  return manager;
}
