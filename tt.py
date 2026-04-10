#!/usr/bin/env python3
"""
tt - Terminal Touch Typing Tutor

A minimal, cross-platform terminal typing tutor with finger-specific lessons
covering all keys including the number row and symbols.

Usage:  python3 tt.py
Requires: Python 3.6+  (Windows: pip install windows-curses)
"""

import argparse
import curses
import json
import os
import random
import sys
import time

# Make ESC key responsive (default 1000ms delay is painful)
os.environ.setdefault("ESCDELAY", "25")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COLOR PAIR IDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C_CORRECT = 1
C_WRONG = 2
C_DIM = 3
C_TITLE = 4
C_ACCENT = 5
C_CURSOR = 6
C_HEADING = 7

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WORD POOL  (common English words for realistic practice)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORD_POOL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "word_pool.txt")
_WORD_POOL_CACHE = None


def load_word_pool():
    """Load practice words from disk and cache the normalized result."""
    global _WORD_POOL_CACHE
    if _WORD_POOL_CACHE is not None:
        return _WORD_POOL_CACHE

    words = []
    seen = set()
    try:
        with open(WORD_POOL_FILE, "r", encoding="utf-8") as fh:
            for raw_line in fh:
                word = raw_line.strip().lower()
                if not word or word.startswith("#") or word in seen:
                    continue
                words.append(word)
                seen.add(word)
    except OSError:
        _WORD_POOL_CACHE = ()
        return _WORD_POOL_CACHE

    _WORD_POOL_CACHE = tuple(words)
    return _WORD_POOL_CACHE

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LESSON DEFINITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LESSONS = [
    # ── Home Row ──────────────────────────────────────────────────────────
    {
        "name": "Home Row",
        "finger": "All fingers — home position",
        "keys": "a s d f g h j k l ; : '",
        "chars": "asdfghjkl;:'",
    },
    # ── Left Hand Fingers ─────────────────────────────────────────────────
    {
        "name": "Left Pinky",
        "finger": "Left pinky finger",
        "keys": "` ~ 1 ! q Q a A z Z",
        "chars": "`~1!qQaAzZ",
    },
    {
        "name": "Left Ring",
        "finger": "Left ring finger",
        "keys": "2 @ w W s S x X",
        "chars": "2@wWsSxX",
    },
    {
        "name": "Left Middle",
        "finger": "Left middle finger",
        "keys": "3 # e E d D c C",
        "chars": "3#eEdDcC",
    },
    {
        "name": "Left Index",
        "finger": "Left index finger",
        "keys": "4 $ 5 % r R t T f F g G v V b B",
        "chars": "4$5%rRtTfFgGvVbB",
    },
    # ── Right Hand Fingers ────────────────────────────────────────────────
    {
        "name": "Right Index",
        "finger": "Right index finger",
        "keys": "6 ^ 7 & y Y u U h H j J n N m M",
        "chars": "6^7&yYuUhHjJnNmM",
    },
    {
        "name": "Right Middle",
        "finger": "Right middle finger",
        "keys": "8 * i I k K , <",
        "chars": "8*iIkK,<",
    },
    {
        "name": "Right Ring",
        "finger": "Right ring finger",
        "keys": "9 ( o O l L . >",
        "chars": "9(oOlL.>",
    },
    {
        "name": "Right Pinky",
        "finger": "Right pinky finger",
        "keys": "0 ) - _ = + p P [ { ] } \\ | ; : ' \" / ?",
        "chars": "0)-_=+pP[{]}\\|;:'\"/?",
    },
    # ── Row-based ─────────────────────────────────────────────────────────
    {
        "name": "Top Row",
        "finger": "All fingers — top letter row",
        "keys": "q w e r t y u i o p [ ] { } \\ |",
        "chars": "qwertyuiop[]{}\\|",
    },
    {
        "name": "Bottom Row",
        "finger": "All fingers — bottom letter row",
        "keys": "z x c v b n m , . / < > ?",
        "chars": "zxcvbnm,./<>?",
    },
    {
        "name": "Number Row",
        "finger": "All fingers — number row",
        "keys": "` 1 2 3 4 5 6 7 8 9 0 - =",
        "chars": "`1234567890-=",
    },
    {
        "name": "Number Symbols",
        "finger": "All fingers — shifted number row",
        "keys": "~ ! @ # $ % ^ & * ( ) _ +",
        "chars": "~!@#$%^&*()_+",
    },
    {
        "name": "All Symbols",
        "finger": "All fingers — shifted keys",
        "keys": "All symbol & punctuation keys",
        "chars": "~!@#$%^&*()_+{}|:\"<>?`-=[]\\;',./",
    },
    {
        "name": "Home ↔ Top Row",
        "finger": "All fingers — row jumps",
        "keys": "Home row + top row",
        "chars": "asdfghjkl;:'qwertyuiop[]{}\\|",
        "alternating_groups": ["asdfghjkl;:'", "qwertyuiop[]{}\\|"],
        "hand_alternating_groups": {
            "left": ["asdfg", "qwert"],
            "right": ["hjkl;:'", "yuiop[]{}\\|"],
        },
    },
    {
        "name": "Home ↔ Bottom Row",
        "finger": "All fingers — row jumps",
        "keys": "Home row + bottom row",
        "chars": "asdfghjkl;:'zxcvbnm,./<>?",
        "alternating_groups": ["asdfghjkl;:'", "zxcvbnm,./<>?"],
        "hand_alternating_groups": {
            "left": ["asdfg", "zxcvb"],
            "right": ["hjkl;:'", "nm,./<>?"],
        },
    },
    {
        "name": "Home ↔ Number Row",
        "finger": "All fingers — row jumps",
        "keys": "Home row + number row",
        "chars": "asdfghjkl;:'`1234567890-=",
        "alternating_groups": ["asdfghjkl;:'", "`1234567890-="],
        "hand_alternating_groups": {
            "left": ["asdfg", "`12345"],
            "right": ["hjkl;:'", "67890-="],
        },
    },
    {
        "name": "Top ↔ Bottom Row",
        "finger": "All fingers — row jumps",
        "keys": "Top row + bottom row",
        "chars": "qwertyuiop[]{}\\|zxcvbnm,./<>?",
        "alternating_groups": ["qwertyuiop[]{}\\|", "zxcvbnm,./<>?"],
        "hand_alternating_groups": {
            "left": ["qwert", "zxcvb"],
            "right": ["yuiop[]{}\\|", "nm,./<>?"],
        },
    },
    {
        "name": "Top ↔ Number Row",
        "finger": "All fingers — row jumps",
        "keys": "Top row + number row",
        "chars": "qwertyuiop[]{}\\|`1234567890-=",
        "alternating_groups": ["qwertyuiop[]{}\\|", "`1234567890-="],
        "hand_alternating_groups": {
            "left": ["qwert", "`12345"],
            "right": ["yuiop[]{}\\|", "67890-="],
        },
    },
    {
        "name": "Bottom ↔ Number Row",
        "finger": "All fingers — row jumps",
        "keys": "Bottom row + number row",
        "chars": "zxcvbnm,./<>?`1234567890-=",
        "alternating_groups": ["zxcvbnm,./<>?", "`1234567890-="],
        "hand_alternating_groups": {
            "left": ["zxcvb", "`12345"],
            "right": ["nm,./<>?", "67890-="],
        },
    },
    # ── Mixed Practice ────────────────────────────────────────────────────
    {
        "name": "Common Words",
        "finger": "All fingers",
        "keys": "All letters",
        "chars": "abcdefghijklmnopqrstuvwxyz",
        "words_only": True,
    },
    {
        "name": "Full Keyboard",
        "finger": "All fingers — everything",
        "keys": "All keys",
        "chars": ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                  "1234567890~!@#$%^&*()_+{}|:\"<>?`-=[]\\;',./"),
    },
]


PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             ".tt_progress.json")
SPARKLINE_BLOCKS = "▁▂▃▄▅▆▇█"
PROGRESS_PLOT_LABEL_W = 5
PROGRESS_PLOT_DATA_COL = PROGRESS_PLOT_LABEL_W + 1
DEFAULT_LAST_SELECTED = 0


def _normalize_lesson_index(selected, total=None):
    """Clamp a lesson index into the valid LESSONS range."""
    if total is None:
        total = len(LESSONS)
    try:
        total = int(total)
    except (TypeError, ValueError):
        total = len(LESSONS)
    if total <= 0:
        return 0

    try:
        selected = int(selected)
    except (TypeError, ValueError):
        return 0
    return min(max(0, selected), total - 1)


def calculate_session_stats(total_correct, total_typed, elapsed):
    """Return a normalized stats dict for a completed practice session."""
    elapsed = max(float(elapsed), 0.0)
    wpm = (total_typed / 5.0) / (elapsed / 60.0) if elapsed > 0 else 0.0
    accuracy = (total_correct / total_typed * 100.0) if total_typed > 0 else 0.0
    return {
        "wpm": wpm,
        "accuracy": accuracy,
        "errors": max(0, total_typed - total_correct),
        "chars": max(0, total_typed),
        "correct": max(0, total_correct),
        "elapsed": elapsed,
    }


def load_progress_history():
    """Load persistent lesson performance history from disk."""
    default_history = {"lessons": {}, "last_selected": DEFAULT_LAST_SELECTED}
    if not os.path.exists(PROGRESS_FILE):
        return dict(default_history)

    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, json.JSONDecodeError):
        return dict(default_history)

    if not isinstance(data, dict):
        return dict(default_history)

    lessons = data.get("lessons", {})
    if not isinstance(lessons, dict):
        lessons = {}

    normalized = {}
    for lesson_name, sessions in lessons.items():
        if isinstance(lesson_name, str) and isinstance(sessions, list):
            normalized[lesson_name] = [entry for entry in sessions if isinstance(entry, dict)]

    return {
        "lessons": normalized,
        "last_selected": _normalize_lesson_index(
            data.get("last_selected", DEFAULT_LAST_SELECTED)
        ),
    }


def save_progress_history(history):
    """Persist lesson performance history to disk."""
    if not isinstance(history, dict):
        history = {}

    lessons = history.get("lessons", {})
    if not isinstance(lessons, dict):
        lessons = {}

    payload = {
        "lessons": lessons,
        "last_selected": _normalize_lesson_index(
            history.get("last_selected", DEFAULT_LAST_SELECTED)
        ),
    }

    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
    except OSError:
        pass


def load_last_selected():
    """Return the most recently selected lesson index."""
    return load_progress_history()["last_selected"]


def save_last_selected(selected):
    """Persist the most recently selected lesson index."""
    history = load_progress_history()
    history["last_selected"] = _normalize_lesson_index(selected)
    save_progress_history(history)
    return history["last_selected"]


def list_lessons(stream=None):
    """Print a numbered lesson list."""
    if stream is None:
        stream = sys.stdout

    for number, lesson in enumerate(LESSONS, start=1):
        print(f"{number:>2}. {lesson['name']}", file=stream)


