using System.Collections.Concurrent;
using Windows.Devices.Bluetooth;
using Windows.Devices.Bluetooth.Advertisement;
using Windows.Devices.Bluetooth.GenericAttributeProfile;
using Windows.Devices.Enumeration;
using Windows.Foundation;
using Windows.Storage.Streams;

namespace ArmorX.Windows.Bluetooth;

public sealed class ArmorXBleTransport : IAsyncDisposable
{
    public static readonly Guid VendorServiceUuid = Guid.Parse("00000000-0000-1000-8000-00805f9b34fb");
    public static readonly Guid WriteUuid = Uuid16(0xFFE1);
    public static readonly Guid NotifyUuid = Uuid16(0xFFE2);
    public static readonly Guid ModelUuid = Uuid16(0x2A24);
    public static readonly Guid FirmwareUuid = Uuid16(0x2A26);
    public static readonly Guid BatteryUuid = Uuid16(0x2A19);

    private const string BluetoothLeAepSelector = "System.Devices.Aep.ProtocolId:=\"{BB7BB05E-5972-42B5-94FC-76EAA7084D49}\"";
    private static readonly string[] AepProperties =
    {
        "System.Devices.Aep.DeviceAddress",
        "System.Devices.Aep.SignalStrength",
        "System.Devices.Aep.IsConnected",
        "System.Devices.Aep.Bluetooth.Le.IsConnectable"
    };

    private readonly ConcurrentDictionary<ulong, BleDiscoveredDevice> _scanCache = new();
    private readonly ConcurrentDictionary<string, ulong> _aepAddressById = new(StringComparer.OrdinalIgnoreCase);
    private BluetoothLEAdvertisementWatcher? _watcher;
    private DeviceWatcher? _aepWatcher;
    private BluetoothLEDevice? _device;
    private readonly List<GattDeviceService> _services = new();
    private readonly Dictionary<Guid, GattCharacteristic> _characteristics = new();
    private GattCharacteristic? _write;
    private GattCharacteristic? _notify;

    public event EventHandler<BleDiscoveredDevice>? DeviceSeen;
    public event EventHandler<byte[]>? PacketReceived;
    public event EventHandler<string>? Log;
    public event EventHandler<bool>? ConnectionChanged;

    public bool IsConnected => _device?.ConnectionStatus == BluetoothConnectionStatus.Connected && _write is not null && _notify is not null;
    public IReadOnlyList<BleDiscoveredDevice> ScanSnapshot => _scanCache.Values.OrderByDescending(x => x.Rssi).ToArray();

    public static bool LooksLikeArmorXName(string? name)
    {
        if (string.IsNullOrWhiteSpace(name)) return false;
        return name.Contains("ARMOR-X", StringComparison.OrdinalIgnoreCase)
            || name.Contains("ARMORX", StringComparison.OrdinalIgnoreCase)
            || name.Contains("ZJ-XT", StringComparison.OrdinalIgnoreCase)
            || name.Contains("BIGBIG WON", StringComparison.OrdinalIgnoreCase)
            || name.Contains("BIGBIGWON", StringComparison.OrdinalIgnoreCase);
    }

