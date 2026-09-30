using ArmorX.Windows.Config;
using ArmorX.Windows.Profiles;

try
{
    var bytes = new byte[ArmorXConfig144.Size];
    bytes[2] = 0x00;
    bytes[3] = 0x90;
    var config = new ArmorXConfig144(bytes);
    config.RecalculateCrc();
    if (!config.CrcValid)
        throw new InvalidOperationException("CRC self-test failed.");

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
        var store = new ProfileStore(tempProfiles);
        await store.SaveAsync("Self Test", config, "TEST", "TEST");
        var loaded = await store.LoadAsync("Self Test");
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
            _ = await store.LoadAsync("Self Test");
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

    Console.WriteLine("ArmorX Studio core backend self-test PASS.");
    return 0;
}
catch (Exception ex)
{
    Console.Error.WriteLine(ex);
    return 1;
}
