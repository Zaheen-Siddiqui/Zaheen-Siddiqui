import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, timedelta
from html import escape

USERNAME = "Zaheen-Siddiqui"
README_PATH = "README.md"
SVG_PATH = "assets/github-analytics.svg"
START_MARKER = "<!-- GITHUB_ANALYTICS:START -->"
END_MARKER = "<!-- GITHUB_ANALYTICS:END -->"

TOKEN = os.environ.get("ANALYTICS_TOKEN")
API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"


def request_json(url, token=TOKEN, payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-profile-analytics",
    }
    if token:
        headers["Authorization"] = "Bearer " + token

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_repositories():
    repositories = []
    page = 1
    while True:
        url = f"{API}/users/{USERNAME}/repos?type=owner&per_page=100&page={page}"
        batch = request_json(url)
        if not batch:
            break
        repositories.extend(
            repo for repo in batch if not repo["private"] and not repo["fork"]
        )
        if len(batch) < 100:
            break
        page += 1
    return repositories


def get_contributions_and_streak():
    today = date.today()
    start = today - timedelta(days=364)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """
    result = request_json(
        GRAPHQL,
        payload={
            "query": query,
            "variables": {
                "login": USERNAME,
                "from": f"{start.isoformat()}T00:00:00Z",
                "to": f"{today.isoformat()}T23:59:59Z",
            },
        },
    )
    if result.get("errors"):
        raise RuntimeError(f"GraphQL error: {result['errors']}")

    calendar = result["data"]["user"]["contributionsCollection"][
        "contributionCalendar"
    ]
    days = sorted(
        (day["date"], day["contributionCount"] > 0)
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    )
    longest = current = 0
    previous = None
    for day_string, active in days:
        current = (
            current + 1
            if active and previous == date.fromisoformat(day_string) - timedelta(days=1)
            else 1 if active else 0
        )
        longest = max(longest, current)
        previous = date.fromisoformat(day_string)
    return calendar["totalContributions"], longest


def get_languages(repositories):
    totals = Counter()
    for repo in repositories:
        for language, byte_count in request_json(repo["languages_url"]).items():
            totals[language] += byte_count
    return totals


def get_authored_pr_count():
    query = urllib.parse.quote(f"author:{USERNAME} type:pr")
    result = request_json(f"{API}/search/issues?q={query}&per_page=1")
    return result["total_count"]


def percentage(value, total):
    return f"{value / total * 100:.2f}%" if total else "0.00%"


def build_svg(stats):
    languages = stats["languages"]
    total_bytes = sum(languages.values())
    language_items = languages.most_common(6)
    if len(languages) > len(language_items):
        language_items.append(
            ("Other", total_bytes - sum(value for _, value in language_items))
        )

    colors = ["#2f81f7", "#bc8cff", "#f0883e", "#3fb950", "#db61a2", "#a371f7", "#8b949e"]
    bar_x, bar_width, bar_y, bar_height = 24, 752, 466, 18
    bar_parts = []
    legend_parts = []
    current_x = bar_x
    for index, (language, byte_count) in enumerate(language_items):
        width = bar_width * byte_count / total_bytes if total_bytes else 0
        color = colors[index % len(colors)]
        bar_parts.append(
            f'<rect x="{current_x:.2f}" y="{bar_y}" width="{width:.2f}" '
            f'height="{bar_height}" fill="{color}"/>'
        )
        legend_x = 24 + (index % 2) * 376
        legend_y = 518 + (index // 2) * 28
        legend_parts.append(
            f'<circle cx="{legend_x}" cy="{legend_y - 5}" r="5" fill="{color}"/>'
            f'<text x="{legend_x + 14}" y="{legend_y}" class="language">'
            f"{escape(language)} {percentage(byte_count, total_bytes)}</text>"
        )
        current_x += width

    height = 542 + max(0, (len(language_items) - 1) // 2) * 28
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{height}" viewBox="0 0 800 {height}" role="img" aria-labelledby="title desc">
  <title id="title">GitHub Analytics</title>
  <desc id="desc">Live GitHub repository statistics and language usage for {escape(USERNAME)}.</desc>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
    .heading, .value, .small-value, .language {{ fill: #1f2328; }}
    .heading {{ font-size: 22px; font-weight: 600; }}
    .label {{ fill: #656d76; font-size: 13px; }}
    .value {{ font-size: 27px; font-weight: 600; }}
    .small-value {{ font-size: 16px; font-weight: 600; }}
    .sub {{ fill: #656d76; font-size: 12px; }}
    .language {{ font-size: 15px; }}
    .border {{ stroke: #d1d9e0; stroke-width: 1; fill: none; }}
    .icon {{ stroke: #656d76; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; fill: none; }}
    @media (prefers-color-scheme: dark) {{
      .heading, .value, .small-value, .language {{ fill: #e6edf3; }}
      .label, .sub {{ fill: #9198a1; }}
      .icon {{ stroke: #9198a1; }}
      .border {{ stroke: #3d444d; }}
    }}
  </style>
  <rect width="800" height="{height}" rx="8" fill="transparent"/>
  <rect x="0.5" y="54.5" width="383" height="105" rx="8" class="border"/>
  <rect x="400.5" y="54.5" width="399" height="105" rx="8" class="border"/>
  <rect x="0.5" y="171.5" width="383" height="105" rx="8" class="border"/>
  <rect x="400.5" y="171.5" width="399" height="105" rx="8" class="border"/>
  <text x="24" y="87" class="label">Total contributions</text>
  <text x="24" y="124" class="value">{stats["contributions"]:,}</text>
  <text x="24" y="144" class="sub">Past 12 months</text>
  <text x="424" y="87" class="label">Repositories</text>
  <text x="424" y="124" class="value">{stats["repositories"]}</text>
  <text x="424" y="144" class="sub">Public projects</text>
  <text x="24" y="205" class="label">Stars earned</text>
  <text x="24" y="242" class="value">{stats["stars"]:,}</text>
  <text x="424" y="205" class="label">Forks</text>
  <text x="424" y="242" class="value">{stats["forks"]:,}</text>
  <path d="M0 296.5H800M0 359.5H800M0 420.5H800" class="border"/>
  <text x="24" y="324" class="small-value">Pull requests</text>
  <text x="24" y="343" class="sub">Total PRs created</text>
  <text x="776" y="335" text-anchor="end" class="small-value">{stats["pull_requests"]:,}</text>
  <text x="24" y="387" class="small-value">Longest contribution streak</text>
  <text x="24" y="406" class="sub">Consecutive active days</text>
  <text x="776" y="398" text-anchor="end" class="small-value">{stats["longest_streak"]} days</text>
  <text x="24" y="450" class="small-value">Languages</text>
  <text x="776" y="450" text-anchor="end" class="sub">Repository code by bytes</text>
  <clipPath id="language-bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" rx="9"/></clipPath>
  <g clip-path="url(#language-bar)">{"".join(bar_parts)}</g>
  {"".join(legend_parts)}
</svg>
"""


