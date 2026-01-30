import socket
import sounddevice as sd
import numpy as np
import datetime
import os
import time
import queue
import math
import crepe
import contextlib
import sys
import io
from scipy import signal


# ---------------- CONFIG ----------------

OUTPUT_PATH = 'output/audio_log.txt'
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)


# For complex music detection
STEP_MS = 10
CONF_THRESHOLD = 0.50  # Lower threshold (was 0.80)
BUFFER_SECONDS = .25    # Longer analysis window (was 0.6)
SMOOTH_FRAMES = 10      # More smoothing (was 5)
MIN_NOTE_MS = 40       # Slightly longer to filter rapid fluctuations

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F',
              'F#', 'G', 'G#', 'A', 'A#', 'B']

MIN_NOTE_FRAMES = int(MIN_NOTE_MS / STEP_MS)


CHOICE = '6'

# ---------------- HELPERS ----------------

def preprocess_audio(audio_np, rate):
    # High-pass filter at 80 Hz to remove bass rumble
    sos = signal.butter(4, 80, 'hp', fs=rate, output='sos')
    return signal.sosfilt(sos, audio_np)

def hz_to_note(freq_hz):
    if freq_hz <= 0:
        return None
    midi = round(69 + 12 * math.log2(freq_hz / 440.0))
    name = NOTE_NAMES[midi % 12]
    octave = midi // 12 - 1
    return f"{name}{octave}"

# ---------------- MONITOR ----------------

class AudioMonitor:
    def __init__(self, log_file=OUTPUT_PATH):
        self.RATE = 44100
        self.CHUNK = 4096

        self.audio_queue = queue.Queue()
        self.audio_buffer = []

        self.buffer_seconds = BUFFER_SECONDS
        self.last_emitted_note = None

        self.log_file = log_file
        open(self.log_file, 'w').close()

        # UDP
        self.UDP_IP = "127.0.0.1"
        self.UDP_PORT = 5005
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.current_note = None
        self.current_count = 0

        self.note_locked = False

    # ---------- I/O ----------

    def send_pitch_udp(self, pitch):
        try:
            self.udp_sock.sendto(f"{pitch:.2f}".encode(),
                                 (self.UDP_IP, self.UDP_PORT))
        except Exception:
            pass

    def log_data(self, pitch, note):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{ts}] Pitch: {pitch:8.2f} Hz | Note: {note}\n"
        print(line.strip())
        with open(self.log_file, "a") as f:
            f.write(line)

    # ---------- DEVICE SELECTION ----------

    def list_devices(self):
        print("\n" + "=" * 80)
        print("AVAILABLE AUDIO INPUT DEVICES")
        print("=" * 80)

        devices = sd.query_devices()

        for i, d in enumerate(devices):
            if d['max_input_channels'] <= 0:
                continue

            name = d['name'].lower()
            is_loopback = any(
                k in name for k in
                ['stereo mix', 'what u hear', 'wave out',
                 'loopback', 'wasapi', 'primary sound']
            )

            marker = " ← LOOPBACK?" if is_loopback else ""
            print(f"[{i}] {d['name']}{marker}")
            print(f"     Channels: {d['max_input_channels']}")
            print(f"     Default SR: {d['default_samplerate']} Hz\n")

    def select_device(self):
        self.list_devices()

        if CHOICE:
            choice = CHOICE.strip()
        else:
            choice = input("Enter device number: ").strip()
        return int(choice)

    # ---------- AUDIO ----------

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print(status)
        self.audio_queue.put(indata.copy())

    # ---------- MAIN LOOP ----------

    def start_monitoring(self):
        device_idx = self.select_device()
        dev = sd.query_devices(device_idx)

        print("\n" + "=" * 80)
        print(f"Monitoring: {dev['name']}")
        print(f"Sample rate: {self.RATE}")
        print("=" * 80)
        print("Listening... (Ctrl+C to stop)\n")

        with sd.InputStream(
            device=device_idx,
            channels=min(2, dev['max_input_channels']),
            samplerate=self.RATE,
            blocksize=self.CHUNK,
            callback=self.audio_callback
        ):
            while True:
                try:
                    audio = self.audio_queue.get(timeout=1)

                    if audio.ndim > 1:
                        audio = audio.mean(axis=1)

                    self.audio_buffer.append(audio)

                    total_samples = sum(len(x) for x in self.audio_buffer)
                    if total_samples / self.RATE < self.buffer_seconds:
                        continue

                    audio_np = np.concatenate(self.audio_buffer).astype(np.float32)
                    audio_np = preprocess_audio(audio_np, self.RATE)
                    self.audio_buffer = []

                    # -------- CREPE --------

                    with contextlib.redirect_stdout(io.StringIO()):
                        _, frequency, confidence, _ = crepe.predict(
                            audio_np,
                            self.RATE,
                            step_size=STEP_MS,
                            viterbi=True,
                            model_capacity="small"
                        )

                    frequency[confidence < CONF_THRESHOLD] = np.nan

                    kernel = np.ones(SMOOTH_FRAMES)
                    valid = np.isfinite(frequency).astype(float)
                    freq_filled = np.nan_to_num(frequency, nan=0.0)

                    smoothed = np.convolve(freq_filled, kernel, mode="same") / \
                               np.maximum(np.convolve(valid, kernel, mode="same"), 1e-9)

                    for f in smoothed:
                        if not np.isfinite(f) or f <= 0:
                            continue

                        note = hz_to_note(float(f))

                        # reset if silence or invalid
                        if note is None:
                            self.current_note = None
                            self.current_count = 0
                            self.note_locked = False
                            continue

                        # same note → count
                        if note == self.current_note:
                            self.current_count += 1
                        else:
                            # note changed → unlock and restart count
                            self.current_note = note
                            self.current_count = 1
                            self.note_locked = False

                        # emit ONCE per note region
                        if (
                                not self.note_locked and
                                self.current_count >= MIN_NOTE_FRAMES
                        ):
                            self.note_locked = True
                            self.last_emitted_note = note
                            self.log_data(f, note)
                            self.send_pitch_udp(f)



                except queue.Empty:
                    continue
                except KeyboardInterrupt:
                    print("\nStopped.")
                    return


# ---------------- RUN ----------------

if __name__ == "__main__":
    AudioMonitor().start_monitoring()
