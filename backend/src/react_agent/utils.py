"""Utility & helper functions."""

from __future__ import annotations

import typing
from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage


def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


@lru_cache(maxsize=12)
def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)
    return init_chat_model(model, model_provider=provider)


class State:
    """An object that can be used to store arbitrary state."""

    _state: dict[str, typing.Any]

    def __init__(self, state: dict[str, typing.Any] | None = None):
        if state is None:
            state = {}
        super().__setattr__("_state", state)

    def __setattr__(self, key: typing.Any, value: typing.Any) -> None:
        self._state[key] = value

    def __getattr__(self, key: typing.Any) -> typing.Any:
        try:
            return self._state[key]
        except KeyError:
            message = "'{}' object has no attribute '{}'"
            raise AttributeError(message.format(self.__class__.__name__, key))

    def __delattr__(self, key: typing.Any) -> None:
        del self._state[key]


from datetime import datetime, timedelta, timezone


def get_formatted_times(user_timezone: str | None = None) -> str:
    """Returns a formatted string with current times in major time zones.

    This helps the LLM provide accurate time-based information regardless of user location.
    Includes UTC, Eastern Time (ET), Central Time (CT), Pacific Time (PT), and GMT.
    """
    # Get current UTC time
    utc_now = datetime.now(timezone.utc)

    # Define major time zone offsets (hours from UTC)
    time_zones = {
        "UTC": 0,
        "Eastern Time (ET)": -5,  # EST is UTC-5, EDT is UTC-4
        "Central Time (CT)": -6,  # CST is UTC-6, CDT is UTC-5
        "Mountain Time (MT)": -7,  # MST is UTC-7, MDT is UTC-6
        "Pacific Time (PT)": -8,  # PST is UTC-8, PDT is UTC-7
        "GMT": 0,
        "Central European Time (CET)": 1,  # CET is UTC+1, CEST is UTC+2
        "Japan Standard Time (JST)": 9,  # UTC+9
        "Australian Eastern Time (AET)": 10,  # AEST is UTC+10, AEDT is UTC+11
    }

    # Simple DST adjustment (March-November for US time zones)
    # This is a simplified approach and doesn't account for exact DST transition dates
    is_dst_us = 3 <= utc_now.month <= 11
    is_dst_eu = 3 <= utc_now.month <= 10
    is_dst_au = utc_now.month <= 4 or utc_now.month >= 10  # Southern hemisphere DST

    # Apply DST adjustments
    if is_dst_us:
        time_zones["Eastern Time (ET)"] += 1
        time_zones["Central Time (CT)"] += 1
        time_zones["Mountain Time (MT)"] += 1
        time_zones["Pacific Time (PT)"] += 1

    if is_dst_eu:
        time_zones["Central European Time (CET)"] += 1

    if is_dst_au:
        time_zones["Australian Eastern Time (AET)"] += 1

    # Format the time string
    time_strings = []
    date_format = "%Y-%m-%d"
    time_format = "%H:%M:%S"

    for zone_name, offset in time_zones.items():
        zone_time = utc_now.replace(tzinfo=timezone(timedelta(hours=offset)))
        time_strings.append(
            f"{zone_name}: {zone_time.strftime(f'{date_format} {time_format}')}"
        )

    # TODO: Add user timezone to the time strings
    # if user_timezone:
    #    time_strings.append(f"User timezone: {user_timezone}")

    return "\n".join(time_strings)
