namespace ArmorX.Windows.Profiles;

public sealed class ArmorXProfile
{
    public string Name { get; set; } = "Profile";
    public DateTimeOffset SavedUtc { get; set; } = DateTimeOffset.UtcNow;
    public string? DeviceModel { get; set; }
    public string? Firmware { get; set; }
    public string ConfigBase64 { get; set; } = string.Empty;

    public byte[] GetConfigBytes() => Convert.FromBase64String(ConfigBase64);
}
