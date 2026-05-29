import { ChannelBaseHandler } from '../ChannelBaseHandler';
import { ChannelBaseMsg } from '../ChannelBaseMsg';

// PlatformChannelHandler("PingMsg")
export class PingMsgHandler implements ChannelBaseHandler {
  handle(message: ChannelBaseMsg): ChannelBaseMsg {
    return message;
  }
}
