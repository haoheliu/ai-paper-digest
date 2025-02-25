#!/usr/bin/env python3
import os
import time
import subprocess

# Path to the Git repository
REPO_PATH = "/home/lxb/Disk_SSD/projects/ai-paper-digest"

# Git branch to push to
BRANCH = "master"

while True:
    try:
        # Change directory to the repository
        os.chdir(REPO_PATH)

        # Get the current timestamp
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        # Run Git commands
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"refresh database {timestamp}"], check=True)
        subprocess.run(["git", "push", "origin", BRANCH], check=True)

        print(f"[{timestamp}] Successfully pushed to {BRANCH}")

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

    # Wait for an hour before running again
    time.sleep(3600)
