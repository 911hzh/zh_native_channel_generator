import 'package:zh_native_channel/zh_native_channel.dart';

@ChannelMsg()
class NestedMsg extends ChannelBaseMsg {
  String title = 'guest';
  final NestedUser user;
  final List<NestedUser> users;
  final Map<String, NestedUser> userMap;
  final NestedMeta? meta;

  NestedMsg({
    this.title = 'guest',
    required this.user,
    required this.users,
    required this.userMap,
    this.meta,
  });

  static NestedMsg fromMap(Map<String, dynamic> map) {
    return NestedMsg(
      title: map['title'] as String? ?? 'guest',
      user: NestedUser.fromMap(map['user'] as Map<String, dynamic>? ?? {}),
      users: ((map['users'] as List?) ?? [])
          .whereType<Map<String, dynamic>>()
          .map(NestedUser.fromMap)
          .toList(),
      userMap: ((map['userMap'] as Map?) ?? {}).map(
        (key, value) => MapEntry(
          key.toString(),
          NestedUser.fromMap(value as Map<String, dynamic>? ?? {}),
        ),
      ),
      meta: map['meta'] is Map<String, dynamic>
          ? NestedMeta.fromMap(map['meta'] as Map<String, dynamic>)
          : null,
    );
  }

  @override
  Map<String, dynamic> toMap() {
    return {
      'title': title,
      'user': user.toMap(),
      'users': users.map((item) => item.toMap()).toList(),
      'userMap': userMap.map((key, value) => MapEntry(key, value.toMap())),
      'meta': meta?.toMap(),
    };
  }
}

class NestedUser {
  final String name;
  int age = 18;
  final NestedAddress address;
  final List<NestedAddress> addresses;

  NestedUser({
    required this.name,
    this.age = 18,
    required this.address,
    required this.addresses,
  });

  static NestedUser fromMap(Map<String, dynamic> map) {
    return NestedUser(
      name: map['name'] as String? ?? '',
      age: map['age'] as int? ?? 0,
      address: NestedAddress.fromMap(
        map['address'] as Map<String, dynamic>? ?? {},
      ),
      addresses: ((map['addresses'] as List?) ?? [])
          .whereType<Map<String, dynamic>>()
          .map(NestedAddress.fromMap)
          .toList(),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'name': name,
      'age': age,
      'address': address.toMap(),
      'addresses': addresses.map((item) => item.toMap()).toList(),
    };
  }
}

class NestedAddress {
  String city = '';

  NestedAddress({this.city = ''});

  static NestedAddress fromMap(Map<String, dynamic> map) {
    return NestedAddress(city: map['city'] as String? ?? '');
  }

  Map<String, dynamic> toMap() {
    return {'city': city};
  }
}

class NestedMeta {
  final bool enabled;

  NestedMeta({required this.enabled});

  static NestedMeta fromMap(Map<String, dynamic> map) {
    return NestedMeta(enabled: map['enabled'] as bool? ?? false);
  }

  Map<String, dynamic> toMap() {
    return {'enabled': enabled};
  }
}
