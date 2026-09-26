using ArmorX.Windows.Protocol;

namespace ArmorX.Windows.Config;

public sealed class ArmorXConfig144
{
    public const int Size = 144;
    public const int MapKeysOffset = 112;
    private readonly byte[] _bytes;

    public ArmorXConfig144(ReadOnlySpan<byte> bytes)
    {
        if (bytes.Length != Size)
            throw new ArmorXProtocolException($"ARMOR-X Pro configuration must be {Size} bytes, got {bytes.Length}.");
        _bytes = bytes.ToArray();
        var declared = (_bytes[2] << 8) | _bytes[3];
        if (declared != Size)
            throw new ArmorXProtocolException($"Configuration declared length is {declared}, expected {Size}.");
    }

    public byte[] ToArray() => _bytes.ToArray();
    public ReadOnlySpan<byte> Bytes => _bytes;

    public ushort StoredCrc => (ushort)((_bytes[0] << 8) | _bytes[1]);
    public ushort CalculatedCrc => Crc16Modbus.Compute(_bytes.AsSpan(2));
    public bool CrcValid => StoredCrc == CalculatedCrc;

    public void RecalculateCrc()
    {
        var crc = CalculatedCrc;
        _bytes[0] = (byte)(crc >> 8);
        _bytes[1] = (byte)crc;
    }

    public byte GetByte(int offset) => _bytes[offset];
    public void SetByte(int offset, int value) => _bytes[offset] = checked((byte)value);

    public uint GetUInt32Be(int offset) =>
        ((uint)_bytes[offset] << 24) |
        ((uint)_bytes[offset + 1] << 16) |
        ((uint)_bytes[offset + 2] << 8) |
        _bytes[offset + 3];

    public void SetUInt32Be(int offset, uint value)
    {
        _bytes[offset] = (byte)(value >> 24);
        _bytes[offset + 1] = (byte)(value >> 16);
        _bytes[offset + 2] = (byte)(value >> 8);
        _bytes[offset + 3] = (byte)value;
    }

    public byte GetMapTarget(int sourceId) => _bytes[MapKeysOffset + sourceId];
    public void SetMapTarget(int sourceId, int targetId) => _bytes[MapKeysOffset + sourceId] = checked((byte)targetId);

    public string ToHex() => ArmorXFrames.Hex(_bytes);
}
