"""FastAPI应用服务。"""

import pandas as pd

from chanlun_core import ChanConfig, ChanEngine

from .schemas import AnalysisRequest, AnalysisResponse


class AnalysisService:
    """将HTTP输入转换为领域模型并执行缠论计算。"""

    @staticmethod
    def analyze(request: AnalysisRequest) -> AnalysisResponse:
        frame = pd.DataFrame(
            [kline.model_dump(mode="python") for kline in request.klines]
        )
        config = ChanConfig(**request.config.model_dump())
        engine = ChanEngine(request.code, request.frequency, config)
        engine.process_klines(frame)
        return AnalysisResponse.model_validate(engine.snapshot())
