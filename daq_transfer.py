"""
DAQ Data Transfer Module

This module provides the core transfer functionality for the DAQ data transfer system.
It handles copying data between storage devices with comprehensive safety checks,
progress monitoring, and logging.

The module supports:
- SSD to HDD transfers (primary copy)
- HDD to HDD transfers (backup copy)
- Storage space validation
- Progress monitoring with rsync
- Automatic flag file creation for tracking transfer status
"""

import os
import sys
import re
import time
import shlex
import subprocess
import threading
from typing import Tuple, Optional
from daq_utils import (
    Colors, get_directory_size, check_storage_usage, ask_urgent_confirmation,
    ask_command_execution, validate_path_exists, ensure_trailing_slash,
    check_flag_file_exists, create_flag_file, execute_rsync_command,
    print_info, print_success, print_warning, print_error_block, format_size_gb,
    get_data_files
)


class TransferProgressBar:
    """Enhanced progress bar for file transfers with file count and data progress."""
    
    def __init__(self, total_files: int, total_size: int):
        self.total_files = total_files
        self.total_size = total_size
        self.transferred_files = 0
        self.transferred_size = 0
        self.current_file = ""
        self.transfer_rate = ""
        self.eta = ""
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def update(self, files_done: int = None, size_done: int = None, 
               current_file: str = "", transfer_rate: str = "", eta: str = ""):
        """Update progress bar values safely."""
        with self.lock:
            if files_done is not None:
                self.transferred_files = files_done
            if size_done is not None:
                self.transferred_size = size_done
            if current_file:
                self.current_file = current_file
            if transfer_rate:
                self.transfer_rate = transfer_rate
            if eta:
                self.eta = eta
    
    def display(self):
        """Display the enhanced progress bar."""
        with self.lock:
            # Calculate percentages
            file_progress = (self.transferred_files / self.total_files) if self.total_files > 0 else 0
            size_progress = (self.transferred_size / self.total_size) if self.total_size > 0 else 0
            
            # Create progress bars
            bar_length = 40
            file_filled = int(bar_length * file_progress)
            size_filled = int(bar_length * size_progress)
            
            file_bar = '█' * file_filled + '-' * (bar_length - file_filled)
            size_bar = '█' * size_filled + '-' * (bar_length - size_filled)
            
            # Format sizes
            transferred_gb = self.transferred_size / (1024**3)
            total_gb = self.total_size / (1024**3)
            
            # Truncate filename for display
            display_file = self.current_file[:50] + "..." if len(self.current_file) > 50 else self.current_file
            
            # Calculate elapsed time
            elapsed = time.time() - self.start_time
            elapsed_str = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
            
            # Clear the line and print progress
            print(f"\r{' ' * 120}", end='')
            print(f"\r{Colors.INFO}Files:{Colors.ENDC} [{file_bar}] "
                  f"{self.transferred_files:3d}/{self.total_files:3d} "
                  f"({file_progress:.1%})", end='')
            print(f"\n{Colors.INFO}Data: {Colors.ENDC} [{size_bar}] "
                  f"{transferred_gb:.1f}/{total_gb:.1f}GB "
                  f"({size_progress:.1%}) "
                  f"{Colors.WARNING}{self.transfer_rate}{Colors.ENDC}", end='')
            print(f"\n{Colors.INFO}File: {Colors.ENDC} {display_file}", end='')
            print(f"\n{Colors.INFO}Time: {Colors.ENDC} {elapsed_str} elapsed"
                  f"{f' | ETA: {self.eta}' if self.eta else ''}", end='')
            print(f"\033[3A", end='', flush=True)  # Move cursor up 3 lines


