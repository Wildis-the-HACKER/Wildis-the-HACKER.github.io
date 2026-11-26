from datetime import datetime
import os
from PIL import Image, ImageDraw, ImageFont
import requests

# --- CONFIGURATION ---
CLUB_SLUG = "the-rook-republic-chess-club"
BASE_DIR = "republic_recovery"
EVENTS_FILE = os.path.join(BASE_DIR, "events.txt")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
GO_DIR = os.path.join(BASE_DIR, "go")
MAX_SIDEBAR_SLOTS = 8  # Shows the next 8 upcoming events in the sidebar

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(GO_DIR, exist_ok=True)

# Theme Colors (Rook Republic Dark Mode)
WIDTH = 300
BG_DARK = (22, 24, 29)
CARD_BG = (32, 35, 42)
ACCENT_GOLD = (230, 165, 50)
ACCENT_RED = (210, 65, 45)
TEXT_WHITE = (240, 242, 245)
TEXT_MUTED = (155, 162, 175)
BORDER_COLOR = (55, 60, 72)

font_header = ImageFont.load_default(size=18)
font_bold = ImageFont.load_default(size=14)
font_small = ImageFont.load_default(size=12)


def get_club_stats():
  url = f"https://chess.com{CLUB_SLUG}/members"
  headers = {"User-Agent": "RookRepublicSidebarBot/1.0"}
  try:
    res = requests.get(url, headers=headers, timeout=10).json()
    weekly = res.get("weekly", [])
    monthly = res.get("monthly", [])
    all_time = res.get("all_time", [])
    total = len(weekly) + len(monthly) + len(all_time)

    recent = weekly + monthly
    recent.sort(key=lambda x: x.get("joined", 0), reverse=True)
    newest = [m["username"] for m in recent[:3]]
    return total, newest
  except Exception:
    return "N/A", ["Check Club Page"]


def parse_and_filter_events(filepath):
  if not os.path.exists(filepath):
    return [], 0

  with open(filepath, "r", encoding="utf-8") as f:
    raw_lines = f.readlines()

  blocks = []
  current = {}
  for line in raw_lines:
    clean = line.strip()
    if clean.startswith("#"):
      continue
    if not clean:
      if current:
        blocks.append(current)
        current = {}
      continue
    if ":" in clean:
      key, val = clean.split(":", 1)
      current[key.strip().lower()] = val.strip()
  if current:
    blocks.append(current)

  total_db_count = len(blocks)
  today_str = datetime.utcnow().strftime("%Y-%m-%d")

  # Keep only today's and future events, sorted chronologically
  upcoming = []
  for b in blocks:
    ev_date = b.get("date", "9999-12-31")
    if ev_date >= today_str:
      upcoming.append(b)

  upcoming.sort(key=lambda x: x.get("date", "9999-12-31"))
  return upcoming, total_db_count


def build_header(total_members, newest_members):
  img = Image.new("RGB", (WIDTH, 145), BG_DARK)
  draw = ImageDraw.Draw(img)

  draw.rectangle([0, 0, WIDTH, 4], fill=ACCENT_GOLD)
  draw.line([(0, 0), (0, 145)], fill=BORDER_COLOR, width=2)
  draw.line([(WIDTH - 1, 0), (WIDTH - 1, 145)], fill=BORDER_COLOR, width=2)

  draw.text(
      (16, 14), "THE ROOK REPUBLIC", fill=ACCENT_GOLD, font=font_header
  )
  draw.text(
      (16, 38), "Official Club Command Center", fill=TEXT_MUTED, font=font_small
  )

  draw.rounded_rectangle(
      [12, 60, WIDTH - 12, 132], radius=6, fill=CARD_BG, outline=BORDER_COLOR
  )
  draw.text(
      (22, 68),
      f"Citizens: {total_members}",
      fill=TEXT_WHITE,
      font=font_bold,
  )
  draw.text(
      (22, 90), "Newest Recruits:", fill=ACCENT_GOLD, font=font_small
  )

  recruits_text = ", ".join(newest_members) if newest_members else "None yet"
  if len(recruits_text) > 36:
    recruits_text = recruits_text[:33] + "..."
  draw.text((22, 108), recruits_text, fill=TEXT_WHITE, font=font_small)

  img.save(os.path.join(ASSETS_DIR, "01_header.png"))


