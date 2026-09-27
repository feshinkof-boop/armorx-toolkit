/* trace the obfuscated permission_handler plugin class f.a.a.n */
'use strict';
Java.perform(function () {
  var C;
  try { C = Java.use('f.a.a.n'); } catch (e) { console.log('[PLUGIN] class missing: ' + e); return; }
  var methods = C.class.getDeclaredMethods();
  var names = [];
  methods.forEach(function (m) {
    var name = m.getName();
    var params = m.getParameterTypes();
    var sig = [];
    for (var i = 0; i < params.length; i++) sig.push(params[i].getName());
    names.push(name + '(' + sig.join(',') + ')');
    try {
      var ov = C[name];
      if (!ov) return;
      ov.overload.apply(ov, sig).implementation = function () {
        var args = Array.prototype.slice.call(arguments);
        var r = this[name].apply(this, args);
        var rs;
        try { rs = (r === null || r === undefined) ? String(r) : String(r); } catch (e) { rs = '<' + e + '>'; }
        var line = name + '(' + args.map(function (a) { return a === null ? 'null' : String(a); }).join(',') + ') -> ' + rs;
        console.log('[PLUGIN] ' + line);
        try { send({ kind: 'armorx-bt', api: 'plugin-trace', detail: line }); } catch (e) {}
        return r;
      };
    } catch (e) { console.log('[PLUGIN] hookfail ' + name + ': ' + e); }
  });
  console.log('[PLUGIN] f.a.a.n methods: ' + JSON.stringify(names));
});