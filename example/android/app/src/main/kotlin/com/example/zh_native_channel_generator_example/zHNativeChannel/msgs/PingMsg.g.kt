// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

package com.example.zh_native_channel_generator_example.zHNativeChannel.msgs

import com.example.zh_native_channel.ChannelBaseMsg
import com.example.zh_native_channel.ChannelMsgException

data class PingMsg(
    val text: String
) : ChannelBaseMsg {
    override fun toMap(): Map<String, Any?> {
        return mapOf(
            "text" to text
        )
    }

    companion object {
        fun fromMap(map: Map<String, Any?>): PingMsg {
            return PingMsg(
                text = map["text"] as? String ?: throw ChannelMsgException("Field text is missing or has invalid type.")
            )
        }
    }
}
