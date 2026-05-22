"""
DAQ Automated Data Deletion Script - EXTREMELY DANGEROUS

This script monitors internal SSD storage capacity and automatically deletes
validated data when storage exceeds 60% usage. This is the MOST DANGEROUS
script in the DAQ system as it PERMANENTLY DELETES experimental data.

⚠️  CRITICAL SAFETY REQUIREMENTS:
- DRY RUN IS DEFAULT - Real deletion requires explicit --real-deletion flag
- Double verification of copy/validation status before any deletion
- Comprehensive logging of all operations and decisions
- Storage monitoring with visual feedback
- Automatic stopping when storage drops below 30%
- Sequential deletion starting from lowest run numbers

Deletion Trigger: Storage usage > 60%
Deletion Stop: Storage usage < 30%
Deletion Order: Lowest run number first (Run_1, Run_2, Run_3...)

Usage:
    python3 daq_auto_deletion.py [--real-deletion] [--interval SECONDS] [--force-threshold PERCENT]
    
Arguments:
    --real-deletion     : REQUIRED for actual deletion (default: dry-run mode)
    --interval SECONDS  : Monitoring interval in seconds (default: 300 = 5 minutes)
    --force-threshold PERCENT : Override 60% trigger threshold (DANGEROUS)
    
Examples:
    python3 daq_auto_deletion.py                           # Safe dry-run monitoring
    python3 daq_auto_deletion.py --real-deletion          # DANGEROUS: Real deletion mode
    python3 daq_auto_deletion.py --interval 120           # Check every 2 minutes (dry-run)
    
CRITICAL SAFETY NOTES:
- This script PERMANENTLY DELETES experimental data
- Always test with dry-run mode first
- Verify backup status manually before using --real-deletion
- Monitor logs carefully during operation
- Have backup recovery plan ready

Log Location: ./Log/auto_deletion_log_YYYYMMDD_HHMMSS.txt
"""

import os
import sys
import time
import argparse
import datetime
import shutil
import subprocess
from typing import List, Tuple, Optional
from daq_utils import (
    Colors, print_info, print_warning, print_error, print_success,
    validate_path_exists, check_flag_file_exists, get_data_files
)

class StorageInfo:
    """Storage information container."""
    def __init__(self, total_bytes: int, used_bytes: int, free_bytes: int, usage_percent: float):
        self.total_bytes = total_bytes
        self.used_bytes = used_bytes
        self.free_bytes = free_bytes
        self.usage_percent = usage_percent
        
    def __str__(self):
        return f"Storage: {self.used_bytes//1024//1024//1024:.1f}GB used / {self.total_bytes//1024//1024//1024:.1f}GB total ({self.usage_percent:.1f}%)"

