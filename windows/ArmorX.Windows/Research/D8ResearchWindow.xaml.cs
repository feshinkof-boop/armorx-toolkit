using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Windows;
using Microsoft.Win32;
using ArmorX.Windows.Bluetooth;
using ArmorX.Windows.Config;
using ArmorX.Windows.Device;
using ArmorX.Windows.Protocol;

namespace ArmorX.Windows.Research;

public partial class D8ResearchWindow : Window
{
    private readonly ArmorXBleTransport _transport = new();
    private ArmorXDeviceSession? _session;
    private CancellationTokenSource? _runCts;
    private bool _running;
    private bool _closing;
    private int _sequence;
    private readonly object _captureLock = new();
    private readonly List<CapturedPacket> _captured = new();
    private string? _evidenceDirectory;

    private string LastDevicePath => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "ArmorX", "last-device.txt");

    public D8ResearchWindow()
    {
        InitializeComponent();

        _transport.PacketReceived += Transport_PacketReceived;
        _transport.ConnectionChanged += Transport_ConnectionChanged;
        _transport.Log += (_, message) => AppendLog("BLE " + message);

        Loaded += async (_, _) =>
        {
            _transport.EnsurePersistentDiscovery();
            var adapter = await _transport.GetAdapterStatusAsync();
            ConnectionText.Text = adapter;
            AppendLog("Adapter: " + adapter);
        };

        Closing += async (_, _) =>
        {
            _closing = true;
            _runCts?.Cancel();
            _session?.Dispose();
            await _transport.DisposeAsync();
        };
    }

    private async void Run_Click(object sender, RoutedEventArgs e)
    {
        if (_running) return;

        var answer = MessageBox.Show(
            "Before this run:\n\n" +
            "1. ARMOR-X Pro is physically attached to the Xbox controller.\n" +
            "2. USB dongle is unplugged.\n" +
            "3. BIGBIG WON mobile/Windows app is closed.\n" +
            "4. ARMOR-X Pro is powered on.\n\n" +
            "This Stage-1 run sends only proven initialization/config-read traffic plus the recovered read-only D5/GetMacroList request. It DOES NOT transmit D8 macro writes.\n\n" +
            "Start the autonomous discovery run?",
            "D8 Macro Discovery",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);

        if (answer != MessageBoxResult.Yes) return;

        _running = true;
        RunButton.IsEnabled = false;
        AbortButton.IsEnabled = true;
        _runCts = new CancellationTokenSource();

        lock (_captureLock)
        {
            _captured.Clear();
            _sequence = 0;
        }

        try
        {
            await RunDiscoveryAsync(_runCts.Token);
        }
        catch (OperationCanceledException)
        {
            SetStep(0, "Run aborted.", "No further device traffic will be sent.");
            AppendLog("RUN ABORTED");
            await FinalizePartialEvidenceAsync("aborted");
        }
        catch (Exception ex)
        {
            SetStep(0, "Run stopped by an error.", ex.Message);
            AppendLog("ERROR " + ex);
            await FinalizePartialEvidenceAsync("error", ex);
            MessageBox.Show(ex.Message, "D8 discovery error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            _running = false;
            RunButton.IsEnabled = true;
            AbortButton.IsEnabled = false;
            _runCts?.Dispose();
            _runCts = null;
        }
    }

    private void Abort_Click(object sender, RoutedEventArgs e) => _runCts?.Cancel();

    private async Task RunDiscoveryAsync(CancellationToken cancellationToken)
    {
        SetStep(5, "Finding ARMOR-X Pro automatically...", "Turn ARMOR-X Pro on and leave it on. Do not use another BLE app.");
        if (!await EnsureConnectedAsync(cancellationToken))
            throw new InvalidOperationException("ARMOR-X Pro could not be found within the recovery window.");

        var stamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
        _evidenceDirectory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "ArmorX", "Research", "D8", stamp);
        Directory.CreateDirectory(_evidenceDirectory);

        SetStep(15, "Saving the current D6 configuration baseline...", "Do not press buttons yet.");
        var baseline = await RequireSession().ReadConfigAsync(cancellationToken);
        var baselineBytes = baseline.ToArray();
        await File.WriteAllBytesAsync(Path.Combine(_evidenceDirectory, "baseline-config-144.bin"), baselineBytes, cancellationToken);
        await File.WriteAllTextAsync(
            Path.Combine(_evidenceDirectory, "baseline-config-144.hex.txt"),
            Convert.ToHexString(baselineBytes).ToLowerInvariant(),
            cancellationToken);

        var baselineMetadata = new
        {
            model = _session?.Model,
            firmware = _session?.Firmware,
            battery = _session?.BatteryPercent,
            crc_valid = baseline.CrcValid,
            crc = $"0x{baseline.StoredCrc:X4}",
            sha256 = Sha256(baselineBytes),
            captured_utc = DateTimeOffset.UtcNow
        };
        await WriteJsonAsync(Path.Combine(_evidenceDirectory, "baseline.json"), baselineMetadata, cancellationToken);
        AppendLog($"Baseline saved: CRC=0x{baseline.StoredCrc:X4}, SHA256={baselineMetadata.sha256}");

        var probes = new List<D5ProbeEvidence>();
        for (var i = 1; i <= 3; i++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            await EnsureConnectedOrRecoverAsync(cancellationToken);

            SetStep(20 + i * 15,
                $"Read-only D5 macro-list probe {i}/3...",
                "No physical action required. Keep the controller powered on.");

            var start = DateTimeOffset.UtcNow;
            var startSequence = CurrentSequence;
            RecordTx(ArmorXFrames.GetMacroList, $"D5/GetMacroList probe {i}");
            await _transport.WriteAsync(ArmorXFrames.GetMacroList, cancellationToken);
            await Task.Delay(TimeSpan.FromSeconds(3), cancellationToken);
            var end = DateTimeOffset.UtcNow;

            var packets = Snapshot(startSequence)
                .Where(x => x.Direction == "RX" && x.Bytes.Length >= 3 && x.Bytes[2] == ArmorXFrames.OpGetMacroList)
                .ToArray();

            var payload = ReassembleLongPayload(packets.Select(x => x.Bytes), ArmorXFrames.OpGetMacroList);
            var probe = new D5ProbeEvidence(
                i,
                start,
                end,
                ArmorXFrames.Hex(ArmorXFrames.GetMacroList),
                packets.Select(ToPacketEvidence).ToArray(),
                payload is null ? null : Convert.ToHexString(payload).ToLowerInvariant(),
                payload is null ? null : Sha256(payload));

            probes.Add(probe);
            await WriteJsonAsync(Path.Combine(_evidenceDirectory, $"d5-probe-{i}.json"), probe, cancellationToken);
            AppendLog(payload is null
                ? $"D5 probe {i}: no complete A4/D5 payload reconstructed."
                : $"D5 probe {i}: {payload.Length} payload bytes, SHA256={Sha256(payload)}");
        }

        var nonNullHashes = probes.Where(x => x.PayloadSha256 is not null).Select(x => x.PayloadSha256!).ToArray();
        var d5Stable = nonNullHashes.Length >= 2 && nonNullHashes.Distinct(StringComparer.OrdinalIgnoreCase).Count() == 1;

        SetStep(75, "Passive BLE observation: 8 seconds...", "Leave the controller untouched unless it powers off; if it does, turn it back on.");
        var passiveStart = DateTimeOffset.UtcNow;
        await Task.Delay(TimeSpan.FromSeconds(8), cancellationToken);
        var passiveEnd = DateTimeOffset.UtcNow;

        SetStep(88, "Analyzing captured D8 evidence...", "No D8 write will be attempted.");
        var snapshot = Snapshot(0);
        var d8Analysis = D8CaptureAnalyzer.AnalyzePackets(snapshot.Select(x => x.Bytes), "live-research-run");
        await WriteJsonAsync(Path.Combine(_evidenceDirectory, "d8-live-analysis.json"), d8Analysis, cancellationToken);
        await File.WriteAllTextAsync(
            Path.Combine(_evidenceDirectory, "d8-live-analysis.md"),
            D8CaptureAnalyzer.ToMarkdown(d8Analysis),
            cancellationToken);

        await WriteRawJsonlAsync(snapshot, Path.Combine(_evidenceDirectory, "ble-evidence.jsonl"), cancellationToken);

        var summary = new
        {
            app_version = "0.3.0-research.1",
            stage = "D8 macro discovery Stage 1",
            started_from_validated_public_code = "5133de9612e83613dd8741f9f61f51910c2ee77f",
            device = new { model = _session?.Model, firmware = _session?.Firmware, battery = _session?.BatteryPercent },
            baseline = baselineMetadata,
            d5_request = Convert.ToHexString(ArmorXFrames.GetMacroList).ToLowerInvariant(),
            d5_probe_count = probes.Count,
            d5_complete_payload_count = probes.Count(x => x.PayloadSha256 is not null),
            d5_repeated_payload_stable = d5Stable,
            d8_candidate_frames_observed = d8Analysis.CandidateFrameCount,
            d8_valid_a4_frames_observed = d8Analysis.ValidD8FrameCount,
            d8_transfer_groups_reconstructed = d8Analysis.Transfers.Count,
            passive_window = new { started_utc = passiveStart, ended_utc = passiveEnd },
            safety = new
            {
                d8_tx_enabled = false,
                guessed_macro_payloads_sent = false,
                statement = "Only known initialization/config-read traffic and A504D57E D5/GetMacroList are intentionally transmitted by the D8 discovery workflow."
            },
            next_gate = d8Analysis.Transfers.Count > 0
                ? "Correlate controlled D8 variants before enabling any D8 writer."
                : "Obtain/import official-client D8 captures with controlled one-variable macro changes; do not guess the payload."
        };
        await WriteJsonAsync(Path.Combine(_evidenceDirectory, "d8-discovery-summary.json"), summary, cancellationToken);

        var readme = BuildEvidenceReadme(probes, d5Stable, d8Analysis);
        await File.WriteAllTextAsync(Path.Combine(_evidenceDirectory, "README.txt"), readme, cancellationToken);

        SetStep(96, "Packaging one evidence ZIP...", "Almost done.");
        var zip = CreateEvidenceZip(_evidenceDirectory);
        SetStep(100, "D8 Stage-1 discovery complete.", "Upload the generated ZIP to ChatGPT. Do not run separate manual tests.");
        OutputText.Text = zip;
        FooterText.Text = $"Complete. D8 TX remained locked. Evidence ZIP: {zip}";
        AppendLog("EVIDENCE ZIP " + zip);

        MessageBox.Show(
            "D8 discovery is complete.\n\nUpload this single ZIP to ChatGPT:\n" + zip +
            "\n\nDo not run additional manual macro writes yet.",
            "D8 discovery complete",
            MessageBoxButton.OK,
            MessageBoxImage.Information);
    }

    private async void ImportCapture_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "Import a text/JSONL BLE capture containing raw hexadecimal frames",
            Filter = "Capture text (*.jsonl;*.txt;*.log)|*.jsonl;*.txt;*.log|All files (*.*)|*.*"
        };
        if (dialog.ShowDialog(this) != true) return;

        try
        {
            var analysis = D8CaptureAnalyzer.AnalyzeFile(dialog.FileName);
            var basePath = Path.Combine(
                Path.GetDirectoryName(dialog.FileName) ?? Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                Path.GetFileNameWithoutExtension(dialog.FileName) + ".d8-analysis");
            await File.WriteAllTextAsync(basePath + ".md", D8CaptureAnalyzer.ToMarkdown(analysis));
            await File.WriteAllTextAsync(basePath + ".json", JsonSerializer.Serialize(analysis, JsonOptions));
            AppendLog($"Imported capture: {analysis.ValidD8FrameCount} valid A4/D8 frames, {analysis.Transfers.Count} transfer(s).");
            MessageBox.Show(
                $"Analysis complete.\n\nValid A4/D8 frames: {analysis.ValidD8FrameCount}\nTransfers: {analysis.Transfers.Count}\n\nSaved:\n{basePath}.md\n{basePath}.json",
                "D8 capture analysis",
                MessageBoxButton.OK,
                MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "Import failed", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private async Task<bool> EnsureConnectedAsync(CancellationToken cancellationToken)
    {
        if (_transport.IsConnected && _session is not null) return true;

        _transport.EnsurePersistentDiscovery();
        await _transport.EnumerateWindowsCachedArmorXAsync(cancellationToken);

        var tried = new HashSet<ulong>();
        var deadline = DateTime.UtcNow + TimeSpan.FromMinutes(2);

        while (DateTime.UtcNow < deadline)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var candidates = new List<ulong>();
            if (TryLoadRememberedAddress(out var remembered)) candidates.Add(remembered);
            candidates.AddRange(_transport.ScanSnapshot
                .Where(x => ArmorXBleTransport.LooksLikeArmorXName(x.Name))
                .OrderByDescending(x => x.Rssi)
                .Select(x => x.Address));

            foreach (var address in candidates.Distinct())
            {
                if (!tried.Add(address) && DateTime.UtcNow < deadline - TimeSpan.FromSeconds(20)) continue;
                if (await TryOpenAsync(address, cancellationToken)) return true;
            }

            ConnectionText.Text = "Waiting for ARMOR-X Pro...";
            ActionText.Text = "Turn ARMOR-X Pro on. The app is searching and will reconnect automatically.";
            await Task.Delay(1500, cancellationToken);
            if (tried.Count > 0 && DateTime.UtcNow.Second % 10 < 2) tried.Clear();
        }

        return false;
    }

    private async Task EnsureConnectedOrRecoverAsync(CancellationToken cancellationToken)
    {
        if (_transport.IsConnected && _session is not null) return;
        AppendLog("Link lost. Automatic recovery started.");
        SetStep((int)RunProgress.Value, "ARMOR-X disconnected.", "Turn ARMOR-X Pro on. Recovery is automatic.");
        if (!await EnsureConnectedAsync(cancellationToken))
            throw new TimeoutException("Automatic BLE recovery timed out.");
        AppendLog("Link recovered.");
    }

    private async Task<bool> TryOpenAsync(ulong address, CancellationToken cancellationToken)
    {
        try
        {
            _session?.Dispose();
            _session = null;
            await _transport.ConnectAsync(address, cancellationToken);
            var session = new ArmorXDeviceSession(_transport);
            session.Log += (_, message) => AppendLog("SESSION " + message);
            await session.InitializeAsync(cancellationToken);
            _session = session;
            RememberAddress(address);
            ConnectionText.Text = $"Connected · {session.Model ?? "ARMOR-X Pro"} · FW {session.Firmware ?? "?"} · {session.BatteryPercent?.ToString() ?? "?"}%";
            AppendLog(ConnectionText.Text);
            return true;
        }
        catch (Exception ex)
        {
            AppendLog($"Connect attempt failed: {ex.Message}");
            try { await _transport.DisconnectAsync(); } catch { }
            _session?.Dispose();
            _session = null;
            return false;
        }
    }

    private void Transport_PacketReceived(object? sender, byte[] packet)
    {
        var copy = packet.ToArray();
        lock (_captureLock)
        {
            _captured.Add(new CapturedPacket(
                ++_sequence,
                DateTimeOffset.UtcNow,
                "RX",
                copy,
                ArmorXFrames.IsValid(copy)));
        }

        Dispatcher.Invoke(() => AppendLog($"RX {ArmorXFrames.Hex(copy)}"));
    }

    private void RecordTx(byte[] packet, string label)
    {
        var copy = packet.ToArray();
        lock (_captureLock)
        {
            _captured.Add(new CapturedPacket(
                ++_sequence,
                DateTimeOffset.UtcNow,
                "TX",
                copy,
                ArmorXFrames.IsValid(copy)));
        }
        AppendLog($"TX {label}: {ArmorXFrames.Hex(copy)}");
    }

    private void Transport_ConnectionChanged(object? sender, bool connected)
    {
        Dispatcher.Invoke(() =>
        {
            if (connected) return;
            ConnectionText.Text = "Disconnected / asleep";
            if (_running)
            {
                ActionText.Text = "Turn ARMOR-X Pro on. The next stage will recover automatically.";
                AppendLog("ConnectionChanged: disconnected");
            }
        });
    }

    private ArmorXDeviceSession RequireSession() =>
        _session ?? throw new InvalidOperationException("ARMOR-X session is not available.");

    private int CurrentSequence
    {
        get { lock (_captureLock) return _sequence; }
    }

    private CapturedPacket[] Snapshot(int afterSequence)
    {
        lock (_captureLock)
            return _captured.Where(x => x.Sequence > afterSequence).Select(x => x with { Bytes = x.Bytes.ToArray() }).ToArray();
    }

    private static byte[]? ReassembleLongPayload(IEnumerable<byte[]> frames, byte opcode)
    {
        var valid = frames
            .Where(x => x.Length >= 5 && x[0] == ArmorXFrames.LongHeader && x[2] == opcode && ArmorXFrames.IsValid(x))
            .ToArray();
        if (valid.Length == 0) return null;

        var byIndex = valid.GroupBy(x => (int)x[3]).ToDictionary(g => g.Key, g => g.Last());
        var max = byIndex.Keys.Max();
        if (max < 1 || Enumerable.Range(1, max).Any(i => !byIndex.ContainsKey(i))) return null;

        return Enumerable.Range(1, max)
            .SelectMany(i => byIndex[i].AsSpan(4, byIndex[i].Length - 5).ToArray())
            .ToArray();
    }

    private async Task WriteRawJsonlAsync(IEnumerable<CapturedPacket> packets, string path, CancellationToken cancellationToken)
    {
        var sb = new StringBuilder();
        foreach (var packet in packets)
        {
            sb.AppendLine(JsonSerializer.Serialize(new
            {
                sequence = packet.Sequence,
                timestamp_utc = packet.TimestampUtc,
                direction = packet.Direction,
                valid = packet.Valid,
                hex = Convert.ToHexString(packet.Bytes).ToLowerInvariant()
            }));
        }
        await File.WriteAllTextAsync(path, sb.ToString(), cancellationToken);
    }

    private static PacketEvidence ToPacketEvidence(CapturedPacket packet) =>
        new(packet.Sequence, packet.TimestampUtc, packet.Direction, packet.Valid,
            Convert.ToHexString(packet.Bytes).ToLowerInvariant());

    private static async Task WriteJsonAsync(string path, object value, CancellationToken cancellationToken) =>
        await File.WriteAllTextAsync(path, JsonSerializer.Serialize(value, JsonOptions), cancellationToken);

    private string CreateEvidenceZip(string sourceDirectory)
    {
        var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        if (string.IsNullOrWhiteSpace(desktop) || !Directory.Exists(desktop))
            desktop = sourceDirectory;

        var zip = Path.Combine(desktop, $"ArmorX-D8-Discovery-{Path.GetFileName(sourceDirectory)}.zip");
        if (File.Exists(zip)) File.Delete(zip);
        ZipFile.CreateFromDirectory(sourceDirectory, zip, CompressionLevel.Optimal, includeBaseDirectory: true);
        return zip;
    }

    private async Task FinalizePartialEvidenceAsync(string state, Exception? exception = null)
    {
        if (string.IsNullOrWhiteSpace(_evidenceDirectory) || !Directory.Exists(_evidenceDirectory)) return;
        try
        {
            var snapshot = Snapshot(0);
            await WriteRawJsonlAsync(snapshot, Path.Combine(_evidenceDirectory, "ble-evidence.jsonl"), CancellationToken.None);
            await File.WriteAllTextAsync(
                Path.Combine(_evidenceDirectory, "partial-run.txt"),
                $"state={state}\r\ntime_utc={DateTimeOffset.UtcNow:O}\r\nexception={exception}\r\n");
            var zip = CreateEvidenceZip(_evidenceDirectory);
            OutputText.Text = zip;
        }
        catch { }
    }

    private static string BuildEvidenceReadme(
        IReadOnlyList<D5ProbeEvidence> probes,
        bool d5Stable,
        D8CaptureAnalysis d8)
    {
        var sb = new StringBuilder();
        sb.AppendLine("ArmorX D8 Macro Discovery - Stage 1");
        sb.AppendLine("=================================");
        sb.AppendLine();
        sb.AppendLine("Safety boundary:");
        sb.AppendLine("- D8 transmit is disabled.");
        sb.AppendLine("- No guessed macro payload was sent.");
        sb.AppendLine("- The workflow used known initialization/config reads plus recovered D5/GetMacroList A5 04 D5 7E.");
        sb.AppendLine();
        sb.AppendLine($"D5 probes: {probes.Count}");
        sb.AppendLine($"Complete D5 payloads reconstructed: {probes.Count(x => x.PayloadSha256 is not null)}");
        sb.AppendLine($"Repeated D5 payload stable: {d5Stable}");
        sb.AppendLine($"D8 candidate frames observed live: {d8.CandidateFrameCount}");
        sb.AppendLine($"D8 transfer groups reconstructed live: {d8.Transfers.Count}");
        sb.AppendLine();
        sb.AppendLine("Next gate:");
        sb.AppendLine(d8.Transfers.Count > 0
            ? "Compare controlled one-variable D8 transfers before implementing any writer."
            : "Import controlled official-client D8 captures. Do not infer or guess the D8 payload layout.");
        return sb.ToString();
    }

    private void SetStep(int percent, string progress, string action)
    {
        RunProgress.Value = Math.Clamp(percent, 0, 100);
        ProgressText.Text = progress;
        ActionText.Text = action;
        AppendLog($"STEP {percent}% {progress}");
    }

    private void AppendLog(string message)
    {
        if (!Dispatcher.CheckAccess())
        {
            Dispatcher.Invoke(() => AppendLog(message));
            return;
        }

        LogBox.AppendText($"[{DateTime.Now:HH:mm:ss.fff}] {message}{Environment.NewLine}");
        LogBox.ScrollToEnd();
    }

    private bool TryLoadRememberedAddress(out ulong address)
    {
        address = 0;
        try
        {
            if (!File.Exists(LastDevicePath)) return false;
            var text = File.ReadAllText(LastDevicePath).Trim();
            return ulong.TryParse(text, System.Globalization.NumberStyles.HexNumber, null, out address);
        }
        catch { return false; }
    }

    private void RememberAddress(ulong address)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(LastDevicePath)!);
            File.WriteAllText(LastDevicePath, address.ToString("X12"));
        }
        catch { }
    }

    private static string Sha256(byte[] bytes) =>
        Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true
    };

    private sealed record CapturedPacket(
        int Sequence,
        DateTimeOffset TimestampUtc,
        string Direction,
        byte[] Bytes,
        bool Valid);

    private sealed record PacketEvidence(
        int Sequence,
        DateTimeOffset TimestampUtc,
        string Direction,
        bool Valid,
        string Hex);

    private sealed record D5ProbeEvidence(
        int Probe,
        DateTimeOffset StartedUtc,
        DateTimeOffset EndedUtc,
        string RequestHex,
        IReadOnlyList<PacketEvidence> ReplyPackets,
        string? PayloadHex,
        string? PayloadSha256);
}
