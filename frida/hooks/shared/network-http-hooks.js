/*
 * armorx-lab :: network-side capture hooks (HTTP to m.bigbigwon.com:8080)
 * ---------------------------------------------------------------------------
 * WHY THIS IS NATIVE-LEVEL AND NOT (ONLY) JAVA-LEVEL:
 *   The BIGBIG WON apps are Flutter. Their HTTP client is Dart's `dart:io`
 *   HttpClient (package:http / dio on top of it). dart:io performs its own
 *   networking inside the Flutter engine and does NOT route through Java's
 *   HttpURLConnection / OkHttp. A purely Java-level hook therefore MISSES the
 *   app's real traffic.
 *
 *   This script therefore hooks the libc socket primitives (connect / send* /
 *   recv* / write* / read*), learns the peer address of every file descriptor
 *   via connect(), and only dumps payloads for descriptors talking to the
 *   watched port(s) (default 8080). Java OkHttp / HttpURLConnection hooks are
 *   included as a secondary net for any native/platform traffic.
 *
 * Companion approach (documented in README): mitmproxy in regular/transparent
 * mode. The endpoint is PLAINTEXT http://, so no TLS pinning is involved —
 * mitmproxy works with the emulator's HTTP proxy option set.
 *
 * Load order (native hooks must be installed early):
 *   frida -U -f <pkg> -l hooks/shared/network-http-hooks.js -l hooks/shared/bt-platform-hooks.js -l hooks/<ver>/entry-<ver>.js
 */

'use strict';

var NETCFG = {
  TAG: '[ARMORX-NET]',
  PORTS: [8080],          // watched TCP ports (m.bigbigwon.com:8080)
  HOSTS: ['m.bigbigwon.com', 'bigbigwon.com'],
  MAX_BYTES: 4096,
  DUMP_ALWAYS_FOR_PORTS: true
};

function nlog(obj) {
  try {
    obj.ts = new Date().toISOString();
    obj.kind = 'armorx-net';
    console.log(NETCFG.TAG, JSON.stringify(obj));
    try { send(obj); } catch (e) {}
  } catch (e) { console.log(NETCFG.TAG, 'emit-error ' + e); }
}

function nnote(m) { console.log(NETCFG.TAG, '### ' + m); }

// Frida-version-compatible global export lookup.
//   Frida <=16 : Module.findExportByName(null, name)
//   Frida 17+  : Module.findGlobalExportByName(name) / getGlobalExportByName(name)
function findExport(name) {
  try { if (typeof Module.findExportByName === 'function') { var p = Module.findExportByName(null, name); if (p) return p; } } catch (e) {}
  try { if (typeof Module.findGlobalExportByName === 'function') { var q = Module.findGlobalExportByName(name); if (q) return q; } } catch (e) {}
  try { if (typeof Module.getGlobalExportByName === 'function') { var r = Module.getGlobalExportByName(name); if (r) return r; } } catch (e) {}
  try { return Process.getModuleByName('libc.so').getExportByName(name); } catch (e) {}
  return null;
}

function bufHex(p, len) {
  try {
    if (p.isNull() || len <= 0) return null;
    var n = len > NETCFG.MAX_BYTES ? NETCFG.MAX_BYTES : len;
    var ab = Memory.readByteArray(p, n);
    var u8 = new Uint8Array(ab);
    var hex = '';
    for (var i = 0; i < u8.length; i++) hex += (u8[i] < 16 ? '0' : '') + u8[i].toString(16);
    if (len > n) hex += '...(+' + (len - n) + 'B)';
    return hex;
  } catch (e) { return null; }
}

function bufAscii(p, len) {
  try {
    var n = len > 256 ? 256 : len;
    var ab = Memory.readByteArray(p, n);
    var u8 = new Uint8Array(ab), out = '';
    for (var i = 0; i < u8.length; i++) out += (u8[i] >= 0x20 && u8[i] < 0x7f) ? String.fromCharCode(u8[i]) : '.';
    return out;
  } catch (e) { return null; }
}

// ---------------------------------------------------------------------------
// fd -> peer map, learned from connect()
// ---------------------------------------------------------------------------
var fdMap = {};

