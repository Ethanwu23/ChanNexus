import json
import unittest
from pathlib import Path

import httpx
import pandas as pd

from chanlun_core import ChanConfig, ChanEngine
from web.chanlun_chart.api.main import create_app


FIXTURE_FILE = Path(__file__).parent / "fixtures" / "characterization_cases.json"


def first_case() -> tuple[dict, list[dict]]:
    case = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))["cases"][0]
    rows = []
    for index, (high, low) in enumerate(zip(case["highs"], case["lows"])):
        middle = (high + low) / 2
        rows.append(
            {
                "date": (
                    pd.Timestamp(case["start_date"]) + pd.Timedelta(days=index)
                ).isoformat(),
                "open": middle,
                "close": middle,
                "high": high,
                "low": low,
                "volume": 100 + index,
            }
        )
    return case, rows


class FastApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        transport = httpx.ASGITransport(app=create_app())
        self.client = httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_health_and_openapi(self):
        response = await self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "ChanNexus"})

        paths = (await self.client.get("/api/openapi.json")).json()["paths"]
        self.assertIn("/api/v1/health", paths)
        self.assertIn("/api/v1/analysis", paths)
        self.assertIn("/tv/config", paths)
        self.assertIn("/tv/time", paths)

    async def test_tradingview_time_uses_existing_timestamp_contract(self):
        response = await self.client.get("/tv/time")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), int)

    async def test_analysis_response_matches_domain_snapshot(self):
        case, rows = first_case()
        response = await self.client.post(
            "/api/v1/analysis",
            json={
                "code": case["code"],
                "frequency": case["frequency"],
                "config": case["config"],
                "klines": rows,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)

        frame = pd.DataFrame(rows)
        expected = ChanEngine(
            case["code"],
            case["frequency"],
            ChanConfig(**case["config"]),
        ).process_klines(frame).snapshot()
        self.assertEqual(response.json(), expected)

    async def test_invalid_kline_returns_validation_error(self):
        response = await self.client.post(
            "/api/v1/analysis",
            json={
                "code": "TEST.INVALID",
                "frequency": "d",
                "klines": [
                    {
                        "date": "2026-01-01T00:00:00",
                        "open": 8,
                        "close": 8,
                        "high": 7,
                        "low": 9,
                        "volume": 100,
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
