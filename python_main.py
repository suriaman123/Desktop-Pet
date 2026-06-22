"""
Desktop Pet V5

"""

import tkinter as tk
import math, random, time, threading, struct, wave, io, os, sys

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageTk
except ImportError:
    os.system("pip install pillow --break-system-packages -q")
    from PIL import Image, ImageDraw, ImageFilter, ImageTk

try:
    from pynput import mouse as pmouse, keyboard as pkeyboard
    PYNPUT_OK = True
except ImportError:
    os.system("pip install pynput --break-system-packages -q")
    try:
        from pynput import mouse as pmouse, keyboard as pkeyboard
        PYNPUT_OK = True
    except Exception:
        PYNPUT_OK = False

# ── Palette ───────────────────────────────────────────────────────────────────
TAN     = (200, 164, 110, 255)
TAN_L   = (228, 196, 145, 255)
DARK    = (59,   42,  26, 255)
DARK_M  = (90,   65,  35, 255)
STEEL   = (107, 140, 174, 255)
STEEL_D = (70,  100, 140, 255)
NOSE    = (26,   16,   8, 255)
EYE_C   = (15,    8,   2, 255)
WHITE   = (255, 255, 255, 255)
TONGUE  = (232, 112, 112, 255)
PINK    = (255, 107, 157, 255)
PINK_D  = (210,  50, 110, 255)

CHROMA  = "#010101"   # transparency key
GOLD    = "#FFD166"
PANEL   = "#1E1206"

# ── Sound ─────────────────────────────────────────────────────────────────────
def _make_woof():
    sr = 22050
    clips = []
    for freq, dur, vol in [(400, 0.10, 0.65), (260, 0.16, 0.50)]:
        n = int(sr * dur)
        buf = bytearray()
        for i in range(n):
            t2 = i / sr
            v = (math.sin(2*math.pi*freq*t2)
                 + 0.5*math.sin(2*math.pi*freq*2.1*t2)
                 + 0.15*math.sin(2*math.pi*freq*0.5*t2)) / 1.65
            env = min(1.0, i/(sr*0.008)) * max(0.0, 1-(i/(n*0.5)))**1.8
            val = max(-32767, min(32767, int(v*env*vol*32767)))
            buf += struct.pack('<h', val)
        clips.append(bytes(buf))
    bio = io.BytesIO()
    with wave.open(bio,'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(clips[0]+clips[1])
    return bio.getvalue()

WOOF_WAV = _make_woof()

def play_woof():
    def _do():
        try:
            import winsound, tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
                f.write(WOOF_WAV); fname = f.name
            winsound.PlaySound(fname, winsound.SND_FILENAME | winsound.SND_ASYNC)
            threading.Timer(1.5, lambda: os.unlink(fname) if os.path.exists(fname) else None).start()
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()

# ── Sprite drawing ─────────────────────────────────────────────────────────────
def ov(d, cx, cy, rx, ry, **kw):
    d.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], **kw)

