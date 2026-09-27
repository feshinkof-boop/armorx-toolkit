from pathlib import Path

ROOT = Path("windows/ArmorX.Windows")

profile_store = r'''
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
        profile ??= throw new InvalidDataException("Invalid profile JSON.");
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
'''

diagnostics = r'''
using System.Reflection;
using System.Text;

namespace ArmorX.Windows.Infrastructure;

public sealed class UserDiagnosticLog
{
    private readonly object _gate = new();
    private readonly Queue<string> _entries = new();
    private const int MaxEntries = 300;

    public void Add(string message)
    {
        var line = $"{DateTimeOffset.Now:yyyy-MM-dd HH:mm:ss zzz}  {message}";
        lock (_gate)
        {
            _entries.Enqueue(line);
            while (_entries.Count > MaxEntries) _entries.Dequeue();
        }
    }

    public async Task ExportAsync(
        string path,
        string? model,
        string? firmware,
        string connectionState,
        string safetyState)
    {
        string[] entries;
        lock (_gate) entries = _entries.ToArray();

        var info = Assembly.GetExecutingAssembly()
            .GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion
            ?? Assembly.GetExecutingAssembly().GetName().Version?.ToString()
            ?? "unknown";

        var sb = new StringBuilder();
        sb.AppendLine("ArmorX Windows end-user diagnostic report");
        sb.AppendLine("=========================================");
        sb.AppendLine($"Generated: {DateTimeOffset.Now:O}");
        sb.AppendLine($"App version: {info}");
        sb.AppendLine($"OS: {Environment.OSVersion}");
        sb.AppendLine($".NET: {Environment.Version}");
        sb.AppendLine($"Device model: {model ?? "-"}");
        sb.AppendLine($"Firmware: {firmware ?? "-"}");
        sb.AppendLine($"Connection: {connectionState}");
        sb.AppendLine($"Safety state: {safetyState}");
        sb.AppendLine();
        sb.AppendLine("Recent high-level events");
        sb.AppendLine("------------------------");
        foreach (var line in entries) sb.AppendLine(line);
        sb.AppendLine();
        sb.AppendLine("This report intentionally excludes BLE addresses, raw packets, research captures, and profile/config contents.");

        await File.WriteAllTextAsync(path, sb.ToString(), Encoding.UTF8);
    }
}
'''

(ROOT / "Profiles/ProfileStore.cs").write_text(profile_store.lstrip("\n"), encoding="utf-8")
(ROOT / "Infrastructure/UserDiagnosticLog.cs").write_text(diagnostics.lstrip("\n"), encoding="utf-8")

xaml = ROOT / "MainWindow.xaml"
s = xaml.read_text(encoding="utf-8")

old_left = '''                            <Button Style="{StaticResource PrimaryButton}" Margin="0,10,0,8" Content="Save current profile" Click="SaveProfile_Click"/>
                            <Button Style="{StaticResource SecondaryButton}" Margin="0,0,0,8" Content="Refresh profiles" Click="RefreshProfiles_Click"/>
                            <Button Style="{StaticResource SecondaryButton}" Margin="0" Content="Open profiles folder" Click="OpenProfilesFolder_Click"/>'''
new_left = '''                            <Button Style="{StaticResource PrimaryButton}" Margin="0,10,0,8" Content="Save current profile" Click="SaveProfile_Click"/>
                            <Button Style="{StaticResource SecondaryButton}" Margin="0,0,0,8" Content="Import profile..." Click="ImportProfile_Click"/>
                            <Button Style="{StaticResource SecondaryButton}" Margin="0,0,0,8" Content="Refresh profiles" Click="RefreshProfiles_Click"/>
                            <Button Style="{StaticResource SecondaryButton}" Margin="0" Content="Open profiles folder" Click="OpenProfilesFolder_Click"/>'''
if old_left not in s:
    raise SystemExit("Profiles left button block not found")
s = s.replace(old_left, new_left, 1)

old_note = '''<StackPanel><TextBlock Text="Saved profiles" FontSize="18" FontWeight="SemiBold"/><TextBlock Text="Loading a profile changes the editor only. It does not write the controller until you click Apply &amp; Verify." Foreground="{StaticResource TextSecondary}" Margin="0,3,0,12" TextWrapping="Wrap"/></StackPanel>'''
new_note = '''<StackPanel><TextBlock Text="Saved profiles" FontSize="18" FontWeight="SemiBold"/><TextBlock Text="Loading a profile changes the editor only. On Apply &amp; Verify, only supported public fields are merged onto a fresh device read so unknown/reserved bytes stay with the controller." Foreground="{StaticResource TextSecondary}" Margin="0,3,0,12" TextWrapping="Wrap"/></StackPanel>'''
if old_note not in s:
    raise SystemExit("Profiles note not found")
