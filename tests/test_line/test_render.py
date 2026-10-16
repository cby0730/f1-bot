"""Rendering handler output as LINE message objects."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from f1_bot.line.render import Output, keyboard_message, markdown_to_plain, to_line_messages


def test_strips_bold_italic_and_escapes():
    assert markdown_to_plain("*Bold* and _it_ \\_x\\* \\` \\[") == "Bold and it _x* ` ["


def test_code_block_kept_verbatim_without_fences():
    text = "*Header*\n\n```\nPOS  DRIVER_NAME *  PTS\n 1   VER       \\_ 25\n```\nfoot"
    assert (
        markdown_to_plain(text) == "Header\n\nPOS  DRIVER_NAME *  PTS\n 1   VER       \\_ 25\nfoot"
    )


def test_inline_code_kept_verbatim():
    assert markdown_to_plain("tz `Asia/Taipei_x`") == "tz Asia/Taipei_x"


def test_link_keeps_url_and_separates_trailing_punctuation():
    text = "star on [GitHub](https://github.com/cby0730/f1-bot)!"
    assert markdown_to_plain(text) == "star on GitHub: https://github.com/cby0730/f1-bot !"


def test_link_url_underscores_untouched():
    text = "\n[Wikipedia](https://en.wikipedia.org/wiki/Max_Verstappen)"
    assert markdown_to_plain(text) == "\nWikipedia: https://en.wikipedia.org/wiki/Max_Verstappen"


def test_unmatched_backtick_is_literal():
    assert markdown_to_plain("a ` b") == "a ` b"


def test_keyboard_rows_become_horizontal_boxes_of_postbacks():
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("◀", callback_data="a"),
                InlineKeyboardButton("▶", callback_data="b"),
            ],
            [InlineKeyboardButton("x" * 50, callback_data="c")],
        ]
    )
    msg = keyboard_message(kb, "alt")
    rows = msg["contents"]["body"]["contents"]
    assert msg["type"] == "flex" and msg["altText"] == "alt"
    assert [[b["action"]["data"] for b in r["contents"]] for r in rows] == [["a", "b"], ["c"]]
    long_action = rows[1]["contents"][0]["action"]
    assert long_action["type"] == "postback"
    assert len(long_action["label"]) == 40
    assert long_action["displayText"] == long_action["label"]


def test_markdown_only_stripped_when_parse_mode_markdown():
    messages = to_line_messages([Output("*a*"), Output("*b*", ParseMode.MARKDOWN)])
    assert [m["text"] for m in messages] == ["*a*", "b"]


def test_keyboard_follows_its_text_with_first_line_as_alt_text():
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Go", callback_data="go")]])
    messages = to_line_messages([Output("\n*Title*\nbody", ParseMode.MARKDOWN, kb)])
    assert [m["type"] for m in messages] == ["text", "flex"]
    assert messages[1]["altText"] == "Title"


def test_text_truncated_to_line_limit():
    (msg,) = to_line_messages([Output("x" * 6000)])
    assert len(msg["text"]) == 5000
