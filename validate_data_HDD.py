"""
DAQ Data Validation Script (HDD to HDD)

This script validates the integrity of experimental data that has been copied
from one external HDD to another (backup copy). This validation ensures the 
backup copy process completed successfully.

Usage:
    python3 validate_data_HDD.py <run_number>
    
Example:
    python3 validate_data_HDD.py 999

The script performs comprehensive validation:
- Verifies that data was previously copied (COPIED.flag exists)
- Compares file lists and sizes between source HDD and destination HDD
- Validates data integrity using SHA256 checksums
- Creates validation flags upon successful completion

Source data location: /Volumes/HDD_24TB_6/Run_<run_number>/
Destination: /Volumes/HDD_16TB_4/Run_<run_number>/ (hardcoded)

Prerequisites: Data must have been copied and COPIED.flag must exist.
"""

import sys
from daq_validation import HDDValidator
from daq_utils import validate_args_count

def main():
    """
    Main function for HDD to HDD data validation.
    
    Validates command line arguments and performs the validation using the
    HDDValidator class which handles all integrity checks and validation logic.
    
    Arguments:
        run_number: Required - The run number to validate
    """
    # Validate command line arguments (1 argument plus script name)
    validate_args_count(
        sys.argv,
        2,
        "./Valid_Data_HDD.sh",
        "<run_num>"
    )
    
    # Extract arguments
    run_number = sys.argv[1]
    
    # Create validator and perform validation
    validator = HDDValidator()
    validator.validate_data(run_number)


if __name__ == "__main__":
    main()