def build_events(upcoming_events, total_db_count):
  # Section Divider
  div_img = Image.new("RGB", (WIDTH, 36), BG_DARK)
  d_draw = ImageDraw.Draw(div_img)
  d_draw.line([(0, 0), (0, 36)], fill=BORDER_COLOR, width=2)
  d_draw.line([(WIDTH - 1, 0), (WIDTH - 1, 36)], fill=BORDER_COLOR, width=2)
  d_draw.text(
      (16, 10),
      f"UPCOMING EVENTS ({len(upcoming_events)} ACTIVE)",
      fill=ACCENT_RED,
      font=font_bold,
  )
  div_img.save(os.path.join(ASSETS_DIR, "02_events_title.png"))

  # Generate the next 8 slots + auto-updating redirect HTML files
  for i in range(MAX_SIDEBAR_SLOTS):
    img_path = os.path.join(ASSETS_DIR, f"event_{i+1}.png")
    go_path = os.path.join(GO_DIR, f"event{i+1}.html")

    if i < len(upcoming_events):
      ev = upcoming_events[i]
      date_str = ev.get("date", "TBD")
      title_str = ev.get("event", "Club Event")
      time_str = ev.get("time", "")
      link_url = ev.get(
          "link", f"https://chess.com{CLUB_SLUG}"
      )

      try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        display_date = dt.strftime("%b %d").upper()
      except ValueError:
        display_date = date_str[:6]

      row_img = Image.new("RGB", (WIDTH, 54), BG_DARK)
      r_draw = ImageDraw.Draw(row_img)
      r_draw.line([(0, 0), (0, 54)], fill=BORDER_COLOR, width=2)
      r_draw.line([(WIDTH - 1, 0), (WIDTH - 1, 54)], fill=BORDER_COLOR, width=2)

      r_draw.rounded_rectangle(
          [12, 3, WIDTH - 12, 50], radius=5, fill=CARD_BG, outline=BORDER_COLOR
      )
      r_draw.rounded_rectangle([18, 12, 78, 41], radius=4, fill=ACCENT_RED)
      r_draw.text((24, 19), display_date, fill=TEXT_WHITE, font=font_small)

      r_draw.text((86, 10), title_str[:24], fill=TEXT_WHITE, font=font_bold)
      r_draw.text((86, 29), f"Time: {time_str}", fill=TEXT_MUTED, font=font_small)
      row_img.save(img_path)

      with open(go_path, "w", encoding="utf-8") as f:
        f.write(
            f'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url={link_url}"></head></html>'
        )
    else:
      # Invisible 1x1 pixel when fewer than 8 upcoming events remain
      Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(img_path)
      with open(go_path, "w", encoding="utf-8") as f:
        f.write(
            f'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url=https://github.io{BASE_DIR}/"></head></html>'
        )

  # Footer Banner linking to the full 100+ event database viewer
  foot_img = Image.new("RGB", (WIDTH, 42), BG_DARK)
  f_draw = ImageDraw.Draw(foot_img)
  f_draw.line([(0, 0), (0, 42)], fill=BORDER_COLOR, width=2)
  f_draw.line([(WIDTH - 1, 0), (WIDTH - 1, 42)], fill=BORDER_COLOR, width=2)
  f_draw.rectangle([0, 38, WIDTH, 42], fill=ACCENT_GOLD)
  f_draw.text(
      (28, 12),
      f"View Full Calendar ({total_db_count} Events) ->",
      fill=ACCENT_GOLD,
      font=font_small,
  )
  foot_img.save(os.path.join(ASSETS_DIR, "99_footer.png"))


if __name__ == "__main__":
  total, newest = get_club_stats()
  upcoming, total_count = parse_and_filter_events(EVENTS_FILE)
  build_header(total, newest)
  build_events(upcoming, total_count)