def build_section(stats):
    return f"""## GitHub Analytics

{START_MARKER}
<p align="center">
  <img src="./assets/github-analytics.svg" alt="GitHub Analytics" width="100%" />
</p>

| Metric | Value | Metric | Value |
|:--|--:|:--|--:|
| Contributions (12 months) | `{stats["contributions"]:,}` | Public repositories | `{stats["repositories"]}` |
| Stars earned | `{stats["stars"]:,}` | Forks | `{stats["forks"]:,}` |
| Pull requests authored | `{stats["pull_requests"]:,}` | Longest streak | `{stats["longest_streak"]} days` |

{END_MARKER}"""


def update_readme(section):
    with open(README_PATH, "r", encoding="utf-8") as file:
        readme = file.read()
    if START_MARKER not in readme or END_MARKER not in readme:
        raise RuntimeError("Analytics markers are missing from README.md")
    start = readme.index(START_MARKER)
    end = readme.index(END_MARKER) + len(END_MARKER)
    updated = readme[:start] + section.split("\n\n", 1)[1] + readme[end:]
    if updated != readme:
        with open(README_PATH, "w", encoding="utf-8") as file:
            file.write(updated)
        print("README.md updated.")
    else:
        print("No statistics changes detected.")


def write_svg(svg):
    with open(SVG_PATH, "w", encoding="utf-8") as file:
        file.write(svg)


if __name__ == "__main__":
    try:
        repositories = get_repositories()
        contributions, longest_streak = get_contributions_and_streak()
        stats = {
            "contributions": contributions,
            "longest_streak": longest_streak,
            "stars": sum(repo["stargazers_count"] for repo in repositories),
            "forks": sum(repo["forks_count"] for repo in repositories),
            "repositories": len(repositories),
            "pull_requests": get_authored_pr_count(),
            "languages": get_languages(repositories),
        }
        write_svg(build_svg(stats))
        update_readme(build_section(stats))
    except (KeyError, TypeError, urllib.error.URLError, TimeoutError, RuntimeError) as error:
        raise SystemExit(f"Analytics update failed: {error}")
