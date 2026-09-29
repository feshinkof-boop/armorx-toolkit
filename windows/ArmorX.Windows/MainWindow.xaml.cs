using System.ComponentModel;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Windows;
using ArmorX.Windows.Bridge;
using ArmorX.Windows.Input;
using ArmorX.Windows.Tray;
using Microsoft.Web.WebView2.Core;

namespace ArmorX.Windows;

public partial class MainWindow : Window
{
    private readonly ArmorXAppController _controller = new();
    private readonly GamepadMonitor _gamepad = new();
    private readonly TrayService _tray = new();
    private readonly JsonSerializerOptions _json = new(JsonSerializerDefaults.Web)
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };
    private bool _webReady;
    private bool _allowClose;
    private bool _trayNoticeShown;

    public MainWindow()
    {
        InitializeComponent();

        Loaded += MainWindow_Loaded;
        Closing += MainWindow_Closing;
        StateChanged += (_, _) =>
        {
            if (WindowState == WindowState.Minimized)
            {
                Hide();
                if (!_trayNoticeShown)
                {
                    _trayNoticeShown = true;
                    _tray.ShowFirstMinimizeNotice();
                }
            }
        };

        _controller.StateChanged += async (_, _) => await PushStateAsync();
        _controller.HideRequested += (_, _) => Dispatcher.Invoke(HideToTray);
        _controller.ExitRequested += (_, _) => Dispatcher.Invoke(ExitNow);
        _gamepad.Changed += (_, snapshot) => PushEvent("gamepad", snapshot);

        _tray.ShowRequested += (_, _) => Dispatcher.Invoke(ShowFromTray);
        _tray.ExitRequested += (_, _) => Dispatcher.Invoke(ExitNow);
    }

    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        try
        {
            await Web.EnsureCoreWebView2Async();
            var webRoot = Path.Combine(AppContext.BaseDirectory, "wwwroot");
            if (!Directory.Exists(webRoot) || !File.Exists(Path.Combine(webRoot, "index.html")))
                throw new DirectoryNotFoundException(
                    "ArmorX Studio web assets are missing. Reinstall the Windows package.");

            Web.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
            Web.CoreWebView2.Settings.AreDevToolsEnabled = true;
            Web.CoreWebView2.Settings.IsStatusBarEnabled = false;
            Web.CoreWebView2.SetVirtualHostNameToFolderMapping(
                "app.armorx", webRoot, CoreWebView2HostResourceAccessKind.DenyCors);
            Web.CoreWebView2.WebMessageReceived += WebMessageReceived;
            Web.CoreWebView2.NavigationCompleted += async (_, _) =>
            {
                _webReady = true;
                await PushStateAsync();
            };
            Web.Source = new Uri("https://app.armorx/index.html");
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show(
                ex.ToString(),
                "ArmorX Studio - startup error",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
    }

    private async void WebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        BridgeRequest? request = null;
        try
        {
            request = JsonSerializer.Deserialize<BridgeRequest>(e.WebMessageAsJson, _json)
                      ?? throw new InvalidDataException("Invalid bridge request.");
            var result = await _controller.HandleAsync(request.Action, request.Payload);
            Post(new { type = "response", id = request.Id, ok = true, result });
            await PushStateAsync();
        }
        catch (Exception ex)
        {
            Post(new
            {
                type = "response",
                id = request?.Id,
                ok = false,
                error = ex.Message
            });
        }
    }

    private async Task PushStateAsync()
    {
        if (!_webReady || Dispatcher.HasShutdownStarted) return;
        try
        {
            var state = await _controller.BuildStateAsync();
            await Dispatcher.InvokeAsync(() =>
            {
                Post(new { type = "event", @event = "state", payload = state });
                UpdateTray(state);
            });
        }
        catch { }
    }

    private void UpdateTray(object state)
    {
        using var doc = JsonDocument.Parse(JsonSerializer.Serialize(state, _json));
        var root = doc.RootElement;
        var connection = root.GetProperty("connection");
        var headline = connection.GetProperty("headline").GetString() ?? "Not connected";
        var battery = connection.TryGetProperty("battery", out var b) && b.ValueKind == JsonValueKind.Number
            ? $"{b.GetInt32()}%"
            : "—";
        var profile = root.TryGetProperty("activeProfile", out var p) && p.ValueKind == JsonValueKind.String
            ? p.GetString()
            : null;
        _tray.Update(headline, battery, profile);
    }

    private void PushEvent(string eventName, object payload)
    {
        if (!_webReady || Dispatcher.HasShutdownStarted) return;
        _ = Dispatcher.InvokeAsync(() => Post(new { type = "event", @event = eventName, payload }));
    }

    private void Post(object value)
    {
        if (!_webReady || Web.CoreWebView2 is null) return;
        Web.CoreWebView2.PostWebMessageAsJson(JsonSerializer.Serialize(value, _json));
    }

    private void HideToTray()
    {
        Hide();
        if (!_trayNoticeShown)
        {
            _trayNoticeShown = true;
            _tray.ShowFirstMinimizeNotice();
        }
    }

    private void ShowFromTray()
    {
        Show();
        WindowState = WindowState.Normal;
        Activate();
    }

    private void ExitNow()
    {
        _allowClose = true;
        Close();
    }

    private async void MainWindow_Closing(object? sender, CancelEventArgs e)
    {
        if (!_allowClose)
        {
            e.Cancel = true;
            HideToTray();
            return;
        }

        _webReady = false;
        _gamepad.Dispose();
        _tray.Dispose();
        await _controller.DisposeAsync();
    }

    public void ForceCloseForTesting()
    {
        _allowClose = true;
        Close();
    }

    private sealed record BridgeRequest(string Id, string Action, JsonElement Payload);
}
