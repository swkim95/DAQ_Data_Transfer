#!/bin/bash

# Path to monitor (default: SSD 8TB volume)
MONITOR_PATH="/Volumes/SSD_8TB"

format_bytes() {
    awk -v bytes="$1" 'BEGIN {
        split("B KB MB GB TB PB", unit, " ");
        idx = 1;
        while (bytes >= 1024 && idx < 6) {
            bytes /= 1024;
            idx++;
        }
        printf "%.1f%s", bytes, unit[idx];
    }'
}

# Function to display the storage status
display_status() {
    if [ ! -d "$MONITOR_PATH" ]; then
        echo -e "\033[1;31m[ERROR]\033[0m Target path '$MONITOR_PATH' does not exist or is not mounted."
        echo -e "\033[1;31mPlease mount the SSD_8TB volume and try again.\033[0m"
        sleep 5
        return
    fi

    # Size of each event in bytes (9 DAQs × (65536 + 256) = 9 × 65792)
    event_size_bytes=592128

    # Get the storage information for the target volume in KB to avoid scientific notation
    df -k "$MONITOR_PATH" | awk 'NR==2 {print $2, $3, $4, $5, $6}' | while read size_kb used_kb avail_kb perc mount
    do
        size_display=$(format_bytes $((size_kb * 1024)) )
        used_display=$(format_bytes $((used_kb * 1024)) )
        avail_display=$(format_bytes $((avail_kb * 1024)) )

        # Remove the % symbol from the percentage
        perc_num=${perc%\%}

        # Calculate the remaining percentage
        free_perc=$((100 - perc_num))

        # Convert available space to KB
        # Estimate the number of events that can be stored
        avail_bytes=$((avail_kb * 1024))
        num_events=$((avail_bytes / event_size_bytes))

        # Create the status bar
        bar="["
        for ((i=0; i<perc_num; i+=2)); do
            bar+="#"
        done
        for ((i=perc_num; i<100; i+=2)); do
            bar+=" "
        done
        bar+="]"

        # Check usage and set colors and warnings
        if [ "$perc_num" -gt 80 ]; then
            # Over 80% used: red bar and warning
            echo -e "\033[1;31m$bar $perc used | $size_display total | $used_display used | $avail_display free | $free_perc% free (mounted on $mount)\033[0m"
            echo -e "\033[1;31m[WARNING] STORAGE RUNNING LOW, CONTACT SUNGWON KIM FOR DATA MANAGEMENT\033[0m"
            echo -e "\033[1;31mAbout $num_events events can be stored in the remaining space.\033[0m"
        elif [ "$perc_num" -gt 50 ]; then
            # Over 50% used: yellow bar and warning
            echo -e "\033[1;33m$bar $perc used | $size_display total | $used_display used | $avail_display free | $free_perc% free (mounted on $mount)\033[0m"
            echo -e "\033[1;33m[WARNING] STORAGE USAGE ABOVE 50%\033[0m"
            echo -e "\033[1;33mAbout $num_events events can be stored in the remaining space.\033[0m"
        else
            # Under 50% used: green bar
            echo -e "\033[0;32m$bar $perc used | $size_display total | $used_display used | $avail_display free | $free_perc% free (mounted on $mount)\033[0m"
            echo -e "\033[0;32mAbout $num_events events can be stored in the remaining space.\033[0m"
        fi
    done
}

# Refresh every 5 seconds
while true; do
    # Clear the screen for a clean refresh
    clear
    
    # Display the current status
    display_status

    # Wait for 5 seconds before refreshing
    sleep 5
done
