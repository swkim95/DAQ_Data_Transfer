"""
DAQ Data Transfer Utilities

This module provides shared utilities for the DAQ data transfer system.
It contains common functions for:
- Console output formatting and colors
- Storage usage monitoring and validation
- Directory operations and safety checks
- User confirmation prompts
- File and path operations

All functions maintain strict safety checks to prevent data loss.
"""

import os
import sys
import shutil
import subprocess
import shlex
from typing import Tuple, List, Optional


class Colors:
    """ANSI color codes for console output formatting."""
    HEADER = '\033[95m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    ERRORBLOCK = '\033[41m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    INFO = '\033[94m'
    INFOBLOCK = '\033[44m'
    CMD = '\033[35m'


def get_directory_size(dir_path: str) -> int:
    """
    Calculate the total size of a directory in bytes.
    
    Args:
        dir_path: Path to the directory
        
    Returns:
        Total size in bytes
        
    Raises:
        OSError: If directory cannot be accessed
    """
    total = 0
    with os.scandir(dir_path) as dir_iterator:
        for entry in dir_iterator:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_directory_size(entry.path)
    return total


def display_storage_usage_bar(total: int, used: int, free: int) -> None:
    """
    Display a visual storage usage bar with detailed information.
    
    Args:
        total: Total storage space in bytes
        used: Used storage space in bytes  
        free: Free storage space in bytes
    """
    total_GB = round(total / 1024 / 1024 / 1024, 3)
    used_GB = round(used / 1024 / 1024 / 1024, 3)
    free_GB = round(free / 1024 / 1024 / 1024, 3)
    
    progress_bar_length = 50
    num_of_sharp = round(progress_bar_length * (used / total))
    num_of_bar = (progress_bar_length - num_of_sharp)
    used_percent = round((100 * (used / total)), 3)
    
    # Color coding based on usage percentage
    bar_color = Colors.OKGREEN
    if used_percent >= 50:
        bar_color = Colors.WARNING
    if used_percent >= 70:
        bar_color = Colors.ERROR
        
    print(f"{Colors.INFO}[INFO]{Colors.ENDC}{bar_color} Storage usage : [" + 
          "#" * num_of_sharp + "-" * num_of_bar + f"]{Colors.ENDC}", end=' ')
    print(f"{bar_color}{Colors.BOLD}{used_percent}%{Colors.ENDC}")
    print(f"{Colors.INFO}[INFO]{Colors.ENDC}{bar_color}{Colors.BOLD} Total : {total_GB} GB / " +
          f"Used : {used_GB} GB / Free : {Colors.UNDERLINE}{free_GB} GB{Colors.ENDC}")


def check_storage_usage(storage_path: str) -> Tuple[int, int, int]:
    """
    Check storage usage and display warnings/errors based on usage thresholds.
    
    Args:
        storage_path: Path to check storage usage for
        
    Returns:
        Tuple of (total, used, free) storage in bytes
        
    Raises:
        SystemExit: If storage usage is too high and user doesn't confirm urgent need
    """
    total, used, free = shutil.disk_usage(storage_path)
    display_storage_usage_bar(total, used, free)
    
    usage_fraction = used / total
    
    if usage_fraction >= 0.8:
        print(f"{Colors.ERRORBLOCK}{'#' * 95}{Colors.ENDC}")
        print(f"{Colors.ERRORBLOCK}[ERROR] Storage used more than {Colors.BOLD}" +
              f"{round(100 * usage_fraction, 2)}%{Colors.ENDC}{Colors.ERRORBLOCK} of the total space. " +
              f"If not urgent, can't copy the data {Colors.ENDC}")
        print(f"{Colors.ERRORBLOCK}{'#' * 95}{Colors.ENDC}")
        urgent = ask_urgent_confirmation()
        if not urgent:
            sys.exit()
    elif usage_fraction >= 0.7:
        print(f"{Colors.WARNING}{'#' * 94}{Colors.ENDC}")
        print(f"{Colors.WARNING}[WARNING] Storage used more than {Colors.BOLD}" +
              f"{round(100 * usage_fraction, 2)}%{Colors.ENDC}{Colors.WARNING} of the total space. " +
              f"If not urgent, please change HDD {Colors.ENDC}")
        print(f"{Colors.WARNING}{'#' * 94}{Colors.ENDC}")
    
    return total, used, free


def ask_urgent_confirmation() -> bool:
    """
    Ask user for confirmation when attempting potentially risky actions.
    
    Returns:
        True if user confirms with 'yes', False if user replies 'n'
        
    Raises:
        SystemExit: If user cancels the operation
    """
    answer = input(f"{Colors.ERRORBLOCK}{Colors.BOLD}[CONFIRMATION]{Colors.ENDC} " +
                  f"Trying to take action which is {Colors.ERROR}{Colors.BOLD}NOT RECOMMENDED{Colors.ENDC}. " +
                  f"Are you sure? [yes/n] ")
    
    while answer not in ('yes', 'n'):
        print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} Only available options are " +
              f"`{Colors.OKGREEN}{Colors.BOLD}yes{Colors.ENDC}` or " +
              f"`{Colors.OKGREEN}{Colors.BOLD}n{Colors.ENDC}`, please check your reply")
        answer = input(f"{Colors.ERRORBLOCK}{Colors.BOLD}[CONFIRMATION]{Colors.ENDC} " +
                      f"Trying to take action which is {Colors.ERROR}{Colors.BOLD}NOT RECOMMENDED{Colors.ENDC}. " +
                      f"Are you sure? [yes/n] ")
    
    return answer == 'yes'