s = s.replace(old_note, new_note, 1)

old_bottom = '''                            <Button Grid.Row="2" Style="{StaticResource PrimaryButton}" Margin="0,12,0,0" Content="Load selected into editor" Click="LoadProfile_Click"/>'''
new_bottom = '''                            <StackPanel Grid.Row="2" Margin="0,12,0,0">
                                <Button Style="{StaticResource PrimaryButton}" Margin="0,0,0,8" Content="Load selected into editor" Click="LoadProfile_Click"/>
                                <WrapPanel>
                                    <Button Style="{StaticResource SecondaryButton}" Margin="0,0,8,8" Content="Export selected..." Click="ExportProfile_Click"/>
                                    <Button Style="{StaticResource SecondaryButton}" Margin="0,0,8,8" Content="Duplicate as name above" Click="DuplicateProfile_Click"/>
                                    <Button Style="{StaticResource SecondaryButton}" Margin="0,0,8,8" Content="Rename to name above" Click="RenameProfile_Click"/>
                                    <Button Style="{StaticResource DangerButton}" Margin="0,0,0,8" Content="Delete selected" Click="DeleteProfile_Click"/>
                                </WrapPanel>
                            </StackPanel>'''
if old_bottom not in s:
    raise SystemExit("Profiles bottom button not found")
s = s.replace(old_bottom, new_bottom, 1)

profiles_end = '''            </TabItem>
        </TabControl>'''
about = '''            </TabItem>

            <TabItem Header="About">
                <ScrollViewer VerticalScrollBarVisibility="Auto">
                    <Grid Margin="0,14,0,0">
                        <Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition Width="14"/><ColumnDefinition/></Grid.ColumnDefinitions>
                        <Border Grid.Column="0" Style="{StaticResource Card}" VerticalAlignment="Top">
                            <StackPanel>
                                <TextBlock Text="ArmorX Windows" FontSize="20" FontWeight="SemiBold"/>
                                <TextBlock Text="Public configurator · v0.2.1" Foreground="{StaticResource TextSecondary}" Margin="0,3,0,16"/>
                                <TextBlock Text="A community-built BLE configurator for BIGBIG WON ARMOR-X Pro. Stable public features are kept separate from the internal research/capture application." TextWrapping="Wrap"/>
                                <Button Style="{StaticResource PrimaryButton}" Margin="0,18,0,8" Content="Open project on GitHub" Click="OpenProject_Click"/>
                                <Button Style="{StaticResource SecondaryButton}" Margin="0,0,0,8" Content="Export diagnostics..." Click="ExportDiagnostics_Click"/>
                                <Button Style="{StaticResource SecondaryButton}" Margin="0" Content="Open automatic backups folder" Click="OpenBackupsFolder_Click"/>
                            </StackPanel>
                        </Border>
                        <Border Grid.Column="2" Style="{StaticResource Card}" VerticalAlignment="Top">
                            <StackPanel>
                                <TextBlock Text="Compatibility" FontSize="20" FontWeight="SemiBold"/>
                                <TextBlock Text="Current device" Foreground="{StaticResource TextSecondary}" Margin="0,14,0,3"/>
                                <TextBlock FontWeight="SemiBold"><Run Text="Model: "/><Run Text="{Binding ModelText}"/><Run Text="    Firmware: "/><Run Text="{Binding FirmwareText}"/></TextBlock>
                                <TextBlock Text="Validated reference hardware" Foreground="{StaticResource TextSecondary}" Margin="0,14,0,3"/>
                                <TextBlock Text="ARMOR-X Pro · ZJ-XT · firmware 2741" FontWeight="SemiBold"/>
                                <TextBlock Text="The app preserves unknown/reserved configuration bytes, automatically backs up the current 144-byte image before writes, and verifies writes with a complete read-back." TextWrapping="Wrap" Margin="0,14,0,0"/>
                                <TextBlock Text="Diagnostic exports are end-user reports only: they exclude BLE addresses, raw packets, research captures, and configuration contents." TextWrapping="Wrap" Foreground="{StaticResource TextSecondary}" Margin="0,14,0,0"/>
                            </StackPanel>
                        </Border>
                    </Grid>
                </ScrollViewer>
            </TabItem>
        </TabControl>'''
if profiles_end not in s:
    raise SystemExit("TabControl end insertion point not found")
s = s.replace(profiles_end, about, 1)
xaml.write_text(s, encoding="utf-8")

cs = ROOT / "MainWindow.xaml.cs"
s = cs.read_text(encoding="utf-8")

if "using Microsoft.Win32;" not in s:
    s = s.replace("using System.Windows;\n", "using System.Windows;\nusing Microsoft.Win32;\n")
if "using ArmorX.Windows.Infrastructure;" not in s:
    s = s.replace("using ArmorX.Windows.Device;\n", "using ArmorX.Windows.Device;\nusing ArmorX.Windows.Infrastructure;\n")

