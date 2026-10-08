import os
import json
import urllib.request
from datetime import date, timedelta
from xml.sax.saxutils import escape

USERNAME = "niteshjan06"
OUTPUT = "assets/github-activity.svg"

TOKEN = os.environ["GITHUB_TOKEN"]

today = date.today()
start = today - timedelta(days=365)

query = """
query($from: DateTime!, $to: DateTime!) {
  user(login: "niteshjan06") {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

variables = {
    "from": f"{start.isoformat()}T00:00:00Z",
    "to": f"{today.isoformat()}T23:59:59Z"
}

payload = json.dumps({
    "query": query,
    "variables": variables
}).encode()

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "github-activity-generator"
    }
)

with urllib.request.urlopen(request) as response:
    data = json.loads(response.read().decode())

if "errors" in data:
    raise RuntimeError(data["errors"])

calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]

days = []

for week in calendar["weeks"]:
    for d in week["contributionDays"]:
        days.append({
            "date": d["date"],
            "count": d["contributionCount"],
            "level": d["contributionLevel"]
        })

days.sort(key=lambda x: x["date"])

# --------------------------------------------------
# Calculate current streak
# --------------------------------------------------

day_map = {d["date"]: d["count"] for d in days}

current_streak = 0
check_day = today

while True:
    key = check_day.isoformat()

    if day_map.get(key, 0) > 0:
        current_streak += 1
        check_day -= timedelta(days=1)
    else:
        break

# If today has no contribution, start from yesterday
if current_streak == 0:
    check_day = today - timedelta(days=1)

    while True:
        key = check_day.isoformat()

        if day_map.get(key, 0) > 0:
            current_streak += 1
            check_day -= timedelta(days=1)
        else:
            break

# --------------------------------------------------
# Calculate longest streak
# --------------------------------------------------

longest_streak = 0
running = 0

for d in days:
    if d["count"] > 0:
        running += 1
        longest_streak = max(longest_streak, running)
    else:
        running = 0

# --------------------------------------------------
# Total contributions
# --------------------------------------------------

total = calendar["totalContributions"]

# --------------------------------------------------
# Streak date ranges
# --------------------------------------------------

current_end = today
current_start = today

if current_streak > 0:
    current_start = today - timedelta(days=current_streak - 1)

# Find longest streak dates
best_start = None
best_end = None
running_start = None
running_length = 0

for d in days:
    if d["count"] > 0:
        if running_start is None:
            running_start = date.fromisoformat(d["date"])

        running_length += 1

        if running_length == longest_streak:
            best_start = running_start
            best_end = date.fromisoformat(d["date"])
    else:
        running_start = None
        running_length = 0

# --------------------------------------------------
# SVG helpers
# --------------------------------------------------

WIDTH = 1100
HEIGHT = 500

svg = []

svg.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">'
)

svg.append("""
<rect width="1100" height="500" rx="12" fill="#0d1117"/>
""")

# Title
svg.append("""
<text x="28" y="42"
      fill="#f0f6fc"
      font-family="Arial, Helvetica, sans-serif"
      font-size="25"
      font-weight="700">
  ⚡ GitHub Activity
</text>
""")

svg.append("""
<line x1="20" y1="58" x2="1080" y2="58"
      stroke="#30363d" stroke-width="1"/>
""")

# --------------------------------------------------
# Statistics
# --------------------------------------------------

columns = [320, 550, 780]

stats = [
    (str(total), "Total Contributions"),
    (str(current_streak), "Current Streak"),
    (str(longest_streak), "Longest Streak")
]

for x, (number, label) in zip(columns, stats):

    svg.append(
        f'<text x="{x}" y="125" text-anchor="middle" '
        f'fill="#79b8ff" font-family="Arial" '
        f'font-size="34" font-weight="700">{number}</text>'
    )

    svg.append(
        f'<text x="{x}" y="160" text-anchor="middle" '
        f'fill="#79b8ff" font-family="Arial" '
        f'font-size="15">{label}</text>'
    )

# Current streak date
if current_streak > 0:
    current_text = current_start.strftime("%d %b") + " - " + current_end.strftime("%d %b")
else:
    current_text = today.strftime("%d %b")

svg.append(
    f'<text x="550" y="190" text-anchor="middle" '
    f'fill="#56d364" font-family="Arial" font-size="13">'
    f'{escape(current_text)}</text>'
)

# Longest streak date
if best_start and best_end:
    best_text = best_start.strftime("%d %b") + " - " + best_end.strftime("%d %b")
else:
    best_text = "—"

svg.append(
    f'<text x="780" y="190" text-anchor="middle" '
    f'fill="#56d364" font-family="Arial" font-size="13">'
    f'{escape(best_text)}</text>'
)

# Date range
svg.append(
    f'<text x="320" y="190" text-anchor="middle" '
    f'fill="#56d364" font-family="Arial" font-size="13">'
    f'{start.strftime("%d %b %Y")} - Present</text>'
)

# --------------------------------------------------
# Contribution heatmap
# --------------------------------------------------

# Group into weeks
weeks = []

for i in range(0, len(days), 7):
    week = days[i:i + 7]

    if week:
        weeks.append(week)

cell = 15
gap = 5
start_x = 28
start_y = 340

colors = {
    "NONE": "#161b22",
    "FIRST_QUARTILE": "#0e4429",
    "SECOND_QUARTILE": "#006d32",
    "THIRD_QUARTILE": "#26a641",
    "FOURTH_QUARTILE": "#39d353"
}

for week_index, week in enumerate(weeks):

    x = start_x + week_index * (cell + gap)

    for day_index, d in enumerate(week):

        y = start_y + day_index * (cell + gap)

        level = d["level"]

        color = colors.get(level, "#161b22")

        svg.append(
            f'<rect x="{x}" y="{y}" '
            f'width="{cell}" height="{cell}" rx="3" '
            f'fill="{color}"/>'
        )

# --------------------------------------------------
# Footer
# --------------------------------------------------

svg.append(
    '<text x="28" y="470" fill="#8b949e" '
    'font-family="Arial" font-size="12">'
    'Contribution activity • Updated automatically'
    '</text>'
)

svg.append("</svg>")

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(svg))

print("GitHub activity SVG generated successfully.")
print("Total contributions:", total)
print("Current streak:", current_streak)
print("Longest streak:", longest_streak)
