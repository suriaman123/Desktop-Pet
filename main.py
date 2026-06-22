"""
Desktop Pet V8

"""

import tkinter as tk
import math, random, time, threading, os, sys, shutil

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

# ── Sound paths ───────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
SND_WOOF1   = os.path.join(_HERE, "woof.mp3")
SND_WOOF2   = os.path.join(_HERE, "woof2.mp3")
SND_THIRSTY = os.path.join(_HERE, "thirsty.mp3")

def play_sound(path):
    """Play an mp3 on Windows (winsound only does wav, so try pygame/playsound/start)."""
    if not os.path.exists(path):
        return
    def _do():
        try:
            # Try pygame first (best cross-platform)
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
                return
            except Exception:
                pass
            # Windows fallback: os.startfile plays in default app (silent background)
            import subprocess
            subprocess.Popen(['powershell','-c',f'(New-Object Media.SoundPlayer).Play()'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Final fallback: Windows Media Player via cmd
            os.system(f'start /min wmplayer "{path}" 2>nul')
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()

def play_woof():
    play_sound(random.choice([SND_WOOF1, SND_WOOF2]))

def play_thirsty():
    play_sound(SND_THIRSTY)

# If pygame not available, try to install it silently
def _ensure_pygame():
    try:
        import pygame
    except ImportError:
        try:
            os.system("pip install pygame --break-system-packages -q")
        except Exception:
            pass
threading.Thread(target=_ensure_pygame, daemon=True).start()


# ── Palette — matched to real Yorkie photos ───────────────────────────────────
GOLD_FACE  = (195, 150,  80, 255)
GOLD_EAR   = (210, 170, 100, 255)
GOLD_LIGHT = (230, 195, 130, 255)
DARK_BODY  = ( 45,  38,  42, 255)
DARK_MED   = ( 75,  62,  55, 255)
STEEL_BODY = ( 60,  55,  65, 255)
FUR_DARK   = ( 55,  42,  25, 255)
NOSE_C     = ( 25,  18,  10, 255)
EYE_C      = ( 12,   8,   4, 255)
WHITE      = (255, 255, 255, 255)
TONGUE_C   = (230, 100,  90, 255)
PINK       = (255, 107, 157, 255)
PINK_D     = (200,  50, 100, 255)

CHROMA = "#010101"
GOLD   = "#FFD166"
PANEL  = "#1E1206"


# ── Sprite drawing ─────────────────────────────────────────────────────────────
def ov(d, cx, cy, rx, ry, **kw):
    d.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], **kw)

