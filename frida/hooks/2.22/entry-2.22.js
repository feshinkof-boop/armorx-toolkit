/*
 * armorx-lab :: ENTRY SCRIPT for BIGBIG WON 2.22 (com.moojiang.bigbigwon, versionCode 12)
 * ---------------------------------------------------------------------------
 * BLE stack:  Flutter plugin  flutter_reactive_ble  (package name in dex:
 *             com.signify.hue.flutterreactiveble), sitting on top of
 *             RxAndroidBle 2  (com.polidea.rxandroidble2).
 * MethodChannels seen in dex:  flutter_reactive_ble_method
 *                              flutter_reactive_ble_scan
 *                              flutter_reactive_ble_status
 *
 * RUN (from /home/salamanka/armorx-lab):
 *   frida -U -f com.moojiang.bigbigwon \
 *     -l frida/hooks/shared/bt-platform-hooks.js \
 *     -l frida/hooks/2.22/entry-2.22.js
 *
 * The platform hooks in the shared file already capture every android.bluetooth.*
 * call. This entry adds the plugin/library-layer names so a capture can be read
 * in the app's own vocabulary (scan / connect / write / notify).
 */

'use strict';

// fallbacks so the script still runs if the shared file was not loaded first
if (typeof note !== 'function') { var note = function (m) { console.log('[ARMORX-BT] ### ' + m); }; }
if (typeof emit !== 'function') { var emit = function (o) { console.log('[ARMORX-BT] ' + JSON.stringify(o)); }; }
if (typeof hookAll !== 'function') {
  var hookAll = function () { return false; };
}

var ENTRY = '2.22';

if (typeof Java === 'undefined') {
  note('entry ' + ENTRY + ': Java bridge unavailable in this Frida runtime -> use Frida 16.x');
} else
Java.perform(function () {
  note('entry script ' + ENTRY + ' attaching (flutter_reactive_ble + RxAndroidBle2)');

  // ---------------------------------------------------------------------
  // A. flutter_reactive_ble MethodChannels  (Dart <-> platform bridge)
  // ---------------------------------------------------------------------
  function hookChannelHandler(channelName) {
    try {
      var MC = Java.use('io.flutter.plugin.common.MethodChannel');
      var m = MC.setMethodCallHandler;
      m.overloads.forEach(function (ov) {
        ov.implementation = function () {
          var name = null;
          try { name = this.name ? this.name.value : null; } catch (e) {
            try { name = String(this.name); } catch (e2) {}
          }
          if (name && name.indexOf(channelName) === 0) {
            note('MethodChannel handler registered: ' + name);
            emit({ api: 'MethodChannel.setMethodCallHandler', channel: name });
          }
          return ov.apply(this, Array.prototype.slice.call(arguments));
        };
      });
      note('HOOKED MethodChannel.setMethodCallHandler (filter "' + channelName + '")');
    } catch (e) { note('channel handler hook failed: ' + e); }
  }
  hookChannelHandler('flutter_reactive_ble');

  // ---------------------------------------------------------------------
  // B. RxAndroidBle 2  (the Java library under flutter_reactive_ble)
  // ---------------------------------------------------------------------
  var rx = [
    ['com.polidea.rxandroidble2.RxBleClient', 'create'],
    ['com.polidea.rxandroidble2.RxBleDevice', 'establishConnection'],
    ['com.polidea.rxandroidble2.RxBleDevice', 'connect'],
    ['com.polidea.rxandroidble2.RxBleDevice', 'getName'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'readCharacteristic'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'writeCharacteristic'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'writeDescriptor'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'setupNotification'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'requestMtu'],
    ['com.polidea.rxandroidble2.RxBleConnection', 'discoverServices'],
    ['com.polidea.rxandroidble2.scan.ScanResult', 'getBleDevice']
  ];
  rx.forEach(function (pair) {
    var n = hookAll(pair[0], pair[1], function (self, args) {
      var rec = { api: pair[0] + '.' + pair[1], entry: ENTRY };
      try { rec.args = args.map(function (a) { return a === null ? null : String(a); }); } catch (e) {}
      emit(rec);
      return null;
    });
    if (!n) note('MISS ' + pair[0] + '.' + pair[1] + ' (RxAndroidBle version differs)');
  });

  // ---------------------------------------------------------------------
  // C. hint: reactive_ble exposes a "BleStatus" stream the app polls at start
  // ---------------------------------------------------------------------
  try {
    var Semantics = Java.use('com.signify.hue.flutterreactiveble.BleStatus');
    note('flutterreactiveble.BleStatus present');
  } catch (e) { /* obfuscated in release builds - ignore */ }

  // ---------------------------------------------------------------------
  // D. R8-proof plugin discovery: the release build renames the plugin class,
  //    so find the loaded class that owns these preserved method names.
  // ---------------------------------------------------------------------
  if (typeof armorxProbePlugin === 'function') {
    armorxProbePlugin('flutterreactiveble', [
      'scanForDevices', 'connectToDevice', 'disconnectFromDevice', 'discoverServices',
      'readCharacteristic', 'writeCharacteristicWithResponse',
      'writeCharacteristicWithoutResponse', 'negotiateMtuSize',
      'readNotifications', 'stopNotifications', 'requestConnectionPriority',
      'initializeClient', 'deinitializeClient', 'clearGattCache'
    ], 2000);
  } else {
    note('armorxProbePlugin not loaded (add shared/flutter-plugin-probe.js to the -l list)');
  }

  note('entry script ' + ENTRY + ' ready');
  emit({ api: 'entry-ready', entry: ENTRY, ble_lib: 'flutter_reactive_ble' });
});
