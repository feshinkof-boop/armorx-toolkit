/* find the permission_handler plugin's real call path by trapping its log line */
'use strict';
Java.perform(function () {
  var Log = Java.use('android.util.Log');
  var Exception = Java.use('java.lang.Exception');
  var seen = {};
  Log.d.overload('java.lang.String', 'java.lang.String').implementation = function (tag, msg) {
    try {
      if (tag && String(tag).indexOf('permission') >= 0) {
        var key = String(tag) + '|' + String(msg);
        if (!seen[key]) {
          seen[key] = 1;
          var st = Log.getStackTraceString(Exception.$new());
          console.log('[PERMSTACK] ' + tag + ' :: ' + msg + '\n' + st);
          try { send({ kind: 'armorx-bt', api: 'permstack', tag: String(tag), msg: String(msg), stack: String(st) }); } catch (e) {}
        }
      }
    } catch (e) {}
    return this.d(tag, msg);
  };
  console.log('[PERMSTACK] Log.d probe installed');
});
