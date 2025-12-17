"""
DAQ Data Processing Automation Script

This script monitors the experimental data directory and automatically processes
new runs through the complete dual-backup workflow:

1. Monitors /Volumes/SSD_8TB/ for new run directories
2. When a new run appears (Run_N), processes unprocessed runs starting from the lowest run number:
   a. Copy SSD → HDD_16TB_2 (primary backup)
   b. Validate SSD ↔ HDD_16TB_2
   c. Copy HDD_16TB_2 → HDD_16TB_4 (secondary backup)
   d. Validate HDD_16TB_2 ↔ HDD_16TB_4

Safety Features:
- Checks if data is already copied before starting transfer
- Comprehensive logging of all operations
- Monitors for errors and stops on failure
- Does NOT automate deletion (manual safety requirement)
- Validates all prerequisites before each step

Usage:
    python3 daq_automation.py [--interval SECONDS] [--dry-run]
    
Arguments:
    --interval SECONDS  : Monitoring interval in seconds (default: 60)
    --dry-run          : Show what would be done without executing
    
Example:
    python3 daq_automation.py --interval 30
    
Logging:
    Main log: ./Log/automation_log_YYYYMMDD_HHMMSS.txt
    Individual operations logged to their respective directories
    
CRITICAL: This script handles extremely valuable experimental data.
All operations include comprehensive safety checks and logging.
"""

import os
import sys
import time
import argparse
import subprocess
import datetime
from typing import List, Tuple, Optional
from daq_utils import (
    Colors, print_info, print_warning, print_error, print_success,
    validate_path_exists, check_flag_file_exists
)

