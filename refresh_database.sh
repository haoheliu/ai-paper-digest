
#!/bin/bash

# Path to the script you want to run
SCRIPT="/home/lxb/Disk_SSD/projects/ai-paper-digest/refresh_database.sh"
LOG_FILE="/home/lxb/Disk_SSD/projects/ai-paper-digest/cron.log"

# Run the script every hour indefinitely
while true; do
    echo "Running script at $(date)" >> "$LOG_FILE"
    bash "$SCRIPT" >> "$LOG_FILE" 2>&1
    sleep 3600  # Wait for 1 hour (3600 seconds)
done