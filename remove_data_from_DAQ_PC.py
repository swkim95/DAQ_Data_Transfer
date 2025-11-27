"""
DAQ Data Removal Script

This script safely removes experimental data from the MacStudio internal SSD
after it has been copied and validated. This is the final step in the 3-stage 
data management process:
1. Copy (using transfer_from_DAQ_PC_to_HDD.py)
2. Validate (using validate_data.py)
3. Remove (SSD cleanup) - This script

Usage:
    python3 remove_data_from_DAQ_PC.py <run_number>
    
Example:
    python3 remove_data_from_DAQ_PC.py 999

The script performs comprehensive safety checks before deletion:
- Verifies that data was previously validated (VALIDATED.flag exists)
- Compares run numbers between SSD and HDD data
- Verifies file lists and sizes match exactly
- Confirms data exists in HDD before deleting from SSD
- Displays final storage usage after deletion

Source data location: /Volumes/SSD_8TB/Run_<run_number>/
HDD verification path: /Volumes/HDD_16TB_2/Run_<run_number>/ (hardcoded)

Prerequisites: 
- Data must have been copied (COPIED.flag exists)
- Data must have been validated (VALIDATED.flag exists)
- HDD copy must exist and match exactly

CRITICAL: This script permanently deletes data. All safety checks must pass.
"""

import os
import sys
import shutil
from daq_utils import (
    Colors, get_directory_size, compare_run_numbers, validate_path_exists,
    ensure_trailing_slash, check_flag_file_exists, display_storage_usage_bar,
    print_info, print_warning, print_error_block, validate_args_count
)

def check_if_exists_in_HDD(ssd_dir: str, hdd_dir: str) -> None:
    """
    Verify that SSD data exists in HDD with identical content before removal.
    
    Args:
        ssd_dir: SSD directory path
        hdd_dir: HDD directory path
        
    Raises:
        SystemExit: If data doesn't match or verification fails
    """
    # Check run numbers match
    compare_run_numbers(ssd_dir, hdd_dir)
    
    print_info("Checking if source directory properly copied to destination before removing...")
    print_info(f"Checking source directory: {Colors.OKCYAN}{Colors.BOLD}{ssd_dir}{Colors.ENDC}")
    print_info(f"Checking destination directory: {Colors.OKCYAN}{Colors.BOLD}{hdd_dir}{Colors.ENDC}")
    
    # Get data file lists from both directories (excluding flag files)
    from daq_utils import get_data_files
    ssd_file_list = get_data_files(ssd_dir)
    hdd_file_list = get_data_files(hdd_dir)
    
    # Extract just filenames for comparison
    ssd_filenames = [os.path.basename(f) for f in ssd_file_list]
    hdd_filenames = [os.path.basename(f) for f in hdd_file_list]
    ssd_filenames.sort()
    hdd_filenames.sort()
    
    # Check total data file sizes (excluding flag files)
    ssd_data_size = sum(os.path.getsize(f) for f in ssd_file_list)
    hdd_data_size = sum(os.path.getsize(f) for f in hdd_file_list)
    
    if ssd_data_size != hdd_data_size:
        print(f"{Colors.ERROR}[ERROR]{Colors.ENDC} Data file size in source and destination mismatch. Please check!")
        print(f"Data file size in source: {Colors.ERROR}{Colors.BOLD}{Colors.UNDERLINE}{ssd_data_size}{Colors.ENDC} " +
              f"(Bytes) in destination: {Colors.ERROR}{Colors.BOLD}{Colors.UNDERLINE}{hdd_data_size}{Colors.ENDC} (Bytes)")
        sys.exit()
    
    # Compare data file lists (excluding flag files)
    if len(ssd_filenames) != len(hdd_filenames):
        print(f"{Colors.ERROR}[ERROR]{Colors.ENDC} Data file count mismatch between source and destination. Please check!")
        print(f"Source data file count: {Colors.ERROR}{Colors.BOLD}{len(ssd_filenames)}{Colors.ENDC}")
        print(f"Destination data file count: {Colors.ERROR}{Colors.BOLD}{len(hdd_filenames)}{Colors.ENDC}")
        sys.exit()
    
    # Check each data file in the lists
    for idx, (ssd_filename, hdd_filename) in enumerate(zip(ssd_filenames, hdd_filenames)):
        if ssd_filename != hdd_filename:
            print(f"{Colors.ERROR}[ERROR]{Colors.ENDC} Mismatch between source data files & destination data files. Please check!")
            print(f"Source data file at index {Colors.ERROR}{Colors.BOLD}{idx}{Colors.ENDC}: " +
                  f"{Colors.ERROR}{Colors.BOLD}{ssd_filename}{Colors.ENDC}")
            print(f"Destination data file at index {Colors.ERROR}{Colors.BOLD}{idx}{Colors.ENDC}: " +
                  f"{Colors.ERROR}{Colors.BOLD}{hdd_filename}{Colors.ENDC}")
            sys.exit()
    
    print_info(f"Data file list & size check between source folder and destination folder " +
              f"{Colors.OKGREEN}{Colors.BOLD}successful!{Colors.ENDC} Proceeding...")


