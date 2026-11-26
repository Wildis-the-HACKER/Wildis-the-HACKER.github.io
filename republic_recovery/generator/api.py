"""
Chess.com PubAPI client for Rook Republic Recovery.

The client makes requests serially, observes a 12-hour minimum cache interval,
uses ETag/Last-Modified validators, and can fall back to stale cached responses
if Chess.com is temporarily unavailable.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
import json
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ChessComAPIError(RuntimeError):
    """Raised when a Chess.com PubAPI request cannot be completed."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat(timespec="seconds")


def _best_rating(stats: dict[str, Any]) -> int | None:
    """Return the highest historical rating exposed in stats.*.best.rating."""
    ratings: list[int] = []
    for section in stats.values():
        if not isinstance(section, dict):
            continue
        best = section.get("best")
        if isinstance(best, dict):
            rating = best.get("rating")
            if isinstance(rating, (int, float)):
                ratings.append(int(rating))
    return max(ratings) if ratings else None


class ChessComPubAPI:
    def __init__(
        self,
        club_slug: str,
        cache_file: str | Path = "data/api_cache.json",
        base_url: str = "https://api.chess.com/pub",
        user_agent: str = "RookRepublicRecovery/0.1",
        timeout: int = 20,
        minimum_cache_seconds: int = 43_200,
        retries: int = 3,
        stale_cache_on_error: bool = True,
    ) -> None:
        self.club_slug = club_slug.strip().lower()
        self.base_url = base_url.rstrip("/")
        self.cache_file = Path(cache_file)
        self.timeout = timeout
        self.minimum_cache_seconds = max(43_200, int(minimum_cache_seconds))
        self.stale_cache_on_error = stale_cache_on_error
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        })

        retry = Retry(
            total=max(0, int(retries)),
            connect=max(0, int(retries)),
            read=max(0, int(retries)),
            status=max(0, int(retries)),
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=1, pool_maxsize=1)
        self.session.mount("https://", adapter)

        self.warnings: list[str] = []
        self.endpoint_status: dict[str, str] = {}

    def _load_cache(self) -> dict[str, Any]:
        if not self.cache_file.exists():
            return {}
        try:
            loaded = json.loads(self.cache_file.read_text(encoding="utf-8"))
            return loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def save_cache(self) -> None:
        temp = self.cache_file.with_suffix(self.cache_file.suffix + ".tmp")
        temp.write_text(json.dumps(self.cache, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(self.cache_file)

    def _request_json(self, url: str) -> dict[str, Any]:
        """Fetch one JSON endpoint, reusing fresh cache and conditional headers."""
        entry = self.cache.get(url, {})
        now = time.time()

        if entry.get("data") is not None:
            fetched_at = float(entry.get("fetched_at", 0))
            if now - fetched_at < self.minimum_cache_seconds:
                self.endpoint_status[url] = "cached"
                return entry["data"]

        headers: dict[str, str] = {}
        if entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]
        if entry.get("last_modified"):
            headers["If-Modified-Since"] = entry["last_modified"]

        try:
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            if response.status_code == 304 and entry.get("data") is not None:
                entry["fetched_at"] = now
                self.cache[url] = entry
                self.endpoint_status[url] = "not_modified"
                return entry["data"]

            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ChessComAPIError(f"Expected a JSON object from {url}")

            self.cache[url] = {
                "fetched_at": now,
                "fetched_at_iso": _iso_now(),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "data": data,
            }
            self.endpoint_status[url] = "updated"
            return data

        except (requests.RequestException, ValueError, ChessComAPIError) as exc:
            if self.stale_cache_on_error and entry.get("data") is not None:
                self.warnings.append(f"Using stale cached data for {url}: {exc}")
                self.endpoint_status[url] = "stale_cache"
                return entry["data"]
            raise ChessComAPIError(f"Unable to retrieve {url}: {exc}") from exc

    def get_club(self) -> dict[str, Any]:
        return self._request_json(f"{self.base_url}/club/{self.club_slug}")

    def get_members(self) -> dict[str, Any]:
        return self._request_json(f"{self.base_url}/club/{self.club_slug}/members")

    def get_matches(self) -> dict[str, Any]:
        return self._request_json(f"{self.base_url}/club/{self.club_slug}/matches")

    def get_player(self, username: str) -> dict[str, Any]:
        from urllib.parse import quote
        return self._request_json(f"{self.base_url}/player/{quote(username, safe='')}")

    def get_player_stats(self, username: str) -> dict[str, Any]:
        from urllib.parse import quote
        return self._request_json(f"{self.base_url}/player/{quote(username, safe='')}/stats")

    @staticmethod
    def _unique_members(member_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Merge weekly/monthly/all_time buckets, keeping latest joined timestamp."""
        unique: dict[str, dict[str, Any]] = {}
        for bucket in ("weekly", "monthly", "all_time"):
            members = member_data.get(bucket, [])
            if not isinstance(members, list):
                continue
            for member in members:
                if not isinstance(member, dict):
                    continue
                username = member.get("username")
                if not isinstance(username, str) or not username.strip():
                    continue
                current = unique.get(username.lower())
                joined = int(member.get("joined") or 0)
                if current is None or joined > int(current.get("joined") or 0):
                    unique[username.lower()] = {"username": username, "joined": joined}
        return sorted(unique.values(), key=lambda item: int(item.get("joined") or 0), reverse=True)

    @staticmethod
    def _active_match_count(matches: dict[str, Any]) -> int:
        registered = matches.get("registered") or []
        in_progress = matches.get("in_progress") or []
        return len(registered) + len(in_progress)

    def fetch_snapshot(
        self,
        newest_limit: int = 5,
        fetch_newest_profiles: bool = True,
    ) -> dict[str, Any]:
        """
        Fetch the data needed by the census and newest-citizens sections.

        Calls are intentionally serial to reduce the chance of PubAPI 429 responses.
        Player profile and stats lookups are limited to the newest N members.
        """
        self.warnings = []
        self.endpoint_status = {}

        club = self.get_club()
        members_data = self.get_members()
        matches = self.get_matches()

        newest = self._unique_members(members_data)[:max(0, newest_limit)]
        newest_citizens: list[dict[str, Any]] = []

        for member in newest:
            citizen = dict(member)
            citizen["profile_url"] = (
                "https://www.chess.com/member/" + requests.utils.quote(member["username"], safe="")
            )
            citizen["avatar"] = None
            citizen["best_rating"] = None

            if fetch_newest_profiles:
                try:
                    profile = self.get_player(member["username"])
                    citizen["avatar"] = profile.get("avatar")
                except ChessComAPIError as exc:
                    self.warnings.append(f"Profile lookup failed for {member['username']}: {exc}")
                try:
                    stats = self.get_player_stats(member["username"])
                    citizen["best_rating"] = _best_rating(stats)
                except ChessComAPIError as exc:
                    self.warnings.append(f"Stats lookup failed for {member['username']}: {exc}")

            newest_citizens.append(citizen)

        self.save_cache()
        return {
            "fetched_at": _iso_now(),
            "club": {
                "name": club.get("name"),
                "members_count": club.get("members_count"),
                "average_daily_rating": club.get("average_daily_rating"),
                "created": club.get("created"),
                "icon": club.get("icon"),
                "url": club.get("url"),
            },
            "members": {
                "activity_bucket_counts": {
                    key: len(members_data.get(key) or [])
                    for key in ("weekly", "monthly", "all_time")
                },
                "unique_listed_count": len(self._unique_members(members_data)),
            },
            "active_matches": self._active_match_count(matches),
            "match_counts": {
                "registered": len(matches.get("registered") or []),
                "in_progress": len(matches.get("in_progress") or []),
                "finished": len(matches.get("finished") or []),
            },
            "newest_citizens": newest_citizens,
            "warnings": self.warnings,
            "endpoint_status": self.endpoint_status,
        }


def load_api_from_config(config_path: str | Path = "config.json") -> ChessComPubAPI:
    config_path = Path(config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    api = config["api"]
    club = config["club"]
    return ChessComPubAPI(
        club_slug=club["slug"],
        cache_file=api.get("cache_file", "data/api_cache.json"),
        base_url=api.get("base_url", "https://api.chess.com/pub"),
        user_agent=api.get("user_agent", "RookRepublicRecovery/0.1"),
        timeout=api.get("timeout_seconds", 20),
        minimum_cache_seconds=api.get("minimum_cache_seconds", 43_200),
        retries=api.get("retries", 3),
        stale_cache_on_error=api.get("stale_cache_on_error", True),
    )


if __name__ == "__main__":
    client = load_api_from_config()
    snapshot = client.fetch_snapshot(
        newest_limit=5,
        fetch_newest_profiles=True,
    )
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))