s = s.replace(
    "    private readonly BackupStore _backupStore = new();\n",
    "    private readonly BackupStore _backupStore = new();\n    private readonly UserDiagnosticLog _diagnostics = new();\n"
)

constructor_marker = '''        DataContext = this;

        _transport.DeviceSeen += Transport_DeviceSeen;'''
if constructor_marker not in s:
    raise SystemExit("Constructor marker not found")
s = s.replace(
    constructor_marker,
    '''        DataContext = this;
        _diagnostics.Add("Application started.");

        _transport.DeviceSeen += Transport_DeviceSeen;''',
    1
)

adapter_marker = '''            var adapter = await _transport.GetAdapterStatusAsync();
            ConnectionDetail = adapter == "Bluetooth ready"'''
if adapter_marker not in s:
    raise SystemExit("Adapter marker not found")
s = s.replace(
    adapter_marker,
    '''            var adapter = await _transport.GetAdapterStatusAsync();
            _diagnostics.Add($"Bluetooth status: {adapter}.");
            ConnectionDetail = adapter == "Bluetooth ready"''',
    1
)

connected_marker = '''            if (connected)
            {
                ConnectionHeadline = "Connected";'''
s = s.replace(
    connected_marker,
    '''            if (connected)
            {
                _diagnostics.Add("BLE connection established.");
                ConnectionHeadline = "Connected";''',
    1
)
disconnect_marker = '''            if (_closing || _manualDisconnect || _connectionOperation) return;
            ConnectionHeadline = "Disconnected / asleep";'''
s = s.replace(
    disconnect_marker,
    '''            if (_closing || _manualDisconnect || _connectionOperation) return;
            _diagnostics.Add("Device disconnected or entered sleep; recovery started.");
            ConnectionHeadline = "Disconnected / asleep";''',
    1
)

identity_marker = '''            ConnectionDetail = $"{ModelText} · firmware {FirmwareText}";
            StatusText = "Connected. Reading configuration...";'''
s = s.replace(
    identity_marker,
    '''            ConnectionDetail = $"{ModelText} · firmware {FirmwareText}";
            _diagnostics.Add($"Device ready: model {ModelText}, firmware {FirmwareText}, battery {BatteryText}.");
            StatusText = "Connected. Reading configuration...";''',
    1
)

read_marker = '''            LoadDeviceConfig(config);
            StatusText = $"Configuration refreshed · CRC'''
s = s.replace(
    read_marker,
    '''            LoadDeviceConfig(config);
            _diagnostics.Add($"Configuration read completed; CRC {(config.CrcValid ? "valid" : "invalid")}.");
            StatusText = $"Configuration refreshed · CRC''',
    1
)

verified_marker = '''            SafetyText = $"Verified · pre-write backup: {Path.GetFileName(backupPath)}";
            StatusText = $"Saved and verified · CRC 0x{result.ReadBackConfig.StoredCrc:X4}.";'''
s = s.replace(
    verified_marker,
    '''            SafetyText = $"Verified · pre-write backup: {Path.GetFileName(backupPath)}";
            _diagnostics.Add($"Apply & Verify passed; {changes.Count} semantic byte change(s), CRC 0x{result.ReadBackConfig.StoredCrc:X4}.");
            StatusText = $"Saved and verified · CRC 0x{result.ReadBackConfig.StoredCrc:X4}.";''',
    1
)

restore_marker = '''            SafetyText = $"Backup restored and verified · undo backup: {Path.GetFileName(undoPath)}";
            StatusText = $"Backup restored and verified · CRC 0x{result.ReadBackConfig.StoredCrc:X4}.";'''
s = s.replace(
    restore_marker,
    '''            SafetyText = $"Backup restored and verified · undo backup: {Path.GetFileName(undoPath)}";
            _diagnostics.Add($"Backup restore verified; CRC 0x{result.ReadBackConfig.StoredCrc:X4}.");
            StatusText = $"Backup restored and verified · CRC 0x{result.ReadBackConfig.StoredCrc:X4}.";''',
    1
)

