# Implementation Tasks: Pixel Art Characters

## Task Overview

- **Total tasks:** 5
- **Estimated complexity:** Medium
- **Suggested approach:** Sequential — each task depends on the previous

## Dependency Graph

    T1 → T2 → T3 → T4 → T5

## Tasks

---

### T1: Define sprite pixel arrays and SpriteBuilder

**File:** `entities/sprites.py` (new file)

**Description:**

Create the new module with:

1. Signal color constants as module-level strings:
   ```
   SKIN_SIGNAL, HAIR_SIGNAL, SHIRT_SIGNAL, PANTS_SIGNAL, SHOES_SIGNAL, HAT_SIGNAL
   ```

2. Two walk frame arrays: `WALK_FRAME_A` and `WALK_FRAME_B`.
   Both are `list[list[str | None]]` of shape `[17][10]` (17 rows, 10 columns).
   Frame B differs from Frame A only in rows 11–16 (legs and feet). Suggested
   approach for generating the initial arrays: write a small script or use a
   building agent to generate a valid 10x17 human silhouette, print it as a
   Python literal, then paste it in. The pixel layout described in `design.md`
   (head rows 3–4, torso rows 6–10, legs rows 11–13, feet rows 14–16) is the
   target.

3. An optional `HAT_LAYER` array of the same shape with hat pixels using
   `HAT_SIGNAL` and `None` everywhere else.

4. A `build_frame` function with this exact signature:
   ```python
   def build_frame(
       pixel_array: list[list[str | None]],
       color_map: dict[str, tuple[int, int, int]],
       hat_layer: list[list[str | None]] | None,
       hat_color: tuple[int, int, int] | None,
       flip_h: bool = False,
   ) -> pygame.Surface:
   ```
   Implementation steps inside `build_frame`:
   - Build signal-to-actual mapping from `color_map` and optional `hat_color`
   - Create `pygame.Surface((10, 17), pygame.SRCALPHA)`
   - Iterate rows and columns; for each pixel:
     - If `None`: skip (leave transparent)
     - If signal color key: call `surface.set_at((col, row), actual_color)`
   - If `hat_layer` is not None and `hat_color` is not None:
     - Repeat pixel iteration for `hat_layer`
   - Upscale with `pygame.transform.scale(surface, (30, 51))`
   - If `flip_h`: return `pygame.transform.flip(result, True, False)`
   - Return result

**Depends on:** None

**Completion criteria:**
- [ ] `entities/sprites.py` exists and is importable.
- [ ] `WALK_FRAME_A` and `WALK_FRAME_B` are defined, shape `[17][10]`.
- [ ] `HAT_LAYER` is defined, same shape.
- [ ] `build_frame` accepts the specified signature and returns a `pygame.Surface`
      of size `(30, 51)`.
- [ ] Calling `build_frame` with all signal colors mapped produces a surface with
      no pixel equal to any signal color.
- [ ] Transparent pixels in the input produce fully transparent pixels in the output
      (alpha == 0).
- [ ] `flip_h=True` produces a horizontally mirrored surface.

**Complexity:** Medium (the pixel array content requires art judgment; the builder
logic is straightforward)

**Notes:**
- The 10x17 grid at 3x is 30x51. Verify `pygame.transform.scale` preserves pixel
  crispness (it uses nearest-neighbor by default — do NOT use `smoothscale`).
- The hat layer is blitted on top of the base after the base is constructed on the
  same native surface, before the 3x upscale. This ensures hat pixels scale
  consistently with body pixels.
- A simple visual sanity check: call `build_frame` in a standalone script, save the
  output via `pygame.image.save()`, and open it to inspect the result before
  proceeding to T2.

---

### T2: Add clothing color data to constants.py

**File:** `game/constants.py`

**Description:**

Add the following constants. Do not remove or modify any existing constants.

1. `CLOTHING_COLOR_MAP: dict[str, tuple[tuple, tuple]]` — maps clothing keyword
   to `(shirt_rgb, pants_rgb)`. Keys (lowercase): `"hoodie"`, `"jacket"`,
   `"parka"`, `"raincoat"`, `"vest"`, `"scarf"`, `"tracksuit"`, `"blouse"`.
   Values: visible, CCTV-appropriate RGB tuples (avoid values below 40 in all
   channels, which disappear under the vignette at screen edges).

2. `SKIN_TONES: list[tuple]` — 5 entries (see design.md).

3. `HAIR_COLORS: list[tuple]` — 5 entries (see design.md).

