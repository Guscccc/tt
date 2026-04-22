import json
import pathlib
import re
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


def addstr_texts(screen):
    return [call[3] for call in screen.calls if call[0] == "addstr"]

def _results_texts(lines):
    return [text for text, _ in lines]



def test_draw_practice_wubi_shows_corresponding_wrong_character_after_completion(monkeypatch):
    screen = FakeScreen(height=24, width=100)
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    lines = [[{"char": "我", "code": "q", "rank": 1, "selectors": (" ", "1"), "target": "q "}]]
    typed = [["f "]]

    monkeypatch.setattr(tt, "load_wubi_code_index", lambda: {"f": ["地"], "q": ["我"]})
    monkeypatch.setattr(tt.time, "time", lambda: 105.0)

    tt.draw_practice(
        screen,
        lesson,
        lines,
        typed,
        cur_line=1,
        cur_col=0,
        start_time=100.0,
        total_correct=0,
        total_typed=2,
    )

    texts = addstr_texts(screen)
    char_calls = [call for call in screen.calls if len(call) == 5 and call[0] == "addstr"]
    assert any("地" == text for text in texts)
    assert not any(call[3] == "我" and call[4] == tt.C_WRONG for call in char_calls)
    assert not any("Wrong 地" in text for text in texts)



def test_draw_practice_wubi_shows_nonminimal_correct_character_in_blue(monkeypatch):
    screen = FakeScreen(height=24, width=100)
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    lines = [[{"char": "我", "code": "q", "rank": 1, "selectors": (" ", "1"), "target": "q "}]]
    typed = [["trnt "]]

    monkeypatch.setattr(tt, "load_wubi_code_index", lambda: {"q": ["我"], "trnt": ["我"]})
    monkeypatch.setattr(tt.time, "time", lambda: 105.0)

    tt.draw_practice(
        screen,
        lesson,
        lines,
        typed,
        cur_line=1,
        cur_col=0,
        start_time=100.0,
        total_correct=0,
        total_typed=5,
    )

    char_calls = [call for call in screen.calls if call[0] == "addstr" and call[3] == "我"]
    assert char_calls
    assert any(call[4] == tt.C_WUBI_NONMINIMAL for call in char_calls)



def test_draw_practice_wubi_hides_error_feedback_until_commit(monkeypatch):
    screen = FakeScreen(height=24, width=100)
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    lines = [[{"char": "我", "code": "q", "rank": 1, "selectors": (" ", "1"), "target": "q "}]]
    typed = [["f"]]

    monkeypatch.setattr(tt, "load_wubi_code_index", lambda: {"f": ["地"], "q": ["我"]})
    monkeypatch.setattr(tt.time, "time", lambda: 105.0)

    tt.draw_practice(
        screen,
        lesson,
        lines,
        typed,
        cur_line=0,
        cur_col=0,
        start_time=100.0,
        total_correct=0,
        total_typed=1,
    )

    texts = addstr_texts(screen)
    assert any("Err: 0" in text for text in texts)
    assert any("Acc: 100%" in text for text in texts)
    assert not any("Wrong 地" in text for text in texts)



def test_init_colors_uses_white_on_blue_for_nonminimal_wubi(monkeypatch):
    init_calls = []

    monkeypatch.setattr(tt.curses, "start_color", lambda: None)
    monkeypatch.setattr(tt.curses, "use_default_colors", lambda: None)
    monkeypatch.setattr(tt.curses, "init_pair", lambda pair, fg, bg: init_calls.append((pair, fg, bg)))
    monkeypatch.setattr(tt.curses, "COLOR_GREEN", 2, raising=False)
    monkeypatch.setattr(tt.curses, "COLOR_WHITE", 7, raising=False)
    monkeypatch.setattr(tt.curses, "COLOR_RED", 1, raising=False)
    monkeypatch.setattr(tt.curses, "COLOR_CYAN", 6, raising=False)
    monkeypatch.setattr(tt.curses, "COLOR_YELLOW", 3, raising=False)
    monkeypatch.setattr(tt.curses, "COLOR_BLACK", 0, raising=False)
    monkeypatch.setattr(tt.curses, "COLOR_MAGENTA", 5, raising=False)
    monkeypatch.setattr(tt.curses, "COLOR_BLUE", 4, raising=False)

    tt.init_colors()

    assert (tt.C_WUBI_NONMINIMAL, tt.curses.COLOR_WHITE, tt.curses.COLOR_BLUE) in init_calls



def _progress_alignment_columns(lines):
    texts = _results_texts(lines)
    acc_line = next((text for text in texts if text.startswith("Acc:")), None)
    if acc_line is None:
        return None

    assert acc_line.startswith("Acc:".ljust(tt.PROGRESS_PLOT_DATA_COL))

    chart_line = next(
        (text for text in texts if "|" in text and not text.startswith("Acc:")),
        None,
    )
    if chart_line is not None:
        return (chart_line.index("|") + 1, tt.PROGRESS_PLOT_DATA_COL)

    wpm_line = next(
        (text for text in texts if text.startswith("WPM:") and "latest " in text),
        None,
    )
    if wpm_line is not None:
        assert wpm_line.startswith("WPM:".ljust(tt.PROGRESS_PLOT_DATA_COL))
        return (tt.PROGRESS_PLOT_DATA_COL, tt.PROGRESS_PLOT_DATA_COL)

    return None


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



def test_calculate_session_stats_supports_character_based_speed():
    stats = tt.calculate_session_stats(total_correct=8, total_typed=10, elapsed=30, chars_per_word=1.0)

    assert stats["wpm"] == pytest.approx(20.0)
    assert stats["accuracy"] == pytest.approx(80.0)
    assert stats["errors"] == 2


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
        },
        "last_selected": 11,
        "error_chars": {
            tt.ERROR_CATEGORY_ENGLISH: {"a": 3, "b": 1},
            tt.ERROR_CATEGORY_WUBI: {"我": 2},
        },
    }

    tt.save_progress_history(history)

    assert json.loads(progress_file.read_text(encoding="utf-8")) == history
    assert tt.load_progress_history() == history


