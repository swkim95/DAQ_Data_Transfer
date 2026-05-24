#!/bin/bash

# DAQ Automated Data Deletion Launcher - EXTREMELY DANGEROUS
#
# This script provides a convenient way to start the automated deletion system
# with comprehensive safety warnings and confirmation steps.
#
# Usage:
#     ./start_auto_deletion.sh [OPTIONS]
#
# Options:
#     --real-deletion              : Enable real deletion mode (EXTREMELY DANGEROUS)
#     --interval SECONDS           : Monitoring interval (default: 300 seconds)
#     --background                 : Run in background with nohup
#     --force-threshold PERCENT    : Override the 60% trigger threshold
#                                    (must be >30 and <=90)
#     --require-secondary-backup   : Also require HDD_16TB_4 to be copied/validated
#                                    before a run is eligible for deletion
#     --stop                       : Stop running auto-deletion
#     --status                     : Show auto-deletion status
#
# Examples:
#     ./start_auto_deletion.sh                                    # Safe dry-run monitoring (60%)
#     ./start_auto_deletion.sh --force-threshold 85               # Dry-run, trigger at 85%
#     ./start_auto_deletion.sh --real-deletion --force-threshold 85   # Real deletion, trigger at 85%
#     ./start_auto_deletion.sh --background                       # Run in background
#     ./start_auto_deletion.sh --stop                             # Stop auto-deletion

# Color definitions for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Script paths
DELETION_SCRIPT="daq_auto_deletion.py"
PID_FILE="./Log/auto_deletion.pid"
LOG_DIR="./Log"

# Functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_critical() {
    echo -e "${RED}${BOLD}[CRITICAL]${NC} $1"
}

# Display extreme safety warnings
show_safety_warnings() {
    echo
    echo -e "${RED}${BOLD}████████████████████████████████████████████████████████████████${NC}"
    echo -e "${RED}${BOLD}█                                                              █${NC}"
    echo -e "${RED}${BOLD}█              EXTREMELY DANGEROUS OPERATION                  █${NC}"
    echo -e "${RED}${BOLD}█                                                              █${NC}"
    echo -e "${RED}${BOLD}█  This script PERMANENTLY DELETES experimental data          █${NC}"
    echo -e "${RED}${BOLD}█  when storage exceeds 60% usage.                            █${NC}"
    echo -e "${RED}${BOLD}█                                                              █${NC}"
    echo -e "${RED}${BOLD}█  ONLY USE if you understand the risks and have              █${NC}"
    echo -e "${RED}${BOLD}█  verified all backups are valid and accessible.            █${NC}"
    echo -e "${RED}${BOLD}█                                                              █${NC}"
    echo -e "${RED}${BOLD}████████████████████████████████████████████████████████████████${NC}"
    echo
}

# Check if auto-deletion is running
is_auto_deletion_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # Running
        else
            rm -f "$PID_FILE"  # Clean up stale PID file
            return 1  # Not running
        fi
    fi
    return 1  # Not running
}

# Stop auto-deletion
stop_auto_deletion() {
    if is_auto_deletion_running; then
        local pid=$(cat "$PID_FILE")
        print_warning "Stopping auto-deletion (PID: $pid)..."
        
        # Send SIGTERM first
        kill "$pid" 2>/dev/null
        
        # Wait for graceful shutdown
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [[ $count -lt 15 ]]; do
            sleep 1
            ((count++))
        done
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            print_warning "Forcing termination..."
            kill -9 "$pid" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        print_success "Auto-deletion stopped"
    else
        print_info "Auto-deletion is not running"
    fi
}

