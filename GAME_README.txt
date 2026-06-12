PAC-MAN — 42 Edition
====================

LAUNCH
------
Linux / macOS : double-click "pacman" or run ./pacman in a terminal.
Windows       : double-click pacman.exe.

The game reads config.json (same folder) on startup.
Missing or invalid values are replaced by safe defaults — the game
never crashes on a bad config.

CONTROLS
--------
Arrow keys / WASD   Move Pac-Man
P                   Pause / Resume
Esc                 Pause  |  Back  |  Quit confirmation
Enter / Y           Confirm selection or dialog
N / Backspace       Cancel dialog

CHEAT MODE  (hold LCtrl + key, in-game only)
--------------------------------------------
I   Toggle invincibility
F   Toggle ghost freeze
T   Toggle level-timer freeze
W   Toggle noclip (walk through walls)
E   Grant one extra life
↑   Speed Pac-Man up   (+25 %, max 200 %)
↓   Slow Pac-Man down  (-25 %, min  50 %)
L   Collect all pacgums (skip level)
C   Cycle visual palette

CONFIGURATION  (config.json)
----------------------------
highscore_filename   Path to the highscore JSON file   (default: highscore.json)
lives                Starting lives                     (default: 3)
pacgum               Pacgum count per level             (default: 42)
points_per_pacgum    Score per pacgum                   (default: 10)
points_per_super_pacgum  Score per super-pacgum         (default: 50)
points_per_ghost     Score per eaten ghost              (default: 200)
seed                 RNG seed for level 1               (default: 42)
level_max_time       Time limit per level in seconds    (default: 90)
level                Array of {width, height} objects   (min 10 entries)

Lines starting with # are treated as comments and ignored.

SCORING
-------
Eat a pacgum          +10 pts  (configurable)
Eat a super-pacgum    +50 pts  (configurable)
Eat a ghost           +200 pts (configurable)

HIGHSCORES
----------
Top-10 scores are saved in highscore.json after each game (win or lose).
Player names: max 10 alphanumeric characters and spaces.
