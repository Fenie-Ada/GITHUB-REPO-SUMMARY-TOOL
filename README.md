# GitHub Repo Summary Tool
A command-line tool that takes any GitHub username and prints a short report of that user's public repositories.

The report contains:
1. All of the user's public repos (forks -- copies of other people's projects -- are not included)

2. Each repo's:
    number of stars,
    languages used, 
    language most used, 
    and the date of the last push (update).

3. Count of how many repos use each language
4. The top 5 repos, from the one with the most stars
5. The most recently updated repo



## How languages are found
The tool reads each repo's file list and works out the languages from the file types. 
It does not open the files. 
If the file types don't reveal a language, it falls back to the main language GitHub has detected for that repo.



## Requirements
- Python 3
- The `requests` library

```
python -m pip install requests
```



## For accounts with many repos:
- More than 20 repos: the tool tells you how many there are and asks if you want to proceed.
- More than 40 repos: only the first 40 (newest first) are listed. 



## GitHub request limit (optional token)
Without logging in, GitHub allows 60 requests per hour. The tool uses 1 request for the repo list plus 1 for each repo, so large accounts can use up the limit quickly.

To raise the limit to 5,000 per hour, create a free GitHub personal access token (no permissions needed) and save it on your computer as an environment variable named `GITHUB_TOKEN`. The tool uses it automatically if it finds one. On Windows:

```
setx GITHUB_TOKEN "your_token_here"
```

Then open a new terminal. Never put the token in the code or share it.