4. `HAT_COLORS: list[tuple]` — 4 entries (see design.md).

5. `SPRITE_ANIM_STRIDE: float = 12.0` — distance in pixels of travel before
   toggling walk frame.

6. Update `PERSON_HEIGHT = 51` (was 50). Add a comment explaining the change.

**Depends on:** T1 (concepts only; no code dependency yet)

**Completion criteria:**
- [ ] All six items above are present in `constants.py`.
- [ ] `PERSON_HEIGHT` is 51.
- [ ] `CLOTHING_COLOR_MAP` has exactly 8 keys matching the clothing keywords in
      `PERSON_TEMPLATE_DATA`.
- [ ] All color tuples have 3 integer components in range 0–255.
- [ ] No existing constants are removed or renamed.

**Complexity:** Low

**Notes:**
- The existing `PERSON_COLORS` list can remain but will no longer be used for
  drawing once T4 is complete. Leave it in place for now to avoid breaking the
  current `Game.__init__` pairing logic until T4 handles that.

---

### T3: Add build_sprite to Person

**File:** `entities/person.py`

**Description:**

Add sprite building and animation state to the `Person` class.

1. Add new imports at the top of the file:
   ```python
   from entities.sprites import build_frame, WALK_FRAME_A, WALK_FRAME_B, HAT_LAYER
   from game.constants import (
       # existing imports ...
       CLOTHING_COLOR_MAP,
       SKIN_TONES,
       HAIR_COLORS,
       HAT_COLORS,
       SPRITE_ANIM_STRIDE,
   )
   ```

2. Add to `Person.__init__`:
   ```python
   self._frames: list[list[pygame.Surface]] = []  # built by build_sprite()
   self._frame_idx: int = 0
   self._anim_dist: float = 0.0
   ```

3. Add new method `build_sprite(self) -> None`:
   - Determine `shirt_color, pants_color` by searching `CLOTHING_COLOR_MAP` for a
     substring match against `self.attributes.get("clothing", "").lower()`.
     Fall back to `(120, 120, 120), (60, 60, 60)` if no match.
   - Determine `skin_color` = `SKIN_TONES[hash(name) % len(SKIN_TONES)]`
     where `name = self.attributes.get("name", "")`.
   - Determine `hair_color` = `HAIR_COLORS[(hash(name) >> 2) % len(HAIR_COLORS)]`.
   - Determine `has_hat` = `(hash(name) >> 3) % 2 == 0`.
   - Determine `hat_color` = `HAT_COLORS[hash(name) % len(HAT_COLORS)]` if
     `has_hat` else `None`.
   - Build `color_map`:
     ```python
     color_map = {
         "skin": skin_color,
         "hair": hair_color,
         "shirt": shirt_color,
         "pants": pants_color,
         "shoes": (50, 50, 50),
     }
     ```
   - For each frame array `[WALK_FRAME_A, WALK_FRAME_B]`:
     - Build right-facing: `build_frame(arr, color_map, HAT_LAYER if has_hat else None, hat_color, flip_h=False)`
     - Build left-facing: `build_frame(arr, color_map, HAT_LAYER if has_hat else None, hat_color, flip_h=True)`
     - Append `[right, left]` to `self._frames`.

4. Update `update(self, dt)` to accumulate animation distance after the existing
   position update:
   ```python
   self._anim_dist += abs(self.vx * dt * 60)
   if self._anim_dist >= SPRITE_ANIM_STRIDE:
       self._anim_dist -= SPRITE_ANIM_STRIDE
       self._frame_idx = 1 - self._frame_idx
   ```

5. Update `draw(self, surface)`:
   - If `self._frames` is populated:
     ```python
     facing = 0 if self.vx >= 0 else 1
     surface.blit(self._frames[self._frame_idx][facing], self.rect)
     ```
   - Else: fall back to the existing `pygame.draw.rect` (keeps the game runnable
     if `build_sprite` was not called).

**Depends on:** T1, T2

**Completion criteria:**
- [ ] `Person.build_sprite()` exists and populates `self._frames` with a 2x2 list
      of `pygame.Surface` objects.
- [ ] `self._frames[0]` = `[frame_A_right, frame_A_left]`
- [ ] `self._frames[1]` = `[frame_B_right, frame_B_left]`
- [ ] `update()` accumulates `_anim_dist` and toggles `_frame_idx` at the stride
      threshold.
- [ ] `draw()` blits from `_frames` when available, falls back to rect otherwise.
- [ ] The fallback rect draw is preserved exactly as it currently exists.

