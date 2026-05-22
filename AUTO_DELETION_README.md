# DAQ Automated Data Deletion System - EXTREMELY DANGEROUS

⚠️ **CRITICAL WARNING: This system PERMANENTLY DELETES experimental data when storage exceeds 60% usage.**

## Overview

The automated deletion system monitors internal SSD storage and safely deletes validated data when storage exceeds the trigger threshold (60% by default). It includes comprehensive safety checks and logging to prevent accidental data loss.

### How It Works

1. **Continuous Monitoring**: Checks SSD storage usage every 5 minutes (configurable)
2. **Trigger Point**: When storage exceeds 60%, starts deletion process
3. **Sequential Deletion**: Deletes runs in order (Run_1, Run_2, Run_3...)
4. **Safety Verification**: Before each deletion, verifies:
   - Data exists in HDD_24TB_6 (and additionally HDD_16TB_4 when `--require-secondary-backup` is set)
   - All required copies have COPIED.flag and VALIDATED.flag
   - Data file counts match between source and the required backup(s)
5. **Stop Point**: When storage drops below 30%, stops deletion
6. **Resume Monitoring**: Returns to monitoring mode

## Files

| File | Purpose |
|------|---------|
| `daq_auto_deletion.py` | Main auto-deletion script |
| `start_auto_deletion.sh` | Launcher with safety features |
| `AUTO_DELETION_README.md` | This documentation |

## Safety Features

### 🛡️ **Multiple Safety Layers**

1. **Dry-Run Default**: Real deletion requires explicit confirmation
2. **Double Verification**: Checks all safety requirements twice
3. **Comprehensive Logging**: Every decision and action logged
4. **Sequential Processing**: Only one run deleted at a time
5. **Storage Monitoring**: Visual storage status display
6. **Fail-Safe Stops**: Stops on any error or safety failure

### 🔐 **Required Confirmations**

For real deletion mode:
- Type exact confirmation phrase: `DELETE_DATA_PERMANENTLY`
- Additional launcher confirmation: `ENABLE_REAL_DELETION`
- Explicit `--real-deletion` flag required

### 📋 **Pre-Deletion Checks**

For each run, verifies:
- ✅ Source directory exists in SSD
- ✅ Copy exists in HDD_24TB_6 with COPIED.flag
- ✅ Copy exists in HDD_16TB_4 with COPIED.flag  *(only with `--require-secondary-backup`)*
- ✅ Source has VALIDATED.flag
- ✅ HDD_24TB_6 copy has VALIDATED.flag
- ✅ HDD_16TB_4 copy has VALIDATED.flag *(only with `--require-secondary-backup`)*
- ✅ Data file counts match across all required locations

## Usage

### 🧪 **Safe Testing (Recommended First)**

```bash
# Safe dry-run monitoring (default)
./start_auto_deletion.sh

# Test with custom interval
./start_auto_deletion.sh --interval 120

# Background dry-run monitoring
./start_auto_deletion.sh --background

# Check status
./start_auto_deletion.sh --status
```

### ⚠️ **Real Deletion Mode (DANGEROUS)**

```bash
# Enable real deletion (requires confirmations)
./start_auto_deletion.sh --real-deletion

# Real deletion in background (EXTREMELY DANGEROUS)
./start_auto_deletion.sh --real-deletion --background
```

### 🛑 **Stop Operations**

```bash
# Stop any running auto-deletion
./start_auto_deletion.sh --stop
```

## Configuration

### Default Settings
- **Trigger Threshold**: 60% storage usage
- **Stop Threshold**: 30% storage usage  
- **Monitoring Interval**: 300 seconds (5 minutes)
- **Mode**: Dry-run (safe)

### Advanced Configuration
```bash
# Custom trigger threshold (use with extreme caution)
python3 daq_auto_deletion.py --force-threshold 75

# Faster monitoring (minimum 60 seconds)
python3 daq_auto_deletion.py --interval 60
```

## Example Scenarios

### Scenario 1: Normal Operation
```
Storage: 72% used (881,671 events used, 340,429 available) → Trigger deletion
├── Check Run_1: All safety checks pass
├── Delete Run_1: Success (now 65% used, 401,234 events available)
├── Check Run_2: All safety checks pass  
├── Delete Run_2: Success (now 58% used, 462,845 events available)
├── Check Run_3: All safety checks pass
├── Delete Run_3: Success (now 28% used, 734,512 events available)
└── Stop: Below 30% threshold
```

### Scenario 2: Safety Failure
```
Storage: 75% used → Trigger deletion
├── Check Run_1: Missing VALIDATED.flag in HDD_16TB_4
├── Skip Run_1: Safety check failed
├── Check Run_2: All safety checks pass
├── Delete Run_2: Success
└── Continue with next runs...
```

## Logging

### Log Files
| File | Content |
|------|---------|
| `./Log/auto_deletion_log_YYYYMMDD_HHMMSS.txt` | Main deletion log |
| `./Log/auto_deletion_console.log` | Console output (background mode) |
| `./Log/Remove_Log/Log_Run_*.txt` | Individual deletion logs |

### Log Entry Types
- **INFO**: Normal operations and status updates
- **WARNING**: Non-critical issues (skipped runs, etc.)
- **ERROR**: Failures that stop the process
- **SUCCESS**: Successful operations
- **CRITICAL**: Deletion triggers and confirmations