# Start auto-deletion
start_auto_deletion() {
    local real_deletion=false
    local interval=300
    local background=false
    local force_threshold=""
    local require_secondary=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --real-deletion)
                real_deletion=true
                shift
                ;;
            --interval)
                interval="$2"
                shift 2
                ;;
            --background)
                background=true
                shift
                ;;
            --force-threshold)
                force_threshold="$2"
                shift 2
                ;;
            --require-secondary-backup)
                require_secondary=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validate --force-threshold (numeric, in (stop_threshold, 90])
    if [[ -n "$force_threshold" ]]; then
        if ! [[ "$force_threshold" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            print_error "--force-threshold must be a number (got: $force_threshold)"
            return 1
        fi
        # Use awk for float comparison since bash arithmetic is integer-only.
        if awk -v v="$force_threshold" 'BEGIN { exit !(v > 90.0) }'; then
            print_error "--force-threshold cannot exceed 90% for safety (got: $force_threshold)"
            return 1
        fi
        if awk -v v="$force_threshold" 'BEGIN { exit !(v <= 30.0) }'; then
            print_error "--force-threshold must be greater than the 30% stop threshold (got: $force_threshold)"
            return 1
        fi
    fi
    
    # Check if already running
    if is_auto_deletion_running; then
        local pid=$(cat "$PID_FILE")
        print_warning "Auto-deletion is already running (PID: $pid)"
        return 1
    fi
    
    # Validate interval
    if ! [[ "$interval" =~ ^[0-9]+$ ]] || [[ "$interval" -lt 5 ]]; then
        print_error "Interval must be a number >= 5 seconds"
        return 1
    fi
    
    # Check if deletion script exists
    if [[ ! -f "$DELETION_SCRIPT" ]]; then
        print_error "Deletion script not found: $DELETION_SCRIPT"
        return 1
    fi
    
    # Show safety warnings
    show_safety_warnings
    
    # Safety confirmation for real deletion
    if [[ "$real_deletion" == true ]]; then
        print_critical "REAL DELETION MODE REQUESTED"
        print_critical "This will PERMANENTLY DELETE experimental data"
        echo
        print_warning "Safety checklist:"
        echo "  1. Have you verified all backups are complete and accessible?"
        echo "  2. Have you tested the deletion process in dry-run mode?"
        echo "  3. Do you have a data recovery plan if something goes wrong?"
        echo "  4. Are you authorized to delete experimental data?"
        echo
        echo -e "${RED}${BOLD}Type 'ENABLE_REAL_DELETION' to confirm real deletion mode:${NC}"
        read confirmation
        
        if [[ "$confirmation" != "ENABLE_REAL_DELETION" ]]; then
            print_info "Real deletion not confirmed. Starting in dry-run mode instead."
            real_deletion=false
        else
            print_critical "REAL DELETION MODE CONFIRMED"
        fi
    fi
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    # Build command
    local cmd="python3 $DELETION_SCRIPT --interval $interval"
    if [[ "$real_deletion" == true ]]; then
        cmd="$cmd --real-deletion"
    fi
    if [[ -n "$force_threshold" ]]; then
        cmd="$cmd --force-threshold $force_threshold"
    fi
    if [[ "$require_secondary" == true ]]; then
        cmd="$cmd --require-secondary-backup"
    fi
    
    if [[ "$background" == true ]]; then
        print_info "Starting auto-deletion in background..."
        if [[ "$real_deletion" == true ]]; then
            print_critical "BACKGROUND MODE WITH REAL DELETION ENABLED"
        else
            print_info "Background mode with dry-run (safe monitoring)"
        fi
        print_info "Command: $cmd"
        
        # Start in background with nohup
        nohup $cmd > "$LOG_DIR/auto_deletion_console.log" 2>&1 &
        local pid=$!
        echo "$pid" > "$PID_FILE"
        
        # Wait a moment to check if it started successfully
        sleep 3
        if ps -p "$pid" > /dev/null 2>&1; then
            print_success "Auto-deletion started in background (PID: $pid)"
            print_info "Console output: $LOG_DIR/auto_deletion_console.log"
            print_info "Main log files: $LOG_DIR/auto_deletion_log_*.txt"
            print_info "Use './start_auto_deletion.sh --stop' to stop"
            
            if [[ "$real_deletion" == true ]]; then
                print_critical "MONITOR LOGS CAREFULLY - REAL DELETION IS ACTIVE"
            fi
        else
            print_error "Failed to start auto-deletion"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        print_info "Starting auto-deletion in foreground..."
        if [[ "$real_deletion" == true ]]; then
            print_critical "FOREGROUND MODE WITH REAL DELETION ENABLED"
        else
            print_info "Foreground mode with dry-run (safe monitoring)"
        fi
        print_info "Command: $cmd"
        print_info "Press Ctrl+C to stop"
        echo
        
        # Start in foreground
        $cmd
    fi
}

# Show status
show_status() {
    if is_auto_deletion_running; then
        local pid=$(cat "$PID_FILE")
        print_success "Auto-deletion is running (PID: $pid)"
        
        # Show recent log entries
        local latest_log=$(ls -t "$LOG_DIR"/auto_deletion_log_*.txt 2>/dev/null | head -1)
        if [[ -n "$latest_log" ]]; then
            print_info "Latest log: $latest_log"
            print_info "Recent entries:"
            tail -10 "$latest_log" | sed 's/^/  /'
        fi
        
        # Check if it's in real deletion mode
        if grep -q "Real deletion mode: True" "$latest_log" 2>/dev/null; then
            print_critical "RUNNING IN REAL DELETION MODE"
        else
            print_info "Running in safe dry-run mode"
        fi
    else
        print_info "Auto-deletion is not running"
    fi
}

# Show help
show_help() {
    echo "DAQ Automated Data Deletion Launcher - EXTREMELY DANGEROUS"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --real-deletion              Enable real deletion mode (EXTREMELY DANGEROUS)"
    echo "  --interval SECONDS           Monitoring interval (default: 300 seconds)"
    echo "  --background                 Run in background with nohup"
    echo "  --force-threshold PERCENT    Override the 60% trigger threshold"
    echo "                               (must be >30 and <=90)"
    echo "  --require-secondary-backup   Also require HDD_16TB_4 to be copied/validated"
    echo "                               before a run is eligible for deletion"
    echo "  --stop                       Stop running auto-deletion"
    echo "  --status                     Show auto-deletion status"
    echo "  --help                       Show this help message"
    echo
    echo "Examples:"
    echo "  $0                                                 # Safe dry-run, 60% trigger"
    echo "  $0 --force-threshold 85                            # Dry-run, 85% trigger"
    echo "  $0 --real-deletion --force-threshold 85            # Real deletion, 85% trigger"
    echo "  $0 --background --force-threshold 80               # Background dry-run at 80%"
    echo "  $0 --interval 120                                  # Check every 2 minutes"
    echo "  $0 --stop                                          # Stop auto-deletion"
    echo "  $0 --status                                        # Show status"
    echo
    show_safety_warnings
}

# Main script logic
main() {
    # Check if no arguments provided
    if [[ $# -eq 0 ]]; then
        start_auto_deletion
        return $?
    fi
    
    # Parse main commands
    case "$1" in
        --stop)
            stop_auto_deletion
            ;;
        --status)
            show_status
            ;;
        --help|-h)
            show_help
            ;;
        *)
            start_auto_deletion "$@"
            ;;
    esac
}

# Run main function with all arguments
main "$@"