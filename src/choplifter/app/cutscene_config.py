from pathlib import Path

def get_hostage_rescue_cutscene_path(mission_id: str, assets_dir: Path, default_asset: str, by_mission: dict) -> Path:
    asset = by_mission.get((mission_id or "").strip().lower(), default_asset)
    return assets_dir / asset

HOSTAGE_RESCUE_CUTSCENE_EVENT_ID = "hostage_rescue_16"
HOSTAGE_RESCUE_CUTSCENE_THRESHOLD = 16
HOSTAGE_RESCUE_CUTSCENE_DEFAULT_ASSET = "hostage-rescue-cutscene.mpg"
# Example: {"airport": "airport-rescue-cutscene.mpg"}
HOSTAGE_RESCUE_CUTSCENE_BY_MISSION = {}