def test_load_progress_history_handles_missing_and_malformed_files(tmp_path, monkeypatch):
    progress_file = tmp_path / "missing.json"
    monkeypatch.setattr(tt, "PROGRESS_FILE", str(progress_file))

    assert tt.load_progress_history() == {
        "lessons": {},
        "last_selected": 0,
        "error_chars": {
            tt.ERROR_CATEGORY_ENGLISH: {},
            tt.ERROR_CATEGORY_WUBI: {},
        },
    }

    progress_file.write_text("{not valid json", encoding="utf-8")
    assert tt.load_progress_history() == {
        "lessons": {},
        "last_selected": 0,
        "error_chars": {
            tt.ERROR_CATEGORY_ENGLISH: {},
            tt.ERROR_CATEGORY_WUBI: {},
        },
    }


def test_load_progress_history_normalizes_last_selected(tmp_path, monkeypatch):
    progress_file = tmp_path / "progress.json"
    monkeypatch.setattr(tt, "PROGRESS_FILE", str(progress_file))
    progress_file.write_text(json.dumps({"lessons": {}, "last_selected": 999}), encoding="utf-8")

    assert tt.load_progress_history()["last_selected"] == len(tt.LESSONS) - 1


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


def test_save_and_load_last_selected_round_trip(tmp_path, monkeypatch):
    progress_file = tmp_path / "progress.json"
    monkeypatch.setattr(tt, "PROGRESS_FILE", str(progress_file))

    saved = tt.save_last_selected(14)

    assert saved == 14
    assert tt.load_last_selected() == 14
    payload = json.loads(progress_file.read_text(encoding="utf-8"))
    assert payload["last_selected"] == 14
    assert payload["error_chars"] == {
        tt.ERROR_CATEGORY_ENGLISH: {},
        tt.ERROR_CATEGORY_WUBI: {},
    }



def test_build_error_practice_lessons_separates_english_and_wubi():
    lessons = tt.build_error_practice_lessons(
        {
            tt.ERROR_CATEGORY_ENGLISH: {
                "z": 2,
                "a": 5,
                "!": 1,
                "q": 4,
                "w": 3,
                "e": 6,
                "r": 7,
            },
            tt.ERROR_CATEGORY_WUBI: {"我": 4, "你": 1, "他": 6, "们": 3, "的": 2, "了": 5},
        }
    )

    assert [lesson["name"] for lesson in lessons] == [
        "English Error Practice",
        "Wubi Error Practice",
    ]
    assert lessons[0]["chars"] == "reaqw"
    assert lessons[0]["error_practice"] == tt.ERROR_CATEGORY_ENGLISH
    assert len(lessons[0]["chars"]) == tt.ERROR_PRACTICE_MAX_CHARS
    assert lessons[1]["wubi_chars"] == ("他", "了", "我", "们", "的")
    assert lessons[1]["wubi_single_char"] is True
    assert lessons[1]["error_practice"] == tt.ERROR_CATEGORY_WUBI
    assert len(lessons[1]["wubi_chars"]) == tt.ERROR_PRACTICE_MAX_CHARS



def test_record_error_char_persists_immediately(tmp_path, monkeypatch):
    progress_file = tmp_path / "progress.json"
    monkeypatch.setattr(tt, "PROGRESS_FILE", str(progress_file))

    tt.record_error_char(tt.ERROR_CATEGORY_ENGLISH, "a")
    tt.record_error_char(tt.ERROR_CATEGORY_ENGLISH, "a")
    tt.record_error_char(tt.ERROR_CATEGORY_WUBI, "我")

    loaded = tt.load_progress_history()
    assert loaded["error_chars"] == {
        tt.ERROR_CATEGORY_ENGLISH: {"a": 2},
        tt.ERROR_CATEGORY_WUBI: {"我": 1},
    }
    assert [lesson["name"] for lesson in tt.build_error_practice_lessons(loaded["error_chars"])] == [
        "English Error Practice",
        "Wubi Error Practice",
    ]


def test_compress_series_and_sparkline_edge_cases():
    assert tt.compress_series([1, 2, 3], 5) == [1, 2, 3]
    assert tt.compress_series([1, 2, 3, 4], 2) == pytest.approx([1.5, 3.5])
    assert tt.make_sparkline([], 10) == ""
    assert tt.make_sparkline([7, 7, 7], 3) == "▅▅▅"
    assert tt.make_sparkline([1, 9, 8], 3) == "▁█▇"


def test_build_wpm_plot_lines_returns_readable_multiline_chart():
    lines = tt.build_wpm_plot_lines([10, 20, 30, 25, 35], width=32, height=7)

    assert len(lines) == 7
    assert lines[0].startswith("WPM Progress:")
    assert any("latest:" in line for line in lines)
    assert any("|" in line for line in lines[1:])
    assert all(len(line) <= 32 for line in lines)


def test_load_word_pool_reads_external_file_and_caches(tmp_path, monkeypatch):
    word_pool_file = tmp_path / "word_pool.txt"
    word_pool_file.write_text("Alpha\nbeta\n\n# comment\nALPHA\ngamma\n", encoding="utf-8")
    monkeypatch.setattr(tt, "WORD_POOL_FILE", str(word_pool_file))
    monkeypatch.setattr(tt, "_WORD_POOL_CACHE", None)

    assert tt.load_word_pool() == ("alpha", "beta", "gamma")

    word_pool_file.write_text("delta\n", encoding="utf-8")
    assert tt.load_word_pool() == ("alpha", "beta", "gamma")



def test_load_wubi_single_char_codes_reads_shortest_codes_and_caches(tmp_path, monkeypatch):
    wubi_file = tmp_path / "wubi86.yaml"
    wubi_file.write_text(
        "# comment\n我 q\n我 trnt\n去 fcu\n云 fcu\n好 vb\n", encoding="utf-8"
    )
    monkeypatch.setattr(tt, "WUBI86_FILE", str(wubi_file))
    monkeypatch.setattr(tt, "_WUBI_CODE_INDEX_CACHE", None)
    monkeypatch.setattr(tt, "_WUBI_SINGLE_CACHE", None)

    assert tt.load_wubi_single_char_codes() == {"我": "q", "去": "fcu", "云": "fcu", "好": "vb"}

    wubi_file.write_text("新 xx\n", encoding="utf-8")
    assert tt.load_wubi_single_char_codes() == {"我": "q", "去": "fcu", "云": "fcu", "好": "vb"}



