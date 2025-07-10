# coding: utf-8
import serial
import threading
import time
import math
import CONFIG

class IMUModule:
    def __init__(self, port=CONFIG.IMU_PORT, baudrate=CONFIG.IMU_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        
        # IMU data
        self.acc = [0.0, 0.0, 0.0]      # Acceleration (g)
        self.gyro = [0.0, 0.0, 0.0]     # Angular velocity (deg/s)
        self.angle = [0.0, 0.0, 0.0]    # Euler angles (deg)
        self.valid = False
        self.timestamp = 0
        
        # Calibration data
        self.gyro_offset = [0.0, 0.0, 0.0]
        self.acc_offset = [0.0, 0.0, 0.0]
        self.angle_offset = [0.0, 0.0, 0.0]
        self.is_calibrated = False
        
        # Frame parsing state
        self.FrameState = 0
        self.Bytenum = 0
        self.CheckSum = 0
        self.ACCData = [0.0] * 8
        self.GYROData = [0.0] * 8
        self.AngleData = [0.0] * 8
        
        # Thread control
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
    
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.5)
            self.connected = self.ser.isOpen()
            if self.connected:
                print(f"IMU connected on {self.port} at {self.baudrate} baud")
            else:
                print("Failed to open IMU serial port")
            return self.connected
        except Exception as e:
            print(f"IMU connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        if self.ser and self.ser.isOpen():
            self.ser.close()
            self.connected = False
            print("IMU disconnected")
    
    def _get_acc(self, datahex):
        axl = datahex[0]
        axh = datahex[1]
        ayl = datahex[2]
        ayh = datahex[3]
        azl = datahex[4]
        azh = datahex[5]
        
        k_acc = 16.0
        acc_x = (axh << 8 | axl) / 32768.0 * k_acc
        acc_y = (ayh << 8 | ayl) / 32768.0 * k_acc
        acc_z = (azh << 8 | azl) / 32768.0 * k_acc
        
        if acc_x >= k_acc:
            acc_x -= 2 * k_acc
        if acc_y >= k_acc:
            acc_y -= 2 * k_acc
        if acc_z >= k_acc:
            acc_z -= 2 * k_acc
            
        return [acc_x, acc_y, acc_z]  # Return list instead of tuple

    def _get_gyro(self, datahex):
        wxl = datahex[0]
        wxh = datahex[1]
        wyl = datahex[2]
        wyh = datahex[3]
        wzl = datahex[4]
        wzh = datahex[5]
        
        k_gyro = 2000.0
        gyro_x = (wxh << 8 | wxl) / 32768.0 * k_gyro
        gyro_y = (wyh << 8 | wyl) / 32768.0 * k_gyro
        gyro_z = (wzh << 8 | wzl) / 32768.0 * k_gyro
        
        if gyro_x >= k_gyro:
            gyro_x -= 2 * k_gyro
        if gyro_y >= k_gyro:
            gyro_y -= 2 * k_gyro
        if gyro_z >= k_gyro:
            gyro_z -= 2 * k_gyro
            
        return [gyro_x, gyro_y, gyro_z]  # Return list instead of tuple

    def _get_angle(self, datahex):
        rxl = datahex[0]
        rxh = datahex[1]
        ryl = datahex[2]
        ryh = datahex[3]
        rzl = datahex[4]
        rzh = datahex[5]
        
        k_angle = 180.0
        angle_x = (rxh << 8 | rxl) / 32768.0 * k_angle
        angle_y = (ryh << 8 | ryl) / 32768.0 * k_angle
        angle_z = (rzh << 8 | rzl) / 32768.0 * k_angle
        
        if angle_x >= k_angle:
            angle_x -= 2 * k_angle
        if angle_y >= k_angle:
            angle_y -= 2 * k_angle
        if angle_z >= k_angle:
            angle_z -= 2 * k_angle
            
        return [angle_x, angle_y, angle_z]  # Return list instead of tuple
    
    def _due_data(self, inputdata):
        for data in inputdata:
            if self.FrameState == 0:  # When the state is not determined
                if data == 0x55 and self.Bytenum == 0:  # Frame header 1
                    self.CheckSum = data
                    self.Bytenum = 1
                    continue
                elif data == 0x51 and self.Bytenum == 1:  # Acceleration frame
                    self.CheckSum += data
                    self.FrameState = 1
                    self.Bytenum = 2
                elif data == 0x52 and self.Bytenum == 1:  # Angular velocity frame
                    self.CheckSum += data
                    self.FrameState = 2
                    self.Bytenum = 2
                elif data == 0x53 and self.Bytenum == 1:  # Angle frame
                    self.CheckSum += data
                    self.FrameState = 3
                    self.Bytenum = 2
            
            elif self.FrameState == 1:  # Acceleration frame
                if self.Bytenum < 10:  # Read 8 data
                    self.ACCData[self.Bytenum-2] = data
                    self.CheckSum += data
                    self.Bytenum += 1
                else:
                    if data == (self.CheckSum & 0xff):  # Verify checksum
                        with self._lock:
                            self.acc = self._get_acc(self.ACCData)
                    self.CheckSum = 0
                    self.Bytenum = 0
                    self.FrameState = 0
            
            elif self.FrameState == 2:  # Angular velocity frame
                if self.Bytenum < 10:
                    self.GYROData[self.Bytenum-2] = data
                    self.CheckSum += data
                    self.Bytenum += 1
                else:
                    if data == (self.CheckSum & 0xff):
                        with self._lock:
                            self.gyro = self._get_gyro(self.GYROData)
                    self.CheckSum = 0
                    self.Bytenum = 0
                    self.FrameState = 0
            
            elif self.FrameState == 3:  # Angle frame
                if self.Bytenum < 10:
                    self.AngleData[self.Bytenum-2] = data
                    self.CheckSum += data
                    self.Bytenum += 1
                else:
                    if data == (self.CheckSum & 0xff):
                        with self._lock:
                            self.angle = self._get_angle(self.AngleData)
                            self.timestamp = time.time()
                            
                            # Validate IMU data
                            max_gyro = max(abs(g) for g in self.gyro)
                            max_acc = max(abs(a) for a in self.acc)
                            
                            if (max_gyro <= CONFIG.IMU_MAX_GYRO and 
                                max_acc <= CONFIG.IMU_MAX_ACC):
                                self.valid = True
                            else:
                                self.valid = False
                    
                    self.CheckSum = 0
                    self.Bytenum = 0
                    self.FrameState = 0
    
    def _read_loop(self):
        while self.running and self.connected:
            try:
                if self.ser.in_waiting:
                    data = self.ser.read(self.ser.in_waiting)
                    self._due_data(data)
                time.sleep(0.001)  # Small delay to prevent CPU hogging
            except Exception as e:
                print(f"IMU read error: {e}")
                time.sleep(1)  # Wait before retrying
    
    def start(self):
        if not self.connected:
            if not self.connect():
                return False
        
        self.running = True
        self.thread = threading.Thread(target=self._read_loop)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.disconnect()
    
    def get_imu_data(self):
        with self._lock:
            return {
                'timestamp': self.timestamp,
                'acc': self.acc.copy(),
                'gyro': self.gyro.copy(),
                'angle': self.angle.copy(),
                'valid': self.valid
            }
    
    def calibrate_zero_point(self, samples=100, delay=0.01):
        """
        Calibrate IMU zero point by averaging multiple readings while stationary
        
        Args:
            samples: Number of samples to collect for averaging
            delay: Delay between samples in seconds
        
        Returns:
            bool: True if calibration was successful
        """
        if not self.connected:
            if not self.connect():
                print("Cannot calibrate: IMU not connected")
                return False
        
        print("IMU zero-point calibration started")
        print("Please keep the device completely stationary...")
        
        # Wait for initial stabilization
        time.sleep(1.0)
        
        # Collect samples
        gyro_samples = []
        acc_samples = []
        angle_samples = []
        
        for i in range(samples):
            with self._lock:
                if self.valid:
                    gyro_samples.append(self.gyro.copy())
                    acc_samples.append(self.acc.copy())
                    angle_samples.append(self.angle.copy())
            
            # Progress indicator
            if (i+1) % 20 == 0:
                print(f"Calibrating: {i+1}/{samples} samples collected")
                
            time.sleep(delay)
        
        # Calculate offsets if we have enough valid samples
        if len(gyro_samples) < samples * 0.8:  # At least 80% of expected samples
            print("Calibration failed: Not enough valid samples")
            return False
        
        # Calculate average offsets
        self.gyro_offset = [0.0, 0.0, 0.0]
        self.acc_offset = [0.0, 0.0, 0.0]
        self.angle_offset = [0.0, 0.0, 0.0]
        
        # Calculate average for gyro (should be zero when stationary)
        for axis in range(3):
            self.gyro_offset[axis] = sum(sample[axis] for sample in gyro_samples) / len(gyro_samples)
        
        # For accelerometer, we only offset X and Y, but keep Z affected by gravity
        for axis in range(2):  # Only X and Y
            self.acc_offset[axis] = sum(sample[axis] for sample in acc_samples) / len(acc_samples)
        
        # For angle, we record the initial orientation to be used as reference
        for axis in range(3):
            self.angle_offset[axis] = sum(sample[axis] for sample in angle_samples) / len(angle_samples)
        
        print("IMU zero-point calibration completed")
        print(f"Gyro offsets: {self.gyro_offset}")
        print(f"Acc offsets: {self.acc_offset}")
        print(f"Initial angles: {self.angle_offset}")
        
        self.is_calibrated = True
        return True

    def apply_calibration(self, raw_data, offsets):
        """Apply calibration offsets to raw data"""
        return [raw_data[i] - offsets[i] for i in range(len(raw_data))]

    def get_calibrated_imu_data(self):
        """Get IMU data with calibration applied"""
        with self._lock:
            if not hasattr(self, 'is_calibrated') or not self.is_calibrated:
                return self.get_imu_data()  # Return uncalibrated data
            
            # Apply calibration to gyro and accelerometer
            calibrated_gyro = self.apply_calibration(self.gyro, self.gyro_offset)
            calibrated_acc = self.apply_calibration(self.acc, self.acc_offset)
            
            # For angle, we calculate relative to initial orientation
            calibrated_angle = self.apply_calibration(self.angle, self.angle_offset)
            
            # Normalize yaw angle to 0-360 range
            if calibrated_angle[2] < 0:
                calibrated_angle[2] += 360
            
            return {
                'timestamp': self.timestamp,
                'acc': calibrated_acc,
                'gyro': calibrated_gyro,
                'angle': calibrated_angle,
                'raw_angle': self.angle.copy(),  # Keep raw angle for reference
                'valid': self.valid
            }
    
    def reset_calibration(self):
        """Reset calibration data"""
        self.gyro_offset = [0.0, 0.0, 0.0]
        self.acc_offset = [0.0, 0.0, 0.0]
        self.angle_offset = [0.0, 0.0, 0.0]
        self.is_calibrated = False
        print("IMU calibration reset")
        return True
    
    def set_calibration(self, gyro_offset, acc_offset, angle_offset):
        """Set calibration data manually"""
        self.gyro_offset = gyro_offset
        self.acc_offset = acc_offset
        self.angle_offset = angle_offset
        self.is_calibrated = True
        print("IMU calibration data set manually")
        return True
    
    def get_calibration_status(self):
        """Get calibration status and data"""
        return {
            'is_calibrated': self.is_calibrated,
            'gyro_offset': self.gyro_offset.copy() if self.is_calibrated else [0.0, 0.0, 0.0],
            'acc_offset': self.acc_offset.copy() if self.is_calibrated else [0.0, 0.0, 0.0],
            'angle_offset': self.angle_offset.copy() if self.is_calibrated else [0.0, 0.0, 0.0]
        }


# For standalone testing
if __name__ == "__main__":
    imu = IMUModule()
    imu.start()
    
    try:
        print("Starting IMU module test...")
        print("Press 'c' to calibrate, 'q' to quit")
        
        while True:
            # Check for keyboard input
            if input_available():
                key = read_key()
                if key.lower() == 'q':
                    print("Quitting...")
                    break
                elif key.lower() == 'c':
                    imu.calibrate_zero_point()
            
            # Get and display IMU data
            data = imu.get_calibrated_imu_data() if imu.is_calibrated else imu.get_imu_data()
            
            if data['valid']:
                print(f"\rTime: {time.strftime('%H:%M:%S')}", end='')
                print(f" | Acc (g): X={data['acc'][0]:.2f}, Y={data['acc'][1]:.2f}, Z={data['acc'][2]:.2f}", end='')
                print(f" | Gyro (°/s): X={data['gyro'][0]:.2f}, Y={data['gyro'][1]:.2f}, Z={data['gyro'][2]:.2f}", end='')
                print(f" | Angle (°): R={data['angle'][0]:.2f}, P={data['angle'][1]:.2f}, Y={data['angle'][2]:.2f}", end='')
                print(f" | Calibrated: {imu.is_calibrated}", end='    \r')
            else:
                print("\rWaiting for valid IMU data...", end='    \r')
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        pass
    finally:
        imu.stop()
        print("\nIMU module stopped")

# Helper functions for keyboard input (only used in standalone testing)
def input_available():
    """Check if input is available (platform dependent)"""
    import sys, os
    if os.name == 'nt':  # Windows
        import msvcrt
        return msvcrt.kbhit()
    else:  # Unix/Linux/MacOS
        import select
        r, _, _ = select.select([sys.stdin], [], [], 0)
        return r != []

def read_key():
    """Read a single keypress (platform dependent)"""
    import sys, os
    if os.name == 'nt':  # Windows
        import msvcrt
        return msvcrt.getch().decode('utf-8')
    else:  # Unix/Linux/MacOS
        import termios, tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
