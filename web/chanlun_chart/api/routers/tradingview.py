"""TradingView基础协议接口。"""

import datetime

from fastapi import APIRouter

from chanlun import fun
from chanlun.base import Market
from chanlun.exchange import get_exchange

from ..schemas import TradingViewConfigResponse


router = APIRouter(prefix="/tv", tags=["TradingView"])


FREQUENCY_MAPS = {
    "10s": "10S",
    "30s": "30S",
    "1m": "1",
    "2m": "2",
    "3m": "3",
    "5m": "5",
    "10m": "10",
    "15m": "15",
    "30m": "30",
    "60m": "60",
    "120m": "120",
    "3h": "180",
    "4h": "240",
    "d": "1D",
    "2d": "2D",
    "w": "1W",
    "m": "1M",
    "y": "12M",
}


MARKETS = (
    Market.A,
    Market.HK,
    Market.FX,
    Market.US,
    Market.FUTURES,
    Market.NY_FUTURES,
    Market.CURRENCY,
    Market.CURRENCY_SPOT,
)


@router.get("/config", response_model=TradingViewConfigResponse)
def configuration() -> TradingViewConfigResponse:
    """返回图表组件支持的市场和周期。"""
    frequencies = {
        frequency
        for market in MARKETS
        for frequency in get_exchange(market).support_frequencys()
    }
    supported_resolutions = [
        value
        for frequency, value in FREQUENCY_MAPS.items()
        if frequency in frequencies
    ]
    return TradingViewConfigResponse(
        supports_search=True,
        supports_group_request=False,
        supported_resolutions=supported_resolutions,
        supports_marks=True,
        supports_timescale_marks=True,
        supports_time=False,
        exchanges=[
            {"value": "a", "name": "沪深", "desc": "沪深A股"},
            {"value": "hk", "name": "港股", "desc": "港股"},
            {"value": "fx", "name": "外汇", "desc": "外汇"},
            {"value": "us", "name": "美股", "desc": "美股"},
            {"value": "futures", "name": "国内期货", "desc": "国内期货"},
            {"value": "ny_futures", "name": "纽约期货", "desc": "纽约期货"},
            {"value": "currency", "name": "数字货币(Futures)", "desc": "数字货币（合约）"},
            {"value": "currency_spot", "name": "数字货币(Spot)", "desc": "数字货币（现货）"},
        ],
    )


@router.get("/time", response_model=int)
def server_time() -> int:
    """返回服务器当前Unix时间戳。"""
    return fun.datetime_to_int(datetime.datetime.now())
