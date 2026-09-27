/*
 * armorx-lab :: ENTRY SCRIPT for BIGBIG WON 2.24 (com.moojiang.bigbigwon, versionCode 24)
 * ---------------------------------------------------------------------------
 * BLE stack:  Flutter plugin  flutter_reactive_ble
 *             (dex package com.signify.hue.flutterreactiveble) over
 *             RxAndroidBle 2 (com.polidea.rxandroidble2).
 * MethodChannels: flutter_reactive_ble_method / _scan / _status
 *   NOTE: dex string scan of 2.24 also contains the literal "flutter_blue_plus/methods"
 *         but NO com.lib.flutter_blue_plus.* classes are present -> 2.24 still uses
 *         flutter_reactive_ble at runtime; the stray string is a leftover/dependency
 *         artefact. (Verified with `unzip -p base.apk classes*.dex | strings`.)
 *
 * APK ABI: arm64-v8a ONLY. See ../README.md and results/final/avd-frida-readiness.md
 *          for the dynamic-run limitations of this build.
 *
 * RUN (from /home/salamanka/armorx-lab):
 *   frida -U -f com.moojiang.bigbigwon \
 *     -l frida/hooks/shared/bt-platform-hooks.js \
 *     -l frida/hooks/2.24/entry-2.24.js
 */

'use strict';

if (typeof note !== 'function') { var note = function (m) { console.log('[ARMORX-BT] ### ' + m); }; }
if (typeof emit !== 'function') { var emit = function (o) { console.log('[ARMORX-BT] ' + JSON.stringify(o)); }; }
if (typeof hookAll !== 'function') { var hookAll = function () { return false; }; }

var ENTRY = '2.24';

if (typeof Java === 'undefined') {
  note('entry ' + ENTRY + ': Java bridge unavailable in this Frida runtime -> use Frida 16.x');
} else
Java.perform(function () {
  note('entry script ' + ENTRY + ' attaching (flutter_reactive_ble + RxAndroidBle2)');

  // A. reactive_ble channels
  try {
    var MC = Java.use('io.flutter.plugin.common.MethodChannel');
    MC.setMethodCallHandler.overloads.forEach(function (ov) {
      ov.implementation = function () {
        var name = null;
        try { name = String(this.name); } catch (e) { try { name = this.name.value; } catch (e2) {} }
        if (name && name.indexOf('flutter_reactive_ble') === 0) {
          emit({ api: 'MethodChannel.setMethodCallHandler', channel: name, entry: ENTRY });
        }
        return ov.apply(this, Array.prototype.slice.call(arguments));
      };
    });
    note('HOOKED MethodChannel.setMethodCallHandler');
  } catch (e) { note('channel hook failed: ' + e); }

  // B. RxAndroidBle2 semantic layer
  [
    ['com.polidea.rxandroidble2.RxBleClient', 'create'],
    ['com.polidea.rxandroidble2.RxBleDevice', 'establishConnection'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'readCharacteristic'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'writeCharacteristic'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'writeDescriptor'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'setupNotification'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'requestMtu'],
    ['com.polidea.rxandroidble2.scan.ScanResult', 'getBleDevice']
  ].forEach(function (pair) {
    hookAll(pair[0], pair[1], function (self, args) {
      var rec = { api: pair[0] + '.' + pair[1], entry: ENTRY };
      try { rec.args = args.map(function (a) { return a === null ? null : String(a); }); } catch (e) {}
      emit(rec);
      return null;
    });
  });

  // D. R8-proof plugin discovery (release build renames the plugin class)
  if (typeof armorxProbePlugin === 'function') {
    armorxProbePlugin('flutterreactiveble', [
      'scanForDevices', 'connectToDevice', 'disconnectFromDevice', 'discoverServices',
      'readCharacteristic', 'writeCharacteristicWithResponse',
      'writeCharacteristicWithoutResponse', 'negotiateMtuSize',
      'readNotifications', 'stopNotifications', 'requestConnectionPriority',
      'initializeClient', 'deinitializeClient', 'clearGattCache'
    ], 2000);
  }

  note('entry script ' + ENTRY + ' ready');
  emit({ api: 'entry-ready', entry: ENTRY, ble_lib: 'flutter_reactive_ble' });
});
