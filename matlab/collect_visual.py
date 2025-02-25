#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from xep_radar_connector import XEPRadarConnector, RadarConfig
from datetime import datetime
import os
import platform
import argparse
import time

class RadarVisualizer:
    def __init__(self, port: str):
        """Initialize RadarVisualizer with port"""
        self.config = RadarConfig(com_port=port)
        self.radar = None
        self.fig = None
        self.axes = []
        self.lines = []
        self.animation = None
        self.Fs = 23.328  # GHz, matching MATLAB
        
        # Ensure results directory exists
        self.base_dir = 'results'
        os.makedirs(self.base_dir, exist_ok=True)
        
    def initialize_plots(self):
        """Initialize matplotlib plots with proper configuration"""
        self.fig, self.axes = plt.subplots(3, 1, figsize=(10, 12))
        frame_size = self.radar.samplers_per_frame
        
        # Time domain plot
        ax1 = self.axes[0]
        h1 = ax1.plot(range(frame_size), np.zeros(frame_size))[0]
        ax1.set_title('Radar Time Waveform')
        ax1.set_xlabel('Bin')
        ax1.set_ylabel('Amplitude')
        ax1.set_xlim([0, frame_size])
        ax1.set_ylim([-5, 5])
        ax1.grid(True)
        self.lines.append(h1)
        
        # FFT magnitude plot
        f = self.calculate_frequency_axis(frame_size)
        ax2 = self.axes[1]
        h2 = ax2.plot(f, np.zeros(frame_size))[0]
        ax2.set_title('FFT of the Signal')
        ax2.set_xlabel('Frequency (GHz)')
        ax2.set_ylabel('Magnitude')
        ax2.set_xlim([0, 12])
        ax2.set_ylim([0, 550])
        ax2.grid(True)
        self.lines.append(h2)
        
        # Phase plot
        ax3 = self.axes[2]
        h3 = ax3.plot(f, np.zeros(frame_size))[0]
        ax3.set_title('Phase of the Signal')
        ax3.set_xlabel('Frequency (GHz)')
        ax3.set_ylabel('Angle (degrees)')
        ax3.set_xlim([0, 12])
        ax3.set_ylim([-180, 180])
        ax3.grid(True)
        self.lines.append(h3)
        
        plt.tight_layout()
        
    def calculate_frequency_axis(self, frame_size):
        """Calculate frequency axis for FFT plots"""
        freq_bin = np.arange(0, frame_size) - frame_size/2
        freq_bin = freq_bin * self.Fs / frame_size
        return freq_bin*2.0/(100.0/78.0)
        
    def update_plots(self, frame):
        """Update all plots with new frame data"""
        try:
            # Get frame data and process
            frame_data = np.abs(self.radar.get_frame_normalized())
            frame_data = frame_data - 255  # Match MATLAB processing
            
            # Calculate FFT
            Y = np.fft.fft(frame_data)
            f = self.calculate_frequency_axis(len(frame_data))
            
            # Update time domain plot
            self.lines[0].set_ydata(frame_data)
            
            # Update FFT magnitude plot
            fft_mag = np.abs(Y)
            self.lines[1].set_ydata(fft_mag)
            
            # Update max frequency in title
            half = len(f) // 2
            max_idx = np.argmax(fft_mag[half:]) + half
            self.axes[1].set_title(f'FFT of the Signal: {abs(f[max_idx]):.1f} GHz, max: {fft_mag[max_idx]:.1f}')
            
            # Update phase plot
            self.lines[2].set_ydata(np.angle(Y, deg=True))
            
            # Log data
            timestamp = datetime.now().strftime('%H:%M:%S.%f')
            frame_str = ' '.join(map(str, frame_data))
            with open(self.get_log_filename(), 'a') as f:
                f.write(f"{timestamp} {frame_str}\n")
            
            return self.lines
            
        except Exception as e:
            print(f"Error updating plots: {e}")
            plt.close()
            return self.lines
            
    def configure_radar(self):
        """Configure radar parameters to match MATLAB settings"""
        self.radar.update_chip("rx_wait", 0)
        self.radar.update_chip("frame_start", 0)
        self.radar.update_chip("frame_end", 2)
        self.radar.update_chip("ddc_en", 0)
        self.radar.update_chip("tx_region", 3)
        self.radar.update_chip("tx_power", 3)
            
    def get_log_filename(self):
        """Get the current log filename"""
        if not hasattr(self, 'log_file'):
            start_time = datetime.now()
            self.log_file = os.path.join(self.base_dir,
                                       f'{start_time.strftime("%m_%d_%H%M%S")}_continuous.txt')
            print(f"Saving data to: {self.log_file}")
        return self.log_file
            
    def start_visualization(self):
        """Start continuous data visualization"""
        self.initialize_plots()
        
        # Create animation for real-time updates
        self.animation = FuncAnimation(
            self.fig,
            self.update_plots,
            interval=50,  # 50ms update interval
            blit=True,
            save_count=100  # Limit frame cache to last 100 frames
        )
        
        plt.show()
        
    def collect_data_only(self, duration=None):
        """Collect data without visualization
        
        Args:
            duration: Optional duration in seconds to collect data. If None, runs until interrupted.
        """
        print(f"Starting data collection without visualization...")
        print(f"Saving data to: {self.get_log_filename()}")
        
        start_time = time.time()
        try:
            while True:
                # Get frame data and process
                frame_data = np.abs(self.radar.get_frame_normalized())
                frame_data = frame_data - 255  # Match MATLAB processing
                
                # Calculate FFT (for logging purposes)
                Y = np.fft.fft(frame_data)
                f = self.calculate_frequency_axis(len(frame_data))
                
                # Find max frequency
                fft_mag = np.abs(Y)
                half = len(f) // 2
                max_idx = np.argmax(fft_mag[half:]) + half
                max_freq = abs(f[max_idx])
                
                # Log data
                timestamp = datetime.now().strftime('%H:%M:%S.%f')
                frame_str = ' '.join(map(str, frame_data))
                with open(self.get_log_filename(), 'a') as f:
                    f.write(f"{timestamp} {frame_str}\n")
                
                # Print status every second
                if int(time.time()) > int(start_time) and int(time.time()) % 5 == 0:
                    print(f"Collecting data... Max frequency: {max_freq:.1f} GHz, max magnitude: {fft_mag[max_idx]:.1f}")
                    start_time = time.time()
                
                # Check if duration is specified and elapsed
                if duration and (time.time() - start_time) > duration:
                    print(f"Collection completed after {duration} seconds")
                    break
                    
                # Small delay to prevent CPU overload
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("Data collection stopped by user")
        except Exception as e:
            print(f"Error during data collection: {e}")

