using System.Windows;
using ArmorX.Windows.Config;
using ArmorX.Windows.Protocol;
using ArmorX.Windows.Research;

namespace ArmorX.Windows;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        if (e.Args.Any(x => string.Equals(x, "--ui-smoke", StringComparison.OrdinalIgnoreCase)))
        {
            try
            {
                var window = new D8ResearchWindow();
                window.Measure(new Size(1080, 760));
                window.Arrange(new Rect(0, 0, 1080, 760));
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

                if (Convert.ToHexString(ArmorXFrames.GetMacroList) != "A504D57E")
                    throw new InvalidOperationException("D5/GetMacroList frame self-test failed.");

                var synthetic = Enumerable.Range(0, 37).Select(i => (byte)(i + 1)).ToArray();
                var frames = ArmorXFrames.FragmentLong(ArmorXFrames.OpWriteMacro, synthetic).ToArray();
                var analysis = D8CaptureAnalyzer.AnalyzePackets(frames, "synthetic-self-test");
                if (analysis.Transfers.Count != 1 ||
                    analysis.Transfers[0].PayloadLength != synthetic.Length ||
                    !Convert.FromHexString(analysis.Transfers[0].PayloadHex).SequenceEqual(synthetic))
                    throw new InvalidOperationException("D8 analyzer reassembly self-test failed.");

                var modified = synthetic.ToArray();
                modified[5] ^= 0x55;
                var modifiedAnalysis = D8CaptureAnalyzer.AnalyzePackets(
                    ArmorXFrames.FragmentLong(ArmorXFrames.OpWriteMacro, modified),
                    "synthetic-diff-self-test");
                var diff = D8CaptureAnalyzer.Compare(analysis.Transfers[0], modifiedAnalysis.Transfers[0]);
                if (diff.ChangedSharedOffsets.Count != 1 || diff.ChangedSharedOffsets[0].Offset != 5)
                    throw new InvalidOperationException("D8 analyzer diff self-test failed.");

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
            MessageBox.Show(args.Exception.ToString(), "ArmorX D8 Research - unexpected error", MessageBoxButton.OK, MessageBoxImage.Error);
            args.Handled = true;
        };

        try
        {
            var window = new D8ResearchWindow();
            MainWindow = window;
            window.Show();
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.ToString(), "ArmorX D8 Research - startup error", MessageBoxButton.OK, MessageBoxImage.Error);
            Shutdown(2);
        }
    }
}