def execute_rsync_with_progress(source_dir: str, destination_path: str, 
                              log_dir: str) -> bool:
    """
    Execute rsync command with enhanced progress monitoring.
    
    Args:
        source_dir: Source directory path
        destination_path: Destination directory path
        log_dir: Directory for storing logs
        
    Returns:
        True if transfer successful, False otherwise
    """
    # Get file count and total size for progress tracking
    source_files = get_data_files(source_dir)
    total_files = len(source_files)
    total_size = sum(os.path.getsize(f) for f in source_files if os.path.exists(f))
    
    if total_files == 0:
        print_warning("No files found to transfer!")
        return True
    
    print_info(f"Starting transfer of {total_files} files ({total_size / (1024**3):.1f} GB)")
    
    # Initialize progress bar
    progress_bar = TransferProgressBar(total_files, total_size)
    
    # Construct rsync command
    rsync_command = f"rsync -avh --progress {shlex.quote(source_dir)} {shlex.quote(destination_path)}"
    
    try:
        # Start rsync process
        process = subprocess.Popen(
            rsync_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        transferred_files = 0
        current_file = ""
        
        # Parse rsync output in real-time
        for line in process.stdout:
            line = line.strip()
            
            # Parse file completion
            if line and not line.startswith('sending') and not line.startswith('sent') \
               and not line.startswith('total size') and '.dat' in line:
                # Extract filename
                if '/' in line:
                    current_file = line.split('/')[-1]
                    if current_file.endswith('.dat'):
                        transferred_files += 1
                        progress_bar.update(files_done=transferred_files, current_file=current_file)
                        progress_bar.display()
            
            # Parse progress information from rsync
            progress_match = re.search(r'(\d+)%\s+(\S+)\s+(\d+:\d+:\d+)', line)
            if progress_match:
                percent = int(progress_match.group(1))
                rate = progress_match.group(2)
                eta = progress_match.group(3)
                
                # Estimate transferred size based on percentage
                estimated_size = int((percent / 100.0) * total_size)
                progress_bar.update(size_done=estimated_size, transfer_rate=rate, eta=eta)
                progress_bar.display()
        
        # Wait for process to complete
        return_code = process.wait()
        
        # Clear progress display
        print(f"\r{' ' * 120}")
        print(f"\r{' ' * 120}")
        print(f"\r{' ' * 120}")
        print(f"\r{' ' * 120}")
        print()
        
        if return_code == 0:
            print_success(f"Transfer completed successfully! {total_files} files transferred.")
            return True
        else:
            print_error_block(f"Transfer failed with exit code {return_code}")
            return False
            
    except Exception as e:
        print_error_block(f"Error during transfer: {e}")
        return False


class DAQTransfer:
    """
    Base class for DAQ data transfers with comprehensive safety checks.
    
    This class handles the common logic for transferring experimental data
    between different storage devices while maintaining strict safety protocols
    to prevent data loss.
    """
    
    def __init__(self, source_prefix: str, log_dir: str = "./Log/Copy_Log/"):
        """
        Initialize the transfer handler.
        
        Args:
            source_prefix: Base path prefix for source directories
            log_dir: Directory for storing transfer logs
        """
        self.source_prefix = source_prefix
        self.log_dir = log_dir
        
        # Ensure unbuffered output for real-time logging
        os.environ["PYTHONUNBUFFERED"] = "1"
    
    def get_default_destination(self) -> str:
        """
        Get the default destination directory for this transfer type.
        
        Returns:
            Default destination directory path
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement get_default_destination")
    
    def validate_transfer_compatibility(self, source_path: str, destination_path: str) -> bool:
        """
        Validate that the transfer can proceed safely by checking:
        - Source directory size
        - Destination storage space
        - Storage usage thresholds
        
        Args:
            source_path: Path to source directory
            destination_path: Path to destination directory
            
        Returns:
            True if transfer is safe to proceed
            
        Raises:
            SystemExit: If transfer cannot proceed safely
        """
        # Get parent directory of source for size calculation
        source_dir = os.path.dirname(source_path)
        print_info(f"Checking size of source data folder: {Colors.OKCYAN}{Colors.BOLD}{source_dir}{Colors.ENDC}")
        
        source_folder_size = get_directory_size(source_dir)
        print_info(f"Source data folder size = {Colors.OKCYAN}{Colors.BOLD}{format_size_gb(source_folder_size)}{Colors.ENDC}")
        
        # Check destination storage
        storage_dir = os.path.dirname(destination_path)
        print_info(f"Checking destination storage: {Colors.OKCYAN}{Colors.BOLD}{storage_dir}{Colors.ENDC}")
        
        total_space, used_space, free_space = check_storage_usage(storage_dir)
        remaining_fraction_after_transfer = (free_space - source_folder_size) / total_space
        
        # Check if there's enough space
        if free_space <= source_folder_size:
            print_error_block("Source data folder larger than destination free space, please change to new storage device")
            print_error_block("############################################################################")
            sys.exit()
        
        # Warn if remaining space will be low after transfer
        if remaining_fraction_after_transfer <= 0.2:
            print(f"{Colors.WARNING}{'#' * 97}{Colors.ENDC}")
            print(f"{Colors.WARNING}[WARNING] Storage usage will exceed " +
                  f"{Colors.BOLD}{round(100 - (100 * remaining_fraction_after_transfer), 2)}%{Colors.ENDC}" +
                  f"{Colors.WARNING} after transferring the source folder, BE CAREFUL WHEN TRANSFERRING!!{Colors.ENDC}")
            print(f"{Colors.WARNING}{'#' * 97}{Colors.ENDC}")
            
            urgent = ask_urgent_confirmation()
            if not urgent:
                print(f"{Colors.ERROR}{'#' * 99}{Colors.ENDC}")
                print(f"{Colors.ERROR}[ERROR] Storage usage will exceed " +
                      f"{Colors.BOLD}{round(100 - (100 * remaining_fraction_after_transfer), 2)}%{Colors.ENDC}" +
                      f"{Colors.ERROR} after transferring the source folder, CAN'T TRANSFER IF NOT URGENT!!{Colors.ENDC}")
                print(f"{Colors.ERROR}{'#' * 99}{Colors.ENDC}")
                sys.exit()
        
        return True
    
    def generate_destination_path(self, source_path: str, destination_base: str) -> str:
        """
        Generate the full destination path based on source path.
        
        Args:
            source_path: Source directory path
            destination_base: Base destination directory
            
        Returns:
            Full destination path
        """
        source_name = source_path.rstrip('/').split("/")[-1]
        # For SSD->HDD transfers, replace SSD with HDD in folder name
        if "SSD" in source_name:
            copy_folder_name = source_name.replace("SSD", "HDD")
        else:
            copy_folder_name = source_name
        
        return os.path.join(destination_base, copy_folder_name) + "/"
    
    def create_rsync_command(self, source_path: str, destination_path: str, run_identifier: str) -> str:
        """
        Create the rsync command for data transfer.
        
        Args:
            source_path: Source directory path
            destination_path: Destination directory path
            run_identifier: Identifier for the run (for log naming)
            
        Returns:
            Complete rsync command string
        """
        log_file = os.path.join(self.log_dir, f"rsync_log{run_identifier}.txt")
        
        cmd = (f"rsync -avh --itemize-changes --log-file={log_file} "
               f"--progress {source_path} {destination_path}")
        
        return cmd
    
    def perform_transfer(self, source_path: str, destination_path: str, run_identifier: str) -> None:
        """
        Perform the actual data transfer using rsync.
        
        Args:
            source_path: Source directory path
            destination_path: Full destination path (including target folder)
            run_identifier: Identifier for the run (for log naming)
        """
        print_info(f"Copying folder {Colors.BOLD}{Colors.OKCYAN}{source_path}{Colors.ENDC} " +
                  f"to {Colors.BOLD}{Colors.OKCYAN}{destination_path}{Colors.ENDC}")
        
        rsync_cmd = self.create_rsync_command(source_path, destination_path, run_identifier)
        
        execute_transfer = ask_command_execution(rsync_cmd)
        if execute_transfer:
            success = execute_rsync_with_progress(source_path, destination_path, self.log_dir)
            if not success:
                print_error_block("Transfer failed. Please check the logs and try again.")
                sys.exit()
    
    def create_completion_flags(self, source_path: str, destination_path: str) -> None:
        """
        Create flag files to mark successful completion of transfer.
        
        Args:
            source_path: Source directory path
            destination_path: Destination directory path
        """
        create_flag_file(source_path, "COPIED.flag")
        create_flag_file(destination_path, "COPIED.flag")
        print_success("Transferring the data completed. PLEASE WRITE LOG & PROCEED TO VALIDATION STEP")
    
    def check_already_copied_warning(self, source_path: str) -> None:
        """
        Check if source has already been copied and warn user.
        
        Args:
            source_path: Source directory path to check
            
        Raises:
            SystemExit: If user chooses not to proceed with re-copying
        """
        if check_flag_file_exists(source_path, "COPIED.flag"):
            print(f"{Colors.WARNING}{'#' * 95}{Colors.ENDC}")
            print(f"{Colors.WARNING}[WARNING] You're trying to copy the source folder which may " +
                  f"already be copied, PLEASE CHECK BEFORE COPY!!!{Colors.ENDC}")
            print(f"{Colors.WARNING}{'#' * 95}{Colors.ENDC}")
            
            confirmed = ask_urgent_confirmation()
            if not confirmed:
                sys.exit()
    
    def transfer_data(self, run_number: str, destination_dir: str = None, 
                     check_copy_flag: bool = True) -> None:
        """
        Main method to transfer data from source to destination.
        
        Args:
            run_number: Run number identifier
            destination_dir: Base destination directory (optional, uses default if not provided)
            check_copy_flag: Whether to check for existing copy flags
            
        This method orchestrates the complete transfer process:
        1. Validates paths and arguments
        2. Checks storage compatibility
        3. Warns about existing copies if applicable
        4. Performs the transfer
        5. Creates completion flags
        """
        # Use default destination if not provided
        if destination_dir is None:
            destination_dir = self.get_default_destination()
        
        # Construct source path
        source_dir = self.source_prefix + run_number
        source_dir = ensure_trailing_slash(source_dir)
        destination_dir = ensure_trailing_slash(destination_dir)
        
        # Validate paths exist
        validate_path_exists(source_dir, "Source folder")
        validate_path_exists(destination_dir, "Destination folder")
        
        # Check if already copied (if enabled)
        if check_copy_flag:
            self.check_already_copied_warning(source_dir)
        
        print_info(f"Transferring source folder: {Colors.BOLD}{Colors.OKCYAN}{source_dir}{Colors.ENDC} " +
                  f"to destination dir: {Colors.BOLD}{Colors.OKCYAN}{destination_dir}{Colors.ENDC}")
        print_info("Checking folder size...")
        
        # Validate transfer compatibility
        status = self.validate_transfer_compatibility(source_dir, destination_dir)
        
        if status:
            # Generate full destination path
            destination_path = self.generate_destination_path(source_dir, destination_dir)
            
            # Perform the transfer
            self.perform_transfer(source_dir, destination_path, run_number)
            
            # Create completion flags
            self.create_completion_flags(source_dir, destination_path)


class SSDToHDDTransfer(DAQTransfer):
    """Transfer handler for SSD to HDD transfers (primary copies).

    Source:      /Volumes/SSD_8TB/Run_<N>
    Destination: /Volumes/HDD_24TB_6/Run_<N>
    """

    DEFAULT_DESTINATION = "/Volumes/HDD_24TB_6/"

    def __init__(self):
        super().__init__(
            source_prefix="/Volumes/SSD_8TB/Run_",
            log_dir="./Log/Copy_Log/"
        )
    
    def get_default_destination(self) -> str:
        """Return the default destination for SSD to HDD transfers."""
        return self.DEFAULT_DESTINATION


class HDDToHDDTransfer(DAQTransfer):
    """Transfer handler for HDD to HDD transfers (secondary backup copies).

    Source:      /Volumes/HDD_24TB_6/Run_<N>
    Destination: /Volumes/HDD_16TB_4/Run_<N>
    """

    DEFAULT_SOURCE = "/Volumes/HDD_24TB_6/"
    DEFAULT_DESTINATION = "/Volumes/HDD_16TB_4/"

    def __init__(self):
        super().__init__(
            source_prefix="/Volumes/HDD_24TB_6/Run_",
            log_dir="./Log_HDD/Copy_Log/"
        )
    
    def get_default_destination(self) -> str:
        """Return the default destination for HDD to HDD transfers."""
        return self.DEFAULT_DESTINATION
    
    def check_already_copied_warning(self, source_path: str) -> None:
        """
        Override to skip copy flag check for HDD-to-HDD transfers.
        HDD-to-HDD transfers are backup copies and don't need this check.
        """
        pass  # Intentionally do nothing for HDD transfers