def draw_yorkie(mood='idle', frame=0, total=8, scale=1.0, facing='right'):
    W, H = int(200*scale), int(170*scale)
    img  = Image.new('RGBA', (W, H), (0,0,0,0))
    d    = ImageDraw.Draw(img)
    s    = scale

    t      = (frame/total)*2*math.pi
    bob    = math.sin(t)*1.6*s
    tail_w = math.sin(t*1.5)*28
    walk   = (mood == 'walk')
    sleepy = (mood == 'sleepy')
    happy  = (mood == 'happy')
    blink  = (frame in (0,1)) and not sleepy

    bx  = int(W*0.50)
    by  = int(H*0.56) + int(bob)
    flr = by + int(42*s)

    # ── TAIL ─────────────────────────────────────────────────────────────────
    tx, ty = bx+int(48*s), by-int(8*s)
    p = (tx, ty)
    for i in range(6):
        a  = math.radians(55 + tail_w - i*12)
        nx = int(p[0] + math.cos(a)*8*s)
        ny = int(p[1] - math.sin(a)*8*s)
        w  = max(1, int((9-i)*s*0.7))
        col = GOLD_FACE if i > 1 else DARK_BODY
        d.line([p,(nx,ny)], fill=col, width=w)
        ov(d,nx,ny,w,w,fill=GOLD_EAR if i>2 else col)
        p = (nx, ny)

    # ── BACK LEGS ────────────────────────────────────────────────────────────
    for off, ph in [(int(15*s),0),(int(30*s),math.pi)]:
        lx = bx+off
        sw = math.sin(t+ph)*7*s if walk else 0
        ov(d,lx,by+int(22*s),int(8*s),int(14*s),fill=DARK_MED)
        d.line([(lx,by+int(30*s)),(int(lx+sw),flr-int(2*s))],
               fill=DARK_BODY,width=max(2,int(8*s)))
        ov(d,int(lx+sw),flr,int(8*s),int(4*s),fill=FUR_DARK)

    # ── BODY ─────────────────────────────────────────────────────────────────
    ov(d,bx,by,int(48*s),int(30*s),fill=DARK_BODY)
    ov(d,bx-int(5*s),by-int(8*s),int(30*s),int(8*s),fill=STEEL_BODY)
    # Long silky fur drape lines
    for fx in range(-38,42,4):
        ov(d,bx+int(fx*s),by+int(18*s),int(1*s),int(12*s),
           fill=(40,35,38,100))
    # Golden chest
    ov(d,bx-int(36*s),by,int(14*s),int(18*s),fill=GOLD_FACE)

    # ── FRONT LEGS ───────────────────────────────────────────────────────────
    for off, ph in [(-int(26*s),math.pi),(-int(11*s),0)]:
        lx = bx+off
        sw = math.sin(t+ph)*7*s if walk else 0
        ov(d,lx,by+int(20*s),int(7*s),int(10*s),fill=DARK_MED)
        d.line([(lx,by+int(27*s)),(int(lx+sw),flr-int(2*s))],
               fill=DARK_BODY,width=max(2,int(7*s)))
        # tan lower leg
        d.line([(lx,by+int(32*s)),(int(lx+sw*0.6),flr-int(5*s))],
               fill=GOLD_FACE,width=max(1,int(3*s)))
        ov(d,int(lx+sw),flr,int(7*s),int(4*s),fill=FUR_DARK)

    # ── HEAD ─────────────────────────────────────────────────────────────────
    hx = bx - int(44*s)
    hy = by  - int(18*s)

    # Left ear
    d.polygon([(hx-int(12*s),hy-int(8*s)),(hx-int(4*s),hy-int(40*s)),
               (hx+int(8*s),hy-int(38*s)),(hx+int(10*s),hy-int(6*s))],fill=DARK_BODY)
    d.polygon([(hx-int(9*s),hy-int(9*s)),(hx-int(2*s),hy-int(33*s)),
               (hx+int(6*s),hy-int(31*s)),(hx+int(7*s),hy-int(7*s))],fill=GOLD_FACE)
    ov(d,hx+int(2*s),hy-int(39*s),int(5*s),int(5*s),fill=GOLD_LIGHT)

    # Right ear
    d.polygon([(hx+int(10*s),hy-int(6*s)),(hx+int(14*s),hy-int(36*s)),
               (hx+int(22*s),hy-int(30*s)),(hx+int(18*s),hy+int(4*s))],fill=DARK_BODY)
    d.polygon([(hx+int(11*s),hy-int(6*s)),(hx+int(15*s),hy-int(30*s)),
               (hx+int(20*s),hy-int(26*s)),(hx+int(17*s),hy+int(3*s))],fill=DARK_MED)

    # Skull
    ov(d,hx,hy,int(22*s),int(20*s),fill=DARK_BODY)

    # Golden face fur (the defining Yorkie look)
    ov(d,hx-int(1*s),hy-int(2*s),int(18*s),int(16*s),fill=GOLD_FACE)
    ov(d,hx,hy+int(2*s),int(12*s),int(11*s),fill=GOLD_EAR)
    ov(d,hx,hy-int(10*s),int(13*s),int(9*s),fill=GOLD_FACE)
    ov(d,hx-int(12*s),hy+int(6*s),int(9*s),int(8*s),fill=GOLD_FACE)
    ov(d,hx+int(10*s),hy+int(5*s),int(8*s),int(7*s),fill=GOLD_FACE)
    # Face fur wisps
    for a_deg in range(0,360,35):
        a  = math.radians(a_deg)
        sx = hx + math.cos(a)*int(14*s)
        sy = hy + math.sin(a)*int(12*s)
        ex = hx + math.cos(a)*int(20*s)
        ey = hy + math.sin(a)*int(18*s)
        d.line([(int(sx),int(sy)),(int(ex),int(ey))],fill=GOLD_EAR,
               width=max(1,int(1.5*s)))

    # Muzzle + beard
    ov(d,hx+int(3*s),hy+int(9*s),int(10*s),int(8*s),fill=GOLD_EAR)
    ov(d,hx+int(3*s),hy+int(19*s),int(7*s),int(6*s),fill=GOLD_LIGHT)

    # Eyes
    for ex_off,ey_off in [(-int(8*s),-int(4*s)),(int(7*s),-int(5*s))]:
        ex_ = hx+ex_off; ey_ = hy+ey_off
        if blink or sleepy:
            d.arc([ex_-int(5*s),ey_,ex_+int(5*s),ey_+int(5*s)],
                  180,360,fill=EYE_C,width=max(1,int(2*s)))
        else:
            ov(d,ex_,ey_,int(5*s),int(5*s),fill=EYE_C)
            ov(d,ex_-int(2*s),ey_-int(2*s),int(2*s),int(2*s),fill=WHITE)
            ov(d,ex_,ey_,int(3*s),int(3*s),fill=(50,30,10,180))

    # Nose
    ov(d,hx+int(3*s),hy+int(5*s),int(5*s),int(4*s),fill=NOSE_C)
    ov(d,hx+int(1*s),hy+int(4*s),int(1.5*s),int(1*s),fill=(80,60,50,160))

    # Mouth
    d.arc([hx-int(2*s),hy+int(8*s),hx+int(8*s),hy+int(15*s)],
          10,170,fill=DARK_BODY,width=max(1,int(1*s)))

    # Tongue
    if happy:
        ov(d,hx+int(3*s),hy+int(15*s),int(5*s),int(7*s),fill=TONGUE_C)
        d.line([(hx+int(3*s),hy+int(13*s)),(hx+int(3*s),hy+int(20*s))],
               fill=(200,70,70,180),width=max(1,int(1*s)))

    # Whiskers
    for side in (-1,1):
        for wy_off in (5,9):
            d.line([(hx+int(3*s)+side*int(8*s),hy+int(wy_off*s)),
                    (hx+int(3*s)+side*int(20*s),hy+int((wy_off+1)*s))],
                   fill=(200,180,150,110),width=max(1,int(1*s)))

    # Top-knot + bow
    bwx,bwy = hx-int(1*s), hy-int(28*s)
    for i in range(5):
        a = math.radians(-90+i*18-36)
        d.line([(bwx,bwy+int(5*s)),
                (int(bwx+math.cos(a)*10*s),int(bwy+math.sin(a)*10*s))],
               fill=GOLD_FACE,width=max(1,int(2*s)))
    ov(d,bwx-int(7*s),bwy,int(7*s),int(5*s),fill=PINK)
    ov(d,bwx+int(7*s),bwy,int(7*s),int(5*s),fill=PINK)
    ov(d,bwx,bwy,int(3*s),int(3*s),fill=PINK_D)

    img = img.filter(ImageFilter.SMOOTH_MORE)

    if facing == 'left':
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

    return img