### Sample Log
```
[2024-01-15 14:30:00] [CRITICAL] Starting DAQ automated deletion system
[2024-01-15 14:30:00] [CRITICAL] Mode: DRY RUN
[2024-01-15 14:30:00] [INFO] Trigger threshold: 70.0%
[2024-01-15 14:30:00] [INFO] Storage monitoring: 72.3% used
[2024-01-15 14:30:00] [CRITICAL] Storage usage 72.3% exceeds trigger threshold 70.0%
[2024-01-15 14:30:01] [INFO] Evaluating Run_1 for deletion...
[2024-01-15 14:30:01] [SUCCESS] Safety verification PASSED for Run_1 (2.4GB)
[2024-01-15 14:30:01] [WARNING] DRY RUN: Would delete Run_1 (2.4GB)
[2024-01-15 14:30:01] [INFO] Storage after deletion: 68.1%
```

## Visual Storage Display

The system shows real-time storage status with event capacity calculations:

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ STORAGE STATUS: HIGH                                                                 │
│ |████████████████████████████████████▌─────────────| 72.3%                        │
│ Used: 723.0GB / Total: 1000.0GB / Free: 277.0GB                                    │
│ Events: 883,710 used / 1,222,100 total / 338,390 available                         │
│ Event size: 197,376 bytes (0.19 MB each)                                           │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

Color coding:
- 🟢 **Green**: < 30% (Good)
- 🟡 **Yellow**: 30-60% (Moderate) 
- 🟠 **Orange**: 60-80% (High)
- 🔴 **Red**: > 80% (Critical)

## Troubleshooting

### Common Issues

#### 1. Script Won't Start Real Deletion
```bash
# Check confirmation phrase (case sensitive)
Type exactly: DELETE_DATA_PERMANENTLY

# Check launcher confirmation
Type exactly: ENABLE_REAL_DELETION
```

#### 2. No Runs Being Deleted
```bash
# Check run safety status
python3 daq_auto_deletion.py --interval 60  # Dry run to see issues

# Common causes:
# - Missing VALIDATED.flag files
# - Missing backup copies
# - File count mismatches
```

#### 3. Storage Not Decreasing
```bash
# Check if deletions are actually happening
tail -f ./Log/auto_deletion_log_*.txt

# Verify removal script works manually
./Remove_Data.sh <run_number>
```

#### 4. Script Stuck/Hanging
```bash
# Stop the process
./start_auto_deletion.sh --stop

# Check logs for errors
./start_auto_deletion.sh --status
```

### Manual Recovery

If auto-deletion fails:

1. **Stop the process**: `./start_auto_deletion.sh --stop`
2. **Check the logs**: Review latest auto_deletion_log file
3. **Verify manually**: Test `./Remove_Data.sh <run_number>` manually
4. **Fix issues**: Address any safety check failures
5. **Restart**: Use dry-run mode first to test

## Emergency Procedures

### 🚨 **If Deletion Goes Wrong**

1. **STOP IMMEDIATELY**: `./start_auto_deletion.sh --stop`
2. **Check what was deleted**: Review deletion logs
3. **Verify backups**: Ensure HDD copies are intact
4. **Contact data recovery specialist** if needed
5. **Do NOT restart** until root cause is identified

### 📞 **Emergency Contacts**

- **Data Recovery**: Contact system administrator
- **Backup Verification**: Check HDD_24TB_6 (primary) and HDD_16TB_4 (secondary, if enabled)
- **Log Analysis**: Review all log files for failure points

## Performance

### Resource Usage
- **CPU**: Minimal during monitoring, moderate during deletion
- **Memory**: ~100MB Python process
- **Disk I/O**: High during deletion operations
- **Storage**: Monitors `/Volumes/SSD_8TB/`

### Timing Estimates
- **Storage check**: <1 second
- **Safety verification**: 2-5 seconds per run
- **Deletion**: 1-10 minutes per run (depends on size)
- **Full cycle**: Variable based on number of runs to delete

## Best Practices

### 🎯 **Recommended Workflow**

1. **Always test first**: Run in dry-run mode for several cycles
2. **Monitor actively**: Watch logs during real deletion
3. **Verify backups**: Manually check a few runs before enabling real deletion
4. **Start conservatively**: Begin with default settings
5. **Have recovery plan**: Know how to restore from backups

### 🔄 **Regular Maintenance**

- **Weekly**: Review deletion logs for patterns
- **Monthly**: Verify backup integrity
- **Before major experiments**: Test deletion system
- **After system changes**: Re-test in dry-run mode

### ⚡ **Performance Optimization**

- **Faster monitoring**: Use `--interval 60` during high-activity periods
- **Background operation**: Use `--background` for continuous operation
- **Log rotation**: Archive old logs to prevent disk filling

---

## ⚠️ **FINAL SAFETY REMINDERS**

1. **This system PERMANENTLY DELETES experimental data**
2. **Always use dry-run mode first**
3. **Verify all backups before enabling real deletion**
4. **Monitor logs continuously during operation**
5. **Have a data recovery plan ready**
6. **Only authorized personnel should use real deletion mode**

**When in doubt, DO NOT use real deletion mode. Contact the data management team for assistance.**