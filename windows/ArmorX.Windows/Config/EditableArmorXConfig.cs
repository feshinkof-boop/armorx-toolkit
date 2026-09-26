using System.Collections.ObjectModel;
using ArmorX.Windows.Infrastructure;

namespace ArmorX.Windows.Config;

public sealed record MappingTarget(int Id, string Name)
{
    public override string ToString() => $"{Name} ({Id})";
}

public sealed class ByteFieldViewModel : ObservableObject
{
    private readonly ArmorXConfig144 _config;
    public string Label { get; }
    public int Offset { get; }

    public ByteFieldViewModel(string label, int offset, ArmorXConfig144 config)
    {
        Label = label;
        Offset = offset;
        _config = config;
    }

    public int Value
    {
        get => _config.GetByte(Offset);
        set
        {
            var clamped = Math.Clamp(value, 0, 255);
            if (_config.GetByte(Offset) == clamped) return;
            _config.SetByte(Offset, clamped);
            RaisePropertyChanged();
        }
    }
}

public sealed class EditableArmorXConfig : ObservableObject
{
    private readonly ArmorXConfig144 _config;

    public EditableArmorXConfig(ArmorXConfig144 config)
    {
        _config = config;
        LeftStickCurve = MakeCurve(20, "L");
        RightStickCurve = MakeCurve(28, "R");
        GyroCurve0 = MakeCurve(44, "G0");
        GyroCurve1 = MakeCurve(52, "G1");
        GyroCurve2 = MakeCurve(60, "G2");
    }

    public static IReadOnlyList<MappingTarget> ProvenMappingTargets { get; } = new[]
    {
        new MappingTarget(0, "A"), new MappingTarget(1, "B"), new MappingTarget(2, "Clear"),
        new MappingTarget(3, "X"), new MappingTarget(4, "Y"), new MappingTarget(6, "LB"),
        new MappingTarget(7, "RB"), new MappingTarget(8, "LT"), new MappingTarget(9, "RT"),
        new MappingTarget(10, "View"), new MappingTarget(11, "Menu"),
        new MappingTarget(12, "Guide / Xbox"), new MappingTarget(13, "L3"), new MappingTarget(14, "R3"),
        new MappingTarget(16, "D-pad Up"), new MappingTarget(17, "D-pad Down"),
        new MappingTarget(18, "D-pad Left"), new MappingTarget(19, "D-pad Right"),
        new MappingTarget(23, "M1"), new MappingTarget(24, "M2"),
        new MappingTarget(25, "M3"), new MappingTarget(26, "M4")
    };

    public ObservableCollection<ByteFieldViewModel> LeftStickCurve { get; }
    public ObservableCollection<ByteFieldViewModel> RightStickCurve { get; }
    public ObservableCollection<ByteFieldViewModel> GyroCurve0 { get; }
    public ObservableCollection<ByteFieldViewModel> GyroCurve1 { get; }
    public ObservableCollection<ByteFieldViewModel> GyroCurve2 { get; }

    private ObservableCollection<ByteFieldViewModel> MakeCurve(int start, string prefix) =>
        new(Enumerable.Range(0, 6).Select(i => new ByteFieldViewModel($"{prefix}{i + 1}", start + i, _config)));

    private int B(int offset) => _config.GetByte(offset);
    private void B(int offset, int value, string property)
    {
        value = Math.Clamp(value, 0, 255);
        if (_config.GetByte(offset) == value) return;
        _config.SetByte(offset, value);
        RaisePropertyChanged(property);
        RaisePropertyChanged(nameof(RawHex));
        RaisePropertyChanged(nameof(CrcStatus));
    }

    public int MotorSpeedIdx { get => B(4); set => B(4, value, nameof(MotorSpeedIdx)); }
    public int MotorMax { get => B(5); set => B(5, value, nameof(MotorMax)); }

