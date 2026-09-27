/*
 * armorx-lab :: obfuscation-proof Flutter plugin probe (shared helper)
 * ---------------------------------------------------------------------------
 * WHY: the BIGBIG WON release builds are R8-shrunk. In 2.23/2.24 the Flutter
 * embedding classes are renamed (io/flutter/embedding/android/a..x) and the
 * plugin's MethodCallHandler class name is not stable. Method *names* that the
 * Dart side calls over the method channel ARE preserved in the dex (they appear
 * as string literals), e.g.:
 *     scanForDevices / connectToDevice / discoverServices / readCharacteristic
 *     writeCharacteristicWithResponse / writeCharacteristicWithoutResponse
 *     negotiateMtuSize / readNotifications / stopNotifications / requestMtu
 * So we discover the owning class AT RUNTIME from the loaded-class list and
 * hook the methods by name. This survives obfuscation.
 *
 * Usage (from an entry script, after the shared hooks are loaded):
 *     armorxProbePlugin('flutterreactiveble', ['scanForDevices', ...]);
 */

'use strict';

function armorxProbePlugin(pkgNeedle, methodNames, delayMs) {
  if (typeof Java === 'undefined') return;
  var delay = delayMs || 1500;
  setTimeout(function () {
    Java.perform(function () {
      var hitClasses = {};
      Java.enumerateLoadedClasses({
        onMatch: function (cn) {
          if (cn.toLowerCase().indexOf(pkgNeedle.toLowerCase()) !== -1) hitClasses[cn] = true;
        },
        onComplete: function () {
          var names = Object.keys(hitClasses);
          console.log('[ARMORX-PLUGIN] discovered ' + names.length + ' class(es) matching "' + pkgNeedle + '": ' + names.join(', '));
          var total = 0;
          names.forEach(function (cn) {
            var clazz;
            try { clazz = Java.use(cn); } catch (e) { return; }
            methodNames.forEach(function (mn) {
              var m;
              try { m = clazz[mn]; } catch (e) { return; }
              if (!m || !m.overloads) return;
              m.overloads.forEach(function (ov) {
                ov.implementation = function () {
                  var args = Array.prototype.slice.call(arguments);
                  var rec = { api: cn + '.' + mn, layer: 'flutter-plugin' };
                  try {
                    if (args[0] !== null && args[0] !== undefined) {
                      try { rec.channel_method = String(args[0].method); } catch (e) {}
                      try { var a = args[0].arguments; rec.channel_args = a === null ? null : String(a); } catch (e) {}
                    }
                  } catch (e) {}
                  try { console.log('[ARMORX-BT] ' + JSON.stringify(rec)); send(rec); } catch (e) {}
                  return ov.apply(this, args);
                };
                total++;
              });
            });
          });
          console.log('[ARMORX-PLUGIN] hooked ' + total + ' plugin method overload(s) by name');
          try { send({ kind: 'armorx-bt', api: 'plugin-probe-done', pkg: pkgNeedle, classes: names.length, overloads: total }); } catch (e) {}
        }
      });
    });
  }, delay);
}
