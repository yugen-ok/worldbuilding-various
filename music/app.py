import socket
import tkinter as tk
import math

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

root = tk.Tk()
root.title("Musical Pitch Visualizer")
root.geometry("600x650")
root.configure(bg="black")

# Frequency display
label = tk.Label(root, text="--- Hz", font=("Consolas", 32), fg="lime", bg="black")
label.pack(pady=10)

# Canvas for spiral
canvas = tk.Canvas(root, width=600, height=600, bg="black", highlightthickness=0)
canvas.pack()

# Note names
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# A4 = 440 Hz reference
A4 = 440.0


def hz_to_point_index(hz):
    """Convert frequency to point index (0-47) on the spiral"""
    if hz <= 0:
        return 0
    # Calculate semitones from A4
    semitones = 12 * math.log2(hz / A4)
    # A4 is in octave 4, and A is note 9
    # We'll use octaves 2-5 (C2 to B5)
    # C2 is -33 semitones from A4
    point = round(semitones + 33)
    # Clamp to 0-47
    return max(0, min(47, point))


def point_to_note_name(point):
    """Convert point index to note name like 'A2'"""
    octave = (point // 12) + 2  # Starting from octave 2
    note = point % 12
    return f"{NOTE_NAMES[note]}{octave}"


current_point = 0


def draw_spiral():
    canvas.delete("all")

    center_x = 300
    center_y = 300
    base_radius = 30

    # Draw 48 points (4 octaves × 12 notes) on a true spiral
    for i in range(48):
        # Spiral parameters: radius grows continuously, angle increases continuously
        # After each full rotation (12 notes), radius doubles
        angle = (i / 12) * 2 * math.pi - math.pi / 2
        radius = base_radius * (2 ** (i / 12))

        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)

        # Highlight current point
        is_active = (i == current_point)
        point_size = 8 if is_active else 3
        color = "lime" if is_active else "gray30"

        canvas.create_oval(
            x - point_size, y - point_size,
            x + point_size, y + point_size,
            fill=color, outline=color
        )

    # Draw note name in center
    note_name = point_to_note_name(current_point)
    canvas.create_text(
        center_x, center_y,
        text=note_name,
        fill="lime",
        font=("Consolas", 48, "bold")
    )


def poll_socket():
    global current_point
    try:
        while True:
            data, _ = sock.recvfrom(1024)
            hz_str = data.decode("utf-8")
            try:
                hz = float(hz_str)
                current_point = hz_to_point_index(hz)
                label.config(text=f"{hz_str} Hz")
                draw_spiral()
            except ValueError:
                pass
    except BlockingIOError:
        pass

    root.after(20, poll_socket)


# Initial draw
draw_spiral()
poll_socket()

root.mainloop()