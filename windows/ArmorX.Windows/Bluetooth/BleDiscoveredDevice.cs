using ArmorX.Windows.Infrastructure;

namespace ArmorX.Windows.Bluetooth;

public sealed class BleDiscoveredDevice : ObservableObject
{
    private string _name;
    private short _rssi;
    private string _discoverySource;
    private DateTimeOffset _lastSeenUtc;

    public BleDiscoveredDevice(ulong address, string name, short rssi, string discoverySource = "unknown")
    {
        Address = address;
        _name = name;
        _rssi = rssi;
        _discoverySource = discoverySource;
        _lastSeenUtc = DateTimeOffset.UtcNow;
    }

    public ulong Address { get; }
    public string AddressText => string.Join(":", Enumerable.Range(0, 6)
        .Select(i => ((Address >> ((5 - i) * 8)) & 0xFF).ToString("X2")));

    public string Name { get => _name; set => SetProperty(ref _name, value); }
    public short Rssi { get => _rssi; set => SetProperty(ref _rssi, value); }
    public string DiscoverySource { get => _discoverySource; set => SetProperty(ref _discoverySource, value); }
    public DateTimeOffset LastSeenUtc { get => _lastSeenUtc; set => SetProperty(ref _lastSeenUtc, value); }

    public override string ToString() => $"{(string.IsNullOrWhiteSpace(Name) ? "BLE device" : Name)} [{AddressText}]";
}
