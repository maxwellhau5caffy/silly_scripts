#!/usr/bin/env python3
import subprocess
from pathlib import Path
import os

def update_docker_images():
    # Hard-coded base directory
    base_dir = Path(os.path.expanduser("~/docker"))

    # Recursively find all docker-compose.yml files
    compose_files = list(base_dir.rglob("docker-compose.yml"))

    if not compose_files:
        print("No docker-compose.yml files found in ~/docker.")
        return

    for compose_file in compose_files:
        dir_path = compose_file.parent
        print("="*60)
        print(f"Updating Docker images in: {dir_path}")
        print("="*60)
        try:
            # Pull latest images
            subprocess.run(
                ["docker-compose", "pull"],
                cwd=dir_path,
                check=True
            )
            # Optionally recreate containers
            # subprocess.run(["docker-compose", "up", "-d"], cwd=dir_path, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to update images in {dir_path}: {e}")

    print("All Docker images updated!")

if __name__ == "__main__":
    update_docker_images()

