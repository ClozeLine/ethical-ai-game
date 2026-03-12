import hashlib
import random

import pygame

from entities.sprites import (
    BODY_FRAME_A,
    BODY_FRAME_B,
    EYE_COLOR,
    HAT_OVERLAY,
    SIG_HAIR,
    SIG_HAT,
    SIG_PANTS,
    SIG_SHIRT,
    SIG_SHOES,
    SIG_SKIN,
    apply_hat,
    build_frame,
)
from game.constants import (
    CARD_BG_COLOR,
    CARD_BORDER_COLOR,
    CARD_OFFSET_X,
    CARD_PADDING,
    CLOTHING_COLOR_DEFAULT,
    CLOTHING_COLOR_MAP,
    HAIR_COLORS,
    HAT_COLORS,
    PERSON_HEIGHT,
    PERSON_SPEED_MAX,
    PERSON_SPEED_MIN,
    PERSON_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SKIN_TONES,
    SPRITE_ANIM_STRIDE,
    SPRITE_SCALE,
)


class Person:
    def __init__(self, color: tuple[int, int, int], attributes: dict | None = None):
        self.x = float(random.randint(0, SCREEN_WIDTH - PERSON_WIDTH))
        self.y = float(random.randint(0, SCREEN_HEIGHT - PERSON_HEIGHT))
        self.rect = pygame.Rect(int(self.x), int(self.y), PERSON_WIDTH, PERSON_HEIGHT)
        self.color = color

        self.speed = random.uniform(PERSON_SPEED_MIN, PERSON_SPEED_MAX)
        self.vx = self.speed * random.choice((-1, 1))

        self.attributes: dict = attributes or {}
        self.is_suspect: bool = False
        self.is_flagged: bool = False

        # Animation state
        self._anim_dist: float = 0.0
        self._anim_frame: int = 0  # 0 = standing, 1 = stride
        self._facing_right: bool = self.vx >= 0
        self._sprites: list[pygame.Surface] | None = None

    @property
    def name(self) -> str:
        return self.attributes.get("name", "")

    def build_sprite(self):
        """Pre-render 4 sprite surfaces: [A_right, A_left, B_right, B_left]."""
        name = self.attributes.get("name", "")
        h = hashlib.md5(name.encode()).hexdigest()

        # Deterministic selections from hash
        skin = SKIN_TONES[int(h[0:2], 16) % len(SKIN_TONES)]
        hair = HAIR_COLORS[int(h[2:4], 16) % len(HAIR_COLORS)]
        has_hat = int(h[4:6], 16) % 2 == 0
        hat_color = HAT_COLORS[int(h[6:8], 16) % len(HAT_COLORS)]

        # Clothing from description
        clothing_desc = self.attributes.get("clothing", "").lower()
        shirt, pants = CLOTHING_COLOR_DEFAULT
        for keyword, (s, p) in CLOTHING_COLOR_MAP.items():
            if keyword in clothing_desc:
                shirt, pants = s, p
                break

        # Shoes: pants darkened by 20 per channel
        shoes = (max(0, pants[0] - 20), max(0, pants[1] - 20), max(0, pants[2] - 20))

        color_map = {
            SIG_SKIN: skin,
            SIG_HAIR: hair,
            SIG_SHIRT: shirt,
            SIG_PANTS: pants,
            SIG_SHOES: shoes,
            SIG_HAT: hat_color,
            EYE_COLOR: (26, 26, 46),
        }

        # Build templates (optionally with hat)
        if has_hat:
            tmpl_a = apply_hat(BODY_FRAME_A, HAT_OVERLAY)
            tmpl_b = apply_hat(BODY_FRAME_B, HAT_OVERLAY)
        else:
            tmpl_a = BODY_FRAME_A
            tmpl_b = BODY_FRAME_B

        frame_a = build_frame(tmpl_a, color_map, SPRITE_SCALE)
        frame_b = build_frame(tmpl_b, color_map, SPRITE_SCALE)

        assert frame_a.get_size() == (PERSON_WIDTH, PERSON_HEIGHT), (
            f"Sprite size {frame_a.get_size()} != ({PERSON_WIDTH}, {PERSON_HEIGHT})"
        )

        # [A_right, A_left, B_right, B_left]
        self._sprites = [
            frame_a,
            pygame.transform.flip(frame_a, True, False),
            frame_b,
            pygame.transform.flip(frame_b, True, False),
        ]

    def update(self, dt: float):
        dx = self.vx * dt * 60
        self.x += dx

        # Track facing direction
        if dx > 0:
            self._facing_right = True
        elif dx < 0:
            self._facing_right = False

        # Accumulate distance for animation
        self._anim_dist += abs(dx)
        if self._anim_dist >= SPRITE_ANIM_STRIDE:
            self._anim_dist -= SPRITE_ANIM_STRIDE
            self._anim_frame = 1 - self._anim_frame

        # Wrap around screen edges, randomize height on re-entry
        if self.x > SCREEN_WIDTH:
            self.x = -PERSON_WIDTH
            self.y = float(random.randint(0, SCREEN_HEIGHT - PERSON_HEIGHT))
        elif self.x < -PERSON_WIDTH:
            self.x = SCREEN_WIDTH
            self.y = float(random.randint(0, SCREEN_HEIGHT - PERSON_HEIGHT))

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def draw(self, surface: pygame.Surface):
        if self._sprites:
            idx = self._anim_frame * 2 + (0 if self._facing_right else 1)
            surface.blit(self._sprites[idx], (self.rect.x, self.rect.y))
        else:
            pygame.draw.rect(surface, self.color, self.rect)

    def build_card(self, font: pygame.font.Font):
        """Pre-render the card surface. Call once after construction."""
        if not self.attributes:
            return
        lines = [f"{k.upper()}: {v}" for k, v in self.attributes.items() if k != "clothing"]
        self._card_lines = [font.render(line, True, CARD_BORDER_COLOR) for line in lines]
        line_h = font.get_height()
        self._card_w = max(r.get_width() for r in self._card_lines) + CARD_PADDING * 2
        self._card_h = line_h * len(self._card_lines) + CARD_PADDING * 2
        self._card_line_h = line_h

        # Pre-render background + border + text into a single surface
        self._card_surf = pygame.Surface((self._card_w, self._card_h), pygame.SRCALPHA)
        self._card_surf.fill(CARD_BG_COLOR)
        pygame.draw.rect(self._card_surf, CARD_BORDER_COLOR, (0, 0, self._card_w, self._card_h), 1)
        for i, r in enumerate(self._card_lines):
            self._card_surf.blit(r, (CARD_PADDING, CARD_PADDING + i * line_h))

    def draw_card(self, surface: pygame.Surface):
        if not self.attributes or not hasattr(self, "_card_surf"):
            return

        # Position to the right of the person; flip left if off-screen
        card_x = self.rect.right + CARD_OFFSET_X
        if card_x + self._card_w > SCREEN_WIDTH:
            card_x = self.rect.left - CARD_OFFSET_X - self._card_w
        card_x = max(0, min(card_x, SCREEN_WIDTH - self._card_w))

        card_y = max(0, min(self.rect.top, SCREEN_HEIGHT - self._card_h))

        surface.blit(self._card_surf, (card_x, card_y))