def test_load_wubi_code_index_preserves_candidate_order(tmp_path, monkeypatch):
    wubi_file = tmp_path / "wubi86.yaml"
    wubi_file.write_text("去 fcu\n云 fcu\n动 fcln\n", encoding="utf-8")
    monkeypatch.setattr(tt, "WUBI86_FILE", str(wubi_file))
    monkeypatch.setattr(tt, "_WUBI_CODE_INDEX_CACHE", None)

    assert tt.load_wubi_code_index() == {"fcu": ["去", "云"], "fcln": ["动"]}



def test_resolve_wubi_typed_char_supports_selector_aliases(tmp_path, monkeypatch):
    wubi_file = tmp_path / "wubi86.yaml"
    wubi_file.write_text("去 fcu\n云 fcu\n支 fcu\n", encoding="utf-8")
    monkeypatch.setattr(tt, "WUBI86_FILE", str(wubi_file))
    monkeypatch.setattr(tt, "_WUBI_CODE_INDEX_CACHE", None)

    assert tt.resolve_wubi_typed_char("fcu2") == "云"
    assert tt.resolve_wubi_typed_char("fcu;") == "云"
    assert tt.resolve_wubi_typed_char("fcu3") == "支"
    assert tt.resolve_wubi_typed_char("fcu'") == "支"



def test_build_chinese_wubi_lessons_creates_500_char_frequency_bands(monkeypatch):
    monkeypatch.setattr(tt, "load_wubi_single_char_entries", lambda: {
        str(i): {"char": str(i), "code": f"c{i}", "rank": 1, "selectors": (" ", "1"), "target": f"c{i} "}
        for i in range(1, 3201)
    })
    monkeypatch.setattr(tt, "load_chinese_frequency_chars", lambda: tuple(str(i) for i in range(1, 3201)))

    lessons = tt.build_chinese_wubi_lessons(22)

    assert len(lessons) == 6
    assert lessons[0]["name"] == "Chinese Wubi 1: 1-500"
    assert lessons[-1]["name"] == "Chinese Wubi 6: 2501-3000"
    assert len(lessons[0]["wubi_chars"]) == 500
    assert len(lessons[-1]["wubi_chars"]) == 500


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


def test_generate_practice_small_height_lines_are_dense():
    tt.random.seed(3)
    lesson = {
        "name": "Synthetic",
        "finger": "All fingers",
        "keys": "a b c",
        "chars": "abc",
    }

    one_line = tt.generate_practice(lesson, width=12, num_lines=1)
    two_lines = tt.generate_practice(lesson, width=12, num_lines=2)
    three_lines = tt.generate_practice(lesson, width=12, num_lines=3)

    assert len(one_line) == 1
    assert len(two_lines) == 2
    assert len(three_lines) == 3
    assert len(one_line[0]) >= 11
    assert all(len(line) >= 11 for line in two_lines)
    assert all(len(line) >= 10 for line in three_lines)



def test_generate_practice_wubi_lesson_uses_single_char_entries_with_shortest_codes(monkeypatch):
    monkeypatch.setattr(tt, "load_wubi_single_char_entries", lambda: {
        "我": {"char": "我", "code": "q", "rank": 1, "selectors": (" ", "1"), "target": "q "},
        "去": {"char": "去", "code": "fcu", "rank": 1, "selectors": (" ", "1"), "target": "fcu "},
        "云": {"char": "云", "code": "fcu", "rank": 2, "selectors": ("2", ";"), "target": "fcu2"},
    })
    tt.random.seed(4)
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "wubi_single_char": True,
        "wubi_chars": ("我", "去", "云"),
    }

    lines = tt.generate_practice(lesson, width=8, num_lines=2)

    assert len(lines) == 2
    assert all(lines)
    assert all(all(set(entry) == {"char", "code", "rank", "selectors", "target"} for entry in line) for line in lines)
    assert all(all(entry["target"] in {"q ", "fcu ", "fcu2"} for entry in line) for line in lines)
    assert all(
        sum(tt.char_display_width(entry["char"]) for entry in line) + max(0, len(line) - 1) <= 8
        for line in lines
    )


def test_generate_practice_row_jump_lesson_alternates_rows_per_hand():
    tt.random.seed(2)
    lesson = next(lesson for lesson in tt.LESSONS if lesson["name"] == "Home ↔ Number Row")
    hand_groups = {
        hand: [set(group) for group in groups]
        for hand, groups in lesson["hand_alternating_groups"].items()
    }

    lines = tt.generate_practice(lesson, width=24, num_lines=3)

    assert len(lines) == 3
    assert all(len(line) <= 24 for line in lines)

    for line in lines:
        for fragment in line.split():
            assert len(fragment) >= 2
            last_group_by_hand = {}
            for ch in fragment:
                matched = [
                    (hand, group_idx)
                    for hand, groups in hand_groups.items()
                    for group_idx, group in enumerate(groups)
                    if ch in group
                ]
                assert len(matched) == 1
                hand, group_idx = matched[0]
                if hand in last_group_by_hand:
                    assert group_idx != last_group_by_hand[hand]
                last_group_by_hand[hand] = group_idx


def test_all_row_jump_lessons_use_strict_hand_alternation_groups():
    row_jump_lessons = [lesson for lesson in tt.LESSONS if lesson.get("alternating_groups")]

    assert [lesson["name"] for lesson in row_jump_lessons] == [
        "Home ↔ Top Row",
        "Home ↔ Bottom Row",
        "Home ↔ Number Row",
        "Top ↔ Bottom Row",
        "Top ↔ Number Row",
        "Bottom ↔ Number Row",
    ]
    assert all(len(lesson["alternating_groups"]) == 2 for lesson in row_jump_lessons)
    assert all(lesson["chars"] == "".join(lesson["alternating_groups"])
               for lesson in row_jump_lessons)
    assert all(sorted(lesson["hand_alternating_groups"]) == ["left", "right"]
               for lesson in row_jump_lessons)
    assert all(len(groups) == 2
               for lesson in row_jump_lessons
               for groups in lesson["hand_alternating_groups"].values())


def test_fit_text_and_practice_left_x_helpers():
    assert tt.fit_text("abcdef", 0) == ""
    assert tt.fit_text("abcdef", 3) == "abc"
    assert tt.fit_text("abcdef", 5) == "ab..."
    assert tt.fit_text("abc", 5) == "abc"
    assert tt.practice_left_x(10) == 2
    assert tt.practice_left_x(12) == 4


