# Terminal Typing Tutor

Minimal terminal touch-typing practice in Python with finger-specific lessons, row drills, common words, and full-keyboard practice.

## Features

- Home row, left/right hand, top/bottom row, number row, symbol, word, and full-keyboard lessons
- Covers all letters, uppercase letters, digits, and every supported symbol/punctuation key
- Searchable lesson menu
- Live WPM, accuracy, errors, and progress bar
- Saved lesson history with progress charts in the results screen

## Supported symbols

```text
~ ! @ # $ % ^ & * ( ) _ + { } | : " < > ? ` - = [ ] \ ; ' , . /
```

## Requirements

- Python 3.6+
- Linux/macOS: built-in `curses`
- Windows: `pip install windows-curses`

## Run

```bash
python3 tt.py
```

## Controls

- Menu: `↑/↓` or `j/k`, `Enter` to start, type to search, `Esc` to clear/back, `q` to quit
- Practice: type the text, `Backspace` to correct, `Tab` to restart, `Esc` for menu
- Results: `r` retry, `m` or `Esc` menu, `q` quit

## Progress

Session history is stored in `.tt_progress.json` next to `tt.py`.
