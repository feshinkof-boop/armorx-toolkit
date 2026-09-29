using System.Collections.Concurrent;
using System.Text;
using ArmorX.Windows.Bluetooth;
using ArmorX.Windows.Config;
using ArmorX.Windows.Protocol;

namespace ArmorX.Windows.Device;

public sealed class ArmorXDeviceSession : IDisposable
{
    private readonly ArmorXBleTransport _transport;
    private readonly ConcurrentDictionary<byte, TaskCompletionSource<byte[]>> _shortWaiters = new();
    private readonly object _longLock = new();
    private readonly A4Reassembler _d6Reassembler = new();
    private TaskCompletionSource<byte[]>? _d6Waiter;

    public event EventHandler<string>? Log;

    public string? Model { get; private set; }
    public string? Firmware { get; private set; }
    public int? BatteryPercent { get; private set; }
    public int? ZkmVersion { get; private set; }
    public string? DeviceUuid { get; private set; }

    public ArmorXDeviceSession(ArmorXBleTransport transport)
    {
        _transport = transport;
        _transport.PacketReceived += OnPacket;
    }

    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        var zkmTask = RegisterShortWaiter(ArmorXFrames.OpGetZkmVersion, TimeSpan.FromSeconds(3), cancellationToken);
        await SendAsync(ArmorXFrames.GetZkmVersion, "0B/GetZkmVersion", cancellationToken);
        try
        {
            var reply = await zkmTask;
            if (reply.Length >= 5) ZkmVersion = reply[3];
        }
        catch (TimeoutException) { Emit("0B response timed out; continuing with standard GATT reads."); }

        Model = DecodeText(await _transport.ReadCharacteristicAsync(ArmorXBleTransport.ModelUuid, cancellationToken));
        Firmware = DecodeText(await _transport.ReadCharacteristicAsync(ArmorXBleTransport.FirmwareUuid, cancellationToken));
        var battery = await _transport.ReadCharacteristicAsync(ArmorXBleTransport.BatteryUuid, cancellationToken);
        BatteryPercent = battery is { Length: > 0 } ? battery[0] : null;
        Emit($"Identity: model={Model ?? "?"}, firmware={Firmware ?? "?"}, battery={(BatteryPercent?.ToString() ?? "?")}%.");

