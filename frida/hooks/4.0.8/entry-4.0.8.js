/*
 * armorx-lab :: ENTRY SCRIPT for BIGBIG WON 4.0.8
 *               (com.moojiang.bigbigwon.mygt, versionCode 409)
 * ---------------------------------------------------------------------------
 * BLE stack:  Flutter plugin  flutter_blue_plus
 *             dex class: com.lib.flutter_blue_plus.FlutterBluePlusPlugin
 *             MethodChannel: flutter_blue_plus/methods
 *             There is NO com.polidea.rxandroidble2 / com.signify.hue.flutterreactiveble
 *             in this build -> it is a genuine stack migration from 2.24.
 *
 * APK: split APK (base.apk + config.arm64_v8a.apk + config.<locale/density>.apk),
 *      shipped as BIGBIGWON-4.0.8.apkm. lib/arm64-v8a ONLY.
 *      -> install with: adb install-multiple base.apk config.arm64_v8a.apk config.en.apk config.xxhdpi.apk
 *
 * RUN (from /home/salamanka/armorx-lab):
 *   frida -U -f com.moojiang.bigbigwon.mygt \
 *     -l frida/hooks/shared/network-http-hooks.js \
 *     -l frida/hooks/shared/bt-platform-hooks.js \
 *     -l frida/hooks/4.0.8/entry-4.0.8.js
 */

'use strict';

if (typeof note !== 'function') { var note = function (m) { console.log('[ARMORX-BT] ### ' + m); }; }
if (typeof emit !== 'function') { var emit = function (o) { console.log('[ARMORX-BT] ' + JSON.stringify(o)); }; }
if (typeof hookAll !== 'function') { var hookAll = function () { return false; }; }

var ENTRY = '4.0.8';

if (typeof Java === 'undefined') {
  note('entry ' + ENTRY + ': Java bridge unavailable in this Frida runtime -> use Frida 16.x');
} else
Java.perform(function () {
  note('entry script ' + ENTRY + ' attaching (flutter_blue_plus)');

  // ---------------------------------------------------------------------
  // A. FlutterBluePlusPlugin.onMethodCall  -> every Dart->platform BLE verb
  // ---------------------------------------------------------------------
  var n = hookAll('com.lib.flutter_blue_plus.FlutterBluePlusPlugin', 'onMethodCall',
    function (self, args) {
      var rec = { api: 'FlutterBluePlusPlugin.onMethodCall', entry: ENTRY };
      try { rec.method = String(args[0].method); } catch (e) { rec.method = '<unknown>'; }
      try {
        var a = args[0].arguments;
        rec.arguments = a === null ? null : String(a);
      } catch (e) {}
      emit(rec);
      return null;
    });
  if (!n) note('MISS com.lib.flutter_blue_plus.FlutterBluePlusPlugin.onMethodCall');

  // ---------------------------------------------------------------------
  // B. flutter_blue_plus channel registration
  // ---------------------------------------------------------------------
  try {
    var MC = Java.use('io.flutter.plugin.common.MethodChannel');
    MC.setMethodCallHandler.overloads.forEach(function (ov) {
      ov.implementation = function () {
        var name = null;
        try { name = String(this.name); } catch (e) { try { name = this.name.value; } catch (e2) {} }
        if (name && name.indexOf('flutter_blue_plus') === 0) {
          emit({ api: 'MethodChannel.setMethodCallHandler', channel: name, entry: ENTRY });
        }
        return ov.apply(this, Array.prototype.slice.call(arguments));
      };
    });
    note('HOOKED MethodChannel.setMethodCallHandler (flutter_blue_plus)');
  } catch (e) { note('channel hook failed: ' + e); }

  // ---------------------------------------------------------------------
  // C. extra: flutter_blue_plus caches scan results; expose its callbacks
  // ---------------------------------------------------------------------
  [
    ['com.lib.flutter_blue_plus.FlutterBluePlusPlugin$1', 'onScanResult'],
    ['com.lib.flutter_blue_plus.FlutterBluePlusPlugin$2', 'onBatchScanResults'],
    ['com.lib.flutter_blue_plus.FlutterBluePlusPlugin$3', 'onScanFailed'],
    ['com.lib.flutter_blue_plus.FlutterBluePlusPlugin$4', 'onConnectionStateChange'],
    ['com.lib.flutter_blue_plus.FlutterBluePlusPlugin$5', 'onCharacteristicChanged']
  ].forEach(function (pair) {
    var k = hookAll(pair[0], pair[1], function (self, args) {
      emit({ api: pair[0] + '.' + pair[1], entry: ENTRY });
      return null;
    });
    if (k) note('HOOKED ' + pair[0] + '.' + pair[1]);
  });

  // D. R8-proof plugin discovery (release build may rename the plugin class)
  if (typeof armorxProbePlugin === 'function') {
    armorxProbePlugin('flutter_blue_plus', [
      'onMethodCall', 'startScan', 'stopScan', 'connect', 'disconnect',
      'discoverServices', 'readCharacteristic', 'writeCharacteristic',
      'setNotifyValue', 'readDescriptor', 'writeDescriptor', 'requestMtu',
      'readRssi', 'setLogLevel', 'getAdapterState'
    ], 2000);
  }

  note('entry script ' + ENTRY + ' ready');
  emit({ api: 'entry-ready', entry: ENTRY, ble_lib: 'flutter_blue_plus' });
});
