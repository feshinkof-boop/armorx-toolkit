using System.Drawing;
using System.Windows.Forms;

namespace ArmorX.Windows.Tray;

public sealed class TrayService : IDisposable
{
    private readonly NotifyIcon _icon;
    private readonly ToolStripMenuItem _status;
    private readonly ToolStripMenuItem _battery;
    private readonly ToolStripMenuItem _profile;

    public event EventHandler? ShowRequested;
    public event EventHandler? ExitRequested;

    public TrayService()
    {
        _status = new ToolStripMenuItem("Status: Not connected") { Enabled = false };
        _battery = new ToolStripMenuItem("Battery: —") { Enabled = false };
        _profile = new ToolStripMenuItem("Profile: Live configuration") { Enabled = false };

        var show = new ToolStripMenuItem("Open ArmorX Studio");
        show.Click += (_, _) => ShowRequested?.Invoke(this, EventArgs.Empty);
        var exit = new ToolStripMenuItem("Exit");
        exit.Click += (_, _) => ExitRequested?.Invoke(this, EventArgs.Empty);

        var menu = new ContextMenuStrip();
        menu.Items.AddRange(new ToolStripItem[]
        {
            _status, _battery, _profile,
            new ToolStripSeparator(),
            show,
            new ToolStripSeparator(),
            exit
        });

        _icon = new NotifyIcon
        {
            Icon = SystemIcons.Application,
            Text = "ArmorX Studio",
            Visible = true,
            ContextMenuStrip = menu
        };
        _icon.DoubleClick += (_, _) => ShowRequested?.Invoke(this, EventArgs.Empty);
    }

    public void Update(string connection, string battery, string? profile)
    {
        _status.Text = $"Status: {connection}";
        _battery.Text = $"Battery: {battery}";
        _profile.Text = $"Profile: {(string.IsNullOrWhiteSpace(profile) ? "Live configuration" : profile)}";
        var shortConnection = connection.Length > 26 ? connection[..26] : connection;
        var shortProfile = string.IsNullOrWhiteSpace(profile) ? "Live" :
            (profile.Length > 18 ? profile[..18] : profile);
        var text = $"ArmorX · {shortConnection} · {battery} · {shortProfile}";
        _icon.Text = text.Length > 63 ? text[..63] : text;
    }

    public void ShowFirstMinimizeNotice()
    {
        _icon.BalloonTipTitle = "ArmorX Studio is still running";
        _icon.BalloonTipText = "Live battery/profile status stays in the system tray. Use Exit from the tray to quit.";
        _icon.ShowBalloonTip(2500);
    }

    public void Dispose()
    {
        _icon.Visible = false;
        _icon.Dispose();
    }
}
