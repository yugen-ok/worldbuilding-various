import math
import winsound
import time

# ----------------------------
# Config
# ----------------------------
NOTE_DURATION = 5000  # milliseconds
PAUSE = 50            # ms between notes

# ----------------------------
# Note → frequency
# ----------------------------
NOTE_OFFSETS = {
    "C": -9, "C#": -8, "D": -7, "D#": -6,
    "E": -5, "F": -4, "F#": -3,
    "G": -2, "G#": -1,
    "A": 0, "A#": 1, "B": 2,
}

def note_to_freq(note):
    name = note[:-1]
    octave = int(note[-1])
    semitones = NOTE_OFFSETS[name] + (octave - 4) * 12
    return int(440 * (2 ** (semitones / 12)))

def play_melody(melody):
    for token in melody.split():
        if token == "_":
            time.sleep(NOTE_DURATION / 1000)
        else:
            freq = note_to_freq(token)
            winsound.Beep(freq, NOTE_DURATION)
            time.sleep(PAUSE / 1000)

# ----------------------------
# Example
# ----------------------------
melody = "A2 B2 C3 D3 C3 B2 A2"
play_melody(melody)
