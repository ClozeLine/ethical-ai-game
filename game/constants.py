# Screen
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Red Handed"

# CCTV look
BG_COLOR = (15, 15, 20)
TIMESTAMP_COLOR = (0, 200, 0)
TIMESTAMP_FONT_SIZE = 20
SCANLINE_ALPHA = 25
SCANLINE_SPACING = 4
VIGNETTE_STRENGTH = 120
NOISE_PIXELS_PER_FRAME = 300
NOISE_ALPHA = 30

# Person blocks
PERSON_WIDTH = 30
PERSON_HEIGHT = 51
PERSON_COLORS = [
    (200, 60, 60),    # red
    (60, 120, 200),   # blue
    (60, 180, 80),    # green
    (200, 180, 50),   # yellow
    (180, 80, 180),   # purple
    (200, 130, 50),   # orange
    (80, 200, 200),   # cyan
    (200, 200, 200),  # white
]
SPRITE_SCALE = 3
SPRITE_ANIM_STRIDE = 12.0

PERSON_SPEED_MIN = 0.5
PERSON_SPEED_MAX = 2.0
# Hover cards
CARD_PADDING = 6
CARD_OFFSET_X = 10
CARD_BG_COLOR = (10, 10, 15, 200)
CARD_BORDER_COLOR = (0, 200, 0)
CARD_FONT_SIZE = 13

PERSON_TEMPLATE_DATA = [
    {"name": "MARCUS REID", "age": "34", "clothing": "Black hoodie", "mood": "Nervous", "behavior": "Pacing"},
    {"name": "ELENA VOSS", "age": "28", "clothing": "Red jacket", "mood": "Calm", "behavior": "Browsing"},
    {"name": "JAMES OKAFOR", "age": "41", "clothing": "Green parka", "mood": "Anxious", "behavior": "Loitering"},
    {"name": "SARAH CHEN", "age": "25", "clothing": "Yellow raincoat", "mood": "Cheerful", "behavior": "Walking"},
    {"name": "DMITRI VOLKOV", "age": "37", "clothing": "Purple vest", "mood": "Agitated", "behavior": "Arguing"},
    {"name": "AMIRA HASSAN", "age": "30", "clothing": "Orange scarf", "mood": "Distracted", "behavior": "Texting"},
    {"name": "LUCAS ORTEGA", "age": "22", "clothing": "Cyan tracksuit", "mood": "Relaxed", "behavior": "Sitting"},
    {"name": "NADIA PETROV", "age": "45", "clothing": "White blouse", "mood": "Focused", "behavior": "Watching"},
]

# Sprite color pools
SKIN_TONES = [
    (255, 224, 189),  # light
    (234, 192, 134),  # fair
    (198, 152, 104),  # medium
    (160, 110, 70),   # olive
    (120, 80, 50),    # brown
    (80, 50, 30),     # dark
]

HAIR_COLORS = [
    (40, 30, 20),     # black
    (70, 50, 30),     # dark brown
    (120, 80, 40),    # brown
    (180, 140, 80),   # dirty blonde
    (230, 200, 120),  # blonde
    (180, 60, 30),    # auburn
    (100, 100, 110),  # grey
    (220, 220, 220),  # white/silver
]

HAT_COLORS = [
    (50, 50, 55),     # dark grey
    (140, 30, 30),    # maroon
    (30, 60, 120),    # navy
    (60, 100, 50),    # olive green
    (120, 90, 50),    # tan
    (80, 40, 90),     # plum
]

CLOTHING_COLOR_MAP = {
    "black":  ((40, 40, 45),    (30, 30, 35)),
    "red":    ((180, 50, 50),   (60, 50, 50)),
    "green":  ((50, 140, 60),   (40, 60, 50)),
    "yellow": ((200, 180, 50),  (80, 70, 50)),
    "purple": ((140, 60, 150),  (60, 40, 70)),
    "orange": ((200, 120, 40),  (70, 55, 40)),
    "cyan":   ((60, 180, 190),  (40, 80, 90)),
    "white":  ((220, 220, 225), (80, 80, 85)),
    "blue":   ((50, 80, 180),   (40, 50, 80)),
    "grey":   ((120, 120, 125), (60, 60, 65)),
}
CLOTHING_COLOR_DEFAULT = ((100, 100, 105), (60, 60, 65))

# Dispatch panel
PANEL_WIDTH = 360
PANEL_HEIGHT = 140
PANEL_MARGIN = 16
PANEL_BG_COLOR = (10, 10, 15, 210)
PANEL_BORDER_COLOR = (0, 200, 0)
PANEL_TEXT_COLOR = (0, 200, 0)
PANEL_HEADER_COLOR = (0, 255, 0)
PANEL_FONT_SIZE = 15

# Timer bar
TIMER_BAR_HEIGHT = 10
TIMER_BAR_COLOR = (0, 200, 0)
TIMER_BAR_WARNING_COLOR = (200, 40, 40)
TIMER_BAR_BG_COLOR = (40, 40, 45)
TIMER_TEXT_COLOR = (0, 200, 0)

# Briefing
BRIEFING_DURATION = 3.0

# Flag outline
FLAG_OUTLINE_COLOR = (220, 40, 40)
FLAG_OUTLINE_WIDTH = 3
