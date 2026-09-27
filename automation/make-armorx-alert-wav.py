#!/usr/bin/env python3
"""Generate the ARMOR-X alert tone (unmistakable, not a click).

Pure Python standard library (wave + math): several alternating
700-1000 Hz tones with a short silence, 16-bit mono 44.1 kHz, ~2.4 s.
Written because /usr/share/sounds had no suitable alarm/warning file for a
guaranteed-audible alert, and no external tools may be assumed installed.
"""
import math
import struct
import sys
import wave

OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/salamanka/armorx-lab/automation/armorx-alert.wav"
RATE = 44100
AMP = 0.72

# (frequency Hz, seconds) -- 0 Hz means silence
PATTERN = [
    (700, 0.30), (1000, 0.30), (700, 0.30),
    (0, 0.15),
    (1000, 0.40), (700, 0.40),
    (0, 0.20),
    (1000, 0.30), (700, 0.30),
    (0, 0.10),
]


def envelope(i, n, rate):
    """5 ms raised-cosine attack/release so the tone has no click artefacts."""
    ramp = int(0.005 * rate)
    if ramp <= 0:
        return 1.0
    if i < ramp:
        return 0.5 - 0.5 * math.cos(math.pi * i / ramp)
    if i > n - ramp:
        return 0.5 - 0.5 * math.cos(math.pi * (n - i) / ramp)
    return 1.0


def main():
    frames = bytearray()
    for freq, dur in PATTERN:
        n = int(dur * RATE)
        for i in range(n):
            if freq <= 0:
                s = 0.0
            else:
                # arcade-style: fundamental + light 3rd harmonic for penetration
                t = i / RATE
                s = math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(2 * math.pi * 3 * freq * t)
                s = max(-1.0, min(1.0, s * 0.8))
                s *= envelope(i, n, RATE)
            frames += struct.pack("<h", int(s * AMP * 32767))
    with wave.open(OUT, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))
    print(f"wrote {OUT}: {len(frames) // 2} frames, {len(frames) / 2 / RATE:.2f} s, {RATE} Hz mono 16-bit")


if __name__ == "__main__":
    main()
