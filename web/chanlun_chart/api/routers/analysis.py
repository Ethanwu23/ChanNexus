"""缠论分析接口。"""

from fastapi import APIRouter

from ..schemas import AnalysisRequest, AnalysisResponse
from ..services import AnalysisService


router = APIRouter(prefix="/api/v1", tags=["缠论分析"])


@router.post("/analysis", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest) -> AnalysisResponse:
    """执行一次无状态缠论分析。"""
    return AnalysisService.analyze(request)
