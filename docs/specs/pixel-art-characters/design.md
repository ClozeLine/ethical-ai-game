# Design: Pixel Art Characters

## Architecture Overview

The current draw pipeline is:

    Person.draw() → rect fill → screen
    → scanlines → vignette → noise → timestamp → display.flip()

After this feature the pipeline becomes:

    Person.draw() → blit pre-baked composite surface → screen
    → scanlines → vignette → noise → timestamp → display.flip()

Nothing in the outer pipeline changes. All new complexity is encapsulated in `entities/sprites.py`
(sprite data + builder) and minor changes to `entities/person.py` (build frames, animate).

---

## Sprite Canvas Design

### Dimensions

    Native:  10 x 17 pixels
    Display: 30 x 51 pixels (3x integer scale, nearest-neighbor)

The 10x17 native canvas breaks down as:

    Row  0       : top of hat (if present) — transparent on no-hat variant
    Rows 1–2     : hat brim / hair
    Rows 3–4     : head (skin)
    Row  5       : neck (skin) + collar
    Rows 6–10    : torso / shirt
    Rows 11–13   : legs / pants
    Rows 14–16   : feet / shoes

This is a deliberate "chunky humanoid" proportioning optimized for CCTV silhouette readability at
small sizes. Exact pixel layout is defined in `entities/sprites.py`.

---

## Signal Color System

Five signal colors are reserved as placeholders in the raw pixel arrays. These colors are chosen
to be vivid, mutually distinct, and not used in the game's CCTV color palette:

    SKIN_SIGNAL   = "#FF00FF"   (magenta)
    HAIR_SIGNAL   = "#00FFFF"   (cyan)
    SHIRT_SIGNAL  = "#FF8000"   (orange)
    PANTS_SIGNAL  = "#8000FF"   (violet)
    SHOES_SIGNAL  = "#00FF80"   (spring green)
    HAT_SIGNAL    = "#FF0080"   (hot pink)
    TRANSPARENT   = None  (or a dedicated BG sentinel like "#010101")

At build time, `SpriteBuilder` scans each pixel of the 2D array and replaces signal colors with
the character's actual colors. The result is a `pygame.Surface` with SRCALPHA; background pixels
are set transparent.

### Why This Over Palette Swapping (8-bit Surfaces)

pygame-ce surfaces default to 32-bit RGBA. Palette-based swapping requires converting to 8-bit,
which interacts badly with SRCALPHA transparency and requires careful palette management.
Signal-color replacement via PixelArray or direct pixel-by-pixel construction at build time avoids
this entirely and is done only once per person — the per-frame cost is zero.

### Build-Time Replacement Strategy

Construct the surface using `pygame.Surface((10, 17), pygame.SRCALPHA)` then iterate the 2D pixel
array and call `surface.set_at((x, y), actual_color)` for each pixel. At 10x17 = 170 pixels this
loop runs in negligible time even in pure Python. Then upscale once with `pygame.transform.scale`.

Two scaled surfaces are built: one for `WALK_FRAME_A` and one for `WALK_FRAME_B`.

---

## Sprite Data Format

Sprites are defined as Python lists of lists of strings. Each string is either a hex color code
(`"#FF00FF"`) or `None` for transparent. Example (schematic):

```python
# entities/sprites.py  (schematic — not actual pixel data)

WALK_FRAME_A = [
    [None, None, "#FF00FF", "#FF00FF", None, None, ...],  # row 0 (head top)
    ...
    [None, "#8000FF", "#8000FF", "#8000FF", None, ...],   # row 12 (pants)
    ...
]

WALK_FRAME_B = [
    # identical to WALK_FRAME_A except rows 11-16 (legs/feet)
    ...
]

HAT_LAYER = [
    ["#FF0080", "#FF0080", "#FF0080", ...],  # row 0
    ...
    [None, None, None, ...],  # rows below hat brim = transparent
]
```

This format is:
- Human-readable and hand-editable
- No binary files, no asset pipeline
- Copyable into a GitHub comment or diff
- Fully reproducible from source alone

---

## SpriteBuilder API

File: `entities/sprites.py`