function parseSockaddr(sa) {
  try {
    var family = sa.readU16();
    if (family === 2) { // AF_INET
      var port = sa.add(2).readU8() * 256 + sa.add(3).readU8();
      var ip = sa.add(4).readU8() + '.' + sa.add(5).readU8() + '.' + sa.add(6).readU8() + '.' + sa.add(7).readU8();
      return { family: 'AF_INET', ip: ip, port: port };
    }
    if (family === 10) { // AF_INET6
      var port6 = sa.add(2).readU8() * 256 + sa.add(3).readU8();
      var parts = [];
      for (var i = 0; i < 8; i++) parts.push(((sa.add(8 + i * 2).readU8() << 8) | sa.add(9 + i * 2).readU8()).toString(16));
      return { family: 'AF_INET6', ip: parts.join(':'), port: port6 };
    }
    return { family: 'other(' + family + ')' };
  } catch (e) { return null; }
}

function isWatched(peer) {
  return peer && peer.port && NETCFG.PORTS.indexOf(peer.port) !== -1;
}

function installConnectHook() {
  ['connect'].forEach(function (fn) {
    var p = findExport(fn);
    if (!p) { nnote('no libc ' + fn); return; }
    Interceptor.attach(p, {
      onEnter: function (args) {
        this.fd = args[0].toInt32();
        this.sa = args[1];
        this.peer = parseSockaddr(args[1]);
      },
      onLeave: function (retval) {
        if (this.peer) fdMap[this.fd] = this.peer;
        if (isWatched(this.peer)) {
          nlog({ api: 'connect', fd: this.fd, peer: this.peer, ret: retval.toInt32() });
        }
      }
    });
    nnote('HOOKED libc ' + fn);
  });
}

function installCloseHooks() {
  ['close'].forEach(function (fn) {
    var p = findExport(fn);
    if (!p) return;
    Interceptor.attach(p, {
      onEnter: function (args) { this.fd = args[0].toInt32(); },
      onLeave: function () { delete fdMap[this.fd]; }
    });
    nnote('HOOKED libc ' + fn);
  });
}

function installSendHooks() {
  // buf, len are args[1], args[2] for send/sendto/write
  var simple = ['send', 'sendto', 'write'];
  simple.forEach(function (fn) {
    var p = findExport(fn);
    if (!p) { nnote('no libc ' + fn); return; }
    Interceptor.attach(p, {
      onEnter: function (args) {
        var fd = args[0].toInt32();
        var peer = fdMap[fd];
        if (!isWatched(peer)) return;
        var len = args[2].toInt32();
        nlog({ api: 'libc.' + fn, dir: 'out', fd: fd, peer: peer, len: len,
               data_hex: bufHex(args[1], len), data_ascii: bufAscii(args[1], len) });
      }
    });
    nnote('HOOKED libc ' + fn);
  });

  // sendmsg(fd, msghdr*, flags)
  var p = findExport('sendmsg');
  if (p) {
    Interceptor.attach(p, {
      onEnter: function (args) {
        var fd = args[0].toInt32();
        var peer = fdMap[fd];
        if (!isWatched(peer)) return;
        var msg = args[1];
        try {
          var iov = msg.add(16).readPointer();      // x86_64 msghdr.msg_iov
          var iovlen = msg.add(24).readU64().toNumber();
          for (var i = 0; i < iovlen && i < 4; i++) {
            var base = iov.add(i * 16).readPointer();
            var len = iov.add(i * 16 + 8).readU64().toNumber();
            nlog({ api: 'libc.sendmsg', dir: 'out', fd: fd, peer: peer, len: len,
                   data_hex: bufHex(base, len), data_ascii: bufAscii(base, len) });
          }
        } catch (e) { nnote('sendmsg parse error ' + e); }
      }
    });
    nnote('HOOKED libc sendmsg');
  }
}

