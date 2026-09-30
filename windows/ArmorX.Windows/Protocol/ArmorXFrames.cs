namespace ArmorX.Windows.Protocol;

public static class ArmorXFrames
{
    public const byte ShortHeader = 0xA5;
    public const byte LongHeader = 0xA4;

    public const byte OpGetZkmVersion = 0x0B;
    public const byte OpPostWrite = 0x0E;
    public const byte OpReadConfig = 0xD6;
    public const byte OpWriteConfig = 0xD7;
    public const byte OpGetDeviceUuid = 0xEF;

    public static readonly byte[] GetZkmVersion = BuildShort(OpGetZkmVersion);
    public static readonly byte[] GetDeviceUuid = BuildShort(OpGetDeviceUuid, new byte[8]);
    public static readonly byte[] ReadConfig = BuildShort(OpReadConfig);
    public static readonly byte[] PostWrite = BuildShort(OpPostWrite, new byte[] { 0x00 });

    public static byte[] BuildShort(byte opcode, ReadOnlySpan<byte> data = default)
    {
        var frame = new byte[4 + data.Length];
        frame[0] = ShortHeader;
        frame[1] = checked((byte)frame.Length);
        frame[2] = opcode;
        data.CopyTo(frame.AsSpan(3));
        frame[^1] = Checksum(frame.AsSpan(0, frame.Length - 1));
        return frame;
    }

    public static IEnumerable<byte[]> FragmentLong(byte opcode, byte[] payload, int chunkSize = 15)
    {
        if (payload.Length == 0)
            yield break;

        var index = 1;
        for (var offset = 0; offset < payload.Length; offset += chunkSize, index++)
        {
            var take = Math.Min(chunkSize, payload.Length - offset);
            var frame = new byte[take + 5];
            frame[0] = LongHeader;
            frame[1] = checked((byte)frame.Length);
            frame[2] = opcode;
            frame[3] = checked((byte)index);
            Array.Copy(payload, offset, frame, 4, take);
            frame[^1] = Checksum(frame.AsSpan(0, frame.Length - 1));
            yield return frame;
        }
    }

    public static byte Checksum(ReadOnlySpan<byte> bytes)
    {
        var sum = 0;
        foreach (var b in bytes)
            sum += b;
        return (byte)(sum & 0xFF);
    }

    public static bool IsValid(ReadOnlySpan<byte> frame)
    {
        if (frame.Length < 4)
            return false;
        if (frame[0] is not (ShortHeader or LongHeader))
            return false;
        if (frame[1] != frame.Length)
            return false;
        return Checksum(frame[..^1]) == frame[^1];
    }

    public static string Hex(ReadOnlySpan<byte> bytes) => Convert.ToHexString(bytes).Replace("-", " ");
}
