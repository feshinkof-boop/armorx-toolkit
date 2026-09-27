using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.Runtime.CompilerServices;
using System.Windows;
using ArmorX.Windows.Bluetooth;
using ArmorX.Windows.Config;
using ArmorX.Windows.Device;
using ArmorX.Windows.Profiles;

namespace ArmorX.Windows;

public partial class MainWindow : Window, INotifyPropertyChanged
{
    private readonly ArmorXBleTransport _transport = new();
    private readonly ProfileStore _profileStore = new();
    private readonly BackupStore _backupStore = new();
    private readonly SemaphoreSlim _connectGate = new(1, 1);
    private ArmorXDeviceSession? _session;
    private EditableArmorXConfig? _config;
    private ArmorXProfile? _selectedProfile;
    private string _connectionHeadline = "Not connected";
    private string _connectionDetail = "Turn on the ARMOR-X Pro, then choose Connect / Recover.";
    private string _statusText = "Ready";
    private string _modelText = "-";
    private string _firmwareText = "-";
    private string _batteryText = "-";
    private string _safetyText = "No device baseline loaded.";
    private byte[]? _deviceBaseline;
    private bool _busy;
    private bool _manualDisconnect;
    private bool _connectionOperation;
    private bool _closing;
    private CancellationTokenSource? _guardianCts;

    private string LastDevicePath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ArmorX", "last-device.txt");

    public event PropertyChangedEventHandler? PropertyChanged;

    public ObservableCollection<BleDiscoveredDevice> Devices { get; } = new();
    public ObservableCollection<ArmorXProfile> Profiles { get; } = new();
    public IReadOnlyList<MappingTarget> MappingTargets => EditableArmorXConfig.ProvenMappingTargets;
    public string ProfileDirectory => _profileStore.DirectoryPath;

    public ArmorXProfile? SelectedProfile { get => _selectedProfile; set => Set(ref _selectedProfile, value); }
    public EditableArmorXConfig? Config
    {
        get => _config;
        private set
        {
            if (ReferenceEquals(_config, value)) return;
            if (_config is not null) _config.Changed -= Config_Changed;
            _config = value;
            if (_config is not null) _config.Changed += Config_Changed;
            OnPropertyChanged();
            UpdateDirtyState();
        }
    }
    public string ConnectionHeadline { get => _connectionHeadline; private set => Set(ref _connectionHeadline, value); }
    public string ConnectionDetail { get => _connectionDetail; private set => Set(ref _connectionDetail, value); }
    public string StatusText { get => _statusText; private set => Set(ref _statusText, value); }
    public string ModelText { get => _modelText; private set => Set(ref _modelText, value); }
    public string FirmwareText { get => _firmwareText; private set => Set(ref _firmwareText, value); }
    public string BatteryText { get => _batteryText; private set => Set(ref _batteryText, value); }
    public string SafetyText { get => _safetyText; private set => Set(ref _safetyText, value); }

    public MainWindow()
    {
        InitializeComponent();
        DataContext = this;

        _transport.DeviceSeen += Transport_DeviceSeen;
        _transport.ConnectionChanged += Transport_ConnectionChanged;

        Loaded += async (_, _) =>
        {
            await RefreshProfilesAsync();
            _transport.EnsurePersistentDiscovery();
            var adapter = await _transport.GetAdapterStatusAsync();
            ConnectionDetail = adapter == "Bluetooth ready"
                ? "Bluetooth ready. Turn on the ARMOR-X Pro, then choose Connect / Recover."
                : adapter;
        };

        Closing += async (_, _) =>
        {
            _closing = true;
            _guardianCts?.Cancel();
            _session?.Dispose();
            await _transport.DisposeAsync();
        };
    }

    private void Transport_DeviceSeen(object? sender, BleDiscoveredDevice item)
    {
        Dispatcher.Invoke(() =>
        {
            var existing = Devices.FirstOrDefault(x => x.Address == item.Address);
            if (existing is null) Devices.Add(item);
        });
    }

