# Website Publishing Assistant User Guide

## Overview

Website Publishing Assistant is a desktop application for automated website deployment, featuring scheduled publishing, merge-based deployment, multi-server synchronization, and date-time validation.

## Features

- 🖥️ **Modern GUI Interface** - Intuitive tkinter-based GUI, no web browser required
- 📁 **Flexible File Selection** - Support for selecting multiple files or folders for deployment
- 🗑️ **Smart File Protection** - Configure excluded files (like web.config) to protect important server configurations
- 🌐 **Multi-Server Deployment** - Deploy to multiple target servers simultaneously with project folder structure support
- 📅 **Date-Time Validation** - Scheduled publishing with date picker, prevents setting past dates
- ⚛️ **Merge-Based Deployment** - Intelligently merge local files with existing server files, protecting important data
- 🔍 **File Conflict Detection** - Check for local file conflicts before deployment
- 📊 **Detailed Logging** - Comprehensive deployment process logging for troubleshooting
- 💾 **Configuration Persistence** - Automatically save all settings, restore after restart

## System Requirements

- Windows 10/11 (Windows SSH environment support)
- Python 3.7+
- Required packages:
  - tkinter (usually included with Python)
  - paramiko (SSH connection)
  - tkcalendar (date picker)
  - json (configuration management)
  - threading (multi-threading support)

## Installation

### Method 1: Direct Python Execution

1. Ensure Python 3.7 or higher is installed
2. Install required packages:
   ```bash
   pip install paramiko tkcalendar
   ```
3. Run the application:
   ```bash
   python app.py
   ```

### Method 2: Package as EXE

Use PyInstaller to package the application as a standalone executable:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Package the application:
   ```bash
   pyinstaller --onefile --windowed --name="Website Publishing Assistant" app.py
   ```

3. After packaging, the `Website Publishing Assistant.exe` file will be generated in the `dist` folder

## Usage Instructions

### 1. Basic Configuration

#### 1.1 Configure Source Files
1. Open the application and switch to the "Settings" tab
2. In the "Target Source Files" area:
   - Click "Add File" to select individual files
   - Click "Add Folder" to select entire folders
   - Select items and click "Remove" to delete unwanted items

#### 1.2 Configure Protected Files
1. In the "Files to Delete Before Publishing" area
2. Enter file names in the text field (e.g., `web.config`, `appsettings.json`)
3. Click the "Add" button
4. Multiple files can be added; select and click "Remove" to delete
5. Click "Test Delete Files" to check for local file conflicts

#### 1.3 Configure Target Servers
1. Click "Add Server" in the "Target Servers" area
2. Fill in the dialog box:
   - **IP Address**: Server IP address
   - **Username**: SSH login username
   - **Password**: SSH login password
   - **Target Path**: Parent directory path for deployment (e.g., `D:\websites`)
   - **SSH Port**: SSH connection port (default 22)
3. Click "OK" to save
4. Multiple servers can be added; select and click "Remove" to delete or "Edit" to modify
5. Click "Test Connection" to verify server connectivity

### 2. Publishing Operations

#### 2.1 Immediate Publishing
1. Switch to the "Publish" tab
2. Confirm all settings are correct
3. Click the "Publish Now" button
4. The application will display publishing progress and status

#### 2.2 Scheduled Publishing
1. In the "Scheduled Publishing Settings" area on the "Publish" tab
2. Select publishing date (click date field to open calendar)
3. Set publishing time (24-hour format)
4. Click "Set Scheduled Publishing"
5. The application will display:
   - Next publishing time
   - Countdown timer
   - Target server list
6. To cancel, click "Cancel Schedule"

### 3. Merge-Based Deployment Process

The application uses the following steps to ensure deployment safety and completeness:

1. **Configuration Validation**: Check source files, target servers, and network connections
2. **File Conflict Detection**: Check if local files contain files that need protection
3. **Project Structure Creation**: Create project folders for each source directory under the server parent directory
4. **Filtered File Upload**: Skip protected files, upload only necessary update files
5. **Merge Deployment**: Use xcopy (Windows) or rsync (Linux) for intelligent merging
6. **Protect Important Files**: Server's web.config, database files, and other important files are preserved
7. **Feature Updates**: New feature files overwrite old versions for version upgrades
8. **Cleanup Temporary Files**: Clean up temporary files from the deployment process

