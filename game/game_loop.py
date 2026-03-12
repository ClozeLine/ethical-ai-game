import os
import random
import textwrap
from datetime import datetime

import pygame

from entities.person import Person
from game.constants import (
    BG_COLOR,
    BRIEFING_DURATION,
    CARD_FONT_SIZE,
    FLAG_OUTLINE_COLOR,
    FLAG_OUTLINE_WIDTH,
    FPS,
    NOISE_ALPHA,
    NOISE_PIXELS_PER_FRAME,
    PANEL_BG_COLOR,
    PANEL_BORDER_COLOR,
    PANEL_FONT_SIZE,
    PANEL_HEADER_COLOR,
    PANEL_HEIGHT,
    PANEL_MARGIN,
    PANEL_TEXT_COLOR,
    PANEL_WIDTH,
    PERSON_COLORS,
    PERSON_TEMPLATE_DATA,
    SCANLINE_ALPHA,
    SCANLINE_SPACING,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TIMER_BAR_BG_COLOR,
    TIMER_BAR_COLOR,
    TIMER_BAR_HEIGHT,
    TIMER_BAR_WARNING_COLOR,
    TIMER_TEXT_COLOR,
    TIMESTAMP_COLOR,
    TIMESTAMP_FONT_SIZE,
    TITLE,
    VIGNETTE_STRENGTH,
)
from game.round_data import RoundDef, load_rounds
from game.states import GameState


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        # Fonts
        self.font = pygame.font.SysFont("couriernew", TIMESTAMP_FONT_SIZE)
        self.card_font = pygame.font.SysFont("couriernew", CARD_FONT_SIZE)
        self.panel_font = pygame.font.SysFont("couriernew", PANEL_FONT_SIZE)

        # Load round data
        rounds = load_rounds()
        self.round_def: RoundDef = rounds[0]

        # Set up people from round definition
        self.people: list[Person] = []
        self._setup_people_for_round(self.round_def)

        # State machine
        self.state = GameState.BRIEFING
        self.briefing_timer: float = 0.0
        self.round_timer: float = self.round_def.timer_seconds
        self.flagged_person: Person | None = None

        # Load background image
        self._bg = self._load_background()

        # Pre-render static overlays
        self._scanline_surf = self._make_scanlines()
        self._vignette_surf = self._make_vignette()
        self._noise_pool = self._make_noise_pool()
        self._noise_index = 0

        # Pre-render dispatch panel
        self._panel_surf = self._build_panel()

    def _setup_people_for_round(self, round_def: RoundDef):
        # Build a lookup from name → (color, template)
        template_lookup: dict[str, tuple[tuple[int, int, int], dict]] = {}
        for color, tmpl in zip(PERSON_COLORS, PERSON_TEMPLATE_DATA):
            template_lookup[tmpl["name"]] = (color, tmpl)

        self.people = []
        for name in round_def.people_names:
            if name not in template_lookup:
                raise ValueError(
                    f"Round {round_def.round_number}: person '{name}' "
                    f"not found in PERSON_TEMPLATE_DATA"
                )
            color, attrs = template_lookup[name]
            person = Person(color, dict(attrs))
            if name == round_def.suspect_name:
                person.is_suspect = True
            person.build_card(self.card_font)
            person.build_sprite()
            self.people.append(person)

    # --- panel ---

    def _build_panel(self) -> pygame.Surface:
        surf = pygame.Surface((PANEL_WIDTH, PANEL_HEIGHT), pygame.SRCALPHA)
        surf.fill(PANEL_BG_COLOR)
        pygame.draw.rect(surf, PANEL_BORDER_COLOR, (0, 0, PANEL_WIDTH, PANEL_HEIGHT), 1)

        # Header
        header = self.panel_font.render(">> DISPATCH <<", True, PANEL_HEADER_COLOR)
        header_x = (PANEL_WIDTH - header.get_width()) // 2
        surf.blit(header, (header_x, 8))

        # Word-wrap the description
        max_chars = (PANEL_WIDTH - 20) // (self.panel_font.size("A")[0])
        wrapped = textwrap.wrap(self.round_def.description, width=max_chars)
        y = 8 + header.get_height() + 6
        for line in wrapped:
            rendered = self.panel_font.render(line, True, PANEL_TEXT_COLOR)
            surf.blit(rendered, (10, y))
            y += rendered.get_height() + 2

        return surf

    def _draw_panel(self):
        px, py = PANEL_MARGIN, PANEL_MARGIN
        self.screen.blit(self._panel_surf, (px, py))

        # Timer bar area: below the static panel content
        bar_y = py + PANEL_HEIGHT - TIMER_BAR_HEIGHT - 24
        bar_x = px + 10
        # Reserve space for timer text inside the panel
        timer_text_w = 60
        bar_w = PANEL_WIDTH - 20 - timer_text_w - 6

        # Timer fraction
        if self.state == GameState.BRIEFING:
            frac = 1.0
        elif self.state == GameState.TIME_UP:
            frac = 0.0
        else:
            frac = max(0.0, self.round_timer / self.round_def.timer_seconds)

        # Background bar
        pygame.draw.rect(self.screen, TIMER_BAR_BG_COLOR, (bar_x, bar_y, bar_w, TIMER_BAR_HEIGHT))
        # Fill bar
        bar_color = TIMER_BAR_WARNING_COLOR if frac < 0.25 else TIMER_BAR_COLOR
        fill_w = int(bar_w * frac)
        if fill_w > 0:
            pygame.draw.rect(self.screen, bar_color, (bar_x, bar_y, fill_w, TIMER_BAR_HEIGHT))

        # Timer text (inside panel bounds, right of bar)
        if self.state == GameState.BRIEFING:
            time_text = f"{self.round_def.timer_seconds:.1f}s"
        else:
            time_text = f"{max(0, self.round_timer):.1f}s"
        text_color = TIMER_BAR_WARNING_COLOR if frac < 0.25 else TIMER_TEXT_COLOR
        timer_surf = self.panel_font.render(time_text, True, text_color)
        self.screen.blit(timer_surf, (bar_x + bar_w + 6, bar_y - 2))

        # Status text for terminal states
        panel_bottom = py + PANEL_HEIGHT
        status = None
        if self.state == GameState.FLAGGED:
            status = ">> SUSPECT FLAGGED <<"
        elif self.state == GameState.TIME_UP:
            status = ">> TIME EXPIRED <<"

        if status:
            status_surf = self.panel_font.render(status, True, PANEL_HEADER_COLOR)
            sx = px + (PANEL_WIDTH - status_surf.get_width()) // 2
            sy = min(bar_y + TIMER_BAR_HEIGHT + 4, panel_bottom - status_surf.get_height() - 2)
            self.screen.blit(status_surf, (sx, sy))

    # --- click handling ---

    def _handle_click(self, pos: tuple[int, int]):
        if self.state != GameState.PLAYING:
            return
        # Check in reverse draw order (topmost person first)
        for person in reversed(self.people):
            if person.rect.collidepoint(pos):
                person.is_flagged = True
                person.vx = 0  # Freeze flagged person in place
                self.flagged_person = person
                self.state = GameState.FLAGGED
                return

    def _draw_flag_outline(self):
        if self.flagged_person is None:
            return
        r = self.flagged_person.rect.inflate(FLAG_OUTLINE_WIDTH * 2, FLAG_OUTLINE_WIDTH * 2)
        pygame.draw.rect(self.screen, FLAG_OUTLINE_COLOR, r, FLAG_OUTLINE_WIDTH)

    # --- overlay builders ---

    def _load_background(self) -> pygame.Surface | None:
        bg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bg.png")
        if not os.path.exists(bg_path):
            return None
        img = pygame.image.load(bg_path).convert()
        if img.get_size() != (SCREEN_WIDTH, SCREEN_HEIGHT):
            img = pygame.transform.smoothscale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        return img

    def _make_scanlines(self) -> pygame.Surface:
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(0, SCREEN_HEIGHT, SCANLINE_SPACING):
            pygame.draw.line(surf, (0, 0, 0, SCANLINE_ALPHA), (0, y), (SCREEN_WIDTH, y))
        return surf

    def _make_vignette(self) -> pygame.Surface:
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        steps = 40
        for i in range(steps):
            alpha = int(VIGNETTE_STRENGTH * ((steps - i) / steps) ** 2)
            rect = pygame.Rect(i * 2, i * 2, SCREEN_WIDTH - i * 4, SCREEN_HEIGHT - i * 4)
            if rect.width <= 0 or rect.height <= 0:
                break
            pygame.draw.rect(surf, (0, 0, 0, alpha), rect, width=2)
        return surf

    def _make_noise_pool(self, count: int = 30) -> list[pygame.Surface]:
        pool = []
        for _ in range(count):
            surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for _ in range(NOISE_PIXELS_PER_FRAME):
                x = random.randint(0, SCREEN_WIDTH - 1)
                y = random.randint(0, SCREEN_HEIGHT - 1)
                v = random.randint(150, 255)
                surf.set_at((x, y), (v, v, v, NOISE_ALPHA))
            pool.append(surf)
        return pool

    def _draw_noise(self):
        self.screen.blit(self._noise_pool[self._noise_index], (0, 0))
        self._noise_index = (self._noise_index + 1) % len(self._noise_pool)

    def _draw_timestamp(self):
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        line1 = self.font.render("CAM 01", True, TIMESTAMP_COLOR)
        line2 = self.font.render(now, True, TIMESTAMP_COLOR)
        self.screen.blit(line1, (SCREEN_WIDTH - line1.get_width() - 16, 16))
        self.screen.blit(line2, (SCREEN_WIDTH - line2.get_width() - 16, 16 + line1.get_height() + 4))

    # --- main loop ---

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)

            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)

            # State updates
            if self.state == GameState.BRIEFING:
                self.briefing_timer += dt
                if self.briefing_timer >= BRIEFING_DURATION:
                    self.state = GameState.PLAYING
            elif self.state == GameState.PLAYING:
                self.round_timer -= dt
                if self.round_timer <= 0:
                    self.round_timer = 0
                    self.state = GameState.TIME_UP

            # People always walk
            for person in self.people:
                person.update(dt)

            # Draw
            if self._bg:
                self.screen.blit(self._bg, (0, 0))
            else:
                self.screen.fill(BG_COLOR)

            for person in self.people:
                person.draw(self.screen)

            # Flag outline (before overlays so scanlines apply on top)
            self._draw_flag_outline()

            # Info cards always visible
            for person in self.people:
                person.draw_card(self.screen)

            # Dispatch panel (before CCTV overlays)
            self._draw_panel()

            # CCTV post-processing
            self.screen.blit(self._scanline_surf, (0, 0))
            self.screen.blit(self._vignette_surf, (0, 0))
            self._draw_noise()
            self._draw_timestamp()

            pygame.display.flip()

        pygame.quit()
