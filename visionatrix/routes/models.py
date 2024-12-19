import logging

from fastapi import APIRouter, Request

from .. import orphan_models
from ..pydantic_models import OrphanModel
from .helpers import require_admin

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/models", tags=["models"])


@ROUTER.get("/orphan")
def get_orphan_models(request: Request) -> list[OrphanModel]:
    """
    Retrieves a list of orphaned AI model files not associated with any installed flow.

    Orphaned models are files found in ComfyUI's model directories that are not required
    by installed flows. This endpoint provides metadata for each orphaned model,
    including file path, size, and potential usage in flows.

    Access to this endpoint is restricted to administrators.
    """
    require_admin(request)
    return orphan_models.get_orphan_models()
