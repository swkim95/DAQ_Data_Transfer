"""
DAQ Data Validation Script (SSD to HDD)

This script validates the integrity of experimental data that has been copied
from the MacStudio internal SSD to external HDDs. This is the second step in 
the 3-stage data management process:
1. Copy (using transfer_from_DAQ_PC_to_HDD.py)
2. Validate (SSD ↔ HDD) - This script  
3. Remove (using remove_data_from_DAQ_PC.py)

Usage:
    python3 validate_data.py <run_number>
    
Example:
    python3 validate_data.py 999

The script performs comprehensive validation:
- Verifies that data was previously copied (COPIED.flag exists)
- Compares file lists and sizes between SSD and HDD
- Validates data integrity using SHA256 checksums
- Creates validation flags upon successful completion

Source data location: /Volumes/SSD_8TB/Run_<run_number>/
Destination: /Volumes/HDD_16TB_2/Run_<run_number>/ (hardcoded)

Prerequisites: Data must have been copied and COPIED.flag must exist.
"""

import sys
from daq_validation import SSDValidator
from daq_utils import validate_args_count

def main():
    """
    Main function for SSD to HDD data validation.
    
    Validates command line arguments and performs the validation using the
    SSDValidator class which handles all integrity checks and validation logic.
    
    Arguments:
        run_number: Required - The run number to validate
    """
    # Validate command line arguments (1 argument plus script name)
    validate_args_count(
        sys.argv,
        2,
        "./Valid_Data.sh",
        "<run_num>"
    )
    
    # Extract arguments
    run_number = sys.argv[1]
    
    # Create validator and perform validation
    validator = SSDValidator()
    validator.validate_data(run_number)


if __name__ == "__main__":
    main()
