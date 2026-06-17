"""
Comprehensive offline E2E test suite for f1-bot.
Contains 26 scenarios implementing full coverage of all bot features.
All external calls (Jolpica, OpenF1, and Telegram Bot API) are fully mocked via pytest-httpx.
SQLite is fully isolated using pytest's tmp_path.
"""

import json
import urllib.parse
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from telegram import Update

from f1_bot.config import Settings
from f1_bot.main import build_app

# Define Bot Details for Mocking
TELEGRAM_TOKEN = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
MOCK_BOT_ID = 123456789
MOCK_USER_ID = 999999


def make_mock_schedule(num_races: int = 24, current_year: int = 2026) -> dict:
    """Helper to generate a valid Jolpica schedule response matching Pydantic schemas."""
    races = []
    for i in range(1, num_races + 1):
        # Races 1 to 15 are completed (past)
        # Races 16 to 24 are upcoming (future)
        if i <= 15:
            month = 3 + (i - 1) // 5
            day = 1 + ((i - 1) % 5) * 5
        else:
            month = 7 + (i - 16) // 5
            day = 1 + ((i - 16) % 5) * 5

        date_str = f"{current_year}-{month:02d}-{day:02d}"

        race_dict = {
            "season": str(current_year),
            "round": str(i),
            "raceName": f"Grand Prix {i}",
            "date": date_str,
            "time": "15:00:00Z",
            "Circuit": {
                "circuitId": f"circuit_{i}",
                "circuitName": f"Circuit {i}",
                "Location": {
                    "locality": f"Locality {i}",
                    "country": f"Country {i}",
                },
            },
        }
        # Sprints on rounds 3, 6, 9, 12 (completed) and 20 (upcoming)
        if i in [3, 6, 9, 12, 20]:
            race_dict["Sprint"] = {"date": date_str, "time": "11:00:00Z"}
            race_dict["SprintQualifying"] = {"date": date_str, "time": "09:00:00Z"}
            race_dict["FirstPractice"] = {"date": date_str, "time": "08:00:00Z"}
            race_dict["Qualifying"] = {"date": date_str, "time": "14:00:00Z"}
        else:
            race_dict["FirstPractice"] = {"date": date_str, "time": "09:00:00Z"}
            race_dict["SecondPractice"] = {"date": date_str, "time": "13:00:00Z"}
            race_dict["ThirdPractice"] = {"date": date_str, "time": "09:00:00Z"}
            race_dict["Qualifying"] = {"date": date_str, "time": "13:00:00Z"}
        races.append(race_dict)
    return {"MRData": {"RaceTable": {"Races": races}}}


@pytest.fixture
def e2e_settings(tmp_path):
    """Returns application settings configured for offline E2E testing."""
    return Settings(
        TELEGRAM_BOT_TOKEN=TELEGRAM_TOKEN,
        sqlite_path=str(tmp_path / "e2e_f1bot.db"),
        jolpica_base_url="https://api.jolpi.ca/ergast/f1",
        openf1_base_url="https://api.openf1.org/v1",
        jolpica_rate_per_second=100.0,
        jolpica_rate_per_hour=10000,
        openf1_rate_per_second=100.0,
        openf1_rate_per_minute=10000,
    )


@pytest.fixture
async def e2e_app(e2e_settings, httpx_mock):
    """Initializes and yields the bot Application, with mocked Telegram getMe/sendMessage."""
    httpx_mock.add_response(
        url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe",
        json={
            "ok": True,
            "result": {
                "id": MOCK_BOT_ID,
                "is_bot": True,
                "first_name": "F1Bot",
                "username": "f1_tg_bot",
            },
        },
        is_optional=True,
        is_reusable=True,
    )

    httpx_mock.add_response(
        url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "ok": True,
            "result": {
                "message_id": 1001,
                "date": int(datetime.now(UTC).timestamp()),
                "chat": {
                    "id": MOCK_USER_ID,
                    "type": "private",
                },
                "from": {
                    "id": MOCK_BOT_ID,
                    "is_bot": True,
                    "first_name": "F1Bot",
                    "username": "f1_tg_bot",
                },
                "text": "mock_response",
            },
        },
        is_optional=True,
        is_reusable=True,
    )

    httpx_mock.add_response(
        url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
        json={
            "ok": True,
            "result": {
                "message_id": 1001,
                "date": int(datetime.now(UTC).timestamp()),
                "chat": {
                    "id": MOCK_USER_ID,
                    "type": "private",
                },
                "from": {
                    "id": MOCK_BOT_ID,
                    "is_bot": True,
                    "first_name": "F1Bot",
                    "username": "f1_tg_bot",
                },
                "text": "mock_response",
            },
        },
        is_optional=True,
        is_reusable=True,
    )

    httpx_mock.add_response(
        url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
        json={"ok": True, "result": True},
        is_optional=True,
        is_reusable=True,
    )

    httpx_mock.add_response(
        url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMyCommands",
        json={"ok": True, "result": True},
        is_optional=True,
        is_reusable=True,
    )

    httpx_mock.add_response(
        url="https://api.jolpi.ca/ergast/f1/current.json",
        json=make_mock_schedule(24, current_year=2026),
        is_optional=True,
    )

    app = build_app(e2e_settings)
    await app.initialize()

    if app.post_init:
        await app.post_init(app)

    await app.start()

    # Pre-populate schedule in DB
    repo = app.bot_data["repo"]
    jolpica = app.bot_data["jolpica"]
    races = await jolpica.get_current_schedule()
    await repo.save_schedule(2026, races)

    yield app

    await app.stop()
    await app.shutdown()


