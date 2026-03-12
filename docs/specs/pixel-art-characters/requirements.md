# Requirements: Pixel Art Characters

## Overview

Replace the solid-color rectangles that currently represent people with small, chunky pixel art
characters. Each character shares one base body sprite, with clothing accessories (hat, shirt,
pants, shoes) rendered as color-tinted layers on top. A 2-frame walk cycle animates at runtime.
The aesthetic must remain compatible with the existing CCTV scanline/vignette/noise overlays.

## User Stories

- As a player, I want to see distinct human silhouettes walking across the CCTV feed, so the
  scene feels like a real surveillance situation rather than abstract colored blocks.
- As a player, I want each person to look visually different through their clothing so I can
  identify suspects by physical description ("red jacket", "black hoodie") rather than by blob color.
- As a developer, I want clothing colors to be driven by the existing `attributes` dict on `Person`
  so that the info card description and the on-screen appearance always agree.

## Functional Requirements

### FR-1: Sprite Size

**Description:** Each character sprite occupies a 10x17 pixel canvas at native resolution and is
displayed at 3x scale (30x51 px), matching the current `PERSON_WIDTH = 30` and fitting within
`PERSON_HEIGHT = 50` with 1 px tolerance.

**Acceptance Criteria:**
- [ ] Native sprite canvas is 10 wide by 17 tall pixels.
- [ ] Display size is 30x51 px via `pygame.transform.scale` with integer 3x factor.
- [ ] Character fits fully within the existing `PERSON_HEIGHT = 50` constant (51 acceptable; update
      constant to 51 if needed).
- [ ] No bilinear blur — only nearest-neighbor scaling is used.

**Priority:** Must Have

---

### FR-2: Shared Base Sprite with Accessory Layers

**Description:** A single base body sprite encodes five distinct color regions using five
placeholder ("signal") colors: skin, hair, shirt, pants, shoes. At construction time, each Person
bakes a final composite surface by tinting each region to the character's assigned colors.

**Acceptance Criteria:**
- [ ] Base sprite is defined once as a 2D Python list of hex color strings (or a small PNG/string
      constant) in a new file `entities/sprites.py`.
- [ ] Five named regions exist: `SKIN`, `HAIR`, `SHIRT`, `PANTS`, `SHOES`.
- [ ] `SpriteBuilder.build(colors: dict) -> pygame.Surface` accepts a dict of region-to-color
      mappings and returns a tinted composite surface with no visible signal colors remaining.
- [ ] The returned surface uses a colorkey or SRCALPHA for the background (transparent around the
      character silhouette).

**Priority:** Must Have

---

### FR-3: Hat Accessory (Optional Layer)

**Description:** A separate hat overlay sprite (same 10x17 canvas, with transparent pixels
everywhere the hat is not drawn) can be conditionally blitted on top of the base. A person either
has a hat or does not.

**Acceptance Criteria:**
- [ ] Hat layer is a separate 2D array with the same canvas dimensions.
- [ ] Hat has its own signal color that gets tinted at build time.
- [ ] `SpriteBuilder.build()` accepts an optional `hat_color` parameter; if `None`, hat is skipped.
- [ ] At least 3 distinct hat colors are available in the palette pool.

**Priority:** Should Have

---

### FR-4: 2-Frame Walk Cycle Animation

**Description:** Each Person alternates between two pre-baked animation frames at a configurable
cadence. Frame A is the resting/neutral pose; Frame B is the stride pose (one leg kicked forward).
The frame shown is determined by the person's accumulated walk distance, not by real time, so
faster people animate faster.

**Acceptance Criteria:**
- [ ] Two frame arrays exist: `WALK_FRAME_A` and `WALK_FRAME_B` in `entities/sprites.py`.
- [ ] Frame B differs from Frame A only in the leg/foot rows (bottom 5 rows of the canvas).
- [ ] Each Person stores `_anim_dist: float` which accumulates `abs(vx * dt * 60)` each update.
- [ ] Current frame index toggles when `_anim_dist` crosses a threshold constant
      `SPRITE_ANIM_STRIDE` (default 12.0 px of travel).
- [ ] `Person.draw()` blits `_frames[_frame_idx]` instead of drawing a rect.
- [ ] Left-facing movement mirrors the sprite horizontally via `pygame.transform.flip`.

**Priority:** Must Have

---

### FR-5: Color Assignment from Attributes

**Description:** Each Person's clothing colors are derived from the `clothing` field in its
`attributes` dict and from a deterministic color pool, so the info card and the visual appearance
agree.

**Acceptance Criteria:**
- [ ] A `CLOTHING_COLOR_MAP` dict in `constants.py` maps clothing descriptor keywords (e.g.
      `"hoodie"`, `"jacket"`, `"parka"`, `"raincoat"`, `"vest"`, `"scarf"`, `"tracksuit"`,
      `"blouse"`) to `(shirt_color, pants_color)` tuples.
- [ ] Skin tone and hair color are chosen from small pools; selection is seeded by the person's
      name so it is stable across runs.
- [ ] Shoes default to a dark gray `(50, 50, 50)` for all characters.
- [ ] Colors must be distinguishable through the CCTV overlays (avoid very dark or fully
      desaturated values).

**Priority:** Must Have

---

### FR-6: CCTV Aesthetic Compatibility

**Description:** Sprites are drawn before the scanline, vignette, and noise overlays, so all
post-processing applies on top — no changes required to the overlay pipeline.

**Acceptance Criteria:**
- [ ] `person.draw(surface)` call site in `game_loop.py` does not change.
- [ ] Sprites are not drawn after the CCTV overlays (current draw order is preserved).
- [ ] Sprite colors are bright enough to be visible at `SCANLINE_ALPHA = 25` and
      `VIGNETTE_STRENGTH = 120` at screen edges.

**Priority:** Must Have

---

## Non-Functional Requirements

- **Performance:** Sprite baking (region tinting) happens once per Person at construction time in
  `build_card()` or an equivalent new `build_sprite()` method. Zero per-frame pixel manipulation.
- **Scaling:** `pygame.transform.scale` (nearest-neighbor, not `smoothscale`) is used for the 3x
  upscale, called once at build time, not per frame.
- **Maintainability:** All sprite pixel data lives in `entities/sprites.py`. Adding a new accessory
  type requires only adding a new 2D array and a new signal color — no changes to the draw loop.
- **No external assets:** The entire sprite definition is Python source code (2D lists of color
  strings). No PNG files. No external tools required to regenerate sprites.

## Out of Scope

- Vertical movement animation (people only move horizontally).
- More than 2 walk frames (a 4-frame cycle is better art but unnecessary complexity here).
- Gender or body-type variation in the base sprite.
- Facial features or expressions.
- Shadow casting.
- Sprite facing changes mid-walk (horizontal flip is sufficient).
- Any changes to the CCTV overlay pipeline.
- Any changes to the info card system.

## Open Decisions

- **PERSON_HEIGHT constant:** Currently 50; displayed sprite will be 51 px at 3x scale. Recommend
  updating to 51. Impact: only affects `person.rect` initialization — no visual change to cards or
  overlays.
- **Hat assignment:** Which persons get hats? Recommend: deterministic based on name hash (roughly
  half the population wears a hat), chosen at Person construction, stored as a bool on `Person`.
