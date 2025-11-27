#!/bin/bash

# External SSD NVMe temperature monitor
# Usage: ./monitor_SSD_temp.sh [device] [interval_seconds]

DEVICE="${1:-/dev/disk7s1}"
INTERVAL="${2:-5}"
SMARTCTL_CMD=$(command -v smartctl)

COLOR_GREEN="\033[0;32m"
COLOR_ORANGE="\033[38;5;708m"
COLOR_RED="\033[1;31m"
COLOR_RESET="\033[0m"

if [ -z "$SMARTCTL_CMD" ]; then
    echo -e "${COLOR_RED}[ERROR] smartctl not found. Please install smartmontools.${COLOR_RESET}"
    exit 1
fi

if [ ! -e "$DEVICE" ]; then
    echo -e "${COLOR_RED}[ERROR] Device $DEVICE not found.${COLOR_RESET}"
    exit 1
fi

monitor_temperature() {
    while true; do
        smart_output=$("$SMARTCTL_CMD" -a "$DEVICE")

        temp_core=$(echo "$smart_output" | awk '/^Temperature:/ {print $(NF-1); exit}')
        temp1=$(echo "$smart_output" | awk '/Temperature Sensor 1:/ {print $(NF-1); exit}')
        temp2=$(echo "$smart_output" | awk '/Temperature Sensor 2:/ {print $(NF-1); exit}')
        temp3=$(echo "$smart_output" | awk '/Temperature Sensor 3:/ {print $(NF-1); exit}')

        warning_threshold=$(echo "$smart_output" | awk '/Warning  Comp. Temp. Threshold:/ {print $(NF-1); exit}')
        critical_threshold=$(echo "$smart_output" | awk '/Critical Comp. Temp. Threshold:/ {print $(NF-1); exit}')

        warning_threshold=${warning_threshold:-90}
        critical_threshold=${critical_threshold:-94}

        temps=("$temp_core" "$temp1" "$temp2" "$temp3")
        labels=("Controller" "Sensor 1" "Sensor 2" "Sensor 3")
        max_temp=0
        display_lines=()

        for idx in "${!temps[@]}"; do
            val=${temps[$idx]}
            label=${labels[$idx]}
            if [[ -z "$val" ]]; then
                display_lines+=("$label: N/A")
                continue
            fi
            if (( val > max_temp )); then max_temp=$val; fi
            display_lines+=("$label: ${val}°C")
        done

        if (( max_temp < 70 )); then
            color=$COLOR_GREEN
            status="TEMPERATURE NORMAL (<70°C)"
        elif (( max_temp < 80 )); then
            color=$COLOR_ORANGE
            status="TEMPERATURE HIGH (70-80°C)"
        else
            color=$COLOR_RED
            status="TEMPERATURE CRITICAL (>=80°C) - STOP OPERATIONS!"
        fi

        clear
        echo -e "${color}==============================================${COLOR_RESET}"
        echo -e "${color}SSD NVMe Temperature Monitor (${DEVICE})${COLOR_RESET}"
        echo -e "${color}Status : $status${COLOR_RESET}"
        echo -e "${color}Warning Threshold : ${warning_threshold}°C | Critical Threshold : ${critical_threshold}°C${COLOR_RESET}"
        echo -e "${color}----------------------------------------------${COLOR_RESET}"
        for line in "${display_lines[@]}"; do
            echo -e "${color}${line}${COLOR_RESET}"
        done
        echo -e "${color}==============================================${COLOR_RESET}"

        if (( max_temp >= 80 )); then
            echo -e "${COLOR_RED}[CRITICAL WARNING] Temperature exceeds 80°C!"
            echo -e "Immediately stop DAQ operations/transfers and cool down the SSD.${COLOR_RESET}"
        elif (( max_temp >= 70 )); then
            echo -e "${COLOR_ORANGE}[WARNING] Temperature between 70-80°C. Monitor closely.${COLOR_RESET}"
        fi

        sleep "$INTERVAL"
    done
}

monitor_temperature