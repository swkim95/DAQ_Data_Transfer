# DAQ Data Processing Automation

This automation system monitors the experimental data directory and automatically processes new runs through the complete backup and validation workflow.

## Overview

The automation system performs a 4-step process when a new run appears:

1. **Copy SSD → HDD_16TB_2** (Primary backup)
2. **Validate SSD ↔ HDD_16TB_2** (Ensure integrity)
3. **Copy HDD_16TB_2 → HDD_16TB_4** (Secondary backup)
4. **Validate HDD_16TB_2 ↔ HDD_16TB_4** (Ensure backup integrity)

## Key Features

### Safety Features
- ✅ **No automatic deletion** - Manual safety requirement maintained
- ✅ **Comprehensive pre-flight checks** - Validates paths, flags, and prerequisites
- ✅ **Skip already processed runs** - Intelligent state tracking
- ✅ **Detailed logging** - All operations logged with timestamps
- ✅ **Error handling** - Stops on any failure, requires manual intervention
- ✅ **Dry-run mode** - Test operations without executing

### Smart Processing
- ✅ **Automatic run detection** - Monitors `/Volumes/SSD_8TB/` for new runs
- ✅ **Sequential processing** - Processes Run_N-1 when Run_N appears
- ✅ **State awareness** - Resumes interrupted workflows
- ✅ **Duplicate prevention** - Checks existing copies before starting transfers

## Files

| File | Purpose |
|------|---------|
| `daq_automation.py` | Main automation script |
| `start_automation.sh` | Launcher script with convenience features |
| `AUTOMATION_README.md` | This documentation |

## Quick Start

### 1. Start with Default Settings
```bash
./start_automation.sh
```
- Checks every 60 seconds
- Runs in foreground
- Full logging enabled

### 2. Start in Background
```bash
./start_automation.sh --background
```
- Runs continuously in background
- Logs to `./Log/automation_console.log`
- Use `--stop` to terminate

### 3. Test Mode (Recommended First)
```bash
./start_automation.sh --dry-run
```
- Shows what would be done
- No actual file operations
- Safe for testing

### 4. Custom Monitoring Interval
```bash
./start_automation.sh --interval 30
```
- Checks every 30 seconds
- Minimum allowed: 10 seconds

## Usage Examples

### Basic Operations
```bash
# Start automation (foreground)
./start_automation.sh

# Start automation (background)
./start_automation.sh --background

# Stop automation
./start_automation.sh --stop

# Check status
./start_automation.sh --status

# Test without executing
./start_automation.sh --dry-run
```

### Advanced Usage
```bash
# Fast monitoring in background
./start_automation.sh --background --interval 15

# Test with custom interval
./start_automation.sh --dry-run --interval 30

# Direct Python execution
python3 daq_automation.py --interval 60 --dry-run
```

## How It Works

### Monitoring Logic
1. **Scans** `/Volumes/SSD_8TB/` for `Run_*` directories
2. **Identifies** the latest run (still being taken)
3. **Processes** the second-to-latest run (completed run)
4. **Tracks** progress using flag files (`COPIED.flag`, `VALIDATED.flag`)

### Processing Workflow
For each run (e.g., Run_11876):

```
Run_11877 appears → Process Run_11876

Step 1: SSD → HDD_16TB_2
├── Check: Already copied?
├── Execute: ./Transfer_Data.sh 11876
└── Verify: COPIED.flag created

Step 2: Validate SSD ↔ HDD_16TB_2  
├── Check: Already validated?
├── Execute: ./Valid_Data.sh 11876
└── Verify: VALIDATED.flag created

Step 3: HDD_16TB_2 → HDD_16TB_4
├── Check: Already copied?
├── Execute: ./Transfer_Data_HDD.sh 11876
└── Verify: COPIED.flag created

Step 4: Validate HDD_16TB_2 ↔ HDD_16TB_4
├── Check: Already validated?
├── Execute: ./Valid_Data_HDD.sh 11876
└── Verify: VALIDATED.flag created
```

### State Management
- **Resumes interrupted workflows** - If Step 2 failed, restarts from Step 2
- **Skips completed steps** - If copying is done, goes directly to validation
- **Prevents duplicates** - Won't re-process fully completed runs

## Logging

### Log Files
| File | Content |
|------|---------|
| `./Log/automation_log_YYYYMMDD_HHMMSS.txt` | Main automation log |
| `./Log/automation_console.log` | Console output (background mode) |
| `./Log/Copy_Log/Log_Run_*.txt` | Individual transfer logs |
| `./Log/Valid_Log/Log_Run_*.txt` | Individual validation logs |
| `./Log_HDD/Copy_Log/Log_Run_*.txt` | HDD transfer logs |
| `./Log_HDD/Valid_Log/Log_Run_*.txt` | HDD validation logs |

