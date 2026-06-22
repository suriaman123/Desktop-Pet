"""
Yorkie Desktop Pet - A Yorkshire Terrier that lives on your Windows desktop!
Features:
  - Always-on-top transparent window
  - Click counter (mouse clicks + keypresses)
  - Woof on click with sound
  - 2D animated mode with moods (idle, happy, sleepy, hungry)
  - 3D Roam mode: dog walks along the taskbar
  - Hunger meter, tail wag, random woofs, sleeping animation
  - Draggable, right-click menu
"""

import tkinter as tk
from tkinter import font as tkfont
import math
import random
import time
import threading
import os
import sys
import struct
import wave
import io

# ── Colour palette ────────────────────────────────────────────────────────────
TAN      = "#C8A46E"   # Yorkie golden coat
DARK_BR  = "#3B2A1A"   # dark brown / saddle
STEEL    = "#6B8CAE"   # steel-blue-grey (face/legs)
NOSE_C   = "#1A1008"
EYE_C    = "#0D0700"
TONGUE   = "#E87070"
BARK_COL = "#FFD166"
BG_TRANS = "#010101"   # near-black used as transparency key on Windows
PANEL_BG = "#2B1D0E"
COUNTER_FG = "#FFD166"
HEART_COL  = "#FF6B9D"
ZZZ_COL    = "#A0C4FF"
STAR_COL   = "#FFF176"

# ── Sound generation (pure Python WAV) ────────────────────────────────────────
def _make_sine(freq, duration, volume=0.4, sample_rate=22050):
    n = int(sample_rate * duration)
    buf = bytearray()
    for i in range(n):
        t = i / sample_rate
        # slight harmonic mix for a barky texture
        val = (math.sin(2*math.pi*freq*t)
               + 0.4*math.sin(2*math.pi*freq*2.1*t)
               + 0.2*math.sin(2*math.pi*freq*0.5*t))
        val = val / 1.6   # normalize
        # amplitude envelope: quick attack, fast decay
        env = min(1.0, i/(sample_rate*0.01)) * max(0.0, 1-(i/(n*0.6)))**2
        val = int(val * env * volume * 32767)
        val = max(-32767, min(32767, val))
        buf += struct.pack('<h', val)
    return bytes(buf), sample_rate

def _write_wav(pcm_data, sample_rate=22050):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()

def _play_wav_bytes(wav_bytes):
    """Play WAV bytes on Windows using winsound, fallback: write temp file."""
    try:
        import winsound
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
            f.write(wav_bytes)
            fname = f.name
        winsound.PlaySound(fname, winsound.SND_FILENAME | winsound.SND_ASYNC)
        # cleanup after ~1 s
        threading.Timer(1.2, lambda: os.unlink(fname) if os.path.exists(fname) else None).start()
    except Exception:
        pass   # silent on non-Windows or missing winsound

# Pre-build the woof sound
_WOOF_PCM, _SR = _make_sine(380, 0.18, volume=0.55)
_WOOF_PCM2, _  = _make_sine(280, 0.22, volume=0.45)
_WOOF_WAV  = _write_wav(_WOOF_PCM  + _WOOF_PCM2)

def play_woof():
    threading.Thread(target=_play_wav_bytes, args=(_WOOF_WAV,), daemon=True).start()

# ── Canvas drawing helpers ────────────────────────────────────────────────────
def oval(c, x, y, rx, ry, **kw):
    return c.create_oval(x-rx, y-ry, x+rx, y+ry, **kw)

def roundrect(c, x1, y1, x2, y2, r=10, **kw):
    pts = [x1+r,y1, x2-r,y1, x2,y1+r, x2,y2-r, x2-r,y2, x1+r,y2, x1,y2-r, x1,y1+r]
    return c.create_polygon(pts, smooth=True, **kw)

