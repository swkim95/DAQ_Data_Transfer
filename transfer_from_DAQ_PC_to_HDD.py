"""
DAQ PC to HDD Transfer Script

This script handles the transfer of experimental data from the MacStudio internal SSD
to external HDDs. This is the first step in the 3-stage data management process:
1. Copy (SSD → HDD) - This script
2. Validate (using validate_data.py)
3. Remove (using remove_data_from_DAQ_PC.py)

Usage:
    python3 transfer_from_DAQ_PC_to_HDD.py <run_number> [destination_path]

Examples:
    python3 transfer_from_DAQ_PC_to_HDD.py 999
    python3 transfer_from_DAQ_PC_to_HDD.py 999 /Volumes/HDD_24TB_6/

The script performs comprehensive safety checks:
- Validates source and destination paths
- Checks storage space and usage thresholds
- Warns about potential overwrites
- Creates transfer logs and completion flags
- Provides real-time progress monitoring

Source data location: /Volumes/SSD_8TB/Run_<run_number>/
Default destination: /Volumes/HDD_24TB_6/Run_<run_number>/
Custom destination: <destination_path>/Run_<run_number>/ (if provided)
"""

import sys
from daq_transfer import SSDToHDDTransfer
from daq_utils import validate_args_count_flexible, Colors

def main():
    """
    Main function for SSD to HDD data transfer.
    
    Validates command line arguments and performs the transfer using the
    SSDToHDDTransfer class which handles all safety checks and transfer logic.
    
    Arguments:
        run_number: Required - The run number to transfer
        destination_path: Optional - Custom destination path (defaults to /Volumes/HDD_24TB_6/)
    """
    # Validate command line arguments (1-2 arguments plus script name)
    validate_args_count_flexible(
        sys.argv, 
        2,  # minimum: script + run_number
        3,  # maximum: script + run_number + destination
        "./Transfer_Data.sh",
        "<run_num> [destination_path]"
    )
    
    # Extract arguments
    run_number = sys.argv[1]
    destination_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Create transfer handler and perform transfer
    transfer_handler = SSDToHDDTransfer()
    transfer_handler.transfer_data(run_number, destination_dir)


if __name__ == "__main__":
    main()