def test_menu_row_helpers_build_expected_structure():
    tt.refresh_lessons(
        {
            tt.ERROR_CATEGORY_ENGLISH: {"a": 2},
            tt.ERROR_CATEGORY_WUBI: {"我": 1},
        }
    )
    rows = tt._build_menu_rows()

    heading_count = sum(1 for kind, _ in rows if kind == "heading")
    lesson_count = sum(1 for kind, _ in rows if kind == "lesson")
    blank_count = sum(1 for kind, _ in rows if kind == "blank")
    row_jump_names = {
        tt.LESSONS[data]["name"]
        for kind, data in rows
        if kind == "lesson" and tt.LESSONS[data].get("alternating_groups")
    }

    assert rows[0] == ("heading", "HOME ROW")
    assert ("heading", "ROW JUMPS") in rows
    assert row_jump_names == {
        "Home ↔ Top Row",
        "Home ↔ Bottom Row",
        "Home ↔ Number Row",
        "Top ↔ Bottom Row",
        "Top ↔ Number Row",
        "Bottom ↔ Number Row",
    }
    assert heading_count == len(tt.MENU_SECTIONS)
    assert lesson_count == len(tt.LESSONS)
    assert blank_count == len(tt.MENU_SECTIONS)
    assert any(kind == "heading" and data == "CHINESE" for kind, data in rows)
    assert any(kind == "heading" and data == "ERROR PRACTICE" for kind, data in rows)
    chinese_lessons = [
        tt.LESSONS[data]["name"]
        for kind, data in rows
        if kind == "lesson" and tt.LESSONS[data].get("wubi_single_char") and not tt.LESSONS[data].get("error_practice")
    ]
    assert len(chinese_lessons) == 6
    assert chinese_lessons[0] == "Chinese Wubi 1: 1-500"
    assert chinese_lessons[-1] == "Chinese Wubi 6: 2501-3000"
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
    assert any("Acc:" in t for t in texts)
    assert texts[-1].startswith("R: Retry")


