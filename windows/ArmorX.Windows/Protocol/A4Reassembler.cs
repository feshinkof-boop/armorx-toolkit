namespace ArmorX.Windows.Protocol;

public sealed class A4Reassembler
{
    private readonly SortedDictionary<int, byte[]> _fragments = new();
    private int? _expectedLength;

    public void Reset()
    {
        _fragments.Clear();
        _expectedLength = null;
    }

    public byte[]? Push(ReadOnlySpan<byte> frame, byte expectedOpcode)
    {
        if (!ArmorXFrames.IsValid(frame) || frame[0] != ArmorXFrames.LongHeader)
            throw new ArmorXProtocolException("Invalid A4 fragment or checksum.");
        if (frame[2] != expectedOpcode)
            return null;

        var index = frame[3];
        if (index == 0)
            throw new ArmorXProtocolException("A4 fragment index 0 is invalid.");

        var data = frame[4..^1].ToArray();
        _fragments[index] = data;

        if (index == 1 && data.Length >= 4)
        {
            _expectedLength = (data[2] << 8) | data[3];
            if (_expectedLength <= 0 || _expectedLength > 4096)
                throw new ArmorXProtocolException($"Unreasonable declared long payload length: {_expectedLength}.");
        }

        if (_expectedLength is null)
            return null;

        var expectedFragments = (_expectedLength.Value + 14) / 15;
        if (_fragments.Count < expectedFragments)
            return null;

        for (var i = 1; i <= expectedFragments; i++)
            if (!_fragments.ContainsKey(i))
                return null;

        var assembled = _fragments.OrderBy(kv => kv.Key).SelectMany(kv => kv.Value).Take(_expectedLength.Value).ToArray();
        if (assembled.Length != _expectedLength.Value)
            return null;

        Reset();
        return assembled;
    }
}
