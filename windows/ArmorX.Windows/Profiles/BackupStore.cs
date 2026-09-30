using System.Security.Cryptography;
using System.Text.Json;
using ArmorX.Windows.Config;

namespace ArmorX.Windows.Profiles;

public sealed class ArmorXBackup
{
    public DateTimeOffset SavedUtc { get; set; } = DateTimeOffset.UtcNow;
    public string Reason { get; set; } = "pre-write";
    public string? DeviceModel { get; set; }
    public string? Firmware { get; set; }
    public string ConfigBase64 { get; set; } = string.Empty;
    public string? ConfigSha256 { get; set; }
    public byte[] GetConfigBytes() => Convert.FromBase64String(ConfigBase64);
}

public sealed class BackupStore
{
    private readonly JsonSerializerOptions _json = new() { WriteIndented = true };
    public string DirectoryPath { get; } = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "ArmorX", "Backups");

    public BackupStore() => Directory.CreateDirectory(DirectoryPath);

    public async Task<string> SaveAsync(
        ArmorXConfig144 config,
        string? deviceModel,
        string? firmware,
        string reason)
    {
        var backup = new ArmorXBackup
        {
            SavedUtc = DateTimeOffset.UtcNow,
            Reason = reason,
            DeviceModel = deviceModel,
            Firmware = firmware,
            ConfigBase64 = Convert.ToBase64String(config.ToArray()),
            ConfigSha256 = Hash(config.ToArray())
        };

        var safeReason = string.Concat(reason.Select(ch =>
            Path.GetInvalidFileNameChars().Contains(ch) ? '_' : ch));
        var file = $"{backup.SavedUtc:yyyyMMdd-HHmmss-fff}-{safeReason}-crc-{config.StoredCrc:X4}.json";
        var path = Path.Combine(DirectoryPath, file);
        await File.WriteAllTextAsync(path, JsonSerializer.Serialize(backup, _json));
        return path;
    }

    public async Task<ArmorXBackup?> LoadLatestAsync()
    {
        foreach (var path in Directory.EnumerateFiles(DirectoryPath, "*.json")
                     .OrderByDescending(File.GetLastWriteTimeUtc))
        {
            try
            {
                var item = JsonSerializer.Deserialize<ArmorXBackup>(
                    await File.ReadAllTextAsync(path), _json);
                if (item is null) continue;
                var bytes = item.GetConfigBytes();
                if (bytes.Length != ArmorXConfig144.Size) continue;
                var config = new ArmorXConfig144(bytes);
                if (!config.CrcValid) continue;
                var hash = Hash(bytes);
                if (!string.IsNullOrWhiteSpace(item.ConfigSha256) &&
                    !string.Equals(item.ConfigSha256, hash, StringComparison.OrdinalIgnoreCase))
                    continue;
                item.ConfigSha256 = hash;
                return item;
            }
            catch
            {
                // Ignore a damaged backup and try the next one.
            }
        }

        return null;
    }

    private static string Hash(byte[] bytes) =>
        Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
}