def test_build_results_lines_full_mode_at_h14_uses_labeled_sparkline(sample_history):
    """h=14: full mode uses a labeled sparkline summary and keeps acc trend."""
    lines = tt._build_results_lines(80, 14, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert "PROGRESS" in texts
    assert any(t.startswith("WPM Progress:") for t in texts)
    assert any("latest 33.0" in t for t in texts)
    assert any(t.startswith("Acc:") for t in texts)
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
    assert any(t.startswith("Acc:") for t in texts)
    assert "" not in texts


def test_build_results_lines_large_layout_includes_progress_chart(sample_history):
    """h=24: full mode with PROGRESS section and WPM bar chart."""
    lines = tt._build_results_lines(80, 24, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert "PROGRESS" in texts
    assert any("Best WPM: 31.0" in t for t in texts)
    assert any("Avg WPM: 24.5" in t for t in texts)
    assert any(t.startswith("WPM Progress:") for t in texts)
    assert any("Acc:" in t for t in texts)
    assert texts[-1].startswith("R: Retry")
def test_build_results_lines_full_mode_plot_appears_at_h15(sample_history):
    """h=15: bar chart appears and keeps the acc trend."""
    lines = tt._build_results_lines(80, 15, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert any(t.startswith("WPM Progress:") for t in texts)
    assert any(t.startswith("Acc:") for t in texts)


def test_build_results_lines_full_mode_at_h14_has_no_blank_gap(sample_history):
    """h=14: full mode should use all rows with a labeled sparkline summary."""
    lines = tt._build_results_lines(80, 14, "Home Row", _sample_stats(), sample_history)
    texts = [t for t, _ in lines]

    assert len(lines) == 14
    assert "" not in texts
    assert any(t.startswith("WPM Progress:") for t in texts)
    assert any(t.startswith("Acc:") for t in texts)


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


def test_build_results_lines_compact_alignment_uses_visible_wpm_start():
    """Compact progress rows should not appear shifted by leading blank sparkline cells."""
    lesson_history = [
        {"wpm": 100.0, "accuracy": 100.0},
        {"wpm": 102.0, "accuracy": 100.0},
        {"wpm": 105.0, "accuracy": 100.0},
        {"wpm": 108.0, "accuracy": 100.0},
        {"wpm": 111.0, "accuracy": 100.0},
        {"wpm": 114.0, "accuracy": 100.0},
        {"wpm": 116.0, "accuracy": 100.0},
        {"wpm": 118.0, "accuracy": 100.0},
        {"wpm": 120.0, "accuracy": 100.0},
        {"wpm": 122.0, "accuracy": 100.0},
        {"wpm": 125.0, "accuracy": 100.0},
        {"wpm": 128.0, "accuracy": 100.0},
        {"wpm": 132.0, "accuracy": 100.0},
        {"wpm": 136.0, "accuracy": 100.0},
        {"wpm": 140.0, "accuracy": 100.0},
        {"wpm": 145.0, "accuracy": 100.0},
        {"wpm": 150.0, "accuracy": 100.0},
        {"wpm": 155.0, "accuracy": 100.0},
        {"wpm": 160.0, "accuracy": 100.0},
        {"wpm": 165.0, "accuracy": 100.0},
        {"wpm": 342.0, "accuracy": 100.0},
        {"wpm": 180.0, "accuracy": 40.0},
        {"wpm": 322.7, "accuracy": 23.6},
    ]
    session_stats = {
        "wpm": 322.7,
        "accuracy": 23.6,
        "errors": 81,
        "chars": 106,
        "elapsed": 3.0,
    }

    lines = tt._build_results_lines(80, 12, "Home Row", session_stats, lesson_history)
    texts = _results_texts(lines)
    wpm_line = next(text for text in texts if text.startswith("WPM:"))
    acc_line = next(text for text in texts if text.startswith("Acc:"))

    assert wpm_line[tt.PROGRESS_PLOT_DATA_COL] != " "
    assert acc_line[tt.PROGRESS_PLOT_DATA_COL] != " "


def test_build_results_lines_layout_dump_and_alignment_for_every_height(sample_history):
    """Print all layouts from h=40..1 and verify Acc aligns with the WPM plot."""
    for height in range(40, 0, -1):
        lines = tt._build_results_lines(80, height, "Home Row", _sample_stats(), sample_history)
        texts = _results_texts(lines)

        print(f"\n[h={height}]")
        for text in texts:
            print(f"  {text}")

        alignment = _progress_alignment_columns(lines)
        if alignment is not None:
            plot_col, acc_col = alignment
            assert plot_col == acc_col, (
                f"At h={height}: plot data starts at column {plot_col}, "
                f"but Acc data starts at column {acc_col}."
            )


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


def test_run_menu_uses_initial_selection_when_enter_pressed_immediately():
    screen = FakeScreen(keys=[10])

    assert tt.run_menu(screen, initial_selected=14) == 14



def test_main_remembers_last_selected_lesson(monkeypatch):
    screen = FakeScreen()
    menu_initial = []
    saved = []
    choices = iter([14, None])

    monkeypatch.setattr(tt, "init_colors", lambda: None)
    monkeypatch.setattr(tt.curses, "curs_set", lambda *_: None)
    monkeypatch.setattr(tt, "load_last_selected", lambda: 11)
    monkeypatch.setattr(tt, "save_last_selected", lambda selected: saved.append(selected))
    monkeypatch.setattr(tt, "run_practice", lambda *_args, **_kwargs: "menu")

    def fake_run_menu(_stdscr, initial_selected=0):
        menu_initial.append(initial_selected)
        return next(choices)

    monkeypatch.setattr(tt, "run_menu", fake_run_menu)

    tt.main(screen)

    assert menu_initial == [11, 14]
    assert saved == [14]


def test_build_startup_config_quick_uses_last_selected():
    args = tt.parse_args(["--quick"])

    config = tt.build_startup_config(args, default_selected=10)

    assert config == {"initial_selected": 10, "start_lesson": 10}


def test_main_quick_start_runs_selected_lesson_before_menu(monkeypatch):
    screen = FakeScreen()
    saved = []
    started = []

    monkeypatch.setattr(tt, "init_colors", lambda: None)
    monkeypatch.setattr(tt.curses, "curs_set", lambda *_: None)
    monkeypatch.setattr(tt, "save_last_selected", lambda selected: saved.append(selected))
    monkeypatch.setattr(tt, "load_last_selected", lambda: 2)
    monkeypatch.setattr(tt, "run_selected_lesson", lambda _stdscr, selected: started.append(selected) or "quit")
    monkeypatch.setattr(
        tt,
        "run_menu",
        lambda *_args, **_kwargs: pytest.fail("run_menu should not be reached after quick-start quit"),
    )

    tt.main(screen, {"initial_selected": 2, "start_lesson": 5})

    assert started == [5]
    assert saved == [5]


def test_run_list_lessons_prints_and_returns_zero(monkeypatch, capsys):
    captured = []

    monkeypatch.setattr(tt, "list_lessons", lambda stream=None: captured.append(stream))

    result = tt.run(["--list-lessons"])

    assert result == 0
    assert captured == [None]
    assert capsys.readouterr() == ("", "")


def test_draw_menu_one_line_prioritizes_selected_lesson():
    screen = FakeScreen(height=1, width=40)

    tt.draw_menu(screen, selected=10)

    texts = addstr_texts(screen)

    assert any("Bottom Row" in text for text in texts)
    assert all("TERMINAL TYPING TUTOR" not in text for text in texts)
    assert all("Enter Select" not in text for text in texts)



def test_draw_practice_one_line_shows_active_typing_line_only(monkeypatch):
    monkeypatch.setattr(tt.time, "time", lambda: 100.0)
    screen = FakeScreen(height=1, width=20)
    lesson = {"name": "Test", "finger": "All", "keys": "a b c", "chars": "abc"}
    lines = ["aaaa", "bbbb", "cccc"]
    typed = [[], [], ["c"]]

    tt.draw_practice(screen, lesson, lines, typed, cur_line=2, cur_col=1,
                     start_time=90.0, total_correct=1, total_typed=1)

    char_texts = [call[3] for call in screen.calls if call[0] == "addstr" and len(call[3]) == 1]
    other_texts = [call[3] for call in screen.calls if call[0] == "addstr" and len(call[3]) > 1]

    assert char_texts
    assert set(char_texts) == {"c"}
    assert all("ESC Menu" not in text for text in other_texts)
    assert all("WPM:" not in text for text in other_texts)


@pytest.mark.parametrize(
    ("height", "expected_visible"),
    [
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 4),
        (6, 5),
        (7, 5),
        (8, 5),
        (9, 5),
        (10, 6),
    ],
)
def test_practice_visible_lines_prioritizes_practice_rows(height, expected_visible):
    assert tt.practice_visible_lines(height) == expected_visible



def test_practice_layout_makes_help_last_extra_line():
    assert tt._practice_layout_flags(14)["show_help"] is False
    assert tt._practice_layout_flags(14)["show_progress"] is True
    assert tt._practice_layout_flags(15)["show_help"] is True


def test_draw_practice_two_line_height_uses_both_lines_for_practice(monkeypatch):
    monkeypatch.setattr(tt.time, "time", lambda: 100.0)
    screen = FakeScreen(height=2, width=20)
    lesson = {"name": "Test", "finger": "All", "keys": "a b c", "chars": "abc"}
    lines = ["aaaa", "bbbb", "cccc"]
    typed = [["a"], [], []]

    tt.draw_practice(screen, lesson, lines, typed, cur_line=0, cur_col=1,
                     start_time=90.0, total_correct=1, total_typed=1)

    rendered_rows = {
        call[1]
        for call in screen.calls
        if call[0] == "addstr" and len(call[3]) == 1
    }
    other_texts = [call[3] for call in screen.calls if call[0] == "addstr" and len(call[3]) > 1]

    assert rendered_rows == {0, 1}
    assert all("WPM" not in text for text in other_texts)
    assert all("Line" not in text for text in other_texts)


def test_practice_layout_dump_is_monotonic():
    previous_visible = None
    previous_reserved = None

    for height in range(12, 0, -1):
        layout = tt._practice_layout(height)
        reserved = height - layout["practice_rows"]
        print(f"h={height:2d} reserved={reserved} layout={layout}")

        assert layout["practice_rows"] >= 1
        assert layout["practice_rows"] + reserved == height

        if previous_visible is not None:
            assert layout["practice_rows"] <= previous_visible
            assert reserved <= previous_reserved

        previous_visible = layout["practice_rows"]
        previous_reserved = reserved


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



def test_run_practice_wubi_requires_selector_key_to_complete(monkeypatch):
    screen = FakeScreen(keys=[ord("w"), ord("b"), ord(" ")])
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    captured = {}

    monkeypatch.setattr(
        tt,
        "generate_practice",
        lambda *_args, **_kwargs: [[{"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "}]],
    )
    monkeypatch.setattr(tt, "draw_practice", lambda *_args, **_kwargs: None)

    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))

    def fake_record_lesson_session(lesson_name, session_stats):
        captured["lesson_name"] = lesson_name
        captured["session_stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert captured["lesson_name"] == "Chinese Wubi 1: 1-500"
    assert captured["session_stats"]["chars"] == 3
    assert captured["session_stats"]["wpm"] == pytest.approx(10.0)
    assert captured["session_stats"]["accuracy"] == pytest.approx(100.0)



def test_run_practice_wubi_caps_session_to_five_lines(monkeypatch):
    screen = FakeScreen(height=40, width=100)
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    captured = {}

    def fake_generate_practice(_lesson, width, num_lines):
        captured["width"] = width
        captured["num_lines"] = num_lines
        return [[{"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "}]]

    def stop_after_first_draw(*_args, **_kwargs):
        raise RuntimeError("stop after setup")

    monkeypatch.setattr(tt, "generate_practice", fake_generate_practice)
    monkeypatch.setattr(tt, "draw_practice", stop_after_first_draw)

    with pytest.raises(RuntimeError, match="stop after setup"):
        tt.run_practice(screen, lesson)
    assert captured["num_lines"] == 5


@pytest.mark.parametrize("selector_key", [ord("2"), ord(";")])
def test_run_practice_wubi_supports_second_candidate_selector(monkeypatch, selector_key):
    screen = FakeScreen(keys=[ord("f"), ord("c"), ord("u"), selector_key])
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    captured = {}

    monkeypatch.setattr(
        tt,
        "generate_practice",
        lambda *_args, **_kwargs: [[{"char": "云", "code": "fcu", "rank": 2, "selectors": ("2", ";"), "target": "fcu2"}]],
    )
    monkeypatch.setattr(tt, "draw_practice", lambda *_args, **_kwargs: None)
    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))

    def fake_record_lesson_session(lesson_name, session_stats):
        captured["session_stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    assert tt.run_practice(screen, lesson) == "menu"
    assert captured["session_stats"]["chars"] == 4
    assert captured["session_stats"]["wpm"] == pytest.approx(10.0)
    assert captured["session_stats"]["accuracy"] == pytest.approx(100.0)


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


@pytest.mark.parametrize("separator_key", [ord(" "), 10, 13])
def test_run_practice_requires_separator_to_advance_completed_line(monkeypatch, separator_key):
    screen = FakeScreen(keys=[ord("a"), ord("b"), separator_key, ord("c"), ord("d")])
    lesson = {"name": "Test", "finger": "All", "keys": "a b c d", "chars": "abcd"}
    states = []
    recorded = {}

    monkeypatch.setattr(tt, "generate_practice", lambda *_args, **_kwargs: ["ab", "cd"])

    def fake_draw_practice(_stdscr, _lesson, _lines, typed, cur_line, cur_col,
                           _start_time, total_correct, total_typed):
        states.append((cur_line, cur_col, ["".join(row) for row in typed], total_correct, total_typed))

    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "draw_practice", fake_draw_practice)

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert [(cur_line, cur_col) for cur_line, cur_col, *_ in states[:5]] == [
        (0, 0),
        (0, 1),
        (0, 2),
        (1, 0),
        (1, 1),
    ]
    assert states[2][2] == ["ab", ""]
    assert states[3][2] == ["ab ", ""]
    assert states[2][3:] == (2, 2)
    assert states[3][3:] == (3, 3)
    assert recorded["stats"]["chars"] == 5
    assert recorded["stats"]["accuracy"] == pytest.approx(100.0)


