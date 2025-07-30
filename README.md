# Ruckit-Geotab Location Sync Integration

A real-time location synchronization service that automatically resolves discrepancies between Geotab and Ruckit fleet management systems, ensuring accurate vehicle tracking across multiple platforms.

## 🚀 Overview

This integration service monitors location data between two fleet management APIs (Geotab and Ruckit) and automatically synchronizes coordinates when discrepancies are detected. The system runs continuously, checking for location mismatches every 2 minutes and updating the Ruckit platform with authoritative location data from Geotab.

## ✨ Key Features

- **Automated Location Synchronization**: Continuous monitoring and sync between Geotab and Ruckit APIs
- **Discrepancy Detection**: Intelligent coordinate comparison with configurable tolerance levels
- **Real-time Updates**: 2-minute polling intervals for near real-time synchronization
- **Credential Management**: Secure handling of API tokens through Geotab's AddInData system
- **Error Handling**: Robust exception handling and retry logic for API failures
- **Logging**: Comprehensive logging for monitoring and debugging

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Geotab API    │    │  Sync Service   │    │   Ruckit API    │
│                 │    │                 │    │                 │
│ • Device Status │◄──►│ • Coordinates   │◄──►│ • Location      │
│ • AddInData     │    │   Comparison    │    │   Updates       │
│ • Credentials   │    │ • Auto-sync     │    │ • Driver Data   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Technical Implementation

### Core Components

1. **LocationSyncScheduler**: Main orchestrator class that manages the sync process
2. **API Integration**: Direct integration with MyGeotab and Ruckit REST APIs
3. **Credential Management**: Retrieves Ruckit API credentials from Geotab's AddInData
4. **Coordinate Comparison**: Implements tolerance-based coordinate matching
5. **Automated Updates**: Posts corrected location data to Ruckit when discrepancies are found

### Data Flow

1. **Credential Retrieval**: Fetches Ruckit API tokens and device mappings from Geotab AddInData
2. **Location Polling**: Retrieves current device locations from both Geotab and Ruckit APIs
3. **Discrepancy Detection**: Compares coordinates with configurable tolerance (0.0001 degrees default)
4. **Automatic Correction**: Posts Geotab coordinates to Ruckit API when mismatches are detected
5. **Continuous Monitoring**: Repeats the process every 2 minutes

## 📋 Prerequisites

- Python 3.7+
- Geotab API credentials with appropriate permissions
- Ruckit API access
- Network connectivity to both APIs

## 🛠️ Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ruckit-geotab-sync
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Geotab credentials
```

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
GEOTAB_USERNAME=your_geotab_username
GEOTAB_DATABASE=your_geotab_database
GEOTAB_PASSWORD=your_geotab_password
```

### Geotab AddInData Setup

The service expects AddInData records in Geotab with the following structure:

```json
{
  "type": "ri-device",
  "details": {
    "gt-device": "device_id_from_geotab",
    "ri-device": "device_id_in_ruckit",
    "ri-token": "ruckit_api_token",
    "ri-driver": "ruckit_driver_id"
  }
}
```

## 🚀 Usage

### Running the Service

```bash
python ruckit.py
```

The service will:
- Authenticate with Geotab API
- Start the continuous sync process
- Log all activities to console
- Run indefinitely until interrupted (Ctrl+C)

### Programmatic Usage

```python
from ruckit import LocationSyncScheduler

# Initialize the scheduler
scheduler = LocationSyncScheduler(
    geotab_username="your_username",
    geotab_database="your_database", 
    geotab_password="your_password"
)

# Start the sync process
scheduler.start()

# Stop when needed
scheduler.stop()
```

## 📊 Monitoring & Logging

The service provides detailed logging for:

- Authentication status
- API call results
- Coordinate comparisons
- Discrepancy detection
- Update success/failure status
- Error conditions and retries

Example log output:
```
=== Starting location sync process at 2024-01-15 10:30:00 ===
Retrieved 25 device status records from Geotab
Retrieved 25 AddInData records from Geotab
Mapped device b123 to Ruckit driver driver456
Processing device b123 - Geotab coords: (-84.3902, 33.7490)
Ruckit coords: (-84.3899, 33.7487)
DISCREPANCY FOUND for device b123!
Successfully posted location update for device truck789
=== Sync completed. Found 3 discrepancies ===
```

## 🔒 Security Considerations

- API credentials are loaded from environment variables
- Placeholder values are automatically filtered out to prevent invalid API calls
- HTTP requests use proper authentication headers
- No sensitive data is logged

## 🏭 Production Deployment

For production deployment, consider:

- **Containerization**: Use Docker for consistent deployment
- **Process Management**: Use systemd, supervisor, or similar for service management  
- **Monitoring**: Implement health checks and alerting
- **Logging**: Configure structured logging with log rotation
- **Error Tracking**: Integrate with error monitoring services

## 🧪 Testing

The service includes built-in validation for:

- API authentication
- Credential validation
- Coordinate comparison logic
- Error handling and recovery

## 📈 Performance

- **Polling Interval**: 2-minute cycles for near real-time sync
- **API Efficiency**: Bulk operations where possible to minimize API calls
- **Memory Usage**: Lightweight operation with minimal memory footprint
- **Scalability**: Can handle hundreds of devices per sync cycle