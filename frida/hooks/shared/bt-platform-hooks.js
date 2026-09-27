/*
 * armorx-lab :: SHARED platform-level Android Bluetooth / BLE tracing hooks
 * ---------------------------------------------------------------------------
 * Library-agnostic. These hooks live on the ANDROID PLATFORM (android.bluetooth.*)
 * so they capture every BLE/GATT operation regardless of which Flutter plugin
 * the app uses (flutter_reactive_ble, flutter_blue_plus, RxAndroidBle2, ...).
 *
 * Load this file BEFORE a per-version entry script:
 *     frida -U -f com.moojiang.bigbigwon -l hooks/shared/bt-platform-hooks.js -l hooks/2.23/entry-2.23.js
 *
 * Design rules
 *   - RAW BYTE ARRAYS ARE LOGGED AS HEX *BEFORE* ANY TEXT ENCODING.
 *     The ASCII/UTF-8 rendering is emitted as a clearly separate field ("ascii=")
 *     so the hex remains the ground truth.
 *   - Every emitted record is also delivered to the host via send() with
 *     type:"armorx-bt" so a capture driver can persist it to JSONL.
 *   - All hooks are wrapped in try/catch: a missing class on a given Android
 *     version must never abort the whole script.
 */

'use strict';

// ---------------------------------------------------------------------------
// config
// ---------------------------------------------------------------------------
var CFG = {
  TAG: '[ARMORX-BT]',
  MAX_BYTES: 1024,   // per-buffer dump cap (hex chars = 2x)
  LOG_ASCII: true,   // include a separate ASCII field *after* the hex
  LOG_BACKTRACE: false, // set true to attach JS backtraces (noisy but useful)
  HOOK_SCAN: true,
  HOOK_GATT: true,
  HOOK_GATT_CALLBACK: true,
  HOOK_DEVICE: true,
  HOOK_VALUE_ACCESSORS: true,
  HOOK_ADAPTER: true,
  HOOK_METHODCHANNEL: true
};

function ts() { return new Date().toISOString(); }

function emit(obj) {
  try {
    obj.ts = ts();
    obj.kind = 'armorx-bt';
    console.log(CFG.TAG, JSON.stringify(obj));
    try { send(obj); } catch (e) { /* host may not be listening */ }
  } catch (e) {
    console.log(CFG.TAG, 'emit-error ' + e);
  }
}

function note(msg) { console.log(CFG.TAG, '### ' + msg); }

// ---------------------------------------------------------------------------
// byte helpers  (hex FIRST, text encoding strictly secondary)
// ---------------------------------------------------------------------------
function jbytesToHex(b) {
  if (b === null || b === undefined) return null;
  var out = '';
  try {
    var n = b.length;
    if (n > CFG.MAX_BYTES * 4) n = CFG.MAX_BYTES; // signed arrays: still fine
    for (var i = 0; i < n; i++) {
      var v = b[i] & 0xff;
      out += (v < 16 ? '0' : '') + v.toString(16);
    }
    if (b.length > n) out += '...(+' + (b.length - n) + 'B)';
  } catch (e) { return '<hex-err:' + e + '>'; }
  return out;
}

function jbytesToAscii(b) {
  if (!CFG.LOG_ASCII || b === null || b === undefined) return undefined;
  var out = '';
  try {
    var n = b.length > 256 ? 256 : b.length;
    for (var i = 0; i < n; i++) {
      var v = b[i] & 0xff;
      out += (v >= 0x20 && v < 0x7f) ? String.fromCharCode(v) : '.';
    }
  } catch (e) { return undefined; }
  return out;
}

// native Pointer (used by libc hooks / dart buffers)
function ptrToHex(p, len) {
  try {
    if (p.isNull()) return null;
    return Memory.readByteArray(p, len);
  } catch (e) { return null; }
}

function abToHex(ab) {
  if (ab === null) return null;
  var u8;
  try { u8 = new Uint8Array(ab); } catch (e) { return null; }
  var n = u8.length > CFG.MAX_BYTES ? CFG.MAX_BYTES : u8.length;
  var out = '';
  for (var i = 0; i < n; i++) out += (u8[i] < 16 ? '0' : '') + u8[i].toString(16);
  if (u8.length > n) out += '...(+' + (u8.length - n) + 'B)';
  return out;
}

