# coding: utf-8
import time
import threading
import json
from GPS import GPSModule
from IMU import IMUModule
from fusion import KalmanFilter
import CONFIG

# 导入MQTT客户端
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    print("警告: paho-mqtt库未安装，MQTT功能将不可用")
    MQTT_AVAILABLE = False

class FusionSystem:
    def __init__(self):
        self.gps = GPSModule()
        self.imu = IMUModule()
        self.kf = KalmanFilter()
        
        self.running = False
        self.fusion_thread = None
        self.last_print_time = 0
        
        # API result
        self._lock = threading.Lock()
        self._latest_result = {
            'timestamp': 0,
            'latitude': 0.0,
            'longitude': 0.0,
            'altitude': 0.0,
            'speed': 0.0,
            'course': 0.0,
            'roll': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'pos_accuracy': 0.0,
            'heading_accuracy': 0.0,
            'valid': False
        }

        # MQTT客户端配置
        self.mqtt_client = None
        self.mqtt_enabled = MQTT_AVAILABLE
        self.mqtt_broker = 'localhost'  # MQTT broker地址
        self.mqtt_port = 1883  # MQTT broker端口
        self.mqtt_topic = 'navigation/position'  # 定位数据主题
        self._init_mqtt_client()

    def _init_mqtt_client(self):
        """初始化MQTT客户端"""
        if not self.mqtt_enabled:
            print("MQTT功能不可用，跳过MQTT客户端初始化")
            return

        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()  # 启动后台线程处理网络流量
            print(f"定位模块MQTT客户端已连接到 {self.mqtt_broker}:{self.mqtt_port}")
        except Exception as e:
            print(f"定位模块MQTT客户端连接失败: {e}")
            self.mqtt_enabled = False

    def start(self):
        """Start all modules and fusion thread"""
        print("Starting GPS-IMU fusion system...")
        
        # Start GPS module
        if not self.gps.start():
            print("Failed to start GPS module")
            return False
        
        # Start IMU module
        if not self.imu.start():
            print("Failed to start IMU module")
            self.gps.stop()
            return False
        
        # Perform IMU zero-point calibration
        print("Performing IMU calibration...")
        calibration_success = self.imu.calibrate_zero_point(samples=100)
        if not calibration_success:
            print("Warning: IMU calibration failed, continuing with uncalibrated data")
        
        # Start fusion thread
        self.running = True
        self.fusion_thread = threading.Thread(target=self._fusion_loop)
        self.fusion_thread.daemon = True
        self.fusion_thread.start()
        
        print("GPS-IMU fusion system started successfully")
        return True
    
    def stop(self):
        """Stop all modules and fusion thread"""
        print("Stopping GPS-IMU fusion system...")
        self.running = False
        
        if self.fusion_thread:
            self.fusion_thread.join(timeout=1.0)
        
        self.gps.stop()
        self.imu.stop()

        # 清理MQTT客户端
        self._cleanup_mqtt_client()

        print("GPS-IMU fusion system stopped")

    def _cleanup_mqtt_client(self):
        """清理MQTT客户端资源"""
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()  # 停止后台线程
                self.mqtt_client.disconnect()  # 断开连接
                print("定位模块MQTT客户端已断开连接")
            except Exception as e:
                print(f"定位模块MQTT客户端清理错误: {e}")

    def _fusion_loop(self):
        """Main fusion loop - runs in its own thread"""
        while self.running:
            try:
                current_time = time.time()
                
                # Get GPS data
                gps_data = self.gps.get_position()
                
                # Get calibrated IMU data
                imu_data = self.imu.get_calibrated_imu_data()
                
                # Predict next state using time update
                self.kf.predict(current_time)
                
                # Update with GPS data if valid
                if gps_data['valid']:
                    self.kf.update_gps(
                        gps_data['latitude'],
                        gps_data['longitude'],
                        gps_data['altitude'],
                        gps_data['speed'],
                        gps_data['course'],
                        gps_data['valid']
                    )
                
                # Update with IMU data if valid
                if imu_data['valid']:
                    # Access list elements directly
                    self.kf.update_imu(
                        imu_data['angle'][0],  # roll
                        imu_data['angle'][1],  # pitch
                        imu_data['angle'][2],  # yaw
                        imu_data['valid']
                    )
                
                # Get current state estimate
                state = self.kf.get_state()
                
                # Update latest result for API access
                with self._lock:
                    self._latest_result = {
                        'timestamp': current_time,
                        'latitude': state['latitude'],
                        'longitude': state['longitude'],
                        'altitude': state['altitude'],
                        'speed': state['speed'],
                        'course': state['course'],
                        'roll': state['roll'],
                        'pitch': state['pitch'],
                        'yaw': state['yaw'],
                        'pos_accuracy': state['pos_accuracy'],
                        'heading_accuracy': state['heading_accuracy'],
                        'valid': state['valid']
                    }
                
                # Print results and send MQTT data at specified interval
                if current_time - self.last_print_time >= CONFIG.PRINT_INTERVAL:
                    self._print_results()
                    self._send_mqtt_data()  # 发送MQTT定位数据
                    self.last_print_time = current_time
                
                # Small delay to prevent CPU hogging
                time.sleep(0.01)
                
            except Exception as e:
                print(f"Error in fusion loop: {e}")
                time.sleep(1.0)
    
    def _print_results(self):
        """Print current fusion results to terminal"""
        with self._lock:
            result = self._latest_result.copy()
        
        if not result['valid']:
            print("Waiting for valid data...")
            return
        
        print("\n===== GPS-IMU Fusion Results =====")
        print(f"Time: {time.strftime('%H:%M:%S')}")
        print(f"Position: {result['latitude']:.8f}°, {result['longitude']:.8f}°")
        print(f"Altitude: {result['altitude']:.2f}m")
        print(f"Speed: {result['speed'] * 3.6:.2f} km/h")
        print(f"Course: {result['course']:.2f}°")
        print(f"Attitude: Roll={result['roll']:.2f}°, Pitch={result['pitch']:.2f}°, Yaw={result['yaw']:.2f}°")
        print(f"Accuracy: Position={result['pos_accuracy']:.2f}m, Heading={result['heading_accuracy']:.2f}°")
        print("==================================\n")

    def _send_mqtt_data(self):
        """发送定位数据到MQTT主题"""
        if not self.mqtt_enabled or not self.mqtt_client:
            return

        try:
            # 获取当前定位数据
            with self._lock:
                position_data = self._latest_result.copy()

            # 只有在数据有效时才发送
            if not position_data['valid']:
                return

            # 添加卫星数量信息（如果GPS数据可用）
            gps_data = self.gps.get_position()
            if gps_data['valid']:
                position_data['satellites'] = gps_data.get('satellites', 0)
            else:
                position_data['satellites'] = 0

            # 发送到MQTT主题
            result = self.mqtt_client.publish(self.mqtt_topic, json.dumps(position_data))

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"定位数据已发送到MQTT主题: {self.mqtt_topic}")
            else:
                print(f"定位数据MQTT发送失败，错误码: {result.rc}")

        except Exception as e:
            print(f"定位数据MQTT发送错误: {e}")

    def get_position(self):
        """API method to get the latest fusion results"""
        with self._lock:
            return self._latest_result.copy()
    
    def recalibrate_imu(self):
        """Recalibrate IMU zero point on demand"""
        print("Recalibrating IMU zero point...")
        calibration_success = self.imu.calibrate_zero_point(samples=100)
        if calibration_success:
            print("IMU recalibration successful")
        else:
            print("IMU recalibration failed")
        return calibration_success
    
    def save_calibration(self, filename="imu_calibration.json"):
        """Save IMU calibration data to file"""
        if hasattr(self.imu, 'is_calibrated') and self.imu.is_calibrated:
            import json
            try:
                calibration_data = {
                    'gyro_offset': self.imu.gyro_offset,
                    'acc_offset': self.imu.acc_offset,
                    'angle_offset': self.imu.angle_offset,
                    'timestamp': time.time(),
                    'date': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                with open(filename, 'w') as f:
                    json.dump(calibration_data, f, indent=4)
                print(f"Calibration data saved to {filename}")
                return True
            except Exception as e:
                print(f"Error saving calibration data: {e}")
                return False
        else:
            print("No calibration data available to save")
            return False
    
    def load_calibration(self, filename="imu_calibration.json"):
        """Load IMU calibration data from file"""
        import json
        import os
        
        if not os.path.exists(filename):
            print(f"Calibration file {filename} not found")
            return False
        
        try:
            with open(filename, 'r') as f:
                calibration_data = json.load(f)
            
            self.imu.gyro_offset = calibration_data['gyro_offset']
            self.imu.acc_offset = calibration_data['acc_offset']
            self.imu.angle_offset = calibration_data['angle_offset']
            self.imu.is_calibrated = True
            
            print(f"Loaded calibration data from {filename}")
            print(f"Calibration date: {calibration_data['date']}")
            return True
        except Exception as e:
            print(f"Error loading calibration data: {e}")
            return False


class CommandLineInterface:
    """Simple command line interface for the fusion system"""
    
    def __init__(self, fusion_system):
        self.fusion = fusion_system
        self.running = False
        self.commands = {
            'help': self.show_help,
            'quit': self.quit,
            'exit': self.quit,
            'status': self.show_status,
            'recalibrate': self.recalibrate,
            'save': self.save_calibration,
            'load': self.load_calibration
        }
    
    def start(self):
        """Start the CLI in a separate thread"""
        self.running = True
        self.cli_thread = threading.Thread(target=self._cli_loop)
        self.cli_thread.daemon = True
        self.cli_thread.start()
    
    def _cli_loop(self):
        """Main CLI loop"""
        print("\nGPS-IMU Fusion System CLI")
        print("Type 'help' for available commands")
        
        while self.running:
            try:
                cmd = input("\n> ").strip().lower()
                if cmd in self.commands:
                    self.commands[cmd]()
                elif cmd:
                    print(f"Unknown command: {cmd}")
            except Exception as e:
                print(f"Error processing command: {e}")
    
    def show_help(self):
        """Show available commands"""
        print("\nAvailable commands:")
        print("  help        - Show this help message")
        print("  status      - Show current system status")
        print("  recalibrate - Recalibrate IMU zero point")
        print("  save        - Save IMU calibration to file")
        print("  load        - Load IMU calibration from file")
        print("  quit/exit   - Exit the program")
    
    def show_status(self):
        """Show current system status"""
        position = self.fusion.get_position()
        
        print("\nSystem Status:")
        print(f"GPS Connected: {self.fusion.gps.connected}")
        print(f"IMU Connected: {self.fusion.imu.connected}")
        print(f"IMU Calibrated: {hasattr(self.fusion.imu, 'is_calibrated') and self.fusion.imu.is_calibrated}")
        
        if position['valid']:
            print(f"\nCurrent Position:")
            print(f"  Latitude:  {position['latitude']:.8f}°")
            print(f"  Longitude: {position['longitude']:.8f}°")
            print(f"  Altitude:  {position['altitude']:.2f}m")
            print(f"  Speed:     {position['speed'] * 3.6:.2f} km/h")
            print(f"  Course:    {position['course']:.2f}°")
            print(f"  Roll:      {position['roll']:.2f}°")
            print(f"  Pitch:     {position['pitch']:.2f}°")
            print(f"  Yaw:       {position['yaw']:.2f}°")
        else:
            print("\nPosition data not yet valid")
    
    def recalibrate(self):
        """Recalibrate IMU"""
        print("Recalibrating IMU. Keep the device stationary...")
        self.fusion.recalibrate_imu()
    
    def save_calibration(self):
        """Save calibration data"""
        filename = input("Enter filename (default: imu_calibration.json): ").strip()
        if not filename:
            filename = "imu_calibration.json"
        self.fusion.save_calibration(filename)
    
    def load_calibration(self):
        """Load calibration data"""
        filename = input("Enter filename (default: imu_calibration.json): ").strip()
        if not filename:
            filename = "imu_calibration.json"
        self.fusion.load_calibration(filename)
    
    def quit(self):
        """Exit the program"""
        self.running = False
        print("Exiting CLI...")


if __name__ == "__main__":
    fusion_system = FusionSystem()
    
    try:
        if fusion_system.start():
            print("System started successfully")
            
            # Start command line interface
            cli = CommandLineInterface(fusion_system)
            cli.start()
            
            print("Press Ctrl+C to stop")
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nShutting down...")
        fusion_system.stop()
        print("System stopped")
