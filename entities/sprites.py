import copy

import pygame

# Signal colors — placeholders in templates, replaced at build time
SIG_SKIN = "#FF0001"
SIG_HAIR = "#FF0002"
SIG_SHIRT = "#FF0003"
SIG_PANTS = "#FF0004"
SIG_SHOES = "#FF0005"
SIG_HAT = "#FF0006"
EYE_COLOR = "#1A1A2E"  # Fixed color — resolved via pygame.Color fallback in build_frame

_ = None
K = SIG_SKIN
H = SIG_HAIR
S = SIG_SHIRT
P = SIG_PANTS
E = SIG_SHOES
X = EYE_COLOR
T = SIG_HAT

# 10x17 standing pose
BODY_FRAME_A = [
    [_, _, _, H, H, H, H, _, _, _],  # row 0  hair top
    [_, _, H, H, H, H, H, H, _, _],  # row 1  hair
    [_, _, H, K, K, K, K, H, _, _],  # row 2  forehead
    [_, _, K, K, X, K, X, K, _, _],  # row 3  eyes
    [_, _, K, K, K, K, K, K, _, _],  # row 4  mouth
    [_, _, _, _, K, K, _, _, _, _],  # row 5  neck
    [_, _, S, S, S, S, S, S, _, _],  # row 6  shirt top
    [_, K, S, S, S, S, S, S, K, _],  # row 7  shirt + arms
    [_, K, S, S, S, S, S, S, K, _],  # row 8  shirt + arms
    [_, _, S, S, S, S, S, S, _, _],  # row 9  shirt
    [_, _, S, S, S, S, S, S, _, _],  # row 10 shirt bottom
    [_, _, P, P, P, P, P, P, _, _],  # row 11 pants waist
    [_, _, P, P, _, _, P, P, _, _],  # row 12 pants legs
    [_, _, P, P, _, _, P, P, _, _],  # row 13
    [_, _, P, P, _, _, P, P, _, _],  # row 14
    [_, _, P, P, _, _, P, P, _, _],  # row 15
    [_, E, E, E, _, _, E, E, E, _],  # row 16 shoes
]

# Stride pose — only rows 12-16 differ
BODY_FRAME_B = [
    [_, _, _, H, H, H, H, _, _, _],
    [_, _, H, H, H, H, H, H, _, _],
    [_, _, H, K, K, K, K, H, _, _],
    [_, _, K, K, X, K, X, K, _, _],
    [_, _, K, K, K, K, K, K, _, _],
    [_, _, _, _, K, K, _, _, _, _],
    [_, _, S, S, S, S, S, S, _, _],
    [_, K, S, S, S, S, S, S, K, _],
    [_, K, S, S, S, S, S, S, K, _],
    [_, _, S, S, S, S, S, S, _, _],
    [_, _, S, S, S, S, S, S, _, _],
    [_, _, P, P, P, P, P, P, _, _],
    [_, _, _, P, P, _, P, P, _, _],  # row 12 stride
    [_, _, _, P, P, P, P, _, _, _],  # row 13
    [_, _, P, P, _, _, _, P, P, _],  # row 14
    [_, _, P, P, _, _, _, P, P, _],  # row 15
    [_, E, E, E, _, _, _, E, E, E],  # row 16
]

# Hat overlay — replaces rows 0-2
HAT_OVERLAY = [
    [_, _, T, T, T, T, T, T, _, _],  # row 0
    [_, _, T, T, T, T, T, T, _, _],  # row 1
    [_, T, T, T, T, T, T, T, T, _],  # row 2  brim
]


def build_frame(
    template: list[list[str | None]],
    color_map: dict[str, tuple[int, int, int]],
    scale: int = 3,
) -> pygame.Surface:
    """Build a scaled SRCALPHA surface from a pixel template with color replacement."""
    h = len(template)
    w = len(template[0])
    surf = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)

    for row_i, row in enumerate(template):
        for col_i, pixel in enumerate(row):
            if pixel is None:
                continue
            color = color_map.get(pixel, pygame.Color(pixel))
            surf.fill(color, (col_i * scale, row_i * scale, scale, scale))

    return surf


def apply_hat(
    template: list[list[str | None]],
    hat_overlay: list[list[str | None]],
) -> list[list[str | None]]:
    """Return a deep copy of template with the hat overlay applied to the top rows."""
    result = copy.deepcopy(template)
    for i, hat_row in enumerate(hat_overlay):
        for j, pixel in enumerate(hat_row):
            if pixel is not None:
                result[i][j] = pixel
    return result