def build_cache(scale):
    specs = [('idle',8),('happy',8),('sleepy',8),('hungry',8),('walk',10)]
    cache = {'right': {}, 'left': {}}
    for mood, nf in specs:
        cache['right'][mood] = [
            ImageTk.PhotoImage(draw_yorkie(mood,i,nf,scale,'right')) for i in range(nf)]
        cache['left'][mood]  = [
            ImageTk.PhotoImage(draw_yorkie(mood,i,nf,scale,'left'))  for i in range(nf)]
    return cache


# ── Tk rounded rect ───────────────────────────────────────────────────────────
def rr(c, x1,y1,x2,y2, r=14, **kw):
    pts=[x1+r,y1,x2-r,y1,x2,y1+r,x2,y2-r,x2-r,y2,x1+r,y2,x1,y2-r,x1,y1+r]
    return c.create_polygon(pts, smooth=True, **kw)


# ── Main App ──────────────────────────────────────────────────────────────────
class DesktopPet:
    WIN_W  = 190
    WIN_H  = 220
    ROAM_W = 180
    ROAM_H = 152

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Desktop Pet")
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
        self.roam_dir     = 1           # +1 = right, -1 = left
        self.roam_facing  = 'right'
        self.last_active  = time.time()
        self.hunger       = 100
        self.hunger_tick  = 0
        self.happy_timer  = 0
        self.bark_timer   = 0
        self.always_on_top = True
        self._dx = self._dy = self._wx = self._wy = 0

        # Start position
        wx = self.sw - self.WIN_W - 20
        wy = self.sh - self.WIN_H - 60
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}+{wx}+{wy}")

        # Canvas
        self.cv = tk.Canvas(self.root, width=self.WIN_W, height=self.WIN_H,
                             bg=CHROMA, highlightthickness=0)
        self.cv.pack()

        # Sprites
        self.sprites_2d   = build_cache(scale=1.0)
        self.sprites_roam = build_cache(scale=0.82)
        self.sprites      = self.sprites_2d

        # Bindings
        self.cv.bind('<Button-1>',      self._click)
        self.cv.bind('<Button-3>',      self._menu_show)
        self.cv.bind('<ButtonPress-1>', self._drag_start)
        self.cv.bind('<B1-Motion>',     self._drag)

        # Menu
        self.menu = tk.Menu(self.root, tearoff=0, bg='#2B1D0E', fg=GOLD,
                            activebackground='#4A3018', activeforeground='white',
                            font=('Segoe UI', 10))
        self.menu.add_command(label='🚶 Toggle Roam Mode',     command=self._toggle_roam)
        self.menu.add_command(label='🍖 Feed Yorkie',           command=self._feed)
        self.menu.add_command(label='📌 Toggle Always on Top',  command=self._toggle_topmost)
        self.menu.add_command(label='🔄 Reset Counter',         command=self._reset)
        self.menu.add_separator()
        self.menu.add_command(label='❌ Quit',                  command=self.root.destroy)

        self._setup_hooks()
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
            pmouse.Listener(on_click=on_click, daemon=True).start()
            pkeyboard.Listener(on_press=on_key, daemon=True).start()
        except Exception:
            pass

    def _input_event(self):
        self.count += 1
        self.last_active = time.time()
        if self.mood == 'sleepy':
            self.mood = 'idle'

    # ── Bindings ─────────────────────────────────────────────────────────────
    def _click(self, e):
        if not self.roam_mode and e.y < self.WIN_H - 58:
            play_woof()
            self.happy_timer = 50
            self.bark_timer  = 24

    def _drag_start(self, e):
        self._dx,self._dy = e.x_root,e.y_root
        self._wx,self._wy = self.root.winfo_x(),self.root.winfo_y()

    def _drag(self, e):
        if not self.roam_mode:
            self.root.geometry(
                f"+{self._wx+e.x_root-self._dx}+{self._wy+e.y_root-self._dy}")

    def _menu_show(self, e):
        # Update topmost label dynamically
        label = '📌 Always on Top: ON' if self.always_on_top else '📌 Always on Top: OFF'
        self.menu.entryconfigure(2, label=label)
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
        self.hunger = 100
        self.happy_timer = 55
        self.bark_timer  = 18
        self.last_active = time.time()
        play_woof()

    def _toggle_topmost(self):
        self.always_on_top = not self.always_on_top
        self.root.attributes('-topmost', self.always_on_top)

    def _reset(self):
        self.count = 0

    # ── Tick ─────────────────────────────────────────────────────────────────
    def _tick(self):
        # ── Mood ─────────────────────────────────────────────────────────────
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

        # ── Hunger ───────────────────────────────────────────────────────────
        self.hunger_tick += 1
        if self.hunger_tick >= 350:
            self.hunger_tick = 0
            prev = self.hunger
            self.hunger = max(0, self.hunger - 5)
            # Play thirsty sound when hunger first drops low
            if prev >= 20 and self.hunger < 20:
                play_thirsty()

        # ── Bark timer ───────────────────────────────────────────────────────
        if self.bark_timer > 0:
            self.bark_timer -= 1

        # Random bark
        if random.random() < 0.003 and self.mood != 'sleepy':
            play_woof()
            self.bark_timer = 18

        # ── Roam ─────────────────────────────────────────────────────────────
        if self.roam_mode:
            speed = 2.5
            self.roam_x += self.roam_dir * speed

            if self.roam_x >= self.sw - self.ROAM_W - 4:
                self.roam_dir    = -1
                self.roam_facing = 'left'
            elif self.roam_x <= 4:
                self.roam_dir    = 1
                self.roam_facing = 'right'

            self.root.geometry(
                f"{self.ROAM_W}x{self.ROAM_H}"
                f"+{int(self.roam_x)}+{self.sh-self.ROAM_H-2}")

        # ── Sprite frame ─────────────────────────────────────────────────────
        facing = self.roam_facing if self.roam_mode else 'right'
        sp = self.sprites[facing].get(self.mood, self.sprites[facing]['idle'])
        self.frame_idx = (self.frame_idx + 1) % len(sp)

        self._draw()
        self.root.after(90, self._tick)

    # ── Draw ─────────────────────────────────────────────────────────────────
    def _draw(self):
        self.cv.delete('all')
        if self.roam_mode:
            self._draw_roam()
        else:
            self._draw_2d()

    def _draw_2d(self):
        c = self.cv
        W, H = self.WIN_W, self.WIN_H
        c.create_rectangle(0,0,W,H,fill=CHROMA,outline='')
        rr(c,6,6,W-6,H-6,r=22,fill=PANEL,outline='#5A3A1A',width=2)

        # Title
        c.create_text(W//2,20,text='🐾  Desktop Pet  🐾',
                      fill=GOLD,font=('Segoe UI',9,'bold'))

        # Hunger bar
        bx,by,bw,bh = 20,34,W-40,9
        c.create_rectangle(bx,by,bx+bw,by+bh,fill='#0E0804',outline='#5A3A1A')
        hw = int(bw*self.hunger/100)
        hcol = '#5EBD6F' if self.hunger>50 else ('#F2A73B' if self.hunger>25 else '#EB5757')
        if hw>0:
            c.create_rectangle(bx,by,bx+hw,by+bh,fill=hcol,outline='')
        c.create_text(bx-2,by+4,text='🍖',anchor='e',font=('Segoe UI',7))

        # Mood icon
        icons={'idle':'😊','happy':'🥰','sleepy':'😴','hungry':'😋','walk':'🐕'}
        c.create_text(W-10,by+4,text=icons.get(self.mood,'😊'),
                      font=('Segoe UI',13),anchor='e')

        # Pin indicator
        if not self.always_on_top:
            c.create_text(W//2,H-62,text='📌 off',fill='#6A4010',
                          font=('Segoe UI',7))

        # Dog
        sp = self.sprites['right'].get(self.mood,self.sprites['right']['idle'])
        c.create_image(W//2+14,125,image=sp[self.frame_idx],anchor='center')

        # Woof bubble
        if self.bark_timer > 0:
            bub_x,bub_y = W-32,72
            rr(c,bub_x-30,bub_y-15,bub_x+30,bub_y+15,r=10,
               fill='white',outline='#CCC',width=1)
            c.create_text(bub_x,bub_y,text='Woof! 🐾',
                          fill='#333',font=('Segoe UI',9,'bold'))
            c.create_polygon(bub_x-8,bub_y+13,bub_x-4,bub_y+23,bub_x+4,bub_y+13,
                             fill='white',outline='')

        # Counter
        py = H-58
        rr(c,14,py,W-14,H-8,r=15,fill='#0E0804',outline='#8B5E1A',width=2)
        c.create_text(W//2,py+12,text='A C T I V I T Y',
                      fill='#6A4010',font=('Segoe UI',6,'bold'))
        c.create_text(W//2,py+33,text=f'{self.count:,}',
                      fill=GOLD,font=('Segoe UI Semibold',19,'bold'))

        c.create_text(W//2,H-1,text='click dog = woof  •  right-click = menu',
                      fill='#3A2008',font=('Segoe UI',6),anchor='s')

    def _draw_roam(self):
        c = self.cv
        W, H = self.ROAM_W, self.ROAM_H
        c.create_rectangle(0,0,W,H,fill=CHROMA,outline='')

        facing = self.roam_facing
        sp = self.sprites[facing].get(self.mood,self.sprites[facing]['walk'])
        c.create_image(W//2+6,H//2+8,image=sp[self.frame_idx],anchor='center')

        # Counter badge
        c.create_oval(W-44,4,W-4,30,fill='#1E1206',outline=GOLD,width=2)
        c.create_text(W-24,17,text=str(self.count),
                      fill=GOLD,font=('Segoe UI',8,'bold'))

        if self.bark_timer > 0:
            c.create_text(W//2,12,text='Woof! 🐾',
                          fill=GOLD,font=('Segoe UI',9,'bold'))


if __name__ == '__main__':
    DesktopPet()