def test_run_practice_wrong_separator_character_counts_as_error_and_advances(monkeypatch):
    screen = FakeScreen(keys=[ord("a"), ord("b"), ord("x"), ord("c"), ord("d")])
    lesson = {"name": "Test", "finger": "All", "keys": "a b c d", "chars": "abcd"}
    states = []
    recorded = {}

    monkeypatch.setattr(tt, "generate_practice", lambda *_args, **_kwargs: ["ab", "cd"])

    def fake_draw_practice(_stdscr, _lesson, _lines, typed, cur_line, cur_col,
                           _start_time, total_correct, total_typed):
        states.append((cur_line, cur_col, ["".join(row) for row in typed], total_correct, total_typed))

    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "draw_practice", fake_draw_practice)

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert [(cur_line, cur_col) for cur_line, cur_col, *_ in states[:5]] == [
        (0, 0),
        (0, 1),
        (0, 2),
        (1, 0),
        (1, 1),
    ]
    assert states[3][2] == ["abx", ""]
    assert states[3][3:] == (2, 3)
    assert recorded["stats"]["chars"] == 5
    assert recorded["stats"]["accuracy"] == pytest.approx(80.0)


@pytest.mark.parametrize("separator_key", [ord(" "), 10, 13])
def test_run_practice_backspace_from_next_line_deletes_trailing_separator(monkeypatch, separator_key):
    screen = FakeScreen(keys=[ord("a"), ord("b"), separator_key, 127, separator_key, ord("c"), ord("d")])
    lesson = {"name": "Test", "finger": "All", "keys": "a b c d", "chars": "abcd"}
    states = []
    recorded = {}

    monkeypatch.setattr(tt, "generate_practice", lambda *_args, **_kwargs: ["ab", "cd"])

    def fake_draw_practice(_stdscr, _lesson, _lines, typed, cur_line, cur_col,
                           _start_time, total_correct, total_typed):
        states.append((cur_line, cur_col, ["".join(row) for row in typed], total_correct, total_typed))

    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "draw_practice", fake_draw_practice)

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert [(cur_line, cur_col) for cur_line, cur_col, *_ in states[:7]] == [
        (0, 0),
        (0, 1),
        (0, 2),
        (1, 0),
        (0, 2),
        (1, 0),
        (1, 1),
    ]
    assert states[3][2] == ["ab ", ""]
    assert states[3][3:] == (3, 3)
    assert states[4][2] == ["ab", ""]
    assert states[4][3:] == (3, 3)
    assert states[5][2] == ["ab ", ""]
    assert states[5][3:] == (4, 4)
    assert recorded["stats"]["chars"] == 6
    assert recorded["stats"]["accuracy"] == pytest.approx(100.0)