def remove_folder(ssd_dir: str) -> None:
    """
    Safely remove the SSD directory after all checks pass.
    
    Args:
        ssd_dir: SSD directory path to remove
        
    Note:
        This function automatically proceeds with deletion after all safety
        checks have passed. Interactive confirmation is disabled for automated operation.
    """
    print(f"{Colors.WARNING}[DELETING]{Colors.ENDC} Removing folder: " +
          f"{Colors.OKCYAN}{Colors.BOLD}{Colors.UNDERLINE}{ssd_dir}{Colors.ENDC}")
    
    print_info(f"Deleting directory {Colors.OKCYAN}{Colors.BOLD}{Colors.UNDERLINE}{ssd_dir}{Colors.ENDC}")
    
    try:
        shutil.rmtree(ssd_dir)
        print_info(f"Directory {Colors.OKCYAN}{Colors.BOLD}{Colors.UNDERLINE}{ssd_dir}{Colors.ENDC} " +
                  f"deleted successfully.")
    except OSError as e:
        print(f"{Colors.ERROR}[ERROR]{Colors.ENDC} Failed to delete directory: {e}")
        sys.exit()


def validate_prerequisites(ssd_dir: str) -> None:
    """
    Validate that all prerequisites for safe removal are met.
    
    Args:
        ssd_dir: SSD directory path to validate
        
    Raises:
        SystemExit: If VALIDATED.flag doesn't exist
    """
    if not check_flag_file_exists(ssd_dir, "VALIDATED.flag"):
        print_error_block("DAQ data must be VALIDATED before deleting. PLEASE CHECK ARGUMENTS!!!")
        sys.exit()


def display_final_storage_usage() -> None:
    """Display SSD storage usage after data removal."""
    print_info("Checking SSD storage usage after removal...")
    total, used, free = shutil.disk_usage("/Volumes/SSD_8TB/")
    display_storage_usage_bar(total, used, free)


def main():
    """
    Main function for safe SSD data removal.
    
    Validates command line arguments and performs the removal using comprehensive
    safety checks to ensure data integrity and prevent accidental data loss.
    
    Arguments:
        run_number: Required - The run number to remove from SSD
    """
    # Validate command line arguments (1 argument plus script name)
    validate_args_count(
        sys.argv,
        2,
        "./Remove_Data.sh",
        "<run_num>"
    )
    
    # Extract arguments
    run_number = sys.argv[1]
    
    # Construct paths with hardcoded HDD verification path
    ssd_dir_prefix = "/Volumes/SSD_8TB/Run_"
    hdd_dir_prefix = "/Volumes/HDD_16TB_2/Run_"
    
    ssd_dir = ssd_dir_prefix + run_number
    hdd_dir = hdd_dir_prefix + run_number
    
    ssd_dir = ensure_trailing_slash(ssd_dir)
    hdd_dir = ensure_trailing_slash(hdd_dir)
    
    # Validate paths exist
    validate_path_exists(ssd_dir, "Original SSD data")
    validate_path_exists(hdd_dir, "Copied HDD data")
    
    # Check prerequisites
    validate_prerequisites(ssd_dir)
    
    # Verify data integrity between SSD and HDD
    check_if_exists_in_HDD(ssd_dir, hdd_dir)
    
    # Final warning before deletion
    print(f"{Colors.WARNING}{'#' * 76}{Colors.ENDC}")
    print(f"{Colors.WARNING}[WARNING] You're trying to {Colors.BOLD}{Colors.UNDERLINE}remove the DATA{Colors.ENDC}" +
          f"{Colors.WARNING} from DAQ PC. PLEASE BE CAREFUL!!!{Colors.ENDC}")
    print(f"{Colors.WARNING}{'#' * 76}{Colors.ENDC}")
    
    # Perform the removal
    remove_folder(ssd_dir)
    
    # Display final storage usage
    display_final_storage_usage()


if __name__ == "__main__":
    main()
