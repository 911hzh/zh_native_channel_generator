import Foundation
import zh_native_channel

// PlatformChannelHandler("PingMsg")
final class PingMsgHandler: ChannelBaseHandler {
  func handle(_ message: ChannelBaseMsg) async throws -> ChannelBaseMsg {
    guard let ping = message as? PingMsg else {
      throw ChannelMsgError.typeMismatch(expected: "PingMsg")
    }
    return PingMsg(text: "ios:\(ping.text)")
  }
}