class DAQAutomation:
    """
    Automated DAQ data processing system.
    
    Monitors for new runs and automatically processes the previous run
    through the complete backup and validation workflow.
    """
    
    def __init__(self, monitoring_interval: int = 60, dry_run: bool = False):
        """
        Initialize the automation system.
        
        Args:
            monitoring_interval: Seconds between directory checks
            dry_run: If True, show what would be done without executing
        """
        self.monitoring_interval = monitoring_interval
        self.dry_run = dry_run
        
        # Paths
        self.source_base = "/Volumes/SSD_8TB"
        self.hdd1_base = "/Volumes/HDD_16TB_2"
        self.hdd2_base = "/Volumes/HDD_16TB_4"
        
        # Script paths
        self.transfer_ssd_script = "./Transfer_Data.sh"
        self.validate_ssd_script = "./Valid_Data.sh"
        self.transfer_hdd_script = "./Transfer_Data_HDD.sh"
        self.validate_hdd_script = "./Valid_Data_HDD.sh"
        
        # Logging
        self.setup_logging()
        
        # State tracking
        self.last_processed_run = None
        self.currently_processing = False
        
    def setup_logging(self) -> None:
        """Setup logging infrastructure."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"./Log/automation_log_{timestamp}.txt"
        
        # Ensure log directory exists
        os.makedirs("./Log", exist_ok=True)
        
        # Initialize log file
        with open(self.log_file, 'w') as f:
            f.write(f"DAQ Automation Log - Started at {datetime.datetime.now()}\n")
            f.write(f"Monitoring interval: {self.monitoring_interval} seconds\n")
            f.write(f"Dry run mode: {self.dry_run}\n")
            f.write("=" * 80 + "\n\n")
    
    def log_message(self, message: str, level: str = "INFO") -> None:
        """
        Log a message to both console and log file.
        
        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, SUCCESS)
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
        else:
            print(log_entry)
        
        # Write to log file
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_entry + "\n")
                f.flush()
        except Exception as e:
            print(f"Failed to write to log file: {e}")
    
    def get_run_directories(self) -> List[int]:
        """
        Get list of run numbers from the source directory.
        
        Returns:
            Sorted list of run numbers found in the source directory
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
            
            return sorted(run_dirs)
        
        except Exception as e:
            self.log_message(f"Error scanning run directories: {e}", "ERROR")
            return []
    
    def is_run_already_copied(self, run_number: int) -> Tuple[bool, bool]:
        """
        Check if a run is already copied to HDDs.
        
        Args:
            run_number: Run number to check
            
        Returns:
            Tuple of (copied_to_hdd1, copied_to_hdd2)
        """
        hdd1_path = os.path.join(self.hdd1_base, f"Run_{run_number}")
        hdd2_path = os.path.join(self.hdd2_base, f"Run_{run_number}")
        
        hdd1_copied = os.path.exists(hdd1_path) and check_flag_file_exists(hdd1_path, "COPIED.flag")
        hdd2_copied = os.path.exists(hdd2_path) and check_flag_file_exists(hdd2_path, "COPIED.flag")
        
        return hdd1_copied, hdd2_copied
    
    def is_run_validated(self, run_number: int) -> Tuple[bool, bool]:
        """
        Check if a run is already validated.
        
        Args:
            run_number: Run number to check
            
        Returns:
            Tuple of (ssd_validated, hdd_validated)
        """
        source_path = os.path.join(self.source_base, f"Run_{run_number}")
        hdd1_path = os.path.join(self.hdd1_base, f"Run_{run_number}")
        hdd2_path = os.path.join(self.hdd2_base, f"Run_{run_number}")
        
        # SSD validation: check if VALIDATED.flag exists in source
        ssd_validated = os.path.exists(source_path) and check_flag_file_exists(source_path, "VALIDATED.flag")
        
        # HDD validation: check if VALIDATED.flag exists in both HDDs
        hdd_validated = (os.path.exists(hdd1_path) and check_flag_file_exists(hdd1_path, "VALIDATED.flag") and
                        os.path.exists(hdd2_path) and check_flag_file_exists(hdd2_path, "VALIDATED.flag"))
        
        return ssd_validated, hdd_validated
    
    def execute_script(self, script_path: str, run_number: int, additional_args: List[str] = None) -> bool:
        """
        Execute a shell script with live output and proper logging.
        
        Args:
            script_path: Path to the script to execute
            run_number: Run number argument
            additional_args: Additional arguments for the script
            
        Returns:
            True if successful, False otherwise
        """
        if additional_args is None:
            additional_args = []
            
        cmd = [script_path, str(run_number)] + additional_args
        
        if self.dry_run:
            self.log_message(f"DRY RUN: Would execute: {' '.join(cmd)}")
            return True
        
        self.log_message(f"Executing: {' '.join(cmd)}")
        
        try:
            # Set environment variable to signal automation mode (disables tee logging)
            env = os.environ.copy()
            env['DAQ_AUTOMATION'] = 'true'
            
            # Use direct execution to preserve terminal behavior for progress bars
            import signal
            
            # Store original stdout
            original_stdout = sys.stdout
            
            # Start the process with direct terminal output (preserves \r behavior)
            process = subprocess.Popen(
                cmd,
                env=env,
                # Let output go directly to terminal for perfect progress bar behavior
                stdout=None,  # Use terminal stdout directly
                stderr=None   # Use terminal stderr directly
            )
            
            # Monitor process with timeout
            start_time = time.time()
            timeout = 3600  # 1 hour timeout
            
            while True:
                # Check for timeout
                if time.time() - start_time > timeout:
                    self.log_message(f"Script timed out after {timeout} seconds", "ERROR")
                    try:
                        process.kill()
                    except:
                        pass
                    return False
                
                # Check if process has finished
                if process.poll() is not None:
                    break
                    
                # Small delay to avoid busy waiting
                time.sleep(0.1)
            
            # Get the return code
            return_code = process.returncode
            
            if return_code == 0:
                self.log_message(f"Successfully completed: {' '.join(cmd)}", "SUCCESS")
                return True
            else:
                self.log_message(f"Script failed with return code {return_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log_message(f"Error executing script: {e}", "ERROR")
            if 'process' in locals():
                try:
                    process.kill()
                except:
                    pass
            return False
    
    def process_run(self, run_number: int) -> bool:
        """
        Process a single run through the complete workflow.
        
        Args:
            run_number: Run number to process
            
        Returns:
            True if all steps completed successfully, False otherwise
        """
        self.log_message(f"Starting processing of Run_{run_number}")
        
        # Check if run exists in source
        source_path = os.path.join(self.source_base, f"Run_{run_number}")
        if not os.path.exists(source_path):
            self.log_message(f"Source path does not exist: {source_path}", "ERROR")
            return False
        
        # Check current status (primary + secondary backup)
        hdd1_copied, hdd2_copied = self.is_run_already_copied(run_number)
        ssd_validated, hdd_validated = self.is_run_validated(run_number)
        
        self.log_message(f"Current status for Run_{run_number}:")
        self.log_message(f"  HDD1 copied: {hdd1_copied}")
        self.log_message(f"  HDD2 copied: {hdd2_copied}")
        self.log_message(f"  SSD validated: {ssd_validated}")
        self.log_message(f"  HDD validated: {hdd_validated}")
        
        # Step 1: Copy SSD → HDD1 (if not already done)
        if not hdd1_copied:
            self.log_message(f"Step 1: Copying Run_{run_number} from SSD to HDD1")
            if not self.execute_script(self.transfer_ssd_script, run_number):
                self.log_message(f"Failed to copy Run_{run_number} to HDD1", "ERROR")
                return False
            hdd1_copied = True
        else:
            self.log_message(f"Step 1: Run_{run_number} already copied to HDD1, skipping")
        
        # Step 2: Validate SSD ↔ HDD1 (if not already done)
        if not ssd_validated:
            self.log_message(f"Step 2: Validating Run_{run_number} between SSD and HDD1")
            if not self.execute_script(self.validate_ssd_script, run_number):
                self.log_message(f"Failed to validate Run_{run_number} SSD↔HDD1", "ERROR")
                return False
            ssd_validated = True
        else:
            self.log_message(f"Step 2: Run_{run_number} already validated (SSD↔HDD1), skipping")
        
        # Step 3: Copy HDD1 → HDD2 (secondary backup)
        if not hdd2_copied:
            if not hdd1_copied:
                self.log_message("Cannot start secondary backup before primary copy is complete", "ERROR")
                return False
            self.log_message(f"Step 3: Copying Run_{run_number} from HDD1 to HDD2")
            if not self.execute_script(self.transfer_hdd_script, run_number):
                self.log_message(f"Failed to copy Run_{run_number} to HDD2", "ERROR")
                return False
            hdd2_copied = True
        else:
            self.log_message(f"Step 3: Run_{run_number} already copied to HDD2, skipping")
        
        # Step 4: Validate HDD1 ↔ HDD2 (if not already done)
        if not hdd_validated:
            if not hdd2_copied:
                self.log_message("Cannot validate HDD backups before secondary copy is complete", "ERROR")
                return False
            self.log_message(f"Step 4: Validating Run_{run_number} between HDD1 and HDD2")
            if not self.execute_script(self.validate_hdd_script, run_number):
                self.log_message(f"Failed to validate Run_{run_number} HDD1↔HDD2", "ERROR")
                return False
            hdd_validated = True
        else:
            self.log_message(f"Step 4: Run_{run_number} already validated (HDD1↔HDD2), skipping")
        
        self.log_message(f"Successfully completed dual backup and validation for Run_{run_number}", "SUCCESS")
        return True
    
    def run_monitoring_cycle(self) -> None:
        """Run one monitoring cycle."""
        try:
            # Get current run directories
            run_numbers = self.get_run_directories()
            
            if len(run_numbers) < 2:
                self.log_message(f"Found {len(run_numbers)} runs, need at least 2 to start processing")
                return
            
            # Latest run is still being taken, so process the second-to-last
            latest_run = max(run_numbers)
            processable_runs = [r for r in run_numbers if r < latest_run]
            
            if not processable_runs:
                self.log_message("No processable runs found")
                return
            
            # Find the lowest unprocessed run (process in chronological order)
            for run_number in sorted(processable_runs):
                hdd1_copied, hdd2_copied = self.is_run_already_copied(run_number)
                ssd_validated, hdd_validated = self.is_run_validated(run_number)
                
                # If this run is completely processed (primary + secondary), continue to the next
                if hdd1_copied and hdd2_copied and ssd_validated and hdd_validated:
                    if self.last_processed_run is None or run_number > self.last_processed_run:
                        self.last_processed_run = run_number
                    self.log_message(f"Run_{run_number} is already fully processed (dual backup)")
                    continue
                
                # Process this run
                self.log_message(f"Found processable run: Run_{run_number} (latest is Run_{latest_run})")
                
                if self.currently_processing:
                    self.log_message("Already processing a run, skipping this cycle")
                    return
                
                self.currently_processing = True
                success = self.process_run(run_number)
                
                if success:
                    self.last_processed_run = run_number
                    self.log_message(f"Successfully processed Run_{run_number}", "SUCCESS")
                else:
                    self.log_message(f"Failed to process Run_{run_number}", "ERROR")
                
                self.currently_processing = False
                return  # Process one run per cycle
                
        except Exception as e:
            self.log_message(f"Error in monitoring cycle: {e}", "ERROR")
            self.currently_processing = False
    
    def run(self) -> None:
        """Run the automation system."""
        self.log_message("Starting DAQ automation system")
        self.log_message(f"Monitoring directory: {self.source_base}")
        self.log_message(f"Check interval: {self.monitoring_interval} seconds")
        
        if self.dry_run:
            self.log_message("DRY RUN MODE - No actual operations will be performed", "WARNING")
        
        try:
            while True:
                self.log_message(f"Running monitoring cycle...")
                self.run_monitoring_cycle()
                
                self.log_message(f"Waiting {self.monitoring_interval} seconds for next cycle...")
                time.sleep(self.monitoring_interval)
                
        except KeyboardInterrupt:
            self.log_message("Automation stopped by user", "WARNING")
        except Exception as e:
            self.log_message(f"Fatal error: {e}", "ERROR")
            raise


def main():
    """Main function for the automation script."""
    parser = argparse.ArgumentParser(description="DAQ Data Processing Automation")
    parser.add_argument("--interval", type=int, default=60,
                       help="Monitoring interval in seconds (default: 60)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without executing")
    
    args = parser.parse_args()
    
    # Validate monitoring interval
    if args.interval < 1:
        print("Error: Monitoring interval must be at least 1 seconds")
        sys.exit(1)
    
    # Create and run automation system
    automation = DAQAutomation(
        monitoring_interval=args.interval,
        dry_run=args.dry_run
    )
    
    automation.run()


if __name__ == "__main__":
    main()