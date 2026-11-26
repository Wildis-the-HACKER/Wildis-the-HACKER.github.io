from datetime import datetime
import os
from PIL import Image, ImageDraw, ImageFont
import requests

# --- CONFIGURATION ---
CLUB_SLUG = "the-rook-republic-chess-club"
EVENTS_FILENAME = "events.txt"
OUTPUT_DIR = "sidebar-assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Dimensions & Styling (Rook Republic Dark Theme)
WIDTH = 300
BG_DARK = (22, 24, 29)
CARD_BG = (32, 35, 42)
ACCENT_GOLD = (230, 165, 50)
ACCENT_RED = (210, 65, 45)
TEXT_WHITE = (240, 242, 245)
TEXT_MUTED = (155, 162, 175)
BORDER_COLOR = (55, 60, 72)

# Fonts (Uses default scalable font; you can replace with a .ttf file in your repo)
font_header = ImageFont.load_default(size=18)
font_sub = ImageFont.load_default(size=13)
font_bold = ImageFont.load_default(size=14)
font_small = ImageFont.load_default(size=12)


def get_club_stats():
  url = f"https://chess.com{CLUB_SLUG}/members"
  headers = {"User-Agent": "RookRepublicSidebarGenerator/1.0"}
  try:
    res = requests.get(url, headers=headers, timeout=10).json()
    weekly = res.get("weekly", [])
    monthly = res.get("monthly", [])
    all_time = res.get("all_time", [])
    total = len(weekly) + len(monthly) + len(all_time)

    # Sort newest recruits by join timestamp
    recent = weekly + monthly
    recent.sort(key=lambda x: x.get("joined", 0), reverse=True)
    newest = [m["username"] for m in recent[:3]]
    return total, newest
  except Exception:
    return "N/A", ["Check Club Page"]


def parse_events(filepath):
  if not os.path.exists(filepath):
    return []

  with open(filepath, "r", encoding="utf-8") as f:
    raw_lines = f.readlines()

  # Strip top comments and group into blocks separated by blank lines
  blocks = []
  current_block = {}
  for line in raw_lines:
    clean = line.strip()
    if clean.startswith("#"):
      continue
    if not clean:
      if current_block:
        blocks.append(current_block)
        current_block = {}
      continue
    if ":" in clean:
      key, val = clean.split(":", 1)
      current_block[key.strip().lower()] = val.strip()

  if current_block:
    blocks.append(current_block)

  return blocks


def draw_header_card(total_members, newest_members):
  # Top header + Census stats (300 x 145)
  img = Image.new("RGB", (WIDTH, 145), BG_DARK)
  draw = ImageDraw.Draw(img)

  # Top accent bar & outer frame
  draw.rectangle([0, 0, WIDTH, 4], fill=ACCENT_GOLD)
  draw.line([(0, 0), (0, 145)], fill=BORDER_COLOR, width=2)
  draw.line([(WIDTH - 1, 0), (WIDTH - 1, 145)], fill=BORDER_COLOR, width=2)

  # Club Title
  draw.text(
      (16, 14), "THE ROOK REPUBLIC", fill=ACCENT_GOLD, font=font_header
  )
  draw.text(
      (16, 38), "Official Club Command Center", fill=TEXT_MUTED, font=font_small
  )

  # Stats Box
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

  img.save(os.path.join(OUTPUT_DIR, "01_header.png"))


def draw_event_slices(events):
  # Section Divider Banner (300 x 36)
  div_img = Image.new("RGB", (WIDTH, 36), BG_DARK)
  d_draw = ImageDraw.Draw(div_img)
  d_draw.line([(0, 0), (0, 36)], fill=BORDER_COLOR, width=2)
  d_draw.line([(WIDTH - 1, 0), (WIDTH - 1, 36)], fill=BORDER_COLOR, width=2)
  d_draw.text(
      (16, 10), "UPCOMING CLUB EVENTS", fill=ACCENT_RED, font=font_bold
  )
  div_img.save(os.path.join(OUTPUT_DIR, "02_events_title.png"))

  # Generate up to 6 individual clickable event banners
  max_slots = 6
  for i in range(max_slots):
    slot_path = os.path.join(OUTPUT_DIR, f"event_{i+1}.png")
    if i < len(events):
      ev = events[i]
      date_str = ev.get("date", "TBD")
      title_str = ev.get("event", "Club Event")
      time_str = ev.get("time", "")

      # Format YYYY-MM-DD into a cleaner label like "Oct 03" if possible
      try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        display_date = dt.strftime("%b %d").upper()
      except ValueError:
        display_date = date_str

      row_img = Image.new("RGB", (WIDTH, 54), BG_DARK)
      r_draw = ImageDraw.Draw(row_img)
      r_draw.line([(0, 0), (0, 54)], fill=BORDER_COLOR, width=2)
      r_draw.line([(WIDTH - 1, 0), (WIDTH - 1, 54)], fill=BORDER_COLOR, width=2)

      # Event Card Row
      r_draw.rounded_rectangle(
          [12, 3, WIDTH - 12, 50], radius=5, fill=CARD_BG, outline=BORDER_COLOR
      )
      # Date Pill
      r_draw.rounded_rectangle([18, 9, 76, 44], radius=4, fill=ACCENT_RED)
      r_draw.text((24, 19), display_date, fill=TEXT_WHITE, font=font_small)

      # Event Title & Time
      r_draw.text((86, 10), title_str[:24], fill=TEXT_WHITE, font=font_bold)
      r_draw.text((86, 29), f"Time: {time_str}", fill=TEXT_MUTED, font=font_small)

      row_img.save(slot_path)
    else:
      # Save a tiny 1x1 transparent pixel for unused slots so HTML links never break!
      empty = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
      empty.save(slot_path)

  # Footer Banner (300 x 38)
  foot_img = Image.new("RGB", (WIDTH, 38), BG_DARK)
  f_draw = ImageDraw.Draw(foot_img)
  f_draw.line([(0, 0), (0, 38)], fill=BORDER_COLOR, width=2)
  f_draw.line([(WIDTH - 1, 0), (WIDTH - 1, 38)], fill=BORDER_COLOR, width=2)
  f_draw.rectangle([0, 34, WIDTH, 38], fill=ACCENT_GOLD)
  f_draw.text(
      (52, 11), "Click any event above to join ->", fill=TEXT_MUTED, font=font_small
  )
  foot_img.save(os.path.join(OUTPUT_DIR, "99_footer.png"))


if __name__ == "__main__":
  total, newest = get_club_stats()
  events = parse_events(EVENTS_FILENAME)
  draw_header_card(total, newest)
  draw_event_slices(events)
