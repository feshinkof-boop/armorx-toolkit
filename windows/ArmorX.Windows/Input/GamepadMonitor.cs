using Windows.Gaming.Input;

namespace ArmorX.Windows.Input;

public sealed record GamepadSnapshot(
    bool Connected,
    string Name,
    double LeftX,
    double LeftY,
    double RightX,
    double RightY,
    double LeftTrigger,
    double RightTrigger,
    IReadOnlyDictionary<string, bool> Buttons,
    long Timestamp);

public sealed class GamepadMonitor : IDisposable
{
    private readonly System.Threading.Timer _timer;
    private int _polling;
    private GamepadSnapshot? _last;

    public event EventHandler<GamepadSnapshot>? Changed;

    public GamepadMonitor()
    {
        _timer = new System.Threading.Timer(_ => Poll(), null, 250, 33);
    }

    private void Poll()
    {
        if (Interlocked.Exchange(ref _polling, 1) != 0) return;
        try
        {
            var pad = Gamepad.Gamepads.FirstOrDefault();
            if (pad is null)
            {
                Publish(new GamepadSnapshot(
                    false, "No Xbox-compatible controller",
                    0, 0, 0, 0, 0, 0,
                    EmptyButtons(), DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()));
                return;
            }

            var r = pad.GetCurrentReading();
            var b = r.Buttons;
            var buttons = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase)
            {
                ["A"] = b.HasFlag(GamepadButtons.A),
                ["B"] = b.HasFlag(GamepadButtons.B),
                ["X"] = b.HasFlag(GamepadButtons.X),
                ["Y"] = b.HasFlag(GamepadButtons.Y),
                ["LB"] = b.HasFlag(GamepadButtons.LeftShoulder),
                ["RB"] = b.HasFlag(GamepadButtons.RightShoulder),
                ["L3"] = b.HasFlag(GamepadButtons.LeftThumbstick),
                ["R3"] = b.HasFlag(GamepadButtons.RightThumbstick),
                ["View"] = b.HasFlag(GamepadButtons.View),
                ["Menu"] = b.HasFlag(GamepadButtons.Menu),
                ["DUp"] = b.HasFlag(GamepadButtons.DPadUp),
                ["DDown"] = b.HasFlag(GamepadButtons.DPadDown),
                ["DLeft"] = b.HasFlag(GamepadButtons.DPadLeft),
                ["DRight"] = b.HasFlag(GamepadButtons.DPadRight),
                ["P1"] = b.HasFlag(GamepadButtons.Paddle1),
                ["P2"] = b.HasFlag(GamepadButtons.Paddle2),
                ["P3"] = b.HasFlag(GamepadButtons.Paddle3),
                ["P4"] = b.HasFlag(GamepadButtons.Paddle4),
            };

            Publish(new GamepadSnapshot(
                true,
                "Xbox-compatible controller",
                ClampAxis(r.LeftThumbstickX),
                ClampAxis(r.LeftThumbstickY),
                ClampAxis(r.RightThumbstickX),
                ClampAxis(r.RightThumbstickY),
                ClampUnit(r.LeftTrigger),
                ClampUnit(r.RightTrigger),
                buttons,
                unchecked((long)r.Timestamp)));
        }
        catch
        {
        }
        finally
        {
            Volatile.Write(ref _polling, 0);
        }
    }

    private void Publish(GamepadSnapshot next)
    {
        if (_last is not null && Equivalent(_last, next)) return;
        _last = next;
        Changed?.Invoke(this, next);
    }

    private static bool Equivalent(GamepadSnapshot a, GamepadSnapshot b)
    {
        if (a.Connected != b.Connected) return false;
        if (Math.Abs(a.LeftX - b.LeftX) > .002 ||
            Math.Abs(a.LeftY - b.LeftY) > .002 ||
            Math.Abs(a.RightX - b.RightX) > .002 ||
            Math.Abs(a.RightY - b.RightY) > .002 ||
            Math.Abs(a.LeftTrigger - b.LeftTrigger) > .002 ||
            Math.Abs(a.RightTrigger - b.RightTrigger) > .002) return false;
        foreach (var key in a.Buttons.Keys)
            if (a.Buttons[key] != b.Buttons.GetValueOrDefault(key)) return false;
        return true;
    }

    private static Dictionary<string, bool> EmptyButtons() => new(StringComparer.OrdinalIgnoreCase)
    {
        ["A"] = false, ["B"] = false, ["X"] = false, ["Y"] = false,
        ["LB"] = false, ["RB"] = false, ["L3"] = false, ["R3"] = false,
        ["View"] = false, ["Menu"] = false,
        ["DUp"] = false, ["DDown"] = false, ["DLeft"] = false, ["DRight"] = false,
        ["P1"] = false, ["P2"] = false, ["P3"] = false, ["P4"] = false,
    };

    private static double ClampAxis(double value) => Math.Clamp(value, -1.0, 1.0);
    private static double ClampUnit(double value) => Math.Clamp(value, 0.0, 1.0);

    public void Dispose() => _timer.Dispose();
}
