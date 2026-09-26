using System.Windows;
using ArmorX.Windows.Config;

namespace ArmorX.Windows;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        if (e.Args.Any(x => string.Equals(x, "--ui-smoke", StringComparison.OrdinalIgnoreCase)))
        {
            try
            {
                var window = new MainWindow();
                window.Measure(new Size(1200, 860));
                window.Close();
                Shutdown(0);
            }
            catch
            {
                Shutdown(3);
            }
            return;
        }

        if (e.Args.Any(x => string.Equals(x, "--self-test", StringComparison.OrdinalIgnoreCase)))
        {
            try
            {
                var bytes = new byte[ArmorXConfig144.Size];
                bytes[2] = 0x00;
                bytes[3] = 0x90;
                var config = new ArmorXConfig144(bytes);
                config.RecalculateCrc();
                if (!config.CrcValid) throw new InvalidOperationException("CRC self-test failed.");
                if (!EditableArmorXConfig.ProvenMappingTargets.Any(x => x.Id == 12 && x.Name.Contains("Guide", StringComparison.OrdinalIgnoreCase)))
                    throw new InvalidOperationException("Guide mapping self-test failed.");
                Shutdown(0);
            }
            catch
            {
                Shutdown(1);
            }
            return;
        }

        DispatcherUnhandledException += (_, args) =>
        {
            MessageBox.Show(args.Exception.ToString(), "ArmorX Windows - unexpected error", MessageBoxButton.OK, MessageBoxImage.Error);
            args.Handled = true;
        };

        try
        {
            var window = new MainWindow();
            MainWindow = window;
            window.Show();
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.ToString(), "ArmorX Windows - startup error", MessageBoxButton.OK, MessageBoxImage.Error);
            Shutdown(2);
        }
    }
}