    public int TriggerMode { get => B(9); set => B(9, value, nameof(TriggerMode)); }
    public int TriggerLeftDeadzoneCenter { get => B(10); set => B(10, value, nameof(TriggerLeftDeadzoneCenter)); }
    public int TriggerLeftDeadzoneSide { get => B(11); set => B(11, value, nameof(TriggerLeftDeadzoneSide)); }
    public int TriggerRightDeadzoneCenter { get => B(12); set => B(12, value, nameof(TriggerRightDeadzoneCenter)); }
    public int TriggerRightDeadzoneSide { get => B(13); set => B(13, value, nameof(TriggerRightDeadzoneSide)); }

    public int JoystickCircleLimit { get => B(14); set => B(14, value, nameof(JoystickCircleLimit)); }
    public int StickTurn { get => B(15); set => B(15, value, nameof(StickTurn)); }
    public int LeftStickDeadzoneCenter { get => B(16); set => B(16, value, nameof(LeftStickDeadzoneCenter)); }
    public int LeftStickDeadzoneSide { get => B(17); set => B(17, value, nameof(LeftStickDeadzoneSide)); }
    public int RightStickDeadzoneCenter { get => B(18); set => B(18, value, nameof(RightStickDeadzoneCenter)); }
    public int RightStickDeadzoneSide { get => B(19); set => B(19, value, nameof(RightStickDeadzoneSide)); }

    public int SensorMode { get => B(36); set => B(36, value, nameof(SensorMode)); }
    public int SensorDir { get => B(37); set => B(37, value, nameof(SensorDir)); }
    public int SensorRightKey0 { get => B(38); set => B(38, value, nameof(SensorRightKey0)); }
    public int SensorRightKey1 { get => B(39); set => B(39, value, nameof(SensorRightKey1)); }
    public int SensorMin { get => B(68); set => B(68, value, nameof(SensorMin)); }

    public uint SensorRightKeyBit
    {
        get => _config.GetUInt32Be(40);
        set { if (_config.GetUInt32Be(40) == value) return; _config.SetUInt32Be(40, value); RaisePropertyChanged(); RaisePropertyChanged(nameof(RawHex)); }
    }
    public uint SensorSwitch
    {
        get => _config.GetUInt32Be(69);
        set { if (_config.GetUInt32Be(69) == value) return; _config.SetUInt32Be(69, value); RaisePropertyChanged(); RaisePropertyChanged(nameof(RawHex)); }
    }

    public int TurboSpeedIdx { get => B(80); set => B(80, value, nameof(TurboSpeedIdx)); }
    public uint TurboKey
    {
        get => _config.GetUInt32Be(81);
        set { if (_config.GetUInt32Be(81) == value) return; _config.SetUInt32Be(81, value); RaisePropertyChanged(); RaisePropertyChanged(nameof(RawHex)); }
    }

    public int M1TargetId { get => _config.GetMapTarget(23); set => SetMap(23, value, nameof(M1TargetId)); }
    public int M2TargetId { get => _config.GetMapTarget(24); set => SetMap(24, value, nameof(M2TargetId)); }
    public int M3TargetId { get => _config.GetMapTarget(25); set => SetMap(25, value, nameof(M3TargetId)); }
    public int M4TargetId { get => _config.GetMapTarget(26); set => SetMap(26, value, nameof(M4TargetId)); }

    private void SetMap(int source, int value, string property)
    {
        if (_config.GetMapTarget(source) == value) return;
        _config.SetMapTarget(source, value);
        RaisePropertyChanged(property);
        RaisePropertyChanged(nameof(RawHex));
    }

    public string CrcStatus => _config.CrcValid ? $"Valid 0x{_config.StoredCrc:X4}" : $"Edited / will recalc (stored 0x{_config.StoredCrc:X4}, calc 0x{_config.CalculatedCrc:X4})";
    public string RawHex => _config.ToHex();

    public ArmorXConfig144 BuildForWrite()
    {
        var copy = new ArmorXConfig144(_config.ToArray());
        copy.RecalculateCrc();
        return copy;
    }

    public byte[] RawBytes() => _config.ToArray();
}