def make_tg_update(
    app, text: str, user_id: int = MOCK_USER_ID, chat_id: int = MOCK_USER_ID
) -> Update:
    """Helper to construct a Telegram Update containing a text command message."""
    first_word = text.split()[0]
    data = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": int(datetime.now(UTC).timestamp()),
            "chat": {
                "id": chat_id,
                "type": "private",
            },
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test User",
                "username": "testuser",
            },
            "text": text,
            "entities": [
                {
                    "type": "bot_command",
                    "offset": 0,
                    "length": len(first_word),
                }
            ],
        },
    }
    return Update.de_json(data, app.bot)


def make_tg_callback_query_update(
    app, callback_data: str, user_id: int = MOCK_USER_ID, chat_id: int = MOCK_USER_ID
) -> Update:
    """Helper to construct a Telegram Update containing a callback query click."""
    data = {
        "update_id": 2,
        "callback_query": {
            "id": "123",
            "chat_instance": "mock_chat",
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test User",
                "username": "testuser",
            },
            "message": {
                "message_id": 1001,
                "date": int(datetime.now(UTC).timestamp()),
                "chat": {
                    "id": chat_id,
                    "type": "private",
                },
                "text": "Choose timezone region:",
            },
            "data": callback_data,
        },
    }
    return Update.de_json(data, app.bot)


def extract_reply_message(httpx_mock) -> str:
    """Helper to extract the text of the last sendMessage or editMessageText request captured."""
    requests = httpx_mock.get_requests()
    send_msg_reqs = [
        r for r in requests if "sendMessage" in str(r.url) or "editMessageText" in str(r.url)
    ]
    if not send_msg_reqs:
        raise ValueError("No sendMessage or editMessageText request was captured by httpx_mock.")

    last_req = send_msg_reqs[-1]
    content_type = last_req.headers.get("content-type", "")

    if "application/json" in content_type:
        body = json.loads(last_req.read().decode("utf-8"))
        return body.get("text", "")
    else:
        body = last_req.read().decode("utf-8")
        parsed = urllib.parse.parse_qs(body)
        return parsed.get("text", [""])[0]


# ==============================================================================
# CATEGORY A: Core Bot Commands & Basic Navigation (6 scenarios)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_01_start_command(e2e_app, httpx_mock):
    """Scenario 1: /start command E2E"""
    update = make_tg_update(e2e_app, "/start")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Welcome to *F1 Bot*" in reply_text
    assert "/help" in reply_text


@pytest.mark.asyncio
async def test_scenario_02_help_command(e2e_app, httpx_mock):
    """Scenario 2: /help command E2E"""
    update = make_tg_update(e2e_app, "/help")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "F1 Bot Commands" in reply_text


@pytest.mark.asyncio
async def test_scenario_03_schedule_command(e2e_app, httpx_mock):
    """Scenario 3: /schedule command E2E"""
    update = make_tg_update(e2e_app, "/schedule")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Grand Prix 1" in reply_text


@pytest.mark.asyncio
async def test_scenario_04_countdown_command(e2e_app, httpx_mock):
    """Scenario 4: /countdown command E2E"""
    update = make_tg_update(e2e_app, "/countdown")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Grand Prix" in reply_text
    assert "Countdown" in reply_text


