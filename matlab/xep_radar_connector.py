import logging
import platform
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union, List
import serial
import serial.tools.list_ports
import numpy as np
from contextlib import contextmanager

class RadarError(Exception):
    """Base exception for radar-related errors."""
    pass

class ConnectionError(RadarError):
    """Raised when connection issues occur."""
    pass

class TimeoutError(RadarError):
    """Raised when operations timeout."""
    pass

class ProtocolError(RadarError):
    """Raised when protocol-related issues occur."""
    pass

@dataclass
class RadarConfig:
    """Configuration parameters for the radar connection."""
    com_port: str
    baudrate: int = 115200
    timeout: float = 5.0
    retry_attempts: int = 20
    packet_version: int = 0  # 0 for legacy, 1 for v2

    @staticmethod
    def find_radar_port() -> Optional[str]:
        """Find and return the first available radar port.
        
        Returns:
            Optional[str]: Platform-specific port name or None if not found
        """
        # List all available ports
        available_ports = list(serial.tools.list_ports.comports())
        
        if not available_ports:
            return None
            
        # On Linux, ports are typically named /dev/ttyUSB* or /dev/ttyACM*
        # On Windows, ports are named COM*
        system = platform.system().lower()
        
        for port in available_ports:
            port_name = port.device
            if system == 'linux' and ('ttyUSB' in port_name or 'ttyACM' in port_name):
                return port_name
            elif system == 'windows' and port_name.startswith('COM'):
                return port_name
                
        return None

    @classmethod
    def create_default(cls) -> 'RadarConfig':
        """Create a RadarConfig instance with automatically detected port.
        
        Returns:
            RadarConfig: Configuration instance with detected port or default COM3/ttyUSB0
        """
        port = cls.find_radar_port()
        if not port:
            # Fallback to default ports based on platform
            if platform.system().lower() == 'windows':
                port = 'COM3'
            else:
                port = '/dev/ttyUSB0'
        
        return cls(com_port=port)

class PacketType(Enum):
    """Enum for different types of radar packets."""
    RAW = "raw"
    NORMALIZED = "normalized"

class XEPRadarConnector:
    """Python implementation of X4 radar communication."""
    
    def __init__(self, config: RadarConfig):
        """Initialize the radar connector with given configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # State management
        self._is_open = False
        self._num_samplers = 0
        self._x4_down_converter = False
        
        # Connection object
        self._serial = None
        
        # Initialize connection
        self._connect()

    def _connect(self) -> None:
        """Establish initial connection to the radar."""
        for attempt in range(self.config.retry_attempts):
            try:
                self._serial = serial.Serial(
                    port=self.config.com_port,
                    baudrate=self.config.baudrate,
                    timeout=self.config.timeout
                )
                
                # Set control signals
                self._serial.dtr = True
                self._serial.rts = True
                
                # Initialize handle
                self._write_command("NVA_CreateHandle()")
                self._read_response()
                return
                
            except serial.SerialException as e:
                self.logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.config.retry_attempts - 1:
                    raise ConnectionError("Failed to establish connection") from e

    def open(self, connect_string: str) -> None:
        """Open connection to radar module."""
        if self._is_open:
            raise RadarError("Radar connection already open")
            
        self._write_command(f"OpenRadar({connect_string})")
        self._read_response()
        self._is_open = True
        self._update_samplers()

    def close(self) -> None:
        """Close radar connection."""
        if not self._is_open:
            return
            
        self._write_command("Close()")
        self._read_response()
        self._is_open = False
        if self._serial:
            self._serial.close()
            self._serial = None

    def get_frame_raw(self) -> np.ndarray:
        """Get raw frame data from radar."""
        self._write_command("GetFrameRaw()")
        frame = self._read_frame(PacketType.RAW)
        return self._process_frame(frame)

    def get_frame_normalized(self) -> np.ndarray:
        """Get normalized frame data from radar."""
        self._write_command("GetFrameNormalized()")
        frame = self._read_frame(PacketType.NORMALIZED)
        return self._process_frame(frame)

    def update_chip(self, register_name: str, value: Union[int, float]) -> None:
        """Update register value on the radar chip."""
        if register_name in ['ddc_en', 'DownConvert']:
            self._x4_down_converter = bool(value)
            
        cmd = f"VarSetValue_ByName({register_name},{value})"
        self._write_command(cmd)
        self._read_response()
        self._update_samplers()

    def _write_command(self, command: str) -> None:
        """Write command to serial port."""
        if not self._serial:
            raise ConnectionError("Serial connection not established")
        self._serial.write(command.encode() + b'\n')

    def _read_response(self) -> bytes:
        """Read and validate response from radar."""
        response = bytearray()
        while True:
            if not self._serial.in_waiting:
                continue
                
            byte = self._serial.read()
            response.extend(byte)
            
            if len(response) >= 5 and response[-5:] == b'<ACK>':
                return response[:-5]
                
            if len(response) >= 5 and response[:5] == b'<ERR>':
                error_msg = response[5:].decode().strip()
                raise ProtocolError(f"Radar error: {error_msg}")

    def _read_frame(self, packet_type: PacketType) -> bytes:
        """Read a frame from the radar."""
        frame_data = bytearray()
        while True:
            if not self._serial.in_waiting:
                continue
                
            byte = self._serial.read()
            frame_data.extend(byte)
            
            # Check for frame end marker
            if len(frame_data) >= 5 and frame_data[-5:] == b'<ACK>':
                return frame_data[:-5]
                
            if len(frame_data) >= 5 and frame_data[:5] == b'<ERR>':
                error_msg = frame_data[5:].decode().strip()
                raise ProtocolError(f"Radar error during frame read: {error_msg}")

    def _process_frame(self, frame: bytes) -> np.ndarray:
        """Process raw frame data into numpy array."""
        data = np.frombuffer(frame, dtype=np.float32)
        
        if self._x4_down_converter:
            # Convert to complex I/Q data
            return data[::2] + 1j * data[1::2]
        return data

    def _update_samplers(self) -> None:
        """Update the number of samplers from radar."""
        self._write_command("VarGetValue_ByName(SamplersPerFrame)")
        response = self._read_response()
        self._num_samplers = int(response.decode())

    @contextmanager
    def connection(self, connect_string: str):
        """Context manager for radar connection."""
        try:
            self.open(connect_string)
            yield self
        finally:
            self.close()

    @property
    def is_open(self) -> bool:
        """Check if radar connection is open."""
        return self._is_open

    @property
    def samplers_per_frame(self) -> int:
        """Get number of samplers per frame."""
        return self._num_samplers