def test_run_practice_backspace_keeps_totals_before_completion(monkeypatch):
    screen = FakeScreen(keys=[ord("a"), 127, ord("a"), ord("b")])
    lesson = {"name": "Test", "finger": "All", "keys": "a b", "chars": "ab"}
    totals = []

    monkeypatch.setattr(tt, "generate_practice", lambda *_args, **_kwargs: ["ab"])

    def fake_draw_practice(_stdscr, _lesson, _lines, typed, _cur_line, _cur_col,
                           _start_time, total_correct, total_typed):
        totals.append(([[c for c in row] for row in typed], total_correct, total_typed))

    time_values = iter([100.0, 104.0])
    monkeypatch.setattr(tt, "draw_practice", fake_draw_practice)
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))

    recorded = {}

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert [item[1:] for item in totals[:4]] == [(0, 0), (1, 1), (1, 1), (2, 2)]
    assert recorded["stats"]["chars"] == 3
    assert recorded["stats"]["accuracy"] == pytest.approx(100.0)



def test_run_practice_records_error_even_after_backspace(monkeypatch):
    screen = FakeScreen(keys=[ord("x"), 127, ord("a"), ord("b")])
    lesson = {"name": "Test", "finger": "All", "keys": "a b", "chars": "ab"}
    recorded = {}
    seen_errors = []

    monkeypatch.setattr(tt, "generate_practice", lambda *_args, **_kwargs: ["ab"])
    monkeypatch.setattr(tt, "draw_practice", lambda *_args, **_kwargs: None)
    time_values = iter([100.0, 104.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "record_error_char", lambda category, ch: seen_errors.append((category, ch)))

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    assert tt.run_practice(screen, lesson) == "menu"
    assert seen_errors == [(tt.ERROR_CATEGORY_ENGLISH, "a")]
    assert recorded["stats"]["chars"] == 3
    assert recorded["stats"]["errors"] == 1
    assert recorded["stats"]["accuracy"] == pytest.approx(66.6666666667)



def test_run_practice_wubi_backspace_deletes_committed_character(monkeypatch):
    screen = FakeScreen(keys=[ord("w"), ord("b"), ord(" "), 127, ord("w"), ord("b"), ord(" "), ord("w"), ord("b"), ord(" ")])
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    states = []
    recorded = {}

    monkeypatch.setattr(
        tt,
        "generate_practice",
        lambda *_args, **_kwargs: [[
            {"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "},
            {"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "},
        ]],
    )

    def fake_draw_practice(_stdscr, _lesson, _lines, typed, cur_line, cur_col,
                           _start_time, total_correct, total_typed):
        states.append((cur_line, cur_col, [list(row) for row in typed], total_correct, total_typed))

    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "draw_practice", fake_draw_practice)

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert [(cur_line, cur_col) for cur_line, cur_col, *_ in states[:10]] == [
        (0, 0),
        (0, 0),
        (0, 0),
        (0, 1),
        (0, 0),
        (0, 0),
        (0, 0),
        (0, 1),
        (0, 1),
        (0, 1),
    ]
    assert states[3][2] == [["wb ", ""]]
    assert states[3][3:] == (3, 3)
    assert states[4][2] == [["", ""]]
    assert states[4][3:] == (3, 3)
    assert recorded["stats"]["chars"] == 9
    assert recorded["stats"]["accuracy"] == pytest.approx(100.0)



def test_run_practice_wubi_backspace_within_composition_removes_one_key(monkeypatch):
    screen = FakeScreen(keys=[ord("w"), ord("b"), 127, ord("b"), ord(" ")])
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    states = []
    recorded = {}

    monkeypatch.setattr(
        tt,
        "generate_practice",
        lambda *_args, **_kwargs: [[{"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "}]],
    )

    def fake_draw_practice(_stdscr, _lesson, _lines, typed, cur_line, cur_col,
                           _start_time, total_correct, total_typed):
        states.append((cur_line, cur_col, [list(row) for row in typed], total_correct, total_typed))

    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "draw_practice", fake_draw_practice)

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert states[1][2] == [["w"]]
    assert states[1][3:] == (1, 1)
    assert states[2][2] == [["wb"]]
    assert states[2][3:] == (2, 2)
    assert states[3][2] == [["w"]]
    assert states[3][3:] == (2, 2)
    assert recorded["stats"]["chars"] == 4
    assert recorded["stats"]["accuracy"] == pytest.approx(100.0)



def test_run_practice_wubi_does_not_record_error_before_commit(monkeypatch):
    screen = FakeScreen(keys=[ord("x"), ord(" ")])
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    recorded = {}
    seen_errors = []
    seen_error_counts = []

    monkeypatch.setattr(
        tt,
        "generate_practice",
        lambda *_args, **_kwargs: [[{"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "}]],
    )

    def fake_draw_practice(_stdscr, _lesson, _lines, _typed, _cur_line, _cur_col,
                           _start_time, _total_correct, _total_typed):
        seen_error_counts.append(len(seen_errors))

    monkeypatch.setattr(tt, "draw_practice", fake_draw_practice)
    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "record_error_char", lambda category, ch: seen_errors.append((category, ch)))

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    assert tt.run_practice(screen, lesson) == "menu"
    assert seen_error_counts == [0, 0]
    assert seen_errors == [(tt.ERROR_CATEGORY_WUBI, "他")]
    assert recorded["stats"]["chars"] == 2
    assert recorded["stats"]["errors"] == 1
    assert recorded["stats"]["accuracy"] == pytest.approx(0.0)



