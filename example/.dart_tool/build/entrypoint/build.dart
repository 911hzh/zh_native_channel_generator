// @dart=3.6
// ignore_for_file: type=lint
// build_runner >=2.4.16
import 'dart:io' as _io;
import 'package:build_runner/src/build_plan/builder_factories.dart'
    as _build_runner;
import 'package:build_runner/src/bootstrap/processes.dart' as _build_runner;
import 'package:zh_native_channel_generator/src/builders/ChannelRegisterBuilder.dart'
    as _i1;

final _builderFactories = _build_runner.BuilderFactories(
  {
    'zh_native_channel_generator:channel_register_builder': [
      _i1.channelRegisterBuilder
    ],
  },
  postProcessBuilderFactories: {},
);
void main(List<String> args) async {
  _io.exitCode = await _build_runner.ChildProcess.run(
    args,
    _builderFactories,
  )!;
}