@pytest.mark.asyncio
async def test_scenario_05_countdown_no_upcoming_races(e2e_app, httpx_mock):
    """Scenario 5: /countdown when no upcoming races are scheduled."""
    # Mock a past schedule (year 2020)
    httpx_mock.add_response(
        url="https://api.jolpi.ca/ergast/f1/current.json",
        json=make_mock_schedule(24, current_year=2020),
    )
    repo = e2e_app.bot_data["repo"]
    await repo.sqlite._conn.execute("DELETE FROM races")
    await repo.sqlite._conn.commit()

    # Fetch 2020 schedule from mocked API and save to database
    races = await e2e_app.bot_data["jolpica"].get_current_schedule()
    await repo.save_schedule(2026, races)

    update = make_tg_update(e2e_app, "/countdown")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "No upcoming race available yet" in reply_text


@pytest.mark.asyncio
async def test_scenario_06_timezone_interactive_flow(e2e_app, httpx_mock):
    """Scenario 6: Interactive timezone configuration callback workflow."""
    # 1. Trigger timezone region selection page
    update = make_tg_update(e2e_app, "/timezone")
    await e2e_app.process_update(update)
    reply_text = extract_reply_message(httpx_mock)
    assert "Choose your region:" in reply_text

    # 2. Simulate clicking 'Europe' region button
    cb_update = make_tg_callback_query_update(e2e_app, "tz:region:🌍 Europe")
    await e2e_app.process_update(cb_update)
    reply_text = extract_reply_message(httpx_mock)
    assert "pick a city:" in reply_text

    # 3. Simulate clicking 'Europe/London' set button
    cb_update_set = make_tg_callback_query_update(e2e_app, "tz:set:Europe/London")
    await e2e_app.process_update(cb_update_set)
    reply_text = extract_reply_message(httpx_mock)
    assert "Timezone set to *Europe/London*" in reply_text

    # Verify preference saved in DB
    repo = e2e_app.bot_data["repo"]
    tz = await repo.get_user_timezone(MOCK_USER_ID)
    assert tz == "Europe/London"


# ==============================================================================
# CATEGORY B: Timezone Propagation & Commands (4 scenarios)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_07_direct_timezone_valid(e2e_app, httpx_mock):
    """Scenario 7: Direct timezone set with valid IANA name."""
    update = make_tg_update(e2e_app, "/timezone Europe/London")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Timezone set to *Europe/London*" in reply_text

    repo = e2e_app.bot_data["repo"]
    tz = await repo.get_user_timezone(MOCK_USER_ID)
    assert tz == "Europe/London"


@pytest.mark.asyncio
async def test_scenario_08_direct_timezone_invalid(e2e_app, httpx_mock):
    """Scenario 8: Direct timezone set with invalid name."""
    update = make_tg_update(e2e_app, "/timezone Mars/Olympus")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Unknown timezone" in reply_text


@pytest.mark.asyncio
async def test_scenario_09_next_utc_default(e2e_app, httpx_mock):
    """Scenario 9: /next command output defaults to UTC."""
    # Reset user timezone to default / delete preference
    repo = e2e_app.bot_data["repo"]
    await repo.sqlite._conn.execute(
        "DELETE FROM user_preferences WHERE telegram_id=?", (MOCK_USER_ID,)
    )
    await repo.sqlite._conn.commit()

    update = make_tg_update(e2e_app, "/next")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "UTC" in reply_text


@pytest.mark.asyncio
async def test_scenario_10_next_custom_timezone(e2e_app, httpx_mock):
    """Scenario 10: /next command output converted to user timezone preference."""
    # Save timezone preference
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.user import UserPreference

    await repo.upsert_user_preference(
        UserPreference(telegram_id=MOCK_USER_ID, timezone="Europe/Paris")
    )

    update = make_tg_update(e2e_app, "/next")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "CEST" in reply_text or "CET" in reply_text


# ==============================================================================
# CATEGORY C: Results & Query Validation (5 scenarios)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_11_results_no_args_fallback(e2e_app, httpx_mock):
    """Scenario 11: /results with no arguments (fallback to last completed race results)."""
    # Round 15 is last completed race
    httpx_mock.add_response(
        url="https://api.jolpi.ca/ergast/f1/2026/15/results.json",
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2026",
                            "round": "15",
                            "raceName": "GP 15",
                            "date": "2026-06-08",
                            "Circuit": {
                                "circuitId": "c15",
                                "circuitName": "C15",
                                "Location": {"locality": "L15", "country": "C15"},
                            },
                            "Results": [
                                {
                                    "position": "1",
                                    "grid": "1",
                                    "laps": "50",
                                    "status": "Finished",
                                    "points": "25",
                                    "Driver": {
                                        "driverId": "ver",
                                        "givenName": "Max",
                                        "familyName": "Verstappen",
                                        "code": "VER",
                                    },
                                    "Constructor": {"constructorId": "rb", "name": "Red Bull"},
                                }
                            ],
                        }
                    ]
                }
            }
        },
    )

    update = make_tg_update(e2e_app, "/results")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Max Verstappen" in reply_text
    assert "Grand Prix 15" in reply_text


