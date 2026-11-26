"""Fetch the latest club snapshot and render all sidebar PNG sections."""
from pathlib import Path
import json

from generator.api import load_api_from_config
from generator.render import SidebarRenderer


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    config_path = root / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    api = load_api_from_config(config_path)
    api.cache_file = root / config["api"].get("cache_file", "data/api_cache.json")
    snapshot = api.fetch_snapshot(
        newest_limit=int(config["api"].get("newest_citizens_limit", 5)),
        fetch_newest_profiles=bool(config["api"].get("fetch_newest_profiles", True)),
    )
    (root / "data" / "snapshot.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    outputs = SidebarRenderer(config, root).render_all(snapshot)
    print(f"Rendered {len(outputs)} PNG section(s):")
    for path in outputs:
        print(f"  {path.relative_to(root).as_posix()}")
    if snapshot.get("warnings"):
        print("Warnings:")
        for warning in snapshot["warnings"]:
            print(f"  - {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