**Complexity:** Low-Medium

**Notes:**
- `hash()` in Python is not stable across interpreter invocations by default
  (PYTHONHASHSEED). For deterministic results, either set `PYTHONHASHSEED=0` in
  the run environment or use a stable hash like `sum(ord(c) for c in name)`. The
  simpler stable alternative: `stable_hash = lambda s: sum(ord(c) * i for i, c in enumerate(s, 1))`.
  Use this instead of `hash()` to guarantee the same skin/hair/hat across runs.

---

### T4: Wire build_sprite into Game.__init__

**File:** `game/game_loop.py`

**Description:**

Call `build_sprite()` for each person in `Game.__init__`, alongside the existing
`build_card()` call.

Current code:
```python
for person in self.people:
    person.build_card(self.card_font)
```

Change to:
```python
for person in self.people:
    person.build_sprite()
    person.build_card(self.card_font)
```

No other changes to `game_loop.py` are needed.

**Depends on:** T3

**Completion criteria:**
- [ ] `build_sprite()` is called for every person before the game loop starts.
- [ ] `build_card()` is still called for every person.
- [ ] The game runs without error.
- [ ] Characters appear as pixel art sprites (not colored rectangles) on the CCTV
      screen.
- [ ] Characters visually animate between two frames as they walk.
- [ ] Left-moving characters display a horizontally mirrored sprite.

**Complexity:** Low

---

### T5: Visual tuning and verification

**Files:** `entities/sprites.py`, `game/constants.py`

**Description:**

Run the game and verify all visual requirements are met. Make adjustments to pixel
arrays and color values as needed. This is the only task that may require iterative
changes.

Checks to perform:
1. All 6 (or 8) characters are visually distinct from each other.
2. No character uses colors that are invisible against the dark background under
   the CCTV overlays (scan the screen center and edges).
3. Walk animation is perceptibly different between a slow person (vx ~0.5) and a
   fast person (vx ~2.0).
4. Hats appear on approximately half the characters.
5. Clothing colors on-screen roughly match the clothing description in the info
   card (e.g., the person with "Red jacket" wears a reddish shirt layer).
6. Left-facing and right-facing sprites look like mirror images (no artifacts).
7. Sprites are crisp/pixelated, not blurry (confirms nearest-neighbor scaling).

If any pixel colors are too dark or too similar, adjust the relevant entries in
`CLOTHING_COLOR_MAP`, `SKIN_TONES`, `HAIR_COLORS`, or `HAT_COLORS` in
`constants.py`.

If any sprite pixel rows look wrong (e.g., hat appears in wrong place, legs are
missing), edit the relevant rows in `WALK_FRAME_A`, `WALK_FRAME_B`, or `HAT_LAYER`
in `entities/sprites.py`.

**Depends on:** T4

**Completion criteria:**
- [ ] All functional requirements FR-1 through FR-6 are met.
- [ ] Game runs at full 60fps with no performance regression.
- [ ] Characters are visually readable through scanlines and vignette overlay.
- [ ] Walk animation visually conveys locomotion speed differences.
- [ ] PERSON_HEIGHT in constants.py is 51 and person.rect size matches.

**Complexity:** Low (if T1–T4 are correct) to Medium (if pixel art needs rework)

**Notes:**
- If the pixel art silhouette in T1 is clearly wrong (unrecognizable as a human),
  go back and revise the 2D arrays before proceeding. The simplest human at 10x17:
  a 4x4 head, 2x6 torso, 2 leg columns of 3 rows each, 2 foot columns of 2 rows.
  Shoulders at 6 wide. Total filled pixels ~40 out of 170; it should look sparse
  but humanoid.

---

## Verification Plan

After all tasks are complete, verify the full feature end-to-end:

- [ ] Launch the game with `uv run python main.py`.
- [ ] Confirm no import errors or AttributeErrors on startup.
- [ ] Confirm all persons are rendered as pixel art characters (no colored rects).
- [ ] Hover over each character and confirm the info card clothing description
      visually matches the shirt/pants color on the sprite.
- [ ] Watch for 30 seconds: confirm animation cycles are visible and match
      movement speed.
- [ ] Confirm characters wrap around the screen edge correctly (sprite appears at
      opposite edge, no clipping artifacts).
- [ ] Confirm CCTV overlays (scanlines, vignette, noise) apply on top of sprites.
- [ ] Open `entities/sprites.py` and confirm no PNG files were created or required.
