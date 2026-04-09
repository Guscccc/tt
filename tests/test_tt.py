import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import tt


class FakeScreen:
    def __init__(self, keys=(), height=24, width=100):
        self.keys = list(keys)
        self.height = height
        self.width = width
        self.calls = []
        self.keypad_value = None
        self.timeout_value = None

    def getmaxyx(self):
        return self.height, self.width

    def erase(self):
        self.calls.append(("erase",))

    def addstr(self, y, x, text, attr=0):
        self.calls.append(("addstr", y, x, text, attr))

    def refresh(self):
        self.calls.append(("refresh",))

    def getch(self):
        if not self.keys:
            raise AssertionError("FakeScreen.getch() called with no keys remaining")
        return self.keys.pop(0)

    def keypad(self, value):
        self.keypad_value = value

    def timeout(self, value):
        self.timeout_value = value


@pytest.fixture(autouse=True)
def patch_curses(monkeypatch):
    monkeypatch.setattr(tt.curses, "color_pair", lambda n: n)
    monkeypatch.setattr(tt.curses, "curs_set", lambda *_: None)
    monkeypatch.setattr(tt.curses, "KEY_RESIZE", -1000, raising=False)
    monkeypatch.setattr(tt.curses, "KEY_BACKSPACE", 127, raising=False)
    monkeypatch.setattr(tt.curses, "KEY_UP", -1001, raising=False)
    monkeypatch.setattr(tt.curses, "KEY_DOWN", -1002, raising=False)
    monkeypatch.setattr(tt.curses, "KEY_ENTER", 10, raising=False)


@pytest.fixture
def sample_history():
    return [
        {"wpm": 18.0, "accuracy": 92.0},
        {"wpm": 24.5, "accuracy": 95.0},
        {"wpm": 31.0, "accuracy": 97.5},
    ]


def test_calculate_session_stats_normal_case():
    stats = tt.calculate_session_stats(total_correct=45, total_typed=50, elapsed=30)

    assert stats["wpm"] == pytest.approx(20.0)
    assert stats["accuracy"] == pytest.approx(90.0)
    assert stats["errors"] == 5
    assert stats["chars"] == 50
    assert stats["correct"] == 45
    assert stats["elapsed"] == pytest.approx(30.0)


def test_calculate_session_stats_zero_elapsed_and_zero_typed():
    stats = tt.calculate_session_stats(total_correct=0, total_typed=0, elapsed=0)

    assert stats["wpm"] == 0.0
    assert stats["accuracy"] == 0.0
    assert stats["errors"] == 0


def test_save_and_load_progress_history_round_trip(tmp_path, monkeypatch):
    progress_file = tmp_path / "progress.json"
    monkeypatch.setattr(tt, "PROGRESS_FILE", str(progress_file))

    history = {
        "lessons": {
            "Home Row": [
                {
                    "timestamp": "2025-01-01 00:00:00",
                    "wpm": 33.2,
                    "accuracy": 98.1,
                    "errors": 1,
                    "chars": 50,
                    "correct": 49,
                    "elapsed": 18.0,
                }
            ]
        }
    }

    tt.save_progress_history(history)

    assert json.loads(progress_file.read_text(encoding="utf-8")) == history
    assert tt.load_progress_history() == history


def test_load_progress_history_handles_missing_and_malformed_files(tmp_path, monkeypatch):
    progress_file = tmp_path / "missing.json"
    monkeypatch.setattr(tt, "PROGRESS_FILE", str(progress_file))

    assert tt.load_progress_history() == {"lessons": {}}

    progress_file.write_text("{not valid json", encoding="utf-8")
    assert tt.load_progress_history() == {"lessons": {}}


def test_record_lesson_session_appends_and_rounds_values(tmp_path, monkeypatch):
    progress_file = tmp_path / "progress.json"
    monkeypatch.setattr(tt, "PROGRESS_FILE", str(progress_file))
    monkeypatch.setattr(tt.time, "strftime", lambda _fmt: "2025-02-03 04:05:06")

    first = tt.record_lesson_session(
        "Home Row",
        {
            "wpm": 27.126,
            "accuracy": 98.456,
            "errors": 1,
            "chars": 42,
            "correct": 41,
            "elapsed": 12.345,
        },
    )
    second = tt.record_lesson_session(
        "Home Row",
        {
            "wpm": 31.994,
            "accuracy": 96.444,
            "errors": 2,
            "chars": 55,
            "correct": 53,
            "elapsed": 14.999,
        },
    )

    assert len(first) == 1
    assert len(second) == 2
    loaded = tt.load_progress_history()["lessons"]["Home Row"]
    assert loaded[0]["timestamp"] == "2025-02-03 04:05:06"
    assert loaded[0]["wpm"] == 27.13
    assert loaded[0]["accuracy"] == 98.46
    assert loaded[0]["elapsed"] == 12.35
    assert loaded[1]["wpm"] == 31.99
    assert loaded[1]["accuracy"] == 96.44
    assert loaded[1]["elapsed"] == 15.0


