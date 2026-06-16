// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

import Foundation
import zh_native_channel

enum GeneratedChannelRegistrations {
    static func registerAll() {
        MethodChannelMsgManager.shared.registerMessages(registerMessages)
        MethodChannelMsgManager.shared.registerHandlers(registerHandlers)
    }

    static func registerMessages(_ register: ChannelBaseMsgRegister) {
        register.registerChannel("NestedMsg") { try NestedMsg(map: $0) }
        register.registerChannel("PingMsg") { try PingMsg(map: $0) }
    }

    static func registerHandlers(_ register: ChannelHandlerRegister) {
        register.registerChannel("PingMsg", handler: PingMsgHandler())
    }
}
