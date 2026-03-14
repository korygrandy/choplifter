from pathlib import Path

def get_hostage_rescue_cutscene_path(mission_id: str, assets_dir: Path, default_asset: str, by_mission: dict) -> Path:
    asset = by_mission.get((mission_id or "").strip().lower(), default_asset)
    path = assets_dir / asset
    if path.exists():
        return path
    return assets_dir / default_asset

HOSTAGE_RESCUE_CUTSCENE_EVENT_ID = "hostage_rescue_16"
HOSTAGE_RESCUE_CUTSCENE_THRESHOLD = 16
HOSTAGE_RESCUE_CUTSCENE_DEFAULT_ASSET = "hostage-rescue-cutscene.mpg"
# Example: {"airport": "airport-rescue-cutscene.mpg"}
HOSTAGE_RESCUE_CUTSCENE_BY_MISSION = {
    "city": "city-seige-cutscene.avi",
    "city_center": "city-seige-cutscene.avi",
    "citycenter": "city-seige-cutscene.avi",
    "mission1": "city-seige-cutscene.avi",
    "m1": "city-seige-cutscene.avi",
    "airport": "airport-fuselage-rescue-cutscene.avi",
    "airport_special_ops": "airport-fuselage-rescue-cutscene.avi",
    "airportspecialops": "airport-fuselage-rescue-cutscene.avi",
    "mission2": "airport-fuselage-rescue-cutscene.avi",
    "m2": "airport-fuselage-rescue-cutscene.avi",
    "worship": "hostage-rescue-cutscene.avi",
    "worship_center": "hostage-rescue-cutscene.avi",
    "worshipcenter": "hostage-rescue-cutscene.avi",
    "mission3": "hostage-rescue-cutscene.avi",
    "m3": "hostage-rescue-cutscene.avi",
}
