"""
DAQ Remote Backup Script  (HDD_24TB_6  ->  KNU remote server)

Secondary backup that ships completed, validated runs from the primary HDD
to a remote server over rsync-over-SSH. Pairs with daq_automation.py: it
will only upload a run after daq_automation.py has produced COPIED.flag +
VALIDATED.flag on /Volumes/HDD_24TB_6.

Workflow per monitoring cycle:
    1.  Scan /Volumes/HDD_24TB_6 for Run_* directories.
    2.  For each run, in chronological order, check ALL of:
            - Run is fully backed up to HDD_24TB_6:  COPIED.flag exists
            - Run is validated against SSD:          VALIDATED.flag exists
            - Run is no longer being taken:          Run_<N+1> exists on
              /Volumes/SSD_8TB or /Volumes/HDD_24TB_6
            - Run has not been uploaded yet:         UPLOADED.flag missing
    3.  If all conditions are met, rsync the run to the remote server.
    4.  On success, touch UPLOADED.flag on HDD_24TB_6 so the next cycle skips it.

Authentication:
    SSH password auth is supported via `sshpass`. The password is read from
    the environment variable SSHPASS (`sshpass -e`); it is never put on the
    command line, written to a log file, or printed. Public-key auth is also
    supported -- if SSHPASS is unset the script falls back to plain rsync
    over ssh, which will work if the remote accepts key-based login.

Usage:
    export SSHPASS='your-knu-password'
    python3 daq_remote_backup.py --remote user@knu.example.com:/path/to/backup
    python3 daq_remote_backup.py --remote ... --dry-run          # safe test
    python3 daq_remote_backup.py --remote ... --once             # single pass
    python3 daq_remote_backup.py --remote ... --interval 30      # custom poll

CRITICAL: this is data-bearing automation. Run with --dry-run first to
confirm which runs would be uploaded.
"""

import argparse
import datetime
import os
import shlex
import shutil
import subprocess
import sys
import time
from typing import List, Tuple

from daq_utils import (
    Colors,
    check_flag_file_exists,
    create_flag_file,
    print_error,
    print_info,
    print_success,
    print_warning,
)


# Flag names used to track state on the primary HDD.
COPIED_FLAG = "COPIED.flag"
VALIDATED_FLAG = "VALIDATED.flag"
UPLOADED_FLAG = "UPLOADED.flag"


