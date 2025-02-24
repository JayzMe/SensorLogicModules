#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from xep_radar_connector import XEPRadarConnector, RadarConfig
from datetime import datetime
import os
import sys
import platform
import argparse
from threading import Event

class PracticalRadarTest:
    def __init__(self, port: str, timestamp=None):
        """Initialize PracticalRadarTest with port"""
        self.config = RadarConfig(com_port=port)
        self.radar = None
        self.fig = None
        self.axes = []
        self.lines = []
        self.animation = None
        self.frame_0 = None
        self.Fs = 23.328  # GHz, matching MATLAB
        
        # Ensure results directory exists
        os.makedirs('results', exist_ok=True)
        # Ensure results directory exists
        self.base_dir = 'results'
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Store timestamp for reference
        if timestamp is None:
            timestamp = datetime.now()
        self.timestamp = timestamp
        
    def initialize_plots(self):
        """Initialize matplotlib plots with proper configuration"""
        self.fig, self.axes = plt.subplots(3, 1, figsize=(10, 12))
        frame_size = self.radar.samplers_per_frame
        
        # Time domain plot (subplot 1)
        ax1 = self.axes[0]
        h1 = ax1.plot(range(frame_size), np.zeros(frame_size))[0]
        ax1.set_title('Radar Time Waveform')
        ax1.set_xlabel('Bin')
        ax1.set_ylabel('Amplitude')
        ax1.set_xlim([0, frame_size])
        ax1.set_ylim([-5, 5])
        ax1.grid(True)
        self.lines.append(h1)
        
        # FFT magnitude plot (subplot 2)
        f = self.calculate_frequency_axis(frame_size)
        ax2 = self.axes[1]
        h2 = ax2.plot(f, np.zeros(frame_size))[0]
        ax2.set_title('FFT of the Signal')
        ax2.set_xlabel('Frequency (GHz)')
        ax2.set_ylabel('Magnitude')
        ax2.set_xlim([0, 12])
        ax2.set_ylim([0, 55])
        ax2.grid(True)
        self.lines.append(h2)
        
        # Phase plot (subplot 3)
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
        
    def initialize_reference_frame(self):
        """Initialize reference frame by averaging 10 frames"""
        frame_sum = np.zeros(self.radar.samplers_per_frame)
        for _ in range(10):
            frame_sum += np.abs(self.radar.get_frame_normalized())
        self.frame_0 = np.floor(frame_sum / 10)
        
    def update_plots(self, frame):
        """Update all plots with new frame data"""
        try:
            # Get frame data and process
            frame_data = np.abs(self.radar.get_frame_normalized())
            # frame_data = frame_data - self.frame_0
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
            
            # Log data with microsecond precision in plot mode
            if not hasattr(self, 'plot_file'):
                # Create plot file with start time on first update
                start_time = datetime.now()
                self.plot_file = os.path.join(self.base_dir,
                                            f'{start_time.strftime("%m_%d_%H%M%S")}_plot.txt')
                print(f"Saving plot data to: {self.plot_file}")
                
            timestamp = datetime.now().strftime('%H:%M:%S.%f')
            frame_str = ' '.join(map(str, frame_data))
            with open(self.plot_file, 'a') as f:
                f.write(f"{timestamp} {frame_str}\n")
            
            return self.lines
            
        except Exception as e:
            print(f"Error updating plots: {e}")
            plt.close()
            return self.lines
            
    def configure_radar(self):
        """Configure radar parameters to match MATLAB settings"""
        self.radar.update_chip("rx_wait", 0)
        self.radar.update_chip("frame_start", 2)
        self.radar.update_chip("frame_end", 4)
        self.radar.update_chip("ddc_en", 0)
        self.radar.update_chip("tx_region", 3)
        self.radar.update_chip("tx_power", 3)
            
    def start_acquisition(self):
        """Start real-time data acquisition and plotting"""
        self.initialize_plots()
        # self.initialize_reference_frame()
        
        # Create animation for real-time updates
        self.animation = FuncAnimation(
            self.fig,
            self.update_plots,
            interval=50,  # 50ms update interval
            blit=True,
            save_count=100
        )
        
        plt.show()

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