        var efTask = RegisterShortWaiter(ArmorXFrames.OpGetDeviceUuid, TimeSpan.FromSeconds(3), cancellationToken);
        await SendAsync(ArmorXFrames.GetDeviceUuid, "EF/GetDeviceUUID", cancellationToken);
        try
        {
            var ef = await efTask;
            if (ef.Length >= 12) DeviceUuid = Convert.ToHexString(ef.AsSpan(3, 8)).ToLowerInvariant();
        }
        catch (TimeoutException) { Emit("EF response timed out; local configuration is still available."); }
    }

    public async Task<int?> RefreshBatteryAsync(CancellationToken cancellationToken = default)
    {
        var battery = await _transport.ReadCharacteristicAsync(
            ArmorXBleTransport.BatteryUuid, cancellationToken);
        BatteryPercent = battery is { Length: > 0 } ? battery[0] : null;
        return BatteryPercent;
    }

    public async Task<ArmorXConfig144> ReadConfigAsync(CancellationToken cancellationToken = default)
    {
        Task<byte[]> wait;
        lock (_longLock)
        {
            if (_d6Waiter is { Task.IsCompleted: false })
                throw new InvalidOperationException("A D6 read is already pending.");
            _d6Reassembler.Reset();
            _d6Waiter = new(TaskCreationOptions.RunContinuationsAsynchronously);
            wait = _d6Waiter.Task;
        }

        try
        {
            await Task.Delay(350, cancellationToken);
            await SendAsync(ArmorXFrames.ReadConfig, "D6/ReadConfig", cancellationToken);
            var bytes = await wait.WaitAsync(TimeSpan.FromSeconds(6), cancellationToken);
            var config = new ArmorXConfig144(bytes);
            Emit($"D6 complete: {bytes.Length} bytes, CRC {(config.CrcValid ? "valid" : "INVALID")} 0x{config.StoredCrc:X4}.");
            return config;
        }
        finally
        {
            lock (_longLock)
            {
                if (_d6Waiter is not null && ReferenceEquals(_d6Waiter.Task, wait))
                {
                    _d6Waiter.TrySetCanceled();
                    _d6Waiter = null;
                    _d6Reassembler.Reset();
                }
            }
        }
    }

    public async Task<WriteVerifyResult> WriteAndVerifyAsync(
        ArmorXConfig144 config,
        CancellationToken cancellationToken = default)
    {
        config.RecalculateCrc();
        var expected = config.ToArray();
        Emit($"Writing D7 full image, CRC 0x{config.StoredCrc:X4}...");

        var ackTask = RegisterShortWaiter(ArmorXFrames.OpWriteConfig, TimeSpan.FromSeconds(2), cancellationToken);
        foreach (var frame in ArmorXFrames.FragmentLong(ArmorXFrames.OpWriteConfig, expected))
        {
            await SendAsync(frame, $"D7 fragment {frame[3]}", cancellationToken, verbose: false);
            await Task.Delay(12, cancellationToken);
        }

        var ackSeen = false;
        try
        {
            var ack = await ackTask;
            ackSeen = ack.Length >= 5 && ack[3] == 0x00;
            Emit("D7 acknowledgement received.");
        }
        catch (TimeoutException)
        {
            Emit("No D7 acknowledgement observed; verification will decide the result.");
        }

        var postTask = RegisterShortWaiter(ArmorXFrames.OpPostWrite, TimeSpan.FromSeconds(2), cancellationToken);
        await SendAsync(ArmorXFrames.PostWrite, "0E/PostWrite", cancellationToken);
        var postEchoSeen = false;
        try { await postTask; postEchoSeen = true; Emit("0E echo received."); }
        catch (TimeoutException) { Emit("0E echo not observed; verification will decide the result."); }

        var first = await ReadConfigAsync(cancellationToken);
        var second = await ReadConfigAsync(cancellationToken);
        var firstBytes = first.ToArray();
        var secondBytes = second.ToArray();

        var mismatch1 = Enumerable.Range(0, expected.Length).Where(i => expected[i] != firstBytes[i]).ToArray();
        var mismatch2 = Enumerable.Range(0, expected.Length).Where(i => expected[i] != secondBytes[i]).ToArray();
        var readsAgree = firstBytes.SequenceEqual(secondBytes);
        var mismatches = mismatch1.Concat(mismatch2).Distinct().OrderBy(x => x).ToArray();
        var exact = mismatch1.Length == 0 && mismatch2.Length == 0 && readsAgree;

        Emit(exact
            ? "Read-back verification PASS: two 144-byte reads match the target exactly."
            : $"Read-back verification FAILED: {mismatches.Length} target mismatch offset(s); reads agree={readsAgree}.");

        return new WriteVerifyResult(
            exact, ackSeen, postEchoSeen, second, first, second, readsAgree, mismatches);
    }

    private Task<byte[]> RegisterShortWaiter(byte opcode, TimeSpan timeout, CancellationToken cancellationToken)
    {
        var tcs = new TaskCompletionSource<byte[]>(TaskCreationOptions.RunContinuationsAsynchronously);
        if (!_shortWaiters.TryAdd(opcode, tcs))
            throw new InvalidOperationException($"A waiter for opcode 0x{opcode:X2} is already pending.");

        _ = TimeoutWaiterAsync(opcode, tcs, timeout, cancellationToken);
        return tcs.Task;
    }

    private async Task TimeoutWaiterAsync(byte opcode, TaskCompletionSource<byte[]> tcs, TimeSpan timeout, CancellationToken cancellationToken)
    {
        try
        {
            await Task.Delay(timeout, cancellationToken);
            if (_shortWaiters.TryRemove(opcode, out var current) && ReferenceEquals(current, tcs))
                tcs.TrySetException(new TimeoutException($"Timed out waiting for opcode 0x{opcode:X2}."));
        }
        catch (OperationCanceledException)
        {
            if (_shortWaiters.TryRemove(opcode, out var current) && ReferenceEquals(current, tcs))
                current.TrySetCanceled(cancellationToken);
        }
    }

    private async Task SendAsync(byte[] frame, string label, CancellationToken cancellationToken, bool verbose = true)
    {
        if (!ArmorXFrames.IsValid(frame))
            throw new ArmorXProtocolException($"Attempted to send invalid frame: {label}.");
        if (verbose) Emit($"TX {label}: {ArmorXFrames.Hex(frame)}");
        await _transport.WriteAsync(frame, cancellationToken);
    }

    private void OnPacket(object? sender, byte[] packet)
    {
        if (!ArmorXFrames.IsValid(packet))
        {
            Emit($"RX invalid/ignored: {ArmorXFrames.Hex(packet)}");
            return;
        }

        var opcode = packet[2];
        if (packet[0] == ArmorXFrames.ShortHeader)
        {
            if (_shortWaiters.TryRemove(opcode, out var waiter)) waiter.TrySetResult(packet);
            return;
        }

        if (packet[0] == ArmorXFrames.LongHeader && opcode == ArmorXFrames.OpReadConfig)
        {
            try
            {
                var full = _d6Reassembler.Push(packet, ArmorXFrames.OpReadConfig);
                if (full is null) return;
                lock (_longLock)
                {
                    _d6Waiter?.TrySetResult(full);
                    _d6Waiter = null;
                }
            }
            catch (Exception ex)
            {
                lock (_longLock)
                {
                    _d6Waiter?.TrySetException(ex);
                    _d6Waiter = null;
                }
            }
        }
    }

    private static string? DecodeText(byte[]? data)
    {
        if (data is null || data.Length == 0) return null;
        return Encoding.UTF8.GetString(data).Trim('\0', ' ', '\r', '\n');
    }

    private void Emit(string message) => Log?.Invoke(this, message);

    public void Dispose()
    {
        _transport.PacketReceived -= OnPacket;
        foreach (var waiter in _shortWaiters.Values) waiter.TrySetCanceled();
        _shortWaiters.Clear();
    }
}

public sealed record WriteVerifyResult(
    bool ExactMatch,
    bool AckSeen,
    bool PostWriteEchoSeen,
    ArmorXConfig144 ReadBackConfig,
    ArmorXConfig144 FirstReadBackConfig,
    ArmorXConfig144 SecondReadBackConfig,
    bool VerificationReadsAgree,
    IReadOnlyList<int> MismatchOffsets);