function installRecvHooks() {
  // recv/recvfrom/read: dump AFTER the call using the return length
  var simple = ['recv', 'recvfrom', 'read'];
  simple.forEach(function (fn) {
    var p = findExport(fn);
    if (!p) { nnote('no libc ' + fn); return; }
    Interceptor.attach(p, {
      onEnter: function (args) {
        this.fd = args[0].toInt32();
        this.buf = args[1];
        this.peer = fdMap[this.fd];
      },
      onLeave: function (retval) {
        if (!isWatched(this.peer)) return;
        var n = retval.toInt32();
        if (n <= 0) return;
        nlog({ api: 'libc.' + fn, dir: 'in', fd: this.fd, peer: this.peer, len: n,
               data_hex: bufHex(this.buf, n), data_ascii: bufAscii(this.buf, n) });
      }
    });
    nnote('HOOKED libc ' + fn);
  });

  var p = findExport('recvmsg');
  if (p) {
    Interceptor.attach(p, {
      onEnter: function (args) { this.fd = args[0].toInt32(); this.msg = args[1]; this.peer = fdMap[this.fd]; },
      onLeave: function (retval) {
        if (!isWatched(this.peer)) return;
        if (retval.toInt32() <= 0) return;
        try {
          var iov = this.msg.add(16).readPointer();
          var len = iov.add(8).readU64().toNumber();
          var base = iov.readPointer();
          nlog({ api: 'libc.recvmsg', dir: 'in', fd: this.fd, peer: this.peer, len: len,
                 data_hex: bufHex(base, len), data_ascii: bufAscii(base, len) });
        } catch (e) {}
      }
    });
    nnote('HOOKED libc recvmsg');
  }
}

// ---------------------------------------------------------------------------
// Java secondary net: OkHttp + HttpURLConnection
// ---------------------------------------------------------------------------
function installJavaNetHooks() {
  if (typeof Java === 'undefined') {
    nnote('Java bridge not available in this Frida runtime (Frida 17+ requires ' +
          'compiling the agent with frida-java-bridge). Native socket hooks still active.');
    return;
  }
  Java.perform(function () {
    try {
      var Builder = Java.use('okhttp3.Request$Builder');
      ['url', 'addHeader', 'header', 'method', 'post', 'put', 'delete', 'patch', 'build'].forEach(function (mn) {
        try {
          var m = Builder[mn]; if (!m) return;
          m.overloads.forEach(function (ov) {
            ov.implementation = function () {
              var a = Array.prototype.slice.call(arguments);
              var rec = { api: 'okhttp3.Request$Builder.' + mn };
              try { rec.args = a.map(function (x) { return x === null ? null : String(x); }); } catch (e) {}
              if (mn === 'build') { try { rec.url = this.url().toString(); } catch (e) {} }
              nlog(rec);
              return ov.apply(this, a);
            };
          });
        } catch (e) {}
      });
      nnote('HOOKED okhttp3.Request$Builder');
    } catch (e) { nnote('okhttp3 absent (expected for Flutter dart:io apps)'); }

    try {
      var HUC = Java.use('java.net.HttpURLConnection');
      ['setRequestMethod', 'getInputStream', 'getOutputStream', 'connect'].forEach(function (mn) {
        try {
          var m = HUC[mn]; if (!m) return;
          m.overloads.forEach(function (ov) {
            ov.implementation = function () {
              var a = Array.prototype.slice.call(arguments);
              var rec = { api: 'HttpURLConnection.' + mn };
              try { rec.url = this.getURL().toString(); } catch (e) {}
              try { rec.args = a.map(function (x) { return x === null ? null : String(x); }); } catch (e) {}
              nlog(rec);
              return ov.apply(this, a);
            };
          });
        } catch (e) {}
      });
      nnote('HOOKED java.net.HttpURLConnection');
    } catch (e) { nnote('HttpURLConnection hook failed: ' + e); }
  });
}

// ---------------------------------------------------------------------------
// boot
// ---------------------------------------------------------------------------
nnote('=========================================================');
nnote(' armorx-lab network capture hooks (ports ' + NETCFG.PORTS.join(',') + ')');
nnote('=========================================================');
try { installConnectHook(); } catch (e) { nnote('connect hook err ' + e); }
try { installCloseHooks(); } catch (e) { nnote('close hook err ' + e); }
try { installSendHooks(); } catch (e) { nnote('send hook err ' + e); }
try { installRecvHooks(); } catch (e) { nnote('recv hook err ' + e); }
try { installJavaNetHooks(); } catch (e) { nnote('java net hook err ' + e); }
nnote('network hooks installed');
try { send({ kind: 'armorx-net', api: 'hooks-ready', ts: new Date().toISOString() }); } catch (e) {}
