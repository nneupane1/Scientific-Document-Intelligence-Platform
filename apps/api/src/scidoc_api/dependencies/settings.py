from typing import cast

from fastapi import Request
from scidoc_core.config import Settings


def app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)
