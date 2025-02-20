# XEP Radar Connector Documentation

## Overview
The XEP Radar Connector is a Python implementation for communicating with X4 radar modules. It provides a synchronous interface for radar communication, offering reliable and straightforward integration options for different application needs.

## Key Features
- Automatic port detection and configuration
- Error handling and retry mechanisms
- Support for raw and normalized frame data
- Register value manipulation
- Context manager support for safe connection handling

## Core Components

### 1. Exception Classes
The module defines a hierarchy of custom exceptions for specific error scenarios:
- `RadarError`: Base exception for all radar-related errors
- `ConnectionError`: Handles connection-specific issues
- `TimeoutError`: Manages timeout scenarios
- `ProtocolError`: Handles protocol-related problems

### 2. RadarConfig Class
```python
@dataclass
class RadarConfig:
    com_port: str
    baudrate: int = 115200
    timeout: float = 5.0
    retry_attempts: int = 20
    packet_version: int = 0  # 0 for legacy, 1 for v2
```

Key features:
- Automatic port detection across different platforms (Windows/Linux)
- Default configuration creation with platform-specific port detection
- Customizable communication parameters

Methods:
- `find_radar_port()`: Automatically detects the radar port
- `create_default()`: Creates a default RadarConfig instance with automatically detected port

### 3. PacketType Enum
Implemented packet types:
- RAW: Used for raw frame data retrieval
- NORMALIZED: Used for normalized frame data retrieval

### 4. XEPRadarConnector Class

#### Initialization
```python
def __init__(self, config: RadarConfig):
    """Initialize the radar connector with given configuration."""
```
- Manages connection state
- Initializes serial communication
- Sets up logging
- Initializes the `_x4_down_converter` flag

Properties:
- `is_open`: Checks if the radar connection is open
- `samplers_per_frame`: Gets the number of samplers per frame

#### Key Methods

##### Connection Management
- `open(connect_string)`: Opens radar connection
- `close()`: Closes radar connection
- `connection(connect_string)`: Context manager for safe connection handling

##### Data Acquisition
Frame Reading:
- `get_frame_raw()`: Retrieves raw frame data
- `get_frame_normalized()`: Retrieves normalized frame data

##### Chip Configuration
- `update_chip(register_name, value)`: Updates register value on the radar chip

#### Internal Operations
1. Communication:
   - `_write_command()`: Writes commands to serial port
   - `_read_response()`: Reads and validates responses
   - `_read_frame()`: Reads frame data
   - `_process_frame()`: Processes raw frame data into numpy arrays
2. State Management:
   - `_connect()`: Establishes initial connection
   - `_update_samplers()`: Updates sampler count

## Usage Examples

### Basic Usage
```python
# Create configuration
config = RadarConfig.create_default()

# Initialize connector
radar = XEPRadarConnector(config)

# Using context manager
with radar.connection("COM3") as r:
    # Get frame data
    frame = r.get_frame_raw()
```

### Register Updates
```python
# Update chip register
radar.update_chip("ddc_en", 1)  # Enable down-converter
frame = radar.get_frame_raw()  # Will now return complex I/Q data
```

## Error Handling
The connector implements comprehensive error handling:
- Connection retry mechanism with configurable attempts
- Protocol error detection and handling
- Timeout management
- Proper resource cleanup

## Data Processing
- Supports both raw and normalized frame data
- Handles complex I/Q data conversion when down-converter is enabled
- Uses numpy for efficient data processing

## Best Practices
1. Always use the context manager when possible for automatic resource cleanup
2. Implement proper error handling for radar operations
3. Monitor connection state using the `is_open` property
4. Use the automatic port detection feature for better portability
5. Check `samplers_per_frame` property when processing frame data

## Technical Details
- Default baudrate: 115200
- Default timeout: 5.0 seconds
- Default retry attempts: 20
- Supports both legacy (v0) and v2 packet versions
- Platform-independent port detection
- Efficient binary data handling using numpy arrays

## Implementation Notes
- Frame data is processed using numpy for efficient array operations
- When down-converter is enabled, frame data is converted to complex I/Q format
- Serial communication includes proper error checking and acknowledgment handling
- Platform-specific port detection handles both Windows (COM*) and Linux (ttyUSB*/ttyACM*) ports