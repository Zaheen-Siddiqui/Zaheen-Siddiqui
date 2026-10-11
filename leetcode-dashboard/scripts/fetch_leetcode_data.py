"""Fetch the public LeetCode profile data used by the dashboard."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

USERNAME = os.getenv("LEETCODE_USERNAME")
ENDPOINT = "https://leetcode.com/graphql"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "leetcode_data.json"

QUERIES: dict[str, str] = {
    "profile": """query userProfile($username: String!) {
      matchedUser(username: $username) {
        username profile { realName userAvatar ranking reputation starRating aboutMe }
        submitStatsGlobal { acSubmissionNum { difficulty count submissions } totalSubmissionNum { difficulty count submissions } }
        submissionCalendar
        contributions { points }
        badges { id displayName icon creationDate }
        tagProblemCounts { advanced { tagName problemsSolved } intermediate { tagName problemsSolved } fundamental { tagName problemsSolved } }
      }
    }""",
    "recent": """query recentAc($username: String!) {
      recentAcSubmissionList(username: $username, limit: 20) { id title titleSlug timestamp lang }
    }""",
    "contest": """query contest($username: String!) {
      userContestRanking(username: $username) { attendedContestsCount rating globalRanking totalParticipants topPercentage }
      userContestRankingHistory(username: $username) { attended rating ranking contest { title startTime } }
    }""",
}


def request(query: str) -> dict[str, Any]:
    response = requests.post(
        ENDPOINT,
        json={"query": query, "variables": {"username": USERNAME}},
        headers={"Content-Type": "application/json", "User-Agent": "Zaheen-Siddiqui-LeetCode-Dashboard/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError("; ".join(error.get("message", "GraphQL request failed") for error in payload["errors"]))
    return payload.get("data", {})


def main() -> None:
    if not USERNAME:
        raise RuntimeError("LEETCODE_USERNAME is required; configure it as a GitHub Actions secret.")
    raw: dict[str, Any] = {"username": USERNAME, "fetchedAt": datetime.now(timezone.utc).isoformat()}
    for name, query in QUERIES.items():
        try:
            raw[name] = request(query)
        except (requests.RequestException, ValueError, RuntimeError) as error:
            print(f"Warning: {name} request failed: {error}", file=sys.stderr)
            raw[name] = {}
    if not raw.get("profile", {}).get("matchedUser"):
        raise RuntimeError(f"LeetCode profile not found for {USERNAME!r}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()