class DAQRemoteBackup:
    """Watches HDD_24TB_6 and uploads validated runs to a remote server."""

    def __init__(
        self,
        remote_dest: str,
        monitoring_interval: int = 60,
        dry_run: bool = False,
        ssh_port: int = 22,
        run_once: bool = False,
        rsync_timeout: int = 6 * 3600,
        bwlimit_kbps: int = 0,
        remote_chmod: str = "ugo=rwx",
    ):
        """
        Args:
            remote_dest:         rsync destination like "user@host:/path/" .
                                 The trailing slash is added automatically.
            monitoring_interval: Seconds between scans (ignored if run_once).
            dry_run:             If True, print the rsync that would run but
                                 do not actually transfer or create flags.
            ssh_port:            SSH port for the remote (default 22).
            run_once:            If True, do a single pass over eligible runs
                                 and exit; otherwise loop forever.
            rsync_timeout:       Per-run rsync timeout in seconds.
            bwlimit_kbps:        rsync --bwlimit value in KiB/s; 0 disables it.
                                 Capping bandwidth bounds the TCP send-queue
                                 depth, which is a defensive measure against
                                 the known macOS TCP-SACK accounting bug that
                                 has paniced this machine — see commit notes.
                                 Recommended: 50000 (≈50 MB/s) on a healthy
                                 LAN; 0 (default) means no limit.
            remote_chmod:        rsync --chmod spec applied to every uploaded
                                 file and directory on the remote side. The
                                 default "ugo=rwx" yields 0777 on both files
                                 and directories so collaborators on the
                                 receiving server can read/edit them
                                 regardless of group membership. Pass an
                                 empty string to keep source permissions.
        """
        self.remote_dest = remote_dest.rstrip("/") + "/"
        self.monitoring_interval = monitoring_interval
        self.dry_run = dry_run
        self.ssh_port = ssh_port
        self.run_once = run_once
        self.rsync_timeout = rsync_timeout
        self.bwlimit_kbps = bwlimit_kbps
        self.remote_chmod = remote_chmod

        # Paths
        self.hdd_base = "/Volumes/HDD_24TB_6"
        self.ssd_base = "/Volumes/SSD_8TB"

        # Logging
        self.copy_log_dir = "./Log/Remote_Backup_Log"
        os.makedirs(self.copy_log_dir, exist_ok=True)
        self.setup_logging()

        # Detect sshpass / password availability
        self.sshpass_path = shutil.which("sshpass")
        self.use_sshpass = bool(os.environ.get("SSHPASS")) and self.sshpass_path is not None

    # ------------------------------------------------------------------ logging
    def setup_logging(self) -> None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("./Log", exist_ok=True)
        self.log_file = f"./Log/remote_backup_log_{timestamp}.txt"
        with open(self.log_file, "w") as f:
            f.write(f"DAQ Remote Backup Log - Started at {datetime.datetime.now()}\n")
            f.write(f"Remote destination:  {self.remote_dest}\n")
            f.write(f"SSH port:            {self.ssh_port}\n")
            f.write(f"Monitoring interval: {self.monitoring_interval} seconds\n")
            f.write(f"Run once:            {self.run_once}\n")
            f.write(f"Dry run:             {self.dry_run}\n")
            f.write("=" * 80 + "\n\n")

    def log_message(self, message: str, level: str = "INFO") -> None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        if level == "INFO":
            print_info(message)
        elif level == "WARNING":
            print_warning(message)
        elif level == "ERROR":
            print_error(message)
        elif level == "SUCCESS":
            print_success(message)
        else:
            print(entry)
        try:
            with open(self.log_file, "a") as f:
                f.write(entry + "\n")
                f.flush()
        except Exception as exc:
            print(f"Failed to write to log file: {exc}")

    # --------------------------------------------------------- run discovery
    def _list_run_numbers(self, base: str) -> List[int]:
        if not os.path.isdir(base):
            return []
        out = []
        try:
            for item in os.listdir(base):
                if not item.startswith("Run_"):
                    continue
                if not os.path.isdir(os.path.join(base, item)):
                    continue
                try:
                    out.append(int(item.replace("Run_", "")))
                except ValueError:
                    continue
        except Exception as exc:
            self.log_message(f"Error scanning {base}: {exc}", "ERROR")
        return sorted(out)

    def get_hdd_runs(self) -> List[int]:
        return self._list_run_numbers(self.hdd_base)

    def get_ssd_runs(self) -> List[int]:
        return self._list_run_numbers(self.ssd_base)

    # ----------------------------------------------------- eligibility check
    def is_eligible(self, run_number: int, hdd_runs: List[int], ssd_runs: List[int]) -> Tuple[bool, str]:
        """
        Decide whether Run_<run_number> is ready for remote upload.

        Returns (True, reason) when eligible, (False, reason) otherwise.
        """
        run_dir = os.path.join(self.hdd_base, f"Run_{run_number}")

        if not os.path.isdir(run_dir):
            return False, f"Run directory missing on HDD: {run_dir}"

        if not check_flag_file_exists(run_dir, COPIED_FLAG):
            return False, f"Primary backup not finished (no {COPIED_FLAG})"

        if not check_flag_file_exists(run_dir, VALIDATED_FLAG):
            return False, f"Primary backup not validated (no {VALIDATED_FLAG})"

        # "Next run is being copied (or already copied)" - the same
        # second-to-latest gating as daq_automation.py.
        next_run = run_number + 1
        if next_run not in hdd_runs and next_run not in ssd_runs:
            return False, f"Next run Run_{next_run} not yet visible on SSD or HDD"

        if check_flag_file_exists(run_dir, UPLOADED_FLAG):
            return False, f"Already uploaded ({UPLOADED_FLAG} present)"

        return True, "Eligible"

    # ------------------------------------------------------------ rsync exec
    def _build_rsync_command(self, run_number: int) -> List[str]:
        """
        Build the rsync argv. Note: returned as a Python list (no shell
        interpolation), so the password is never on the command line.
        """
        run_dir = os.path.join(self.hdd_base, f"Run_{run_number}") + "/"
        remote_run = self.remote_dest + f"Run_{run_number}/"
        log_file = os.path.join(
            self.copy_log_dir, f"rsync_remote_Run_{run_number}.log"
        )

        # SSH options chosen for stable long-haul throughput:
        #   - ServerAlive* keeps the control connection healthy even on
        #     idle stretches of the transfer.
        #   - IPQoS=throughput hints to the kernel/routers that this is a
        #     bulk stream, which results in cleaner TCP buffer behaviour
        #     and slightly reduces the SACK-edge cases that have caused
        #     macOS kernel panics on this host (see top-of-file note).
        #   - TCPKeepAlive=yes adds an OS-level liveness probe on top of
        #     the SSH-level ServerAlive (defence in depth on flaky links).
        ssh_cmd = (
            f"ssh -p {self.ssh_port} "
            f"-o StrictHostKeyChecking=accept-new "
            f"-o ServerAliveInterval=60 "
            f"-o ServerAliveCountMax=10 "
            f"-o IPQoS=throughput "
            f"-o TCPKeepAlive=yes"
        )

        rsync_args = [
            "rsync",
            "-avh",
            "--itemize-changes",
            "--partial",
            "--human-readable",
            "--progress",
            f"--log-file={log_file}",
            # Skip macOS sidecars + local-only flags.
            "--exclude=._*",
            "--exclude=.DS_Store",
            f"--exclude={UPLOADED_FLAG}",
            "-e", ssh_cmd,
        ]

        # Force a uniform permission set on the remote side so
        # collaborators on the receiving server can always read/edit the
        # uploaded files regardless of source umask. Default is
        # "ugo=rwx" → mode 0777 on both files and directories. The
        # operator can pass --remote-chmod "" to disable this and
        # preserve the source permissions instead.
        if self.remote_chmod:
            rsync_args.append(f"--chmod={self.remote_chmod}")

        # Optional bandwidth throttle. Mitigates the macOS SACK-accounting
        # panic class by capping how much data sits in the TCP send queue
        # at any given moment. Off by default (0). Recommended ~50000
        # KiB/s on a healthy LAN where the bug has been observed.
        if self.bwlimit_kbps and self.bwlimit_kbps > 0:
            rsync_args.append(f"--bwlimit={self.bwlimit_kbps}")

        rsync_args += [run_dir, remote_run]

        if self.use_sshpass:
            # sshpass -e reads SSHPASS env var; password never appears in argv.
            return [self.sshpass_path, "-e"] + rsync_args
        return rsync_args

    def upload_run(self, run_number: int) -> bool:
        """Upload a single run via rsync. Returns True on success."""
        run_dir = os.path.join(self.hdd_base, f"Run_{run_number}")
        cmd = self._build_rsync_command(run_number)

        # The password lives only in $SSHPASS (read by `sshpass -e`), so it
        # never ends up in argv -- it is safe to log the full command line.
        self.log_message(
            f"Uploading Run_{run_number} to remote (sshpass={'on' if self.use_sshpass else 'off'})"
        )
        self.log_message("Command: " + " ".join(shlex.quote(p) for p in cmd))

        if self.dry_run:
            self.log_message(f"DRY RUN: would upload Run_{run_number}", "WARNING")
            return True

        # Pass current environment so SSHPASS is visible to sshpass.
        env = os.environ.copy()
        start_time = time.time()
        try:
            process = subprocess.Popen(cmd, env=env)
            while True:
                if time.time() - start_time > self.rsync_timeout:
                    self.log_message(
                        f"rsync exceeded {self.rsync_timeout}s timeout, killing",
                        "ERROR",
                    )
                    try:
                        process.kill()
                    except Exception:
                        pass
                    return False
                if process.poll() is not None:
                    break
                time.sleep(0.5)
            rc = process.returncode
        except KeyboardInterrupt:
            self.log_message("Interrupted by user, killing rsync", "WARNING")
            try:
                process.kill()
            except Exception:
                pass
            raise
        except Exception as exc:
            self.log_message(f"rsync subprocess error: {exc}", "ERROR")
            return False

        if rc != 0:
            # rsync exit codes: 0 ok, 23 partial transfer, 30 timeout, etc.
            self.log_message(
                f"rsync for Run_{run_number} exited with code {rc}", "ERROR"
            )
            return False

        # Touch UPLOADED.flag on HDD so we never re-upload.
        try:
            create_flag_file(run_dir, UPLOADED_FLAG)
        except Exception as exc:
            self.log_message(
                f"Upload succeeded but failed to create flag: {exc}", "ERROR"
            )
            return False

        self.log_message(
            f"Successfully uploaded Run_{run_number} and wrote {UPLOADED_FLAG}",
            "SUCCESS",
        )
        return True

    # ------------------------------------------------------------ monitoring
    def run_monitoring_cycle(self) -> bool:
        """
        One scan + at most one upload. Returns True if it processed (or
        attempted) a run this cycle; False if nothing was eligible.
        """
        hdd_runs = self.get_hdd_runs()
        ssd_runs = self.get_ssd_runs()

        if not hdd_runs:
            self.log_message(
                f"No Run_* directories found in {self.hdd_base}", "WARNING"
            )
            return False

        for run_number in hdd_runs:  # already sorted ascending
            ok, reason = self.is_eligible(run_number, hdd_runs, ssd_runs)
            if not ok:
                self.log_message(f"Skip Run_{run_number}: {reason}")
                continue

            self.log_message(f"Eligible: Run_{run_number}")
            success = self.upload_run(run_number)
            if success:
                self.log_message(f"Run_{run_number} done", "SUCCESS")
            else:
                self.log_message(
                    f"Run_{run_number} failed, stopping this cycle", "ERROR"
                )
            return True  # one run per cycle keeps logs and I/O manageable

        return False

    def run(self) -> None:
        self.log_message("Starting DAQ remote backup")
        self.log_message(f"HDD base:           {self.hdd_base}")
        self.log_message(f"SSD base:           {self.ssd_base}")
        self.log_message(f"Remote destination: {self.remote_dest}")
        self.log_message(f"SSH port:           {self.ssh_port}")
        self.log_message(
            f"Remote chmod:       {self.remote_chmod or '(preserve source)'}"
        )
        self.log_message(
            f"Bandwidth limit:    {self.bwlimit_kbps if self.bwlimit_kbps else 'unlimited'}"
            + (" KiB/s" if self.bwlimit_kbps else "")
        )
        self.log_message(
            f"sshpass: {'available' if self.sshpass_path else 'NOT FOUND'}"
            f", SSHPASS env: {'set' if os.environ.get('SSHPASS') else 'unset'}"
        )

        if not self.use_sshpass:
            self.log_message(
                "Will rely on SSH public-key auth (SSHPASS env unset or sshpass missing)",
                "WARNING",
            )

        if self.dry_run:
            self.log_message("DRY RUN MODE - no files will be transferred", "WARNING")

        try:
            while True:
                self.log_message("Running monitoring cycle...")
                self.run_monitoring_cycle()

                if self.run_once:
                    self.log_message("Run-once mode: exiting after one cycle")
                    return

                self.log_message(
                    f"Waiting {self.monitoring_interval} seconds for next cycle..."
                )
                time.sleep(self.monitoring_interval)
        except KeyboardInterrupt:
            self.log_message("Remote backup stopped by user", "WARNING")