# ── Yorkie 2-D drawing ─────────────────────────────────────────────────────────
def draw_yorkie_2d(canvas, cx, cy, scale=1.0, mood='idle',
                   tail_angle=0, blink=False, tongue_out=False):
    """Draw a cute Yorkshire Terrier centred at (cx, cy)."""
    s = scale
    tags = ('dog',)

    # ── Body ──────────────────────────────────────────────────────────────────
    # long silky body coat — golden/tan top, steely legs
    body_w, body_h = 54*s, 40*s
    # dark saddle
    canvas.create_oval(cx-body_w*0.55, cy-body_h*0.35,
                       cx+body_w*0.55, cy+body_h*0.65,
                       fill=DARK_BR, outline='', tags=tags)
    # golden chest
    canvas.create_oval(cx-body_w*0.42, cy-body_h*0.28,
                       cx+body_w*0.42, cy+body_h*0.58,
                       fill=TAN, outline='', tags=tags)

    # ── Tail ──────────────────────────────────────────────────────────────────
    tx = cx + body_w*0.5 + 6*s
    ty = cy - body_h*0.1
    for i in range(3):
        a = math.radians(tail_angle + i*18)
        ex = tx + math.cos(a)*22*s
        ey = ty - math.sin(a)*22*s
        canvas.create_line(tx, ty, ex, ey,
                           fill=DARK_BR, width=max(2, 5*s - i*1.5*s),
                           capstyle=tk.ROUND, tags=tags)

    # ── Legs ──────────────────────────────────────────────────────────────────
    leg_y_top = cy + body_h*0.35
    for lx in [cx-20*s, cx-6*s, cx+6*s, cx+20*s]:
        canvas.create_line(lx, leg_y_top, lx, leg_y_top+22*s,
                           fill=STEEL, width=max(2, 6*s),
                           capstyle=tk.ROUND, tags=tags)
        # paw
        oval(canvas, lx, leg_y_top+24*s, 5*s, 3*s,
             fill=DARK_BR, outline='', tags=tags)

    # ── Head ──────────────────────────────────────────────────────────────────
    hx, hy = cx - body_w*0.28, cy - body_h*0.45
    head_r = 22*s
    # head base (golden top-knot + dark muzzle split)
    oval(canvas, hx, hy, head_r, head_r, fill=DARK_BR, outline='', tags=tags)
    oval(canvas, hx, hy-5*s, head_r*0.82, head_r*0.75, fill=TAN, outline='', tags=tags)

    # Muzzle
    oval(canvas, hx, hy+6*s, head_r*0.55, head_r*0.4,
         fill=TAN, outline='', tags=tags)

    # Nose
    oval(canvas, hx, hy+3*s, 5*s, 3.5*s,
         fill=NOSE_C, outline='', tags=tags)
    # nose shine
    oval(canvas, hx-1.5*s, hy+2*s, 1.5*s, 1*s,
         fill='white', outline='', tags=tags)

    # Eyes (with blink)
    for ex_off in [-9*s, 9*s]:
        ex_ = hx + ex_off
        ey_ = hy - 2*s
        if blink:
            canvas.create_line(ex_-5*s, ey_, ex_+5*s, ey_,
                                fill=EYE_C, width=max(1, 2*s), tags=tags)
        else:
            oval(canvas, ex_, ey_, 5*s, 5.5*s,
                 fill=EYE_C, outline='', tags=tags)
            # shine
            oval(canvas, ex_+1.5*s, ey_-1.5*s, 1.5*s, 1.5*s,
                 fill='white', outline='', tags=tags)

    # Tongue
    if tongue_out:
        canvas.create_arc(hx-5*s, hy+8*s, hx+5*s, hy+18*s,
                          start=200, extent=140,
                          fill=TONGUE, outline='', style=tk.CHORD, tags=tags)

    # Ears — large floppy V-ears
    for side, ex_off in [(-1, -16*s), (1, 16*s)]:
        ear_pts = [
            hx+ex_off,          hy-12*s,
            hx+ex_off+side*14*s, hy-28*s,
            hx+ex_off+side*4*s,  hy+2*s,
        ]
        canvas.create_polygon(ear_pts, fill=DARK_BR, outline='', smooth=True, tags=tags)
        # inner ear gold
        inner = [
            hx+ex_off+side*0.3*s,   hy-10*s,
            hx+ex_off+side*10*s,     hy-24*s,
            hx+ex_off+side*3.5*s,    hy+1*s,
        ]
        canvas.create_polygon(inner, fill=TAN, outline='', smooth=True, tags=tags)

    # Top-knot bow 🎀
    bow_x, bow_y = hx, hy - head_r - 4*s
    for bside in [-1, 1]:
        canvas.create_oval(bow_x+bside*2*s, bow_y-5*s,
                           bow_x+bside*9*s, bow_y+5*s,
                           fill='#FF6B9D', outline='#C94070', width=max(1, s), tags=tags)
    oval(canvas, bow_x, bow_y, 3*s, 3*s,
         fill='#FF4488', outline='', tags=tags)

    # Mood decorations
    if mood == 'happy':
        # hearts
        for hpos in [(-30*s, -30*s), (20*s, -40*s)]:
            _draw_heart(canvas, cx+hpos[0], cy+hpos[1], 8*s, HEART_COL)
    elif mood == 'sleepy':
        # ZZZ
        for i, zp in enumerate([(20*s, -50*s), (30*s, -62*s)]):
            canvas.create_text(cx+zp[0], cy+zp[1],
                               text="z"*( i+1),
                               fill=ZZZ_COL, font=('Arial', max(8, int(10*s)), 'italic'),
                               tags=tags)
    elif mood == 'hungry':
        # stars / sparkles around
        for angle in range(0, 360, 90):
            sx = cx + 50*s * math.cos(math.radians(angle))
            sy = cy + 40*s * math.sin(math.radians(angle))
            _draw_star(canvas, sx, sy, 6*s, STAR_COL)

