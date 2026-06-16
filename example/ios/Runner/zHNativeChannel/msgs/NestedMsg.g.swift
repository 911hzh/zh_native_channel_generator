// 自动生成代码，请勿手动修改
// 由 zh_native_channel_generator/scripts/generate_native_channel.py 生成

import Foundation
import zh_native_channel

struct NestedAddress: Codable {
    let city: String
}

struct NestedUser: Codable {
    let name: String
    let age: Int
    let address: NestedAddress
    let addresses: [NestedAddress]
}

struct NestedMeta: Codable {
    let enabled: Bool
}

struct NestedMsg: Codable, ChannelBaseMsg {
    let user: NestedUser
    let users: [NestedUser]
    let userMap: [String: NestedUser]
    let meta: NestedMeta?
}
