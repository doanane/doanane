import os
import re
import requests
from datetime import datetime, timezone

USERNAME = os.environ.get("USERNAME", "doanane")
GH_TOKEN = os.environ.get("GH_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

GRAPHQL_URL = "https://api.github.com/graphql"


def run_query(query, variables=None):
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables or {}},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ── Fetch contribution data via GraphQL ──────────────────────────────
CONTRIB_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
    repositories(first: 100, ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER], privacy: PRIVATE, orderBy: {field: UPDATED_AT, direction: DESC}) {
      totalCount
    }
    publicRepos: repositories(first: 100, ownerAffiliations: [OWNER], privacy: PUBLIC) {
      totalCount
    }
    followers { totalCount }
    following { totalCount }
    createdAt
  }
}
"""


def get_stats():
    data = run_query(CONTRIB_QUERY, {"login": USERNAME})
    user = data["data"]["user"]
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]

    total_contributions = cal["totalContributions"]
    total_commits = cc["totalCommitContributions"]
    total_prs = cc["totalPullRequestContributions"]
    total_issues = cc["totalIssueContributions"]
    total_repos = cc["totalRepositoryContributions"]
    followers = user["followers"]["totalCount"]
    public_repos = user["publicRepos"]["totalCount"]
    private_repos = user["repositories"]["totalCount"]

    # Calculate current streak
    all_days = []
    for week in cal["weeks"]:
        for day in week["contributionDays"]:
            all_days.append(day)
    all_days.sort(key=lambda d: d["date"], reverse=True)

    streak = 0
    for day in all_days:
        if day["contributionCount"] > 0:
            streak += 1
        else:
            break

    # Account age
    created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    years = (now - created).days // 365

    return {
        "total_contributions": total_contributions,
        "total_commits": total_commits,
        "total_prs": total_prs,
        "total_issues": total_issues,
        "total_repos": total_repos,
        "followers": followers,
        "public_repos": public_repos,
        "private_repos": private_repos,
        "streak": streak,
        "years": years,
        "last_updated": now.strftime("%d %b %Y at %H:%M UTC"),
    }


def update_readme(stats):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    replacements = {
        r"(TOTAL CONTRIBUTIONS-)[0-9,]+": f"TOTAL CONTRIBUTIONS-{stats['total_contributions']:,}",
        r"(Total Commits-)[0-9,]+": f"Total Commits-{stats['total_commits']:,}",
        r"(Pull Requests-)[0-9,]+": f"Pull Requests-{stats['total_prs']:,}",
        r"(Issues Opened-)[0-9,]+": f"Issues Opened-{stats['total_issues']:,}",
        r"(Current Streak-)[0-9]+%20days": f"Current Streak-{stats['streak']}%20days",
        r"(Followers-)[0-9]+": f"Followers-{stats['followers']}",
        r"(Public Repos-)[0-9]+": f"Public Repos-{stats['public_repos']}",
        r"(Private Repos-)[0-9]+": f"Private Repos-{stats['private_repos']}",
        r"(Last Updated-)[^-\"]+": f"Last Updated-{stats['last_updated'].replace(' ', '%20')}",
    }

    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"README updated — {stats['total_contributions']:,} total contributions, streak: {stats['streak']} days")


if __name__ == "__main__":
    stats = get_stats()
    print("Stats fetched:", stats)
    update_readme(stats)
