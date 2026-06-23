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
        is_reusable=True,
    )

    app = build_app(e2e_settings)
    await app.initialize()

    # Patch startup_sync to skip full API sync in tests — we populate manually below
    with patch("f1_bot.main.startup_sync", new_callable=AsyncMock):
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


def _parse_tg_request_body(req) -> dict:
    """Parse a Telegram Bot API request body (JSON or form-encoded) into a dict."""
    content_type = req.headers.get("content-type", "")
    raw = req.read().decode("utf-8")
    if "application/json" in content_type:
        return json.loads(raw)
    # Form-encoded: each field value may itself be JSON (e.g. reply_markup)
    parsed = urllib.parse.parse_qs(raw)
    return {k: v[0] for k, v in parsed.items()}


def extract_reply_message(httpx_mock) -> str:
    """Helper to extract the text of the last sendMessage or editMessageText request captured."""
    requests = httpx_mock.get_requests()
    send_msg_reqs = [
        r for r in requests if "sendMessage" in str(r.url) or "editMessageText" in str(r.url)
    ]
    if not send_msg_reqs:
        raise ValueError("No sendMessage or editMessageText request was captured by httpx_mock.")

    body = _parse_tg_request_body(send_msg_reqs[-1])
    return body.get("text", "")


def has_reply_markup(httpx_mock) -> bool:
    """Return True if the last sendMessage or editMessageText included a reply_markup field."""
    requests = httpx_mock.get_requests()
    send_msg_reqs = [
        r for r in requests if "sendMessage" in str(r.url) or "editMessageText" in str(r.url)
    ]
    if not send_msg_reqs:
        return False
    body = _parse_tg_request_body(send_msg_reqs[-1])
    return "reply_markup" in body


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
async def test_scenario_11_results_shows_race_results_from_db(e2e_app, httpx_mock):
    """Scenario 11: /results shows race results pre-populated in SQLite."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.constructor import Constructor
    from f1_bot.models.driver import Driver
    from f1_bot.models.results import RaceResult

    results = [
        RaceResult(
            position=1,
            grid=1,
            laps=50,
            status="Finished",
            points=25.0,
            driver=Driver(
                driver_id="ver", given_name="Max", family_name="Verstappen", nationality="Dutch"
            ),
            constructor=Constructor(constructor_id="rb", name="Red Bull", nationality="Austrian"),
        )
    ]
    await repo.save_race_results(2026, 15, results)

    update = make_tg_update(e2e_app, "/results")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Max Verstappen" in reply_text


@pytest.mark.asyncio
async def test_scenario_12_results_callback_filtered_race(e2e_app, httpx_mock):
    """Scenario 12: Clicking race filter on /results shows race results for round."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.constructor import Constructor
    from f1_bot.models.driver import Driver
    from f1_bot.models.results import RaceResult

    results = [
        RaceResult(
            position=1,
            grid=1,
            laps=50,
            status="Finished",
            points=25.0,
            driver=Driver(
                driver_id="ham", given_name="Lewis", family_name="Hamilton", nationality="British"
            ),
            constructor=Constructor(constructor_id="mer", name="Mercedes", nationality="German"),
        )
    ]
    await repo.save_race_results(2026, 14, results)

    cb_update = make_tg_callback_query_update(e2e_app, "res:filtered:race:14")
    await e2e_app.process_update(cb_update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Lewis Hamilton" in reply_text


@pytest.mark.asyncio
async def test_scenario_13_results_shows_keyboard(e2e_app, httpx_mock):
    """Scenario 13: /results shows inline keyboard for session filtering."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.constructor import Constructor
    from f1_bot.models.driver import Driver
    from f1_bot.models.results import RaceResult

    results = [
        RaceResult(
            position=1,
            grid=2,
            laps=50,
            status="Finished",
            points=25.0,
            driver=Driver(
                driver_id="nor", given_name="Lando", family_name="Norris", nationality="British"
            ),
            constructor=Constructor(constructor_id="mcl", name="McLaren", nationality="British"),
        )
    ]
    await repo.save_race_results(2026, 15, results)

    update = make_tg_update(e2e_app, "/results")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Lando Norris" in reply_text
    assert has_reply_markup(httpx_mock)


@pytest.mark.asyncio
async def test_scenario_14_results_qualifying_filter(e2e_app, httpx_mock):
    """Scenario 14: Clicking qualifying filter shows qualifying results."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.constructor import Constructor
    from f1_bot.models.driver import Driver
    from f1_bot.models.results import QualifyingResult

    results = [
        QualifyingResult(
            position=1,
            driver=Driver(
                driver_id="lec",
                given_name="Charles",
                family_name="Leclerc",
                nationality="Monegasque",
            ),
            constructor=Constructor(constructor_id="fer", name="Ferrari", nationality="Italian"),
            q1="1:15.0",
            q2="1:14.0",
            q3="1:13.0",
        )
    ]
    await repo.save_qualifying_results(2026, 10, results)

    cb_update = make_tg_callback_query_update(e2e_app, "res:filtered:qualifying:10")
    await e2e_app.process_update(cb_update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Charles Leclerc" in reply_text


@pytest.mark.asyncio
async def test_scenario_15_results_no_data_for_round(e2e_app, httpx_mock):
    """Scenario 15: /results for a round with no data shows no-data message."""
    # Round 18 has no results saved
    cb_update = make_tg_callback_query_update(e2e_app, "res:filtered:race:18")
    await e2e_app.process_update(cb_update)

    reply_text = extract_reply_message(httpx_mock)
    assert "\u26a0" in reply_text or "No" in reply_text.lower() or "no data" in reply_text.lower()


@pytest.mark.asyncio
async def test_scenario_16_results_sprint_filter(e2e_app, httpx_mock):
    """Scenario 16: Sprint filter on /results shows sprint results."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.constructor import Constructor
    from f1_bot.models.driver import Driver
    from f1_bot.models.results import SprintResult

    results = [
        SprintResult(
            position=1,
            grid=1,
            laps=17,
            status="Finished",
            points=8.0,
            driver=Driver(
                driver_id="ver", given_name="Max", family_name="Verstappen", nationality="Dutch"
            ),
            constructor=Constructor(constructor_id="rb", name="Red Bull", nationality="Austrian"),
        )
    ]
    await repo.save_sprint_results(2026, 12, results)

    cb_update = make_tg_callback_query_update(e2e_app, "res:filtered:sprint:12")
    await e2e_app.process_update(cb_update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Max Verstappen" in reply_text


@pytest.mark.asyncio
async def test_scenario_17_results_sprint_round_3(e2e_app, httpx_mock):
    """Scenario 17: Sprint results for round 3."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.constructor import Constructor
    from f1_bot.models.driver import Driver
    from f1_bot.models.results import SprintResult

    results = [
        SprintResult(
            position=1,
            grid=1,
            laps=17,
            status="Finished",
            points=8.0,
            driver=Driver(
                driver_id="nor", given_name="Lando", family_name="Norris", nationality="British"
            ),
            constructor=Constructor(constructor_id="mcl", name="McLaren", nationality="British"),
        )
    ]
    await repo.save_sprint_results(2026, 3, results)

    cb_update = make_tg_callback_query_update(e2e_app, "res:filtered:sprint:3")
    await e2e_app.process_update(cb_update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Lando Norris" in reply_text


@pytest.mark.asyncio
async def test_scenario_18_results_no_data_empty_schedule(e2e_app, httpx_mock):
    """Scenario 18: /results when schedule has no completed rounds shows no-data."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.race import Circuit, Race

    future_races = [
        Race(
            season=2026,
            round=i,
            name=f"Grand Prix {i}",
            circuit=Circuit(
                circuit_id=f"c{i}", name=f"Circuit {i}", locality=f"Loc{i}", country=f"C{i}"
            ),
            date=datetime(2099, 3 + i, 1).date(),
        )
        for i in range(1, 4)
    ]
    await repo.save_schedule(2026, future_races)

    update = make_tg_update(e2e_app, "/results")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "\u26a0" in reply_text or "No" in reply_text.lower()


@pytest.mark.asyncio
async def test_scenario_19_next_command_shows_upcoming(e2e_app, httpx_mock):
    """Scenario 19: /next shows the next upcoming race with session filter keyboard."""
    update = make_tg_update(e2e_app, "/next")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Grand Prix 16" in reply_text
    assert has_reply_markup(httpx_mock)


@pytest.mark.asyncio
async def test_scenario_20_results_no_completed_sessions(e2e_app, httpx_mock):
    """Scenario 20: /results when no results exist shows no-data message."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.race import Circuit, Race

    future_races = [
        Race(
            season=2026,
            round=i,
            name=f"Grand Prix {i}",
            circuit=Circuit(
                circuit_id=f"c{i}", name=f"Circuit {i}", locality=f"Loc{i}", country=f"C{i}"
            ),
            date=datetime(2099, 3 + i, 1).date(),
        )
        for i in range(1, 4)
    ]
    await repo.save_schedule(2026, future_races)

    update = make_tg_update(e2e_app, "/results")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "\u26a0" in reply_text or "No" in reply_text.lower()


@pytest.mark.asyncio
async def test_scenario_21_results_back_button(e2e_app, httpx_mock):
    """Scenario 21: Back button on filtered results returns to overview."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.constructor import Constructor
    from f1_bot.models.driver import Driver
    from f1_bot.models.results import RaceResult

    results = [
        RaceResult(
            position=1,
            grid=1,
            laps=50,
            status="Finished",
            points=25.0,
            driver=Driver(
                driver_id="ham", given_name="Lewis", family_name="Hamilton", nationality="British"
            ),
            constructor=Constructor(constructor_id="mer", name="Mercedes", nationality="German"),
        )
    ]
    await repo.save_race_results(2026, 15, results)

    cb_update = make_tg_callback_query_update(e2e_app, "res:back:_:15")
    await e2e_app.process_update(cb_update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Lewis Hamilton" in reply_text or "Grand Prix" in reply_text


@pytest.mark.asyncio
async def test_scenario_22_pitstops_from_db(e2e_app, httpx_mock):
    """Scenario 22: /pitstops shows pit stop data from SQLite."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.results import PitStop

    stops = [PitStop(driver_id="hamilton", lap=15, stop_number=1, duration=24.567)]
    await repo.save_pit_stops(2026, 15, stops)

    update = make_tg_update(e2e_app, "/pitstops")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Pit Stops" in reply_text
    assert "24.6" in reply_text
    assert has_reply_markup(httpx_mock)


@pytest.mark.asyncio
async def test_scenario_23_laps_from_db(e2e_app, httpx_mock):
    """Scenario 23: /laps shows lap data from SQLite."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.results import LapTime

    laps = [LapTime(lap_number=45, driver_id="hamilton", time="1:18.293", position=1)]
    await repo.save_lap_timings(2026, 15, laps)

    update = make_tg_update(e2e_app, "/laps")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Lap Times" in reply_text or "Summary" in reply_text
    assert has_reply_markup(httpx_mock)


@pytest.mark.asyncio
async def test_scenario_24_results_round_navigation(e2e_app, httpx_mock):
    """Scenario 24: Full inline keyboard flow — /results then navigate to another round."""
    repo = e2e_app.bot_data["repo"]
    from f1_bot.models.constructor import Constructor
    from f1_bot.models.driver import Driver
    from f1_bot.models.results import RaceResult

    # Populate round 15
    results_15 = [
        RaceResult(
            position=1,
            grid=1,
            laps=50,
            status="Finished",
            points=25.0,
            driver=Driver(
                driver_id="ver", given_name="Max", family_name="Verstappen", nationality="Dutch"
            ),
            constructor=Constructor(constructor_id="rb", name="Red Bull", nationality="Austrian"),
        )
    ]
    await repo.save_race_results(2026, 15, results_15)

    # Populate round 14
    results_14 = [
        RaceResult(
            position=1,
            grid=1,
            laps=50,
            status="Finished",
            points=25.0,
            driver=Driver(
                driver_id="nor", given_name="Lando", family_name="Norris", nationality="British"
            ),
            constructor=Constructor(constructor_id="mcl", name="McLaren", nationality="British"),
        )
    ]
    await repo.save_race_results(2026, 14, results_14)

    # Step 1: /results shows round 15
    update = make_tg_update(e2e_app, "/results")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Max Verstappen" in reply_text

    # Step 2: Navigate to round 14 via callback
    cb_update = make_tg_callback_query_update(e2e_app, "res:filtered:race:14")
    await e2e_app.process_update(cb_update)

    reply_text = extract_reply_message(httpx_mock)
    assert "Lando Norris" in reply_text

    # Verify editMessageText was used
    requests = httpx_mock.get_requests()
    edit_reqs = [r for r in requests if "editMessageText" in str(r.url)]
    assert len(edit_reqs) >= 1


@pytest.mark.asyncio
async def test_scenario_25_next_shows_upcoming_race_sessions(e2e_app, httpx_mock):
    """Scenario 25: /next shows upcoming race info with session filter buttons."""
    update = make_tg_update(e2e_app, "/next")
    await e2e_app.process_update(update)

    reply_text = extract_reply_message(httpx_mock)
    # Round 16 is first upcoming in mock schedule
    assert "Grand Prix 16" in reply_text
    assert has_reply_markup(httpx_mock)


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
