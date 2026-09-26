using System.Text.Json;
using ArmorX.Windows.Config;

namespace ArmorX.Windows.Profiles;

public sealed class ProfileStore
{
    private readonly JsonSerializerOptions _json = new() { WriteIndented = true };
    public string DirectoryPath { get; } = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ArmorX", "Profiles");

    public ProfileStore() => Directory.CreateDirectory(DirectoryPath);

    public async Task SaveAsync(string name, ArmorXConfig144 config, string? deviceModel, string? firmware)
    {
        if (string.IsNullOrWhiteSpace(name))
            throw new ArgumentException("Profile name is required.", nameof(name));

        var profile = new ArmorXProfile
        {
            Name = name.Trim(),
            SavedUtc = DateTimeOffset.UtcNow,
            DeviceModel = deviceModel,
            Firmware = firmware,
            ConfigBase64 = Convert.ToBase64String(config.ToArray())
        };

        await File.WriteAllTextAsync(PathFor(profile.Name), JsonSerializer.Serialize(profile, _json));
    }

    public async Task<ArmorXProfile> LoadAsync(string name)
    {
        var json = await File.ReadAllTextAsync(PathFor(name));
        var profile = JsonSerializer.Deserialize<ArmorXProfile>(json, _json) ?? throw new InvalidDataException("Invalid profile JSON.");
        if (profile.GetConfigBytes().Length != ArmorXConfig144.Size)
            throw new InvalidDataException("Profile does not contain a 144-byte ARMOR-X Pro configuration.");
        return profile;
    }

    public async Task<IReadOnlyList<ArmorXProfile>> ListAsync()
    {
        var result = new List<ArmorXProfile>();
        foreach (var path in Directory.EnumerateFiles(DirectoryPath, "*.json"))
        {
            try
            {
                var profile = JsonSerializer.Deserialize<ArmorXProfile>(await File.ReadAllTextAsync(path), _json);
                if (profile is not null) result.Add(profile);
            }
            catch { }
        }
        return result.OrderByDescending(x => x.SavedUtc).ToArray();
    }

    private string PathFor(string name)
    {
        var safe = string.Concat(name.Trim().Select(ch => Path.GetInvalidFileNameChars().Contains(ch) ? '_' : ch));
        if (string.IsNullOrWhiteSpace(safe)) safe = "Profile";
        return Path.Combine(DirectoryPath, safe + ".json");
    }
}
