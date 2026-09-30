using System.Collections.Concurrent;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ArmorX.Windows.Bluetooth;
using ArmorX.Windows.Config;
using ArmorX.Windows.Device;
using ArmorX.Windows.Infrastructure;
using ArmorX.Windows.Profiles;
using Microsoft.Win32;

namespace ArmorX.Windows.Bridge;

public sealed class ArmorXAppController : IAsyncDisposable
{
    private const string AppVersion = "0.6.0";
    private readonly ArmorXBleTransport _transport = new();
    private readonly ProfileStore _profiles = new();
    private readonly BackupStore _backups = new();
    private readonly UserDiagnosticLog _diagnostics = new();
    private readonly SemaphoreSlim _connectionGate = new(1, 1);
    private readonly SemaphoreSlim _operationGate = new(1, 1);
    private readonly ConcurrentQueue<string> _log = new();

    private ArmorXDeviceSession? _session;
    private EditableArmorXConfig? _config;
    private byte[]? _deviceBaseline;
    private string? _activeProfile;
    private string? _lastBackupName;
    private string _connection = "Not connected";
    private string _connectionDetail = "Power on ARMOR-X Pro, then connect.";
    private string _bluetoothStatus = "Checking Bluetooth...";
    private bool _busy;
    private string _busyText = string.Empty;
    private bool _manualDisconnect;
    private bool _closing;
    private CancellationTokenSource? _guardianCts;
    private CancellationTokenSource? _telemetryCts;
    private PreparedWrite? _preparedWrite;

    public event EventHandler? StateChanged;
    public event EventHandler? HideRequested;
    public event EventHandler? ExitRequested;