function abToAscii(ab) {
  if (!CFG.LOG_ASCII || ab === null) return undefined;
  var u8; try { u8 = new Uint8Array(ab); } catch (e) { return undefined; }
  var n = u8.length > 256 ? 256 : u8.length, out = '';
  for (var i = 0; i < n; i++) out += (u8[i] >= 0x20 && u8[i] < 0x7f) ? String.fromCharCode(u8[i]) : '.';
  return out;
}

// ---------------------------------------------------------------------------
// descriptor helpers
// ---------------------------------------------------------------------------
function s(v) { try { return v === null ? null : v.toString(); } catch (e) { return '<err>'; } }

function uuidOf(o) { try { return o === null ? null : s(o.getUuid()); } catch (e) { return null; } }

function charDesc(ch) {
  var d = {};
  try { d.char_uuid = uuidOf(ch); } catch (e) {}
  try {
    var svc = ch.getService();
    d.service_uuid = svc === null ? null : uuidOf(svc);
  } catch (e) {}
  try { d.properties = ch.getProperties(); } catch (e) {}
  try { d.instance_id = ch.getInstanceId(); } catch (e) {}
  try {
    var v = ch.getValue();
    if (v !== null) {
      d.value_hex = jbytesToHex(v);
      var a = jbytesToAscii(v);
      if (a !== undefined) d.value_ascii = a;
    }
  } catch (e) {}
  return d;
}

function descDesc(desc) {
  var d = {};
  try { d.desc_uuid = uuidOf(desc); } catch (e) {}
  try {
    var ch = desc.getCharacteristic();
    d.char_uuid = uuidOf(ch);
    try { var svc = ch.getService(); d.service_uuid = svc === null ? null : uuidOf(svc); } catch (e) {}
  } catch (e) {}
  try {
    var v = desc.getValue();
    if (v !== null) { d.value_hex = jbytesToHex(v); var a = jbytesToAscii(v); if (a !== undefined) d.value_ascii = a; }
  } catch (e) {}
  return d;
}

function devDesc(dev) {
  var d = {};
  try { d.address = s(dev.getAddress()); } catch (e) {}
  try { d.name = s(dev.getName()); } catch (e) {}
  try { d.type = dev.getType(); } catch (e) {}
  try { d.bond_state = dev.getBondState(); } catch (e) {}
  return d;
}

// ---------------------------------------------------------------------------
// generic hooker: applies to every overload of a method
//   handler(self, args, overload) -> {ret: value}  => return value
//                                 -> anything else => call original and return it
// ---------------------------------------------------------------------------
function hookAll(className, methodName, handler) {
  var clazz;
  try { clazz = Java.use(className); } catch (e) { return false; }
  var m;
  try { m = clazz[methodName]; } catch (e) { return false; }
  if (!m || !m.overloads) return false;
  var ovs = m.overloads;
  for (var i = 0; i < ovs.length; i++) {
    (function (ov) {
      ov.implementation = function () {
        var args = Array.prototype.slice.call(arguments);
        var res;
        try { res = handler(this, args, ov); } catch (e) { note('handler-error ' + className + '.' + methodName + ' : ' + e); }
        if (res && typeof res === 'object' && 'ret' in res) return res.ret;
        return ov.apply(this, args);
      };
    })(ovs[i]);
  }
  return ovs.length;
}

function hooked(className, methodName, n) {
  if (n) note('HOOKED ' + className + '.' + methodName + ' (' + n + ' overload(s))');
  else note('MISS   ' + className + '.' + methodName + ' (class/method absent on this build)');
}

