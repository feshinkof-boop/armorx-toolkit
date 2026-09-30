using System.Windows;
using ArmorX.Windows.Config;

namespace ArmorX.Windows;

public partial class App : System.Windows.Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        if (e.Args.Any(x => string.Equals(x, "--self-test", StringComparison.OrdinalIgnoreCase)))
        {
            Environment.Exit(RunSelfTest() ? 0 : 1);
            return;
        }

        if (e.Args.Any(x => string.Equals(x, "--ui-smoke", StringComparison.OrdinalIgnoreCase)))
        {
            try
            {
                var window = new MainWindow();
                window.Measure(new System.Windows.Size(1280, 800));
                window.ForceCloseForTesting();
                Shutdown(0);
                Environment.Exit(0);
            }
            catch
            {
                Shutdown(3);
            }
            return;
        }

        DispatcherUnhandledException += (_, args) =>
        {
            System.Windows.MessageBox.Show(
                args.Exception.ToString(),
                "ArmorX Studio - unexpected error",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
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
            System.Windows.MessageBox.Show(
                ex.ToString(),
                "ArmorX Studio - startup error",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
            Shutdown(2);
        }
    }

    private static bool RunSelfTest()
    {
        try
        {
            var bytes = new byte[ArmorXConfig144.Size];
            bytes[2] = 0x00;
            bytes[3] = 0x90;
            var config = new ArmorXConfig144(bytes);
            config.RecalculateCrc();
            if (!config.CrcValid) throw new InvalidOperationException("CRC self-test failed.");

            if (!EditableArmorXConfig.ProvenMappingTargets.Any(
                    x => x.Id == 12 && x.Name.Contains("Guide", StringComparison.OrdinalIgnoreCase)))
                throw new InvalidOperationException("Guide mapping self-test failed.");

            var before = new ArmorXConfig144(config.ToArray());
            var editedBytes = config.ToArray();
            editedBytes[135] = 1;
            var edited = new ArmorXConfig144(editedBytes);
            edited.RecalculateCrc();
            var diff = ConfigDiff.Compare(before, edited);
            if (diff.Count != 1 || diff[0].Offset != 135)
                throw new InvalidOperationException("Config diff self-test failed.");

            var currentBytes = before.ToArray();
            currentBytes[100] = 0x5A;
            var current = new ArmorXConfig144(currentBytes);
            current.RecalculateCrc();
            var merged = ConfigDiff.MergeEditorChanges(current, before.ToArray(), edited);
            if (merged.GetByte(100) != 0x5A || merged.GetByte(135) != 1 || !merged.CrcValid)
                throw new InvalidOperationException("Safe merge self-test failed.");

            var tempProfiles = Path.Combine(Path.GetTempPath(), "ArmorX-SelfTest-" + Guid.NewGuid().ToString("N"));
            try
            {
                var store = new ArmorX.Windows.Profiles.ProfileStore(tempProfiles);
                store.SaveAsync("Self Test", config, "TEST", "TEST").GetAwaiter().GetResult();
                var loaded = store.LoadAsync("Self Test").GetAwaiter().GetResult();
                if (!loaded.GetConfigBytes().SequenceEqual(config.ToArray()))
                    throw new InvalidOperationException("Profile round-trip self-test failed.");

                var file = Directory.EnumerateFiles(tempProfiles, "*.json").Single();
                var text = File.ReadAllText(file);
                var marker = Convert.ToBase64String(config.ToArray());
                var tampered = config.ToArray();
                tampered[20] ^= 1;
                File.WriteAllText(file, text.Replace(marker, Convert.ToBase64String(tampered)));
                try
                {
                    _ = store.LoadAsync("Self Test").GetAwaiter().GetResult();
                    throw new InvalidOperationException("Tampered profile was accepted.");
                }
                catch (InvalidDataException)
                {
                }
            }
            finally
            {
                try { if (Directory.Exists(tempProfiles)) Directory.Delete(tempProfiles, true); } catch { }
            }

            return true;
        }
        catch
        {
            return false;
        }
    }
}
