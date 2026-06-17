from f1_bot.api.openf1 import OpenF1Client
from f1_bot.utils.rate_limiter import RateLimiter


async def test_get_session_results_parses_driver_result(httpx_mock):
    limiter = RateLimiter(per_second=100, per_period=10000, period=3600)
    client = OpenF1Client("https://api.openf1.org/v1", limiter)
    httpx_mock.add_response(
        json=[
            {
                "position": 1,
                "driver_number": 4,
                "duration": ["1:10.1", "1:09.5", "1:09.1"],
                "gap_to_leader": None,
                "number_of_laps": 18,
                "dnf": False,
                "dns": False,
                "dsq": False,
            }
        ]
    )

    results = await client.get_session_results(session_key=123)
    await client.close()

    assert len(results) == 1
    assert results[0].driver_number == 4
    assert results[0].duration == ["1:10.1", "1:09.5", "1:09.1"]
