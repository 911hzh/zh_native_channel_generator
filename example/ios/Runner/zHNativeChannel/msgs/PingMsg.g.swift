// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

import Foundation
import zh_native_channel

struct PingMsg: Codable, ChannelBaseMsg {
    let text: String
}
