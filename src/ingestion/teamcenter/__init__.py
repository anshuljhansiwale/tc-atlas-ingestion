from ingestion.config import Settings
from ingestion.teamcenter.base import TeamcenterClient
from ingestion.teamcenter.mock import MockTeamcenterClient
from ingestion.teamcenter.rest import RestTeamcenterClient


def create_teamcenter_client(settings: Settings) -> TeamcenterClient:
    if settings.tc_mode == "mock":
        return MockTeamcenterClient()
    if settings.tc_mode == "rest":
        return RestTeamcenterClient(settings)
    raise ValueError(f"Unsupported TC_MODE={settings.tc_mode!r}; use 'mock' or 'rest'")


__all__ = [
    "TeamcenterClient",
    "MockTeamcenterClient",
    "RestTeamcenterClient",
    "create_teamcenter_client",
]