def draw_yorkie(mood='idle', frame=0, total=8, scale=1.0):
    """Return PIL RGBA image of Yorkie for this frame."""
    W, H = int(180*scale), int(162*scale)
    img = Image.new('RGBA', (W, H), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    s   = scale

    t       = (frame/total) * 2*math.pi
    bob     = math.sin(t) * 1.8 * s
    tail_w  = math.sin(t*1.6) * 26            # tail wag degrees
    walk    = (mood == 'walk')
    sleepy  = (mood == 'sleepy')
    happy   = (mood == 'happy')
    blink   = frame in (0,1) and not sleepy

    cx = int(W * 0.52)
    cy = int(H * 0.52) + int(bob)
    floor_y = cy + int(40*s)

    # ── Shadow ────────────────────────────────────────────────────────────────
    ov(d, cx, int(H*0.93), int(40*s), int(5*s), fill=(0,0,0,45))

    # ── Tail (golden, curves upward) ──────────────────────────────────────────
    tx, ty = cx + int(44*s), cy - int(4*s)
    p = (tx, ty)
    for i in range(7):
        a  = math.radians(75 + tail_w - i*13)
        nx = int(p[0] + math.cos(a)*7*s)
        ny = int(p[1] - math.sin(a)*7*s)
        w  = max(1, int((8-i)*s*0.75))
        d.line([p,(nx,ny)], fill=TAN if i>1 else DARK, width=w)
        ov(d, nx, ny, w, w, fill=TAN if i>1 else DARK)
        p = (nx, ny)

    # ── Back legs ────────────────────────────────────────────────────────────
    for off, ph in [(int(14*s), 0), (int(28*s), math.pi)]:
        lx = cx + off
        sw = math.sin(t+ph)*6*s if walk else 0
        ov(d, lx, cy+int(22*s), int(7*s), int(12*s), fill=TAN)
        d.line([(lx, cy+int(30*s)),(int(lx+sw), floor_y)], fill=TAN_L, width=max(2,int(7*s)))
        ov(d, int(lx+sw), floor_y, int(8*s), int(4*s), fill=DARK)

    # ── Body ─────────────────────────────────────────────────────────────────
    bx, by = cx, cy
    ov(d, bx, by,          int(44*s), int(28*s), fill=DARK)    # dark saddle
    ov(d, bx-int(6*s), by+int(5*s), int(34*s), int(21*s), fill=TAN)  # golden belly
    ov(d, bx-int(34*s), by-int(2*s), int(14*s), int(16*s), fill=TAN_L)  # chest

    # ── Front legs ───────────────────────────────────────────────────────────
    for off, ph in [(-int(24*s), math.pi), (-int(10*s), 0)]:
        lx = cx + off
        sw = math.sin(t+ph)*6*s if walk else 0
        ov(d, lx, cy+int(20*s), int(6*s), int(10*s), fill=TAN)
        d.line([(lx, cy+int(27*s)),(int(lx+sw), floor_y)], fill=STEEL_D, width=max(2,int(6*s)))
        ov(d, int(lx+sw), floor_y, int(7*s), int(4*s), fill=DARK)

    # ── Head ─────────────────────────────────────────────────────────────────
    hx = bx - int(40*s)
    hy = by  - int(16*s)

    # Left (near) ear — large floppy Yorkie ear
    d.polygon([
        (hx-int(14*s), hy-int(8*s)),
        (hx-int(7*s),  hy-int(34*s)),
        (hx+int(4*s),  hy-int(30*s)),
        (hx+int(7*s),  hy-int(6*s)),
    ], fill=DARK)
    d.polygon([
        (hx-int(11*s), hy-int(8*s)),
        (hx-int(5*s),  hy-int(28*s)),
        (hx+int(3*s),  hy-int(25*s)),
        (hx+int(5*s),  hy-int(6*s)),
    ], fill=TAN)

    # Right (far) ear
    d.polygon([
        (hx+int(8*s),  hy-int(6*s)),
        (hx+int(16*s), hy-int(28*s)),
        (hx+int(20*s), hy-int(22*s)),
        (hx+int(14*s), hy+int(4*s)),
    ], fill=DARK)

    # Skull
    ov(d, hx, hy, int(20*s), int(19*s), fill=DARK)
    # Golden forehead fur
    ov(d, hx-int(1*s), hy-int(8*s), int(14*s), int(10*s), fill=TAN_L)
    # Cheek fur
    ov(d, hx-int(8*s), hy+int(5*s), int(10*s), int(9*s), fill=TAN_L)
    ov(d, hx+int(6*s), hy+int(4*s), int(9*s),  int(8*s), fill=TAN_L)
    # Muzzle
    ov(d, hx, hy+int(8*s), int(10*s), int(8*s), fill=TAN)
    # Beard (classic Yorkie fall)
    ov(d, hx, hy+int(17*s), int(7*s), int(6*s), fill=TAN_L)

    # Eyes
    for ex_off in [-int(8*s), int(6*s)]:
        ex_ = hx + ex_off
        ey_ = hy - int(3*s)
        if blink or sleepy:
            d.arc([ex_-int(5*s), ey_-int(2*s), ex_+int(5*s), ey_+int(4*s)],
                  180, 360, fill=EYE_C, width=max(1,int(2*s)))
        else:
            ov(d, ex_, ey_, int(5*s), int(5*s), fill=EYE_C)
            ov(d, ex_-int(2*s), ey_-int(2*s), int(1.5*s), int(1.5*s), fill=WHITE)

    # Nose
    ov(d, hx, hy+int(4*s), int(5*s), int(4*s), fill=NOSE)
    ov(d, hx-int(2*s), hy+int(3*s), int(1*s), int(1*s), fill=(80,55,40,180))

    # Mouth
    d.arc([hx-int(4*s), hy+int(7*s), hx+int(4*s), hy+int(14*s)],
          10, 170, fill=NOSE, width=max(1,int(1*s)))

    # Tongue (happy)
    if happy:
        ov(d, hx, hy+int(14*s), int(5*s), int(6*s), fill=TONGUE)
        d.line([(hx,hy+int(13*s)),(hx,hy+int(19*s))], fill=(200,80,80,180), width=max(1,int(1*s)))

    # Whiskers
    for side in (-1, 1):
        for wy_off in (5, 9):
            d.line([(hx+side*int(8*s), hy+int(wy_off*s)),
                    (hx+side*int(18*s), hy+int((wy_off+1)*s))],
                   fill=(180,160,130,140), width=max(1,int(1*s)))

    # ── Top-knot bow 🎀 ───────────────────────────────────────────────────────
    bwx = hx - int(2*s)
    bwy = hy - int(29*s)
    ov(d, bwx-int(7*s), bwy, int(7*s), int(5*s), fill=PINK)
    ov(d, bwx+int(7*s), bwy, int(7*s), int(5*s), fill=PINK)
    ov(d, bwx, bwy, int(3*s), int(3*s), fill=PINK_D)

    # Soften
    if scale >= 1.0:
        img = img.filter(ImageFilter.SMOOTH)
    return img


def build_cache(scale):
    specs = [('idle',8),('happy',8),('sleepy',8),('hungry',8),('walk',10)]
    cache = {}
    for mood, nf in specs:
        cache[mood] = [ImageTk.PhotoImage(draw_yorkie(mood, i, nf, scale))
                       for i in range(nf)]
    return cache


# ── Tk helpers ────────────────────────────────────────────────────────────────
def rr(c, x1, y1, x2, y2, r=14, **kw):
    pts = [x1+r,y1,x2-r,y1,x2,y1+r,x2,y2-r,x2-r,y2,x1+r,y2,x1,y2-r,x1,y1+r]
    return c.create_polygon(pts, smooth=True, **kw)


# ── App ───────────────────────────────────────────────────────────────────────
class YorkiePet:
    WIN_W  = 190
    WIN_H  = 220
    ROAM_W = 175
    ROAM_H = 148

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Yorkie Pet")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg=CHROMA)
        try:
            self.root.attributes('-transparentcolor', CHROMA)
        except Exception:
            pass

        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()

        # State
        self.count        = 0
        self.mood         = 'idle'
        self.frame_idx    = 0
        self.roam_mode    = False
        self.roam_x       = 100.0
        self.roam_dir     = 1
        self.last_active  = time.time()
        self.hunger       = 100
        self.hunger_tick  = 0
        self.happy_timer  = 0
        self.bark_timer   = 0
        self._dx = self._dy = self._wx = self._wy = 0

        # Position: bottom-right
        wx = self.sw - self.WIN_W - 20
        wy = self.sh - self.WIN_H - 60
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}+{wx}+{wy}")

        # Canvas
        self.cv = tk.Canvas(self.root, width=self.WIN_W, height=self.WIN_H,
                             bg=CHROMA, highlightthickness=0)
        self.cv.pack()

        # Build sprite caches
        self.sprites_2d   = build_cache(scale=1.05)
        self.sprites_roam = build_cache(scale=0.85)
        self.sprites      = self.sprites_2d

        # Bindings
        self.cv.bind('<Button-1>',      self._click)
        self.cv.bind('<Button-3>',      self._menu_show)
        self.cv.bind('<ButtonPress-1>', self._drag_start)
        self.cv.bind('<B1-Motion>',     self._drag)

        # Right-click menu
        self.menu = tk.Menu(self.root, tearoff=0, bg='#2B1D0E', fg=GOLD,
                            activebackground='#4A3018', activeforeground='white',
                            font=('Segoe UI', 10))
        self.menu.add_command(label='🚶 Toggle Roam Mode', command=self._toggle_roam)
        self.menu.add_command(label='🍖 Feed Yorkie',      command=self._feed)
        self.menu.add_command(label='🔄 Reset Counter',    command=self._reset)
        self.menu.add_separator()
        self.menu.add_command(label='❌ Quit',             command=self.root.destroy)

        # Global input hooks
        self._setup_hooks()

        # Start
        self._tick()
        self.root.mainloop()

    # ── Global hooks ─────────────────────────────────────────────────────────
    def _setup_hooks(self):
        if not PYNPUT_OK:
            return
        def on_click(x, y, btn, pressed):
            if pressed: self._input_event()
        def on_key(key):
            self._input_event()
        try:
            ml = pmouse.Listener(on_click=on_click, daemon=True); ml.start()
            kl = pkeyboard.Listener(on_press=on_key, daemon=True); kl.start()
        except Exception:
            pass

    def _input_event(self):
        self.count += 1
        self.last_active = time.time()
        if self.mood == 'sleepy':
            self.mood = 'idle'

    # ── Bindings ─────────────────────────────────────────────────────────────
    def _click(self, e):
        if e.y < self.WIN_H - 58:   # dog area, not counter
            play_woof()
            self.happy_timer = 50
            self.bark_timer  = 24

    def _drag_start(self, e):
        self._dx, self._dy = e.x_root, e.y_root
        self._wx, self._wy = self.root.winfo_x(), self.root.winfo_y()

    def _drag(self, e):
        if not self.roam_mode:
            self.root.geometry(f"+{self._wx+e.x_root-self._dx}+{self._wy+e.y_root-self._dy}")

    def _menu_show(self, e):
        self.menu.post(e.x_root, e.y_root)

    # ── Commands ─────────────────────────────────────────────────────────────
    def _toggle_roam(self):
        self.roam_mode = not self.roam_mode
        if self.roam_mode:
            self.sprites = self.sprites_roam
            self.roam_x  = float(max(5, self.root.winfo_x()))
            self.root.geometry(
                f"{self.ROAM_W}x{self.ROAM_H}+{int(self.roam_x)}+{self.sh-self.ROAM_H-2}")
        else:
            self.sprites = self.sprites_2d
            wx = self.sw - self.WIN_W - 20
            wy = self.sh - self.WIN_H - 60
            self.root.geometry(f"{self.WIN_W}x{self.WIN_H}+{wx}+{wy}")
            self.mood = 'idle'

    def _feed(self):
        self.hunger = 100; self.happy_timer = 55; self.bark_timer = 18
        self.last_active = time.time(); play_woof()

    def _reset(self):
        self.count = 0

    # ── Tick ─────────────────────────────────────────────────────────────────
    def _tick(self):
        # Mood
        if self.happy_timer > 0:
            self.happy_timer -= 1
            self.mood = 'happy'
        elif self.roam_mode:
            self.mood = 'walk'
        else:
            idle = time.time() - self.last_active
            if self.hunger < 20:
                self.mood = 'hungry'
            elif idle > 28:
                self.mood = 'sleepy'
            elif idle > 10 and self.mood == 'happy':
                self.mood = 'idle'

        # Hunger drain
        self.hunger_tick += 1
        if self.hunger_tick >= 350:
            self.hunger_tick = 0
            self.hunger = max(0, self.hunger-5)

        # Bark timer
        if self.bark_timer > 0:
            self.bark_timer -= 1

        # Random bark
        if random.random() < 0.003 and self.mood != 'sleepy':
            play_woof(); self.bark_timer = 18

        # Roam movement
        if self.roam_mode:
            speed = 2.8
            self.roam_x += self.roam_dir * speed
            if self.roam_x >= self.sw - self.ROAM_W - 4:
                self.roam_dir = -1
            elif self.roam_x <= 4:
                self.roam_dir = 1
            self.root.geometry(
                f"{self.ROAM_W}x{self.ROAM_H}+{int(self.roam_x)}+{self.sh-self.ROAM_H-2}")

        # Advance sprite
        sp = self.sprites.get(self.mood, self.sprites['idle'])
        self.frame_idx = (self.frame_idx+1) % len(sp)

        self._draw()
        self.root.after(90, self._tick)

    # ── Draw ─────────────────────────────────────────────────────────────────
    def _draw(self):
        c = self.cv; c.delete('all')
        if self.roam_mode:
            self._draw_roam(c)
        else:
            self._draw_2d(c)

    def _draw_2d(self, c):
        W, H = self.WIN_W, self.WIN_H
        c.create_rectangle(0,0,W,H, fill=CHROMA, outline='')
        rr(c, 6,6, W-6,H-6, r=22, fill=PANEL, outline='#5A3A1A', width=2)

        # Title
        c.create_text(W//2, 20, text='🐾  Yorkie Desktop Pet  🐾',
                      fill=GOLD, font=('Segoe UI', 9, 'bold'))

        # Hunger bar
        bx,by,bw,bh = 20, 34, W-40, 9
        c.create_rectangle(bx,by,bx+bw,by+bh, fill='#0E0804', outline='#5A3A1A')
        hw = int(bw*self.hunger/100)
        hcol = '#5EBD6F' if self.hunger>50 else ('#F2A73B' if self.hunger>25 else '#EB5757')
        if hw>0:
            c.create_rectangle(bx,by,bx+hw,by+bh, fill=hcol, outline='')
        c.create_text(bx-2, by+4, text='🍖', anchor='e', font=('Segoe UI',7))
        mood_icon = {'idle':'😊','happy':'🥰','sleepy':'😴','hungry':'😋','walk':'🐕'}
        c.create_text(W-10, by+4, text=mood_icon.get(self.mood,'😊'),
                      font=('Segoe UI',13), anchor='e')

        # Dog sprite
        sp = self.sprites.get(self.mood, self.sprites['idle'])
        img = sp[self.frame_idx]
        c.create_image(W//2+14, 125, image=img, anchor='center')

        # Woof bubble
        if self.bark_timer > 0:
            bub_x, bub_y = W-32, 72
            rr(c, bub_x-30,bub_y-15, bub_x+30,bub_y+15, r=10,
               fill='white', outline='#CCC', width=1)
            c.create_text(bub_x, bub_y, text='Woof! 🐾',
                          fill='#333', font=('Segoe UI',9,'bold'))
            c.create_polygon(bub_x-8,bub_y+13, bub_x-4,bub_y+23, bub_x+4,bub_y+13,
                             fill='white', outline='')

        # Counter panel
        py = H-58
        rr(c, 14,py, W-14,H-8, r=15, fill='#0E0804', outline='#8B5E1A', width=2)
        c.create_text(W//2, py+12, text='A C T I V I T Y   C O U N T',
                      fill='#6A4010', font=('Segoe UI',6,'bold'))
        c.create_text(W//2, py+33, text=f'{self.count:,}',
                      fill=GOLD, font=('Segoe UI Semibold',19,'bold'))

        c.create_text(W//2, H-1,
                      text='click dog = woof  •  right-click = menu',
                      fill='#3A2008', font=('Segoe UI',6), anchor='s')

    def _draw_roam(self, c):
        W, H = self.ROAM_W, self.ROAM_H
        c.create_rectangle(0,0,W,H, fill=CHROMA, outline='')
        sp = self.sprites.get(self.mood, self.sprites['walk'])
        c.create_image(W//2+8, H//2+6, image=sp[self.frame_idx], anchor='center')
        # Counter badge
        c.create_oval(W-44,4, W-4,30, fill='#1E1206', outline=GOLD, width=2)
        c.create_text(W-24, 17, text=str(self.count),
                      fill=GOLD, font=('Segoe UI',8,'bold'))
        if self.bark_timer>0:
            c.create_text(W//2, 12, text='Woof! 🐾',
                          fill=GOLD, font=('Segoe UI',9,'bold'))


if __name__ == '__main__':
    YorkiePet()
