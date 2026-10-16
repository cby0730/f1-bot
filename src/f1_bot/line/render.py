"""Render handler output (Telegram-shaped) as LINE message objects."""

import re
from dataclasses import dataclass

from telegram import InlineKeyboardMarkup
from telegram.constants import ParseMode

# LINE Messaging API limits (labels verified against /v2/bot/message/validate/reply).
MAX_MESSAGES = 5
_TEXT_LIMIT = 5000
_ALT_TEXT_LIMIT = 400
_LABEL_LIMIT = 40

_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
_ESCAPABLE = "_*`["


@dataclass(frozen=True)
class Output:
    """One message a handler produced: a reply, an edit, or an alert."""

    text: str
    parse_mode: str | None = None
    keyboard: InlineKeyboardMarkup | None = None


def markdown_to_plain(text: str) -> str:
    """Strip Telegram legacy-Markdown markup; LINE shows text messages verbatim.

    Code content is kept verbatim (Telegram does not process escapes inside it), and
    a link keeps its URL so LINE can auto-link it.
    """
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("```", i):
            end = text.find("```", i + 3)
            if end != -1:
                out.append(text[i + 3 : end].strip("\n"))
                i = end + 3
                continue
        if c == "\\" and i + 1 < n and text[i + 1] in _ESCAPABLE:
            out.append(text[i + 1])
            i += 2
            continue
        if c == "`":
            end = text.find("`", i + 1)
            if end != -1:
                out.append(text[i + 1 : end])
                i = end + 1
                continue
        if c == "[":
            m = _LINK.match(text, i)
            if m:
                out.append(f"{markdown_to_plain(m.group(1))}: {m.group(2)}")
                i = m.end()
                # Keep trailing punctuation out of LINE's auto-linked URL.
                if i < n and not text[i].isspace():
                    out.append(" ")
                continue
        if c in "*_":
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def text_message(text: str) -> dict:
    return {"type": "text", "text": text[:_TEXT_LIMIT]}


def _button(text: str, data: str) -> dict:
    label = text[:_LABEL_LIMIT]
    return {
        "type": "button",
        "style": "secondary",
        "height": "sm",
        "action": {"type": "postback", "label": label, "data": data, "displayText": label},
    }


def keyboard_message(keyboard: InlineKeyboardMarkup, alt_text: str) -> dict:
    """An inline keyboard as a Flex bubble: one horizontal box per keyboard row."""
    rows = [
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [_button(b.text, b.callback_data) for b in row],
        }
        for row in keyboard.inline_keyboard
    ]
    return {
        "type": "flex",
        "altText": alt_text[:_ALT_TEXT_LIMIT],
        "contents": {
            "type": "bubble",
            "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": rows},
        },
    }


def to_line_messages(outputs: list[Output]) -> list[dict]:
    messages: list[dict] = []
    for o in outputs:
        text = markdown_to_plain(o.text) if o.parse_mode == ParseMode.MARKDOWN else o.text
        messages.append(text_message(text))
        if o.keyboard and o.keyboard.inline_keyboard:
            first_line = next((line for line in text.splitlines() if line.strip()), text)
            messages.append(keyboard_message(o.keyboard, first_line))
    return messages