def _draw_heart(canvas, x, y, size, color):
    pts = []
    for i in range(31):
        t = math.radians(i * 12)
        hx = size * 16 * (math.sin(t)**3)
        hy = -size * (13*math.cos(t) - 5*math.cos(2*t) - 2*math.cos(3*t) - math.cos(4*t))
        pts.extend([x + hx/16, y + hy/16])
    if len(pts) >= 6:
        canvas.create_polygon(pts, fill=color, outline='', tags=('dog',))

def _draw_star(canvas, x, y, r, color):
    pts = []
    for i in range(10):
        a = math.radians(i*36 - 90)
        ri = r if i%2==0 else r*0.4
        pts.extend([x + ri*math.cos(a), y + ri*math.sin(a)])
    canvas.create_polygon(pts, fill=color, outline='', tags=('dog',))


# ── 3-D Roaming Yorkie (simple but charming) ──────────────────────────────────
def draw_yorkie_3d(canvas, cx, cy, walk_phase, scale=0.75):
    """Isometric-ish 3-D Yorkie walking on taskbar."""
    s = scale
    tags = ('dog',)

    # shadow
    canvas.create_oval(cx-25*s, cy+32*s, cx+25*s, cy+38*s,
                       fill='#00000044', outline='', tags=tags)

    # body — box perspective
    bw, bh, bd = 40*s, 24*s, 22*s
    # isometric body
    body_pts = [
        cx-bw/2, cy,          # left-front-top
        cx+bw/2, cy,          # right-front-top
        cx+bw/2+10*s, cy-8*s, # right-back-top
        cx-bw/2+10*s, cy-8*s, # left-back-top
    ]
    # sides
    canvas.create_polygon(
        cx-bw/2, cy, cx+bw/2, cy,
        cx+bw/2, cy+bh, cx-bw/2, cy+bh,
        fill=TAN, outline=DARK_BR, width=1, tags=tags)
    canvas.create_polygon(
        cx+bw/2, cy, cx+bw/2+10*s, cy-8*s,
        cx+bw/2+10*s, cy-8*s+bh, cx+bw/2, cy+bh,
        fill=DARK_BR, outline=DARK_BR, width=1, tags=tags)
    canvas.create_polygon(
        cx-bw/2, cy, cx+bw/2, cy,
        cx+bw/2+10*s, cy-8*s, cx-bw/2+10*s, cy-8*s,
        fill='#8B6914', outline=DARK_BR, width=1, tags=tags)

    # animated legs
    for i, lx_off in enumerate([-15*s, -5*s, 5*s, 15*s]):
        phase_off = (i % 2) * math.pi
        leg_swing = math.sin(walk_phase + phase_off) * 6*s
        lx = cx + lx_off
        ly_top = cy + bh
        canvas.create_line(lx, ly_top, lx + leg_swing*0.3, ly_top+16*s+leg_swing,
                           fill=STEEL, width=max(2, 5*s),
                           capstyle=tk.ROUND, tags=tags)
        oval(canvas, lx+leg_swing*0.3, ly_top+18*s+leg_swing, 4*s, 2.5*s,
             fill=DARK_BR, outline='', tags=tags)

    # head (3D-ish sphere suggestion)
    hx = cx - bw*0.35
    hy = cy - 10*s
    # head shadow side
    oval(canvas, hx+5*s, hy+3*s, 18*s, 17*s, fill='#2A1C0A', outline='', tags=tags)
    oval(canvas, hx, hy, 18*s, 17*s, fill=DARK_BR, outline='', tags=tags)
    oval(canvas, hx-3*s, hy-5*s, 14*s, 12*s, fill=TAN, outline='', tags=tags)
    # muzzle
    oval(canvas, hx-2*s, hy+5*s, 9*s, 7*s, fill=TAN, outline='', tags=tags)
    oval(canvas, hx-2*s, hy+3*s, 4*s, 3*s, fill=NOSE_C, outline='', tags=tags)
    # eye
    oval(canvas, hx-8*s, hy-2*s, 4*s, 4*s, fill=EYE_C, outline='', tags=tags)
    oval(canvas, hx-9.5*s, hy-3.5*s, 1.5*s, 1.5*s, fill='white', outline='', tags=tags)
    # ear
    canvas.create_polygon(
        hx-12*s, hy-8*s,
        hx-22*s, hy-22*s,
        hx-6*s,  hy+4*s,
        fill=DARK_BR, outline='', smooth=True, tags=tags)

    # tail
    tx = cx + bw/2 + 8*s
    ty = cy + 4*s
    tail_wag = math.sin(walk_phase * 2.5) * 15
    for seg in range(4):
        a = math.radians(-30 + tail_wag + seg*20)
        canvas.create_line(tx+seg*4*s, ty, tx+(seg+1)*4*s + math.cos(a)*6*s,
                           ty - math.sin(a)*8*s,
                           fill=DARK_BR, width=max(2, (4-seg)*2*s),
                           capstyle=tk.ROUND, tags=tags)


