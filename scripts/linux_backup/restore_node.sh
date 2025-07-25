#!/bin/bash

# interactive_restore.sh
# Usage: sudo ./interactive_restore.sh
# Lives in /disk01/backups

set -e

BACKUP_ROOT="/disk01/backups"

if [[ $EUID -ne 0 ]]; then
  echo "Please run this script as root (using sudo)."
  exit 1
fi

# Check backup root directory exists
if [[ ! -d "$BACKUP_ROOT" ]]; then
  echo "Backup root directory $BACKUP_ROOT does not exist."
  exit 1
fi

# List hosts (directories inside /disk01/backups)
hosts=()
while IFS= read -r -d '' dir; do
  hosts+=("$(basename "$dir")")
done < <(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -print0)

if [[ ${#hosts[@]} -eq 0 ]]; then
  echo "No hosts found in $BACKUP_ROOT"
  exit 1
fi

echo "Available hosts:"
for i in "${!hosts[@]}"; do
  printf "  %d) %s\n" $((i+1)) "${hosts[i]}"
done

read -rp "Select a host by number: " host_choice
if ! [[ "$host_choice" =~ ^[0-9]+$ ]] || ((host_choice < 1 || host_choice > ${#hosts[@]})); then
  echo "Invalid host selection."
  exit 1
fi

selected_host="${hosts[host_choice-1]}"
host_dir="$BACKUP_ROOT/$selected_host"

# List backups for the selected host
backups=()
while IFS= read -r -d '' dir; do
  backups+=("$(basename "$dir")")
done < <(find "$host_dir" -mindepth 1 -maxdepth 1 -type d -print0)

if [[ ${#backups[@]} -eq 0 ]]; then
  echo "No backups found for host $selected_host"
  exit 1
fi

echo "Available backups for host $selected_host:"
for i in "${!backups[@]}"; do
  printf "  %d) %s\n" $((i+1)) "${backups[i]}"
done

read -rp "Select a backup by number: " backup_choice
if ! [[ "$backup_choice" =~ ^[0-9]+$ ]] || ((backup_choice < 1 || backup_choice > ${#backups[@]})); then
  echo "Invalid backup selection."
  exit 1
fi

selected_backup="${backups[backup_choice-1]}"
backup_dir="$host_dir/$selected_backup"

# Confirm before restore
echo
echo "You are about to restore backup:"
echo "  Host: $selected_host"
echo "  Backup: $selected_backup"
echo "  Directory: $backup_dir"
echo "This will overwrite files on your root filesystem."

read -rp "Are you sure you want to proceed with a dry-run? (yes/no): " confirm
if [[ "$confirm" != "yes" ]]; then
  echo "Restore aborted."
  exit 0
fi

# Dry run first
echo
echo "Running dry-run to preview restore..."
rsync -aAXvn --no-xattrs "$backup_dir"/ /

echo
read -rp "Dry-run complete. Proceed with actual restore? (yes/no): " proceed
if [[ "$proceed" != "yes" ]]; then
  echo "Restore aborted."
  exit 0
fi

echo
echo "Starting restore..."
rsync -aAXv --no-xattrs "$backup_dir"/ /

echo
echo "Restore completed."

