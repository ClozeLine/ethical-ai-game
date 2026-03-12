# Red Handed

> *A game about bias in humans, given data from AI systems.*

Red Handed is a single-player digital game. It explores how accurate AI-generated data like mood detection, behavioural flags, and such can still produce systematically biased human decisions when combined with time pressure and ambiguous information.

---

## Concept

You play as a surveillance operator watching CCTV footage of a public square. Each round, you receive a police report describing a suspect. You must flag someone before the timer expires.

The twist: the AI data you are given is accurate. The bias is yours.

At the end, a recap screen shows everyone you flagged — innocent or guilty — and reveals the real reason behind each AI signal you acted on. The anxious woman was late to work. The man in the dark hoodie was coming from the gym. You had the data. The data wasn't wrong. But the conditions the system put you in made your decisions systematically biased.

---

## Game Mechanics

### Round Structure
The game consists of **5 rounds**. Each round:
- A police report appears describing a suspect by 2 attributes (e.g. *"dark clothing, appears agitated"*)
- 5–8 people move across the screen, each with a visible 3-icon HUD tag showing their mood, behaviour, and one physical descriptor
- You must click to flag one person before the timer runs out

| Round | Timer | People on screen | Ambiguity |
|-------|-------|-----------------|-----------|
| 1     | 15s   | 5               | Low — 1 clear match |
| 2     | 12s   | 6               | Medium — 2 plausible matches |
| 3     | 9s    | 7               | High — 3 plausible matches |
| 4     | 6s    | 8               | Very high + misleading mood data |
| 5     | 4s    | 8               | Near-impossible to read carefully |

### Ground Truth
Each round has a designated correct suspect who matches the police report fully if read carefully. Under time pressure, players tiebreak on secondary signals — mood tags, clothing colour, movement — which they share with innocent bystanders. The game records *which* signals the player actually acted on.

### HUD Tags
Each person on screen carries a floating 3-icon tag, always visible:

```
[MOOD] [BEHAVIOUR] [PHYSICAL]
e.g. [😰 anxious] [🏃 rushing] [🧥 dark coat]
```

Tags are AI-generated and accurate. They are not evidence of guilt.

### End Condition
The game ends after round 5. A **recap screen** displays:
- Every person you flagged across all rounds
- Whether they were the true suspect or innocent
- The real-world reason behind each AI signal that may have influenced your choice
- Your false positive rate

---

## Learning Goal

> After playing the game, the player should understand that accurate AI-generated data (mood, behaviour flags) can still produce systematically biased human decisions when combined with time pressure and ambiguous descriptions.

---

## Repository Structure

```
red-handed/
│
├── main.py                  # Entry point — run this to start the game
│
├── game/
│   ├── __init__.py
│   ├── game_loop.py         # Core loop: round management, timer, input handling
│   ├── round.py             # Round logic: suspect selection, attribute generation
│   ├── recap.py             # End screen: result display and reveal logic
│   └── constants.py         # Shared constants (timers, round count, screen size, etc.)
│
├── entities/
│   ├── __init__.py
│   ├── person.py            # Person entity: attributes, HUD tag, movement
│   └── suspect.py           # Suspect data class: report, ground truth, reveal text
│
├── data/
│   ├── suspects.json        # Round definitions: reports, true suspects, innocents, reveal texts
│   └── attributes.json      # Attribute pool: moods, behaviours, physical descriptors
│
├── assets/
│   ├── fonts/               # Any custom fonts
│   ├── icons/               # HUD tag icons (mood, behaviour, physical)
│   └── backgrounds/         # CCTV-style background images
│
├── ui/
│   ├── __init__.py
│   ├── hud.py               # HUD rendering: timer bar, round counter, police report panel
│   └── screens.py           # Title screen, recap screen, transitions
│
├── requirements.txt         # pygame (Python 3.14)
└── README.md
```

---

## Setup

**Requirements:** Python 3.14, pygame

```bash
# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py
```

---

## Ethical Context

This game was designed for an AI Ethics course to make the following argument tangible through play:

The problem with AI-assisted surveillance is not only that AI systems can be biased — it is that even an accurate, unbiased AI system can produce biased outcomes at the human decision layer. Mood detection that correctly identifies anxiety does not identify guilt. Behaviour flags that correctly identify erratic movement do not identify threat. When a human operator must act on this data under time pressure, the structural conditions of the system — not individual malice — produce the bias.

The game is designed so that false positives are not the player's fault. They are the system's fault.