// ===========================================================================
// 1. SCANNING  (BluetoothLeScanner + ScanCallback + legacy startLeScan)
// ===========================================================================
function installScanHooks() {
  if (!CFG.HOOK_SCAN) return;

  // --- BluetoothAdapter legacy + modern entry points ---------------------
  hooked('android.bluetooth.BluetoothAdapter', 'startDiscovery',
    hookAll('android.bluetooth.BluetoothAdapter', 'startDiscovery', function (self, args) {
      var d = devDesc(self.getRemoteDevice ? null : null);
      emit({ api: 'BluetoothAdapter.startDiscovery', self: safeAdapterDesc(self) });
      return null;
    }));

  hooked('android.bluetooth.BluetoothAdapter', 'startLeScan',
    hookAll('android.bluetooth.BluetoothAdapter', 'startLeScan', function (self, args) {
      emit({ api: 'BluetoothAdapter.startLeScan (legacy)', self: safeAdapterDesc(self), null_cb: args.length > 0 && args[args.length - 1] === null });
      return null;
    }));

  hooked('android.bluetooth.BluetoothAdapter', 'stopLeScan',
    hookAll('android.bluetooth.BluetoothAdapter', 'stopLeScan', function (self) {
      emit({ api: 'BluetoothAdapter.stopLeScan (legacy)' });
      return null;
    }));

  // --- BluetoothLeScanner (the API both plugins actually reach) ----------
  hooked('android.bluetooth.le.BluetoothLeScanner', 'startScan',
    hookAll('android.bluetooth.le.BluetoothLeScanner', 'startScan', function (self, args) {
      // overloads: (ScanCallback), (List<ScanFilter>, ScanSettings, ScanCallback)
      var cb = args[args.length - 1];
      var filters = null;
      try { if (args.length >= 3 && args[0] !== null) filters = filtersDesc(args[0]); } catch (e) {}
      emit({
        api: 'BluetoothLeScanner.startScan',
        arg_count: args.length,
        settings: args.length >= 3 ? settingsDesc(args[1]) : null,
        filters: filters,
        callback: cb === null ? null : s(cb.$className || java_getClass(cb))
      });
      return null;
    }));

  hooked('android.bluetooth.le.BluetoothLeScanner', 'stopScan',
    hookAll('android.bluetooth.le.BluetoothLeScanner', 'stopScan', function (self, args) {
      emit({ api: 'BluetoothLeScanner.stopScan' });
      return null;
    }));

  hooked('android.bluetooth.le.BluetoothLeScanner', 'flushPendingScanResults',
    hookAll('android.bluetooth.le.BluetoothLeScanner', 'flushPendingScanResults', function () {
      emit({ api: 'BluetoothLeScanner.flushPendingScanResults' });
      return null;
    }));

  // --- ScanCallback -------------------------------------------------------
  var n = hookAll('android.bluetooth.le.ScanCallback', 'onScanResult', function (self, args) {
    emit({ api: 'ScanCallback.onScanResult', callback_type: args[0], result: scanResultDesc(args[1]) });
    return null;
  }); hooked('android.bluetooth.le.ScanCallback', 'onScanResult', n);

  n = hookAll('android.bluetooth.le.ScanCallback', 'onBatchScanResults', function (self, args) {
    var list = [], arr = args[0];
    try { for (var i = 0; i < arr.size(); i++) list.push(scanResultDesc(arr.get(i))); } catch (e) {}
    emit({ api: 'ScanCallback.onBatchScanResults', count: list.length, results: list });
    return null;
  }); hooked('android.bluetooth.le.ScanCallback', 'onBatchScanResults', n);

  n = hookAll('android.bluetooth.le.ScanCallback', 'onScanFailed', function (self, args) {
    emit({ api: 'ScanCallback.onScanFailed', error_code: args[0] });
    return null;
  }); hooked('android.bluetooth.le.ScanCallback', 'onScanFailed', n);
}

function java_getClass(o) { try { return o.getClass().getName(); } catch (e) { return null; } }

function safeAdapterDesc(adapter) {
  var d = {};
  try { d.address = s(adapter.getAddress()); } catch (e) {}
  try { d.name = s(adapter.getName()); } catch (e) {}
  try { d.state = adapter.getState(); } catch (e) {}
  try { d.enabled = adapter.isEnabled(); } catch (e) {}
  return d;
}

function settingsDesc(st) {
  if (st === null) return null;
  var d = {};
  try { d.scan_mode = st.getScanMode(); } catch (e) {}
  try { d.report_delay_ms = st.getReportDelayMillis(); } catch (e) {}
  try { d.callback_type = st.getCallbackType(); } catch (e) {}
  try { d.match_mode = st.getMatchMode(); } catch (e) {}
  try { d.legacy = st.getLegacy(); } catch (e) {}
  return d;
}