```python
# Type signatures only — no implementation

def build_frame(
    pixel_array: list[list[str | None]],
    color_map: dict[str, tuple[int, int, int]],
    hat_layer: list[list[str | None]] | None,
    hat_color: tuple[int, int, int] | None,
    flip_h: bool = False,
) -> pygame.Surface:
    """
    Construct a 30x51 pygame.Surface (3x upscale of 10x17) by replacing
    signal colors in pixel_array with values from color_map, then optionally
    blitting hat_layer on top, then scaling 3x.

    color_map keys: "skin", "hair", "shirt", "pants", "shoes"
    Pixels with None are transparent (SRCALPHA).
    flip_h: produce a horizontally mirrored copy for left-facing walk.
    Returns a ready-to-blit surface; the original pixel arrays are not modified.
    """
```

The builder is a pure function (stateless). Person stores the baked outputs.

---

## Person Changes

### New fields on Person.__init__

```python
self._frames: list[list[pygame.Surface]]
# _frames[0] = [frame_A_right, frame_A_left]  (right = normal, left = flipped)
# _frames[1] = [frame_B_right, frame_B_left]
self._frame_idx: int = 0
self._anim_dist: float = 0.0
```

### New method: build_sprite(self)

Called alongside `build_card()` in `Game.__init__`. Derives colors from `self.attributes` via
`CLOTHING_COLOR_MAP`, calls `build_frame` twice (once for each walk frame, both orientations),
stores results in `_frames`.

### Updated: update(self, dt)

After updating `self.x`, accumulate:

```python
self._anim_dist += abs(self.vx * dt * 60)
if self._anim_dist >= SPRITE_ANIM_STRIDE:
    self._anim_dist -= SPRITE_ANIM_STRIDE
    self._frame_idx = 1 - self._frame_idx
```

### Updated: draw(self, surface)

```python
facing = 0 if self.vx >= 0 else 1
surface.blit(self._frames[self._frame_idx][facing], self.rect)
```

---

## Color Assignment from Attributes

### CLOTHING_COLOR_MAP (in constants.py)

Maps a keyword found in the `clothing` field to `(shirt_rgb, pants_rgb)`:

```python
CLOTHING_COLOR_MAP = {
    "hoodie":    ((60, 60, 60),    (40, 40, 50)),
    "jacket":    ((180, 40, 40),   (50, 50, 70)),
    "parka":     ((50, 140, 60),   (50, 60, 50)),
    "raincoat":  ((200, 180, 40),  (50, 70, 80)),
    "vest":      ((140, 60, 160),  (40, 40, 60)),
    "scarf":     ((180, 90, 30),   (60, 60, 60)),    # scarf = prominent shirt color
    "tracksuit": ((60, 180, 180),  (50, 150, 150)),
    "blouse":    ((190, 190, 190), (70, 70, 90)),
}
```

Matching is case-insensitive substring search against the `clothing` value. If no match, falls
back to a default `(120, 120, 120), (60, 60, 60)`.

### Skin and Hair Pools

```python
SKIN_TONES = [
    (220, 180, 140),  # light
    (190, 140, 100),  # medium-light
    (160, 110, 70),   # medium
    (110, 75, 45),    # medium-dark
    (70, 45, 25),     # dark
]

HAIR_COLORS = [
    (30, 20, 10),     # near-black
    (80, 50, 20),     # dark brown
    (160, 110, 50),   # auburn
    (200, 160, 80),   # blonde
    (180, 180, 180),  # gray
]
```

Selection: `hash(person_name) % len(pool)` — deterministic, no state needed.

### Hat Assignment

```python
has_hat = (hash(person_name) >> 3) % 2 == 0   # ~50% of population
hat_color = HAT_COLORS[hash(person_name) % len(HAT_COLORS)]
```

```python
HAT_COLORS = [
    (30, 30, 30),    # black
    (100, 60, 30),   # brown
    (50, 80, 120),   # navy
    (140, 30, 30),   # burgundy
]
```

---

## Animation Design: 2 Walk Frames

Frame A (neutral):

    Both feet side by side, body upright.
    This is also the standing/idle pose.

Frame B (stride):

    Right leg slightly forward and down, left leg slightly back and up.
    Left arm slightly forward (counterpose to right leg).

At 60fps and `SPRITE_ANIM_STRIDE = 12.0`:
- A person moving at `vx = 1.0` (normal speed, 60px/s) toggles frames every ~0.2s — approximately
  5 toggles per second, giving a 2.5 Hz stride cycle. This reads as "walking briskly."
