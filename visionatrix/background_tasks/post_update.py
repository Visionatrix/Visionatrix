import asyncio
import logging

from packaging.version import Version

from .. import _version
from ..db_queries import (
    get_system_setting,
    set_system_setting,
)
from ..install_update import update_flows
from .background_tasks import register_background_job

LOGGER = logging.getLogger("visionatrix")


@register_background_job("update_flows", run_on_startup=True)
async def update_flows_bg_job(_exit_event: asyncio.Event):
    version = await get_system_setting("visionatrix_version")
    if version != _version.__version__ and not Version(_version.__version__).is_devrelease:
        LOGGER.info("Change of version detected: %s != %s", version, _version.__version__)
        await update_flows()
        await set_system_setting("visionatrix_version", _version.__version__)