    private string LastDevicePath => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "ArmorX", "last-device.txt");

    public ArmorXAppController()
    {
        _transport.DeviceSeen += (_, _) => NotifyState();
        _transport.ConnectionChanged += TransportOnConnectionChanged;
        _transport.Log += (_, line) => AddLog(line);
        _transport.EnsurePersistentDiscovery();
        _ = InitializeBluetoothStatusAsync();
        AddLog("ArmorX Studio controller initialized.");
    }

    public async Task<object?> HandleAsync(string action, JsonElement payload)
    {
        return action switch
        {
            "state" => await BuildStateAsync(),
            "connect" => await ConnectAsync(),
            "disconnect" => await DisconnectAsync(),
            "readConfig" => await ReadConfigAsync(),
            "patchConfig" => PatchConfig(payload),
            "prepareApply" => await PrepareApplyAsync(),
            "commitApply" => await CommitApplyAsync(payload),
            "prepareRestore" => await PrepareRestoreAsync(),
            "commitRestore" => await CommitRestoreAsync(payload),
            "saveProfile" => await SaveProfileAsync(payload),
            "loadProfile" => await LoadProfileAsync(payload),
            "deleteProfile" => await DeleteProfileAsync(payload),
            "renameProfile" => await RenameProfileAsync(payload),
            "duplicateProfile" => await DuplicateProfileAsync(payload),
            "importProfile" => await ImportProfileAsync(),
            "exportProfile" => await ExportProfileAsync(payload),
            "openProfilesFolder" => OpenFolder(_profiles.DirectoryPath),
            "openBackupsFolder" => OpenFolder(_backups.DirectoryPath),
            "openProject" => OpenUrl("https://github.com/feshinkof-boop/armorx-toolkit"),
            "openTextFile" => OpenTextFile(payload),
            "saveTextFile" => SaveTextFile(payload),
            "exportDiagnostics" => await ExportDiagnosticsAsync(),
            "minimizeToTray" => RequestHide(),
            "quit" => RequestExit(),
            _ => throw new InvalidOperationException($"Unknown bridge action '{action}'.")
        };
    }

    private async Task InitializeBluetoothStatusAsync()
    {
        _bluetoothStatus = await _transport.GetAdapterStatusAsync();
        AddLog($"Bluetooth status: {_bluetoothStatus}");
        NotifyState();
    }

    private void TransportOnConnectionChanged(object? sender, bool connected)
    {
        if (connected)
        {
            _connection = "Connected";
            _connectionDetail = "ARMOR-X Pro is ready.";
            NotifyState();
            return;
        }

        if (_closing || _manualDisconnect) return;
        _connection = "Disconnected / asleep";
        _connectionDetail = "Automatic recovery is waiting for ARMOR-X Pro to wake.";
        _session?.Dispose();
        _session = null;
        AddLog("BLE disconnected; recovery guardian started.");
        NotifyState();
        StartGuardian();
    }

    private void StartGuardian()
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
                    if (await RecoverConnectionAsync(interactive: false, token))
                    {
                        AddLog("Automatic BLE recovery succeeded.");
                        return;
                    }
                }
                catch (OperationCanceledException) { return; }
                catch (Exception ex) { AddLog("Recovery attempt failed: " + ex.Message); }
            }
            if (!_transport.IsConnected && !_manualDisconnect)
            {
                _connection = "Disconnected";
                _connectionDetail = "Automatic recovery timed out. Power on ARMOR-X Pro and reconnect.";
                NotifyState();
            }
        }, token);
    }

    private async Task<object> ConnectAsync()
    {
        _manualDisconnect = false;
        _guardianCts?.Cancel();
        return await RunBusyAsync("Finding ARMOR-X Pro...", async () =>
        {
            var ok = await RecoverConnectionAsync(interactive: true, CancellationToken.None);
            if (!ok) throw new InvalidOperationException(_connectionDetail);
            return await BuildStateAsync();
        });
    }

    private async Task<bool> RecoverConnectionAsync(bool interactive, CancellationToken cancellationToken)
    {
        if (!await _connectionGate.WaitAsync(0, cancellationToken)) return false;
        try
        {
            if (_transport.IsConnected && _session is not null) return true;
            if (interactive)
            {
                _connection = "Finding ARMOR-X Pro...";
                _connectionDetail = "Using the remembered device, Windows Bluetooth cache, and live BLE discovery.";
                NotifyState();
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
                    .Where(x => !tried.Contains(x.Address) &&
                                (ArmorXBleTransport.LooksLikeArmorXName(x.Name) ||
                                 (TryLoadRememberedAddress(out var r) && r == x.Address)))
                    .OrderByDescending(x => x.Rssi))
                {
                    tried.Add(item.Address);
                    if (await TryOpenDeviceAsync(item.Address, cancellationToken)) return true;
                }
                await Task.Delay(500, cancellationToken);
            }

            _bluetoothStatus = await _transport.GetAdapterStatusAsync(cancellationToken);
            _connection = "ARMOR-X Pro not found";
            _connectionDetail = _bluetoothStatus == "Bluetooth ready"
                ? "Make sure ARMOR-X Pro is powered on and the official mobile app is disconnected."
                : _bluetoothStatus;
            NotifyState();
            return false;
        }
        finally
        {
            _connectionGate.Release();
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
            session.Log += (_, line) => AddLog(line);
            await session.InitializeAsync(cancellationToken);
            _session = session;
            RememberAddress(address);
            StartTelemetry(session);

            _connection = "Connected";
            _connectionDetail = $"{session.Model ?? "ARMOR-X Pro"} · firmware {session.Firmware ?? "—"}";
            AddLog($"Device ready: {_connectionDetail}, battery {session.BatteryPercent?.ToString() ?? "?"}%.");

            var config = await ReadStableConfigAsync(session, cancellationToken);
            LoadDeviceConfig(config);
            _activeProfile = null;
            _guardianCts?.Cancel();
            NotifyState();
            return true;
        }
        catch (Exception ex)
        {
            AddLog("Open device failed: " + ex.Message);
            try { await _transport.DisconnectAsync(); } catch { }
            _session?.Dispose();
            _session = null;
            return false;
        }
    }

    private void StartTelemetry(ArmorXDeviceSession session)
    {
        _telemetryCts?.Cancel();
        _telemetryCts = new CancellationTokenSource();
        var token = _telemetryCts.Token;
        _ = Task.Run(async () =>
        {
            while (!token.IsCancellationRequested)
            {
                try
                {
                    await Task.Delay(TimeSpan.FromSeconds(45), token);
                    if (token.IsCancellationRequested || !ReferenceEquals(_session, session) || !_transport.IsConnected)
                        return;
                    if (_busy) continue;
                    await session.RefreshBatteryAsync(token);
                    NotifyState();
                }
                catch (OperationCanceledException) { return; }
                catch
                {
                    // Battery telemetry is non-critical; the connection guardian handles real disconnects.
                }
            }
        }, token);
    }

    private async Task<object> DisconnectAsync()
    {
        _manualDisconnect = true;
        _guardianCts?.Cancel();
        _telemetryCts?.Cancel();
        return await RunBusyAsync("Disconnecting...", async () =>
        {
            _session?.Dispose();
            _session = null;
            await _transport.DisconnectAsync();
            _connection = "Not connected";
            _connectionDetail = "Power on ARMOR-X Pro, then connect.";
            NotifyState();
            return await BuildStateAsync();
        });
    }

    private async Task<object> ReadConfigAsync()
    {
        var session = RequireSession();
        return await RunBusyAsync("Reading configuration twice...", async () =>
        {
            var config = await ReadStableConfigAsync(session, CancellationToken.None);
            LoadDeviceConfig(config);
            _activeProfile = null;
            return await BuildStateAsync();
        });
    }

    private object PatchConfig(JsonElement payload)
    {
        var cfg = RequireConfig();
        var field = payload.GetProperty("field").GetString() ?? throw new InvalidOperationException("field is required");
        var value = payload.GetProperty("value");

        switch (field)
        {
            case "motorSpeedIdx": cfg.MotorSpeedIdx = value.GetInt32(); break;
            case "motorMax": cfg.MotorMax = value.GetInt32(); break;
            case "triggerMode": cfg.TriggerMode = value.GetInt32(); break;
            case "triggerLeftDeadzoneCenter": cfg.TriggerLeftDeadzoneCenter = value.GetInt32(); break;
            case "triggerLeftDeadzoneSide": cfg.TriggerLeftDeadzoneSide = value.GetInt32(); break;
            case "triggerRightDeadzoneCenter": cfg.TriggerRightDeadzoneCenter = value.GetInt32(); break;
            case "triggerRightDeadzoneSide": cfg.TriggerRightDeadzoneSide = value.GetInt32(); break;
            case "joystickCircleLimit": cfg.JoystickCircleLimit = value.GetInt32(); break;
            case "stickTurn": cfg.StickTurn = value.GetInt32(); break;
            case "leftStickDeadzoneCenter": cfg.LeftStickDeadzoneCenter = value.GetInt32(); break;
            case "leftStickDeadzoneSide": cfg.LeftStickDeadzoneSide = value.GetInt32(); break;
            case "rightStickDeadzoneCenter": cfg.RightStickDeadzoneCenter = value.GetInt32(); break;
            case "rightStickDeadzoneSide": cfg.RightStickDeadzoneSide = value.GetInt32(); break;
            case "sensorMode": cfg.SensorMode = value.GetInt32(); break;
            case "sensorDir": cfg.SensorDir = value.GetInt32(); break;
            case "sensorRightKey0": cfg.SensorRightKey0 = value.GetInt32(); break;
            case "sensorRightKey1": cfg.SensorRightKey1 = value.GetInt32(); break;
            case "sensorMin": cfg.SensorMin = value.GetInt32(); break;
            case "sensorRightKeyBit": cfg.SensorRightKeyBit = value.GetUInt32(); break;
            case "sensorSwitch": cfg.SensorSwitch = value.GetUInt32(); break;
            case "turboSpeedIdx": cfg.TurboSpeedIdx = value.GetInt32(); break;
            case "turboKey": cfg.TurboKey = value.GetUInt32(); break;
            case "m1TargetId": cfg.M1TargetId = value.GetInt32(); break;
            case "m2TargetId": cfg.M2TargetId = value.GetInt32(); break;
            case "m3TargetId": cfg.M3TargetId = value.GetInt32(); break;
            case "m4TargetId": cfg.M4TargetId = value.GetInt32(); break;
            default:
                if (TrySetCurve(cfg.LeftStickCurve, field, "leftCurve.", value)) break;
                if (TrySetCurve(cfg.RightStickCurve, field, "rightCurve.", value)) break;
                if (TrySetCurve(cfg.GyroCurve0, field, "gyro0.", value)) break;
                if (TrySetCurve(cfg.GyroCurve1, field, "gyro1.", value)) break;
                if (TrySetCurve(cfg.GyroCurve2, field, "gyro2.", value)) break;
                throw new InvalidOperationException($"Unsupported configuration field '{field}'.");
        }

        NotifyState();
        return new { ok = true };
    }

    private static bool TrySetCurve(
        System.Collections.ObjectModel.ObservableCollection<ByteFieldViewModel> curve,
        string field, string prefix, JsonElement value)
    {
        if (!field.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) return false;
        if (!int.TryParse(field[prefix.Length..], out var index) || index < 0 || index >= curve.Count)
            throw new InvalidOperationException($"Invalid curve field '{field}'.");
        curve[index].Value = value.GetInt32();
        return true;
    }

    private async Task<object> PrepareApplyAsync()
    {
        var session = RequireSession();
        var cfg = RequireConfig();
        var baseline = _deviceBaseline ?? throw new InvalidOperationException("Read a device baseline before applying.");

        return await RunBusyAsync<object>("Preparing safe write...", async () =>
        {
            var current = await ReadStableConfigAsync(session, CancellationToken.None);
            var desired = cfg.BuildForWrite();
            var target = ConfigDiff.MergeEditorChanges(current, baseline, desired);
            var changes = ConfigDiff.Compare(current, target);

            if (changes.Count == 0)
                return new { noChange = true, changes = Array.Empty<object>(), summary = "No changes need to be written." };

            var token = Guid.NewGuid().ToString("N");
            _preparedWrite = new PreparedWrite(
                token,
                "apply",
                Hash(current.ToArray()),
                target,
                changes,
                DateTimeOffset.UtcNow);

            return new
            {
                noChange = false,
                token,
                currentSha256 = Hash(current.ToArray()),
                targetSha256 = Hash(target.ToArray()),
                currentCrc = $"0x{current.StoredCrc:X4}",
                targetCrc = $"0x{target.StoredCrc:X4}",
                changes = ChangePayload(changes),
                backup = "Automatic pre-write backup will be created before D7.",
                verification = "Two full 144-byte D6 read-backs must match the target."
            };
        });
    }

    private async Task<object> CommitApplyAsync(JsonElement payload)
    {
        var token = payload.GetProperty("token").GetString() ?? string.Empty;
        var prepared = RequirePrepared(token, "apply");
        var session = RequireSession();

        return await RunExclusiveWriteAsync("Applying and verifying...", async () =>
        {
            var current = await ReadStableConfigAsync(session, CancellationToken.None);
            if (!string.Equals(Hash(current.ToArray()), prepared.CurrentSha256, StringComparison.Ordinal))
            {
                _preparedWrite = null;
                throw new InvalidOperationException(
                    "Device configuration changed after review. Nothing was written. Review the updated diff again.");
            }

            var backupPath = await _backups.SaveAsync(current, session.Model, session.Firmware, "pre-write");
            _lastBackupName = Path.GetFileName(backupPath);
            AddLog($"Pre-write backup saved: {_lastBackupName}");

            var result = await session.WriteAndVerifyAsync(prepared.Target);
            LoadDeviceConfig(result.ReadBackConfig);
            _preparedWrite = null;

            if (!result.ExactMatch)
                throw new InvalidOperationException(
                    $"Write verification failed. {result.MismatchOffsets.Count} offset(s) differ. " +
                    "The actual read-back is loaded and the pre-write backup is preserved.");

            AddLog($"Apply verified with two matching D6 reads; CRC 0x{result.ReadBackConfig.StoredCrc:X4}.");
            return new
            {
                status = "APPLIED",
                ackSeen = result.AckSeen,
                postWriteEchoSeen = result.PostWriteEchoSeen,
                verificationReadsAgree = result.VerificationReadsAgree,
                sha256 = Hash(result.ReadBackConfig.ToArray()),
                crc = $"0x{result.ReadBackConfig.StoredCrc:X4}",
                backup = _lastBackupName
            };
        });
    }

    private async Task<object> PrepareRestoreAsync()
    {
        var session = RequireSession();
        return await RunBusyAsync<object>("Preparing backup restore...", async () =>
        {
            var backup = await _backups.LoadLatestAsync() ??
                         throw new InvalidOperationException("No automatic backup is available.");
            var target = new ArmorXConfig144(backup.GetConfigBytes());
            if (!target.CrcValid) throw new InvalidDataException("Latest backup CRC is invalid.");

            var current = await ReadStableConfigAsync(session, CancellationToken.None);
            var changes = ConfigDiff.Compare(current, target);
            if (changes.Count == 0)
                return new { noChange = true, summary = "The latest backup already matches the controller." };

            var token = Guid.NewGuid().ToString("N");
            _preparedWrite = new PreparedWrite(
                token, "restore", Hash(current.ToArray()), target, changes, DateTimeOffset.UtcNow);

            return new
            {
                noChange = false,
                token,
                currentSha256 = Hash(current.ToArray()),
                targetSha256 = Hash(target.ToArray()),
                currentCrc = $"0x{current.StoredCrc:X4}",
                targetCrc = $"0x{target.StoredCrc:X4}",
                backupDate = backup.SavedUtc.LocalDateTime.ToString("G"),
                backupReason = backup.Reason,
                changes = ChangePayload(changes),
                verification = "The exact saved 144-byte image will be written and verified twice."
            };
        });
    }

    private async Task<object> CommitRestoreAsync(JsonElement payload)
    {
        var token = payload.GetProperty("token").GetString() ?? string.Empty;
        var prepared = RequirePrepared(token, "restore");
        var session = RequireSession();

        return await RunExclusiveWriteAsync("Restoring backup and verifying...", async () =>
        {
            var current = await ReadStableConfigAsync(session, CancellationToken.None);
            if (!string.Equals(Hash(current.ToArray()), prepared.CurrentSha256, StringComparison.Ordinal))
            {
                _preparedWrite = null;
                throw new InvalidOperationException(
                    "Device configuration changed after restore review. Nothing was written.");
            }

            var undoPath = await _backups.SaveAsync(current, session.Model, session.Firmware, "pre-restore");
            _lastBackupName = Path.GetFileName(undoPath);
            var result = await session.WriteAndVerifyAsync(prepared.Target);
            LoadDeviceConfig(result.ReadBackConfig);
            _preparedWrite = null;

            if (!result.ExactMatch)
                throw new InvalidOperationException(
                    $"Restore verification failed at {result.MismatchOffsets.Count} offset(s). " +
                    "The actual read-back is loaded and the undo backup is preserved.");

            _activeProfile = null;
            return new
            {
                status = "RESTORED",
                ackSeen = result.AckSeen,
                postWriteEchoSeen = result.PostWriteEchoSeen,
                verificationReadsAgree = result.VerificationReadsAgree,
                sha256 = Hash(result.ReadBackConfig.ToArray()),
                crc = $"0x{result.ReadBackConfig.StoredCrc:X4}"
            };
        });
    }

    private async Task<object> SaveProfileAsync(JsonElement payload)
    {
        var cfg = RequireConfig();
        var name = payload.GetProperty("name").GetString()?.Trim();
        if (string.IsNullOrWhiteSpace(name)) throw new InvalidOperationException("Profile name is required.");
        await _profiles.SaveAsync(name, cfg.BuildForWrite(), _session?.Model, _session?.Firmware);
        _activeProfile = name;
        AddLog($"Profile saved: {name}");
        NotifyState();
        return await BuildStateAsync();
    }

    private async Task<object> LoadProfileAsync(JsonElement payload)
    {
        var name = payload.GetProperty("name").GetString() ?? throw new InvalidOperationException("Profile name is required.");
        var profile = await _profiles.LoadAsync(name);
        _config = new EditableArmorXConfig(new ArmorXConfig144(profile.GetConfigBytes()));
        _config.Changed += (_, _) => NotifyState();
        _activeProfile = profile.Name;
        AddLog($"Profile loaded into editor: {profile.Name}; controller unchanged.");
        NotifyState();
        return await BuildStateAsync();
    }

    private async Task<object> DeleteProfileAsync(JsonElement payload)
    {
        var name = payload.GetProperty("name").GetString() ?? string.Empty;
        await _profiles.DeleteAsync(name);
        if (string.Equals(_activeProfile, name, StringComparison.OrdinalIgnoreCase)) _activeProfile = null;
        NotifyState();
        return await BuildStateAsync();
    }

    private async Task<object> RenameProfileAsync(JsonElement payload)
    {
        var from = payload.GetProperty("from").GetString() ?? string.Empty;
        var to = payload.GetProperty("to").GetString() ?? string.Empty;
        await _profiles.RenameAsync(from, to);
        if (string.Equals(_activeProfile, from, StringComparison.OrdinalIgnoreCase)) _activeProfile = to;
        NotifyState();
        return await BuildStateAsync();
    }

    private async Task<object> DuplicateProfileAsync(JsonElement payload)
    {
        var from = payload.GetProperty("from").GetString() ?? string.Empty;
        var to = payload.GetProperty("to").GetString() ?? string.Empty;
        await _profiles.DuplicateAsync(from, to);
        NotifyState();
        return await BuildStateAsync();
    }

    private async Task<object> ImportProfileAsync()
    {
        var dialog = new Microsoft.Win32.OpenFileDialog
        {
            Title = "Import ArmorX profile",
            Filter = "ArmorX profile (*.json)|*.json|JSON files (*.json)|*.json"
        };
        if (dialog.ShowDialog() != true) return new { cancelled = true };
        var profile = await _profiles.ImportAsync(dialog.FileName);
        NotifyState();
        return new { cancelled = false, name = profile.Name };
    }

    private async Task<object> ExportProfileAsync(JsonElement payload)
    {
        var name = payload.GetProperty("name").GetString() ?? string.Empty;
        var dialog = new Microsoft.Win32.SaveFileDialog
        {
            Title = "Export ArmorX profile",
            FileName = name + ".json",
            DefaultExt = ".json",
            Filter = "ArmorX profile (*.json)|*.json"
        };
        if (dialog.ShowDialog() != true) return new { cancelled = true };
        await _profiles.ExportAsync(name, dialog.FileName);
        return new { cancelled = false, file = Path.GetFileName(dialog.FileName) };
    }

    private object OpenTextFile(JsonElement payload)
    {
        var filter = payload.TryGetProperty("filter", out var f) ? f.GetString() : null;
        var dialog = new Microsoft.Win32.OpenFileDialog
        {
            Title = payload.TryGetProperty("title", out var t) ? t.GetString() ?? "Open file" : "Open file",
            Filter = string.IsNullOrWhiteSpace(filter) ? "JSON files (*.json)|*.json|All files (*.*)|*.*" : filter
        };
        if (dialog.ShowDialog() != true) return new { cancelled = true };
        return new
        {
            cancelled = false,
            name = Path.GetFileName(dialog.FileName),
            text = File.ReadAllText(dialog.FileName, Encoding.UTF8)
        };
    }

    private object SaveTextFile(JsonElement payload)
    {
        var suggested = payload.TryGetProperty("name", out var n) ? n.GetString() : "armorx.json";
        var text = payload.GetProperty("text").GetString() ?? string.Empty;
        var dialog = new Microsoft.Win32.SaveFileDialog
        {
            Title = payload.TryGetProperty("title", out var t) ? t.GetString() ?? "Save file" : "Save file",
            FileName = suggested,
            DefaultExt = ".json",
            Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*"
        };
        if (dialog.ShowDialog() != true) return new { cancelled = true };
        File.WriteAllText(dialog.FileName, text, new UTF8Encoding(false));
        return new { cancelled = false, name = Path.GetFileName(dialog.FileName) };
    }

    private async Task<object> ExportDiagnosticsAsync()
    {
        var dialog = new Microsoft.Win32.SaveFileDialog
        {
            Title = "Export ArmorX Studio diagnostics",
            FileName = $"ArmorX-Studio-Diagnostics-{DateTime.Now:yyyyMMdd-HHmmss}.txt",
            DefaultExt = ".txt",
            Filter = "Text file (*.txt)|*.txt"
        };
        if (dialog.ShowDialog() != true) return new { cancelled = true };
        await _diagnostics.ExportAsync(
            dialog.FileName,
            _session?.Model ?? "—",
            _session?.Firmware ?? "—",
            _connection,
            PendingSummary());
        return new { cancelled = false, name = Path.GetFileName(dialog.FileName) };
    }

    private object OpenFolder(string path)
    {
        Directory.CreateDirectory(path);
        Process.Start(new ProcessStartInfo("explorer.exe", path) { UseShellExecute = true });
        return new { ok = true };
    }

    private object OpenUrl(string url)
    {
        Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        return new { ok = true };
    }

    private object RequestHide()
    {
        HideRequested?.Invoke(this, EventArgs.Empty);
        return new { ok = true };
    }

    private object RequestExit()
    {
        ExitRequested?.Invoke(this, EventArgs.Empty);
        return new { ok = true };
    }

    public async Task<object> BuildStateAsync()
    {
        var profileRows = await _profiles.ListAsync();
        return new
        {
            app = new
            {
                name = "ArmorX Studio",
                version = AppVersion,
                platform = "Windows",
                projectUrl = "https://github.com/feshinkof-boop/armorx-toolkit"
            },
            connection = new
            {
                connected = _session is not null && _transport.IsConnected,
                headline = _connection,
                detail = _connectionDetail,
                bluetooth = _bluetoothStatus,
                model = _session?.Model,
                firmware = _session?.Firmware,
                battery = _session?.BatteryPercent,
                discovered = _transport.ScanSnapshot
                    .Where(x => ArmorXBleTransport.LooksLikeArmorXName(x.Name))
                    .OrderByDescending(x => x.Rssi)
                    .Take(8)
                    .Select(x => new
                    {
                        name = string.IsNullOrWhiteSpace(x.Name) ? "ARMOR-X candidate" : x.Name,
                        rssi = x.Rssi == short.MinValue ? (short?)null : x.Rssi,
                        source = x.DiscoverySource,
                        lastSeen = x.LastSeenUtc
                    })
                    .ToArray()
            },
            busy = new { active = _busy, text = _busyText },
            config = ConfigPayload(_config, _deviceBaseline),
            profiles = profileRows.Select(x => new
            {
                name = x.Name,
                savedUtc = x.SavedUtc,
                model = x.DeviceModel,
                firmware = x.Firmware
            }).ToArray(),
            activeProfile = _activeProfile,
            lastBackup = _lastBackupName,
            diagnostics = _log.Reverse().Take(80).Reverse().ToArray()
        };
    }

    private object? ConfigPayload(EditableArmorXConfig? cfg, byte[]? baseline)
    {
        if (cfg is null) return null;
        var desired = cfg.BuildForWrite();
        var pending = baseline is { Length: ArmorXConfig144.Size }
            ? ConfigDiff.CompareEditable(baseline, desired.ToArray())
            : Array.Empty<ConfigByteChange>();
        var baselineEditor = baseline is { Length: ArmorXConfig144.Size }
            ? new EditableArmorXConfig(new ArmorXConfig144(baseline))
            : null;

        return new
        {
            crc = $"0x{desired.StoredCrc:X4}",
            crcValid = desired.CrcValid,
            pending = ChangePayload(pending),
            fields = ConfigFields(cfg),
            baseline = baselineEditor is null ? null : ConfigFields(baselineEditor),
            curves = new
            {
                left = cfg.LeftStickCurve.Select(x => x.Value).ToArray(),
                right = cfg.RightStickCurve.Select(x => x.Value).ToArray(),
                gyro0 = cfg.GyroCurve0.Select(x => x.Value).ToArray(),
                gyro1 = cfg.GyroCurve1.Select(x => x.Value).ToArray(),
                gyro2 = cfg.GyroCurve2.Select(x => x.Value).ToArray()
            },
            baselineCurves = baselineEditor is null ? null : new
            {
                left = baselineEditor.LeftStickCurve.Select(x => x.Value).ToArray(),
                right = baselineEditor.RightStickCurve.Select(x => x.Value).ToArray(),
                gyro0 = baselineEditor.GyroCurve0.Select(x => x.Value).ToArray(),
                gyro1 = baselineEditor.GyroCurve1.Select(x => x.Value).ToArray(),
                gyro2 = baselineEditor.GyroCurve2.Select(x => x.Value).ToArray()
            },
            mappings = new
            {
                m1 = cfg.M1TargetId, m2 = cfg.M2TargetId,
                m3 = cfg.M3TargetId, m4 = cfg.M4TargetId
            },
            baselineMappings = baselineEditor is null ? null : new
            {
                m1 = baselineEditor.M1TargetId, m2 = baselineEditor.M2TargetId,
                m3 = baselineEditor.M3TargetId, m4 = baselineEditor.M4TargetId
            },
            mappingTargets = EditableArmorXConfig.ProvenMappingTargets.Select(x => new { id = x.Id, name = x.Name }).ToArray()
        };
    }

    private static object ConfigFields(EditableArmorXConfig cfg) => new
    {
        motorSpeedIdx = cfg.MotorSpeedIdx,
        motorMax = cfg.MotorMax,
        triggerMode = cfg.TriggerMode,
        triggerLeftDeadzoneCenter = cfg.TriggerLeftDeadzoneCenter,
        triggerLeftDeadzoneSide = cfg.TriggerLeftDeadzoneSide,
        triggerRightDeadzoneCenter = cfg.TriggerRightDeadzoneCenter,
        triggerRightDeadzoneSide = cfg.TriggerRightDeadzoneSide,
        joystickCircleLimit = cfg.JoystickCircleLimit,
        stickTurn = cfg.StickTurn,
        leftStickDeadzoneCenter = cfg.LeftStickDeadzoneCenter,
        leftStickDeadzoneSide = cfg.LeftStickDeadzoneSide,
        rightStickDeadzoneCenter = cfg.RightStickDeadzoneCenter,
        rightStickDeadzoneSide = cfg.RightStickDeadzoneSide,
        sensorMode = cfg.SensorMode,
        sensorDir = cfg.SensorDir,
        sensorRightKey0 = cfg.SensorRightKey0,
        sensorRightKey1 = cfg.SensorRightKey1,
        sensorMin = cfg.SensorMin,
        sensorRightKeyBit = cfg.SensorRightKeyBit,
        sensorSwitch = cfg.SensorSwitch,
        turboSpeedIdx = cfg.TurboSpeedIdx,
        turboKey = cfg.TurboKey
    };

    private static object[] ChangePayload(IReadOnlyList<ConfigByteChange> changes) =>
        changes.Select(x => (object)new
        {
            offset = x.Offset,
            before = x.Before,
            after = x.After,
            label = x.Label
        }).ToArray();

    private string PendingSummary()
    {
        if (_config is null || _deviceBaseline is null) return "No device baseline loaded.";
        var pending = ConfigDiff.CompareEditable(_deviceBaseline, _config.BuildForWrite().ToArray());
        return pending.Count == 0 ? "No pending configuration changes." : $"{pending.Count} pending editable byte change(s).";
    }

    private async Task<ArmorXConfig144> ReadStableConfigAsync(
        ArmorXDeviceSession session,
        CancellationToken cancellationToken)
    {
        var first = await session.ReadConfigAsync(cancellationToken);
        var second = await session.ReadConfigAsync(cancellationToken);
        if (!first.CrcValid || !second.CrcValid)
            throw new InvalidDataException("Configuration CRC validation failed.");
        if (!first.ToArray().SequenceEqual(second.ToArray()))
            throw new InvalidDataException("Two live configuration reads disagree. Nothing will be written.");
        return second;
    }

    private void LoadDeviceConfig(ArmorXConfig144 config)
    {
        if (!config.CrcValid) throw new InvalidDataException("Refusing invalid-CRC device configuration.");
        _deviceBaseline = config.ToArray();
        _config = new EditableArmorXConfig(new ArmorXConfig144(config.ToArray()));
        _config.Changed += (_, _) => NotifyState();
        NotifyState();
    }

    private PreparedWrite RequirePrepared(string token, string kind)
    {
        var prepared = _preparedWrite;
        if (prepared is null ||
            !string.Equals(prepared.Token, token, StringComparison.Ordinal) ||
            !string.Equals(prepared.Kind, kind, StringComparison.Ordinal) ||
            DateTimeOffset.UtcNow - prepared.CreatedUtc > TimeSpan.FromMinutes(5))
            throw new InvalidOperationException("The reviewed write plan expired. Review it again.");
        return prepared;
    }

    private ArmorXDeviceSession RequireSession() =>
        _session is not null && _transport.IsConnected
            ? _session
            : throw new InvalidOperationException("Connect ARMOR-X Pro first.");

    private EditableArmorXConfig RequireConfig() =>
        _config ?? throw new InvalidOperationException("Load a controller configuration first.");

    private async Task<T> RunBusyAsync<T>(string text, Func<Task<T>> action)
    {
        if (_busy) throw new InvalidOperationException("ArmorX Studio is already busy.");
        _busy = true;
        _busyText = text;
        NotifyState();
        try { return await action(); }
        finally
        {
            _busy = false;
            _busyText = string.Empty;
            NotifyState();
        }
    }

    private async Task<T> RunExclusiveWriteAsync<T>(string text, Func<Task<T>> action)
    {
        if (!await _operationGate.WaitAsync(0))
            throw new InvalidOperationException("Another controller operation is already running.");
        try { return await RunBusyAsync(text, action); }
        finally { _operationGate.Release(); }
    }

    private void AddLog(string message)
    {
        var line = $"{DateTime.Now:HH:mm:ss}  {message}";
        _log.Enqueue(line);
        while (_log.Count > 300) _log.TryDequeue(out _);
        _diagnostics.Add(message);
        NotifyState();
    }

    private void NotifyState() => StateChanged?.Invoke(this, EventArgs.Empty);

    private static string Hash(byte[] bytes) =>
        Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    private void RememberAddress(ulong address)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(LastDevicePath)!);
        File.WriteAllText(LastDevicePath, address.ToString("X12"));
    }

    private bool TryLoadRememberedAddress(out ulong address)
    {
        address = 0;
        try
        {
            return File.Exists(LastDevicePath) &&
                   ulong.TryParse(File.ReadAllText(LastDevicePath).Trim(),
                       System.Globalization.NumberStyles.HexNumber, null, out address);
        }
        catch { return false; }
    }

    public async ValueTask DisposeAsync()
    {
        _closing = true;
        _guardianCts?.Cancel();
        _telemetryCts?.Cancel();
        _session?.Dispose();
        await _transport.DisposeAsync();
        _connectionGate.Dispose();
        _operationGate.Dispose();
    }

    private sealed record PreparedWrite(
        string Token,
        string Kind,
        string CurrentSha256,
        ArmorXConfig144 Target,
        IReadOnlyList<ConfigByteChange> Changes,
        DateTimeOffset CreatedUtc);
}
