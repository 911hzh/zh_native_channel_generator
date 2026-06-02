// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

package com.example.zh_native_channel_generator_example.zHNativeChannel.msgs

import com.example.zh_native_channel.ChannelBaseMsg
import com.example.zh_native_channel.ChannelMsgException

data class NestedAddress(
    val city: String
) {
    fun toMap(): Map<String, Any?> {
        return mapOf(
            "city" to city
        )
    }

    companion object {
        fun fromMap(map: Map<String, Any?>): NestedAddress {
            return NestedAddress(
                city = map["city"] as? String ?: throw ChannelMsgException("Field city is missing or has invalid type.")
            )
        }
    }
}

data class NestedUser(
    val name: String,
    val age: Int,
    val address: NestedAddress,
    val addresses: List<NestedAddress>
) {
    fun toMap(): Map<String, Any?> {
        return mapOf(
            "name" to name,
            "age" to age,
            "address" to address.toMap(),
            "addresses" to addresses.map { it.toMap() }
        )
    }

    companion object {
        fun fromMap(map: Map<String, Any?>): NestedUser {
            return NestedUser(
                name = map["name"] as? String ?: throw ChannelMsgException("Field name is missing or has invalid type."),
                age = (map["age"] as? Number)?.toInt() ?: throw ChannelMsgException("Field age is missing or has invalid type."),
                address = NestedAddress.fromMap(_requireStringAnyMap(map["address"], "address")),
                addresses = (map["addresses"] as? List<*>)?.map { item -> NestedAddress.fromMap(_requireStringAnyMap(item, "addresses")) } ?: throw ChannelMsgException("Field addresses is missing or has invalid type.")
            )
        }
    }
}

data class NestedMeta(
    val enabled: Boolean
) {
    fun toMap(): Map<String, Any?> {
        return mapOf(
            "enabled" to enabled
        )
    }

    companion object {
        fun fromMap(map: Map<String, Any?>): NestedMeta {
            return NestedMeta(
                enabled = map["enabled"] as? Boolean ?: throw ChannelMsgException("Field enabled is missing or has invalid type.")
            )
        }
    }
}

data class NestedMsg(
    val user: NestedUser,
    val users: List<NestedUser>,
    val userMap: Map<String, NestedUser>,
    val meta: NestedMeta?
) : ChannelBaseMsg {
    override fun toMap(): Map<String, Any?> {
        return mapOf(
            "user" to user.toMap(),
            "users" to users.map { it.toMap() },
            "userMap" to userMap.mapValues { it.value.toMap() },
            "meta" to meta?.toMap()
        )
    }

    companion object {
        fun fromMap(map: Map<String, Any?>): NestedMsg {
            return NestedMsg(
                user = NestedUser.fromMap(_requireStringAnyMap(map["user"], "user")),
                users = (map["users"] as? List<*>)?.map { item -> NestedUser.fromMap(_requireStringAnyMap(item, "users")) } ?: throw ChannelMsgException("Field users is missing or has invalid type."),
                userMap = (map["userMap"] as? Map<*, *>)?.map { entry -> val key = entry.key as? String ?: throw ChannelMsgException("Field userMap is missing or has invalid type."); key to NestedUser.fromMap(_requireStringAnyMap(entry.value, "userMap")) }?.toMap() ?: throw ChannelMsgException("Field userMap is missing or has invalid type."),
                meta = map["meta"]?.let { NestedMeta.fromMap(_requireStringAnyMap(it, "meta")) }
            )
        }
    }
}

private fun _requireStringAnyMap(value: Any?, fieldName: String): Map<String, Any?> {
    val map = value as? Map<*, *>
        ?: throw ChannelMsgException("Field $fieldName is missing or has invalid type.")
    return map.entries.associate { entry ->
        val key = entry.key as? String
            ?: throw ChannelMsgException("Field $fieldName contains a non-string map key.")
        key to entry.value
    }
}