### Log Entry Format
```
[2024-01-15 14:30:25] [INFO] Starting processing of Run_11876
[2024-01-15 14:30:25] [INFO] Current status for Run_11876:
[2024-01-15 14:30:25] [INFO]   HDD1 copied: False
[2024-01-15 14:30:25] [INFO]   HDD2 copied: False
[2024-01-15 14:30:25] [INFO]   SSD validated: False
[2024-01-15 14:30:25] [INFO]   HDD validated: False
[2024-01-15 14:30:26] [INFO] Step 1: Copying Run_11876 from SSD to HDD1
[2024-01-15 14:30:26] [INFO] Executing: ./Transfer_Data.sh 11876
[2024-01-15 14:45:32] [SUCCESS] Successfully completed: ./Transfer_Data.sh 11876
```

## Safety Features

### Pre-Flight Checks
- ✅ Source directory exists
- ✅ Destination HDDs are mounted
- ✅ Required scripts are available
- ✅ Previous steps completed successfully

### Error Handling
- ❌ **Script failure** → Stop processing, log error, require manual intervention
- ❌ **Timeout** → Abort after 1 hour, log timeout
- ❌ **Missing prerequisites** → Skip run, log warning

### Manual Override
All operations can be run manually if automation fails:
```bash
# Manual execution (if automation fails)
./Transfer_Data.sh 11876
./Valid_Data.sh 11876  
./Transfer_Data_HDD.sh 11876
./Valid_Data_HDD.sh 11876
```

## Troubleshooting

### Common Issues

#### 1. Automation Not Starting
```bash
# Check script permissions
ls -la start_automation.sh daq_automation.py

# Check for errors
./start_automation.sh --dry-run
```

#### 2. Stuck Processing
```bash
# Check status
./start_automation.sh --status

# View recent logs
tail -20 ./Log/automation_log_*.txt

# Manual restart
./start_automation.sh --stop
./start_automation.sh --background
```

#### 3. Script Failures
```bash
# Check individual logs
ls -la ./Log/Copy_Log/
ls -la ./Log/Valid_Log/

# Test individual components
./Transfer_Data.sh 11876 --dry-run  # if available
python3 transfer_from_DAQ_PC_to_HDD.py 11876
```

#### 4. Storage Issues
```bash
# Check disk space
df -h /Volumes/HDD_16TB_2
df -h /Volumes/HDD_16TB_4
df -h /Users/yhep/scratch

# Check mount points
ls -la /Volumes/
```

### Manual Recovery

If automation fails mid-process:

1. **Check the logs** to identify the failure point
2. **Verify the current state** of flag files
3. **Run the failed step manually**
4. **Restart automation** - it will resume from the next step

Example:
```bash
# If validation failed
./Valid_Data.sh 11876

# Then restart automation
./start_automation.sh --background
```

## Performance

### Resource Usage
- **CPU**: Minimal (monitoring only)
- **Memory**: ~50MB Python process
- **Network**: None (local operations only)
- **Disk I/O**: High during transfer operations

### Timing
- **Monitoring overhead**: <1 second per cycle
- **Transfer time**: Depends on data size (typically 10-60 minutes)
- **Validation time**: Depends on data size (typically 5-30 minutes)

### Recommended Settings
- **Production**: `--interval 60` (1 minute)
- **Development**: `--interval 30` (30 seconds)  
- **Testing**: `--dry-run` mode first

## Integration

### Starting with System
To start automation automatically:

1. **Add to crontab**:
   ```bash
   @reboot cd /Users/yhep/DAQ_Data_Transfer && ./start_automation.sh --background
   ```

2. **Create launchd service** (macOS):
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>Label</key>
       <string>com.daq.automation</string>
       <key>ProgramArguments</key>
       <array>
           <string>/Users/yhep/DAQ_Data_Transfer/start_automation.sh</string>
           <string>--background</string>
       </array>
       <key>WorkingDirectory</key>
       <string>/Users/yhep/DAQ_Data_Transfer</string>
       <key>RunAtLoad</key>
       <true/>
   </dict>
   </plist>
   ```

### Monitoring Integration
The log files can be integrated with monitoring systems:
- **Splunk**: Monitor `./Log/automation_log_*.txt`
- **Custom alerts**: Parse log files for ERROR messages
- **Dashboard**: Track processing statistics

## Security

### File Permissions
- Scripts require execute permissions
- Log directories created with safe permissions
- No external network access required

### Data Protection
- **No deletion automation** - Manual safety requirement
- **Read-only monitoring** of source directory
- **Comprehensive validation** before any operations
- **Atomic operations** - Either complete or nothing

---

## Support

For issues or questions:
1. Check this documentation
2. Review log files in `./Log/`
3. Test with `--dry-run` mode
4. Run individual scripts manually
5. Contact the development team

**Remember**: This system handles extremely valuable experimental data. When in doubt, stop automation and proceed manually.