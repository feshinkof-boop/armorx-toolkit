using System.Reflection;
using System.Text;

namespace ArmorX.Windows.Infrastructure;

public sealed class UserDiagnosticLog
{
    private readonly object _gate = new();
    private readonly Queue<string> _entries = new();
    private const int MaxEntries = 300;

    public void Add(string message)
    {
        var line = $"{DateTimeOffset.Now:yyyy-MM-dd HH:mm:ss zzz}  {message}";
        lock (_gate)
        {
            _entries.Enqueue(line);
            while (_entries.Count > MaxEntries) _entries.Dequeue();
        }
    }

    public async Task ExportAsync(
        string path,
        string? model,
        string? firmware,
        string connectionState,
        string safetyState)
    {
        string[] entries;
        lock (_gate) entries = _entries.ToArray();

        var info = Assembly.GetExecutingAssembly()
            .GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion
            ?? Assembly.GetExecutingAssembly().GetName().Version?.ToString()
            ?? "unknown";

        var sb = new StringBuilder();
        sb.AppendLine("ArmorX Windows end-user diagnostic report");
        sb.AppendLine("=========================================");
        sb.AppendLine($"Generated: {DateTimeOffset.Now:O}");
        sb.AppendLine($"App version: {info}");
        sb.AppendLine($"OS: {Environment.OSVersion}");
        sb.AppendLine($".NET: {Environment.Version}");
        sb.AppendLine($"Device model: {model ?? "-"}");
        sb.AppendLine($"Firmware: {firmware ?? "-"}");
        sb.AppendLine($"Connection: {connectionState}");
        sb.AppendLine($"Safety state: {safetyState}");
        sb.AppendLine();
        sb.AppendLine("Recent high-level events");
        sb.AppendLine("------------------------");
        foreach (var line in entries) sb.AppendLine(line);
        sb.AppendLine();
        sb.AppendLine("This report intentionally excludes BLE addresses, raw packets, research captures, and profile/config contents.");

        await File.WriteAllTextAsync(path, sb.ToString(), Encoding.UTF8);
    }
}