def ask_command_execution(cmd_line: str) -> bool:
    """
    Ask user for confirmation before executing a command.
    Currently returns True automatically for non-interactive execution.
    
    Args:
        cmd_line: Command line to be executed
        
    Returns:
        Always True (for automatic execution)
        
    Note:
        The interactive confirmation code is commented out but preserved
        for potential future use.
    """
    print(f"{Colors.INFO}[INFO]{Colors.ENDC} Will you execute command " +
          f"`{Colors.BOLD}{Colors.CMD}{cmd_line}{Colors.ENDC}`? [y/n] ")
    return True
    
    # Interactive version (commented out):
    # execute = input(f"{Colors.INFO}[INFO]{Colors.ENDC} Will you execute command " +
    #                f"`{Colors.BOLD}{Colors.CMD}{cmd_line}{Colors.ENDC}`? [y/n] ")
    # while execute not in ('y', 'n'):
    #     print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} Only available options are " +
    #           f"`{Colors.OKGREEN}{Colors.BOLD}y{Colors.ENDC}` or " +
    #           f"`{Colors.OKGREEN}{Colors.BOLD}n{Colors.ENDC}`, please check your reply")
    #     execute = input(f"{Colors.INFO}[INFO]{Colors.ENDC} Will you execute command " +
    #                    f"`{Colors.BOLD}{Colors.CMD}{cmd_line}{Colors.ENDC}`? [y/n] ")
    # 
    # if execute == 'y':
    #     return True
    # else:
    #     print(f"{Colors.INFO}[INFO]{Colors.ENDC} Execution of command " +
    #           f"`{Colors.CMD}{Colors.BOLD}{cmd_line}{Colors.ENDC}` canceled, exiting...")
    #     sys.exit()


def validate_path_exists(path: str, description: str) -> None:
    """
    Validate that a path exists, exit with error if not.
    
    Args:
        path: Path to validate
        description: Description for error messages (e.g., "Source folder", "Destination folder")
        
    Raises:
        SystemExit: If path does not exist
    """
    if not os.path.exists(path):
        print(f"{Colors.ERROR}[ERROR]{Colors.ENDC} {description} " +
              f"{Colors.BOLD}\"{path}\"{Colors.ENDC} {Colors.ERROR}does not exist{Colors.ENDC}, please check")
        sys.exit()


def ensure_trailing_slash(path: str) -> str:
    """
    Ensure a path ends with a trailing slash.
    
    Args:
        path: Input path
        
    Returns:
        Path with trailing slash
    """
    return path if path.endswith("/") else path + "/"


def check_flag_file_exists(directory: str, flag_name: str) -> bool:
    """
    Check if a flag file exists in a directory.
    
    Args:
        directory: Directory to check
        flag_name: Name of the flag file (e.g., "COPIED.flag", "VALIDATED.flag")
        
    Returns:
        True if flag file exists, False otherwise
    """
    return os.path.exists(os.path.join(directory, flag_name))


def create_flag_file(directory: str, flag_name: str) -> None:
    """
    Create a flag file in a directory.
    
    Args:
        directory: Directory where to create the flag
        flag_name: Name of the flag file to create
    """
    os.system(f"touch {os.path.join(directory, flag_name)}")


def execute_rsync_command(cmd_line: str) -> None:
    """
    Execute an rsync command with real-time output streaming.
    
    Args:
        cmd_line: The rsync command to execute
        
    Note:
        Uses subprocess.Popen to stream output in real-time for long-running transfers
    """
    stream = subprocess.Popen(shlex.split(cmd_line), stdout=subprocess.PIPE, encoding='utf-8')
    while True:
        out = stream.stdout.readline()
        if stream.poll() is not None:
            break
        if out != "":
            sys.stdout.write(out)
            sys.stdout.flush()


def print_info(message: str) -> None:
    """Print an informational message with proper formatting."""
    print(f"{Colors.INFO}[INFO]{Colors.ENDC} {message}")


def print_success(message: str) -> None:
    """Print a success message with proper formatting."""
    print(f"{Colors.INFO}[INFO]{Colors.ENDC} {Colors.BOLD}{Colors.OKGREEN}{message}{Colors.ENDC}")


def print_warning(message: str) -> None:
    """Print a warning message with proper formatting."""
    print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} {message}")


def print_error(message: str) -> None:
    """Print an error message with proper formatting."""
    print(f"{Colors.ERROR}[ERROR]{Colors.ENDC} {message}")


def print_error_block(message: str) -> None:
    """Print an error message with block background formatting."""
    print(f"{Colors.ERRORBLOCK}[ERROR]{Colors.ENDC} {message}")