    private void Transport_ConnectionChanged(object? sender, bool connected)
    {
        Dispatcher.Invoke(() =>
        {
            if (connected)
            {
                ConnectionHeadline = "Connected";
                ConnectionDetail = "ARMOR-X Pro is ready.";
                return;
            }

            if (_closing || _manualDisconnect || _connectionOperation) return;
            ConnectionHeadline = "Disconnected / asleep";
            ConnectionDetail = "Turn the ARMOR-X Pro back on. Automatic recovery is active.";
            StatusText = "Waiting for ARMOR-X Pro to wake...";
            _session?.Dispose();
            _session = null;
            StartConnectionGuardian();
        });
    }

    private async void ConnectRecover_Click(object sender, RoutedEventArgs e)
    {
        _manualDisconnect = false;
        _guardianCts?.Cancel();
        await RecoverConnectionAsync(interactive: true, CancellationToken.None);
    }

    private async void Disconnect_Click(object sender, RoutedEventArgs e)
    {
        _manualDisconnect = true;
        _guardianCts?.Cancel();
        await RunBusyAsync("Disconnecting...", async () =>
        {
            _connectionOperation = true;
            try
            {
                _session?.Dispose();
                _session = null;
                await _transport.DisconnectAsync();
            }
            finally { _connectionOperation = false; }
            ConnectionHeadline = "Not connected";
            ConnectionDetail = "Turn on the ARMOR-X Pro, then choose Connect / Recover.";
            StatusText = "Disconnected.";
        });
    }

