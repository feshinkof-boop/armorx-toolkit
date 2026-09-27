/*
 * armorx-lab :: BIGBIG WON 2.22.0901 permission-gate instrumentation
 * ------------------------------------------------------------------
 * The build declares ACCESS_FINE_LOCATION / ACCESS_COARSE_LOCATION with
 * android:maxSdkVersion="32". On an API 33 device those entries are dropped
 * from the app's effective manifest, so the Flutter `permission_handler`
 * plugin logs "No permissions found in manifest for: []" and the Dart side
 * never proceeds to BLE scanning (the ARMOR-X Pro card tap is a no-op).
 *
 * This script makes the platform-side answers consistent with the app's own
 * API-32-era expectation: it reports the two location permissions as present
 * in the manifest and as already granted. It does NOT modify the APK, does not
 * touch the device's real permission database, and only affects this app
 * process. Every intercepted call is logged so the effect is observable.
 *
 * Observation + research only: no vendor bytes are injected.
 */
'use strict';

var PKG = 'com.moojiang.bigbigwon';
var GET_PERMISSIONS = 0x00001000;   // PackageManager.GET_PERMISSIONS

function isLoc(p) {
  return p === 'android.permission.ACCESS_FINE_LOCATION' ||
         p === 'android.permission.ACCESS_COARSE_LOCATION';
}
function log(m) {
  try { console.log('[PERMGATE] ' + m); } catch (e) {}
  try { send({ kind: 'armorx-bt', api: 'permgate', detail: m }); } catch (e) {}
}

if (typeof Java === 'undefined') {
  log('Java bridge unavailable');
} else Java.perform(function () {
  var n = { pkg: 0, check: 0 };

  // ---- 1. make PackageManager report the location permissions in the manifest
  try {
    var PM = Java.use('android.app.ApplicationPackageManager');
    PM.getPackageInfo.overload('java.lang.String', 'int').implementation = function (name, flags) {
      var r = this.getPackageInfo(name, flags);
      try {
        if (name === PKG && (flags & GET_PERMISSIONS)) {
          var cur = r.requestedPermissions.value;
          var list = [];
          if (cur) { for (var i = 0; i < cur.length; i++) list.push(String(cur[i])); }
          var added = false;
          ['android.permission.ACCESS_FINE_LOCATION', 'android.permission.ACCESS_COARSE_LOCATION'].forEach(function (p) {
            if (list.indexOf(p) < 0) { list.push(p); added = true; }
          });
          if (added) {
            var out = Java.array('java.lang.String', list);
            r.requestedPermissions.value = out;
            n.pkg++;
            log('getPackageInfo(' + name + ',' + flags + ') -> injected location perms; requestedPermissions=' + JSON.stringify(list));
          }
        }
      } catch (e) { log('getPackageInfo patch error: ' + e); }
      return r;
    };
    log('hooked ApplicationPackageManager.getPackageInfo');
  } catch (e) { log('getPackageInfo hook failed: ' + e); }

  // ---- 2. report location permissions as granted at check time
  function hookCheck(objName, methods) {
    try {
      var C = Java.use(objName);
      methods.forEach(function (sig) {
        try {
          C[sig[0]].overload.apply(C[sig[0]], sig[1]).implementation = function () {
            var args = Array.prototype.slice.call(arguments);
            var perm = args.length ? String(args[0]) : '';
            if (isLoc(perm)) {
              n.check++;
              log(objName + '.' + sig[0] + '(' + perm + ') -> 0 (GRANTED, forced)');
              return 0;
            }
            return this[sig[0]].apply(this, args);
          };
          log('hooked ' + objName + '.' + sig[0]);
        } catch (e) { log('miss ' + objName + '.' + sig[0] + ': ' + e); }
      });
    } catch (e) { log('class ' + objName + ' missing: ' + e); }
  }

  hookCheck('android.content.Context', [
    ['checkPermission', ['java.lang.String', 'int']],
    ['checkSelfPermission', ['java.lang.String']]
  ]);
  hookCheck('android.app.ApplicationPackageManager', [
    ['checkPermission', ['java.lang.String', 'java.lang.String']]
  ]);

  // androidx PermissionChecker (used by some permission_handler versions)
  try {
    var PC = Java.use('androidx.core.content.PermissionChecker');
    PC.checkSelfPermission.overload('android.content.Context', 'java.lang.String').implementation = function (c, p) {
      if (isLoc(String(p))) { n.check++; log('PermissionChecker.checkSelfPermission(' + p + ') -> 0 (GRANTED, forced)'); return 0; }
      return this.checkSelfPermission(c, p);
    };
    log('hooked PermissionChecker.checkSelfPermission');
  } catch (e) { log('PermissionChecker not present (' + e + ')'); }

  log('permission-gate instrumentation ready');
});