def get_data_files(directory: str) -> List[str]:
    """
    Get a sorted list of data files (.dat files only) from a directory.

    This function specifically includes only real .dat data files and excludes:
    - flag files, logs, images, and other non-data files
    - macOS AppleDouble sidecar files (names starting with "._"). These are
      generated automatically when macOS writes extended-attribute-bearing
      files to a non-APFS/HFS+ destination (e.g. an exFAT/NTFS HDD), and they
      also happen to end in ".dat" (e.g. "._Run_<N>_Wave_MID_1_FILE_0.dat").
      Counting them as real data files makes file lists and sizes appear to
      mismatch between SSD (APFS, no sidecars) and HDD (sidecars present).

    Args:
        directory: Directory to scan for data files

    Returns:
        Sorted list of real .dat file paths only
    """
    file_list = []
    for root_dir, _, files in os.walk(directory):
        for file_name in files:
            if not file_name.endswith('.dat'):
                continue
            # Skip macOS AppleDouble sidecar files (e.g. "._foo.dat")
            if file_name.startswith('._'):
                continue
            file_list.append(os.path.join(root_dir, file_name))

    file_list.sort()
    return file_list


def format_size_gb(size_bytes: int) -> str:
    """
    Format a size in bytes as GB with 3 decimal places.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string like "123.456 GB"
    """
    return f"{round(size_bytes / 1024 / 1024 / 1024, 3)} GB"


def extract_run_number_from_path(path: str) -> str:
    """
    Extract run number from a path containing Run_XXX format.
    
    Args:
        path: Path containing run number
        
    Returns:
        Run number as string
    """
    base_dir = path.rstrip('/').split('/')[-1]
    return base_dir.split('_')[-1]


def compare_run_numbers(ssd_dir: str, hdd_dir: str) -> None:
    """
    Compare run numbers from SSD and HDD directories and exit if they don't match.
    
    Args:
        ssd_dir: SSD directory path
        hdd_dir: HDD directory path
        
    Raises:
        SystemExit: If run numbers don't match
    """
    ssd_run_num = extract_run_number_from_path(ssd_dir)
    hdd_run_num = extract_run_number_from_path(hdd_dir)
    
    if ssd_run_num != hdd_run_num:
        print(f"{Colors.ERRORBLOCK}{'#' * 95}{Colors.ENDC}")
        print(f"{Colors.ERRORBLOCK}[ERROR] The {Colors.BOLD}{Colors.UNDERLINE}RUN NUMBER{Colors.ENDC}" +
              f"{Colors.ERRORBLOCK} of both DAQ DATA and HDD DATA {Colors.BOLD}{Colors.UNDERLINE}" +
              f"MUST BE MATCHED{Colors.ENDC}{Colors.ERRORBLOCK}. PLEASE CHECK ARGUMENTS!!!{Colors.ENDC}")
        print(f"{Colors.ERRORBLOCK}{'#' * 95}{Colors.ENDC}")
        print(f"{Colors.ERROR}[ERROR]{Colors.ENDC} Your DAQ PC data run number : " +
              f"{Colors.ERROR}{Colors.BOLD}{Colors.UNDERLINE}{ssd_run_num}{Colors.ENDC}   " +
              f"Your HDD data run number : {Colors.ERROR}{Colors.BOLD}{Colors.UNDERLINE}{hdd_run_num}{Colors.ENDC}")
        sys.exit()


def validate_args_count(args: List[str], expected_count: int, script_name: str, usage_example: str) -> None:
    """
    Validate command line argument count and print usage if incorrect.
    
    Args:
        args: Command line arguments (sys.argv)
        expected_count: Expected number of arguments including script name
        script_name: Name of the script for usage message
        usage_example: Example usage string
        
    Raises:
        SystemExit: If argument count is incorrect
    """
    if len(args) != expected_count:
        print(f"{Colors.ERROR}[ERROR] Invalid command line argument. " +
              f"Require {expected_count - 1} arguments{Colors.ENDC}")
        print(f"{Colors.INFO}[Usage]{Colors.ENDC} {script_name} {usage_example}")
        sys.exit()


def validate_args_count_flexible(args: List[str], min_count: int, max_count: int, script_name: str, usage_example: str) -> None:
    """
    Validate command line argument count with flexible range and print usage if incorrect.
    
    Args:
        args: Command line arguments (sys.argv)
        min_count: Minimum number of arguments including script name
        max_count: Maximum number of arguments including script name
        script_name: Name of the script for usage message
        usage_example: Example usage string
        
    Raises:
        SystemExit: If argument count is not within range
    """
    if not (min_count <= len(args) <= max_count):
        if min_count == max_count:
            required_text = f"exactly {min_count - 1} arguments"
        else:
            required_text = f"{min_count - 1}-{max_count - 1} arguments"
        
        print(f"{Colors.ERROR}[ERROR] Invalid command line argument. " +
              f"Require {required_text}{Colors.ENDC}")
        print(f"{Colors.INFO}[Usage]{Colors.ENDC} {script_name} {usage_example}")
        sys.exit()