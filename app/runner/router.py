from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_tenant_id
from app.db.session import get_db
from app.runner import service
from app.runner.guardrail import PromptInjectionError
from app.runner.schemas import RunRequest, RunResponse

router = APIRouter(prefix="/agents", tags=["runner"])


@router.post("/{agent_id}/run", response_model=RunResponse)
async def run_agent(
    agent_id: str,
    data: RunRequest,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    try:
        execution = await service.run_agent(
            db,
            tenant_id=tenant_id,
            agent_id=agent_id,
            task=data.task,
            model=data.model,
        )
    except service.AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except service.UnsupportedModelError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except PromptInjectionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except service.ToolNotAssignedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return RunResponse.model_validate(execution)
