#!/bin/bash

# Function to display the storage status
display_status() {
    # Size of each event in KB
    event_size_kb=836

    # Get the storage information for the current directory
    df -h . | awk 'NR==2 {print $2, $3, $4, $5}' | while read size used avail perc
    do
        # Remove the % symbol from the percentage
        perc_num=${perc%\%}

        # Calculate the remaining percentage
        free_perc=$((100 - perc_num))

        # Convert available space to KB
        avail_kb=$(echo $avail | awk '/G/{print $1 * 1024 * 1024} /M/{print $1 * 1024} /K/{print $1} /T/{print $1 * 1024 * 1024 * 1024}')

        # Estimate the number of events that can be stored
        num_events=$((avail_kb / event_size_kb))

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
            echo -e "\033[1;31m$bar $perc used | $size total | $avail free | $free_perc% free\033[0m"
            echo -e "\033[1;31m[WARNING] STORAGE RUNNING LOW, CONTACT SUNGWON KIM FOR DATA MANAGEMENT\033[0m"
            echo -e "\033[1;31mAbout $num_events events can be stored in the remaining space.\033[0m"
        elif [ "$perc_num" -gt 50 ]; then
            # Over 50% used: yellow bar and warning
            echo -e "\033[1;33m$bar $perc used | $size total | $avail free | $free_perc% free\033[0m"
            echo -e "\033[1;33m[WARNING] STORAGE USAGE ABOVE 50%\033[0m"
            echo -e "\033[1;33mAbout $num_events events can be stored in the remaining space.\033[0m"
        else
            # Under 50% used: green bar
            echo -e "\033[0;32m$bar $perc used | $size total | $avail free | $free_perc% free\033[0m"
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
