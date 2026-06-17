from f1_bot.api.jolpica import JolpicaClient
from f1_bot.utils.rate_limiter import RateLimiter


def _client():
    limiter = RateLimiter(per_second=100, per_period=10000, period=3600)
    return JolpicaClient("https://api.jolpi.ca/ergast/f1", limiter)


async def test_get_current_schedule_parses_weekend_sessions(httpx_mock):
    httpx_mock.add_response(
        json={
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "raceName": "Bahrain Grand Prix",
                            "Circuit": {
                                "circuitId": "bahrain",
                                "circuitName": "Bahrain International Circuit",
                                "Location": {"locality": "Sakhir", "country": "Bahrain"},
                            },
                            "date": "2024-03-02",
                            "time": "15:00:00Z",
                            "FirstPractice": {"date": "2024-02-29", "time": "11:30:00Z"},
                            "SecondPractice": {"date": "2024-02-29", "time": "15:00:00Z"},
                            "ThirdPractice": {"date": "2024-03-01", "time": "12:30:00Z"},
                            "Qualifying": {"date": "2024-03-01", "time": "16:00:00Z"},
                        }
                    ]
                }
            }
        }
    )
    client = _client()

    races = await client.get_current_schedule()
    await client.close()

    race = races[0]
    assert race.fp1 is not None
    assert race.fp1.date.isoformat() == "2024-02-29"
    assert race.qualifying is not None
    assert race.qualifying.time.isoformat() == "16:00:00"