def test_compress_series_and_sparkline_edge_cases():
    assert tt.compress_series([1, 2, 3], 5) == [1, 2, 3]
    assert tt.compress_series([1, 2, 3, 4], 2) == pytest.approx([1.5, 3.5])
    assert tt.make_sparkline([], 10) == ""
    assert tt.make_sparkline([7, 7, 7], 3) == "▅▅▅"


def test_build_wpm_plot_lines_returns_readable_multiline_chart():
    lines = tt.build_wpm_plot_lines([10, 20, 30, 25, 35], width=32, height=7)

    assert len(lines) == 7
    assert lines[0].startswith("WPM Progress:")
    assert any("latest:" in line for line in lines)
    assert any("|" in line for line in lines[1:])
    assert all(len(line) <= 32 for line in lines)


def test_words_for_charset_only_returns_allowed_words():
    chars = "abdeilmnorstuwy"
    words = tt.words_for_charset(chars)

    assert words
    assert all(set(word).issubset(set(chars)) for word in words)


def test_generate_practice_respects_width_and_line_count():
    tt.random.seed(0)
    lesson = {
        "name": "Synthetic",
        "finger": "All fingers",
        "keys": "a b c",
        "chars": "abc",
    }

    lines = tt.generate_practice(lesson, width=8, num_lines=3)

    assert len(lines) == 3
    assert all(len(line) <= 8 for line in lines)


def test_generate_practice_words_only_lesson_respects_width():
    tt.random.seed(1)
    lesson = next(lesson for lesson in tt.LESSONS if lesson.get("words_only"))

    lines = tt.generate_practice(lesson, width=10, num_lines=2)

    assert len(lines) == 2
    assert all(len(line) <= 10 for line in lines)


def test_fit_text_and_practice_left_x_helpers():
    assert tt.fit_text("abcdef", 0) == ""
    assert tt.fit_text("abcdef", 3) == "abc"
    assert tt.fit_text("abcdef", 5) == "ab..."
    assert tt.fit_text("abc", 5) == "abc"
    assert tt.practice_left_x(10) == 2
    assert tt.practice_left_x(12) == 4


def test_menu_row_helpers_build_expected_structure():
    rows = tt._build_menu_rows()

    heading_count = sum(1 for kind, _ in rows if kind == "heading")
    lesson_count = sum(1 for kind, _ in rows if kind == "lesson")
    blank_count = sum(1 for kind, _ in rows if kind == "blank")

    assert rows[0] == ("heading", "HOME ROW")
    assert heading_count == len(tt.MENU_SECTIONS)
    assert lesson_count == len(tt.LESSONS)
    assert blank_count == len(tt.MENU_SECTIONS)
    assert tt._selected_menu_pos(0) == 1


def test_lesson_matching_and_best_match_find_expected_lesson():
    assert tt._match_lesson("10", 9) == 1000
    assert tt._match_lesson("home row", 0) >= 800
    assert tt._match_lesson("asdf", 0) >= 400
    assert tt._find_best_match("bottom", len(tt.LESSONS)) == 10
    assert tt._find_best_match("Ω", len(tt.LESSONS)) == -1


def _sample_stats():
    return {
        "wpm": 33.0,
        "accuracy": 97.0,
        "errors": 1,
        "chars": 60,
        "elapsed": 20.0,
    }


