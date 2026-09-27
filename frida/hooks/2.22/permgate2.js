/*
 * armorx-lab :: BIGBIG WON 2.22.0901 permission-gate override (surgical)
 * ---------------------------------------------------------------------
 * The build declares ACCESS_FINE_LOCATION / ACCESS_COARSE_LOCATION with
 * android:maxSdkVersion="32"; on an API 33 device those are dropped from the
 * app's effective manifest. The bundled (obfuscated) `permission_handler`
 * plugin computes the status in class `f.a.a.n`, method
 *     int f(int permissionGroup, android.content.Context)
 * and returns 0 (denied) for the location group (observed group value 3),
 * logging "No permissions found in manifest for: []". The Dart side then never
 * proceeds to BLE scanning.
 *
 * This script forces the location group to 1 (granted) and logs every group
 * value it sees, so the intervention is explicit and observable. It only
 * affects this app process; the APK and the device permission database are
 * untouched.
 */
'use strict';

if (typeof Java === 'undefined') {
  console.log('[PERMGATE2] Java bridge unavailable');
} else Java.perform(function () {
  var LOCATION_GROUP = 3;   // permission_handler PermissionGroup.location
  var forced = 0;

  function log(m) {
    try { console.log('[PERMGATE2] ' + m); } catch (e) {}
    try { send({ kind: 'armorx-bt', api: 'permgate2', detail: m }); } catch (e) {}
  }

  try {
    var C = Java.use('f.a.a.n');
    C.f.overload('int', 'android.content.Context').implementation = function (group, ctx) {
      var real = this.f(group, ctx);
      if (group === LOCATION_GROUP) {
        forced++;
        log('f(group=' + group + ') real=' + real + ' -> 1 (GRANTED, forced)');
        return 1;
      }
      log('f(group=' + group + ') -> ' + real + ' (passthrough)');
      return real;
    };
    log('hooked f.a.a.n.f(int,Context); location group ' + LOCATION_GROUP + ' forced to 1');
  } catch (e) { log('hook f.a.a.n.f failed: ' + e); }
});