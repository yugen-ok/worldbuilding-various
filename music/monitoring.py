import socket
import sounddevice as sd
import numpy as np
import datetime
import os
import time
from collections import deque
import queue
import sys


class AudioMonitor:
    def __init__(self, log_file="audio_log.txt"):
        self.CHUNK = 4096
        self.RATE = 44100
        self.log_file = log_file
        self.audio_queue = queue.Queue()
        self.pitch_buffer = deque(maxlen=5)

        # UDP output to external display
        self.UDP_IP = "127.0.0.1"
        self.UDP_PORT = 5005
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Display lock control (simple + robust)
        self.last_sent_pitch = None
        self.last_sent_time = 0.0

        self.PITCH_CHANGE_CENTS = 80     # must be clearly different
        self.MIN_SEND_INTERVAL = 0.3     # seconds

    def cents_diff(self, a, b):
        return abs(1200 * np.log2(a / b))


    def send_pitch_udp(self, pitch):
        """Send current pitch (Hz) to external app via UDP"""
        if pitch is None:
            return
        try:
            msg = f"{pitch:.2f}"
            self.udp_sock.sendto(msg.encode("utf-8"),
                                 (self.UDP_IP, self.UDP_PORT))
        except Exception:
            pass  # never let UI/IPC break audio

    def list_devices(self):
        """List all available audio devices with detailed info"""
        print("\n" + "=" * 80)
        print("AVAILABLE AUDIO INPUT DEVICES:")
        print("=" * 80)

        devices = sd.query_devices()
        input_devices = []

        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                hostapi = sd.query_hostapis(device['hostapi'])
                input_devices.append(i)

                # Highlight likely loopback devices
                is_loopback = any(keyword in device['name'].lower()
                                  for keyword in ['stereo mix', 'wave out', 'what u hear',
                                                  'loopback', 'wasapi', 'primary sound'])

                marker = " ← LOOPBACK?" if is_loopback else ""

                print(f"\n[{i}] {device['name']}{marker}")
                print(f"    Host API: {hostapi['name']}")
                print(f"    Input Channels: {device['max_input_channels']}")
                print(f"    Default Sample Rate: {device['default_samplerate']} Hz")

        print("\n" + "=" * 80)
        return input_devices

    def test_device(self, device_id):
        """Test if a device can be opened"""
        try:
            device_info = sd.query_devices(device_id)
            channels = min(2, device_info['max_input_channels'])

            # Try non-blocking callback mode for WDM-KS devices
            def dummy_callback(indata, frames, time, status):
                pass

            with sd.InputStream(
                    device=device_id,
                    channels=channels,
                    samplerate=int(device_info['default_samplerate']),
                    blocksize=1024,
                    callback=dummy_callback
            ):
                time.sleep(0.1)  # Brief test
            return True
        except Exception as e:
            print(f"Cannot use device {device_id}: {e}")
            return False

    def select_device(self):
        """Interactive device selection"""
        input_devices = self.list_devices()

        if not input_devices:
            print("\nERROR: No input devices found!")
            return None

        print("\nNOTE: To capture system audio (what's playing), you need:")
        print("  - Windows: Enable 'Stereo Mix' in Sound Settings")
        print("  - Look for devices marked '← LOOPBACK?' above")
        print()

        while True:
            try:
                choice = input("Enter device number (or 'q' to quit): ").strip()

                if choice.lower() == 'q':
                    return None

                device_id = int(choice)

                if device_id not in input_devices:
                    print(f"Invalid choice. Please select from: {input_devices}")
                    continue

                # Test the device
                print(f"\nTesting device {device_id}...")
                if self.test_device(device_id):
                    print(f"✓ Device {device_id} is working!")
                    return device_id
                else:
                    print(f"✗ Device {device_id} cannot be opened. Try another.")

            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                print("\n\nCancelled.")
                return None

    def audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream"""
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())

    def get_pitch_and_frequency(self, audio_data):
        """Extract pitch and frequency from audio data using zero-crossing"""
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = (audio_data[:, 0] + audio_data[:, 1]) / 2.0

        # Calculate RMS (volume/amplitude)
        rms = (sum(x ** 2 for x in audio_data) / len(audio_data)) ** 0.5

        # Only process if there's significant audio
        if rms < 0.0001:
            return None, None, 0.0

        # Zero-crossing rate method for pitch
        try:
            # Count zero crossings
            zero_crossings = 0
            for i in range(1, len(audio_data)):
                if (audio_data[i - 1] >= 0 and audio_data[i] < 0) or \
                        (audio_data[i - 1] < 0 and audio_data[i] >= 0):
                    zero_crossings += 1

            # Estimate frequency from zero crossings
            # Each cycle has 2 zero crossings
            if zero_crossings > 10:
                frequency = (zero_crossings / 2.0) * self.RATE / len(audio_data)

                if 50 < frequency < 2000:  # Valid range
                    self.pitch_buffer.append(frequency)
                    # Simple median without numpy
                    sorted_buffer = sorted(list(self.pitch_buffer))
                    stable_pitch = sorted_buffer[len(sorted_buffer) // 2]
                    return stable_pitch, self.pitch_to_note(stable_pitch), rms

        except Exception as e:
            print(f"Pitch error: {e}")

        return None, None, rms

    def pitch_to_note(self, frequency):
        """Convert frequency to musical note"""
        if frequency <= 0:
            return "N/A"

        A4 = 440.0
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        half_steps = 12 * np.log2(frequency / A4)
        octave = 4 + (half_steps + 9) // 12
        note_idx = int(round(half_steps + 9)) % 12

        return f"{notes[note_idx]}{int(octave)}"

    def get_dominant_frequency(self, audio_data):
        """Get dominant frequency using simple FFT"""
        try:
            if len(audio_data.shape) > 1:
                audio_data = (audio_data[:, 0] + audio_data[:, 1]) / 2.0

            # Use numpy FFT - this should work
            import numpy.fft as fft_module
            n = len(audio_data)
            fft_result = fft_module.fft(audio_data)
            magnitude = [abs(x) for x in fft_result[:n // 2]]
            freqs = [i * self.RATE / n for i in range(n // 2)]

            # Find peak frequency (skip very low frequencies < 20Hz)
            max_mag = 0
            peak_freq = 0.0
            for i, freq in enumerate(freqs):
                if freq > 20 and magnitude[i] > max_mag:
                    max_mag = magnitude[i]
                    peak_freq = freq

            return peak_freq
        except Exception as e:
            return 0.0

    def log_data(self, pitch, note, rms, fft_peak):
        """Write audio data to log file"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        pitch_str = f"{pitch:.2f} Hz" if pitch else "N/A"
        note_str = note if note else "N/A"
        rms_db = 20 * np.log10(rms) if rms > 0 else -100

        log_line = f"[{timestamp}] Pitch: {pitch_str:>12} | Note: {note_str:>4} | " \
                   f"Volume: {rms_db:>6.1f} dB | Peak Freq: {fft_peak:.1f} Hz\n"

        with open(self.log_file, 'a') as f:
            f.write(log_line)

        # Also print to console
        print(log_line.strip())

    def start_monitoring(self):
        """Start monitoring audio output"""

        self.send_pitch_udp(440.0)
        time.sleep(1)
        self.send_pitch_udp(440.0)

        print("\n" + "=" * 80)
        print("AUDIO MONITOR - Real-time Pitch & Frequency Logger")
        print("=" * 80)

        device_idx = self.select_device()

        if device_idx is None:
            print("\nExiting...")
            return

        # Get device info
        device_info = sd.query_devices(device_idx)
        channels = min(2, device_info['max_input_channels'])

        print(f"\n{'=' * 80}")
        print(f"Monitoring: {device_info['name']}")
        print(f"Channels: {channels}")
        print(f"Sample Rate: {self.RATE} Hz")
        print(f"Log file location: {os.path.abspath(self.log_file)}")
        print(f"{'=' * 80}")
        print("\nListening for audio... (Press Ctrl+C to stop)")
        print("NOTE: Make some noise/play audio to see logging!")
        print()

        try:
            # Open audio stream
            with sd.InputStream(
                    device=device_idx,
                    channels=channels,
                    samplerate=self.RATE,
                    blocksize=self.CHUNK,
                    callback=self.audio_callback
            ):
                while True:
                    try:
                        # Get audio data from queue
                        audio_data = self.audio_queue.get(timeout=1)

                        # Get pitch and frequency
                        pitch, note, rms = self.get_pitch_and_frequency(audio_data)
                        fft_peak = self.get_dominant_frequency(audio_data)

                        # Log if there's ANY audio (lowered threshold)
                        if rms > 0.0001:
                            self.log_data(pitch, note, rms, fft_peak)

                            now = time.time()

                            if pitch is None:
                                pass

                            elif self.last_sent_pitch is None:
                                # first pitch → accept immediately
                                self.send_pitch_udp(pitch)
                                self.last_sent_pitch = pitch
                                self.last_sent_time = now

                            elif (
                                    self.cents_diff(pitch, self.last_sent_pitch) > self.PITCH_CHANGE_CENTS
                                    and (now - self.last_sent_time) > self.MIN_SEND_INTERVAL
                            ):
                                # clearly new pitch → update
                                self.send_pitch_udp(pitch)
                                self.last_sent_pitch = pitch
                                self.last_sent_time = now

                        # Debug: print RMS values every 2 seconds even if quiet
                        if not hasattr(self, '_last_debug'):
                            self._last_debug = time.time()
                        if time.time() - self._last_debug > 2:
                            print(f"[DEBUG] Current RMS: {rms:.6f}")
                            self._last_debug = time.time()

                    except queue.Empty:
                        continue
                    except KeyboardInterrupt:
                        raise

        except KeyboardInterrupt:
            print("\n\n" + "=" * 80)
            print("Monitoring stopped")
            print("=" * 80)
        except Exception as e:
            print(f"\nError during monitoring: {e}")

        finally:
            print(f"Log saved to: {os.path.abspath(self.log_file)}")


if __name__ == "__main__":
    # Save to Desktop for easy access
    desktop = os.path.join(os.path.expanduser("~"), "Desktop", "audio_output_log.txt")
    monitor = AudioMonitor(log_file=desktop)
    monitor.start_monitoring()