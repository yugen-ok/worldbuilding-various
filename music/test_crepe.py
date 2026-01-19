import crepe
import soundfile as sf
import numpy as np
import pretty_midi

import math

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F',
              'F#', 'G', 'G#', 'A', 'A#', 'B']


# ---- tuning knobs ----
CONF_THRESHOLD = 0.80     # ignore uncertain frames
SMOOTH_MS = 60            # smoothing window in milliseconds
STEP_MS = 10              # must match step_size above
SMOOTH_FRAMES = max(1, int(round(SMOOTH_MS / STEP_MS)))


MIN_NOTE_MS = 80        # minimum duration to accept a note
MIN_NOTE_FRAMES = int(round(MIN_NOTE_MS / STEP_MS))
MIN_GAP = 0.01  # seconds (10 ms silence between notes)

MIN_MIDI_NOTE_MS = 200  # must be >= MIN_NOTE_MS
MIN_MIDI_NOTE_S = MIN_MIDI_NOTE_MS / 1000.0

audio, sr = sf.read("data/greensleeves.wav")


if audio.ndim > 1:
    audio = np.mean(audio, axis=1)

time, frequency, confidence, _ = crepe.predict(
    audio,
    sr,
    step_size=10,      # ms
    viterbi=False,
    model_capacity="small"
)


def hz_to_note(freq_hz: float) -> str | None:
    if freq_hz <= 0:
        return None
    midi = round(69 + 12 * math.log2(freq_hz / 440.0))
    name = NOTE_NAMES[midi % 12]
    octave = midi // 12 - 1
    return f"{name}{octave}"

# 1) drop low-confidence frames
freq = frequency.copy()
freq[confidence < CONF_THRESHOLD] = np.nan

# 2) smooth using moving average (ignoring NaNs)
kernel = np.ones(SMOOTH_FRAMES, dtype=float)
valid = np.isfinite(freq).astype(float)
freq_filled = np.nan_to_num(freq, nan=0.0)

smoothed = np.convolve(freq_filled, kernel, mode="same") / np.maximum(
    np.convolve(valid, kernel, mode="same"), 1e-9
)

# 3) turn smoothed pitch into a stable note stream (print only changes)
current_note = None
current_count = 0

for t, f in zip(time, smoothed):
    if not np.isfinite(f) or f <= 0:
        current_note = None
        current_count = 0
        continue

    note = hz_to_note(float(f))
    if note is None:
        continue

    if note == current_note:
        current_count += 1
    else:
        current_note = note
        current_count = 1

    # accept note only if it was stable long enough
    if current_count == MIN_NOTE_FRAMES:
        print(f"{t:.3f}s  {note}")

# ---------------- MIDI GENERATION ----------------

midi = pretty_midi.PrettyMIDI()
instrument = pretty_midi.Instrument(program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano"))

NOTE_TO_MIDI = {
    'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4,
    'F': 5, 'F#': 6, 'G': 7, 'G#': 8,
    'A': 9, 'A#': 10, 'B': 11
}

def note_name_to_midi(note: str) -> int:
    name = note[:-1]
    octave = int(note[-1])
    return 12 * (octave + 1) + NOTE_TO_MIDI[name]

# rebuild the same stable-note logic, but store times
events = []

current_note = None
current_start = None
current_count = 0

for t, f in zip(time, smoothed):
    if not np.isfinite(f) or f <= 0:
        # IMPORTANT: do NOT close the note yet
        current_count = 0
        continue

    note = hz_to_note(float(f))
    if note is None:
        continue

    if note == current_note:
        current_count += 1
    else:
        # note changed → close previous note
        if current_note is not None:
            events.append((current_note, current_start, t))

        current_note = note
        current_start = t
        current_count = 1

# flush last note
if current_note is not None:
    events.append((current_note, current_start, time[-1]))


# ---- remove ultra-short ghost notes ----

events = [
    (note, start, end)
    for note, start, end in events
    if end - start >= MIN_MIDI_NOTE_S
]



# write MIDI notes
prev_end = None

instrument.notes = []

for i, (note, start, end) in enumerate(events):
    # force strict legato: end = next start
    if i + 1 < len(events):
        end = events[i + 1][1]

    midi_note = note_name_to_midi(note)

    instrument.notes.append(
        pretty_midi.Note(
            velocity=90,
            pitch=midi_note,
            start=float(start),
            end=float(end)
        )
    )

midi.instruments.append(instrument)

midi.write("output/output_crepe.mid")