def test_build_results_lines_compact_at_h4(sample_history):
    """h=4 compact: RESULTS + stats + sessions + footer."""
    lines = tt._build_results_lines(50, 4, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert len(lines) == 4
    assert texts[0] == "RESULTS"
    assert any("WPM 33.0" in t for t in texts)
    assert texts[-1].startswith("R: Retry")


def test_build_results_lines_compact_at_h5_includes_sparkline(sample_history):
    """h=5: sparkline appears (threshold 5)."""
    lines = tt._build_results_lines(50, 5, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert len(lines) == 5
    assert any("latest 33.0" in t for t in texts)


def test_build_results_lines_compact_at_h9_includes_rating(sample_history):
    """h=9: rating appears (threshold 9)."""
    lines = tt._build_results_lines(50, 9, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert len(lines) == 9
    assert any("keep practicing" in t.lower() or "great" in t.lower()
               or "excellent" in t.lower() or "keep at it" in t.lower()
               for t in texts)


def test_build_results_lines_semicompact_layout(sample_history):
    """h=10: semi-compact with sparkline and acc trend."""
    lines = tt._build_results_lines(50, 10, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert len(lines) == 10
    assert texts[0] == "RESULTS"
    assert any("latest 33.0" in t for t in texts)
    assert any("Best 31.0 WPM" in t for t in texts)
    assert any("Acc trend:" in t for t in texts)
    assert texts[-1].startswith("R: Retry")


def test_build_results_lines_full_mode_at_h14_uses_labeled_sparkline(sample_history):
    """h=14: full mode uses a labeled sparkline summary and keeps acc trend."""
    lines = tt._build_results_lines(80, 14, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert "PROGRESS" in texts
    assert any(t.startswith("WPM Progress:") for t in texts)
    assert any("latest 33.0" in t for t in texts)
    assert any(t.startswith("Acc trend:") for t in texts)
    assert texts[-1].startswith("R: Retry")


def test_build_results_lines_compact_at_h12_has_no_blank_row(sample_history):
    """h=12: compact mode should use the last row for content, not padding."""
    lines = tt._build_results_lines(80, 12, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert len(lines) == 12
    assert "PROGRESS" in texts
    assert "" not in texts
    assert texts[-1].startswith("R: Retry")


def test_build_results_lines_full_mode_at_h13_avoids_blank_gap(sample_history):
    """h=13: the first full layout keeps sparkline + acc trend without a spacer gap."""
    lines = tt._build_results_lines(80, 13, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert len(lines) == 13
    assert "PROGRESS" in texts
    assert any("latest 33.0" in t for t in texts)
    assert any(t.startswith("Acc trend:") for t in texts)
    assert "" not in texts


def test_build_results_lines_large_layout_includes_progress_chart(sample_history):
    """h=24: full mode with PROGRESS section and WPM bar chart."""
    lines = tt._build_results_lines(80, 24, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert "PROGRESS" in texts
    assert any("Best WPM: 31.0" in t for t in texts)
    assert any("Avg WPM: 24.5" in t for t in texts)
    assert any(t.startswith("WPM Progress:") for t in texts)
    assert any("Acc trend:" in t for t in texts)
    assert texts[-1].startswith("R: Retry")
def test_build_results_lines_full_mode_plot_appears_at_h15(sample_history):
    """h=15: bar chart appears and keeps the acc trend."""
    lines = tt._build_results_lines(80, 15, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert any(t.startswith("WPM Progress:") for t in texts)
    assert any(t.startswith("Acc trend:") for t in texts)


def test_build_results_lines_full_mode_at_h14_has_no_blank_gap(sample_history):
    """h=14: full mode should use all rows with a labeled sparkline summary."""
    lines = tt._build_results_lines(80, 14, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert len(lines) == 14
    assert "" not in texts
    assert any(t.startswith("WPM Progress:") for t in texts)
    assert any(t.startswith("Acc trend:") for t in texts)


def test_build_results_lines_full_mode_plot_appears_at_h16(sample_history):
    """h=16: bar chart still appears once a spacer row is available."""
    lines = tt._build_results_lines(80, 16, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert any(t.startswith("WPM Progress:") for t in texts)




def test_build_results_lines_plot_grows_with_height(sample_history):
    """Taller terminal → more plot rows."""
    lines_20 = tt._build_results_lines(80, 20, "Home Row", _sample_stats(), sample_history)
    lines_30 = tt._build_results_lines(80, 30, "Home Row", _sample_stats(), sample_history)

    assert len(lines_30) > len(lines_20)


@pytest.mark.parametrize("height", list(range(1, 41)))
def test_build_results_lines_never_exceeds_terminal_height(sample_history, height):
    """Generated lines must never exceed terminal height."""
    lines = tt._build_results_lines(80, height, "Home Row", _sample_stats(), sample_history)

    assert len(lines) <= height, (
        f"At h={height}: generated {len(lines)} lines, expected <= {height}"
    )


@pytest.mark.parametrize("height", list(range(1, 13)))
def test_build_results_lines_compact_uses_all_lines(sample_history, height):
    """Compact layout (h < 13) should use exactly h lines — no wasted space."""
    lines = tt._build_results_lines(80, height, "Home Row", _sample_stats(), sample_history)

    assert len(lines) == height, (
        f"At h={height}: generated {len(lines)} lines, expected exactly {height}"
    )


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (ord("r"), "retry"),
        (ord("m"), "menu"),
        (ord("q"), "quit"),
    ],
)
def test_draw_results_returns_expected_action(monkeypatch, key, expected):
    monkeypatch.setattr(tt, "_build_results_lines", lambda *_args: [("RESULTS", 0)])
    screen = FakeScreen(keys=[key])

    result = tt.draw_results(screen, "Home Row", {"wpm": 10, "accuracy": 90, "errors": 1, "chars": 10, "elapsed": 10}, [])

    assert result == expected
    assert any(call[0] == "addstr" for call in screen.calls)


def test_run_menu_returns_none_on_quit():
    screen = FakeScreen(keys=[ord("q")])

    assert tt.run_menu(screen) is None


def test_run_menu_search_and_enter_selects_best_match():
    keys = [ord("b"), ord("o"), ord("t"), ord("t"), ord("o"), ord("m"), 10]
    screen = FakeScreen(keys=keys)

    assert tt.run_menu(screen) == 10


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (27, "menu"),
        (9, "retry"),
    ],
)
def test_run_practice_handles_escape_and_tab(monkeypatch, key, expected):
    screen = FakeScreen(keys=[key])
    lesson = {"name": "Test", "finger": "All", "keys": "a b", "chars": "ab"}

    monkeypatch.setattr(tt, "generate_practice", lambda *_args, **_kwargs: ["ab"])
    monkeypatch.setattr(tt, "draw_practice", lambda *_args, **_kwargs: None)

    assert tt.run_practice(screen, lesson) == expected


def test_run_practice_completion_records_session_and_shows_results(monkeypatch):
    screen = FakeScreen(keys=[ord("a"), ord("b")])
    lesson = {"name": "Test", "finger": "All", "keys": "a b", "chars": "ab"}
    captured = {}

    monkeypatch.setattr(tt, "generate_practice", lambda *_args, **_kwargs: ["ab"])
    monkeypatch.setattr(tt, "draw_practice", lambda *_args, **_kwargs: None)

    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))

    def fake_record_lesson_session(lesson_name, session_stats):
        captured["lesson_name"] = lesson_name
        captured["session_stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    def fake_draw_results(_stdscr, lesson_name, session_stats, lesson_history):
        captured["draw_results"] = {
            "lesson_name": lesson_name,
            "session_stats": dict(session_stats),
            "lesson_history": list(lesson_history),
        }
        return "menu"

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", fake_draw_results)

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert captured["lesson_name"] == "Test"
    assert captured["session_stats"]["wpm"] == pytest.approx(4.0)
    assert captured["session_stats"]["accuracy"] == pytest.approx(100.0)
    assert captured["draw_results"]["lesson_name"] == "Test"
    assert captured["draw_results"]["lesson_history"][0]["wpm"] == pytest.approx(4.0)


def test_run_practice_backspace_reduces_totals_before_completion(monkeypatch):
    screen = FakeScreen(keys=[ord("a"), 127, ord("a"), ord("b")])
    lesson = {"name": "Test", "finger": "All", "keys": "a b", "chars": "ab"}
    totals = []

    monkeypatch.setattr(tt, "generate_practice", lambda *_args, **_kwargs: ["ab"])

    def fake_draw_practice(_stdscr, _lesson, _lines, typed, _cur_line, _cur_col,
                           _start_time, total_correct, total_typed):
        totals.append(([[c for c in row] for row in typed], total_correct, total_typed))

    monkeypatch.setattr(tt, "draw_practice", fake_draw_practice)
    monkeypatch.setattr(tt.time, "time", lambda: next(iter([100.0, 104.0])))

    recorded = {}

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert [item[1:] for item in totals[:4]] == [(0, 0), (1, 1), (0, 0), (1, 1)]
    assert recorded["stats"]["accuracy"] == pytest.approx(100.0)
