#!/usr/bin/env python3

import numpy as np
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
        
        # Ensure results directory exists
        os.makedirs('results', exist_ok=True)
        # Ensure results directory exists
        self.base_dir = 'results'
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Store timestamp for reference
        if timestamp is None:
            timestamp = datetime.now()
        self.timestamp = timestamp
        
    def initialize_reference_frame(self):
        """Initialize reference frame by averaging 10 frames"""
        frame_sum = np.zeros(self.radar.samplers_per_frame)
        for _ in range(10):
            frame_sum += np.abs(self.radar.get_frame_normalized())
        self.frame_0 = np.floor(frame_sum / 10)
            
    def configure_radar(self):
        """Configure radar parameters to match MATLAB settings"""
        self.radar.update_chip("rx_wait", 0)
        self.radar.update_chip("frame_start", 2)
        self.radar.update_chip("frame_end", 4)
        self.radar.update_chip("ddc_en", 0)
        self.radar.update_chip("tx_region", 3)
        self.radar.update_chip("tx_power", 3)
            
    def start_acquisition(self):
        """Start real-time data acquisition"""
        # Create data file with start time
        start_time = datetime.now()
        data_file = os.path.join(self.base_dir,
                               f'{start_time.strftime("%m_%d_%H%M%S")}_data.txt')
        print(f"Saving data to: {data_file}")
        
        try:
            import time
            print("Press Ctrl+C to stop data acquisition")
            while True:
                frame_data = np.abs(self.radar.get_frame_normalized()) - 255
                timestamp = datetime.now().strftime('%H:%M:%S.%f')
                frame_str = ' '.join(map(str, frame_data))
                with open(data_file, 'a') as f:
                    f.write(f"{timestamp} {frame_str}\n")
                time.sleep(0.05)  # 50ms interval, similar to previous animation
        except KeyboardInterrupt:
            print("\nData acquisition stopped by user")

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

def run_practical_test(port: str, timestamp=None, stop_event=None,
                       collect_duration: float = 2.0, interval: float = 10.0, total_duration: float = 30.0):
    """Run practical radar test
    
    Args:
        port: Serial port for radar connection
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
            
            try:
                # Option 1: Continuous data collection
                if collect_duration >= total_duration:
                    print("Running in continuous data collection mode")
                    radar_test.start_acquisition()
                # Option 2: Periodic data collection
                else:
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
    parser.add_argument('--collect-duration', type=float, default=5.0,
                      help='Duration of each collection round in seconds (default: 5.0)')
    parser.add_argument('--interval', type=float, default=30.0,
                      help='Time between start of each collection round in seconds (default: 30.0)')
    parser.add_argument('--total-duration', type=float, default=600.0,
                      help='Total duration of all collection rounds in seconds (default: 600.0)')
    args = parser.parse_args()
    
    # Create stop event for clean shutdown
    stop_event = Event()
    
    try:
        print("Running practical radar test with periodic collection...")
        print(f"Collection rounds: {args.collect_duration}s every {args.interval}s for {args.total_duration}s total")
        run_practical_test(args.port, stop_event=stop_event,
                         collect_duration=args.collect_duration,
                         interval=args.interval,
                         total_duration=args.total_duration)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        stop_event.set()  # Signal to stop data collection

if __name__ == "__main__":
    main()