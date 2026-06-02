// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

package com.example.zh_native_channel_generator_example.zHNativeChannel
import com.example.zh_native_channel.ChannelBaseMsgRegister
import com.example.zh_native_channel.ChannelHandlerRegister
import com.example.zh_native_channel.MethodChannelMsgManager
import com.example.zh_native_channel_generator_example.zHNativeChannel.msgs.NestedMsg
import com.example.zh_native_channel_generator_example.zHNativeChannel.msgs.PingMsg
import com.example.zh_native_channel_generator_example.zHNativeChannel.handlers.PingMsgHandler

object GeneratedChannelRegistrations {
    fun registerAll() {
        MethodChannelMsgManager.registerMessages(::registerMessages)
        MethodChannelMsgManager.registerHandlers(::registerHandlers)
    }

    fun registerMessages(register: ChannelBaseMsgRegister) {
        register.registerChannel("NestedMsg") { NestedMsg.fromMap(it) }
        register.registerChannel("PingMsg") { PingMsg.fromMap(it) }
    }

    fun registerHandlers(register: ChannelHandlerRegister) {
        register.registerChannel("PingMsg", PingMsgHandler())
    }
}
