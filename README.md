# Terminal Typing Tutor

Minimal terminal touch-typing practice in Python with finger-specific lessons, row drills, common words, full-keyboard practice, and Chinese single-character Wubi drills.

## Features

- Home row, left/right hand, top/bottom row, number row, symbol, word, and full-keyboard lessons
- Six Chinese Wubi lessons covering the most frequent 3000 characters in 500-character bands from `chinese_character_frequency.csv`
- Wubi single-character drills driven by `wubi86.yaml` with real candidate ordering per code
- Uses exact code plus selector key, so `我` is `q` then `Space` or `1`, `他` is `wb` then `Space` or `1`, and second-choice `云` for `fcu` is `fcu2` or `fcu;`
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

Quick summon mode starts the last-selected lesson immediately:

```bash
python3 tt.py --quick
```

[`tt.py`](tt.py) can be run directly on Windows, provided Python and [`windows-curses`](README.md:23) are installed there. The WSL2 shortcut setup below is just one useful Windows invocation scenario, not a requirement.

You can also print the lesson list from the shell:

```bash
python3 tt.py --list-lessons
```

## Windows 11 hotkey launcher for WSL2

A ready-made Windows launcher script is included at [`windows/tt-hotkey.cmd`](windows/tt-hotkey.cmd). The script enters WSL and runs [`tt.py`](tt.py) with `--quick`.

Use a Windows shortcut to supply the terminal window behavior:

1. In Windows, create a new shortcut wherever you want to trigger it from, such as the Desktop or Start Menu.
2. Set the shortcut target to launch `wt.exe` in focus mode and execute [`windows/tt-hotkey.cmd`](windows/tt-hotkey.cmd).
3. In the shortcut properties, assign a Shortcut key.
4. Edit [`windows/tt-hotkey.cmd`](windows/tt-hotkey.cmd) if you want to change:
   - `TT_WSL_DISTRO` — your WSL distro name
   - `TT_PROJECT_DIR` — the project path inside WSL

To find the distro name, run this in Windows PowerShell or Command Prompt:

```text
wsl -l -v
```

Use the value shown in the `NAME` column, for example `Ubuntu` or `Ubuntu-22.04`.

Example shortcut target:

```text
wt.exe --focus --size 100,1 --pos 80,60 cmd.exe /c "\\wsl.localhost\Ubuntu-22.04\home\gus\tt\windows\tt-hotkey.cmd"
```

Examples:

- `--size 100,1` → one-line practice window
- `--size 120,12` → narrow but taller drill window
- `--pos 40,40` → open near the top-left instead of the default position
- `--focus` → hides the title bar for a more minimal summon window

This keeps terminal presentation in the Windows shortcut while [`windows/tt-hotkey.cmd`](windows/tt-hotkey.cmd) stays responsible only for launching [`tt.py`](tt.py) inside WSL.

## Controls

- Menu: `↑/↓` or `j/k`, `Enter` to start, type to search, `Esc` to clear/back, `q` to quit
- Practice: type the text, `Backspace` to correct, `Tab` to restart, `Esc` for menu
- Chinese Wubi: type the exact single-character code, then finish with a selector key; first candidate accepts `Space` or `1`, second accepts `2` or `;`, third accepts `3` or `'`, and fourth through ninth use `4` to `9`
- Results: `r` retry, `m` or `Esc` menu, `q` quit

## Progress

Session history is stored in `.tt_progress.json` next to `tt.py`.
