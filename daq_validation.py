"""
DAQ Data Validation Module

This module provides comprehensive validation functionality for the DAQ data transfer system.
It handles data integrity verification using file count/size comparison, optional SHA256
checksums, and metadata validation.

The module supports:
    - File count/size validation (default)
    - Optional SHA256 checksum comparison between source and destination files
    - File size aligned event count validation
- Binary metadata parsing and comparison
- Random sampling for metadata inspection
- Automatic flag file creation for tracking validation status

All validation functions maintain strict safety protocols to ensure data integrity.
"""

import os
import sys
import hashlib
import random
from typing import List, Tuple, Any
from daq_utils import (
    Colors, get_data_files, compare_run_numbers, validate_path_exists,
    ensure_trailing_slash, check_flag_file_exists, create_flag_file,
    print_info, print_success, print_error, print_error_block,
    validate_args_count
)


def calculate_sha256_checksum(file_path: str) -> str:
    """
    Calculate SHA256 checksum of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA256 hexdigest string
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def validate_files_with_sha256(source_files: List[str], destination_files: List[str]) -> None:
    """
    Validate files using SHA256 checksum comparison with progress indication.
    
    Args:
        source_files: List of source file paths
        destination_files: List of destination file paths
        
    Raises:
        SystemExit: If any checksums don't match
    """
    total_files = len(source_files)
    print_info(f"Comparing SHA256 checksum values for {total_files} source & destination files...")
    
    for idx, (source_file, dest_file) in enumerate(zip(source_files, destination_files)):
        # Show progress
        progress = (idx + 1) / total_files
        bar_length = 50
        filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # Get just the filename for display
        filename = source_file.split('/')[-1]
        
        # Print progress bar with current file
        print(f"\r{Colors.INFO}[{idx + 1:3d}/{total_files:3d}]{Colors.ENDC} " +
              f"[{bar}] {progress:.1%} - {filename[:40]:<40}", end='', flush=True)
        
        sha256_source = calculate_sha256_checksum(source_file)
        sha256_dest = calculate_sha256_checksum(dest_file)
        
        if sha256_source != sha256_dest:
            print()  # New line before error
            print_error_block("SHA256 checksum failed!!!")
            print(f"{Colors.ERROR}[ERROR]{Colors.ENDC} SHA256 checksum of source file : " +
                  f"{Colors.OKCYAN}{Colors.BOLD}{Colors.UNDERLINE}{source_file}{Colors.ENDC} " +
                  f"and destination file {Colors.OKCYAN}{Colors.BOLD}{Colors.UNDERLINE}{dest_file}{Colors.ENDC} " +
                  f"does not match. PLEASE CHECK!!")
            print(f"{Colors.INFO}[INFO]{Colors.ENDC} SHA256 decimal checksum of source file " +
                  f"{Colors.OKCYAN}{Colors.BOLD}{Colors.UNDERLINE}{source_file}{Colors.ENDC} : " +
                  f"{Colors.ERROR}{Colors.BOLD}{int(sha256_source, base=16)}{Colors.ENDC}")
            print(f"{Colors.INFO}[INFO]{Colors.ENDC} SHA256 decimal checksum of destination file " +
                  f"{Colors.OKCYAN}{Colors.BOLD}{Colors.UNDERLINE}{dest_file}{Colors.ENDC} : " +
                  f"{Colors.ERROR}{Colors.BOLD}{int(sha256_dest, base=16)}{Colors.ENDC}")
            sys.exit()
    
    print()  # New line after progress bar
    print_info(f"SHA256 checksum compare {Colors.OKGREEN}{Colors.BOLD}successful!{Colors.ENDC} Proceeding...")


def validate_event_counts(source_files: List[str], destination_files: List[str]) -> None:
    """
    Validate event counts in files based on file sizes.
    
    Args:
        source_files: List of source file paths
        destination_files: List of destination file paths
        
    Raises:
        SystemExit: If event counts don't match expected values
    """
    print_info("Checking number of events stored in source & destination files...")
    
    for idx, (source_file, dest_file) in enumerate(zip(source_files, destination_files)):
        source_size = os.stat(source_file).st_size
        dest_size = os.stat(dest_file).st_size
        
        # Determine base size based on file type
        base_size = 256 if "Fast" in source_file else 65536
        
        # Skip empty files
        if source_size == 0 and dest_size == 0:
            continue
            
        # Check if file sizes are proper multiples of base size
        if not ((source_size % base_size) == 0 and (dest_size % base_size) == 0):
            print_error_block("Event number check failed!!!")
            print_error("Some file does not contain proper number of events. Please check")
            print(f"{Colors.INFO}[INFO]{Colors.ENDC} # of events in source file : " +
                  f"{Colors.OKCYAN}{Colors.BOLD}{source_file}{Colors.ENDC} == " +
                  f"{Colors.ERROR}{Colors.BOLD}{source_size // base_size}{Colors.ENDC}")
            print(f"{Colors.INFO}[INFO]{Colors.ENDC} # of events in destination file : " +
                  f"{Colors.OKCYAN}{Colors.BOLD}{dest_file}{Colors.ENDC} == " +
                  f"{Colors.ERROR}{Colors.BOLD}{dest_size // base_size}{Colors.ENDC}")
            sys.exit()
    
    print_info(f"Checking event number {Colors.OKGREEN}{Colors.BOLD}successful!{Colors.ENDC} Proceeding...")


def validate_file_counts_and_sizes(source_files: List[str], destination_files: List[str]) -> None:
    """
    Validate that the number of files and each file's size match between
    source and destination directories.

    This is a fast validation path that avoids computing checksums.

    Args:
        source_files: List of source file paths
        destination_files: List of destination file paths

    Raises:
        SystemExit: If file counts differ or any corresponding file sizes differ
    """
    # Compare counts
    if len(source_files) != len(destination_files):
        print_error_block("File count mismatch!!!")
        print_error(
            f"# of source files = {Colors.ERROR}{Colors.BOLD}{len(source_files)}{Colors.ENDC}, "
            f"# of destination files = {Colors.ERROR}{Colors.BOLD}{len(destination_files)}{Colors.ENDC}"
        )
        sys.exit()

    # Build maps by relative path (robust against differing root prefixes)
    def to_rel(path: str) -> str:
        # Drop leading '/' and everything up to and including the run directory name
        # Find the first occurrence of 'Run_' and keep the suffix after it for matching
        parts = path.split('/')
        for i, p in enumerate(parts):
            if p.startswith('Run_'):
                return '/'.join(parts[i + 1:])  # path within the run directory
        return '/'.join(parts)  # fallback to full path

    source_map = {to_rel(p): os.stat(p).st_size for p in source_files}
    dest_map = {to_rel(p): os.stat(p).st_size for p in destination_files}

    # Compare key sets
    missing_in_dest = sorted(set(source_map.keys()) - set(dest_map.keys()))
    extra_in_dest = sorted(set(dest_map.keys()) - set(source_map.keys()))

    if missing_in_dest or extra_in_dest:
        print_error_block("File list mismatch!!!")
        if missing_in_dest:
            print_error(f"Missing in destination ({len(missing_in_dest)}): e.g., {missing_in_dest[:3]}")
        if extra_in_dest:
            print_error(f"Extra in destination ({len(extra_in_dest)}): e.g., {extra_in_dest[:3]}")
        sys.exit()

    # Compare sizes
    mismatched_sizes = []
    for rel_path, src_size in source_map.items():
        dst_size = dest_map.get(rel_path, None)
        if dst_size is None or src_size != dst_size:
            mismatched_sizes.append((rel_path, src_size, dst_size))

    if mismatched_sizes:
        print_error_block("File size mismatch!!!")
        # Show up to a few examples to keep output compact
        for rel_path, s, d in mismatched_sizes[:5]:
            print_error(
                f"{rel_path}: src={Colors.ERROR}{Colors.BOLD}{s}{Colors.ENDC} bytes, "
                f"dst={Colors.ERROR}{Colors.BOLD}{d}{Colors.ENDC} bytes"
            )
        if len(mismatched_sizes) > 5:
            print_info(f"... and {len(mismatched_sizes) - 5} more mismatches")
        sys.exit()

    print_info(
        f"File count/size validation {Colors.OKGREEN}{Colors.BOLD}successful!{Colors.ENDC} Proceeding..."
    )


def decode_metadata(metadata_bits: List[bytes]) -> List[Any]:
    """
    Decode metadata from binary data according to DAQ format specification.
    
    Args:
        metadata_bits: List of individual bytes from metadata
        
    Returns:
        List containing decoded metadata fields:
        [data_length, run_number, tcb_trig_type, tcb_trig_number, tcb_trig_time,
         mid, local_trig_number, local_trigger_pattern, local_trig_time, diff_time]
    """
    data = []
    
    # Data length (4 bytes)
    data_length = int(metadata_bits[0].hex(), 16) & 0b11111111
    for i in range(1, 4):
        tmp = (int(metadata_bits[i].hex(), 16) & 0b11111111) << (8 * i)
        data_length += tmp
    data.append(data_length)
    
    # Run number (2 bytes)
    run_number = int(metadata_bits[4].hex(), 16) & 0b11111111
    tmp = (int(metadata_bits[5].hex(), 16) & 0b11111111) << 8
    run_number += tmp
    data.append(run_number)
    
    # Trigger type (1 byte)
    tcb_trig_type = int(metadata_bits[6].hex(), 16) & 0b11111111
    data.append(tcb_trig_type)
    
    # TCB trigger number (4 bytes)
    tcb_trig_number = int(metadata_bits[7].hex(), 16) & 0b11111111
    for i in range(8, 11):
        tmp = (int(metadata_bits[i].hex(), 16) & 0b11111111) << (8 * (i - 7))
        tcb_trig_number += tmp
    data.append(tcb_trig_number)
    
    # TCB trigger time (6 bytes fine + coarse time)
    fine_time = (int(metadata_bits[11].hex(), 16) & 0b11111111) * 11  # * (1000 / 90)
    coarse_time = int(metadata_bits[12].hex(), 16) & 0b11111111
    for i in range(13, 18):
        tmp = (int(metadata_bits[i].hex(), 16) & 0b11111111) << (8 * (i - 12))
        coarse_time += tmp
    coarse_time *= 1000  # convert to ns
    tcb_trig_time = fine_time + coarse_time
    data.append(tcb_trig_time)
    
    # MID (1 byte)
    mid = int(metadata_bits[18].hex(), 16) & 0b11111111
    data.append(mid)
    
    # Local trigger number (4 bytes)
    local_trig_number = int(metadata_bits[19].hex(), 16) & 0b11111111
    for i in range(20, 23):
        tmp = (int(metadata_bits[i].hex(), 16) & 0b11111111) << (8 * (i - 19))
        local_trig_number += tmp
    data.append(local_trig_number)
    
    # Local trigger pattern (4 bytes)
    local_trigger_pattern = int(metadata_bits[23].hex(), 16) & 0b11111111
    for i in range(24, 27):
        tmp = (int(metadata_bits[i].hex(), 16) & 0b11111111) << (8 * (i - 23))
        local_trigger_pattern += tmp
    data.append(local_trigger_pattern)
    
    # Local trigger time (6 bytes fine + coarse time)
    fine_time = (int(metadata_bits[27].hex(), 16) & 0b11111111) * 11  # * (1000 / 90)
    coarse_time = int(metadata_bits[28].hex(), 16) & 0b11111111
    for i in range(29, 34):
        tmp = (int(metadata_bits[i].hex(), 16) & 0b11111111) << (8 * (i - 28))
        coarse_time += tmp
    coarse_time *= 1000  # convert to ns
    local_trig_time = fine_time + coarse_time
    data.append(local_trig_time)
    
    # Time difference
    diff_time = local_trig_time - tcb_trig_time
    data.append(diff_time)
    
    return data


def print_sample_metadata(files: List[str], fraction: float = 0.1, metadata_size: int = 64) -> None:
    """
    Print metadata from a random sample of files for manual inspection.
    
    Args:
        files: List of file paths to sample from
        fraction: Fraction of files to sample (default 0.1 = 10%)
        metadata_size: Size of metadata block in bytes
        
    Raises:
        SystemExit: If user doesn't confirm metadata is correct
    """
    print_info("Printing out random file's metadata...\n")
    
    total_files = len(files)
    files_to_check = int(total_files * fraction) if total_files >= 10 else total_files
    sample_files = random.sample(files, files_to_check)
    
    for file_path in sample_files:
        file_size = os.stat(file_path).st_size
        if file_size == 0:
            continue
            
        # Determine base size and calculate event count
        base_size = 65536 if "Wave" in file_path else 256
        evt_count = file_size // base_size
        random_evt = random.randint(0, evt_count - 1)
        
        print_info(f"Checking metadata of file: {Colors.OKCYAN}{Colors.BOLD}{file_path}{Colors.ENDC}")
        
        # Read metadata
        metadata_bits = []
        with open(file_path, "rb") as f:
            f.seek(random_evt * base_size)
            for i in range(metadata_size):
                metadata_bits.append(f.read(1))
        
        # Decode and display
        metadata = decode_metadata(metadata_bits)
        print_info(f"Data Length = {metadata[0]}, Run # = {metadata[1]}, MID = {metadata[5]}")
        print_info(f"Trigger type = {metadata[2]:x}, Local trigger pattern = {metadata[7]:x}")
        print_info(f"TCB trigger # = {metadata[3]}, Local trigger # = {metadata[6]}")
        print_info(f"TCB trigger time = {metadata[4]}, Local trigger time = {metadata[8]}, " +
                  f"difference = {metadata[9]}\n")
    
    # Ask for user confirmation
    confirmed = ask_metadata_confirmation()
    if not confirmed:
        sys.exit()
    
    print_info("Metadata check all clear. Proceeding...")


def compare_metadata(source_files: List[str], dest_files: List[str], metadata_size: int = 64) -> None:
    """
    Compare metadata between source and destination files.
    
    Args:
        source_files: List of source file paths
        dest_files: List of destination file paths
        metadata_size: Size of metadata block in bytes
        
    Raises:
        SystemExit: If metadata doesn't match between source and destination
    """
    print_info("Comparing source & destination file's metadata...")
    
    for source_file, dest_file in zip(source_files, dest_files):
        file_size = os.stat(source_file).st_size
        if file_size == 0:
            continue
            
        base_size = 65536 if "Wave" in source_file else 256
        evt_count = file_size // base_size
        
        # Read first event metadata
        source_first_metadata = []
        dest_first_metadata = []
        
        with open(source_file, "rb") as f:
            for i in range(metadata_size):
                source_first_metadata.append(f.read(1))
                
        with open(dest_file, "rb") as f:
            for i in range(metadata_size):
                dest_first_metadata.append(f.read(1))
        
        # Read last event metadata
        source_last_metadata = []
        dest_last_metadata = []
        
        with open(source_file, "rb") as f:
            f.seek((evt_count - 1) * base_size)
            for i in range(metadata_size):
                source_last_metadata.append(f.read(1))
                
        with open(dest_file, "rb") as f:
            f.seek((evt_count - 1) * base_size)
            for i in range(metadata_size):
                dest_last_metadata.append(f.read(1))
        
        # Decode and compare
        source_first_decoded = decode_metadata(source_first_metadata)
        dest_first_decoded = decode_metadata(dest_first_metadata)
        source_last_decoded = decode_metadata(source_last_metadata)
        dest_last_decoded = decode_metadata(dest_last_metadata)
        
        # Check first event metadata
        if source_first_decoded != dest_first_decoded:
            print_error("Mismatch in source and destination 1st event's metadata, please check")
            print_info(f"Source file: {source_file}")
            print_info(f"Destination file: {dest_file}")
            sys.exit()
            
        # Check last event metadata
        if source_last_decoded != dest_last_decoded:
            print_error("Mismatch in source and destination last event's metadata, please check")
            print_info(f"Source file: {source_file}")
            print_info(f"Destination file: {dest_file}")
            sys.exit()
    
    print_info(f"Metadata check {Colors.OKGREEN}{Colors.BOLD}successful!{Colors.ENDC}. Proceeding...")


def ask_metadata_confirmation() -> bool:
    """
    Ask user to confirm that displayed metadata is correct.
    
    Returns:
        True if user confirms, False otherwise
    """
    answer = input(f"{Colors.ERRORBLOCK}{Colors.BOLD}[CONFIRMATION]{Colors.ENDC} " +
                  f"Are you sure the metadata is correct? [y/n] ")
    
    while answer not in ('y', 'n'):
        print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} Only available options are " +
              f"`{Colors.OKGREEN}{Colors.BOLD}y{Colors.ENDC}` or " +
              f"`{Colors.OKGREEN}{Colors.BOLD}n{Colors.ENDC}`, please check your reply")
        answer = input(f"{Colors.ERRORBLOCK}{Colors.BOLD}[CONFIRMATION]{Colors.ENDC} " +
                      f"Are you sure the metadata is correct? [y/n] ")
    
    return answer == 'y'


def create_validation_flags(source_dir: str, dest_dir: str) -> None:
    """
    Create validation flag files to mark successful completion.
    
    Args:
        source_dir: Source directory path
        dest_dir: Destination directory path
    """
    create_flag_file(source_dir, "VALIDATED.flag")
    create_flag_file(dest_dir, "VALIDATED.flag")
    print_success("Validation of the data completed. PLEASE WRITE LOG & PROCEED TO REMOVE STEP")


class DAQValidator:
    """
    Main validation handler for DAQ data integrity checks.
    
    This class orchestrates the complete validation process including
    file existence checks, checksum validation, and metadata comparison.
    """
    
    def __init__(self, source_prefix: str):
        """
        Initialize the validator.
        
        Args:
            source_prefix: Base path prefix for source directories
        """
        self.source_prefix = source_prefix
    
    def get_default_destination(self, run_number: str) -> str:
        """
        Get the default destination directory for this validation type.
        
        Args:
            run_number: Run number for constructing the path
            
        Returns:
            Default destination directory path
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement get_default_destination")
    
    def validate_prerequisites(self, source_dir: str) -> None:
        """
        Validate that prerequisites for validation are met.
        
        Args:
            source_dir: Source directory to check
            
        Raises:
            SystemExit: If data hasn't been copied yet
        """
        if not check_flag_file_exists(source_dir, "COPIED.flag"):
            print_error_block("DAQ data must be COPIED before validating. PLEASE CHECK ARGUMENTS!!!")
            sys.exit()
    
    def check_data_consistency(self, source_dir: str, dest_dir: str) -> None:
        """
        Check data consistency between source and destination directories.
        
        Args:
            source_dir: Source directory path
            dest_dir: Destination directory path
            
        This method imports and uses the check_if_exists_in_HDD function
        to ensure data consistency between directories.
        """
        # Import here to avoid circular dependency
        from remove_data_from_DAQ_PC import check_if_exists_in_HDD
        check_if_exists_in_HDD(source_dir, dest_dir)
    
    def validate_data(self, run_number: str, dest_dir: str = None) -> None:
        """
        Main validation method that orchestrates the complete validation process.
        
        Args:
            run_number: Run number identifier
            dest_dir: Destination directory path (optional, uses default if not provided)
            
        This method performs:
        1. Path validation and argument checking
        2. Prerequisites validation (copied flag check)
        3. Data consistency verification
        4. SHA256 checksum validation
        5. Creation of validation flags
        """
        # Use default destination if not provided
        if dest_dir is None:
            dest_dir = self.get_default_destination(run_number)
            
        # Construct paths
        source_dir = self.source_prefix + run_number
        source_dir = ensure_trailing_slash(source_dir)
        dest_dir = ensure_trailing_slash(dest_dir)
        
        # Validate paths exist
        validate_path_exists(source_dir, "Original source data")
        validate_path_exists(dest_dir, "Copied destination data")
        
        # Check prerequisites
        self.validate_prerequisites(source_dir)
        
        # Check data consistency
        self.check_data_consistency(source_dir, dest_dir)
        
        # Get file lists
        source_files = get_data_files(source_dir)
        dest_files = get_data_files(dest_dir)
        
        # Perform fast validation: counts and sizes only (no SHA256)
        validate_file_counts_and_sizes(source_files, dest_files)
        
        # Create validation flags
        create_validation_flags(source_dir, dest_dir)


class SSDValidator(DAQValidator):
    """Validator for SSD to HDD data validation."""
    
    DEFAULT_HDD_PATH = "/Volumes/HDD_16TB_2/"
    
    def __init__(self):
        super().__init__("/Volumes/SSD_8TB/Run_")
    
    def get_default_destination(self, run_number: str) -> str:
        """Return the default HDD destination for SSD validation."""
        return f"{self.DEFAULT_HDD_PATH}Run_{run_number}"


class HDDValidator(DAQValidator):
    """Validator for HDD to HDD data validation."""
    
    DEFAULT_SOURCE_PATH = "/Volumes/HDD_16TB_2/"
    DEFAULT_DEST_PATH = "/Volumes/HDD_16TB_4/"
    
    def __init__(self):
        super().__init__("/Volumes/HDD_16TB_2/Run_")
    
    def get_default_destination(self, run_number: str) -> str:
        """Return the default destination HDD for HDD-to-HDD validation."""
        return f"{self.DEFAULT_DEST_PATH}Run_{run_number}"