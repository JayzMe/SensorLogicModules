#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from xep_radar_connector import XEPRadarConnector, RadarConfig
import sys
import platform

class RadarTest:
    def __init__(self, port: str):
        """Initialize RadarTest with port"""
        self.config = RadarConfig(com_port=port)
        self.radar = None
        self.fig = None
        self.ax = None
        self.line = None
        self.animation = None
        
    def initialize_plot(self):
        """Initialize matplotlib plot with proper configuration"""
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        frame_size = self.radar.samplers_per_frame
        self.line, = self.ax.plot(range(frame_size), np.zeros(frame_size))
        
        self.ax.set_title('Radar Time Waveform')
        self.ax.set_xlabel('Bin')
        self.ax.set_ylabel('Amplitude')
        self.ax.set_ylim([0, 15])  # Set y-axis range for normalized amplitude
        self.ax.grid(True)
        
    def update_plot(self, frame):
        """Update plot with new frame data"""
        try:
            frame_data = np.abs(self.radar.get_frame_normalized())
            self.line.set_ydata(frame_data)
            return self.line,
        except Exception as e:
            print(f"Error updating plot: {e}")
            plt.close()
            return self.line,
            
    def configure_radar(self):
        """Configure radar parameters"""
        # Match MATLAB vcom_test.m configuration
        self.radar.update_chip("rx_wait", 0)
        self.radar.update_chip("frame_start", 0)
        self.radar.update_chip("frame_end", 4.0)
        self.radar.update_chip("ddc_en", 1)
            
    def start_acquisition(self):
        """Start real-time data acquisition and plotting"""
        self.initialize_plot()
        
        # Create animation for real-time updates
        self.animation = FuncAnimation(
            self.fig,
            self.update_plot,
            interval=50,  # 50ms update interval
            blit=True,
            save_count=100  # Limit frame cache to last 100 frames
        )
        
        # Show plot (blocks until window is closed)
        plt.show()

def normalize_port(port: str) -> str:
    """
    Normalize port name to appropriate format based on platform and input.
    Handles both Windows (COM*) and Linux (/dev/tty*) style ports.
    """
    # If port is just a number, convert to appropriate format
    if port.isdigit():
        return f'COM{port}' if platform.system() == 'Windows' else f'/dev/ttyACM{int(port)-1}'
    
    # If it's already in the correct format, return as is
    if platform.system() == 'Windows':
        return port if port.upper().startswith('COM') else f'COM{port}'
    else:
        if port.upper().startswith('COM'):
            # Convert Windows style to Linux style
            num = int(''.join(filter(str.isdigit, port))) - 1
            return f'/dev/ttyACM{num}'
        elif not port.startswith('/dev/'):
            # Assume it's a Linux port number
            return f'/dev/ttyACM{int(port)-1}'
        return port

def run_radar_test(port: str):
    """Run radar test"""
    normalized_port = normalize_port(port)
    radar_test = RadarTest(normalized_port)
    
    # Use context manager for radar connection
    with XEPRadarConnector(radar_test.config).connection('X4') as radar:
        try:
            radar_test.radar = radar
            print(f"Connected to radar on {normalized_port}")
            print(f"Samplers per frame: {radar.samplers_per_frame}")
            
            radar_test.configure_radar()
            radar_test.start_acquisition()
            
        except Exception as e:
            print(f"Error during radar test: {e}")
            sys.exit(1)

def main():
    # Default to port 4 if no argument provided (matching MATLAB example)
    port = sys.argv[1] if len(sys.argv) > 1 else "4"
    
    try:
        print("Running radar test...")
        run_radar_test(port)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")

if __name__ == "__main__":
    main()