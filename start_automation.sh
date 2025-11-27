#!/bin/bash

# DAQ Data Processing Automation Launcher
#
# This script provides a convenient way to start the DAQ automation system
# with proper logging and background execution capabilities.
#
# Usage:
#     ./start_automation.sh [OPTIONS]
#     
# Options:
#     --interval SECONDS  : Monitoring interval (default: 60)
#     --dry-run          : Show what would be done without executing
#     --background       : Run in background with nohup
#     --stop             : Stop running automation
#     
# Examples:
#     ./start_automation.sh                    # Start with default settings
#     ./start_automation.sh --interval 30     # Check every 30 seconds
#     ./start_automation.sh --dry-run         # Test mode
#     ./start_automation.sh --background      # Run in background
#     ./start_automation.sh --stop            # Stop automation

# Color definitions for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script paths
AUTOMATION_SCRIPT="daq_automation.py"
PID_FILE="./Log/automation.pid"
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

# Check if automation is running
is_automation_running() {
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

# Stop automation
stop_automation() {
    if is_automation_running; then
        local pid=$(cat "$PID_FILE")
        print_info "Stopping automation (PID: $pid)..."
        
        # Send SIGTERM first
        kill "$pid" 2>/dev/null
        
        # Wait for graceful shutdown
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [[ $count -lt 10 ]]; do
            sleep 1
            ((count++))
        done
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            print_warning "Forcing termination..."
            kill -9 "$pid" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        print_success "Automation stopped"
    else
        print_info "Automation is not running"
    fi
}

# Start automation
start_automation() {
    local interval=60
    local dry_run=""
    local background=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interval)
                interval="$2"
                shift 2
                ;;
            --dry-run)
                dry_run="--dry-run"
                shift
                ;;
            --background)
                background=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check if already running
    if is_automation_running; then
        local pid=$(cat "$PID_FILE")
        print_warning "Automation is already running (PID: $pid)"
        return 1
    fi
    
    # Validate interval
    if ! [[ "$interval" =~ ^[0-9]+$ ]] || [[ "$interval" -lt 1 ]]; then
        print_error "Interval must be a number >= 1"
        return 1
    fi
    
    # Check if automation script exists
    if [[ ! -f "$AUTOMATION_SCRIPT" ]]; then
        print_error "Automation script not found: $AUTOMATION_SCRIPT"
        return 1
    fi
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    # Build command
    local cmd="python3 $AUTOMATION_SCRIPT --interval $interval $dry_run"
    
    if [[ "$background" == true ]]; then
        print_info "Starting automation in background..."
        print_info "Command: $cmd"
        
        # Start in background with nohup
        nohup $cmd > "$LOG_DIR/automation_console.log" 2>&1 &
        local pid=$!
        echo "$pid" > "$PID_FILE"
        
        # Wait a moment to check if it started successfully
        sleep 2
        if ps -p "$pid" > /dev/null 2>&1; then
            print_success "Automation started in background (PID: $pid)"
            print_info "Console output: $LOG_DIR/automation_console.log"
            print_info "Main log files: $LOG_DIR/automation_log_*.txt"
            print_info "Use './start_automation.sh --stop' to stop"
        else
            print_error "Failed to start automation"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        print_info "Starting automation in foreground..."
        print_info "Command: $cmd"
        print_info "Press Ctrl+C to stop"
        echo
        
        # Start in foreground
        $cmd
    fi
}

# Show status
show_status() {
    if is_automation_running; then
        local pid=$(cat "$PID_FILE")
        print_success "Automation is running (PID: $pid)"
        
        # Show recent log entries
        local latest_log=$(ls -t "$LOG_DIR"/automation_log_*.txt 2>/dev/null | head -1)
        if [[ -n "$latest_log" ]]; then
            print_info "Latest log: $latest_log"
            print_info "Recent entries:"
            tail -5 "$latest_log" | sed 's/^/  /'
        fi
    else
        print_info "Automation is not running"
    fi
}

# Show help
show_help() {
    echo "DAQ Data Processing Automation Launcher"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --interval SECONDS  Monitoring interval (default: 60)"
    echo "  --dry-run          Show what would be done without executing"
    echo "  --background       Run in background with nohup"
    echo "  --stop             Stop running automation"
    echo "  --status           Show automation status"
    echo "  --help             Show this help message"
    echo
    echo "Examples:"
    echo "  $0                    # Start with default settings"
    echo "  $0 --interval 30     # Check every 30 seconds"
    echo "  $0 --dry-run         # Test mode"
    echo "  $0 --background      # Run in background"
    echo "  $0 --stop            # Stop automation"
    echo "  $0 --status          # Show status"
}

# Main script logic
main() {
    # Check if no arguments provided
    if [[ $# -eq 0 ]]; then
        start_automation
        return $?
    fi
    
    # Parse main commands
    case "$1" in
        --stop)
            stop_automation
            ;;
        --status)
            show_status
            ;;
        --help|-h)
            show_help
            ;;
        *)
            start_automation "$@"
            ;;
    esac
}

# Run main function with all arguments
main "$@"