@pytest.mark.asyncio
async def test_scenario_12_results_valid_round(e2e_app, httpx_mock):
    """Scenario 12: /results r2 (valid round number)."""
    httpx_mock.add_response(
        url="https://api.jolpi.ca/ergast/f1/2026/2/results.json",
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2026",
                            "round": "2",
                            "raceName": "GP 2",
                            "date": "2026-03-09",
                            "Circuit": {
                                "circuitId": "c2",
                                "circuitName": "C2",
                                "Location": {"locality": "L2", "country": "C2"},
                            },
                            "Results": [
                                {
                                    "position": "1",
                                    "grid": "1",
                                    "laps": "50",
                                    "status": "Finished",
                                    "points": "25",
                                    "Driver": {
                                        "driverId": "ham",
                                        "givenName": "Lewis",
                                        "familyName": "Hamilton",
                                        "code": "HAM",
                                    },
                                    "Constructor": {"constructorId": "mer", "name": "Mercedes"},
                                }
                            ],
                        }
                    ]
                }
            }
        },
    )

    update = make_tg_update(e2e_app, "/results r2")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Lewis Hamilton" in reply_text
    assert "Grand Prix 2" in reply_text


@pytest.mark.asyncio
async def test_scenario_13_results_invalid_round(e2e_app, httpx_mock):
    """Scenario 13: /results r99 (exceeds total rounds)."""
    update = make_tg_update(e2e_app, "/results r99")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Invalid round number. The current season has only 24 rounds." in reply_text


@pytest.mark.asyncio
async def test_scenario_14_results_future_round(e2e_app, httpx_mock):
    """Scenario 14: /results r18 (not yet occurred)."""
    update = make_tg_update(e2e_app, "/results r18")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Round 18" in reply_text
    assert "has not occurred yet" in reply_text


@pytest.mark.asyncio
async def test_scenario_15_results_limit_count(e2e_app, httpx_mock):
    """Scenario 15: /results 3 (last 3 completed races, merged via ---)."""
    # Mocking rounds 13, 14, 15
    for r_num in [13, 14, 15]:
        httpx_mock.add_response(
            url=f"https://api.jolpi.ca/ergast/f1/2026/{r_num}/results.json",
            json={
                "MRData": {
                    "RaceTable": {
                        "Races": [
                            {
                                "season": "2026",
                                "round": str(r_num),
                                "raceName": f"GP {r_num}",
                                "date": "2026-05-25",
                                "Circuit": {
                                    "circuitId": f"c{r_num}",
                                    "circuitName": f"C{r_num}",
                                    "Location": {"locality": "Loc", "country": "C"},
                                },
                                "Results": [
                                    {
                                        "position": "1",
                                        "grid": "1",
                                        "laps": "50",
                                        "status": "Finished",
                                        "points": "25",
                                        "Driver": {
                                            "driverId": "ver",
                                            "givenName": "Max",
                                            "familyName": "Verstappen",
                                            "code": "VER",
                                        },
                                        "Constructor": {"constructorId": "rb", "name": "Red Bull"},
                                    }
                                ],
                            }
                        ]
                    }
                }
            },
        )

    update = make_tg_update(e2e_app, "/results 3")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Grand Prix 15" in reply_text
    assert "Grand Prix 14" in reply_text
    assert "Grand Prix 13" in reply_text
    assert "---" in reply_text