def run_practical_test(port: str, enable_plot: bool = True, timestamp=None, stop_event=None,
                      collect_duration: float = 2.0, interval: float = 10.0, total_duration: float = 30.0):
    """Run practical radar test
    
    Args:
        port: Serial port for radar connection
        enable_plot: Whether to enable real-time plotting (default: True)
        timestamp: Optional datetime object for file naming
        stop_event: Optional event to signal stopping data collection
        collect_duration: Duration of each collection round in seconds (default: 2.0)
        interval: Time between start of each collection round in seconds (default: 10.0)
        total_duration: Total duration of all collection rounds in seconds (default: 30.0)
    """
    normalized_port = normalize_port(port)
    radar_test = PracticalRadarTest(normalized_port, timestamp)
    
    with XEPRadarConnector(radar_test.config).connection('X4') as radar:
        try:
            radar_test.radar = radar
            print(f"Connected to radar on {normalized_port}")
            radar_test.configure_radar()
            print(f"Samplers per frame: {radar.samplers_per_frame}")
            print(f"Saving data to directory: {radar_test.base_dir}")
            print("Files will be named with format: MM_DD_HHMMSS.txt")
            
            if enable_plot:
                print("Running in continuous plot mode - data will be saved with '_plot' suffix")
                radar_test.start_acquisition()
            else:
                try:
                    import time
                    start_time = time.time()
                    round_num = 0
                    
                    while time.time() - start_time < total_duration:
                        if stop_event and stop_event.is_set():
                            print("\nData collection stopped by external signal")
                            break
                            
                        round_start = time.time()
                        round_start_time = datetime.now()
                        round_file = os.path.join(radar_test.base_dir,
                                                f'{round_start_time.strftime("%m_%d_%H%M%S")}.txt')
                        print(f"\nStarting collection round {round_num + 1}")
                        print(f"Saving to: {round_file}")
                        
                        # Collect data for collect_duration seconds
                        collection_end = round_start + collect_duration
                        while time.time() < collection_end:
                            if stop_event and stop_event.is_set():
                                break
                                
                            frame_data = np.abs(radar.get_frame_normalized()) - 255
                            timestamp = datetime.now().strftime('%H:%M:%S.%f')
                            frame_str = ' '.join(map(str, frame_data))
                            with open(round_file, 'a') as f:
                                f.write(f"{timestamp} {frame_str}\n")
                                
                        round_num += 1
                        
                        # Wait until next interval
                        next_round = round_start + interval
                        sleep_time = next_round - time.time()
                        if sleep_time > 0:
                            print(f"Waiting {sleep_time:.1f} seconds until next collection round...")
                            time.sleep(sleep_time)
                            
                    print(f"\nCompleted {round_num} collection rounds")
                    
                except KeyboardInterrupt:
                    print("\nData collection stopped by user")
            
        except Exception as e:
            print(f"Error during radar test: {e}")
            sys.exit(1)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Practical radar test with periodic data collection')
    parser.add_argument('--port', default="/dev/ttyACM0", help='Serial port (default: /dev/ttyACM0)')
    parser.add_argument('--no-plot', action='store_true', help='Disable real-time plotting')
    parser.add_argument('--collect-duration', type=float, default=2.0,
                      help='Duration of each collection round in seconds (default: 2.0)')
    parser.add_argument('--interval', type=float, default=10.0,
                      help='Time between start of each collection round in seconds (default: 10.0)')
    parser.add_argument('--total-duration', type=float, default=30.0,
                      help='Total duration of all collection rounds in seconds (default: 30.0)')
    args = parser.parse_args()
    
    # Create stop event for clean shutdown
    stop_event = Event()
    
    try:
        print("Running practical radar test with periodic collection...")
        print(f"Collection rounds: {args.collect_duration}s every {args.interval}s for {args.total_duration}s total")
        run_practical_test(args.port, not args.no_plot, stop_event=stop_event,
                         collect_duration=args.collect_duration,
                         interval=args.interval,
                         total_duration=args.total_duration)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        stop_event.set()  # Signal to stop data collection

if __name__ == "__main__":
    main()