# ── Main Application ──────────────────────────────────────────────────────────
class YorkiePet:
    WIN_W = 200
    WIN_H = 240
    ROAM_W = 160
    ROAM_H = 100

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🐾 Yorkie Pet")
        self.root.overrideredirect(True)          # no title bar
        self.root.attributes('-topmost', True)    # always on top
        self.root.attributes('-alpha', 0.98)
        self.root.configure(bg=BG_TRANS)

        # Platform transparency
        try:
            self.root.attributes('-transparentcolor', BG_TRANS)
        except Exception:
            pass

        # State
        self.click_count   = 0
        self.mood          = 'idle'   # idle | happy | sleepy | hungry
        self.blink         = False
        self.tongue_out    = False
        self.tail_angle    = 60
        self.tail_dir      = 1
        self.roam_mode     = False
        self.walk_phase    = 0.0
        self.roam_x        = 100
        self.roam_dir      = 1
        self.show_bark_txt = False
        self.bark_timer    = 0
        self.last_activity = time.time()
        self.hunger        = 100      # 0-100
        self.hunger_timer  = 0
        self._drag_x       = 0
        self._drag_y       = 0
        self._woof_cooldown = 0

        # Position window bottom-right ish
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}+{sw-220}+{sh-300}")

        # Canvas
        self.canvas = tk.Canvas(self.root,
                                width=self.WIN_W, height=self.WIN_H,
                                bg=BG_TRANS, highlightthickness=0)
        self.canvas.pack()

        # Bindings
        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<ButtonPress-3>', self._show_menu)
        self.canvas.bind('<ButtonPress-1>', self._drag_start)
        self.canvas.bind('<B1-Motion>',    self._drag_motion)
        self.root.bind_all('<KeyPress>', self._on_keypress)

        # Right-click menu
        self.menu = tk.Menu(self.root, tearoff=0,
                            bg=PANEL_BG, fg=COUNTER_FG,
                            activebackground='#4A3018', activeforeground='white',
                            font=('Segoe UI', 10))
        self.menu.add_command(label='🚀 Toggle Roam Mode', command=self._toggle_roam)
        self.menu.add_command(label='🍖 Feed Yorkie',      command=self._feed)
        self.menu.add_command(label='🔄 Reset Counter',    command=self._reset_counter)
        self.menu.add_separator()
        self.menu.add_command(label='❌ Close',            command=self.root.destroy)

        # Start loops
        self._animate()
        self.root.mainloop()

    # ── Input handlers ────────────────────────────────────────────────────────
    def _on_click(self, event):
        self.click_count += 1
        self.last_activity = time.time()
        self.mood = 'happy'
        self.tongue_out = True
        self._woof_cooldown = 3   # skip a few frames before next allowed woof
        play_woof()
        self.show_bark_txt = True
        self.bark_timer = 18

    def _on_keypress(self, event):
        self.click_count += 1
        self.last_activity = time.time()
        if self.mood == 'sleepy':
            self.mood = 'idle'

    def _drag_start(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event):
        if not self.roam_mode:
            nx = event.x_root - self._drag_x
            ny = event.y_root - self._drag_y
            self.root.geometry(f'+{nx}+{ny}')

    def _show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    # ── Commands ──────────────────────────────────────────────────────────────
    def _toggle_roam(self):
        self.roam_mode = not self.roam_mode
        if self.roam_mode:
            sh = self.root.winfo_screenheight()
            self.roam_x = 100
            # place on taskbar area
            self.root.geometry(f"{self.ROAM_W}x{self.ROAM_H}+100+{sh-80}")
        else:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self.root.geometry(f"{self.WIN_W}x{self.WIN_H}+{sw-220}+{sh-300}")

    def _feed(self):
        self.hunger = 100
        self.mood = 'happy'
        self.last_activity = time.time()
        play_woof()

    def _reset_counter(self):
        self.click_count = 0

    # ── Animation loop ────────────────────────────────────────────────────────
    def _animate(self):
        self._frame = getattr(self, '_frame', 0) + 1
        f = self._frame

        # Mood logic
        idle_secs = time.time() - self.last_activity
        if idle_secs > 30:
            self.mood = 'sleepy'
        elif idle_secs > 10 and self.mood == 'happy':
            self.mood = 'idle'

        # Hunger decay
        self.hunger_timer += 1
        if self.hunger_timer > 300:
            self.hunger_timer = 0
            self.hunger = max(0, self.hunger - 5)
        if self.hunger < 20:
            self.mood = 'hungry'

        # Blink every ~120 frames
        self.blink = (f % 120 < 4) or (f % 120 in range(7, 10))

        # Tongue
        if self.mood != 'happy':
            self.tongue_out = False

        # Tail wag
        self.tail_angle += self.tail_dir * 4
        if self.tail_angle > 90 or self.tail_angle < 30:
            self.tail_dir *= -1

        # Random woof (quiet background bark)
        if random.random() < 0.002 and self.mood != 'sleepy':
            play_woof()
            self.show_bark_txt = True
            self.bark_timer = 15

        # Bark text timer
        if self.bark_timer > 0:
            self.bark_timer -= 1
        else:
            self.show_bark_txt = False

        # Roam
        if self.roam_mode:
            self.walk_phase += 0.12
            self.roam_x += self.roam_dir * 2.2
            sw = self.root.winfo_screenwidth()
            if self.roam_x > sw - 80 or self.roam_x < 20:
                self.roam_dir *= -1
            sh = self.root.winfo_screenheight()
            self.root.geometry(f"{self.ROAM_W}x{self.ROAM_H}+{int(self.roam_x)}+{sh-80}")

        self._draw()
        self.root.after(33, self._animate)   # ~30 fps

    def _draw(self):
        c = self.canvas
        c.delete('all')

        if self.roam_mode:
            self._draw_roam(c)
        else:
            self._draw_2d(c)

    def _draw_2d(self, c):
        W, H = self.WIN_W, self.WIN_H
        DOG_CY = 108

        # Panel background (rounded card)
        roundrect(c, 4, 4, W-4, H-4, r=22,
                  fill=PANEL_BG, outline='#5A3A1A', width=2)

        # Title
        c.create_text(W//2, 18, text='🐾 Yorkie Pet', fill=TAN,
                      font=('Segoe UI', 10, 'bold'))

        # Hunger bar
        bar_x, bar_y, bar_w, bar_h = 18, 32, W-36, 8
        c.create_rectangle(bar_x, bar_y, bar_x+bar_w, bar_y+bar_h,
                           fill='#1A0E05', outline='#5A3A1A', width=1)
        col = '#6FCF6F' if self.hunger > 50 else ('#F2A73B' if self.hunger > 20 else '#EB5757')
        c.create_rectangle(bar_x, bar_y,
                           bar_x + int(bar_w * self.hunger/100), bar_y+bar_h,
                           fill=col, outline='')
        c.create_text(bar_x, bar_y-1, text='🍖', anchor='se',
                      font=('Segoe UI', 7))

        # Mood label
        mood_icons = {'idle':'😊', 'happy':'🥰', 'sleepy':'😴', 'hungry':'😋'}
        c.create_text(W-14, 36, text=mood_icons.get(self.mood,'😊'),
                      font=('Segoe UI', 12), anchor='e')

        # Yorkie
        draw_yorkie_2d(c, W//2 + 14, DOG_CY, scale=1.15,
                       mood=self.mood,
                       tail_angle=self.tail_angle,
                       blink=self.blink,
                       tongue_out=self.tongue_out)

        # WOOF bubble
        if self.show_bark_txt:
            bx, by = W//2 + 70, DOG_CY - 50
            roundrect(c, bx-28, by-14, bx+28, by+14, r=10,
                      fill='white', outline='#DDD', width=1)
            c.create_text(bx, by, text='Woof!', fill='#333',
                          font=('Segoe UI', 9, 'bold'))
            # pointer
            c.create_polygon(bx-10, by+12, bx-6, by+22, bx+2, by+12,
                             fill='white', outline='')

        # Counter panel
        panel_y = H - 52
        roundrect(c, 16, panel_y, W-16, H-10, r=14,
                  fill='#1A0E05', outline='#8B5E1A', width=2)
        c.create_text(W//2, panel_y+10, text='ACTIVITY COUNT',
                      fill='#8B5E1A', font=('Segoe UI', 7, 'bold'))
        c.create_text(W//2, panel_y+28, text=f'{self.click_count:,}',
                      fill=COUNTER_FG, font=('Segoe UI Semibold', 17, 'bold'))

        # Tip text
        c.create_text(W//2, H-4, text='click me • right-click for options',
                      fill='#5A3A1A', font=('Segoe UI', 6), anchor='s')

    def _draw_roam(self, c):
        W, H = self.ROAM_W, self.ROAM_H
        cx, cy = W//2, H//2 - 8

        # Transparent bg — just draw the dog
        draw_yorkie_3d(c, cx, cy, self.walk_phase, scale=0.82)

        # Counter badge
        c.create_oval(W-36, 4, W-4, 30, fill='#1A0E05', outline=COUNTER_FG, width=2)
        c.create_text(W-20, 17, text=str(self.click_count),
                      fill=COUNTER_FG, font=('Segoe UI', 8, 'bold'))

        if self.show_bark_txt:
            c.create_text(cx, 10, text='Woof! 🐾', fill=COUNTER_FG,
                          font=('Segoe UI', 9, 'bold'))


if __name__ == '__main__':
    YorkiePet()
