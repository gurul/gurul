#!/usr/bin/env python3
"""
Dynamic GitHub Profile Updater
Tracks coding streak and language usage from GitHub activity.
"""

import os
import re
import requests
from datetime import datetime, timedelta
from collections import defaultdict

GITHUB_TOKEN = os.environ.get("GH_TOKEN")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "your-username")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

GRAPHQL_ENDPOINT = "https://api.github.com/graphql"


def get_contribution_data():
    """Fetch contribution data using GitHub GraphQL API."""
    query = """
    query($username: String!) {
        user(login: $username) {
            contributionsCollection {
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
            repositories(first: 100, ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER], privacy: null, orderBy: {field: UPDATED_AT, direction: DESC}) {
                nodes {
                    name
                    languages(first: 50, orderBy: {field: SIZE, direction: DESC}) {
                        edges {
                            size
                            node {
                                name
                                color
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    response = requests.post(
        GRAPHQL_ENDPOINT,
        json={"query": query, "variables": {"username": GITHUB_USERNAME}},
        headers=HEADERS
    )
    
    if response.status_code != 200:
        print(f"Error fetching data: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()


def calculate_streak(contribution_data):
    """Calculate current coding streak from contribution calendar."""
    if not contribution_data:
        return 0, 0
    
    try:
        calendar = contribution_data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        total_contributions = calendar["totalContributions"]
        
        all_days = []
        for week in calendar["weeks"]:
            for day in week["contributionDays"]:
                all_days.append({
                    "date": datetime.strptime(day["date"], "%Y-%m-%d").date(),
                    "count": day["contributionCount"]
                })
        
        all_days.sort(key=lambda x: x["date"], reverse=True)
        
        streak = 0
        today = datetime.now().date()
        
        for i, day in enumerate(all_days):
            expected_date = today - timedelta(days=i)
            
            if i == 0 and day["date"] == today and day["count"] == 0:
                continue
            
            if day["date"] == expected_date or (i == 0 and day["date"] == today - timedelta(days=1)):
                if day["count"] > 0:
                    streak += 1
                else:
                    break
            elif day["date"] < expected_date:
                break
        
        return streak, total_contributions
        
    except (KeyError, TypeError) as e:
        print(f"Error calculating streak: {e}")
        return 0, 0


def get_language_stats(contribution_data):
    """Aggregate language statistics across all repositories."""
    if not contribution_data:
        return {}
    
    try:
        repos = contribution_data["data"]["user"]["repositories"]["nodes"]
        language_bytes = defaultdict(int)
        
        for repo in repos:
            if repo["languages"]["edges"]:
                for lang in repo["languages"]["edges"]:
                    language_bytes[lang["node"]["name"]] += lang["size"]
        
        sorted_langs = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)
        
        total_bytes = sum(language_bytes.values())
        if total_bytes == 0:
            return {}
        
        language_stats = {}
        for lang, bytes_count in sorted_langs:
            percentage = (bytes_count / total_bytes) * 100
            language_stats[lang] = percentage
        
        return language_stats
        
    except (KeyError, TypeError) as e:
        print(f"Error getting language stats: {e}")
        return {}


def generate_streak_section(streak, total_contributions):
    """Generate the streak display section."""
    section = f"""**{streak}** days consecutive coding

Total contributions this year: **{total_contributions}**"""
    
    return section


def generate_languages_section(language_stats):
    """Generate the languages table section."""
    if not language_stats:
        return "No language data available"
    
    rows = ["| Language | Usage |", "|----------|-------|"]
    
    for lang, percentage in language_stats.items():
        rows.append(f"| {lang} | {percentage:.1f}% |")
    
    return "\n".join(rows)


def update_readme(streak_section, languages_section):
    """Update the README.md with new sections."""
    readme_path = "README.md"
    
    with open(readme_path, "r") as f:
        content = f.read()
    
    content = re.sub(
        r"<!--START_SECTION:streak-->.*?<!--END_SECTION:streak-->",
        f"<!--START_SECTION:streak-->\n{streak_section}\n<!--END_SECTION:streak-->",
        content,
        flags=re.DOTALL
    )
    
    content = re.sub(
        r"<!--START_SECTION:languages-->.*?<!--END_SECTION:languages-->",
        f"<!--START_SECTION:languages-->\n{languages_section}\n<!--END_SECTION:languages-->",
        content,
        flags=re.DOTALL
    )
    
    now = datetime.now().strftime("%B %d, %Y at %H:%M UTC")
    content = re.sub(
        r"<sub>Last updated:.*?</sub>",
        f"<sub>Last updated: {now}</sub>",
        content
    )
    
    with open(readme_path, "w") as f:
        f.write(content)
    
    print(f"README updated successfully at {now}")


def main():
    print("Fetching GitHub data...")
    data = get_contribution_data()
    
    if not data:
        print("Failed to fetch data. Exiting.")
        return
    
    print("Calculating streak...")
    streak, total_contributions = calculate_streak(data)
    print(f"Current streak: {streak} days")
    
    print("Getting language stats...")
    language_stats = get_language_stats(data)
    print(f"Languages found: {list(language_stats.keys())}")
    
    print("Generating sections...")
    streak_section = generate_streak_section(streak, total_contributions)
    languages_section = generate_languages_section(language_stats)
    
    print("Updating README...")
    update_readme(streak_section, languages_section)
    
    print("Done!")


if __name__ == "__main__":
    main()
