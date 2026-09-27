using System.Text.Json;
using ArmorX.Windows.Config;

namespace ArmorX.Windows.Profiles;

public sealed class ProfileStore
{
    private readonly JsonSerializerOptions _json = new() { WriteIndented = true };
    public string DirectoryPath { get; } = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "ArmorX", "Profiles");

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

        await WriteProfileAsync(profile, overwrite: true);
    }

    public async Task<ArmorXProfile> LoadAsync(string name) =>
        ValidateProfile(JsonSerializer.Deserialize<ArmorXProfile>(
            await File.ReadAllTextAsync(PathFor(name)), _json));

    public async Task<IReadOnlyList<ArmorXProfile>> ListAsync()
    {
        var result = new List<ArmorXProfile>();
        foreach (var path in Directory.EnumerateFiles(DirectoryPath, "*.json"))
        {
            try
            {
                var profile = ValidateProfile(JsonSerializer.Deserialize<ArmorXProfile>(
                    await File.ReadAllTextAsync(path), _json));
                result.Add(profile);
            }
            catch
            {
                // A damaged or unrelated JSON file should not break the profile list.
            }
        }

        return result.OrderByDescending(x => x.SavedUtc).ToArray();
    }

    public async Task RenameAsync(string existingName, string newName)
    {
        newName = NormalizeName(newName);
        var oldPath = PathFor(existingName);
        var newPath = PathFor(newName);
        if (!PathsEqual(oldPath, newPath) && File.Exists(newPath))
            throw new IOException($"A profile named '{newName}' already exists.");

        var profile = await LoadAsync(existingName);
        profile.Name = newName;
        profile.SavedUtc = DateTimeOffset.UtcNow;
        await File.WriteAllTextAsync(newPath, JsonSerializer.Serialize(profile, _json));

        if (!PathsEqual(oldPath, newPath) && File.Exists(oldPath))
            File.Delete(oldPath);
    }

    public async Task DuplicateAsync(string existingName, string newName)
    {
        newName = NormalizeName(newName);
        var path = PathFor(newName);
        if (File.Exists(path))
            throw new IOException($"A profile named '{newName}' already exists.");

        var profile = await LoadAsync(existingName);
        profile.Name = newName;
        profile.SavedUtc = DateTimeOffset.UtcNow;
        await File.WriteAllTextAsync(path, JsonSerializer.Serialize(profile, _json));
    }

    public Task DeleteAsync(string name)
    {
        var path = PathFor(name);
        if (File.Exists(path)) File.Delete(path);
        return Task.CompletedTask;
    }

    public async Task ExportAsync(string name, string destinationPath)
    {
        var profile = await LoadAsync(name);
        await File.WriteAllTextAsync(destinationPath, JsonSerializer.Serialize(profile, _json));
    }

    public async Task<ArmorXProfile> ImportAsync(string sourcePath)
    {
        var imported = ValidateProfile(JsonSerializer.Deserialize<ArmorXProfile>(
            await File.ReadAllTextAsync(sourcePath), _json));

        var uniqueName = UniqueName(imported.Name);
        imported.Name = uniqueName;
        imported.SavedUtc = DateTimeOffset.UtcNow;
        await WriteProfileAsync(imported, overwrite: false);
        return imported;
    }

    private async Task WriteProfileAsync(ArmorXProfile profile, bool overwrite)
    {
        profile.Name = NormalizeName(profile.Name);
        if (profile.GetConfigBytes().Length != ArmorXConfig144.Size)
            throw new InvalidDataException("Profile does not contain a 144-byte ARMOR-X Pro configuration.");

        var path = PathFor(profile.Name);
        if (!overwrite && File.Exists(path))
            throw new IOException($"A profile named '{profile.Name}' already exists.");

        await File.WriteAllTextAsync(path, JsonSerializer.Serialize(profile, _json));
    }

    private static ArmorXProfile ValidateProfile(ArmorXProfile? profile)
    {
        if (profile is null) throw new InvalidDataException("Invalid profile JSON.");
        profile.Name = NormalizeName(profile.Name);
        byte[] bytes;
        try { bytes = profile.GetConfigBytes(); }
        catch (Exception ex) { throw new InvalidDataException("Profile config data is not valid Base64.", ex); }

        if (bytes.Length != ArmorXConfig144.Size)
            throw new InvalidDataException("Profile does not contain a 144-byte ARMOR-X Pro configuration.");

        return profile;
    }

    private string UniqueName(string baseName)
    {
        baseName = NormalizeName(baseName);
        if (!File.Exists(PathFor(baseName))) return baseName;
        for (var i = 2; i < 10000; i++)
        {
            var candidate = $"{baseName} ({i})";
            if (!File.Exists(PathFor(candidate))) return candidate;
        }

        throw new IOException("Could not create a unique imported profile name.");
    }

    private static string NormalizeName(string name)
    {
        var trimmed = name.Trim();
        if (string.IsNullOrWhiteSpace(trimmed))
            throw new ArgumentException("Profile name is required.", nameof(name));
        return trimmed;
    }

    private string PathFor(string name)
    {
        var safe = string.Concat(NormalizeName(name)
            .Select(ch => Path.GetInvalidFileNameChars().Contains(ch) ? '_' : ch));
        if (string.IsNullOrWhiteSpace(safe)) safe = "Profile";
        return Path.Combine(DirectoryPath, safe + ".json");
    }

    private static bool PathsEqual(string a, string b) =>
        string.Equals(Path.GetFullPath(a), Path.GetFullPath(b), StringComparison.OrdinalIgnoreCase);
}
