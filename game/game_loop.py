import os
import random
import textwrap
from datetime import datetime
from math import ceil, sqrt

import pygame

from entities.person import Person
from game.constants import (
    BG_COLOR,
    BRIEFING_DURATION,
    CARD_FONT_SIZE,
    CLICK_HITBOX_PADDING,
    FIRED_DIM_COLOR,
    FIRED_HEADER_COLOR,
    FIRED_TEXT_COLOR,
    FLAG_BLINK_RATE,
    FLAG_OUTLINE_COLOR,
    FLAG_OUTLINE_WIDTH,
    FPS,
    NOISE_ALPHA,
    NOISE_PIXELS_PER_FRAME,
    NUM_PEOPLE,
    PANEL_BG_COLOR,
    PANEL_BORDER_COLOR,
    PANEL_FONT_SIZE,
    PANEL_HEADER_COLOR,
    PANEL_HEIGHT,
    PANEL_MARGIN,
    PANEL_TEXT_COLOR,
    PANEL_WIDTH,
    PERSON_COLORS,
    PERSON_HEIGHT,
    PERSON_TEMPLATE_DATA,
    PERSON_WIDTH,
    ROUND_END_PAUSE,
    SCANLINE_ALPHA,
    SCANLINE_SPACING,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STATS_BG_COLOR,
    STATS_DIM_COLOR,
    STATS_MARGIN_TOP,
    STATS_MARGIN_X,
    STATS_PROMPT_COLOR,
    STATS_REVEAL_COLOR,
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
from game.round_data import RoundDef, RoundResult, load_rounds
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
        self.all_rounds = load_rounds()
        self.current_round_index: int = 0
        self.round_def: RoundDef = self.all_rounds[0]
        self.round_results: list[RoundResult] = []

        # Validate that PERSON_COLORS and PERSON_TEMPLATE_DATA stay in sync
        assert len(PERSON_COLORS) == len(PERSON_TEMPLATE_DATA), (
            f"PERSON_COLORS ({len(PERSON_COLORS)}) and "
            f"PERSON_TEMPLATE_DATA ({len(PERSON_TEMPLATE_DATA)}) must have the same length"
        )
        assert NUM_PEOPLE <= len(PERSON_TEMPLATE_DATA), (
            f"NUM_PEOPLE ({NUM_PEOPLE}) exceeds available templates "
            f"({len(PERSON_TEMPLATE_DATA)})"
        )

        # Set up people from round definition
        self.people: list[Person] = []
        self._setup_people_for_round(self.round_def)

        # State machine
        self.state = GameState.BRIEFING
        self.briefing_timer: float = 0.0
        self.round_timer: float = self.round_def.timer_seconds
        self.selected_person: Person | None = None
        self._round_end_timer: float = 0.0

        # Load background image
        self._bg = self._load_background()

        # Pre-render static overlays
        self._scanline_surf = self._make_scanlines()
        self._vignette_surf = self._make_vignette()
        self._noise_pool = self._make_noise_pool()
        self._noise_index = 0

        # Pre-render dispatch panel
        self._panel_surf = self._build_panel()

        # End screen (built when GAME_OVER is reached — stats or fired)
        self._stats_surf: pygame.Surface | None = None
        self._was_fired: bool = False

    def _setup_people_for_round(self, round_def: RoundDef):
        # Build a lookup from name → (color, template)
        template_lookup: dict[str, tuple[tuple[int, int, int], dict]] = {}
        for color, tmpl in zip(PERSON_COLORS, PERSON_TEMPLATE_DATA):
            template_lookup[tmpl["name"]] = (color, tmpl)

        self.people = []

        # 1. Named people (must not exceed NUM_PEOPLE)
        if len(round_def.people_names) > NUM_PEOPLE:
            raise ValueError(
                f"Round {round_def.round_number}: defines {len(round_def.people_names)} "
                f"named people but NUM_PEOPLE is {NUM_PEOPLE}"
            )
        for name in round_def.people_names:
            if name not in template_lookup:
                raise ValueError(
                    f"Round {round_def.round_number}: person '{name}' "
                    f"not found in PERSON_TEMPLATE_DATA"
                )
            color, attrs = template_lookup[name]
            person = Person(color, dict(attrs))
            person.build_card(self.card_font)
            person.build_sprite()
            self.people.append(person)

        # 1b. Pad with extra people from unused templates
        extra_needed = NUM_PEOPLE - len(self.people)
        if extra_needed > 0:
            used_names = set(round_def.people_names)
            unused = [
                (color, tmpl)
                for color, tmpl in zip(PERSON_COLORS, PERSON_TEMPLATE_DATA)
                if tmpl["name"] not in used_names
            ]
            random.shuffle(unused)
            for color, tmpl in unused[:extra_needed]:
                person = Person(color, dict(tmpl))
                person.build_card(self.card_font)
                person.build_sprite()
                self.people.append(person)

        # 2. Spread people across the screen
        self._distribute_positions(self.people)

        # 3. Even left/right split
        self._balance_directions(self.people)

    @staticmethod
    def _balance_directions(people: list[Person]):
        """Assign an even left/right split across all people."""
        n = len(people)
        dirs = [-1] * (n // 2) + [1] * (n - n // 2)
        random.shuffle(dirs)
        for person, d in zip(people, dirs):
            person.set_direction(d)

    @staticmethod
    def _distribute_positions(people: list[Person]):
        """Place people on a grid with jitter to prevent clustering."""
        n = len(people)
        if n == 0:
            return
        aspect = SCREEN_WIDTH / SCREEN_HEIGHT
        cols = max(1, ceil(sqrt(n * aspect)))
        rows = max(1, ceil(n / cols))
        cell_w = SCREEN_WIDTH / cols
        cell_h = SCREEN_HEIGHT / rows

        # Build shuffled cell indices
        cells = [(c, r) for r in range(rows) for c in range(cols)]
        random.shuffle(cells)

        for i, person in enumerate(people):
            col, row = cells[i]
            # Random offset within cell, clamped to screen bounds
            jitter_x = random.uniform(0, max(0, cell_w - PERSON_WIDTH))
            jitter_y = random.uniform(0, max(0, cell_h - PERSON_HEIGHT))
            person.x = col * cell_w + max(0, jitter_x)
            person.y = row * cell_h + max(0, jitter_y)
            # Clamp to screen
            person.x = min(person.x, SCREEN_WIDTH - PERSON_WIDTH)
            person.y = min(person.y, SCREEN_HEIGHT - PERSON_HEIGHT)
            person.rect.x = int(person.x)
            person.rect.y = int(person.y)

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
        elif self.state in (GameState.ROUND_END, GameState.GAME_OVER):
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
        elif self.state in (GameState.ROUND_END, GameState.GAME_OVER):
            time_text = "0.0s"
        else:
            time_text = f"{max(0, self.round_timer):.1f}s"
        text_color = TIMER_BAR_WARNING_COLOR if frac < 0.25 else TIMER_TEXT_COLOR
        timer_surf = self.panel_font.render(time_text, True, text_color)
        self.screen.blit(timer_surf, (bar_x + bar_w + 6, bar_y - 2))

        # Status text (only during ROUND_END; GAME_OVER uses the stats screen)
        panel_bottom = py + PANEL_HEIGHT
        status = None
        if self.state == GameState.ROUND_END and self.round_results:
            last = self.round_results[-1]
            if last.flagged_name is not None:
                status = ">> SUSPECT FLAGGED <<"
            else:
                status = ">> TIME EXPIRED <<"

        if status:
            status_surf = self.panel_font.render(status, True, PANEL_HEADER_COLOR)
            sx = px + (PANEL_WIDTH - status_surf.get_width()) // 2
            sy = min(bar_y + TIMER_BAR_HEIGHT + 4, panel_bottom - status_surf.get_height() - 2)
            self.screen.blit(status_surf, (sx, sy))

    # --- stats/recap screen ---

    def _build_stats_surface(self) -> pygame.Surface:
        """Pre-render the full-screen stats overlay shown at GAME_OVER."""
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        surf.fill(STATS_BG_COLOR)

        x = STATS_MARGIN_X
        y = STATS_MARGIN_TOP

        # Header
        header = self.panel_font.render(">> SURVEILLANCE REPORT <<", True, PANEL_HEADER_COLOR)
        surf.blit(header, ((SCREEN_WIDTH - header.get_width()) // 2, y))
        y += header.get_height() + 8

        # Divider
        pygame.draw.line(surf, PANEL_TEXT_COLOR, (x, y), (SCREEN_WIDTH - x, y))
        y += 12

        # Aggregate stats
        total = len(self.round_results)
        flagged = sum(1 for r in self.round_results if r.flagged_name is not None)
        matched = sum(1 for r in self.round_results if r.was_plausible is True)

        for line in [
            f"ROUNDS COMPLETED: {total}/{len(self.all_rounds)}",
            f"SUSPECTS FLAGGED: {flagged}/{total}",
            f"MATCHED DISPATCH: {matched}/{flagged}" if flagged > 0 else "MATCHED DISPATCH: 0/0",
        ]:
            rendered = self.panel_font.render(line, True, PANEL_TEXT_COLOR)
            surf.blit(rendered, (x, y))
            y += rendered.get_height() + 2

        y += 10

        # Per-round blocks
        round_lookup = {rd.round_number: rd for rd in self.all_rounds}
        for result in self.round_results:
            rd = round_lookup[result.round_number]

            # Truncate dispatch description to fit
            prefix = f'RD {result.round_number} | "'
            suffix = '"'
            char_w = self.panel_font.size("A")[0]
            prefix_px = self.panel_font.size(prefix)[0] + self.panel_font.size(suffix)[0]
            max_desc_chars = (SCREEN_WIDTH - 2 * x - prefix_px) // char_w
            desc = rd.description
            if len(desc) > max_desc_chars:
                desc = desc[:max_desc_chars - 3] + "..."

            # Round header line
            rd_header = self.panel_font.render(
                f'{prefix}{desc}{suffix}', True, PANEL_TEXT_COLOR
            )
            surf.blit(rd_header, (x, y))
            y += rd_header.get_height() + 2

            # Flag status line
            if result.flagged_name is not None:
                if result.was_plausible:
                    flag_text = f"  > FLAGGED: {result.flagged_name}  [MATCHED DISPATCH]"
                    flag_color = PANEL_TEXT_COLOR
                else:
                    flag_text = f"  > FLAGGED: {result.flagged_name}  [DID NOT MATCH]"
                    flag_color = TIMER_BAR_WARNING_COLOR
            else:
                flag_text = "  > NO FLAG -- TIME EXPIRED"
                flag_color = TIMER_BAR_WARNING_COLOR

            flag_surf = self.panel_font.render(flag_text, True, flag_color)
            surf.blit(flag_surf, (x, y))
            y += flag_surf.get_height() + 2

            # Reveal line (only if someone was flagged)
            if result.flagged_name is not None:
                reveal_prefix = "  > "
                if result.flagged_name in rd.reveals:
                    reveal_payload = rd.reveals[result.flagged_name]
                else:
                    reveal_payload = "No additional information on file."
                reveal_text = reveal_prefix + reveal_payload
                # Truncate if needed
                prefix_chars = len(reveal_prefix)
                max_reveal = (SCREEN_WIDTH - 2 * x - 20) // char_w - prefix_chars
                if len(reveal_payload) > max_reveal:
                    reveal_text = reveal_prefix + reveal_payload[:max_reveal - 3] + "..."
                reveal_surf = self.panel_font.render(reveal_text, True, STATS_REVEAL_COLOR)
                surf.blit(reveal_surf, (x, y))
                y += reveal_surf.get_height() + 2

            y += 6

        # Divider
        pygame.draw.line(surf, PANEL_TEXT_COLOR, (x, y), (SCREEN_WIDTH - x, y))
        y += 14

        # Closing message
        closing = self.panel_font.render(
            "EVERY PERSON YOU SAW WAS INNOCENT.", True, PANEL_HEADER_COLOR
        )
        surf.blit(closing, ((SCREEN_WIDTH - closing.get_width()) // 2, y))
        y += closing.get_height() + 10

        # Explanation lines
        explanation = [
            "The data was accurate. The descriptions were vague.",
            "You had seconds to decide. The bias was not in the",
            "system -- it was in the decision.",
        ]
        for line in explanation:
            rendered = self.panel_font.render(line, True, STATS_DIM_COLOR)
            surf.blit(rendered, ((SCREEN_WIDTH - rendered.get_width()) // 2, y))
            y += rendered.get_height() + 2

        y += 16

        # Exit prompt
        prompt = self.panel_font.render("[ ESC TO EXIT ]", True, STATS_PROMPT_COLOR)
        surf.blit(prompt, ((SCREEN_WIDTH - prompt.get_width()) // 2, y))

        return surf

    def _build_fired_surface(self) -> pygame.Surface:
        """Pre-render the 'you're fired' screen for failing to flag anyone."""
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        surf.fill(STATS_BG_COLOR)

        cx = SCREEN_WIDTH // 2
        y = SCREEN_HEIGHT // 2 - 80

        # Header
        header = self.panel_font.render(">> TERMINATED <<", True, FIRED_HEADER_COLOR)
        surf.blit(header, (cx - header.get_width() // 2, y))
        y += header.get_height() + 16

        # Divider
        x = STATS_MARGIN_X
        pygame.draw.line(surf, FIRED_HEADER_COLOR, (x, y), (SCREEN_WIDTH - x, y))
        y += 16

        # Message lines
        lines = [
            "You failed to flag a suspect.",
            "Control has deemed you unproductive.",
            "",
            "You're fired.",
        ]
        for line in lines:
            if line == "":
                y += 10
                continue
            rendered = self.panel_font.render(line, True, FIRED_TEXT_COLOR)
            surf.blit(rendered, (cx - rendered.get_width() // 2, y))
            y += rendered.get_height() + 4

        y += 20

        # Divider
        pygame.draw.line(surf, FIRED_HEADER_COLOR, (x, y), (SCREEN_WIDTH - x, y))
        y += 20

        # Exit prompt
        prompt = self.panel_font.render("[ ESC TO EXIT ]", True, FIRED_DIM_COLOR)
        surf.blit(prompt, (cx - prompt.get_width() // 2, y))

        return surf

    # --- selection / confirm ---

    def _deselect_current(self):
        """Clear current selection, unfreeze the person."""
        if self.selected_person is not None:
            self.selected_person.is_flagged = False
            self.selected_person.unfreeze()
            self.selected_person = None

    def _handle_click(self, pos: tuple[int, int]):
        if self.state != GameState.PLAYING:
            return
        # Check in reverse draw order (topmost person first)
        for person in reversed(self.people):
            hit_rect = person.rect.inflate(CLICK_HITBOX_PADDING * 2, CLICK_HITBOX_PADDING * 2)
            if hit_rect.collidepoint(pos):
                if person is self.selected_person:
                    # Toggle off: clicking the already-selected person deselects
                    self._deselect_current()
                else:
                    # Deselect previous, select new
                    self._deselect_current()
                    person.is_flagged = True
                    person.freeze()
                    self.selected_person = person
                return
        # Clicked empty space → deselect
        self._deselect_current()

    def _handle_confirm(self):
        """Enter key: confirm the current selection and end the round."""
        if self.state != GameState.PLAYING or self.selected_person is None:
            return
        self.round_results.append(RoundResult(
            round_number=self.round_def.round_number,
            flagged_name=self.selected_person.name,
            was_plausible=self.selected_person.name in self.round_def.plausible_names,
            time_remaining=self.round_timer,
        ))
        self.state = GameState.ROUND_END
        self._round_end_timer = 0.0

    def _advance_round(self):
        """Move to the next round, or GAME_OVER if all rounds are done."""
        self.current_round_index += 1
        if self.current_round_index >= len(self.all_rounds):
            self.state = GameState.GAME_OVER
            self._stats_surf = self._build_stats_surface()
            return
        self.round_def = self.all_rounds[self.current_round_index]
        self._deselect_current()
        self._setup_people_for_round(self.round_def)
        self._panel_surf = self._build_panel()
        self.briefing_timer = 0.0
        self.round_timer = self.round_def.timer_seconds
        self.state = GameState.BRIEFING

    def _draw_flag_outline(self):
        if self.selected_person is None:
            return
        # Blink during ROUND_END pause
        if self.state == GameState.ROUND_END:
            cycle = self._round_end_timer * FLAG_BLINK_RATE
            if int(cycle * 2) % 2 == 1:
                return  # outline hidden for half of each blink cycle
        r = self.selected_person.rect.inflate(FLAG_OUTLINE_WIDTH * 2, FLAG_OUTLINE_WIDTH * 2)
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
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self._handle_confirm()

            # State updates
            if self.state == GameState.BRIEFING:
                self.briefing_timer += dt
                if self.briefing_timer >= BRIEFING_DURATION:
                    self.state = GameState.PLAYING
            elif self.state == GameState.PLAYING:
                self.round_timer -= dt
                if self.round_timer <= 0:
                    self.round_timer = 0
                    if self.selected_person is not None:
                        # Auto-confirm the current selection
                        self.round_results.append(RoundResult(
                            round_number=self.round_def.round_number,
                            flagged_name=self.selected_person.name,
                            was_plausible=self.selected_person.name in self.round_def.plausible_names,
                            time_remaining=0.0,
                        ))
                        self.state = GameState.ROUND_END
                        self._round_end_timer = 0.0
                    else:
                        # No one selected — you're fired
                        self._deselect_current()
                        self._was_fired = True
                        self.state = GameState.GAME_OVER
                        self._stats_surf = self._build_fired_surface()
            elif self.state == GameState.ROUND_END:
                self._round_end_timer += dt
                if self._round_end_timer >= ROUND_END_PAUSE:
                    self._advance_round()

            # People walk (except in GAME_OVER)
            if self.state != GameState.GAME_OVER:
                for person in self.people:
                    person.update(dt)

            # Draw
            if self._stats_surf is not None:
                # Stats screen replaces the normal game scene
                self.screen.fill(BG_COLOR)
                self.screen.blit(self._stats_surf, (0, 0))
            else:
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

            # CCTV post-processing (scanlines/vignette/noise apply everywhere
            # for the surveillance aesthetic; timestamp hidden on stats screen)
            self.screen.blit(self._scanline_surf, (0, 0))
            self.screen.blit(self._vignette_surf, (0, 0))
            self._draw_noise()
            if self._stats_surf is None:
                self._draw_timestamp()

            pygame.display.flip()

        pygame.quit()
