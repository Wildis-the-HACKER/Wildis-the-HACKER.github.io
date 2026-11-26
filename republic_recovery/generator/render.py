"""Render the Republic's data-driven sidebar sections as independent PNGs."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any
import json
import textwrap

import requests
from PIL import Image, ImageDraw, ImageFont


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def font(size: int, bold: bool = False):
    names = (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
              "C:/Windows/Fonts/arialbd.ttf"] if bold else
             ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
              "C:/Windows/Fonts/arial.ttf"])
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


class SidebarRenderer:
    def __init__(self, config: dict, root: Path):
        self.config = config
        self.root = root
        r = config["render"]
        self.scale = int(r.get("scale", 3))
        self.width = int(r.get("logical_width", 300)) * self.scale
        self.c = {
            "bg": r.get("background", "#064765"), "panel": r.get("panel", "#0082ba"),
            "card": r.get("card", "#075477"), "deep": r.get("card_deep", "#063b56"),
            "text": r.get("text", "#ffffff"), "muted": r.get("muted", "#b8d7e5"),
            "link": r.get("link", "#7fe3ff"), "green": r.get("green", "#00d985"),
            "border": r.get("border", "#00a2e8")}
        self.tz = ZoneInfo(config.get("project", {}).get("timezone", "UTC"))
        self.out = root / config["paths"].get("output_images", "images")
        self.out.mkdir(parents=True, exist_ok=True)
        self.avatars = root / "assets" / "avatars"
        self.avatars.mkdir(parents=True, exist_ok=True)

    def p(self, n):
        return int(round(n * self.scale))

    def canvas(self, height):
        im = Image.new("RGB", (self.width, self.p(height)), self.c["bg"])
        return im, ImageDraw.Draw(im)

    def txt(self, d, x, y, value, size=10, color=None, bold=False, anchor=None):
        d.text((self.p(x), self.p(y)), str(value), font=font(self.p(size), bold),
               fill=color or self.c["text"], anchor=anchor)

    def panel(self, d, box, fill=None, radius=10, outline=None):
        d.rounded_rectangle(tuple(self.p(v) for v in box), radius=self.p(radius),
                            fill=fill or self.c["card"], outline=outline or self.c["border"],
                            width=self.p(1))

    def header(self, d, title, subtitle=""):
        self.txt(d, 14, 12, title, 16, bold=True)
        if subtitle:
            self.txt(d, 14, 34, subtitle, 9, self.c["muted"])

    def save(self, im, name):
        path = self.out / name
        im.save(path, "PNG", optimize=True)
        return path

    def census(self, snapshot):
        im, d = self.canvas(172)
        self.panel(d, (5, 5, 295, 167), self.c["panel"], 12)
        self.header(d, "THE ROOK REPUBLIC", "A community built around the rook.")
        self.txt(d, 16, 61, "REPUBLIC CENSUS", 11, self.c["link"], True)
        count = snapshot.get("club", {}).get("members_count")
        self.txt(d, 16, 79, "Citizens", 10, self.c["muted"])
        self.txt(d, 16, 94, f"{int(count):,}" if isinstance(count, (int, float)) else "Unavailable", 23, bold=True)
        founded = self.config.get("project", {}).get("founded_date", "")
        try:
            date_label = datetime.strptime(founded, "%Y-%m-%d").strftime("%b %d, %Y").replace(" 0", " ")
        except ValueError:
            date_label = founded or "Not set"
        self.txt(d, 165, 82, "Founded", 9, self.c["muted"])
        self.txt(d, 165, 97, date_label, 11, bold=True)
        active = snapshot.get("active_matches")
        self.txt(d, 165, 123, "Active matches", 9, self.c["muted"])
        self.txt(d, 165, 138, active if active is not None else "—", 13, bold=True)
        goal = int(self.config.get("club", {}).get("member_goal", 0) or 0)
        if goal and isinstance(count, (int, float)):
            ratio = min(1.0, max(0.0, count / goal))
            self.panel(d, (16, 137, 145, 145), self.c["deep"], 4, self.c["deep"])
            d.rounded_rectangle((self.p(16), self.p(137), self.p(16 + 129 * ratio), self.p(145)),
                                radius=self.p(4), fill=self.c["green"])
            self.txt(d, 16, 149, f"Goal: {goal:,}", 8, self.c["muted"])
        self.txt(d, 280, 151, "NATIONAL PIECE: ROOK", 7, self.c["link"], anchor="ra")
        return self.save(im, "01-census.png")

    def avatar(self, url, username):
        if not url:
            return None
        safe = "".join(ch for ch in username if ch.isalnum() or ch in "-_")[:48] or "citizen"
        path = self.avatars / f"{safe}.jpg"
        if path.exists():
            try:
                return Image.open(path).convert("RGB")
            except OSError:
                path.unlink(missing_ok=True)
        try:
            from io import BytesIO
            res = requests.get(url, timeout=10, headers={"User-Agent": "RookRepublicRecovery/0.1"})
            res.raise_for_status()
            image = Image.open(BytesIO(res.content)).convert("RGB")
            image.save(path, "JPEG", quality=88)
            return image
        except Exception:
            return None

    def newest(self, snapshot):
        members = snapshot.get("newest_citizens") or []
        h = max(90, 54 + len(members) * 66)
        im, d = self.canvas(h)
        self.panel(d, (5, 5, 295, h - 5), radius=12)
        self.header(d, "NEWEST CITIZENS", "The latest members to join the Republic.")
        if not members:
            self.txt(d, 16, 62, "Citizen data is not available yet.", 10, self.c["muted"])
        for i, m in enumerate(members):
            y = 55 + i * 66
            self.panel(d, (13, y, 287, y + 58), self.c["deep"], 8, "#ffffff40")
            avatar = self.avatar(m.get("avatar"), m.get("username", "citizen"))
            if avatar:
                avatar = avatar.resize((self.p(42), self.p(42)))
                mask = Image.new("L", avatar.size, 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar.width - 1, avatar.height - 1), fill=255)
                im.paste(avatar, (self.p(21), self.p(y + 8)), mask)
            else:
                d.ellipse((self.p(21), self.p(y + 8), self.p(63), self.p(y + 50)),
                          fill=self.c["panel"], outline=self.c["border"], width=self.p(1))
                self.txt(d, 42, y + 17, "R", 17, bold=True, anchor="mm")
            username = m.get("username", "Unknown")
            self.txt(d, 72, y + 9, username, 11, bold=True)
            try:
                joined = datetime.fromtimestamp(int(m.get("joined", 0)), timezone.utc).astimezone(self.tz)
                joined_label = "Joined " + joined.strftime("%b %d, %Y").replace(" 0", " ")
            except (ValueError, OSError, OverflowError, TypeError):
                joined_label = "Join date unavailable"
            self.txt(d, 72, y + 27, joined_label, 8, self.c["muted"])
            rating = m.get("best_rating")
            rating_label = f"Top rating: {int(rating):,}" if isinstance(rating, (int, float)) else "Top rating: N/A"
            self.txt(d, 72, y + 41, rating_label, 8, self.c["green"])
        return self.save(im, "02-newest-citizens.png")

    def achievements(self):
        items = load_json(self.root / self.config["paths"]["achievements"], [])
        h = max(85, 54 + len(items) * 25)
        im, d = self.canvas(h)
        self.panel(d, (5, 5, 295, h - 5), radius=12)
        self.header(d, "REPUBLIC ACHIEVEMENTS", "Milestones reached and goals still ahead.")
        for i, item in enumerate(items):
            y = 55 + i * 25
            done = bool(item.get("complete"))
            col = self.c["green"] if done else self.c["muted"]
            self.txt(d, 17, y, "✓" if done else "○", 12, col, True)
            self.txt(d, 38, y + 1, item.get("label", "Achievement"), 9, self.c["text"] if done else self.c["muted"])
            self.txt(d, 280, y + 1, "UNLOCKED" if done else "LOCKED", 7, col, anchor="ra")
        return self.save(im, "03-achievements.png")

    def heroes(self):
        records = load_json(self.root / self.config["paths"]["heroes"], {}).get("records", [])
        outputs = []
        for part, start in enumerate(range(0, len(records), 21), 1):
            chunk = records[start:start + 21]
            h = max(75, 58 + len(chunk) * 22)
            im, d = self.canvas(h)
            self.panel(d, (5, 5, 295, h - 5), radius=12)
            self.header(d, "HALL OF HEROES", f"Rook sacrifices honored by the Republic · Part {part}")
            for i, item in enumerate(chunk):
                y = 57 + i * 22
                num = item.get("number", start + i + 1)
                label = item.get("source_label") or item.get("title") or f"The ROOOK #{num}"
                self.txt(d, 16, y, f"#{num}", 8, self.c["link"], True)
                self.txt(d, 48, y, label, 8, bold=True)
                self.txt(d, 280, y, item.get("username", "Unknown"), 7, self.c["muted"], anchor="ra")
            outputs.append(self.save(im, f"04-heroes-{part}.png"))
        return outputs

    def partners(self):
        items = load_json(self.root / self.config["paths"]["partners"], {}).get("items", [])
        h = max(85, 58 + len(items) * 48)
        im, d = self.canvas(h)
        self.panel(d, (5, 5, 295, h - 5), radius=12)
        self.header(d, "PARTNER CLUBS", "Communities connected with the Republic.")
        if not items:
            self.txt(d, 16, 62, "No partner clubs listed.", 9, self.c["muted"])
        for i, item in enumerate(items):
            y = 56 + i * 48
            self.panel(d, (13, y, 287, y + 40), self.c["deep"], 7, "#ffffff40")
            self.txt(d, 22, y + 8, item.get("name", "Unnamed partner"), 10, bold=True)
            review = item.get("source_status") == "needs_review"
            self.txt(d, 22, y + 24, "Destination needs review" if review else "Partner", 8, self.c["muted"])
        return self.save(im, "05-partners.png")

    def quick_links(self):
        groups = load_json(self.root / self.config["paths"]["quick_links"], {}).get("groups", [])
        lines = sum(1 + len(g.get("links", [])) for g in groups)
        h = max(100, 62 + lines * 20)
        im, d = self.canvas(h)
        self.panel(d, (5, 5, 295, h - 5), radius=12)
        self.header(d, "QUICK LINKS", "The Republic directory.")
        y = 55
        for group in groups:
            self.txt(d, 16, y, group.get("category", "Links"), 10, self.c["link"], True)
            y += 20
            for item in group.get("links", []):
                review = item.get("status") == "needs_review"
                label = textwrap.shorten(item.get("label", "Untitled link"), width=38, placeholder="…")
                self.txt(d, 24, y, "• " + label, 8, self.c["muted"] if review else self.c["text"])
                if review:
                    self.txt(d, 280, y, "REVIEW", 6, "#ffd166", anchor="ra")
                y += 18
            y += 4
        return self.save(im, "06-quick-links.png")

    def announcements(self):
        items = load_json(self.root / self.config["paths"]["announcements"], {"items": []}).get("items", [])
        if not items:
            return None
        h = 58 + len(items) * 42
        im, d = self.canvas(h)
        self.panel(d, (5, 5, 295, h - 5), radius=12)
        self.header(d, "REPUBLIC ANNOUNCEMENTS")
        for i, item in enumerate(items):
            y = 55 + i * 42
            self.txt(d, 16, y, item.get("title", "Announcement"), 10, bold=True)
            for j, line in enumerate(textwrap.wrap(item.get("text", ""), width=48)):
                self.txt(d, 16, y + 17 + j * 11, line, 8, self.c["muted"])
        return self.save(im, "07-announcements.png")

    def render_all(self, snapshot):
        paths = [self.census(snapshot), self.newest(snapshot), self.achievements(),
                 *self.heroes(), self.partners(), self.quick_links()]
        extra = self.announcements()
        if extra:
            paths.append(extra)
        return paths
