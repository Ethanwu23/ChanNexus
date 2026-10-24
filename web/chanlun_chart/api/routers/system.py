"""系统状态接口。"""

from fastapi import APIRouter

from ..schemas import HealthResponse


router = APIRouter(prefix="/api/v1", tags=["系统"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """返回进程存活状态。"""
    return HealthResponse(status="ok", service="ChanNexus")
