from enum import Enum, auto


class GameState(Enum):
    MENU = auto()       # Main menu with Play button
    BRIEFING = auto()   # Panel shown, short delay before timer starts
    PLAYING = auto()    # Timer counting down, player can click to select
    ROUND_END = auto()  # Round over (confirmed or timed out), brief pause
    GAME_OVER = auto()  # All rounds complete