### 4. Project Folder Structure

Assuming server path is set to `D:\websites` and source files are:
- `C:\projects\website1`
- `C:\projects\website2`

Server structure after deployment:
```
D:\websites\
├── website1\
│   ├── index.html (updated file)
│   ├── style.css (updated file)
│   ├── web.config (protected server file)
│   └── data.db (protected server file)
└── website2\
    ├── app.js (updated file)
    ├── config.json (protected server file)
    └── logs\ (protected server directory)
```

This process ensures:
- No service interruption during deployment
- Feature files are properly updated
- Important server configuration files are protected
- Database and log files are not lost

## Configuration File

The application automatically creates a `config.json` file in the execution directory containing all settings:

```json
{
  "source_files": ["list of file or folder paths"],
  "delete_files": ["list of protected file names"],
  "servers": [
    {
      "ip": "server IP",
      "username": "username",
      "password": "password",
      "path": "target parent directory path",
      "port": 22
    }
  ],
  "schedule_time": "scheduled publishing time (ISO format)"
}
```

## Logging System

The application creates log files in the `logs` directory:
- File name format: `publish_YYYYMMDD.log`
- Content includes: connection tests, file uploads, deployment processes, error messages
- Log levels: INFO (general information), WARNING (warnings), ERROR (errors)

## Important Notes

### Security
- Passwords are stored in plain text in the configuration file; ensure file security
- Recommend using dedicated deployment accounts with limited permissions
- Regularly change SSH passwords
- Avoid using in unsecured network environments

### Network Requirements
- Ensure SSH connectivity to target servers
- Firewall must allow SSH port (usually 22)
- Recommended for use in internal network environments
- Supports Chinese character processing in Windows SSH environments

### File Permissions
- Ensure SSH user has write permissions to target paths
- If target path doesn't exist, the application will attempt to create it
- Appropriate file system permissions required in Windows environments

### Testing Recommendations
- Test functionality in a test environment before first use
- Use "Test Connection" and "Test Delete Files" functions to verify settings
- Perform complete backups before important production deployments
- Test functionality correctness using local SSH

## Troubleshooting

### Common Issues

1. **SSH Connection Failure**
   - Check IP address, username, and password
   - Confirm SSH service is running
   - Check firewall settings
   - Verify network connectivity

2. **UTF-8 Encoding Errors**
   - Application supports multiple encoding formats
   - Automatically handles Traditional Chinese (CP950) and Simplified Chinese (GBK)
   - If issues persist, check system locale settings

3. **File Upload Failure**
   - Check target path permissions
   - Confirm sufficient disk space
   - Check if files are in use by other processes
   - Confirm SFTP directory creation success

4. **Scheduled Publishing Not Executing**
   - Ensure computer is running at scheduled time
   - Check system time accuracy
   - Verify application hasn't closed unexpectedly
   - Check date setting is in the future

5. **File Conflict Detection Issues**
   - Use "Test Delete Files" function for diagnosis
   - Check file paths and names are correct
   - Confirm local file existence

### Error Logs

Detailed runtime errors are recorded in log files, including:
- Detailed connection error messages
- Reasons for file operation failures
- Complete deployment process records
- Timestamps and error levels

## Version Information

- **Version**: 2.0.0
- **Last Updated**: July 2025
- **Supported Platforms**: Windows 10/11
- **Development Language**: Python 3.7+
- **Major Improvements**:
  - Merge-based deployment mechanism
  - Project folder structure support
  - Date-time validation
  - File conflict detection
  - Windows SSH environment compatibility
  - UTF-8 encoding issue fixes

## Technical Support

For issues or feature improvements:
1. Check log files in the `logs` directory
2. Use testing functions to diagnose problems
3. Refer to source code for custom modifications
4. Contact development team for technical support

---

**Warning**: This application involves server file operations. Please thoroughly test functionality in a test environment before use and ensure appropriate backup measures are in place. Understand the merge-based deployment mechanism before deployment.