def resolve_lesson_selector(selector, default=None):
    """Resolve a CLI lesson selector into a 0-based lesson index."""
    if selector is None or str(selector).strip() == "":
        if default is None:
            return None
        return _normalize_lesson_index(default, len(LESSONS))

    selector = str(selector).strip()
    if selector.isdigit():
        number = int(selector)
        if 1 <= number <= len(LESSONS):
            return number - 1
        raise ValueError(f"Lesson number must be between 1 and {len(LESSONS)}.")

    selector_lower = selector.lower()
    for idx, lesson in enumerate(LESSONS):
        if selector_lower == lesson["name"].lower():
            return idx

    match = _find_best_match(selector_lower, len(LESSONS))
    if match >= 0:
        return match

    raise ValueError(
        f"No lesson matches '{selector}'. Use --list-lessons to see valid options."
    )


def parse_args(argv=None):
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Terminal touch typing tutor with quick-launch support."
    )
    parser.add_argument(
        "-l", "--lesson",
        help="Lesson number, exact name, or search text.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Start practice immediately using --lesson or the last selected lesson.",
    )
    parser.add_argument(
        "--list-lessons",
        action="store_true",
        help="Print numbered lessons and exit.",
    )
    return parser.parse_args(argv)


def build_startup_config(args, default_selected=None):
    """Build initial menu/launch state from parsed CLI args."""
    if default_selected is None:
        default_selected = load_last_selected()

    selected = resolve_lesson_selector(args.lesson, default_selected)
    return {
        "initial_selected": selected,
        "start_lesson": selected if args.quick else None,
    }


def record_lesson_session(lesson_name, session_stats):
    """Append a completed session to the lesson's persistent history."""
    history = load_progress_history()
    lesson_history = history.setdefault("lessons", {}).setdefault(lesson_name, [])
    lesson_history.append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "wpm": round(session_stats["wpm"], 2),
        "accuracy": round(session_stats["accuracy"], 2),
        "errors": int(session_stats["errors"]),
        "chars": int(session_stats["chars"]),
        "correct": int(session_stats["correct"]),
        "elapsed": round(session_stats["elapsed"], 2),
    })
    save_progress_history(history)
    return lesson_history


def compress_series(values, width):
    """Compress a series to fit within *width* points."""
    if width <= 0 or not values:
        return []
    if len(values) <= width:
        return list(values)

    compressed = []
    bucket_size = len(values) / float(width)
    for i in range(width):
        start = int(i * bucket_size)
        end = max(start + 1, int((i + 1) * bucket_size))
        bucket = values[start:end]
        compressed.append(sum(bucket) / len(bucket))
    return compressed


def make_sparkline(values, width):
    """Render a Unicode sparkline for *values* constrained to *width*."""
    points = compress_series(values, width)
    if not points:
        return ""

    low = min(points)
    high = max(points)
    if high - low < 1e-9:
        return "▅" * len(points)

    scale = len(SPARKLINE_BLOCKS) - 1
    chars = []
    for value in points:
        idx = int(round((value - low) / (high - low) * scale))
        idx = max(0, min(scale, idx))
        chars.append(SPARKLINE_BLOCKS[idx])
    return "".join(chars)


def build_wpm_plot_lines(values, width, height):
    """Build a multi-line ASCII bar chart for WPM history."""
    if width <= 12 or height < 3:
        return []

    if not values:
        return [fit_text("WPM: no history yet", width)]

    label_w = PROGRESS_PLOT_LABEL_W
    plot_w = width - label_w - 2
    points = compress_series(values, plot_w)
    if not points:
        return [fit_text("WPM: no history yet", width)]

    max_wpm = max(points)
    min_wpm = min(points)
    latest_wpm = points[-1]

    # Chart dimensions
    chart_height = height - 2 # Reserve 1 for title, 1 for x-axis/latest
    if chart_height < 1:
        chart_height = 1
        
    min_y = 0
    max_y = max(max_wpm * 1.1, 10)  # 10% headroom

    lines = [fit_text("WPM Progress:", width)]
    
    blocks = "  ▂▃▄▅▆▇█"

    for row in range(chart_height - 1, -1, -1):
        row_min_y = min_y + (max_y - min_y) * (row / chart_height)
        row_max_y = min_y + (max_y - min_y) * ((row + 1) / chart_height)
        
        if row == chart_height - 1:
            label = f"{int(max_y):>4} |"
        elif row == 0:
            label = f"{int(min_y):>4} |"
        else:
            label = "     |"
            
        row_chars = []
        for p in points:
            if p >= row_max_y:
                row_chars.append("█")
            elif p <= row_min_y:
                row_chars.append(" ")
            else:
                fraction = (p - row_min_y) / (row_max_y - row_min_y)
                idx = int(fraction * 8)
                idx = max(0, min(8, idx))
                row_chars.append(blocks[idx])
                
        lines.append(fit_text(label + "".join(row_chars), width))

    # Add x-axis line
    axis_line = "     +" + "-" * len(points)
    latest_str = f" latest: {latest_wpm:.1f}"
    if len(axis_line) + len(latest_str) <= width:
        axis_line += latest_str
        
    lines.append(fit_text(axis_line, width))

    return lines


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEXT GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def words_for_charset(chars):
    """Return cached practice words whose letters are all in *chars*."""
    allowed = set(chars.lower())
    return [w for w in load_word_pool() if all(c in allowed for c in w)]


