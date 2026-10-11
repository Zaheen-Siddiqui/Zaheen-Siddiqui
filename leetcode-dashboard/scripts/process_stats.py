"""Generate the SVG dashboard embedded by the GitHub profile README."""

from __future__ import annotations

import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
source_path = ROOT / "data" / "leetcode_data.json"
output_path = ROOT / "data" / "dashboard.svg"


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def text(value: Any) -> str:
    return html.escape(str(value or ""))


def short_number(value: int) -> str:
    return f"{value:,}"


def main() -> None:
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    matched = raw.get("profile", {}).get("matchedUser") or {}
    profile = matched.get("profile") or {}
    stats = matched.get("submitStatsGlobal") or {}
    accepted = {item["difficulty"]: safe_int(item.get("count")) for item in stats.get("acSubmissionNum", [])}
    totals = {item["difficulty"]: safe_int(item.get("submissions")) for item in stats.get("totalSubmissionNum", [])}
    solved = accepted.get("All", sum(accepted.get(key, 0) for key in ("Easy", "Medium", "Hard")))
    submissions = totals.get("All", sum(totals.get(key, 0) for key in ("Easy", "Medium", "Hard")))
    rate = solved / max(submissions, 1) * 100

    calendar_raw = matched.get("submissionCalendar") or "{}"
    calendar = json.loads(calendar_raw) if isinstance(calendar_raw, str) else calendar_raw
    recent = (raw.get("recent", {}).get("recentAcSubmissionList") or [])[:5]
    groups = matched.get("tagProblemCounts") or {}
    skills = []
    for group, tags in groups.items():
        if isinstance(tags, list):
            useful = sorted(
                (tag for tag in tags if safe_int(tag.get("problemsSolved")) > 0),
                key=lambda tag: safe_int(tag.get("problemsSolved")),
                reverse=True,
            )
            if useful:
                skills.append((group.title(), useful[:5]))
    contest = raw.get("contest", {}).get("userContestRanking") or {}
    updated = raw.get("fetchedAt", datetime.now(timezone.utc).isoformat())[:10]

    def rect(x: int, y: int, width: int, height: int, fill: str, radius: int = 8) -> str:
        return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}"/>'

    svg: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="770" viewBox="0 0 1000 770">',
        "<defs><linearGradient id=\"glow\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\"><stop stop-color=\"#17281e\"/><stop offset=\"1\" stop-color=\"#101615\"/></linearGradient></defs>",
        '<rect width="1000" height="770" rx="18" fill="#101615"/>',
        '<rect x="1" y="1" width="998" height="768" rx="17" fill="none" stroke="#2b3a35"/>',
        '<style>text{font-family:Arial,sans-serif}.mono{font-family:monospace}.muted{fill:#91a39a}.green{fill:#b8f36b}.white{fill:#edf5ee}.line{stroke:#2b3a35}</style>',
        f'<text x="42" y="48" class="mono muted" font-size="13" letter-spacing="2">ALGORITHM LOG / UPDATED {text(updated)}</text>',
        f'<text x="42" y="96" class="white" font-size="34" font-weight="bold">{text(profile.get("realName") or raw.get("username", "LeetCode profile"))}</text>',
        '<text x="42" y="123" class="muted" font-size="16">LeetCode problem-solving progress</text>',
        f'<text x="930" y="92" text-anchor="end" class="green" font-size="52" font-weight="bold">{short_number(solved)}</text>',
        '<text x="930" y="119" text-anchor="end" class="muted mono" font-size="12">PROBLEMS SOLVED</text>',
    ]

    cards = [
        ("TOTAL SOLVED", short_number(solved), "all difficulties"),
        ("ACCEPTANCE RATE", f"{rate:.1f}%", "accepted / submitted"),
        ("CONTEST RATING", short_number(safe_int(contest.get("rating"))) if contest.get("rating") else "—", "current rating"),
        ("GLOBAL RANK", f"#{short_number(safe_int(contest.get('globalRanking')))}" if contest.get("globalRanking") else "—", "among contestants"),
    ]
    for index, (label, value, caption) in enumerate(cards):
        x = 42 + index * 231
        svg += [rect(x, 160, 215, 108, "url(#glow)"), f'<text x="{x + 18}" y="185" class="muted mono" font-size="11">{label}</text>',
                f'<text x="{x + 18}" y="230" class="green" font-size="30" font-weight="bold">{value}</text>',
                f'<text x="{x + 18}" y="251" class="muted" font-size="12">{caption}</text>']

    svg += [
        '<text x="42" y="315" class="muted mono" font-size="11" letter-spacing="2">DIFFICULTY BREAKDOWN</text>',
        '<text x="42" y="348" class="white" font-size="22" font-weight="bold">Accepted problems</text>',
    ]
    colors = {"Easy": "#b8f36b", "Medium": "#ffb454", "Hard": "#ff7979"}
    for index, difficulty in enumerate(("Easy", "Medium", "Hard")):
        y = 385 + index * 45
        value = accepted.get(difficulty, 0)
        width = int(470 * value / max(solved, 1))
        svg += [f'<text x="42" y="{y}" class="muted" font-size="13">{difficulty}</text>',
                f'<text x="510" y="{y}" text-anchor="end" class="white mono" font-size="13">{short_number(value)}</text>',
                rect(42, y + 10, 468, 7, "#26342f", 4), rect(42, y + 10, width, 7, colors[difficulty], 4)]

    svg += [
        '<text x="560" y="315" class="muted mono" font-size="11" letter-spacing="2">SUBMISSION ACTIVITY</text>',
        '<text x="560" y="348" class="white" font-size="22" font-weight="bold">Last 6 months</text>',
    ]
    end = datetime.now(timezone.utc).date()
    values = [safe_int(calendar.get(str(int(datetime.combine(end - timedelta(days=day), datetime.min.time(), tzinfo=timezone.utc).timestamp())))) for day in range(181, -1, -1)]
    max_daily = max(values or [1])
    for index, value in enumerate(values):
        x = 560 + (index % 26) * 15
        y = 370 + (index // 26) * 17
        level = min(4, max(1, round(value / max_daily * 4))) if value else 0
        fill = ["#26342f", "#496c44", "#6d9e50", "#95c85c", "#b8f36b"][level]
        svg.append(rect(x, y, 10, 10, fill, 2))

    svg += ['<line x1="42" y1="535" x2="958" y2="535" class="line"/>',
            '<text x="42" y="568" class="muted mono" font-size="11" letter-spacing="2">RECENT ACCEPTED</text>']
    for index, item in enumerate(recent):
        y = 598 + index * 27
        title = text(item.get("title", "Problem"))
        language = text(item.get("lang", ""))
        svg += [f'<text x="42" y="{y}" class="white" font-size="14">{title[:58]}</text>',
                f'<text x="958" y="{y}" text-anchor="end" class="muted mono" font-size="11">{language}</text>']

    skill_text = " · ".join(
        f"{group}: {', '.join(text(tag.get('tagName')) for tag in tags[:4])}" for group, tags in skills
    )
    svg += [
        '<text x="42" y="748" class="muted mono" font-size="11">SKILLS</text>',
        f'<text x="105" y="748" class="muted" font-size="11">{skill_text[:130]}</text>',
        "</svg>",
    ]
    output_path.write_text("".join(svg), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