# ==============================================================================
# CATEGORY D: Sprint Logic & Constraints (4 scenarios)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_16_sprint_valid_round(e2e_app, httpx_mock):
    """Scenario 16: /sprint r3 (sprint weekend completed)."""
    httpx_mock.add_response(
        url="https://api.jolpi.ca/ergast/f1/2026/3/sprint.json",
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2026",
                            "round": "3",
                            "raceName": "GP 3",
                            "date": "2026-03-16",
                            "Circuit": {
                                "circuitId": "c3",
                                "circuitName": "C3",
                                "Location": {"locality": "Loc", "country": "C"},
                            },
                            "SprintResults": [
                                {
                                    "position": "1",
                                    "points": "8",
                                    "Driver": {
                                        "driverId": "ver",
                                        "givenName": "Max",
                                        "familyName": "Verstappen",
                                        "code": "VER",
                                    },
                                    "Constructor": {"constructorId": "rb", "name": "Red Bull"},
                                }
                            ],
                        }
                    ]
                }
            }
        },
    )

    update = make_tg_update(e2e_app, "/sprint r3")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Sprint" in reply_text
    assert "Max Verstappen" in reply_text


@pytest.mark.asyncio
async def test_scenario_17_sprint_non_sprint_weekend(e2e_app, httpx_mock):
    """Scenario 17: /sprint r1 (round without sprint session)."""
    update = make_tg_update(e2e_app, "/sprint r1")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "is not a sprint weekend" in reply_text


@pytest.mark.asyncio
async def test_scenario_18_sprint_future_sprint_weekend(e2e_app, httpx_mock):
    """Scenario 18: /sprint r20 (sprint in the future)."""
    update = make_tg_update(e2e_app, "/sprint r20")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Use /nextsprint" in reply_text


@pytest.mark.asyncio
async def test_scenario_19_nextsprint_command(e2e_app, httpx_mock):
    """Scenario 19: /nextsprint 2 (next 2 sprint sessions)."""
    update = make_tg_update(e2e_app, "/nextsprint 2")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Grand Prix 20" in reply_text
    assert "Sprint" in reply_text


# ==============================================================================
# CATEGORY E: Deep Race Data & OpenF1 API (4 scenarios)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_20_sessionresult_usage_error(e2e_app, httpx_mock):
    """Scenario 20: /sessionresult invalid session arg usage message."""
    update = make_tg_update(e2e_app, "/sessionresult r1 invalid_sess")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Usage: /sessionresult [round] [fp1|fp2|fp3|quali|sq|sprint|race]" in reply_text


@pytest.mark.asyncio
async def test_scenario_21_sessionresult_fp1_flow(e2e_app, httpx_mock):
    """Scenario 21: /sessionresult r1 fp1 (caching and displaying FP1 results via OpenF1)."""
    # 1. Mock OpenF1 sessions
    httpx_mock.add_response(
        url="https://api.openf1.org/v1/sessions?year=2026",
        json=[
            {
                "session_key": 9101,
                "session_name": "Practice 1",
                "session_type": "Practice",
                "meeting_key": 101,
                "date_start": "2026-03-01T09:00:00Z",
                "date_end": "2026-03-01T10:00:00Z",
                "gmt_offset": "+00:00",
                "year": 2026,
            }
        ],
    )

    # 2. Mock OpenF1 session_results
    httpx_mock.add_response(
        url="https://api.openf1.org/v1/session_result?session_key=9101",
        json=[{"position": 1, "driver_number": 44, "duration": "1:14.321"}],
    )

    # 3. Mock Jolpica drivers list for numbers mapping
    httpx_mock.add_response(
        url="https://api.jolpi.ca/ergast/f1/2026/drivers.json",
        json={
            "MRData": {
                "DriverTable": {
                    "Drivers": [
                        {
                            "driverId": "hamilton",
                            "permanentNumber": "44",
                            "code": "HAM",
                            "givenName": "Lewis",
                            "familyName": "Hamilton",
                        }
                    ]
                }
            }
        },
    )

    update = make_tg_update(e2e_app, "/sessionresult r1 fp1")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "FP1 Result" in reply_text
    assert "Lewis Hamilton" in reply_text
    assert "1:14.321" in reply_text


@pytest.mark.asyncio
async def test_scenario_22_pitstops_command(e2e_app, httpx_mock):
    """Scenario 22: /pitstops r1"""
    httpx_mock.add_response(
        url="https://api.jolpi.ca/ergast/f1/2026/1/pitstops.json",
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "PitStops": [
                                {
                                    "driverId": "hamilton",
                                    "lap": "15",
                                    "stop": "1",
                                    "duration": "2.45",
                                }
                            ]
                        }
                    ]
                }
            }
        },
    )

    update = make_tg_update(e2e_app, "/pitstops r1")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Pit Stops" in reply_text
    assert "2.5" in reply_text


