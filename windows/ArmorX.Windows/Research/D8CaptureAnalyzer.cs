using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using ArmorX.Windows.Protocol;

namespace ArmorX.Windows.Research;

public sealed record D8FrameRecord(
    int Sequence,
    string Hex,
    bool Valid,
    byte Header,
    byte Opcode,
    int? FragmentIndex,
    int DataLength,
    string Source);

public sealed record D8TransferAnalysis(
    int TransferIndex,
    int FrameCount,
    IReadOnlyList<int> FragmentIndices,
    IReadOnlyList<int> MissingIndices,
    IReadOnlyList<int> DuplicateIndices,
    bool AllFramesValid,
    bool ContiguousFromOne,
    int PayloadLength,
    string PayloadHex,
    string PayloadSha256);

public sealed record D8CaptureAnalysis(
    string Source,
    int CandidateFrameCount,
    int ValidD8FrameCount,
    int InvalidD8CandidateCount,
    IReadOnlyList<D8FrameRecord> Frames,
    IReadOnlyList<D8TransferAnalysis> Transfers,
    string EvidenceStatement);

public sealed record ByteDelta(int Offset, byte Before, byte After)
{
    public override string ToString() => $"offset {Offset}: 0x{Before:X2} -> 0x{After:X2}";
}

public sealed record D8TransferDiff(
    int BeforeLength,
    int AfterLength,
    string BeforeSha256,
    string AfterSha256,
    IReadOnlyList<ByteDelta> ChangedSharedOffsets,
    int? FirstLengthOnlyOffset,
    int LengthDelta);

public static class D8CaptureAnalyzer
{
    private static readonly Regex HexRun = new(@"(?i)(?:\b[0-9a-f]{2}\b[\s,:-]*){4,}", RegexOptions.Compiled);

    public static D8CaptureAnalysis AnalyzeFile(string path)
    {
        if (!File.Exists(path)) throw new FileNotFoundException("D8 capture file not found.", path);
        var text = File.ReadAllText(path);
        return AnalyzeText(text, Path.GetFileName(path));
    }

    public static D8CaptureAnalysis AnalyzeText(string text, string source = "text")
    {
        var packets = ExtractPackets(text).ToList();
        var frames = new List<D8FrameRecord>();
        var validD8 = new List<byte[]>();
        var invalidCandidates = 0;
        var sequence = 0;

        foreach (var packet in packets)
        {
            sequence++;
            if (packet.Length < 3 || packet[2] != ArmorXFrames.OpWriteMacro) continue;
            var valid = ArmorXFrames.IsValid(packet);
            var isA4 = packet[0] == ArmorXFrames.LongHeader;
            if (!valid || !isA4) invalidCandidates++;
            if (valid && isA4) validD8.Add(packet);
            frames.Add(new D8FrameRecord(
                sequence,
                Convert.ToHexString(packet).ToLowerInvariant(),
                valid,
                packet[0],
                packet[2],
                isA4 && packet.Length > 3 ? packet[3] : null,
                isA4 && packet.Length >= 5 ? Math.Max(0, packet.Length - 5) : 0,
                source));
        }

        var transfers = AnalyzeTransfers(validD8);
        return new D8CaptureAnalysis(
            source,
            frames.Count,
            validD8.Count,
            invalidCandidates,
            frames,
            transfers,
            "A4/D8 framing, checksum, fragment indices and raw payload bytes are observed facts. Payload field semantics remain UNKNOWN until controlled variants correlate byte changes with one macro variable at a time.");
    }

    public static D8CaptureAnalysis AnalyzePackets(IEnumerable<byte[]> packets, string source)
    {
        var text = string.Join(Environment.NewLine, packets.Select(Convert.ToHexString));
        return AnalyzeText(text, source);
    }

    public static D8TransferDiff Compare(D8TransferAnalysis before, D8TransferAnalysis after)
    {
        var a = Convert.FromHexString(before.PayloadHex);
        var b = Convert.FromHexString(after.PayloadHex);
        var shared = Math.Min(a.Length, b.Length);
        var deltas = new List<ByteDelta>();
        for (var i = 0; i < shared; i++)
            if (a[i] != b[i]) deltas.Add(new ByteDelta(i, a[i], b[i]));

        return new D8TransferDiff(
            a.Length,
            b.Length,
            before.PayloadSha256,
            after.PayloadSha256,
            deltas,
            a.Length == b.Length ? null : shared,
            b.Length - a.Length);
    }

