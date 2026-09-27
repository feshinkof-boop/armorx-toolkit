# RESEARCH AVD (instrumented / debug device)

Everything invasive lives here: Frida server, `-writable-system`, extra debug
props, and the virtual-Bluetooth bridge. See `../README.md` for the
REFERENCE-vs-RESEARCH rationale and the ABI table.

## Devices created

| AVD               | System image                        | `ro.product.cpu.abilist`                       | ARM translation |
|-------------------|-------------------------------------|------------------------------------------------|-----------------|
| `armorx_res_api33`| `system-images;android-33;google_apis;x86_64` | `x86_64`                            | **no**          |
| `armorx_res_api30`| `system-images;android-30;google_apis;x86_64` | `x86_64,x86,arm64-v8a,armeabi-v7a,armeabi` | **yes** (`libndk_translation.so`) |

Emulator version verified on this host: **37.1.11.0**, KVM usable
(`emulator -accel-check` → `KVM (version 12) is installed and usable`).

## Scripts

```bash
./create-research-avd.sh                     # create both research AVDs
./launch-research.sh armorx_res_api33 5554   # boot android-13 research device
./launch-research.sh armorx_res_api30 5556   # boot android-11 (ARM translation)
./install-app.sh 2.23 emulator-5554          # install a build (split-aware)
./push-frida-server.sh emulator-5554         # start frida-server in the guest
```

## Virtual Bluetooth: RootCanal / netsim

The Android Emulator implements virtual Bluetooth with **RootCanal** (the virtual
controller) fronted by **Netsim** (`netsimd`, the multi-client packet router).
Emulator **33.1.4.0 or later** supports this; on 37.1.11 it is enabled
automatically — the boot log states:

```
INFO | Activated packet streamer for bluetooth emulation
```

and a `netsimd` process appears on the host. The guest reports the emulated
adapter (`dumpsys bluetooth_manager`: `enabled: true, state: ON,
address BB:BB:BB:00:00:01`).

### Emulator command lines

```bash
# let the emulator start / find netsim itself (default behaviour)
emulator -avd armorx_res_api33 -packet-streamer-endpoint default

# route the guest HCI stream through an external packet streamer (e.g. a Bumble
# controller-mode bridge) instead of netsim
emulator -avd Tiramisu -packet-streamer-endpoint localhost:8877

# additional netsim tuning
emulator -avd <name> -netsim-args <arg> ...
```

Related emulator options present in `emulator -help`: `-packet-streamer-endpoint`,
`-netsim-args`. The legacy `-forward-vhci` flag of older emulators is gone.

### Ports observed on this host (emulator 37.1.11, one AVD running)

| Port        | Owner     | Meaning                                                        |
|-------------|-----------|----------------------------------------------------------------|
| `127.0.0.1:6402` | `netsimd` | RootCanal HCI server port (RootCanal default `--hci_port 6402`) |
| dynamic (e.g. `35335`) | `netsimd` | netsim **gRPC** control port (published into `netsim.ini`) |
| `5554/5555` | `qemu-system-x86` | emulator console / adb                         |

RootCanal's full default port set (standalone build) is
`6401` test · `6402` HCI · `6403` link (BR/EDR) · `6404` link BLE.

### netsim discovery file

The emulator writes the gRPC port to `netsim.ini`:

```
$ cat "$TMPDIR/netsim.ini"          # here: /home/salamanka/.hermes/cache/scratch/netsim.ini
grpc.port=35335
```

Each AVD also gets `<avd>.avd/netsim.ini` containing the emulated BT address:

```
bluetooth.address = BB:BB:BB:00:00:01
```

Bumble's `android-netsim` transport auto-discovers this file, but it searches
`XDG_RUNTIME_DIR` first on Linux, whereas the emulator wrote it to `TMPDIR`.
Either pass the port explicitly, or unset `XDG_RUNTIME_DIR` for the Bumble process.

### Bumble transport strings (verified with bumble 0.0.235)

| Transport spec                              | Mode        | Use                                              |
|---------------------------------------------|-------------|--------------------------------------------------|
| `android-netsim`                            | host        | connect to netsim using the port from `netsim.ini` |
| `android-netsim:localhost:35335`            | host        | connect to netsim at an explicit address         |
| `android-netsim:localhost:8877,name=bumble1`| host        | named chip instance (needed when connecting >1)  |
| `android-netsim:_:8877,mode=controller`     | controller  | act as a netsim server (bridge a real dongle in) |

Verified end-to-end on this host:

```bash
# host stack -> emulator's virtual RootCanal controller
$LAB_ROOT/.venv-bumble/bin/python -m bumble.apps.controller_info android-netsim:localhost:35335
# -> Version: Manufacturer: Google, HCI Version: BLUETOOTH_CORE_5_3
#    Public Address: DA:4C:10:DE:00:00
```

Bridge a physical dongle into the emulator (needs a USB BT controller — **not**
done here, and radio operations are out of scope for phase 5/7/8):

```bash
bumble-hci-bridge android-netsim:_:8877,mode=controller usb:0
emulator -avd <name> -packet-streamer-endpoint localhost:8877
```

## Running the arm64-only builds

`armorx_res_api30` will *install* 2.24 and 4.0.8 (they are arm64-only) but they
crash immediately in binary translation:

```
E ndk_translation: Undefined instruction 0x5ea1b801 at 0x00007d6593de0918
F libc    : Fatal signal 4 (SIGILL) ... in tid 4813 (1.ui), pid 4692 (jiang.bigbigwon)
  #01 pc ... /system/lib64/libndk_translation.so (Decoder<...>::DecodeSimdScalarTwoRegMisc())
```

That is Flutter's arm64 code hitting an instruction `libndk_translation` cannot
decode. See `results/final/avd-frida-readiness.md` for the per-version verdicts.