function filtersDesc(filters) {
  var out = [];
  try {
    for (var i = 0; i < filters.size(); i++) {
      var f = filters.get(i), d = {};
      try { d.device_address = s(f.getDeviceAddress()); } catch (e) {}
      try { d.device_name = s(f.getDeviceName()); } catch (e) {}
      try { d.service_uuid = s(f.getServiceUuid()); } catch (e) {}
      out.push(d);
    }
  } catch (e) {}
  return out;
}

function scanResultDesc(r) {
  if (r === null) return null;
  var d = {};
  try { d.device = devDesc(r.getDevice()); } catch (e) {}
  try { d.rssi = r.getRssi(); } catch (e) {}
  try { d.tx_power = r.getTxPower(); } catch (e) {}
  try {
    var rec = r.getScanRecord();
    if (rec !== null) {
      d.record_hex = jbytesToHex(rec.getBytes());
      d.record_ascii = jbytesToAscii(rec.getBytes());
      d.device_name = s(rec.getDeviceName());
      d.advertise_flags = rec.getAdvertiseFlags();
      d.service_uuids = s(rec.getServiceUuids());
      d.manufacturer_data = rec.getManufacturerSpecificData ? s(rec.getManufacturerSpecificData()) : null;
    }
  } catch (e) {}
  return d;
}

