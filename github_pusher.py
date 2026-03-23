# github_pusher.py — Commit notes and push to GitHub via gh CLI

import os
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def run(cmd: list[str], cwd: str = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command, logging output."""
    logger.debug(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def gh_available() -> bool:
    """Check if the gh CLI is installed."""
    try:
        run(["gh", "--version"])
        return True
    except (FileNotFoundError, RuntimeError):
        return False


def git_available() -> bool:
    """Check if git is installed."""
    try:
        run(["git", "--version"])
        return True
    except (FileNotFoundError, RuntimeError):
        return False


def get_remote_url(cwd: str) -> str | None:
    """Return the existing remote origin URL, or None."""
    result = run(["git", "remote", "get-url", "origin"], cwd=cwd, check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def push_to_github(local_dir: str, repo_name: str, notes_file: str) -> str:
    """
    Commit notes and push to GitHub. Creates the repo if it doesn't exist.

    Args:
        local_dir: Path to the local project directory
        repo_name: GitHub repo name (e.g. "youtube-notes")
        notes_file: Path to the notes.md file (relative or absolute)

    Returns:
        GitHub repository URL
    """
    if not git_available():
        raise RuntimeError("git is not installed or not in PATH")

    if not gh_available():
        raise RuntimeError(
            "gh CLI is not installed. Install from https://cli.github.com/ "
            "and run `gh auth login`"
        )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"🤖 Auto-generated notes: {timestamp}"

    # Ensure we have a git repo
    git_dir = os.path.join(local_dir, ".git")
    if not os.path.exists(git_dir):
        logger.info("Initializing git repository...")
        run(["git", "init"], cwd=local_dir)
        run(["git", "branch", "-M", "main"], cwd=local_dir)

    # Configure git identity if not set
    name_check = run(["git", "config", "user.name"], cwd=local_dir, check=False)
    if not name_check.stdout.strip():
        run(["git", "config", "user.email", "notes-bot@example.com"], cwd=local_dir)
        run(["git", "config", "user.name", "YouTube Notes Bot"], cwd=local_dir)

    # Stage all files
    run(["git", "add", "."], cwd=local_dir)

    # Check if there's anything to commit
    status = run(["git", "status", "--porcelain"], cwd=local_dir)
    if not status.stdout.strip():
        logger.info("Nothing new to commit.")
        existing_remote = get_remote_url(local_dir)
        return existing_remote or f"https://github.com/{repo_name}"

    run(["git", "commit", "-m", commit_msg], cwd=local_dir)

    existing_remote = get_remote_url(local_dir)

    if existing_remote:
        logger.info(f"Pushing to existing remote: {existing_remote}")
        run(["git", "push", "origin", "main"], cwd=local_dir)
        return existing_remote
    else:
        logger.info(f"Creating new GitHub repo: {repo_name}")
        result = run(
            ["gh", "repo", "create", repo_name,
             "--public", "--source=.", "--remote=origin", "--push"],
            cwd=local_dir
        )
        # Extract URL from gh output
        for line in result.stdout.splitlines():
            if "github.com" in line:
                return line.strip()

        # Fallback: get URL from git remote
        remote_url = get_remote_url(local_dir)
        return remote_url or f"https://github.com/{repo_name}"
