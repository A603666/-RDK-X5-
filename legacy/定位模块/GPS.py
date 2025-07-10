# coding: utf-8
import time
import serial
import re
import threading
import CONFIG

class GPSModule:
    def __init__(self, port=CONFIG.GPS_PORT, baudrate=CONFIG.GPS_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        
        # GPS data
        self.utctime = ''
        self.lat = 0.0
        self.lon = 0.0
        self.alt = 0.0
        self.speed_knots = 0.0
        self.speed_kph = 0.0
        self.course = 0.0
        self.satellites = 0
        self.valid = False
        self.timestamp = 0
        
        # Thread control
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
    
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate)
            self.connected = self.ser.isOpen()
            if self.connected:
                print(f"GPS connected on {self.port} at {self.baudrate} baud")
            else:
                print("Failed to open GPS serial port")
            return self.connected
        except Exception as e:
            print(f"GPS connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        if self.ser and self.ser.isOpen():
            self.ser.close()
            self.connected = False
            print("GPS disconnected")
    
    def _convert_to_degrees(self, nmea_data, direction):
        if not nmea_data:
            return 0.0
        
        try:
            # NMEA format: DDMM.MMMM for latitude or DDDMM.MMMM for longitude
            # For latitude, first 2 digits are degrees
            # For longitude, first 3 digits are degrees
            is_longitude = direction in ['E', 'W']
            deg_digits = 3 if is_longitude else 2
            
            if len(nmea_data) < deg_digits + 1:  # Need at least degree digits + 1 for minutes
                return 0.0
                
            deg = float(nmea_data[0:deg_digits])
            min = float(nmea_data[deg_digits:])
            result = deg + (min / 60.0)
            
            # Apply direction
            if direction in ['S', 'W']:
                result = -result
                
            return result
        except Exception as e:
            print(f"Error converting NMEA to degrees: {e}, data: {nmea_data}, direction: {direction}")
            return 0.0
    
    def _parse_gps_data(self, data):
        if not data:
            return False
            
        try:
            # Find GNGGA sentence
            gga_match = re.search(rb'G[NP]GGA.*?\r\n', data)
            if gga_match:
                gga = gga_match.group(0).decode('ascii', errors='ignore')
                gga_parts = gga.split(',')
                
                if len(gga_parts) >= 15:
                    self.utctime = gga_parts[1]
                    
                    # Position data
                    if gga_parts[2] and gga_parts[4]:  # Latitude and longitude are not empty
                        self.lat = self._convert_to_degrees(gga_parts[2], gga_parts[3])
                        self.lon = self._convert_to_degrees(gga_parts[4], gga_parts[5])
                        self.satellites = int(gga_parts[7]) if gga_parts[7] else 0
                        self.alt = float(gga_parts[9]) if gga_parts[9] else 0.0
                        
                        # Debug output to verify conversion
                        print(f"Raw GPS data - Lat: {gga_parts[2]}{gga_parts[3]}, Lon: {gga_parts[4]}{gga_parts[5]}")
                        print(f"Converted - Lat: {self.lat:.6f}, Lon: {self.lon:.6f}")
                        
                        # Validate data
                        if self.satellites >= CONFIG.GPS_MIN_SATELLITES:
                            self.valid = True
                        else:
                            self.valid = False
                    else:
                        self.valid = False
            
            # Find GNVTG sentence for speed and course
            vtg_match = re.search(rb'G[NP]VTG.*?\r\n', data)
            if vtg_match:
                vtg = vtg_match.group(0).decode('ascii', errors='ignore')
                vtg_parts = vtg.split(',')
                
                if len(vtg_parts) >= 10:
                    self.course = float(vtg_parts[1]) if vtg_parts[1] else 0.0
                    self.speed_knots = float(vtg_parts[5]) if vtg_parts[5] else 0.0
                    self.speed_kph = float(vtg_parts[7]) if vtg_parts[7] else 0.0
            
            self.timestamp = time.time()
            return self.valid
            
        except Exception as e:
            print(f"GPS parse error: {e}")
            self.valid = False
            return False
    
    def _read_loop(self):
        buffer = b''
        
        while self.running and self.connected:
            try:
                if self.ser.in_waiting:
                    data = self.ser.read(self.ser.in_waiting)
                    buffer += data
                    
                    # Process complete NMEA sentences
                    if b'\r\n' in buffer:
                        with self._lock:
                            self._parse_gps_data(buffer)
                        buffer = b''  # Clear buffer after processing
                
                time.sleep(0.01)  # Small delay to prevent CPU hogging
                
            except Exception as e:
                print(f"GPS read error: {e}")
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
    
    def get_position(self):
        with self._lock:
            return {
                'timestamp': self.timestamp,
                'latitude': self.lat,
                'longitude': self.lon,
                'altitude': self.alt,
                'speed': self.speed_kph / 3.6,  # Convert to m/s
                'course': self.course,
                'satellites': self.satellites,
                'valid': self.valid
            }

# For standalone testing
if __name__ == "__main__":
    gps = GPSModule()
    gps.start()
    
    try:
        while True:
            pos = gps.get_position()
            if pos['valid']:
                print(f"Time: {time.strftime('%H:%M:%S')}")
                print(f"Lat: {pos['latitude']:.8f}, Lon: {pos['longitude']:.8f}")
                print(f"Alt: {pos['altitude']:.1f}m, Speed: {pos['speed']*3.6:.1f}km/h")
                print(f"Course: {pos['course']:.1f}°, Satellites: {pos['satellites']}")
                print("-------------------")
            else:
                print("Waiting for valid GPS data...")
            time.sleep(1)
    except KeyboardInterrupt:
        gps.stop()
        print("GPS module stopped")