def normalize_port(port: str) -> str:
    """Normalize port name based on platform"""
    if port.isdigit():
        return f'COM{port}' if platform.system() == 'Windows' else f'/dev/ttyACM{int(port)-1}'
    
    if platform.system() == 'Windows':
        return port if port.upper().startswith('COM') else f'COM{port}'
    else:
        if port.upper().startswith('COM'):
            num = int(''.join(filter(str.isdigit, port))) - 1
            return f'/dev/ttyACM{num}'
        elif not port.startswith('/dev/'):
            return f'/dev/ttyACM{int(port)-1}'
        return port

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Radar data collection and visualization tool')
    parser.add_argument('--port', type=str, default="/dev/ttyACM0",
                        help='Serial port for radar connection (default: /dev/ttyACM0)')
    parser.add_argument('--no-visual', action='store_true',
                        help='Disable visualization and only collect data')
    parser.add_argument('--duration', type=int, default=None,
                        help='Duration in seconds to collect data (default: run until interrupted)')
    args = parser.parse_args()
    
    # Use provided port
    normalized_port = normalize_port(args.port)
    visualizer = RadarVisualizer(normalized_port)
    
    with XEPRadarConnector(visualizer.config).connection('X4') as radar:
        try:
            visualizer.radar = radar
            print(f"Connected to radar on {normalized_port}")
            visualizer.configure_radar()
            print(f"Samplers per frame: {radar.samplers_per_frame}")
            
            if args.no_visual:
                # Run without visualization
                visualizer.collect_data_only(duration=args.duration)
            else:
                # Run with visualization
                print("Starting continuous visualization...")
                visualizer.start_visualization()
            
        except Exception as e:
            print(f"Error during operation: {e}")
            
if __name__ == "__main__":
    main()