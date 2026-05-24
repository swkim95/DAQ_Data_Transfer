#!/bin/bash
#
# Launcher for daq_remote_backup.py (HDD_24TB_6 -> KNU remote).
#
# Usage:
#   ./start_remote_backup.sh --remote user@host:/path/ [other flags]
#   ./start_remote_backup.sh --background --remote user@host:/path/
#   ./start_remote_backup.sh --stop
#   ./start_remote_backup.sh --status
#
# Authentication:
#   Export SSHPASS before launching to use password-based auth:
#       export SSHPASS='your-password'
#       ./start_remote_backup.sh --remote user@host:/path/ --background
#
# Other flags are forwarded straight to daq_remote_backup.py:
#       --interval N        polling interval (s)
#       --dry-run           do not transfer anything
#       --once              one cycle then exit
#       --ssh-port N        non-22 SSH port
#       --timeout N         per-run rsync timeout (s)
#       --bwlimit KBPS      cap rsync bandwidth to KBPS KiB/s; 0 = no limit
#                           (default). Setting e.g. 50000 (~50 MB/s) bounds
#                           the TCP send queue and mitigates the macOS
#                           TCP-SACK accounting kernel panic that hit
#                           this host. Run `./start_remote_backup.sh --help`
#                           for the rest.
#       --remote-chmod SPEC apply this --chmod on the remote side; default
#                           'ugo=rwx' uploads everything 0777.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT="daq_remote_backup.py"
LOG_DIR="./Log"
PID_FILE="${LOG_DIR}/remote_backup.pid"
CONSOLE_LOG="${LOG_DIR}/remote_backup_console.log"

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARNING]${NC} $1"; }
err()     { echo -e "${RED}[ERROR]${NC} $1"; }

print_help() {
    cat <<'EOF'
Launcher for daq_remote_backup.py (HDD_24TB_6 -> KNU remote).

Usage:
  ./start_remote_backup.sh --remote user@host:/path/ [options]
  ./start_remote_backup.sh --background --remote user@host:/path/
  ./start_remote_backup.sh --stop
  ./start_remote_backup.sh --status

Authentication:
  Export SSHPASS before launching to use password-based auth:
    export SSHPASS='your-password'
    ./start_remote_backup.sh --remote user@host:/path/ --background

Other flags are forwarded straight to daq_remote_backup.py:
  --remote URL        rsync destination, e.g. user@host:/backup/  (required)
  --interval N        polling interval in seconds (default 60)
  --dry-run           do not actually transfer
  --once              run one pass over eligible runs and exit
  --ssh-port N        non-22 SSH port
  --timeout N         per-run rsync timeout in seconds (default 6h)
  --bwlimit KBPS      cap rsync bandwidth to KBPS KiB/s; 0 = no limit
                      (default 0). Setting e.g. 50000 (~50 MB/s) is the
                      recommended workaround on macOS hosts that have
                      hit the TCP-SACK kernel panic.
  --remote-chmod SPEC rsync --chmod applied remotely. Default 'ugo=rwx'
                      uploads every file/dir as 0777 so collaborators
                      can read/edit. Pass --remote-chmod= (empty) to
                      preserve source permissions.
EOF
}

is_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid; pid=$(cat "$PID_FILE")
        if ps -p "$pid" >/dev/null 2>&1; then
            return 0
        fi
        rm -f "$PID_FILE"
    fi
    return 1
}

stop_it() {
    if is_running; then
        local pid; pid=$(cat "$PID_FILE")
        info "Stopping remote backup (PID: $pid)..."
        kill "$pid" 2>/dev/null
        local n=0
        while ps -p "$pid" >/dev/null 2>&1 && (( n < 10 )); do
            sleep 1; ((n++))
        done
        if ps -p "$pid" >/dev/null 2>&1; then
            warn "Forcing termination..."
            kill -9 "$pid" 2>/dev/null
        fi
        rm -f "$PID_FILE"
        success "Remote backup stopped"
    else
        info "Remote backup is not running"
    fi
}

show_status() {
    if is_running; then
        local pid; pid=$(cat "$PID_FILE")
        success "Remote backup is running (PID: $pid)"
        local latest
        latest=$(ls -t "$LOG_DIR"/remote_backup_log_*.txt 2>/dev/null | head -1)
        if [[ -n "$latest" ]]; then
            info  "Latest log: $latest"
            info  "Recent entries:"
            tail -8 "$latest" | sed 's/^/  /'
        fi
    else
        info "Remote backup is not running"
    fi
}

start_it() {
    local background=false
    local forward=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --background) background=true; shift ;;
            --help|-h) print_help; return 0 ;;
            *) forward+=("$1"); shift ;;
        esac
    done

    if is_running; then
        local pid; pid=$(cat "$PID_FILE")
        warn "Remote backup is already running (PID: $pid)"
        return 1
    fi

    if [[ ! -f "$SCRIPT" ]]; then
        err "Cannot find $SCRIPT in current directory"
        return 1
    fi

    if [[ -z "$SSHPASS" ]]; then
        warn "SSHPASS is not exported. Password auth will not work."
        warn "  export SSHPASS='your-password'  before re-running."
    fi

    if ! command -v sshpass >/dev/null 2>&1; then
        warn "'sshpass' not found on PATH."
        warn "  brew install hudochenkov/sshpass/sshpass"
        warn "Will fall back to plain SSH (public-key auth only)."
    fi

    mkdir -p "$LOG_DIR"
    local cmd=(python3 "$SCRIPT" "${forward[@]}")

    if $background; then
        info "Starting remote backup in background..."
        info "Command: ${cmd[*]}"
        nohup "${cmd[@]}" > "$CONSOLE_LOG" 2>&1 &
        local pid=$!
        echo "$pid" > "$PID_FILE"
        sleep 2
        if ps -p "$pid" >/dev/null 2>&1; then
            success "Remote backup started in background (PID: $pid)"
            info "Console log: $CONSOLE_LOG"
            info "Use './start_remote_backup.sh --stop' to stop"
        else
            err "Failed to start remote backup. See $CONSOLE_LOG"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        info "Starting remote backup in foreground..."
        info "Command: ${cmd[*]}"
        info "Press Ctrl+C to stop"
        echo
        "${cmd[@]}"
    fi
}

main() {
    if [[ $# -eq 0 ]]; then
        err "Missing --remote argument."
        print_help
        exit 2
    fi
    case "$1" in
        --stop)    stop_it ;;
        --status)  show_status ;;
        --help|-h) print_help ;;
        *)         start_it "$@" ;;
    esac
}

main "$@"