profile_insert = s.index("    private async void RefreshProfiles_Click")
handlers = r'''    private async void ImportProfile_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "Import ArmorX profile",
            Filter = "ArmorX profile (*.json)|*.json|JSON files (*.json)|*.json|All files (*.*)|*.*"
        };
        if (dialog.ShowDialog(this) != true) return;

        await RunBusyAsync("Importing profile...", async () =>
        {
            var profile = await _profileStore.ImportAsync(dialog.FileName);
            await RefreshProfilesAsync();
            ProfileNameBox.Text = profile.Name;
            _diagnostics.Add($"Profile imported: {profile.Name}.");
            StatusText = $"Imported profile '{profile.Name}'.";
        });
    }

    private async void ExportProfile_Click(object sender, RoutedEventArgs e)
    {
        if (SelectedProfile is null)
        {
            MessageBox.Show("Select a saved profile first.", "Export profile");
            return;
        }

        var dialog = new SaveFileDialog
        {
            Title = "Export ArmorX profile",
            FileName = SelectedProfile.Name + ".json",
            DefaultExt = ".json",
            Filter = "ArmorX profile (*.json)|*.json"
        };
        if (dialog.ShowDialog(this) != true) return;

        await RunBusyAsync("Exporting profile...", async () =>
        {
            await _profileStore.ExportAsync(SelectedProfile.Name, dialog.FileName);
            _diagnostics.Add($"Profile exported: {SelectedProfile.Name}.");
            StatusText = $"Exported '{SelectedProfile.Name}'.";
        });
    }

    private async void DuplicateProfile_Click(object sender, RoutedEventArgs e)
    {
        if (SelectedProfile is null)
        {
            MessageBox.Show("Select a saved profile first.", "Duplicate profile");
            return;
        }

        var newName = ProfileNameBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(newName) || string.Equals(newName, SelectedProfile.Name, StringComparison.OrdinalIgnoreCase))
            newName = SelectedProfile.Name + " Copy";

        var finalName = newName;
        await RunBusyAsync("Duplicating profile...", async () =>
        {
            await _profileStore.DuplicateAsync(SelectedProfile.Name, finalName);
            await RefreshProfilesAsync();
            ProfileNameBox.Text = finalName;
            _diagnostics.Add($"Profile duplicated as {finalName}.");
            StatusText = $"Duplicated profile as '{finalName}'.";
        });
    }

    private async void RenameProfile_Click(object sender, RoutedEventArgs e)
    {
        if (SelectedProfile is null)
        {
            MessageBox.Show("Select a saved profile first.", "Rename profile");
            return;
        }

        var newName = ProfileNameBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(newName))
        {
            MessageBox.Show("Enter the new name in the Name box first.", "Rename profile");
            return;
        }

        var oldName = SelectedProfile.Name;
        await RunBusyAsync("Renaming profile...", async () =>
        {
            await _profileStore.RenameAsync(oldName, newName);
            await RefreshProfilesAsync();
            _diagnostics.Add($"Profile renamed: {oldName} -> {newName}.");
            StatusText = $"Renamed '{oldName}' to '{newName}'.";
        });
    }

    private async void DeleteProfile_Click(object sender, RoutedEventArgs e)
    {
        if (SelectedProfile is null)
        {
            MessageBox.Show("Select a saved profile first.", "Delete profile");
            return;
        }

        var name = SelectedProfile.Name;
        if (MessageBox.Show($"Delete local profile '{name}'?", "Delete profile",
                MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes)
            return;

        await RunBusyAsync("Deleting profile...", async () =>
        {
            await _profileStore.DeleteAsync(name);
            SelectedProfile = null;
            await RefreshProfilesAsync();
            _diagnostics.Add($"Profile deleted: {name}.");
            StatusText = $"Deleted local profile '{name}'.";
        });
    }

    private void OpenProject_Click(object sender, RoutedEventArgs e) =>
        Process.Start(new ProcessStartInfo("https://github.com/feshinkof-boop/armorx-toolkit") { UseShellExecute = true });

    private void OpenBackupsFolder_Click(object sender, RoutedEventArgs e)
    {
        Directory.CreateDirectory(_backupStore.DirectoryPath);
        Process.Start(new ProcessStartInfo("explorer.exe", _backupStore.DirectoryPath) { UseShellExecute = true });
    }

    private async void ExportDiagnostics_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog
        {
            Title = "Export ArmorX Windows diagnostics",
            FileName = $"ArmorX-Windows-Diagnostics-{DateTime.Now:yyyyMMdd-HHmmss}.txt",
            DefaultExt = ".txt",
            Filter = "Text file (*.txt)|*.txt"
        };
        if (dialog.ShowDialog(this) != true) return;

        await RunBusyAsync("Exporting diagnostics...", async () =>
        {
            await _diagnostics.ExportAsync(dialog.FileName, ModelText, FirmwareText, ConnectionHeadline, SafetyText);
            StatusText = "End-user diagnostic report exported.";
        });
    }

'''
s = s[:profile_insert] + handlers + s[profile_insert:]

catch_marker = '''        catch (Exception ex)
        {
            StatusText = "Error: " + ex.Message;'''
s = s.replace(
    catch_marker,
    '''        catch (Exception ex)
        {
            _diagnostics.Add($"Operation error: {ex.GetType().Name}: {ex.Message}");
            StatusText = "Error: " + ex.Message;''',
    1
)

cs.write_text(s, encoding="utf-8")
print("v0.2.1 profile/diagnostic/about UX prepared")