// ===========================================================================
// 2. BluetoothGatt  (connect / discover / read / write / notify / mtu)
// ===========================================================================
function installGattHooks() {
  if (!CFG.HOOK_GATT) return;

  hooked('android.bluetooth.BluetoothGatt', 'connect',
    hookAll('android.bluetooth.BluetoothGatt', 'connect', function (self, args) {
      emit({ api: 'BluetoothGatt.connect', autoConnect: args.length ? args[0] : undefined, device: gattDevice(self) });
      return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'disconnect',
    hookAll('android.bluetooth.BluetoothGatt', 'disconnect', function (self) {
      emit({ api: 'BluetoothGatt.disconnect', device: gattDevice(self) }); return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'close',
    hookAll('android.bluetooth.BluetoothGatt', 'close', function (self) {
      emit({ api: 'BluetoothGatt.close', device: gattDevice(self) }); return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'discoverServices',
    hookAll('android.bluetooth.BluetoothGatt', 'discoverServices', function (self) {
      emit({ api: 'BluetoothGatt.discoverServices', device: gattDevice(self) }); return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'getServices',
    hookAll('android.bluetooth.BluetoothGatt', 'getServices', function (self) {
      var out = [];
      var r = this.getServices();
      try { for (var i = 0; i < r.size(); i++) out.push(serviceDesc(r.get(i))); } catch (e) {}
      emit({ api: 'BluetoothGatt.getServices', count: out.length, services: out });
      return { ret: r };
    }));

  hooked('android.bluetooth.BluetoothGatt', 'readCharacteristic',
    hookAll('android.bluetooth.BluetoothGatt', 'readCharacteristic', function (self, args) {
      emit({ api: 'BluetoothGatt.readCharacteristic', char: charDesc(args[0]), arg1: args.length > 1 ? args[1] : undefined });
      return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'writeCharacteristic',
    hookAll('android.bluetooth.BluetoothGatt', 'writeCharacteristic', function (self, args) {
      var rec = { api: 'BluetoothGatt.writeCharacteristic', device: gattDevice(self), char: charDesc(args[0]) };
      if (args.length > 1 && args[1] !== null && typeof args[1] !== 'number') {
        rec.write_value_hex = jbytesToHex(args[1]);
        var a = jbytesToAscii(args[1]); if (a !== undefined) rec.write_value_ascii = a;
      }
      if (args.length > 2) rec.write_type = args[2];
      emit(rec);
      return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'writeDescriptor',
    hookAll('android.bluetooth.BluetoothGatt', 'writeDescriptor', function (self, args) {
      var rec = { api: 'BluetoothGatt.writeDescriptor', device: gattDevice(self), desc: descDesc(args[0]) };
      if (args.length > 1 && args[1] !== null && typeof args[1] !== 'number') {
        rec.write_value_hex = jbytesToHex(args[1]);
        var a = jbytesToAscii(args[1]); if (a !== undefined) rec.write_value_ascii = a;
      }
      emit(rec);
      return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'readDescriptor',
    hookAll('android.bluetooth.BluetoothGatt', 'readDescriptor', function (self, args) {
      emit({ api: 'BluetoothGatt.readDescriptor', desc: descDesc(args[0]) });
      return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'setCharacteristicNotification',
    hookAll('android.bluetooth.BluetoothGatt', 'setCharacteristicNotification', function (self, args) {
      emit({ api: 'BluetoothGatt.setCharacteristicNotification', enable: args[1], char: charDesc(args[0]) });
      return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'requestMtu',
    hookAll('android.bluetooth.BluetoothGatt', 'requestMtu', function (self, args) {
      emit({ api: 'BluetoothGatt.requestMtu', mtu: args[0], device: gattDevice(self) });
      return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'requestConnectionPriority',
    hookAll('android.bluetooth.BluetoothGatt', 'requestConnectionPriority', function (self, args) {
      emit({ api: 'BluetoothGatt.requestConnectionPriority', priority: args[0] });
      return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'readRemoteRssi',
    hookAll('android.bluetooth.BluetoothGatt', 'readRemoteRssi', function () {
      emit({ api: 'BluetoothGatt.readRemoteRssi' }); return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'beginReliableWrite',
    hookAll('android.bluetooth.BluetoothGatt', 'beginReliableWrite', function () {
      emit({ api: 'BluetoothGatt.beginReliableWrite' }); return null;
    }));

  hooked('android.bluetooth.BluetoothGatt', 'executeReliableWrite',
    hookAll('android.bluetooth.BluetoothGatt', 'executeReliableWrite', function () {
      emit({ api: 'BluetoothGatt.executeReliableWrite' }); return null;
    }));
}

function gattDevice(self) {
  try { return devDesc(self.getDevice()); } catch (e) { return null; }
}

function serviceDesc(svc) {
  var d = {};
  try { d.uuid = uuidOf(svc); } catch (e) {}
  try {
    var chars = svc.getCharacteristics(), arr = [];
    for (var i = 0; i < chars.size(); i++) arr.push(charDesc(chars.get(i)));
    d.characteristics = arr;
  } catch (e) {}
  return d;
}

// ===========================================================================
// 3. BluetoothGattCallback  (inbound data path)
// ===========================================================================
function installGattCallbackHooks() {
  if (!CFG.HOOK_GATT_CALLBACK) return;

  var C = 'android.bluetooth.BluetoothGattCallback';

  hooked(C, 'onConnectionStateChange',
    hookAll(C, 'onConnectionStateChange', function (self, args) {
      emit({ api: 'GattCallback.onConnectionStateChange', status: args[1], new_state: args[2] });
      return null;
    }));

  hooked(C, 'onServicesDiscovered',
    hookAll(C, 'onServicesDiscovered', function (self, args) {
      emit({ api: 'GattCallback.onServicesDiscovered', status: args[1] });
      return null;
    }));

  hooked(C, 'onCharacteristicRead',
    hookAll(C, 'onCharacteristicRead', function (self, args) {
      var rec = { api: 'GattCallback.onCharacteristicRead', status: args[1] };
      if (args.length > 2 && typeof args[2] === 'number') rec.arg2 = args[2]; // API33 status/offset overload
      if (args.length > 3) { rec.value_hex = jbytesToHex(args[3]); var a = jbytesToAscii(args[3]); if (a !== undefined) rec.value_ascii = a; }
      try { rec.char = charDesc(args[0]); } catch (e) {}
      emit(rec);
      return null;
    }));

  hooked(C, 'onCharacteristicChanged',
    hookAll(C, 'onCharacteristicChanged', function (self, args) {
      var rec = { api: 'GattCallback.onCharacteristicChanged' };
      try { rec.char = charDesc(args[0]); } catch (e) {}
      if (args.length > 1 && args[1] !== null && typeof args[1] !== 'number') {
        rec.value_hex = jbytesToHex(args[1]);
        var a = jbytesToAscii(args[1]); if (a !== undefined) rec.value_ascii = a;
      }
      if (args.length > 2) rec.arg2 = args[2]; // API33 (char, value, status) style
      emit(rec);
      return null;
    }));

  hooked(C, 'onCharacteristicWrite',
    hookAll(C, 'onCharacteristicWrite', function (self, args) {
      var rec = { api: 'GattCallback.onCharacteristicWrite', status: args[1] };
      try { rec.char = charDesc(args[0]); } catch (e) {}
      emit(rec);
      return null;
    }));

  hooked(C, 'onDescriptorRead',
    hookAll(C, 'onDescriptorRead', function (self, args) {
      var rec = { api: 'GattCallback.onDescriptorRead', status: args[1] };
      try { rec.desc = descDesc(args[0]); } catch (e) {}
      if (args.length > 3) { rec.value_hex = jbytesToHex(args[3]); }
      emit(rec);
      return null;
    }));

  hooked(C, 'onDescriptorWrite',
    hookAll(C, 'onDescriptorWrite', function (self, args) {
      var rec = { api: 'GattCallback.onDescriptorWrite', status: args[1] };
      try { rec.desc = descDesc(args[0]); } catch (e) {}
      emit(rec);
      return null;
    }));

  hooked(C, 'onMtuChanged',
    hookAll(C, 'onMtuChanged', function (self, args) {
      emit({ api: 'GattCallback.onMtuChanged', mtu: args[1], status: args[2] });
      return null;
    }));

  hooked(C, 'onReadRemoteRssi',
    hookAll(C, 'onReadRemoteRssi', function (self, args) {
      emit({ api: 'GattCallback.onReadRemoteRssi', rssi: args[1], status: args[2] });
      return null;
    }));

  hooked(C, 'onReliableWriteCompleted',
    hookAll(C, 'onReliableWriteCompleted', function (self, args) {
      emit({ api: 'GattCallback.onReliableWriteCompleted', status: args[1] });
      return null;
    }));
}

// ===========================================================================
// 4. BluetoothDevice.connectGatt
// ===========================================================================
function installDeviceHooks() {
  if (!CFG.HOOK_DEVICE) return;

  hooked('android.bluetooth.BluetoothDevice', 'connectGatt',
    hookAll('android.bluetooth.BluetoothDevice', 'connectGatt', function (self, args) {
      // overloads: (Context, boolean, GattCallback[, int transport[, int phy[, Handler]]])
      var d = devDesc(self);
      var rec = {
        api: 'BluetoothDevice.connectGatt', device: d,
        arg_count: args.length,
        autoConnect: (args.length > 1 && typeof args[1] === 'boolean') ? args[1] : undefined,
        transport: (args.length > 3 && typeof args[3] === 'number') ? args[3] : undefined
      };
      emit(rec);
      return null;
    }));
}

// ===========================================================================
// 5. value accessors on Characteristic / Descriptor (older API data path)
// ===========================================================================
function installValueAccessorHooks() {
  if (!CFG.HOOK_VALUE_ACCESSORS) return;

  hooked('android.bluetooth.BluetoothGattCharacteristic', 'setValue',
    hookAll('android.bluetooth.BluetoothGattCharacteristic', 'setValue', function (self, args) {
      var rec = { api: 'BluetoothGattCharacteristic.setValue', char: uuidOf(self) };
      var v = args[0];
      if (v !== null && typeof v !== 'number' && typeof v !== 'boolean' && typeof v !== 'string') {
        rec.value_hex = jbytesToHex(v); var a = jbytesToAscii(v); if (a !== undefined) rec.value_ascii = a;
      } else { rec.literal = String(v); }
      emit(rec);
      return null;
    }));

  hooked('android.bluetooth.BluetoothGattCharacteristic', 'getValue',
    hookAll('android.bluetooth.BluetoothGattCharacteristic', 'getValue', function (self) {
      var r = this.getValue();
      if (r !== null) {
        var rec = { api: 'BluetoothGattCharacteristic.getValue', char: uuidOf(self), value_hex: jbytesToHex(r) };
        var a = jbytesToAscii(r); if (a !== undefined) rec.value_ascii = a;
        emit(rec);
      }
      return { ret: r };
    }));

  hooked('android.bluetooth.BluetoothGattDescriptor', 'setValue',
    hookAll('android.bluetooth.BluetoothGattDescriptor', 'setValue', function (self, args) {
      var rec = { api: 'BluetoothGattDescriptor.setValue', desc_uuid: uuidOf(self) };
      var v = args[0];
      if (v !== null && typeof v !== 'number' && typeof v !== 'boolean') {
        rec.value_hex = jbytesToHex(v); var a = jbytesToAscii(v); if (a !== undefined) rec.value_ascii = a;
      }
      emit(rec);
      return null;
    }));

  hooked('android.bluetooth.BluetoothGattDescriptor', 'getValue',
    hookAll('android.bluetooth.BluetoothGattDescriptor', 'getValue', function (self) {
      var r = this.getValue();
      if (r !== null) emit({ api: 'BluetoothGattDescriptor.getValue', desc_uuid: uuidOf(self), value_hex: jbytesToHex(r) });
      return { ret: r };
    }));
}

// ===========================================================================
// 6. adapter / manager state (helps correlate enable/disable with captures)
// ===========================================================================
function installAdapterHooks() {
  if (!CFG.HOOK_ADAPTER) return;
  hooked('android.bluetooth.BluetoothAdapter', 'getName',
    hookAll('android.bluetooth.BluetoothAdapter', 'getName', function (self) { return null; }));
  hooked('android.bluetooth.BluetoothManager', 'getAdapter',
    hookAll('android.bluetooth.BluetoothManager', 'getAdapter', function (self) {
      emit({ api: 'BluetoothManager.getAdapter', adapter: safeAdapterDesc(this.getAdapter()) });
      return null;
    }));
}

// ===========================================================================
// 7. Flutter MethodChannel (plugin layer bridge, plugin-agnostic)
// ===========================================================================
function installMethodChannelHooks() {
  if (!CFG.HOOK_METHODCHANNEL) return;
  var C = 'io.flutter.plugin.common.MethodChannel';
  // Release builds are R8-shrunk: the Flutter embedding classes are renamed
  // (io.flutter.embedding.android.a..x), so MethodChannel may not resolve by
  // name. That is expected and NOT an error -- the plugin-layer coverage is
  // provided by shared/flutter-plugin-probe.js instead.
  try { Java.use(C); } catch (e) {
    note('MethodChannel not resolvable by name on this obfuscated build ' +
         '(expected; plugin coverage via flutter-plugin-probe.js)');
    return;
  }
  hooked(C, 'invokeMethod',
    hookAll(C, 'invokeMethod', function (self, args) {
      var chan = safeChannelName(self);
      if (chan === null || !/ble|blue|bluetooth|scan|gatt/i.test(chan)) return null;
      emit({ api: 'MethodChannel.invokeMethod', channel: chan, method: s(args[0]), args: safeArgs(args[1]) });
      return null;
    }));
}

function safeChannelName(mc) {
  try { var f = mc.name; return f ? f.value : s(mc.getName()); } catch (e) {
    try { return s(mc.name); } catch (e2) { return null; }
  }
}
function safeArgs(a) {
  try { return a === null ? null : a.toString(); } catch (e) { return '<args>'; }
}

// ===========================================================================
// boot
// ===========================================================================
if (typeof Java === 'undefined') {
  note('Java bridge NOT available in this Frida runtime. Use Frida <=16.x (bundled ' +
       'Java bridge) or compile this agent with frida-java-bridge for Frida 17+.');
  note('platform BLE hooks NOT installed');
} else {
Java.perform(function () {
  note('=========================================================');
  note(' armorx-lab platform BLE hooks attaching');
  note(' android=' + (function () { try { return Java.androidVersion; } catch (e) { return '?'; } })());
  note('=========================================================');
  javaGuard(function () { installScanHooks(); }, 'scan');
  javaGuard(function () { installGattHooks(); }, 'gatt');
  javaGuard(function () { installGattCallbackHooks(); }, 'gatt-callback');
  javaGuard(function () { installDeviceHooks(); }, 'device');
  javaGuard(function () { installValueAccessorHooks(); }, 'value-accessors');
  javaGuard(function () { installAdapterHooks(); }, 'adapter');
  javaGuard(function () { installMethodChannelHooks(); }, 'methodchannel');
  note('all platform BLE hook groups installed');
  emit({ api: 'hooks-ready' });
});
}

function javaGuard(fn, label) {
  try { fn(); } catch (e) { note('group "' + label + '" failed: ' + e); }
}