- A person at `vx = 2.0` (fast) toggles every ~0.1s — 5 Hz, reads as "hurrying."
- A person at `vx = 0.5` (slow) toggles every ~0.4s — 2.5 Hz, reads as "strolling."

This is the correct perceptual behavior: faster walkers animate faster.

---

## New File Layout

```
entities/
    person.py        (modified: build_sprite, updated update/draw)
    sprites.py       (NEW: pixel arrays, SpriteBuilder, signal color constants)
game/
    constants.py     (modified: CLOTHING_COLOR_MAP, skin/hair/hat pools,
                      SPRITE_ANIM_STRIDE, update PERSON_HEIGHT to 51)
```

No new directories. No PNG files. No asset loader needed.

---

## Key Design Decisions

### Decision 1: Python 2D list arrays instead of PNG files

**Chosen:** Define sprites as `list[list[str | None]]` in Python source.

**Alternatives considered:**
- External PNG files loaded at runtime via `pygame.image.load()`
- Base64-encoded PNG strings embedded in source
- PIL/Pillow generated at startup from array data, then converted to pygame surface

**Rationale:** Python lists are the only approach where the "art" is fully readable, diffable, and
editable without any tools. For a 10x17 = 170-pixel sprite, the list is about 30 lines of code. A
building agent (or human) can edit individual pixels by changing a string in a list. No Pillow
dependency needed. No binary file in git. The CCTV aesthetic forgives imperfect pixel art.

**Risk:** Editing the raw 2D array is harder than drawing in a pixel editor. Mitigation: the
arrays are small enough that a tabular layout is readable, and a building agent can generate the
initial design programmatically before storing it as a literal.

---

### Decision 2: Signal-color replacement over 8-bit palette surfaces

**Chosen:** Build 32-bit SRCALPHA surfaces; replace signal colors at pixel construction time.

**Alternatives considered:**
- `pygame.Surface.set_palette_at()` on 8-bit surfaces
- `pygame.PixelArray` replace() with threshold matching
- Multiple pre-tinted PNG files

**Rationale:** 8-bit palettes require converting surfaces to P mode and interact poorly with
SRCALPHA, which is needed for character transparency. PixelArray.replace() works but requires a
separate copy per color-swap, and the threshold matching adds unpredictability. Direct construction
from the pixel array is the most transparent (no pun intended) approach and runs once at build
time.

**Risk:** None for this scale. 170 pixels × 2 frames × 2 orientations = 680 set_at() calls at
startup. Imperceptible.

---

### Decision 3: Distance-gated animation rather than time-gated

**Chosen:** Accumulate travel distance; toggle frame when distance threshold crossed.

**Alternatives considered:**
- Fixed time interval (e.g., toggle every 200ms regardless of speed)
- Frame counter (toggle every N game frames)

**Rationale:** Distance-gating is the only approach where the visual animation speed correctly
reflects the character's movement speed. A fast person should visibly hustle; a slow person should
amble. Time-gated animation at a fixed interval would make slow people look like they are
ice-skating (feet moving fast, body barely progressing). Frame-counter gating has the same
problem and also makes animation speed framerate-dependent.

---

### Decision 4: No Pillow dependency

**Chosen:** All sprite operations use only pygame-ce (already a dependency).

**Alternatives:** Use PIL/Pillow for image construction, convert to pygame Surface via
`pygame.image.fromstring()`.

**Rationale:** Adding Pillow adds a dependency with no benefit at this scale. pygame-ce already
provides all the surface construction and pixel manipulation primitives needed. Keeping the
dependency count minimal is especially important for a student/academic project.

---

## Security / Compatibility Notes

- `pygame.transform.scale` (not `smoothscale`) preserves pixel art crispness. This is the correct
  function for nearest-neighbor upscaling in pygame-ce.
- The `pygame.SRCALPHA` flag on the sprite surface means transparent pixels will not overdraw the
  background. This is required — without it the 30x51 bounding box would show a black rectangle
  obscuring the CCTV background.
- `PERSON_HEIGHT` change from 50 to 51: the rect is used for collision/hover-card positioning
  only. A 1px increase has no visual impact on cards or overlays.