def test_draw_practice_wubi_uses_committed_character_counts_for_stats(monkeypatch):
    screen = FakeScreen(height=24, width=100)
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    lines = [[
        {"char": "我", "code": "q", "rank": 1, "selectors": (" ", "1"), "target": "q ", "_attempted": True, "_had_error": True},
        {"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb ", "_attempted": True},
    ]]
    typed = [["trnt ", "wb "]]

    monkeypatch.setattr(tt.time, "time", lambda: 105.0)
    monkeypatch.setattr(tt, "load_wubi_code_index", lambda: {"q": ["我"], "trnt": ["我"], "wb": ["他"]})

    tt.draw_practice(
        screen,
        lesson,
        lines,
        typed,
        cur_line=1,
        cur_col=0,
        start_time=100.0,
        total_correct=0,
        total_typed=8,
    )

    texts = addstr_texts(screen)
    assert any("Acc: 50%  Err: 1" in text for text in texts)
    assert any("50%  E1" in text for text in texts)



def test_run_practice_wubi_backspace_clears_uncommitted_error(monkeypatch):
    screen = FakeScreen(keys=[ord("x"), 127, ord("w"), ord("b"), ord(" ")])
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    recorded = {}
    seen_errors = []

    monkeypatch.setattr(
        tt,
        "generate_practice",
        lambda *_args, **_kwargs: [[{"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "}]],
    )
    monkeypatch.setattr(tt, "draw_practice", lambda *_args, **_kwargs: None)
    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "record_error_char", lambda category, ch: seen_errors.append((category, ch)))

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    assert tt.run_practice(screen, lesson) == "menu"
    assert seen_errors == []
    assert recorded["stats"]["chars"] == 4
    assert recorded["stats"]["errors"] == 0
    assert recorded["stats"]["accuracy"] == pytest.approx(75.0)



def test_run_practice_wubi_backspace_keeps_committed_character_error(monkeypatch):
    screen = FakeScreen(keys=[ord("w"), ord(" "), 127, ord("w"), ord("b"), ord(" ")])
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    recorded = {}
    seen_errors = []

    monkeypatch.setattr(
        tt,
        "generate_practice",
        lambda *_args, **_kwargs: [[{"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "}]],
    )
    monkeypatch.setattr(tt, "draw_practice", lambda *_args, **_kwargs: None)
    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "record_error_char", lambda category, ch: seen_errors.append((category, ch)))

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    assert tt.run_practice(screen, lesson) == "menu"
    assert seen_errors == [(tt.ERROR_CATEGORY_WUBI, "他")]
    assert recorded["stats"]["errors"] == 1



def test_run_practice_wubi_backspace_then_wrong_after_correct_counts_error(monkeypatch):
    screen = FakeScreen(keys=[ord("w"), ord("b"), ord(" "), 127, ord("w"), ord(" "), ord("w"), ord("b"), ord(" ")])
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    recorded = {}
    seen_errors = []

    monkeypatch.setattr(
        tt,
        "generate_practice",
        lambda *_args, **_kwargs: [[
            {"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "},
            {"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "},
        ]],
    )
    monkeypatch.setattr(tt, "draw_practice", lambda *_args, **_kwargs: None)
    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "record_error_char", lambda category, ch: seen_errors.append((category, ch)))

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    assert tt.run_practice(screen, lesson) == "menu"
    assert seen_errors == [(tt.ERROR_CATEGORY_WUBI, "他")]
    assert recorded["stats"]["errors"] == 1



@pytest.mark.parametrize("selector_key", [ord(" "), ord("1"), ord("2"), ord("4"), ord(";"), ord("'")])
def test_run_practice_wubi_selector_commits_even_when_wrong(monkeypatch, selector_key):
    screen = FakeScreen(keys=[ord("w"), selector_key])
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    states = []
    recorded = {}

    monkeypatch.setattr(
        tt,
        "generate_practice",
        lambda *_args, **_kwargs: [[{"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "}]],
    )

    def fake_draw_practice(_stdscr, _lesson, _lines, typed, cur_line, cur_col,
                           _start_time, total_correct, total_typed):
        states.append((cur_line, cur_col, [list(row) for row in typed], total_correct, total_typed))

    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "draw_practice", fake_draw_practice)

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert [(cur_line, cur_col) for cur_line, cur_col, *_ in states] == [
        (0, 0),
        (0, 0),
    ]
    assert states[-1][2] == [["w"]]
    assert states[-1][3:] == (1, 1)
    assert recorded["stats"]["chars"] == 2
    assert recorded["stats"]["accuracy"] == pytest.approx(50.0)



def test_run_practice_wubi_selector_commits_after_extra_keys(monkeypatch):
    screen = FakeScreen(keys=[ord("w"), ord("b"), ord("x"), ord(" ")])
    lesson = {
        "name": "Chinese Wubi 1: 1-500",
        "finger": "All fingers",
        "keys": "Exact code then selector",
        "chars": "abcdefghijklmnopqrstuvwxyz1234567890;' ",
        "wubi_single_char": True,
    }
    states = []
    recorded = {}

    monkeypatch.setattr(
        tt,
        "generate_practice",
        lambda *_args, **_kwargs: [[{"char": "他", "code": "wb", "rank": 1, "selectors": (" ", "1"), "target": "wb "}]],
    )

    def fake_draw_practice(_stdscr, _lesson, _lines, typed, cur_line, cur_col,
                           _start_time, total_correct, total_typed):
        states.append((cur_line, cur_col, [list(row) for row in typed], total_correct, total_typed))

    time_values = iter([100.0, 106.0])
    monkeypatch.setattr(tt.time, "time", lambda: next(time_values))
    monkeypatch.setattr(tt, "draw_practice", fake_draw_practice)

    def fake_record_lesson_session(_lesson_name, session_stats):
        recorded["stats"] = dict(session_stats)
        return [{"wpm": session_stats["wpm"], "accuracy": session_stats["accuracy"]}]

    monkeypatch.setattr(tt, "record_lesson_session", fake_record_lesson_session)
    monkeypatch.setattr(tt, "draw_results", lambda *_args, **_kwargs: "menu")

    result = tt.run_practice(screen, lesson)

    assert result == "menu"
    assert [(cur_line, cur_col) for cur_line, cur_col, *_ in states] == [
        (0, 0),
        (0, 0),
        (0, 0),
        (0, 0),
    ]
    assert states[-1][2] == [["wbx"]]
    assert states[-1][3:] == (2, 3)
    assert recorded["stats"]["chars"] == 4
    assert recorded["stats"]["accuracy"] == pytest.approx(50.0)