def _validate_remote(spec: str) -> str:
    """
    Sanity-check the rsync remote spec. Accepts forms like:
        user@host:/abs/path
        user@host:relative/path
        host:/path
    """
    if "@" not in spec or ":" not in spec.split("@", 1)[1]:
        raise argparse.ArgumentTypeError(
            "remote must look like user@host:/path/  (got: %r)" % spec
        )
    return spec


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DAQ Remote Backup (HDD_24TB_6 -> KNU server via rsync/SSH)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Authentication:
  - Set the SSHPASS env var to use password auth (requires `sshpass`):
        export SSHPASS='your-password'
        python3 daq_remote_backup.py --remote user@host:/path/
  - If SSHPASS is unset, falls back to standard SSH (public key auth).

Examples:
  # Safe test (no transfer, no flag files written)
  python3 daq_remote_backup.py --remote user@host:/backup/ --dry-run --once

  # Single pass over eligible runs and exit
  python3 daq_remote_backup.py --remote user@host:/backup/ --once

  # Continuous monitoring every 60 seconds
  python3 daq_remote_backup.py --remote user@host:/backup/
""",
    )
    parser.add_argument(
        "--remote",
        type=_validate_remote,
        required=True,
        help="Remote rsync destination, e.g. user@knu.example.com:/path/",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Monitoring interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--ssh-port", type=int, default=22, help="Remote SSH port (default: 22)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without transferring anything",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one cycle over all eligible runs and exit",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=6 * 3600,
        help="Per-run rsync timeout in seconds (default: 6 hours)",
    )
    parser.add_argument(
        "--bwlimit",
        type=int,
        default=0,
        metavar="KBPS",
        help=(
            "rsync bandwidth cap in KiB/s. 0 disables it (default). "
            "Setting e.g. 50000 (~50 MB/s) bounds TCP send-queue depth "
            "and is recommended as a workaround on macOS hosts that "
            "have experienced the TCP-SACK accounting kernel panic."
        ),
    )
    parser.add_argument(
        "--remote-chmod",
        default="ugo=rwx",
        metavar="SPEC",
        help=(
            "rsync --chmod spec applied on the remote side. Default "
            "'ugo=rwx' yields 0777 on every uploaded file and directory "
            "so the remote collaborators can always read/edit them. "
            "Pass empty string ('--remote-chmod=') to preserve source "
            "permissions instead."
        ),
    )

    args = parser.parse_args()

    if args.interval < 1:
        print("Error: --interval must be >= 1", file=sys.stderr)
        sys.exit(2)

    # Friendly notice if the user clearly wanted password auth but didn't set it.
    if not os.environ.get("SSHPASS"):
        print(
            f"{Colors.WARNING}[WARNING]{Colors.ENDC} SSHPASS env var is not set. "
            "If your remote needs a password, export SSHPASS first:\n"
            "  export SSHPASS='your-password'",
            file=sys.stderr,
        )

    backup = DAQRemoteBackup(
        remote_dest=args.remote,
        monitoring_interval=args.interval,
        dry_run=args.dry_run,
        ssh_port=args.ssh_port,
        run_once=args.once,
        rsync_timeout=args.timeout,
        bwlimit_kbps=args.bwlimit,
        remote_chmod=args.remote_chmod,
    )
    backup.run()


if __name__ == "__main__":
    main()