@pytest.mark.asyncio
async def test_scenario_23_laps_command(e2e_app, httpx_mock):
    """Scenario 23: /laps r1"""
    httpx_mock.add_response(
        url="https://api.jolpi.ca/ergast/f1/2026/1/laps.json?limit=100",
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "Laps": [
                                {
                                    "number": "45",
                                    "Timings": [
                                        {
                                            "driverId": "hamilton",
                                            "position": "1",
                                            "time": "1:18.293",
                                        }
                                    ],
                                }
                            ]
                        }
                    ]
                }
            }
        },
    )

    update = make_tg_update(e2e_app, "/laps r1")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Lap Times" in reply_text
    assert "1:18.293" in reply_text


# ==============================================================================
# CATEGORY F: Message Overflow & Error Resilience (3 scenarios)
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_24_message_overflow_splitting(e2e_app, httpx_mock):
    """Scenario 24: Message overflow splitting (exceeding Telegram's 4096-char limit)."""
    # We will trigger results for multiple completed races (let's say 4 races)
    # Mocking rounds 12, 13, 14, 15
    for r_num in [11, 12, 13, 14, 15]:
        # Generate a very long results list to exceed 4096 chars when formatted together
        results_list = []
        for p in range(1, 21):
            results_list.append(
                {
                    "position": str(p),
                    "grid": str(p),
                    "laps": "50",
                    "status": "Finished",
                    "points": "0",
                    "Driver": {
                        "driverId": f"d_{p}",
                        "givenName": f"DriverNameVeryLongIndeed_{p}",
                        "familyName": f"DriverFamilyVeryLongIndeed_{p}",
                        "code": f"D{p}",
                    },
                    "Constructor": {
                        "constructorId": "const",
                        "name": f"ConstructorVeryLongIndeed_{p}",
                    },
                }
            )
        httpx_mock.add_response(
            url=f"https://api.jolpi.ca/ergast/f1/2026/{r_num}/results.json",
            json={
                "MRData": {
                    "RaceTable": {
                        "Races": [
                            {
                                "season": "2026",
                                "round": str(r_num),
                                "raceName": f"Grand Prix {r_num} with a very very long name and description to trigger overflow easily",
                                "date": "2026-05-25",
                                "Circuit": {
                                    "circuitId": f"c{r_num}",
                                    "circuitName": f"Circuit {r_num}",
                                    "Location": {"locality": "Locality", "country": "Country"},
                                },
                                "Results": results_list,
                            }
                        ]
                    }
                }
            },
        )

    # Trigger /results 5 (last 5 events)
    update = make_tg_update(e2e_app, "/results 5")
    await e2e_app.process_update(update)

    # Verify that multiple sendMessage calls were captured (indicating splitting)
    requests = httpx_mock.get_requests()
    send_msg_reqs = [r for r in requests if "sendMessage" in str(r.url)]
    assert len(send_msg_reqs) > 1


@pytest.mark.asyncio
async def test_scenario_25_api_client_rate_limiting(e2e_app, httpx_mock):
    """Scenario 25: API Client retry logic on HTTP 429 rate limit."""
    # Reset DB schedule
    repo = e2e_app.bot_data["repo"]
    await repo.sqlite._conn.execute("DELETE FROM races")
    await repo.sqlite._conn.commit()

    # Mock first schedule request returning 429
    httpx_mock.add_response(
        url="https://api.jolpi.ca/ergast/f1/current.json",
        status_code=429,
        headers={"Retry-After": "0"},
    )
    # Mock second schedule request succeeding
    httpx_mock.add_response(
        url="https://api.jolpi.ca/ergast/f1/current.json",
        json=make_mock_schedule(24, current_year=2026),
    )

    # Patch asyncio.sleep to keep E2E tests executing instantly
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        update = make_tg_update(e2e_app, "/next")
        await e2e_app.process_update(update)

        sleep_args = [c[0][0] for c in mock_sleep.call_args_list]
        assert 0 in sleep_args

    reply_text = extract_reply_message(httpx_mock)
    assert "Grand Prix 16" in reply_text


@pytest.mark.asyncio
async def test_scenario_26_global_error_recovery(e2e_app, httpx_mock):
    """Scenario 26: Unhandled command exception logs and outputs standard user error message."""
    repo = e2e_app.bot_data["repo"]
    import unittest.mock

    # Force get_schedule to fail with an unhandled exception
    repo.get_schedule = unittest.mock.AsyncMock(side_effect=ValueError("Simulated DB failure"))

    update = make_tg_update(e2e_app, "/results")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Something went wrong. Please try again in a moment." in reply_text
