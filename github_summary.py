import sys
import requests
from datetime import datetime

URL = "https://api.github.com"

def format_date(timestamp):
    # turns GitHub's "2024-05-12T10:30:00Z" into "12-05-2024"
    date = datetime.strptime(timestamp[:10], "%Y-%m-%d")
    return date.strftime("%d-%m-%Y")


def get_repos(username):
    # downloads all public repos for a user and returns a list, or None if the user doesn't exist
    repos = []
    page = 1

    while True:
        url = f"{URL}/users/{username}/repos"
        response = requests.get(
            url,
            params={"per_page": 100, "page": page},  # max 100 repos per page
            timeout=10,
        )

        if response.status_code == 404:
            return None
        if response.status_code == 403:
            raise RuntimeError(
                "GitHub rate limit reached (60 requests per hour without login). "
                "Please wait a while and try again."
            )
        response.raise_for_status()

        data = response.json()
        repos.extend(data)

        if len(data) < 100:
            break
        page += 1

    return repos


def get_repo_languages(repo):
    # returns a dict like {"Python": 12000, "HTML": 3000} (bytes of code per language)
    response = requests.get(repo["languages_url"], timeout=10)

    if response.status_code == 403:
        raise RuntimeError(
            "GitHub rate limit reached (60 requests per hour without login). "
            "Please wait a while and try again."
        )
    response.raise_for_status()

    return response.json()


def count_languages(repos):
    # counts how many repos use each programming language
    counts = {}
    for repo in repos:
        language = repo["language"]
        if language:
            counts[language] = counts.get(language, 0) + 1
    return counts


def build_report(username, repos):
    # returns the report as a list of text lines
    # leave forks out (i.e. copies of other people's projects)
    own_repos = [repo for repo in repos if not repo["fork"]]

    # sorts repos from most stars to least stars and takes the first 5
    top_repos = sorted(own_repos, key=lambda r: r["stargazers_count"], reverse=True)[:5]

    # sorts languages from most used to least used
    languages = count_languages(own_repos)
    sorted_languages = sorted(languages.items(), key=lambda item: item[1], reverse=True)

    # gets the most recently updated repo
    latest = max(own_repos, key=lambda r: r["updated_at"]) if own_repos else None

    lines = []
    lines.append(f"\nGitHub Repo Summary for: {username}\n")
    lines.append("=" * 40)

    # each public repo's summary
    lines.append(f"Public repos (forks not included): {len(own_repos)}\n")
    if own_repos:
        for number, repo in enumerate(own_repos, start=1):
            repo_languages = get_repo_languages(repo)
            if repo_languages:
                all_languages = ", ".join(repo_languages)
                most_used = max(repo_languages, key=repo_languages.get)  # language with the most code
            else:
                all_languages = "Not specified"
                most_used = "Not specified"

            updated = format_date(repo["updated_at"])
            lines.append(f"  {number}. {repo['name']}")
            lines.append(f"     Stars: {repo['stargazers_count']} | Last updated: {updated}")
            lines.append(f"     Languages: {all_languages}")
            lines.append(f"     Most used: {most_used}\n")

    else:
        lines.append("  (no repos yet)")

    # how many repos use each language
    lines.append("")
    lines.append("Count of repos that use a language:")
    if sorted_languages:
        for language, count in sorted_languages:
            lines.append(f"  {language}: {count}")
    else:
        lines.append("  (no language data)\n")
    

    # top 5 repos, from the one with the most stars
    lines.append("")
    lines.append("\nTop 5 repos by stars:")
    if top_repos:
        for number, repo in enumerate(top_repos, start=1):
            lines.append(f"  {number}. {repo['name']} - {repo['stargazers_count']} stars")
    else:
        lines.append("  (no repos yet)")


    # 4. last updated repo
    if latest:
        lines.append("")
        lines.append(f"\nLast updated repo: {latest['name']} on {format_date(latest['updated_at'])}")

    return lines


def save_report(lines, username):
    """Save the report to a text file."""
    filename = f"{username}_github_report.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
    print(f"\nReport saved as {filename}")


def yes_no(question):
    # keeps asking until the user types y or n (capital Y or N also works)
    while True:
        answer = input(question).strip().lower()
        if answer == "y":
            return True
        if answer == "n":
            return False
        print("Please type y or n.")


def main():
    # take the username from the command line if given, otherwise asks for it
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Enter a GitHub username: ").strip()

    if not username:
        print("No username entered.")
        return

    try:
        repos = get_repos(username)
    except requests.exceptions.RequestException:
        print("Could not reach GitHub. Check your internet connection and try again.")
        return
    except RuntimeError as error:
        print(error)
        return

    if repos is None:
        print(f"User '{username}' was not found on GitHub.")
        return

    if not repos:
        print(f"'{username}' has no public repositories.")
        return

    try:
        report = build_report(username, repos)
    except requests.exceptions.RequestException:
        print("Could not reach GitHub. Check your internet connection and try again.")
        return
    except RuntimeError as error:
        print(error)
        return
    
    print()
    print("\n".join(report))

    print()
    if yes_no("\nSave this report to a file? (y/n): "):
        save_report(report, username)


if __name__ == "__main__":
    main()