def generate_practice(lesson, width=55, num_lines=4):
    """Build practice lines from a lesson's character set."""
    width = max(1, width)
    chars = lesson["chars"]

    lower  = [c for c in chars if c.islower()]
    upper  = [c for c in chars if c.isupper()]
    digits = [c for c in chars if c.isdigit()]
    syms   = [c for c in chars if not c.isalnum()]

    fragments = []

    # ── Alternating row-jump mode ──
    if lesson.get("hand_alternating_groups"):
        hand_groups = {}
        for hand, groups in lesson["hand_alternating_groups"].items():
            normalized_groups = [list(group) for group in groups if group]
            if len(normalized_groups) >= 2:
                hand_groups[hand] = normalized_groups[:2]

        hands = [hand for hand, groups in hand_groups.items() if groups[0] and groups[1]]
        if hands:
            for _ in range(32):
                n = random.randint(2, 6)
                next_group_idx = {
                    hand: random.randrange(2)
                    for hand in hands
                }
                frag_chars = []
                for _ in range(n):
                    hand = random.choice(hands)
                    group_idx = next_group_idx[hand]
                    frag_chars.append(random.choice(hand_groups[hand][group_idx]))
                    next_group_idx[hand] = 1 - group_idx
                fragments.append("".join(frag_chars))

    elif lesson.get("alternating_groups"):
        groups = [list(group) for group in lesson["alternating_groups"] if group]
        if len(groups) >= 2:
            for _ in range(32):
                n = random.randint(2, 6)
                start_group = random.randrange(len(groups))
                frag_chars = []
                for i in range(n):
                    group = groups[(start_group + i) % len(groups)]
                    frag_chars.append(random.choice(group))
                fragments.append("".join(frag_chars))

    # ── Words-only mode (Common Words lesson) ──
    elif lesson.get("words_only"):
        pool = list(load_word_pool())
        random.shuffle(pool)
        fragments = pool[:60]
    else:
        # Real English words matching the charset
        matching = words_for_charset(chars)
        if matching:
            fragments += [random.choice(matching) for _ in range(22)]

        # Random letter combos
        if lower:
            for _ in range(12):
                n = random.randint(2, 5)
                fragments.append("".join(random.choice(lower) for _ in range(n)))

        # Capitalised combos
        if upper and lower:
            for _ in range(5):
                n = random.randint(2, 4)
                w = random.choice(upper) + "".join(random.choice(lower) for _ in range(n - 1))
                fragments.append(w)

        # Digit sequences
        if digits:
            for _ in range(8):
                n = random.randint(1, 4)
                fragments.append("".join(random.choice(digits) for _ in range(n)))

        # Symbol sequences
        if syms:
            for _ in range(8):
                n = random.randint(1, 3)
                fragments.append("".join(random.choice(syms) for _ in range(n)))

        # Fallback: random from full charset
        all_c = list(chars)
        if len(fragments) < 12:
            for _ in range(20):
                n = random.randint(2, 4)
                fragments.append("".join(random.choice(all_c) for _ in range(n)))

    random.shuffle(fragments)

    # Ensure no fragment is wider than the available practice width.
    # Without this, narrow terminals can hide part of a fragment while the
    # input logic still expects the user to type the invisible remainder.
    wrapped_fragments = []
    for frag in fragments:
        if len(frag) <= width:
            wrapped_fragments.append(frag)
            continue
        for i in range(0, len(frag), width):
            wrapped_fragments.append(frag[i:i + width])
    fragments = wrapped_fragments

    # ── Wrap into lines ──
    lines, line = [], ""
    for frag in fragments:
        if line and len(line) + 1 + len(frag) > width:
            lines.append(line)
            line = frag
            if len(lines) >= num_lines:
                break
        else:
            line = (line + " " + frag) if line else frag
    if line and len(lines) < num_lines:
        lines.append(line)

    # Pad if needed
    all_c = list(chars)
    while len(lines) < num_lines:
        frags = ["".join(random.choice(all_c) for _ in range(random.randint(2, 5)))
                  for _ in range(12)]
        lines.append(" ".join(frags)[:width])

    return lines


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CURSES HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_CORRECT, curses.COLOR_GREEN, -1)
    curses.init_pair(C_WRONG, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(C_DIM, 8, -1)          # dark grey
    curses.init_pair(C_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(C_ACCENT, curses.COLOR_YELLOW, -1)
    curses.init_pair(C_CURSOR, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(C_HEADING, curses.COLOR_MAGENTA, -1)


def safe_addstr(win, y, x, text, attr=0):
    """Write text, silently ignoring out-of-bounds writes."""
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x >= w:
        return
    max_len = w - x - 1
    if max_len <= 0:
        return
    try:
        win.addstr(y, x, text[:max_len], attr)
    except curses.error:
        pass


def fit_text(text, width):
    """Clip text to *width*, adding ellipsis when there is room."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def format_progress_sparkline(label, plot, width, suffix=""):
    """Render a sparkline row aligned to the progress plot's data column."""
    prefix = label.ljust(PROGRESS_PLOT_DATA_COL)
    suffix_text = f"  {suffix}" if suffix else ""
    return fit_text(f"{prefix}{plot}{suffix_text}", width)


def practice_left_x(width):
    """Return the left margin for practice text based on terminal width."""
    return 2 if width < 12 else 4


def draw_hline(win, y, x, width, char="─"):
    safe_addstr(win, y, x, char * width, curses.color_pair(C_DIM))



def _focused_view_start(total_items, focus_idx, visible_count):
    """Return a viewport start that keeps *focus_idx* visible."""
    if total_items <= 0 or visible_count <= 0:
        return 0
    visible_count = min(total_items, visible_count)
    max_start = total_items - visible_count
    return min(max(0, focus_idx - visible_count // 2), max_start)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MENU SCREEN  (scrollable)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MENU_SECTIONS = [
    ("HOME ROW", [0]),
    ("LEFT HAND", [1, 2, 3, 4]),
    ("RIGHT HAND", [5, 6, 7, 8]),
    ("ROWS", [9, 10, 11, 12, 13]),
    ("ROW JUMPS", [14, 15, 16, 17, 18, 19]),
    ("PRACTICE", [20, 21]),
]


def _build_menu_rows():
    """Pre-build the list of menu rows as (type, data) tuples."""
    rows = []
    for section_name, indices in MENU_SECTIONS:
        rows.append(("heading", section_name))
        for idx in indices:
            rows.append(("lesson", idx))
        rows.append(("blank", None))
    return rows

_MENU_ROWS = _build_menu_rows()


def _selected_menu_pos(selected):
    """Return the index into _MENU_ROWS that corresponds to the lesson *selected*."""
    for i, (kind, data) in enumerate(_MENU_ROWS):
        if kind == "lesson" and data == selected:
            return i
    return 0


def draw_menu(stdscr, selected, input_buf=""):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    show_title = h >= 6
    show_header_rule = h >= 7
    show_footer = (bool(input_buf) and h >= 2) or (not input_buf and h >= 5)
    show_footer_rule = show_footer and h >= 7

    top_y = 0
    if show_title:
        title = "TERMINAL TYPING TUTOR"
        safe_addstr(stdscr, top_y, 2, title, curses.color_pair(C_TITLE) | curses.A_BOLD)
        top_y += 1
    if show_header_rule:
        draw_hline(stdscr, top_y, 2, min(len("TERMINAL TYPING TUTOR"), w - 4))
        top_y += 1

    bottom_y = h
    if show_footer_rule:
        bottom_y -= 1
    if show_footer:
        bottom_y -= 1

    avail = max(1, bottom_y - top_y)
    total_rows = len(_MENU_ROWS)
    sel_pos = _selected_menu_pos(selected)
    scroll = _focused_view_start(total_rows, sel_pos, avail)

    for vi in range(avail):
        ri = scroll + vi
        if ri >= total_rows:
            break
        y = top_y + vi
        kind, data = _MENU_ROWS[ri]
        if kind == "heading":
            safe_addstr(stdscr, y, 2, data, curses.color_pair(C_HEADING) | curses.A_BOLD)
        elif kind == "lesson":
            lesson = LESSONS[data]
            num = data + 1
            marker = "›" if data == selected else " "
            attr = curses.A_REVERSE if data == selected else 0
            label = fit_text(f" {marker} {num:>2}. {lesson['name']}", max(1, w - 4))
            safe_addstr(stdscr, y, 2, label, attr | curses.color_pair(C_TITLE if data == selected else 0))

            keys_col = max(2 + len(label) + 2, min(26, max(2, w // 2)))
            max_keys = w - keys_col - 2
            if max_keys >= 4 and avail >= 3:
                keys_preview = fit_text(lesson["keys"], max_keys)
                safe_addstr(stdscr, y, keys_col, keys_preview, curses.color_pair(C_DIM))
        # "blank" rows are simply left empty

    # Scroll indicators
    if avail >= 1 and scroll > 0:
        safe_addstr(stdscr, top_y, w - 3, "▲", curses.color_pair(C_DIM))
    if avail >= 1 and scroll + avail < total_rows:
        safe_addstr(stdscr, top_y + avail - 1, w - 3, "▼", curses.color_pair(C_DIM))

    if show_footer_rule:
        draw_hline(stdscr, h - 2, 2, min(40, w - 4))

    if show_footer:
        footer_y = h - 1
        if input_buf:
            prompt = fit_text(f"Search: {input_buf}_", max(1, w - 4))
            safe_addstr(stdscr, footer_y, 2, prompt,
                        curses.color_pair(C_ACCENT) | curses.A_BOLD)
            hint_x = 2 + len(prompt) + 2
            hint_w = w - hint_x - 1
            if hint_w >= 6:
                safe_addstr(stdscr, footer_y, hint_x, fit_text("(ESC to clear)", hint_w),
                            curses.color_pair(C_DIM))
        else:
            safe_addstr(stdscr, footer_y, 2,
                        fit_text("↑↓ Nav  Enter Select  Type to search  Q Quit", max(1, w - 4)),
                        curses.color_pair(C_DIM))

    stdscr.refresh()


def _match_lesson(query, idx):
    """Score how well *query* matches lesson at *idx*.  Higher = better.  0 = no match."""
    lesson = LESSONS[idx]
    q = query.lower()
    num_str = str(idx + 1)
    name = lesson["name"].lower()
    keys = lesson.get("keys", "").lower()
    chars = lesson.get("chars", "").lower()

    # Exact number match is top priority
    if q == num_str:
        return 1000
    # Number prefix
    if num_str.startswith(q) and q.isdigit():
        return 900
    # Exact name match
    if q == name:
        return 800
    # Name starts with query
    if name.startswith(q):
        return 700
    # Query is a substring of name
    if q in name:
        return 600
    # Query is a substring of keys
    if q in keys:
        return 500
    # Query is a substring of chars
    if q in chars:
        return 400
    # All query chars exist in name+keys+chars
    searchable = name + " " + keys + " " + chars
    if all(c in searchable for c in q):
        return 300
    return 0


def _find_best_match(query, total):
    """Return the index of the best matching lesson, or -1."""
    if not query:
        return -1
    best_score = 0
    best_idx = -1
    for i in range(total):
        score = _match_lesson(query, i)
        if score > best_score:
            best_score = score
            best_idx = i
    return best_idx


def run_menu(stdscr, initial_selected=0):
    total = len(LESSONS)
    selected = _normalize_lesson_index(initial_selected, total)
    input_buf = ""

    while True:
        draw_menu(stdscr, selected, input_buf)
        key = stdscr.getch()

        if key == curses.KEY_RESIZE:
            continue

        # ESC clears buffer, or quits if buffer empty
        if key == 27:
            if input_buf:
                input_buf = ""
            else:
                return None
            continue

        if key in (ord('q'), ord('Q')) and not input_buf:
            return None
        elif key == curses.KEY_UP or (key == ord('k') and not input_buf):
            input_buf = ""
            selected = (selected - 1) % total
        elif key == curses.KEY_DOWN or (key == ord('j') and not input_buf):
            input_buf = ""
            selected = (selected + 1) % total
        elif key in (curses.KEY_ENTER, 10, 13, ord(' ')):
            if input_buf:
                input_buf = ""
            return selected
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            input_buf = input_buf[:-1]
            match = _find_best_match(input_buf, total)
            if match >= 0:
                selected = match
        elif 32 <= key <= 126:
            input_buf += chr(key)
            match = _find_best_match(input_buf, total)
            if match >= 0:
                selected = match


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TYPING PRACTICE SCREEN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def draw_practice(stdscr, lesson, lines, typed, cur_line, cur_col,
                  start_time, total_correct, total_typed):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # Stats string (used in all header modes)
    elapsed = time.time() - start_time if start_time else 0
    if elapsed > 0 and total_typed > 0:
        wpm = (total_typed / 5.0) / (elapsed / 60.0)
        wpm_str = f"WPM: {wpm:.0f}"
    else:
        wpm_str = "WPM: --"
    acc = (total_correct / total_typed * 100) if total_typed > 0 else 100.0
    acc_str = f"Acc: {acc:.0f}%"
    errors = total_typed - total_correct
    stats = f"{wpm_str}  {acc_str}  Err: {errors}"

    base_y = 0
    if h >= 18:
        # Full layout
        safe_addstr(stdscr, 0, 2, "TERMINAL TYPING TUTOR", curses.color_pair(C_TITLE) | curses.A_BOLD)
        safe_addstr(stdscr, 0, max(2, w - len(stats) - 2), stats, curses.color_pair(C_ACCENT))
        draw_hline(stdscr, 1, 2, min(60, w - 4))
        safe_addstr(stdscr, 2, 2, f"Lesson: {lesson['name']}", curses.color_pair(C_TITLE))
        finger_col = min(28, w // 2)
        safe_addstr(stdscr, 2, finger_col, f"({lesson['finger']})", curses.color_pair(C_DIM))
        keys_str = fit_text(f"Keys: {lesson['keys']}", max(1, w - 4))
        safe_addstr(stdscr, 3, 2, keys_str, curses.color_pair(C_DIM))
        draw_hline(stdscr, 4, 2, min(60, w - 4))
        base_y = 6
    elif h >= 10:
        # Medium: title + compact info
        safe_addstr(stdscr, 0, 2, "TERMINAL TYPING TUTOR", curses.color_pair(C_TITLE) | curses.A_BOLD)
        safe_addstr(stdscr, 0, max(2, w - len(stats) - 2), stats, curses.color_pair(C_ACCENT))
        draw_hline(stdscr, 1, 2, min(60, w - 4))
        info = fit_text(f"{lesson['name']}  Keys: {lesson['keys']}", max(1, w - 4))
        safe_addstr(stdscr, 2, 2, info, curses.color_pair(C_TITLE))
        base_y = 4
    elif h >= 6:
        # Small: one info line with stats on the right
        info = f"{lesson['name']}"
        safe_addstr(stdscr, 0, 1, info, curses.color_pair(C_TITLE))
        safe_addstr(stdscr, 0, max(len(info) + 3, w - len(stats) - 1), stats, curses.color_pair(C_ACCENT))
        base_y = 2

    show_footer = h >= 4
    show_progress = h >= 5
    footer_rows = 1 if show_footer else 0
    progress_rows = 1 if show_progress else 0
    practice_h = max(1, h - base_y - progress_rows - footer_rows)
    spacing = 2 if practice_h >= len(lines) * 2 - 1 else 1
    visible_count = min(len(lines), max(1, 1 + max(0, practice_h - 1) // spacing))
    first_visible_line = _focused_view_start(len(lines), cur_line, visible_count)

    line_x = practice_left_x(w)

    # Practice lines (keep the active typing line visible as space shrinks)
    for screen_idx, li in enumerate(range(first_visible_line,
                                         min(len(lines), first_visible_line + visible_count))):
        y = base_y + screen_idx * spacing
        if y >= base_y + practice_h or y >= h:
            break
        line = lines[li]
        for ci, ch in enumerate(line):
            x = line_x + ci
            if x >= w - 1:
                break

            if li < cur_line or (li == cur_line and ci < cur_col):
                typed_char = typed[li][ci] if ci < len(typed[li]) else None
                if typed_char == ch:
                    attr = curses.color_pair(C_CORRECT)
                else:
                    attr = curses.color_pair(C_WRONG)
                    ch = typed_char if typed_char else ch
                safe_addstr(stdscr, y, x, ch, attr)
            elif li == cur_line and ci == cur_col:
                safe_addstr(stdscr, y, x, ch, curses.color_pair(C_CURSOR))
            else:
                safe_addstr(stdscr, y, x, ch, curses.color_pair(C_DIM))

        if li == cur_line and cur_col == len(line):
            cursor_x = line_x + len(line)
            if cursor_x < w - 1:
                safe_addstr(stdscr, y, cursor_x, " ", curses.color_pair(C_CURSOR))

    # Progress bar
    total_chars = sum(len(l) for l in lines)
    typed_chars = sum(len(t) for t in typed)
    pct = typed_chars / total_chars if total_chars else 0
    if show_progress:
        bar_y = h - footer_rows - 1
        bar_w = min(40, w - line_x - 4)
        if bar_w > 4:
            filled = int(pct * bar_w)
            bar = "█" * filled + "░" * (bar_w - filled)
            safe_addstr(stdscr, bar_y, line_x, bar, curses.color_pair(C_ACCENT))
            safe_addstr(stdscr, bar_y, line_x + bar_w + 1, f"{pct*100:.0f}%", curses.color_pair(C_DIM))

    if show_footer:
        safe_addstr(stdscr, h - 1, 2,
                    fit_text("ESC: Menu  TAB: Restart  Space/Enter: Next line", max(1, w - 4)),
                    curses.color_pair(C_DIM))

    stdscr.refresh()


def _build_results_lines(w, h, lesson_name, session_stats, lesson_history):
    """Build adaptive results-screen lines, including historical progress."""
    wpm = session_stats["wpm"]
    acc = session_stats["accuracy"]
    errors = session_stats["errors"]
    elapsed = session_stats["elapsed"]
    total_typed = session_stats["chars"]
    mins = int(elapsed) // 60
    secs = int(elapsed) % 60

    if acc >= 98 and wpm >= 60:
        rating = "★★★ Excellent!"
    elif acc >= 95 and wpm >= 40:
        rating = "★★  Great job!"
    elif acc >= 90:
        rating = "★   Good, keep practicing!"
    else:
        rating = "    Keep at it!"

    session_count = len(lesson_history)
    history_wpm = [entry.get("wpm", 0.0) for entry in lesson_history]
    history_acc = [entry.get("accuracy", 0.0) for entry in lesson_history]
    best_wpm = max(history_wpm) if history_wpm else 0.0
    avg_wpm = sum(history_wpm) / len(history_wpm) if history_wpm else 0.0
    best_acc = max(history_acc) if history_acc else 0.0
    avg_acc = sum(history_acc) / len(history_acc) if history_acc else 0.0

    max_text_w = max(1, w - 4)
    plot_w = max(8, min(48, max_text_w - 12))
    wpm_plot = make_sparkline(history_wpm, plot_w) or "·"
    acc_plot = make_sparkline(history_acc, plot_w) or "·"

    title_attr = curses.color_pair(C_TITLE) | curses.A_BOLD
    accent_attr = curses.color_pair(C_ACCENT) | curses.A_BOLD
    dim_attr = curses.color_pair(C_DIM)

    # ── Compact layout (h < 13): priority-threshold progressive content ──
    # Each element has a threshold = minimum h at which it appears.
    # Thresholds are set so total included lines == h at every height 1-12,
    # with no trailing blank spacer row.
    if h < 13:
        sparkline_text = format_progress_sparkline("WPM:", wpm_plot, max_text_w,
                                                   f"latest {wpm:.1f}")
        elements = [
            (3, "RESULTS", title_attr),
            (6, fit_text(lesson_name, max_text_w), dim_attr),
            (1, fit_text(f"WPM {wpm:.1f}  Acc {acc:.1f}%  Err {errors}", max_text_w), accent_attr),
            (9, fit_text(rating, max_text_w), accent_attr),
            (12, "PROGRESS", title_attr),
            (4, fit_text(f"Sessions {session_count}  Best {best_wpm:.1f} WPM", max_text_w), dim_attr),
            (10, fit_text(f"Best Acc: {best_acc:.1f}%   Avg Acc: {avg_acc:.1f}%", max_text_w), dim_attr),
            (5, sparkline_text, curses.color_pair(C_ACCENT)),
            (7, format_progress_sparkline("Acc:", acc_plot, max_text_w), dim_attr),
            (8, "─" * min(30, w - 3), dim_attr),
            (11, fit_text(f"Time: {mins}:{secs:02d}  Chars: {total_typed}", max_text_w), dim_attr),
            (2, fit_text("R: Retry  M: Menu  Q: Quit", max_text_w), dim_attr),
        ]
        return [(text, attr) for min_h, text, attr in elements if h >= min_h]

    # ── Full layout (h >= 13): detailed stats + WPM chart ──
    header = [
        ("RESULTS", title_attr),
        (fit_text(f"Lesson:  {lesson_name}", max_text_w), dim_attr),
        (fit_text(f"WPM:     {wpm:.1f}", max_text_w), accent_attr),
        (fit_text(f"Accuracy:{acc:.1f}%", max_text_w), accent_attr),
        (fit_text(f"Errors:  {errors}   Time: {mins}:{secs:02d}   Chars: {total_typed}", max_text_w), dim_attr),
        (fit_text(rating, max_text_w), accent_attr),
    ]
    if h >= 16:
        header.append(("", 0))
    header.extend([
        ("PROGRESS", title_attr),
        (fit_text(f"Sessions: {session_count}   Best WPM: {best_wpm:.1f}   Avg WPM: {avg_wpm:.1f}", max_text_w), dim_attr),
        (fit_text(f"Best Acc: {best_acc:.1f}%   Avg Acc: {avg_acc:.1f}%", max_text_w), dim_attr),
    ])

    footer = [
        ("─" * min(30, w - 3), dim_attr),
        (fit_text("R: Retry  M: Menu  Q: Quit", max_text_w), dim_attr),
    ]

    sparkline_text = format_progress_sparkline("WPM:", wpm_plot, max_text_w,
                                               f"latest {wpm:.1f}")
    acc_trend_text = format_progress_sparkline("Acc:", acc_plot, max_text_w)

    vis_h = h - len(header) - len(footer)
    lines = list(header)

    if vis_h >= 4:
        # Bar chart (vis_h-1 rows) + acc trend
        wpm_plot_lines = build_wpm_plot_lines(history_wpm, max_text_w, vis_h - 1)
        if wpm_plot_lines:
            for pl in wpm_plot_lines:
                lines.append((pl, curses.color_pair(C_ACCENT)))
        else:
            lines.append((sparkline_text, curses.color_pair(C_ACCENT)))
        lines.append((acc_trend_text, dim_attr))
    elif vis_h == 3:
        # Use a labeled sparkline summary so h=14 degrades monotonically into h=13
        # without dropping and then reintroducing the accuracy trend.
        lines.append((fit_text("WPM Progress:", max_text_w), curses.color_pair(C_ACCENT)))
        lines.append((sparkline_text, curses.color_pair(C_ACCENT)))
        lines.append((acc_trend_text, dim_attr))
    elif vis_h == 2:
        # Sparkline + acc trend
        lines.append((sparkline_text, curses.color_pair(C_ACCENT)))
        lines.append((acc_trend_text, dim_attr))
    elif vis_h >= 1:
        # Sparkline only
        lines.append((sparkline_text, curses.color_pair(C_ACCENT)))

    lines.extend(footer)
    return lines


def draw_results(stdscr, lesson_name, session_stats, lesson_history):
    """Show results screen with persistent progress history."""
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        for i, (text, attr) in enumerate(_build_results_lines(
                w, h, lesson_name, session_stats, lesson_history)):
            if i >= h:
                break
            safe_addstr(stdscr, i, 2, text, attr)

        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        if key in (ord('r'), ord('R')):
            return "retry"
        if key in (ord('m'), ord('M'), 27):
            return "menu"
        if key in (ord('q'), ord('Q')):
            return "quit"


def run_practice(stdscr, lesson):
    """Main typing practice loop.  Returns: 'menu', 'retry', or 'quit'."""
    h, w = stdscr.getmaxyx()
    line_width = min(55, max(1, w - practice_left_x(w) - 1))
    # Adapt number of practice lines to terminal height
    num_lines = 4
    if h < 18:
        num_lines = 3
    if h < 14:
        num_lines = 2
    if h < 12:
        num_lines = 1
    lines = generate_practice(lesson, width=line_width, num_lines=num_lines)
    lines = [line + (" " if i < len(lines) - 1 else "")
             for i, line in enumerate(lines)]

    typed = [[] for _ in lines]
    cur_line = 0
    cur_col = 0
    start_time = None
    total_correct = 0
    total_typed = 0

    curses.curs_set(0)  # hide hardware cursor

    def finish_session():
        elapsed = time.time() - start_time if start_time else 1
        session_stats = calculate_session_stats(total_correct,
                                                total_typed,
                                                elapsed)
        lesson_history = record_lesson_session(lesson["name"],
                                               session_stats)
        return draw_results(stdscr, lesson["name"], session_stats,
                            lesson_history)

    while True:
        draw_practice(stdscr, lesson, lines, typed, cur_line, cur_col,
                      start_time, total_correct, total_typed)
        key = stdscr.getch()

        if key == curses.KEY_RESIZE:
            continue

        # ── Special keys ──
        if key == 27:  # ESC
            return "menu"
        if key == 9:   # TAB → restart
            return "retry"

        if cur_line >= len(lines):
            continue

        # ── Backspace (works across lines, including the trailing space) ──
        if key in (curses.KEY_BACKSPACE, 127, 8):
            if cur_col > 0:
                cur_col -= 1
                removed = typed[cur_line].pop()
                total_typed -= 1
                if removed == lines[cur_line][cur_col]:
                    total_correct -= 1
            elif cur_line > 0:
                cur_line -= 1
                cur_col = len(typed[cur_line]) - 1
                removed = typed[cur_line].pop()
                total_typed -= 1
                if removed == lines[cur_line][cur_col]:
                    total_correct -= 1
            continue

        if cur_col >= len(lines[cur_line]):
            continue

        ch = None
        if key in (curses.KEY_ENTER, 10, 13):
            if lines[cur_line][cur_col] == " ":
                ch = " "
        elif 32 <= key <= 126:
            ch = chr(key)

        if ch is None:
            continue

        if start_time is None:
            start_time = time.time()

        expected = lines[cur_line][cur_col]
        typed[cur_line].append(ch)
        total_typed += 1
        if ch == expected:
            total_correct += 1

        cur_col += 1
        if cur_col >= len(lines[cur_line]):
            cur_line += 1
            cur_col = 0
            if cur_line >= len(lines):
                return finish_session()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_selected_lesson(stdscr, selected):
    """Run the selected lesson until the user returns to menu or quits."""
    selected = _normalize_lesson_index(selected, len(LESSONS))
    lesson = LESSONS[selected]

    while True:
        result = run_practice(stdscr, lesson)
        if result == "retry":
            continue
        return result


def main(stdscr, startup=None):
    init_colors()
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.timeout(-1)  # blocking reads

    startup = startup or {}
    selected = _normalize_lesson_index(
        startup.get("initial_selected", load_last_selected()),
        len(LESSONS),
    )

    start_lesson = startup.get("start_lesson")
    if start_lesson is not None:
        selected = _normalize_lesson_index(start_lesson, len(LESSONS))
        save_last_selected(selected)
        if run_selected_lesson(stdscr, selected) == "quit":
            return

    while True:
        choice = run_menu(stdscr, selected)
        if choice is None:
            break

        selected = _normalize_lesson_index(choice, len(LESSONS))
        save_last_selected(selected)
        if run_selected_lesson(stdscr, selected) == "quit":
            return


def run(argv=None):
    """CLI entrypoint used by __main__ and tests."""
    args = parse_args(argv)

    if args.list_lessons:
        list_lessons()
        return 0

    try:
        startup = build_startup_config(args)
    except ValueError as exc:
        print(f"tt: {exc}", file=sys.stderr)
        return 2

    try:
        curses.wrapper(lambda stdscr: main(stdscr, startup))
    except KeyboardInterrupt:
        pass

    print("Happy typing!")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
