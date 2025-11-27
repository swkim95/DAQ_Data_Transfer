"""
HDD to HDD Transfer Script

This script handles the transfer of experimental data from one external HDD to another,
creating a backup copy. This is the second step in the dual-copy strategy for data safety:
1. Copy (SSD → HDD) - Primary copy
2. Copy (HDD → HDD) - This script (backup copy)
3. Validate both copies
4. Remove from SSD

Usage:
    python3 transfer_from_HDD_to_HDD.py <run_number> [destination_path]
    
Examples:
    python3 transfer_from_HDD_to_HDD.py 999
    python3 transfer_from_HDD_to_HDD.py 999 /Volumes/HDD_16TB_4/

The script performs the same safety checks as SSD→HDD transfer:
- Validates source and destination paths
- Checks storage space and usage thresholds  
- Creates transfer logs and completion flags
- Provides real-time progress monitoring

Source data location: /Volumes/HDD_16TB_2/Run_<run_number>/
Default destination: /Volumes/HDD_16TB_4/Run_<run_number>/
Custom destination: <destination_path>/Run_<run_number>/ (if provided)

Note: This script skips the "already copied" warning since HDD→HDD transfers
are intended backup copies and may be run multiple times.
"""

import sys
from daq_transfer import HDDToHDDTransfer
from daq_utils import validate_args_count_flexible

def main():
    """
    Main function for HDD to HDD data transfer.
    
    Validates command line arguments and performs the transfer using the
    HDDToHDDTransfer class which handles all safety checks and transfer logic.
    
    Arguments:
        run_number: Required - The run number to transfer
        destination_path: Optional - Custom destination path (defaults to /Volumes/HDD_16TB_4/)
    """
    # Validate command line arguments (1-2 arguments plus script name)
    validate_args_count_flexible(
        sys.argv, 
        2,  # minimum: script + run_number
        3,  # maximum: script + run_number + destination
        "./Transfer_Data_HDD.sh",
        "<run_num> [destination_path]"
    )
    
    # Extract arguments
    run_number = sys.argv[1]
    destination_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Create transfer handler and perform transfer
    # Note: HDD-to-HDD transfers skip the copy flag check
    transfer_handler = HDDToHDDTransfer()
    transfer_handler.transfer_data(run_number, destination_dir, check_copy_flag=False)


if __name__ == "__main__":
    main()