    public static string ToMarkdown(D8CaptureAnalysis analysis)
    {
        var sb = new StringBuilder();
        sb.AppendLine("# D8 capture analysis");
        sb.AppendLine();
        sb.AppendLine($"- Source: `{analysis.Source}`");
        sb.AppendLine($"- Candidate D8 frames: {analysis.CandidateFrameCount}");
        sb.AppendLine($"- Valid A4/D8 frames: {analysis.ValidD8FrameCount}");
        sb.AppendLine($"- Invalid/non-A4 D8 candidates: {analysis.InvalidD8CandidateCount}");
        sb.AppendLine($"- Reconstructed transfer groups: {analysis.Transfers.Count}");
        sb.AppendLine();
        sb.AppendLine("> " + analysis.EvidenceStatement);
        sb.AppendLine();

        foreach (var t in analysis.Transfers)
        {
            sb.AppendLine($"## Transfer {t.TransferIndex}");
            sb.AppendLine();
            sb.AppendLine($"- Frames: {t.FrameCount}");
            sb.AppendLine($"- Fragment indices: `{string.Join(",", t.FragmentIndices)}`");
            sb.AppendLine($"- Missing indices: `{(t.MissingIndices.Count == 0 ? "none" : string.Join(",", t.MissingIndices))}`");
            sb.AppendLine($"- Duplicate indices: `{(t.DuplicateIndices.Count == 0 ? "none" : string.Join(",", t.DuplicateIndices))}`");
            sb.AppendLine($"- All checksums/length bytes valid: {t.AllFramesValid}");
            sb.AppendLine($"- Contiguous from fragment 1: {t.ContiguousFromOne}");
            sb.AppendLine($"- Raw payload bytes: {t.PayloadLength}");
            sb.AppendLine($"- SHA256: `{t.PayloadSha256}`");
            sb.AppendLine();
            sb.AppendLine("```text");
            sb.AppendLine(FormatHex(Convert.FromHexString(t.PayloadHex)));
            sb.AppendLine("```");
            sb.AppendLine();
        }

        if (analysis.Transfers.Count >= 2)
        {
            sb.AppendLine("## Consecutive transfer diffs");
            sb.AppendLine();
            for (var i = 1; i < analysis.Transfers.Count; i++)
            {
                var diff = Compare(analysis.Transfers[i - 1], analysis.Transfers[i]);
                sb.AppendLine($"### Transfer {i} -> {i + 1}");
                sb.AppendLine();
                sb.AppendLine($"- Length: {diff.BeforeLength} -> {diff.AfterLength} ({diff.LengthDelta:+#;-#;0})");
                sb.AppendLine($"- Changed shared offsets: {diff.ChangedSharedOffsets.Count}");
                foreach (var d in diff.ChangedSharedOffsets.Take(128)) sb.AppendLine($"- {d}");
                if (diff.ChangedSharedOffsets.Count > 128) sb.AppendLine($"- ... {diff.ChangedSharedOffsets.Count - 128} additional changed offsets");
                sb.AppendLine();
            }
        }

        return sb.ToString();
    }

    private static IReadOnlyList<D8TransferAnalysis> AnalyzeTransfers(IReadOnlyList<byte[]> frames)
    {
        var groups = new List<List<byte[]>>();
        List<byte[]>? current = null;
        foreach (var frame in frames)
        {
            var index = frame[3];
            if (current is null || (index == 1 && current.Count > 0))
            {
                current = new List<byte[]>();
                groups.Add(current);
            }
            current.Add(frame);
        }

        var result = new List<D8TransferAnalysis>();
        for (var g = 0; g < groups.Count; g++)
        {
            var group = groups[g];
            var indices = group.Select(x => (int)x[3]).ToArray();
            var duplicates = indices.GroupBy(x => x).Where(x => x.Count() > 1).Select(x => x.Key).OrderBy(x => x).ToArray();
            var max = indices.Length == 0 ? 0 : indices.Max();
            var missing = Enumerable.Range(1, max).Where(i => !indices.Contains(i)).ToArray();
            var unique = group.GroupBy(x => x[3]).ToDictionary(x => (int)x.Key, x => x.Last());
            var payload = unique.OrderBy(x => x.Key).SelectMany(x => x.Value.AsSpan(4, x.Value.Length - 5).ToArray()).ToArray();
            var contiguous = indices.Length > 0 && indices.Contains(1) && missing.Length == 0;
            result.Add(new D8TransferAnalysis(
                g + 1,
                group.Count,
                indices,
                missing,
                duplicates,
                group.All(x => ArmorXFrames.IsValid(x)),
                contiguous,
                payload.Length,
                Convert.ToHexString(payload).ToLowerInvariant(),
                Sha256(payload)));
        }
        return result;
    }

    private static IEnumerable<byte[]> ExtractPackets(string text)
    {
        foreach (var line in text.Split(new[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries))
        {
            var trimmed = line.Trim();
            if (trimmed.Length == 0) continue;

            if (trimmed.StartsWith('{'))
            {
                byte[]? jsonBytes = null;
                var hadHexProperty = false;
                try
                {
                    using var doc = JsonDocument.Parse(trimmed);
                    if (doc.RootElement.TryGetProperty("hex", out var hexElement) && hexElement.ValueKind == JsonValueKind.String)
                    {
                        hadHexProperty = true;
                        jsonBytes = ParseHex(hexElement.GetString());
                    }
                }
                catch { }
                if (hadHexProperty)
                {
                    if (jsonBytes is not null) yield return jsonBytes;
                    continue;
                }
            }

            byte[]? direct = null;
            if (Regex.IsMatch(trimmed, @"(?i)^[0-9a-f\s,:-]+$"))
                direct = ParseHex(trimmed);
            if (direct is not null && direct.Length >= 4)
            {
                yield return direct;
                continue;
            }

            foreach (Match match in HexRun.Matches(trimmed))
            {
                var bytes = ParseHex(match.Value);
                if (bytes is not null && bytes.Length >= 4) yield return bytes;
            }
        }
    }

    private static byte[]? ParseHex(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        var chars = new string(value.Where(Uri.IsHexDigit).ToArray());
        if (chars.Length < 8 || chars.Length % 2 != 0) return null;
        try { return Convert.FromHexString(chars); }
        catch { return null; }
    }

    private static string Sha256(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    private static string FormatHex(byte[] bytes)
    {
        if (bytes.Length == 0) return "<empty>";
        var sb = new StringBuilder();
        for (var offset = 0; offset < bytes.Length; offset += 16)
        {
            var take = Math.Min(16, bytes.Length - offset);
            sb.Append(offset.ToString("X4")).Append("  ");
            for (var i = 0; i < take; i++) sb.Append(bytes[offset + i].ToString("X2")).Append(' ');
            sb.AppendLine();
        }
        return sb.ToString().TrimEnd();
    }
}