class DAQAutoDeletion:
    """
    Automated DAQ data deletion system.
    
    Monitors SSD storage and safely deletes validated data when storage exceeds
    the trigger threshold, with comprehensive safety checks and logging.
    
    Features:
    - Real-time storage monitoring with event capacity calculations
    - Event size: 592,128 bytes (~0.565 MB) per event (9 DAQs active)
    - Visual storage display with color-coded status
    - Sequential deletion starting from lowest run numbers
    - Comprehensive safety verification before each deletion
    """
    
    def __init__(self, real_deletion: bool = False, monitoring_interval: int = 300,
                 trigger_threshold: float = 60.0, stop_threshold: float = 30.0,
                 require_secondary_backup: bool = False):
        """
        Initialize the auto-deletion system.

        Args:
            real_deletion: If True, perform actual deletion (DANGEROUS)
            monitoring_interval: Seconds between storage checks
            trigger_threshold: Storage percentage to trigger deletion
            stop_threshold: Storage percentage to stop deletion
            require_secondary_backup: If True, also require HDD2 (HDD_16TB_4)
                COPIED.flag + VALIDATED.flag before a run is considered safe to
                delete. Default False: only HDD1 (HDD_24TB_6) is required.
        """
        self.real_deletion = real_deletion
        self.monitoring_interval = monitoring_interval
        self.trigger_threshold = trigger_threshold
        self.stop_threshold = stop_threshold
        self.require_secondary_backup = require_secondary_backup

        # Paths
        self.source_base = "/Volumes/SSD_8TB"
        self.hdd1_base = "/Volumes/HDD_24TB_6"
        self.hdd2_base = "/Volumes/HDD_16TB_4"
        
        # Safety limits
        if trigger_threshold > 90.0:
            raise ValueError("Trigger threshold cannot exceed 90% for safety")
        if stop_threshold >= trigger_threshold:
            raise ValueError("Stop threshold must be less than trigger threshold")
        
        # Logging
        self.setup_logging()
        
        # State tracking
        self.deletion_in_progress = False
        self.waiting_for_processing = False  # New state for unprocessed runs
        self.total_runs_deleted = 0
        self.total_bytes_freed = 0
        self.last_unprocessed_runs = set()  # Track which runs were unprocessed
        
    def setup_logging(self) -> None:
        """Setup comprehensive logging infrastructure."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"./Log/auto_deletion_log_{timestamp}.txt"
        
        # Ensure log directory exists
        os.makedirs("./Log", exist_ok=True)
        
        # Initialize log file with critical warnings
        with open(self.log_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("DAQ AUTOMATED DATA DELETION LOG - EXTREMELY DANGEROUS OPERATION\n")
            f.write("=" * 80 + "\n")
            f.write(f"Started at: {datetime.datetime.now()}\n")
            f.write(f"Real deletion mode: {self.real_deletion}\n")
            f.write(f"Monitoring interval: {self.monitoring_interval} seconds\n")
            f.write(f"Trigger threshold: {self.trigger_threshold}%\n")
            f.write(f"Stop threshold: {self.stop_threshold}%\n")
            f.write("=" * 80 + "\n\n")
    
    def log_message(self, message: str, level: str = "INFO") -> None:
        """
        Log a message to both console and log file.
        
        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, SUCCESS, CRITICAL)
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Print to console with colors
        if level == "INFO":
            print_info(message)
        elif level == "WARNING":
            print_warning(message)
        elif level == "ERROR":
            print_error(message)
        elif level == "SUCCESS":
            print_success(message)
        elif level == "CRITICAL":
            print(f"{Colors.ERROR}{Colors.BOLD}[CRITICAL]{Colors.ENDC} {message}")
        else:
            print(log_entry)
        
        # Write to log file
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_entry + "\n")
                f.flush()
        except Exception as e:
            print(f"Failed to write to log file: {e}")
    
    def get_storage_info(self) -> StorageInfo:
        """
        Get current storage information for the SSD.
        
        Returns:
            StorageInfo object with current storage statistics
        """
        try:
            total, used, free = shutil.disk_usage(self.source_base)
            usage_percent = (used / total) * 100
            return StorageInfo(total, used, free, usage_percent)
        except Exception as e:
            self.log_message(f"Failed to get storage info: {e}", "ERROR")
            raise
    
    def display_storage_status(self, storage: StorageInfo) -> None:
        """
        Display visual storage status like monitor_storage.sh with event calculations.
        
        Args:
            storage: Current storage information
        """
        # Convert to GB for display
        total_gb = storage.total_bytes / (1024**3)
        used_gb = storage.used_bytes / (1024**3)
        free_gb = storage.free_bytes / (1024**3)
        
        # Calculate events based on current DAQ configuration:
        # 9 DAQs × (Waveform 65536 B + Fast 256 B) = 9 × 65792 = 592,128 bytes per event
        event_size_bytes = 592_128

        total_events_capacity = storage.total_bytes // event_size_bytes
        used_events = storage.used_bytes // event_size_bytes
        free_events = storage.free_bytes // event_size_bytes
        
        # Create visual bar (50 characters wide)
        bar_length = 50
        filled_length = int(bar_length * (storage.usage_percent / 100))
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # Set colors based on usage
        if storage.usage_percent > 80:
            color = Colors.ERROR
            status = "CRITICAL"
        elif storage.usage_percent > 70:
            color = Colors.WARNING
            status = "HIGH"
        elif storage.usage_percent > 50:
            color = Colors.WARNING
            status = "MODERATE"
        else:
            color = Colors.OKGREEN
            status = "GOOD"
        
        print(f"\n{color}┌{'─' * 86}┐{Colors.ENDC}")
        print(f"{color}│ STORAGE STATUS: {status:<20} {Colors.ENDC}")
        print(f"{color}│ |{bar}| {storage.usage_percent:.1f}% {Colors.ENDC}")
        print(f"{color}│ Used: {used_gb:.1f}GB / Total: {total_gb:.1f}GB / Free: {free_gb:.1f}GB {Colors.ENDC}")
        print(f"{color}│ Events: {free_events:,} available / {total_events_capacity:,} total {Colors.ENDC}")
        print(f"{color}│ Event size: {event_size_bytes:,} bytes ({event_size_bytes/1024/1024:.2f} MB each) {Colors.ENDC}")
        print(f"{color}└{'─' * 86}┘{Colors.ENDC}\n")
        
        # Show threshold status
        if storage.usage_percent > self.trigger_threshold:
            if self.waiting_for_processing:
                self.log_message(f"Storage usage {storage.usage_percent:.1f}% exceeds trigger threshold {self.trigger_threshold}% - WAITING FOR PROCESSING", "WARNING")
                self.log_message(f"Waiting for {len(self.last_unprocessed_runs)} runs to be copied and validated", "WARNING")
            else:
                self.log_message(f"Storage usage {storage.usage_percent:.1f}% exceeds trigger threshold {self.trigger_threshold}%", "CRITICAL")
            self.log_message(f"Can store approximately {free_events:,} more events before reaching 100%", "WARNING")
        elif storage.usage_percent < self.stop_threshold:
            self.log_message(f"Storage usage {storage.usage_percent:.1f}% below stop threshold {self.stop_threshold}%", "SUCCESS")
            self.log_message(f"Can store approximately {free_events:,} more events in available space", "SUCCESS")
        else:
            self.log_message(f"Can store approximately {free_events:,} more events in available space", "INFO")
    
    def get_run_directories(self) -> List[int]:
        """
        Get sorted list of run numbers from the source directory.
        
        Returns:
            Sorted list of run numbers (lowest first for deletion order)
        """
        try:
            if not os.path.exists(self.source_base):
                self.log_message(f"Source directory {self.source_base} does not exist", "ERROR")
                return []
            
            run_dirs = []
            for item in os.listdir(self.source_base):
                if item.startswith("Run_") and os.path.isdir(os.path.join(self.source_base, item)):
                    try:
                        run_num = int(item.replace("Run_", ""))
                        run_dirs.append(run_num)
                    except ValueError:
                        continue
            
            return sorted(run_dirs)  # Lowest first for deletion order
        
        except Exception as e:
            self.log_message(f"Error scanning run directories: {e}", "ERROR")
            return []
    
    def verify_run_safety(self, run_number: int) -> Tuple[bool, str]:
        """
        Verify that a run is safe to delete (copied and validated).
        
        Args:
            run_number: Run number to verify
            
        Returns:
            Tuple of (is_safe, reason_message)
        """
        source_path = os.path.join(self.source_base, f"Run_{run_number}")
        hdd1_path = os.path.join(self.hdd1_base, f"Run_{run_number}")
        hdd2_path = os.path.join(self.hdd2_base, f"Run_{run_number}")

        # Check 1: Source exists
        if not os.path.exists(source_path):
            return False, f"Source directory does not exist: {source_path}"

        # Check 2: HDD1 copy exists and has COPIED flag
        if not os.path.exists(hdd1_path):
            return False, f"HDD1 copy does not exist: {hdd1_path}"
        if not check_flag_file_exists(hdd1_path, "COPIED.flag"):
            return False, f"HDD1 copy not flagged as copied: {hdd1_path}/COPIED.flag missing"

        # Check 3 (optional): HDD2 copy exists and has COPIED flag
        if self.require_secondary_backup:
            if not os.path.exists(hdd2_path):
                return False, f"HDD2 copy does not exist: {hdd2_path}"
            if not check_flag_file_exists(hdd2_path, "COPIED.flag"):
                return False, f"HDD2 copy not flagged as copied: {hdd2_path}/COPIED.flag missing"

        # Check 4: Source has VALIDATED flag
        if not check_flag_file_exists(source_path, "VALIDATED.flag"):
            return False, f"Source not flagged as validated: {source_path}/VALIDATED.flag missing"

        # Check 5: HDD1 has VALIDATED flag
        if not check_flag_file_exists(hdd1_path, "VALIDATED.flag"):
            return False, f"HDD1 copy not flagged as validated: {hdd1_path}/VALIDATED.flag missing"

        # Check 6 (optional): HDD2 has VALIDATED flag
        if self.require_secondary_backup:
            if not check_flag_file_exists(hdd2_path, "VALIDATED.flag"):
                return False, f"HDD2 copy not flagged as validated: {hdd2_path}/VALIDATED.flag missing"

        # Check 7: Data file counts match (extra safety)
        try:
            source_files = get_data_files(source_path)
            hdd1_files = get_data_files(hdd1_path)

            if len(source_files) != len(hdd1_files):
                return False, f"Data file count mismatch: Source={len(source_files)}, HDD1={len(hdd1_files)}"

            if self.require_secondary_backup:
                hdd2_files = get_data_files(hdd2_path)
                if len(source_files) != len(hdd2_files):
                    return False, f"Data file count mismatch: Source={len(source_files)}, HDD2={len(hdd2_files)}"
        except Exception as e:
            return False, f"Error checking data file counts: {e}"

        return True, "All safety checks passed"
    
    def calculate_run_size(self, run_number: int) -> int:
        """
        Calculate the total size of a run directory.
        
        Args:
            run_number: Run number to calculate size for
            
        Returns:
            Size in bytes, or 0 if error
        """
        try:
            source_path = os.path.join(self.source_base, f"Run_{run_number}")
            if not os.path.exists(source_path):
                return 0
            
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(source_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except OSError:
                        continue
            
            return total_size
        except Exception:
            return 0
    
    def delete_run(self, run_number: int) -> bool:
        """
        Delete a single run with comprehensive safety checks.
        
        Args:
            run_number: Run number to delete
            
        Returns:
            True if successful, False otherwise
        """
        self.log_message(f"{'DRY RUN: ' if not self.real_deletion else ''}Attempting to delete Run_{run_number}", "CRITICAL")
        
        # Verify safety first
        is_safe, reason = self.verify_run_safety(run_number)
        if not is_safe:
            self.log_message(f"SAFETY CHECK FAILED for Run_{run_number}: {reason}", "ERROR")
            return False
        
        # Calculate size before deletion
        run_size = self.calculate_run_size(run_number)
        run_size_gb = run_size / (1024**3)
        
        self.log_message(f"Safety verification PASSED for Run_{run_number} ({run_size_gb:.2f}GB)", "SUCCESS")
        
        if self.real_deletion:
            # Execute actual deletion using the existing script
            self.log_message(f"EXECUTING REAL DELETION of Run_{run_number}", "CRITICAL")
            
            try:
                result = subprocess.run(
                    ["./Remove_Data.sh", str(run_number)],
                    capture_output=True,
                    text=True,
                    timeout=1800  # 30 minute timeout
                )
                
                if result.returncode == 0:
                    self.log_message(f"Successfully deleted Run_{run_number} ({run_size_gb:.2f}GB)", "SUCCESS")
                    self.total_runs_deleted += 1
                    self.total_bytes_freed += run_size
                    return True
                else:
                    self.log_message(f"Deletion script failed for Run_{run_number}: {result.stderr}", "ERROR")
                    return False
                    
            except subprocess.TimeoutExpired:
                self.log_message(f"Deletion script timed out for Run_{run_number}", "ERROR")
                return False
            except Exception as e:
                self.log_message(f"Error executing deletion script for Run_{run_number}: {e}", "ERROR")
                return False
        else:
            # Dry run mode
            self.log_message(f"DRY RUN: Would delete Run_{run_number} ({run_size_gb:.2f}GB)", "WARNING")
            self.total_runs_deleted += 1
            self.total_bytes_freed += run_size
            return True
    
    def deletion_cycle(self) -> bool:
        """
        Perform one deletion cycle - attempts to delete one safe run.
        
        Returns:
            True if deletion should continue (more runs available and above stop threshold)
            False if should stop (reached stop threshold, no safe runs, or error)
        """
        storage = self.get_storage_info()
        self.display_storage_status(storage)
        
        # Check if we should stop
        if storage.usage_percent < self.stop_threshold:
            self.log_message(f"Storage usage {storage.usage_percent:.1f}% below stop threshold {self.stop_threshold}%", "SUCCESS")
            return False
        
        # Get runs to delete (sorted by number, lowest first)
        run_numbers = self.get_run_directories()
        if not run_numbers:
            self.log_message("No run directories found", "WARNING")
            return False
        
        # Track unprocessed runs and find deletable runs
        unprocessed_runs = set()
        
        # Find the first deletable run
        for run_number in run_numbers:
            self.log_message(f"Evaluating Run_{run_number} for deletion...")
            
            is_safe, reason = self.verify_run_safety(run_number)
            if is_safe:
                success = self.delete_run(run_number)
                if success:
                    # Successfully deleted a run - clear waiting state
                    self.waiting_for_processing = False
                    self.last_unprocessed_runs.clear()
                    
                    # Check storage again after deletion
                    new_storage = self.get_storage_info()
                    self.log_message(f"Storage after deletion: {new_storage.usage_percent:.1f}%")
                    
                    if new_storage.usage_percent < self.stop_threshold:
                        self.log_message("Reached stop threshold, stopping deletion cycle", "SUCCESS")
                        return False
                    else:
                        return True  # Continue deletion
                else:
                    self.log_message(f"Failed to delete Run_{run_number}, stopping deletion cycle", "ERROR")
                    return False
            else:
                # Track this as an unprocessed run
                if "copy" in reason.lower() or "validat" in reason.lower() or "flag" in reason.lower():
                    unprocessed_runs.add(run_number)
                self.log_message(f"Skipping Run_{run_number}: {reason}", "WARNING")
                continue
        
        # Check if we have only unprocessed runs
        if unprocessed_runs and len(unprocessed_runs) == len(run_numbers):
            # All remaining runs are unprocessed - enter waiting state
            if not self.waiting_for_processing:
                self.log_message("All remaining runs are unprocessed (not copied/validated)", "WARNING")
                self.log_message("Entering 'waiting for processing' state - will monitor for newly processed runs", "INFO")
                self.waiting_for_processing = True
            
            # Check if any runs became processable since last check
            newly_processable = self.last_unprocessed_runs - unprocessed_runs
            if newly_processable:
                self.log_message(f"Detected newly processable runs: {sorted(newly_processable)}", "SUCCESS")
                self.waiting_for_processing = False
                return True  # Retry deletion cycle
            
            self.last_unprocessed_runs = unprocessed_runs.copy()
            self.log_message(f"Still waiting for {len(unprocessed_runs)} runs to be processed: Run_{min(unprocessed_runs)} - Run_{max(unprocessed_runs)}", "INFO")
            return False  # Don't continue deletion, but stay in monitoring mode
        elif unprocessed_runs:
            # Some runs are processable, some aren't - this is normal
            self.log_message(f"Found {len(unprocessed_runs)} unprocessed runs, but no safe runs available for deletion", "WARNING")
            return False
        else:
            # No runs found at all
            self.log_message("No run directories found for deletion", "WARNING")
            return False
    
    def monitoring_cycle(self) -> None:
        """Run one monitoring cycle."""
        try:
            storage = self.get_storage_info()
            self.display_storage_status(storage)
            
            # Log current status
            self.log_message(f"Storage monitoring: {storage.usage_percent:.1f}% used")
            
            # Check if deletion is needed
            if storage.usage_percent > self.trigger_threshold:
                if not self.deletion_in_progress and not self.waiting_for_processing:
                    self.log_message(f"Storage usage {storage.usage_percent:.1f}% exceeds trigger threshold {self.trigger_threshold}%", "CRITICAL")
                    self.log_message("Starting automated deletion process", "CRITICAL")
                    self.deletion_in_progress = True
                elif self.waiting_for_processing:
                    self.log_message(f"Storage usage {storage.usage_percent:.1f}% still above threshold, but waiting for runs to be processed", "WARNING")
                
                # Perform deletion cycles until stop threshold reached or no more runs
                while True:
                    continue_deletion = self.deletion_cycle()
                    if not continue_deletion:
                        if not self.waiting_for_processing:
                            # True completion - either reached threshold or no more runs
                            self.deletion_in_progress = False
                            self.log_message("Deletion process completed", "SUCCESS")
                        else:
                            # In waiting state - keep deletion_in_progress true but log waiting status
                            self.log_message("Continuing to monitor for newly processed runs", "INFO")
                        break  # Exit deletion loop
                    else:
                        # Continue with next deletion cycle after brief pause
                        self.log_message("Continuing deletion to reach stop threshold...", "INFO")
                        time.sleep(2)  # Brief pause between deletions for system stability
            else:
                # Storage below trigger threshold
                if self.deletion_in_progress or self.waiting_for_processing:
                    self.deletion_in_progress = False
                    self.waiting_for_processing = False
                    self.last_unprocessed_runs.clear()
                    self.log_message("Storage below trigger threshold, stopping deletion", "SUCCESS")
                
        except Exception as e:
            self.log_message(f"Error in monitoring cycle: {e}", "ERROR")
    
    def run(self) -> None:
        """Run the automated deletion system."""
        self.log_message("Starting DAQ automated deletion system", "CRITICAL")
        self.log_message(f"Mode: {'REAL DELETION' if self.real_deletion else 'DRY RUN'}", "CRITICAL")
        self.log_message(f"Trigger threshold: {self.trigger_threshold}%", "INFO")
        self.log_message(f"Stop threshold: {self.stop_threshold}%", "INFO")
        self.log_message(f"Check interval: {self.monitoring_interval} seconds", "INFO")
        self.log_message(f"HDD1 (primary backup): {self.hdd1_base}", "INFO")
        if self.require_secondary_backup:
            self.log_message(f"HDD2 (secondary backup) REQUIRED: {self.hdd2_base}", "INFO")
        else:
            self.log_message("HDD2 (secondary backup) NOT required for deletion", "INFO")
        
        if not self.real_deletion:
            self.log_message("DRY RUN MODE - No actual deletions will be performed", "WARNING")
        
        try:
            while True:
                self.monitoring_cycle()
                
                # Show summary if any deletions occurred
                if self.total_runs_deleted > 0:
                    freed_gb = self.total_bytes_freed / (1024**3)
                    self.log_message(f"Session summary: {self.total_runs_deleted} runs processed, {freed_gb:.2f}GB freed", "INFO")
                
                self.log_message(f"Waiting {self.monitoring_interval} seconds for next cycle...")
                time.sleep(self.monitoring_interval)
                
        except KeyboardInterrupt:
            self.log_message("Automated deletion stopped by user", "WARNING")
            freed_gb = self.total_bytes_freed / (1024**3)
            self.log_message(f"Final summary: {self.total_runs_deleted} runs processed, {freed_gb:.2f}GB freed", "INFO")
        except Exception as e:
            self.log_message(f"Fatal error: {e}", "ERROR")
            raise


def main():
    """Main function for the automated deletion script."""
    parser = argparse.ArgumentParser(
        description="DAQ Automated Data Deletion - EXTREMELY DANGEROUS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CRITICAL SAFETY WARNINGS:
- This script PERMANENTLY DELETES experimental data
- DRY RUN is the default mode for safety
- Use --real-deletion flag only after careful verification
- Always monitor logs during operation
- Have backup recovery plan ready

Examples:
  python3 daq_auto_deletion.py                    # Safe dry-run monitoring
  python3 daq_auto_deletion.py --real-deletion   # DANGEROUS: Real deletion
  python3 daq_auto_deletion.py --interval 120    # Check every 2 minutes
        """
    )
    
    parser.add_argument("--real-deletion", action="store_true",
                       help="Enable real deletion mode (DANGEROUS)")
    parser.add_argument("--interval", type=int, default=300,
                       help="Monitoring interval in seconds (default: 300)")
    parser.add_argument("--force-threshold", type=float,
                       help="Override 60%% trigger threshold (DANGEROUS)")
    parser.add_argument("--require-secondary-backup", action="store_true",
                       help="Also require the secondary (HDD_16TB_4) backup to be "
                            "copied and validated before deleting from the SSD. "
                            "Default: off (only HDD_24TB_6 is required).")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.interval < 5:
        print("Error: Monitoring interval must be at least 5 seconds for safety")
        sys.exit(1)
    
    trigger_threshold = args.force_threshold if args.force_threshold else 60.0
    
    if trigger_threshold > 90.0:
        print("Error: Trigger threshold cannot exceed 90% for safety")
        sys.exit(1)
    
    # Safety confirmation for real deletion mode
    if args.real_deletion:
        print(f"{Colors.ERROR}{Colors.BOLD}WARNING: REAL DELETION MODE ENABLED{Colors.ENDC}")
        print(f"{Colors.ERROR}This will PERMANENTLY DELETE experimental data{Colors.ENDC}")
        print(f"{Colors.ERROR}Are you absolutely sure? Type 'DELETE_DATA_PERMANENTLY' to confirm:{Colors.ENDC}")
        
        confirmation = input().strip()
        if confirmation != "DELETE_DATA_PERMANENTLY":
            print("Confirmation failed. Exiting for safety.")
            sys.exit(1)
        
        print(f"{Colors.ERROR}Real deletion mode confirmed. Proceeding...{Colors.ENDC}")
    
    # Create and run deletion system
    deletion_system = DAQAutoDeletion(
        real_deletion=args.real_deletion,
        monitoring_interval=args.interval,
        trigger_threshold=trigger_threshold,
        require_secondary_backup=args.require_secondary_backup,
    )
    
    deletion_system.run()


if __name__ == "__main__":
    main()