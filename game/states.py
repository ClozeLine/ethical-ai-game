from enum import Enum, auto


class GameState(Enum):
    BRIEFING = auto()   # Panel shown, short delay before timer starts
    PLAYING = auto()    # Timer counting down, player can click to flag
    FLAGGED = auto()    # Person selected, round over
    TIME_UP = auto()    # Timer expired, no flag made
