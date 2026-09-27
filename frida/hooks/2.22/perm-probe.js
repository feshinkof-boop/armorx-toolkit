/* permission request probe: log which runtime permissions the app requests */
'use strict';
var seen = {};
Java.perform(function () {
  function n(m){ console.log('[PERM] ' + m); }
  // Activity.requestPermissions(String[], int)
  try {
    var Act = Java.use('android.app.Activity');
    Act.requestPermissions.overload('[Ljava.lang.String;', 'int').implementation = function (p, c) {
      var l = [];
      for (var i = 0; i < p.length; i++) l.push(String(p[i]));
      n('Activity.requestPermissions code=' + c + ' perms=' + JSON.stringify(l));
      return this.requestPermissions(p, c);
    };
    n('hooked Activity.requestPermissions');
  } catch (e) { n('Activity hook failed: ' + e); }
  // PermissionChecker / ContextCompat
  try {
    var CC = Java.use('androidx.core.content.ContextCompat');
    CC.checkSelfPermission.overload('android.content.Context', 'java.lang.String').implementation = function (ctx, perm) {
      var r = this.checkSelfPermission(ctx, perm);
      n('ContextCompat.checkSelfPermission ' + perm + ' -> ' + r);
      return r;
    };
    n('hooked ContextCompat.checkSelfPermission');
  } catch (e) { n('ContextCompat hook failed: ' + e); }
  // PermissionManager-ish: find the class holding the log string is hard; instead hook ActivityCompat
  try {
    var AC = Java.use('androidx.core.app.ActivityCompat');
    AC.requestPermissions.overload('android.app.Activity', '[Ljava.lang.String;', 'int').implementation = function (a, p, c) {
      var l = [];
      for (var i = 0; i < p.length; i++) l.push(String(p[i]));
      n('ActivityCompat.requestPermissions code=' + c + ' perms=' + JSON.stringify(l));
      return this.requestPermissions(a, p, c);
    };
    n('hooked ActivityCompat.requestPermissions');
  } catch (e) { n('ActivityCompat hook failed: ' + e); }
  n('perm probe ready');
});