    private async Task<bool> RecoverConnectionAsync(bool interactive, CancellationToken cancellationToken)
    {
        if (!await _connectGate.WaitAsync(0, cancellationToken)) return false;
        try
        {
            if (_transport.IsConnected && _session is not null) return true;

            _connectionOperation = true;
            if (interactive)
            {
                ConnectionHeadline = "Finding ARMOR-X Pro...";
                ConnectionDetail = "Using the remembered device, Windows Bluetooth cache, and live BLE discovery.";
                StatusText = "Searching for ARMOR-X Pro...";
            }

            _transport.EnsurePersistentDiscovery();
            await _transport.EnumerateWindowsCachedArmorXAsync(cancellationToken);

            var tried = new HashSet<ulong>();
            var candidates = new List<ulong>();
            if (TryLoadRememberedAddress(out var remembered)) candidates.Add(remembered);
            candidates.AddRange(_transport.ScanSnapshot
                .Where(x => ArmorXBleTransport.LooksLikeArmorXName(x.Name))
                .OrderByDescending(x => x.Rssi)
                .Select(x => x.Address));

            foreach (var address in candidates.Distinct())
            {
                tried.Add(address);
                if (await TryOpenDeviceAsync(address, cancellationToken)) return true;
            }

            var deadline = DateTime.UtcNow + (interactive ? TimeSpan.FromSeconds(18) : TimeSpan.FromSeconds(6));
            while (DateTime.UtcNow < deadline)
            {
                cancellationToken.ThrowIfCancellationRequested();
                foreach (var item in _transport.ScanSnapshot
                             .Where(x => (ArmorXBleTransport.LooksLikeArmorXName(x.Name) || (TryLoadRememberedAddress(out var r) && r == x.Address)) && !tried.Contains(x.Address))
                             .OrderByDescending(x => x.Rssi))
                {
                    tried.Add(item.Address);
                    if (await TryOpenDeviceAsync(item.Address, cancellationToken)) return true;
                }
                await Task.Delay(500, cancellationToken);
            }

            if (interactive)
            {
                var adapter = await _transport.GetAdapterStatusAsync(cancellationToken);
                ConnectionHeadline = "ARMOR-X Pro not found";
                ConnectionDetail = adapter == "Bluetooth ready"
                    ? "Make sure the ARMOR-X Pro is powered on and the official mobile app is closed, then try again."
                    : adapter;
                StatusText = "Connection failed.";
                MessageBox.Show(ConnectionDetail, "ArmorX Windows", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            return false;
        }
        catch (OperationCanceledException) { return false; }
        catch (Exception ex)
        {
            if (interactive)
            {
                ConnectionHeadline = "Connection problem";
                ConnectionDetail = ex.Message;
                StatusText = "Connection error: " + ex.Message;
                MessageBox.Show(ex.Message, "ArmorX Windows", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            return false;
        }
        finally
        {
            _connectionOperation = false;
            _connectGate.Release();
        }
    }

    private async Task<bool> TryOpenDeviceAsync(ulong address, CancellationToken cancellationToken)
    {
        try
        {
            _session?.Dispose();
            _session = null;
            await _transport.ConnectAsync(address, cancellationToken);
            var session = new ArmorXDeviceSession(_transport);
            await session.InitializeAsync(cancellationToken);
            _session = session;
            RememberAddress(address);

            ModelText = session.Model ?? "ARMOR-X Pro";
            FirmwareText = session.Firmware ?? "-";
            BatteryText = session.BatteryPercent is int b ? $"{b}%" : "-";
            ConnectionHeadline = "Connected to ARMOR-X Pro";
            ConnectionDetail = $"{ModelText} · firmware {FirmwareText}";
            StatusText = "Connected. Reading configuration...";

            var config = await session.ReadConfigAsync(cancellationToken);
            LoadDeviceConfig(config);
            StatusText = config.CrcValid
                ? $"Configuration loaded and verified · CRC 0x{config.StoredCrc:X4}."
                : $"Configuration loaded · CRC mismatch (stored 0x{config.StoredCrc:X4}).";
            _guardianCts?.Cancel();
            return true;
        }
        catch
        {
            try { await _transport.DisconnectAsync(); } catch { }
            _session?.Dispose();
            _session = null;
            return false;
        }
    }

    private void StartConnectionGuardian()
    {
        if (_manualDisconnect || _closing) return;
        _guardianCts?.Cancel();
        _guardianCts = new CancellationTokenSource();
        var token = _guardianCts.Token;
        _ = Task.Run(async () =>
        {
            var until = DateTime.UtcNow + TimeSpan.FromMinutes(3);
            while (!token.IsCancellationRequested && DateTime.UtcNow < until)
            {
                try
                {
                    await Task.Delay(TimeSpan.FromSeconds(4), token);
                    if (_transport.IsConnected) return;
                    var recovered = await Dispatcher.InvokeAsync(() => RecoverConnectionAsync(interactive: false, token)).Task.Unwrap();
                    if (recovered)
                    {
                        await Dispatcher.InvokeAsync(() =>
                        {
                            ConnectionHeadline = "Reconnected";
                            ConnectionDetail = "ARMOR-X Pro woke up and was recovered automatically.";
                            StatusText = "Connection restored.";
                        });
                        return;
                    }
                }
                catch (OperationCanceledException) { return; }
                catch { }
            }
            await Dispatcher.InvokeAsync(() =>
            {
                if (!_transport.IsConnected && !_manualDisconnect)
                {
                    ConnectionHeadline = "Disconnected";
                    ConnectionDetail = "Turn on the ARMOR-X Pro and choose Connect / Recover.";
                    StatusText = "Automatic recovery timed out.";
                }
            });
        }, token);
    }

    private async void ReadConfig_Click(object sender, RoutedEventArgs e)
    {
        if (_session is null)
        {
            MessageBox.Show("Connect the ARMOR-X Pro first.", "ArmorX Windows", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        await RunBusyAsync("Reading configuration...", async () =>
        {
            var config = await _session.ReadConfigAsync();
            LoadDeviceConfig(config);
            StatusText = $"Configuration refreshed · CRC {(config.CrcValid ? "valid" : "invalid")} 0x{config.StoredCrc:X4}.";
        });
    }

    private void ReviewChanges_Click(object sender, RoutedEventArgs e)
    {
        if (Config is null || _deviceBaseline is null)
        {
            MessageBox.Show("Read a configuration from the ARMOR-X Pro first.", "Review changes",
                MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        var desired = Config.BuildForWrite();
        var changes = ConfigDiff.Compare(_deviceBaseline, desired.ToArray());
        MessageBox.Show(ConfigDiff.FormatSummary(changes), "Pending configuration changes",
            MessageBoxButton.OK, changes.Count == 0 ? MessageBoxImage.Information : MessageBoxImage.Question);
    }

    private async void WriteVerify_Click(object sender, RoutedEventArgs e)
    {
        if (_session is null || Config is null || _deviceBaseline is null)
        {
            MessageBox.Show("Connect and read a configuration first. ArmorX Windows writes from the controller's own image so unknown bytes are preserved.",
                "ArmorX Windows", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        await RunBusyAsync("Preparing safe write...", async () =>
        {
            var current = await _session.ReadConfigAsync();
            var backupPath = await _backupStore.SaveAsync(current, _session.Model, _session.Firmware, "pre-write");

            var editorDesired = Config.BuildForWrite();
            var writeConfig = ConfigDiff.MergeEditorChanges(current, _deviceBaseline, editorDesired);
            var changes = ConfigDiff.Compare(current, writeConfig);

            if (changes.Count == 0)
            {
                _deviceBaseline = current.ToArray();
                SafetyText = $"No pending changes · backup saved: {Path.GetFileName(backupPath)}";
                StatusText = "Nothing to write.";
                return;
            }

            var prompt = ConfigDiff.FormatSummary(changes) +
                         Environment.NewLine + Environment.NewLine +
                         $"A full 144-byte backup was saved first:{Environment.NewLine}{backupPath}" +
                         Environment.NewLine + Environment.NewLine +
                         "Apply these changes, persist them, and verify all 144 bytes by reading the device back?";

            var answer = MessageBox.Show(prompt, "Review · Apply & Verify",
                MessageBoxButton.YesNo, MessageBoxImage.Question);
            if (answer != MessageBoxResult.Yes)
            {
                SafetyText = $"Write cancelled · backup saved: {Path.GetFileName(backupPath)}";
                StatusText = "Write cancelled. Device unchanged.";
                return;
            }

            StatusText = "Applying settings and verifying...";
            var result = await _session.WriteAndVerifyAsync(writeConfig);
            LoadDeviceConfig(result.ReadBackConfig);

            if (!result.ExactMatch)
            {
                StatusText = $"Verification failed · {result.MismatchOffsets.Count} byte(s) differ.";
                SafetyText = $"Pre-write backup available: {Path.GetFileName(backupPath)}";
                MessageBox.Show(
                    "The device read-back did not exactly match the requested configuration. The actual device image is now loaded into the editor. Use Restore last backup if needed.",
                    "ArmorX Windows", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            SafetyText = $"Verified · pre-write backup: {Path.GetFileName(backupPath)}";
            StatusText = $"Saved and verified · CRC 0x{result.ReadBackConfig.StoredCrc:X4}.";
            MessageBox.Show(
                "Settings saved successfully. The complete 144-byte read-back matches. A pre-write backup was kept automatically.",
                "ArmorX Windows", MessageBoxButton.OK, MessageBoxImage.Information);
        });
    }

    private async void RestoreLastBackup_Click(object sender, RoutedEventArgs e)
    {
        if (_session is null)
        {
            MessageBox.Show("Connect the ARMOR-X Pro first.", "Restore last backup",
                MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        await RunBusyAsync("Preparing backup restore...", async () =>
        {
            var targetBackup = await _backupStore.LoadLatestAsync();
            if (targetBackup is null)
            {
                MessageBox.Show("No automatic backup is available yet.", "Restore last backup",
                    MessageBoxButton.OK, MessageBoxImage.Information);
                StatusText = "No backup available.";
                return;
            }

            var target = new ArmorXConfig144(targetBackup.GetConfigBytes());
            var current = await _session.ReadConfigAsync();
            var changes = ConfigDiff.Compare(current, target);

            if (changes.Count == 0)
            {
                LoadDeviceConfig(current);
                StatusText = "The latest backup already matches the device.";
                return;
            }

            var prompt = ConfigDiff.FormatSummary(changes) +
                         Environment.NewLine + Environment.NewLine +
                         $"Backup date: {targetBackup.SavedUtc.LocalDateTime:G}" +
                         Environment.NewLine +
                         $"Backup reason: {targetBackup.Reason}" +
                         Environment.NewLine + Environment.NewLine +
                         "Restore this complete backed-up image and verify it by reading all 144 bytes back?";

            var answer = MessageBox.Show(prompt, "Restore last backup",
                MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (answer != MessageBoxResult.Yes)
            {
                StatusText = "Restore cancelled. Device unchanged.";
                return;
            }

            var undoPath = await _backupStore.SaveAsync(current, _session.Model, _session.Firmware, "pre-restore");
            StatusText = "Restoring backup and verifying...";
            var result = await _session.WriteAndVerifyAsync(target);
            LoadDeviceConfig(result.ReadBackConfig);

            if (!result.ExactMatch)
            {
                SafetyText = $"Restore verification failed · previous state backed up: {Path.GetFileName(undoPath)}";
                StatusText = $"Restore verification failed · {result.MismatchOffsets.Count} byte(s) differ.";
                MessageBox.Show("Restore did not verify exactly. The actual device image is loaded in the editor.",
                    "Restore last backup", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            SafetyText = $"Backup restored and verified · undo backup: {Path.GetFileName(undoPath)}";
            StatusText = $"Backup restored and verified · CRC 0x{result.ReadBackConfig.StoredCrc:X4}.";
            MessageBox.Show("Backup restored successfully and all 144 read-back bytes match.",
                "Restore last backup", MessageBoxButton.OK, MessageBoxImage.Information);
        });
    }

    private async void SaveProfile_Click(object sender, RoutedEventArgs e)
    {
        if (Config is null)
        {
            MessageBox.Show("There is no configuration loaded to save.", "ArmorX Windows");
            return;
        }
        var name = ProfileNameBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(name)) name = "ArmorX Profile";
        await RunBusyAsync("Saving profile...", async () =>
        {
            await _profileStore.SaveAsync(name, Config.BuildForWrite(), _session?.Model, _session?.Firmware);
            await RefreshProfilesAsync();
            StatusText = $"Saved local profile '{name}'.";
        });
    }

    private async void LoadProfile_Click(object sender, RoutedEventArgs e)
    {
        if (SelectedProfile is null)
        {
            MessageBox.Show("Select a saved profile first.", "ArmorX Windows");
            return;
        }
        await RunBusyAsync("Loading profile...", async () =>
        {
            var profile = await _profileStore.LoadAsync(SelectedProfile.Name);
            Config = new EditableArmorXConfig(new ArmorXConfig144(profile.GetConfigBytes()));
            ProfileNameBox.Text = profile.Name;
            StatusText = $"Loaded '{profile.Name}' into the editor. The controller has not been changed yet.";
        });
    }

    private async void RefreshProfiles_Click(object sender, RoutedEventArgs e) => await RefreshProfilesAsync();

    private void OpenProfilesFolder_Click(object sender, RoutedEventArgs e)
    {
        Directory.CreateDirectory(_profileStore.DirectoryPath);
        Process.Start(new ProcessStartInfo("explorer.exe", _profileStore.DirectoryPath) { UseShellExecute = true });
    }

    private async Task RefreshProfilesAsync()
    {
        var profiles = await _profileStore.ListAsync();
        await Dispatcher.InvokeAsync(() =>
        {
            Profiles.Clear();
            foreach (var profile in profiles) Profiles.Add(profile);
        });
    }

    private void LoadDeviceConfig(ArmorXConfig144 config)
    {
        _deviceBaseline = config.ToArray();
        Config = new EditableArmorXConfig(config);
        UpdateDirtyState();
    }

    private void Config_Changed(object? sender, EventArgs e) => UpdateDirtyState();

    private void UpdateDirtyState()
    {
        if (Config is null || _deviceBaseline is null)
        {
            SafetyText = "No device baseline loaded.";
            return;
        }

        try
        {
            var desired = Config.BuildForWrite();
            var changes = ConfigDiff.Compare(_deviceBaseline, desired.ToArray());
            SafetyText = changes.Count == 0
                ? "No pending semantic changes · automatic backup runs before every write."
                : $"{changes.Count} pending semantic byte change(s) · review before Apply & Verify.";
        }
        catch
        {
            SafetyText = "Pending-change state unavailable.";
        }
    }

    private bool TryLoadRememberedAddress(out ulong address)
    {
        address = 0;
        try
        {
            if (!File.Exists(LastDevicePath)) return false;
            var text = File.ReadAllText(LastDevicePath).Trim();
            return ulong.TryParse(text, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out address);
        }
        catch { return false; }
    }

    private void RememberAddress(ulong address)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(LastDevicePath)!);
            File.WriteAllText(LastDevicePath, address.ToString("X12", CultureInfo.InvariantCulture));
        }
        catch { }
    }

    private async Task RunBusyAsync(string status, Func<Task> action)
    {
        if (_busy) return;
        _busy = true;
        StatusText = status;
        try { await action(); }
        catch (Exception ex)
        {
            StatusText = "Error: " + ex.Message;
            MessageBox.Show(ex.Message, "ArmorX Windows", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally { _busy = false; }
    }

    private bool Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value;
        OnPropertyChanged(name);
        return true;
    }

    private void OnPropertyChanged([CallerMemberName] string? name = null) => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
