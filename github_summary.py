import os
import sys
import requests
from datetime import datetime

URL = "https://api.github.com"

TOKEN = os.environ.get("GITHUB_TOKEN")  # optional, read from your computer, not saved in the code
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

# file types counted as programming languages
LANGUAGE_FILES = {
    ".py": "Python", ".html": "HTML", ".htm": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".sass": "Sass", ".less": "Less",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".vue": "Vue",
    ".java": "Java", ".c": "C", ".cpp": "C++", ".cc": "C++", ".cs": "C#",
    ".php": "PHP", ".sql": "SQL", ".go": "Go", ".rs": "Rust",
    ".rb": "Ruby", ".kt": "Kotlin", ".swift": "Swift", ".dart": "Dart",
    ".sh": "Shell", ".bash": "Shell", ".bat": "Batchfile", ".ps1": "PowerShell",
    ".applescript": "AppleScript", ".scpt": "AppleScript",
    ".r": "R", ".lua": "Lua", ".pl": "Perl", ".scala": "Scala",
    ".ipynb": "Jupyter Notebook",
}

# file types that are not programming languages (shown when a repo has no code)
OTHER_FILES = {
    ".md": "Markdown", ".txt": "Text files", ".json": "JSON", ".csv": "CSV",
    ".png": "Images", ".jpg": "Images", ".jpeg": "Images", ".pdf": "PDF",
    ".docx": "Word documents", ".xlsx": "Excel files", ".pptx": "PowerPoint files",
}

# folders to ignore (installed packages / not your own code)
SKIP_FOLDERS = ("node_modules/", "venv/", "__pycache__/")


def format_date(timestamp):
    date = datetime.strptime(timestamp[:10], "%Y-%m-%d")
    return date.strftime("%d-%m-%Y")


def last_pushed(repo):
    # the date code was last pushed; "updated_at" also changes when someone stars the repo or edits settings
    return repo["pushed_at"] or repo["created_at"]


def get_repos(username):
    repos = []
    page = 1

    while True:
        url = f"{URL}/users/{username}/repos"
        response = requests.get(
            url,
            params={"per_page": 100, "page": page},  # max 100 repos per page
            headers=HEADERS,
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


def get_repo_files(repo):
    # returns the list of files in the repo
    url = f"{URL}/repos/{repo['full_name']}/git/trees/{repo['default_branch']}"
    response = requests.get(url, params={"recursive": 1}, headers=HEADERS, timeout=10)

    if response.status_code in (404, 409):
        return None  # nothing has been uploaded to this repo yet
    if response.status_code == 403:
        raise RuntimeError(
            "GitHub rate limit reached (60 requests per hour without login). "
            "Please wait a while and try again."
        )
    response.raise_for_status()

    tree = response.json()["tree"]
    return [item for item in tree if item["type"] == "blob"]  # "blob" means a file


def find_languages(files):
    # works out the languages from the file names
    languages = {}  # language -> total size of its files, in the order the files appear
    others = []     # non-code files found, e.g. README, Markdown, Text files

    for file in files:
        path = file["path"]
        if any(folder in path for folder in SKIP_FOLDERS):
            continue  # ignore installed packages

        name = path.split("/")[-1].lower()
        extension = os.path.splitext(name)[1]

        if extension in LANGUAGE_FILES:
            language = LANGUAGE_FILES[extension]
            languages[language] = languages.get(language, 0) + file["size"]
        elif name.startswith("readme"):
            if "README" not in others:
                others.append("README")
        elif extension in OTHER_FILES:
            kind = OTHER_FILES[extension]
            if kind not in others:
                others.append(kind)
        elif extension in OTHER_FILES:
            kind = OTHER_FILES[extension]
            if kind not in others:
                others.append(kind)
        else:
            # a file type that is in neither list: show what it actually is
            label = f"{extension} files" if extension else path.split("/")[-1]
            if label not in others:
                others.append(label)

    return languages, others


def count_languages(repos):
    # counts how many repos use each programming language
    counts = {}
    for repo in repos:
        language = repo["language"]
        if language:
            counts[language] = counts.get(language, 0) + 1
    return counts


def build_report(username, repos, total=None):
    # returns the report as a list of text lines
    own_repos = [repo for repo in repos if not repo["fork"]]

    # sorts repos from most stars to least stars and takes the first 5
    top_repos = sorted(own_repos, key=lambda r: r["stargazers_count"], reverse=True)[:5]

    # sorts languages from most used to least used
    languages = count_languages(own_repos)
    sorted_languages = sorted(languages.items(), key=lambda item: item[1], reverse=True)

    # gets the most recently updated repo
    latest = max(own_repos, key=last_pushed) if own_repos else None

    lines = []
    lines.append(f"\nGitHub Repo Summary for: {username}\n")
    lines.append("=" * 40)

    # each repo's summary
    if total and total > len(own_repos):
        lines.append(f"Public repos (forks not included): {total} (showing the first {len(own_repos)})\n")
    else:
        lines.append(f"Public repos (forks not included): {len(own_repos)}\n")
    if own_repos:
        for number, repo in enumerate(own_repos, start=1):
            updated = format_date(last_pushed(repo))
            lines.append(f"  {number}. {repo['name']}")
            lines.append(f"     Stars: {repo['stargazers_count']} | Last updated: {updated}")

            files = get_repo_files(repo)
            if not files:
                lines.append("     Language(s): This repo is empty")
            else:
                languages, others = find_languages(files)

                # if the file names didn't reveal a language, use the one GitHub detected
                if not languages and repo["language"]:
                    languages = {repo["language"]: 0}

                if languages:
                    lines.append(f"     Language(s): {', '.join(languages)}")
                    if len(languages) > 1:
                        most_used = max(languages, key=languages.get)  # language with the most code
                        lines.append(f"     Most used: {most_used}")
                else:
                    lines.append("     Language(s): None")
                    if others:
                        lines.append(f"     Contains: {', '.join(others)}")
            lines.append("")

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
    

    # outputs top 5 repos, from the one with the most stars
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
        lines.append(f"\nLast updated repo: {latest['name']} on {format_date(last_pushed(latest))}")

    return lines


def save_report(lines, username):
    """Save the report to a text file."""
    filename = f"{username}_github_report.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
    print(f"\nReport saved as {filename}")


def yes_no(question):
    # keeps asking until the user types y or n
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

     # accounts with many repos: ask first (forks are not included in the report)
    own_repos = [repo for repo in repos if not repo["fork"]]
    total = len(own_repos)

    if total > 20:
        message = f"\nThis account has {total} repos (forks not included)."
        if total > 40:
            message += " Only the first 40 will be listed."
        print(message)
        if not yes_no("Shall I proceed? (y/n): "):
            print("No report was made.")
            return

    if total > 40:
        own_repos.sort(key=last_pushed, reverse=True)  # newest first, like the repositories page
        repos = own_repos[:40]

    
    try:
        report = build_report(username, repos, total)
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