    public async Task<string> GetAdapterStatusAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            var adapter = await AwaitWithTimeoutAsync(async () => await BluetoothAdapter.GetDefaultAsync(), TimeSpan.FromSeconds(4), cancellationToken);
            if (adapter is null) return "Bluetooth adapter not found";
            try
            {
                var radio = await AwaitWithTimeoutAsync(async () => await adapter.GetRadioAsync(), TimeSpan.FromSeconds(4), cancellationToken);
                return radio.State == global::Windows.Devices.Radios.RadioState.On ? "Bluetooth ready" : $"Bluetooth radio is {radio.State}";
            }
            catch
            {
                return adapter.IsCentralRoleSupported ? "Bluetooth ready" : "Bluetooth LE central role not supported";
            }
        }
        catch (Exception ex)
        {
            return "Bluetooth check failed: " + ex.Message;
        }
    }

    public void EnsurePersistentDiscovery(bool clearCache = false)
    {
        if (clearCache) _scanCache.Clear();
        EnsureAdvertisementWatcher();
        EnsureAepWatcher();
    }

    private void EnsureAdvertisementWatcher()
    {
        if (_watcher?.Status == BluetoothLEAdvertisementWatcherStatus.Started) return;
        if (_watcher is not null)
        {
            try { _watcher.Received -= OnAdvertisement; } catch { }
            try { _watcher.Stop(); } catch { }
        }
        _watcher = new BluetoothLEAdvertisementWatcher { ScanningMode = BluetoothLEScanningMode.Active };
        _watcher.Received += OnAdvertisement;
        _watcher.Start();
        EmitLog("BLE discovery started.");
    }

    private void EnsureAepWatcher()
    {
        if (_aepWatcher?.Status is DeviceWatcherStatus.Started or DeviceWatcherStatus.EnumerationCompleted) return;
        if (_aepWatcher is not null)
        {
            DetachAepWatcher(_aepWatcher);
            try { _aepWatcher.Stop(); } catch { }
        }
        _aepWatcher = DeviceInformation.CreateWatcher(BluetoothLeAepSelector, AepProperties, DeviceInformationKind.AssociationEndpoint);
        _aepWatcher.Added += OnAepAdded;
        _aepWatcher.Updated += OnAepUpdated;
        _aepWatcher.Removed += OnAepRemoved;
        _aepWatcher.Start();
    }

    private BleDiscoveredDevice Upsert(ulong address, string? name, short rssi, string source)
    {
        name ??= string.Empty;
        var item = _scanCache.AddOrUpdate(address,
            a => new BleDiscoveredDevice(a, name, rssi, source),
            (_, existing) =>
            {
                if (!string.IsNullOrWhiteSpace(name)) existing.Name = name;
                if (rssi != short.MinValue) existing.Rssi = rssi;
                if (!existing.DiscoverySource.Contains(source, StringComparison.OrdinalIgnoreCase))
                    existing.DiscoverySource = existing.DiscoverySource == "unknown" ? source : existing.DiscoverySource + "+" + source;
                existing.LastSeenUtc = DateTimeOffset.UtcNow;
                return existing;
            });
        DeviceSeen?.Invoke(this, item);
        return item;
    }

    private void OnAdvertisement(BluetoothLEAdvertisementWatcher sender, BluetoothLEAdvertisementReceivedEventArgs args) =>
        Upsert(args.BluetoothAddress, args.Advertisement.LocalName, args.RawSignalStrengthInDBm, "live");

    private void OnAepAdded(DeviceWatcher sender, DeviceInformation info)
    {
        if (!TryGetAepAddress(info.Properties, out var address)) return;
        _aepAddressById[info.Id] = address;
        Upsert(address, info.Name, ReadAepRssi(info.Properties), "Windows");
    }

    private void OnAepUpdated(DeviceWatcher sender, DeviceInformationUpdate update)
    {
        if (!_aepAddressById.TryGetValue(update.Id, out var address) && !TryGetAepAddress(update.Properties, out address)) return;
        _aepAddressById[update.Id] = address;
        var name = _scanCache.TryGetValue(address, out var existing) ? existing.Name : string.Empty;
        Upsert(address, name, ReadAepRssi(update.Properties), "Windows");
    }

    private void OnAepRemoved(DeviceWatcher sender, DeviceInformationUpdate update) => _aepAddressById.TryRemove(update.Id, out _);

    private static bool TryGetAepAddress(IReadOnlyDictionary<string, object> properties, out ulong address)
    {
        address = 0;
        if (!properties.TryGetValue("System.Devices.Aep.DeviceAddress", out var raw) || raw is null) return false;
        var compact = raw.ToString()?.Replace(":", string.Empty).Replace("-", string.Empty);
        return !string.IsNullOrWhiteSpace(compact) && ulong.TryParse(compact, System.Globalization.NumberStyles.HexNumber, null, out address);
    }

    private static short ReadAepRssi(IReadOnlyDictionary<string, object> properties)
    {
        if (!properties.TryGetValue("System.Devices.Aep.SignalStrength", out var raw) || raw is null) return short.MinValue;
        try { return Convert.ToInt16(raw, System.Globalization.CultureInfo.InvariantCulture); } catch { return short.MinValue; }
    }

    private void DetachAepWatcher(DeviceWatcher watcher)
    {
        watcher.Added -= OnAepAdded;
        watcher.Updated -= OnAepUpdated;
        watcher.Removed -= OnAepRemoved;
    }

    public async Task<int> EnumerateWindowsCachedArmorXAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            var infos = await AwaitWithTimeoutAsync(async () => await DeviceInformation.FindAllAsync(BluetoothLEDevice.GetDeviceSelector()), TimeSpan.FromSeconds(8), cancellationToken);
            var count = 0;
            foreach (var info in infos)
            {
                if (!LooksLikeArmorXName(info.Name)) continue;
                BluetoothLEDevice? cached = null;
                try
                {
                    cached = await AwaitWithTimeoutAsync(async () => await BluetoothLEDevice.FromIdAsync(info.Id), TimeSpan.FromSeconds(4), cancellationToken);
                    if (cached is null) continue;
                    Upsert(cached.BluetoothAddress, string.IsNullOrWhiteSpace(cached.Name) ? info.Name : cached.Name, short.MinValue, "cache");
                    count++;
                }
                catch { }
                finally { cached?.Dispose(); }
            }
            return count;
        }
        catch { return 0; }
    }

    public async Task ConnectAsync(ulong address, CancellationToken cancellationToken = default)
    {
        await DisconnectAsync();
        EnsurePersistentDiscovery();
        EmitLog($"Opening ARMOR-X at 0x{address:X12}...");

        _device = await AwaitWithTimeoutAsync(async () => await BluetoothLEDevice.FromBluetoothAddressAsync(address), TimeSpan.FromSeconds(8), cancellationToken);
        if (_device is null) throw new InvalidOperationException("Windows could not open the ARMOR-X Pro. Turn it on and try again.");
        _device.ConnectionStatusChanged += OnConnectionStatusChanged;

        var serviceResult = await AwaitWithTimeoutAsync(async () => await _device.GetGattServicesAsync(BluetoothCacheMode.Uncached), TimeSpan.FromSeconds(8), cancellationToken);
        if (serviceResult.Status != GattCommunicationStatus.Success) throw new InvalidOperationException($"GATT service discovery failed: {serviceResult.Status}.");
        _services.AddRange(serviceResult.Services);

        foreach (var service in _services)
        {
            var chars = await AwaitWithTimeoutAsync(async () => await service.GetCharacteristicsAsync(BluetoothCacheMode.Uncached), TimeSpan.FromSeconds(6), cancellationToken);
            if (chars.Status != GattCommunicationStatus.Success) continue;
            foreach (var ch in chars.Characteristics) _characteristics.TryAdd(ch.Uuid, ch);
        }

        var vendor = _services.FirstOrDefault(x => x.Uuid == VendorServiceUuid) ?? throw new InvalidOperationException("ARMOR-X vendor BLE service was not found.");
        var vendorChars = await AwaitWithTimeoutAsync(async () => await vendor.GetCharacteristicsAsync(BluetoothCacheMode.Uncached), TimeSpan.FromSeconds(6), cancellationToken);
        if (vendorChars.Status != GattCommunicationStatus.Success) throw new InvalidOperationException("ARMOR-X vendor characteristics could not be opened.");

        _write = vendorChars.Characteristics.FirstOrDefault(x => x.Uuid == WriteUuid) ?? throw new InvalidOperationException("ARMOR-X write characteristic FFE1 was not found.");
        _notify = vendorChars.Characteristics.FirstOrDefault(x => x.Uuid == NotifyUuid) ?? throw new InvalidOperationException("ARMOR-X notify characteristic FFE2 was not found.");
        _notify.ValueChanged += OnNotification;

        var notifyStatus = await AwaitWithTimeoutAsync(async () => await _notify.WriteClientCharacteristicConfigurationDescriptorAsync(GattClientCharacteristicConfigurationDescriptorValue.Notify), TimeSpan.FromSeconds(6), cancellationToken);
        if (notifyStatus != GattCommunicationStatus.Success) throw new InvalidOperationException($"Enabling ARMOR-X notifications failed: {notifyStatus}.");

        EmitLog("ARMOR-X BLE connection ready.");
        ConnectionChanged?.Invoke(this, true);
    }

    public async Task DisconnectAsync()
    {
        if (_notify is not null)
        {
            try
            {
                _notify.ValueChanged -= OnNotification;
                await AwaitWithTimeoutAsync(async () => await _notify.WriteClientCharacteristicConfigurationDescriptorAsync(GattClientCharacteristicConfigurationDescriptorValue.None), TimeSpan.FromSeconds(2), CancellationToken.None);
            }
            catch { }
        }
        _write = null;
        _notify = null;
        _characteristics.Clear();
        foreach (var service in _services) service.Dispose();
        _services.Clear();
        if (_device is not null)
        {
            _device.ConnectionStatusChanged -= OnConnectionStatusChanged;
            _device.Dispose();
            _device = null;
        }
        ConnectionChanged?.Invoke(this, false);
    }

    public async Task WriteAsync(ReadOnlyMemory<byte> data, CancellationToken cancellationToken = default)
    {
        var write = _write ?? throw new InvalidOperationException("ARMOR-X is not connected.");
        using var writer = new DataWriter();
        writer.WriteBytes(data.ToArray());
        var status = await AwaitWithTimeoutAsync(async () => await write.WriteValueAsync(writer.DetachBuffer(), GattWriteOption.WriteWithoutResponse), TimeSpan.FromSeconds(5), cancellationToken);
        if (status != GattCommunicationStatus.Success) throw new IOException($"BLE write failed: {status}.");
    }

    public async Task<byte[]?> ReadCharacteristicAsync(Guid uuid, CancellationToken cancellationToken = default)
    {
        if (!_characteristics.TryGetValue(uuid, out var characteristic))
        {
            foreach (var service in _services)
            {
                var result = await AwaitWithTimeoutAsync(async () => await service.GetCharacteristicsForUuidAsync(uuid, BluetoothCacheMode.Uncached), TimeSpan.FromSeconds(5), cancellationToken);
                if (result.Status != GattCommunicationStatus.Success || result.Characteristics.Count == 0) continue;
                characteristic = result.Characteristics[0];
                _characteristics[uuid] = characteristic;
                break;
            }
        }
        if (characteristic is null) return null;
        var read = await AwaitWithTimeoutAsync(async () => await characteristic.ReadValueAsync(BluetoothCacheMode.Uncached), TimeSpan.FromSeconds(5), cancellationToken);
        if (read.Status != GattCommunicationStatus.Success) return null;
        return BufferToBytes(read.Value);
    }

    private void OnNotification(GattCharacteristic sender, GattValueChangedEventArgs args)
    {
        try { PacketReceived?.Invoke(this, BufferToBytes(args.CharacteristicValue)); }
        catch (Exception ex) { EmitLog("Notification decode failed: " + ex.Message); }
    }

    private void OnConnectionStatusChanged(BluetoothLEDevice sender, object args)
    {
        var connected = sender.ConnectionStatus == BluetoothConnectionStatus.Connected;
        EmitLog($"Connection status: {sender.ConnectionStatus}");
        ConnectionChanged?.Invoke(this, connected);
    }

    private static byte[] BufferToBytes(IBuffer buffer)
    {
        using var reader = DataReader.FromBuffer(buffer);
        var data = new byte[reader.UnconsumedBufferLength];
        reader.ReadBytes(data);
        return data;
    }

    private static async Task<T> AwaitWithTimeoutAsync<T>(Func<Task<T>> operation, TimeSpan timeout, CancellationToken cancellationToken)
    {
        try { return await operation().WaitAsync(timeout, cancellationToken); }
        catch (TimeoutException) { throw new TimeoutException("Bluetooth operation timed out. The ARMOR-X Pro may have powered off or gone to sleep."); }
    }

    private async Task StopDiscoveryAsync()
    {
        if (_watcher is not null)
        {
            try { _watcher.Received -= OnAdvertisement; _watcher.Stop(); } catch { }
            _watcher = null;
        }
        if (_aepWatcher is not null)
        {
            try { DetachAepWatcher(_aepWatcher); _aepWatcher.Stop(); } catch { }
            _aepWatcher = null;
        }
        await Task.CompletedTask;
    }

    public static Guid Uuid16(ushort value) => Guid.Parse($"0000{value:x4}-0000-1000-8000-00805f9b34fb");
    private void EmitLog(string message) => Log?.Invoke(this, message);

    public async ValueTask DisposeAsync()
    {
        await DisconnectAsync();
        await StopDiscoveryAsync();
    }
}

