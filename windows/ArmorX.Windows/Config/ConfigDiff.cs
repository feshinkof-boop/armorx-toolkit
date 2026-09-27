namespace ArmorX.Windows.Config;

public sealed record ConfigByteChange(int Offset, byte Before, byte After, string Label);

public static class ConfigDiff
{
    public static IReadOnlyList<ConfigByteChange> Compare(
        ArmorXConfig144 before,
        ArmorXConfig144 after,
        bool includeCrc = false) =>
        Compare(before.ToArray(), after.ToArray(), includeCrc);

    public static IReadOnlyList<ConfigByteChange> Compare(
        byte[] before,
        byte[] after,
        bool includeCrc = false)
    {
        if (before.Length != ArmorXConfig144.Size || after.Length != ArmorXConfig144.Size)
            throw new ArgumentException("ARMOR-X Pro config diff requires two 144-byte images.");

        var start = includeCrc ? 0 : 2;
        var result = new List<ConfigByteChange>();
        for (var i = start; i < ArmorXConfig144.Size; i++)
        {
            if (before[i] == after[i]) continue;
            result.Add(new ConfigByteChange(i, before[i], after[i], LabelFor(i)));
        }

        return result;
    }

    public static ArmorXConfig144 MergeEditorChanges(
        ArmorXConfig144 currentDevice,
        byte[] editorBaseline,
        ArmorXConfig144 editorDesired)
    {
        if (editorBaseline.Length != ArmorXConfig144.Size)
            throw new ArgumentException("Editor baseline must be 144 bytes.", nameof(editorBaseline));

        var current = currentDevice.ToArray();
        var desired = editorDesired.ToArray();

        for (var i = 2; i < ArmorXConfig144.Size; i++)
        {
            if (editorBaseline[i] != desired[i])
                current[i] = desired[i];
        }

        var merged = new ArmorXConfig144(current);
        merged.RecalculateCrc();
        return merged;
    }

    public static string FormatSummary(IReadOnlyList<ConfigByteChange> changes, int max = 18)
    {
        if (changes.Count == 0) return "No semantic configuration changes are pending.";

        var lines = new List<string>
        {
            $"{changes.Count} semantic byte change(s) will be written:",
            ""
        };

        foreach (var change in changes.Take(max))
            lines.Add($"Offset {change.Offset,3}  {change.Label,-24}  0x{change.Before:X2} -> 0x{change.After:X2}");

        if (changes.Count > max)
            lines.Add($"... and {changes.Count - max} more.");

        lines.Add("");
        lines.Add("CRC bytes 0-1 will be recalculated automatically.");
        return string.Join(Environment.NewLine, lines);
    }

    private static string LabelFor(int offset)
    {
        if (offset is >= 112 and <= 143) return $"mapKeys[{offset - 112}]";
        return offset switch
        {
            4 => "motorSpeedIdx",
            5 => "motorMax",
            9 => "triggerMode",
            10 => "triggerLeftCenter",
            11 => "triggerLeftSide",
            12 => "triggerRightCenter",
            13 => "triggerRightSide",
            14 => "circleLimit",
            15 => "stickTurn",
            16 => "leftDzCenter",
            17 => "leftDzSide",
            18 => "rightDzCenter",
            19 => "rightDzSide",
            >= 20 and <= 25 => $"leftCurve[{offset - 20}]",
            >= 28 and <= 33 => $"rightCurve[{offset - 28}]",
            36 => "sensorMode",
            37 => "sensorDir",
            38 => "sensorRightKey0",
            39 => "sensorRightKey1",
            >= 40 and <= 43 => "sensorRightKeyBit",
            >= 44 and <= 49 => $"gyro0[{offset - 44}]",
            >= 52 and <= 57 => $"gyro1[{offset - 52}]",
            >= 60 and <= 65 => $"gyro2[{offset - 60}]",
            68 => "sensorMin",
            >= 69 and <= 72 => "sensorSwitch",
            80 => "turboSpeedIdx",
            >= 81 and <= 84 => "turboKey",
            _ => "preserved/raw"
        };
    }
}
