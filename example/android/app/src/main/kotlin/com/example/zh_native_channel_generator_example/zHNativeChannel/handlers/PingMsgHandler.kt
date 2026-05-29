package com.example.zh_native_channel_generator_example.zHNativeChannel.handlers

import com.example.zh_native_channel.ChannelBaseHandler
import com.example.zh_native_channel.ChannelBaseMsg
import com.example.zh_native_channel.ChannelMsgException
import com.example.zh_native_channel_generator_example.zHNativeChannel.msgs.PingMsg

// PlatformChannelHandler("PingMsg")
class PingMsgHandler : ChannelBaseHandler {
    override fun handle(message: ChannelBaseMsg): ChannelBaseMsg {
        val ping = message as? PingMsg
            ?: throw ChannelMsgException("Expected PingMsg.")
        return PingMsg(text = "android:${ping.text}")
    }
}
