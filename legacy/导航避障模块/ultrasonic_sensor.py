# coding: utf-8
# 超声波避障传感器驱动模块 - 基于DYP-A02-V2.0和RDKX5 UART3通信
# 实现UART3串口通信、距离数据解析、安全阈值判断和避障策略

import time
import serial
import threading
import statistics
from config import get_navigation_config, get_uart_config, get_avoidance_config, get_system_config

class UltrasonicSensor:
    """超声波避障传感器驱动类 - 复用传感器模块串口通信架构"""
    
    def __init__(self):
        # 传感器配置 - 复用配置管理模式
        self.config = get_navigation_config()['ULTRASONIC']
        self.uart_config = get_uart_config()
        self.avoidance_config = get_avoidance_config()
        self.system_config = get_system_config()
        
        # 串口连接参数 - 复用传感器模块连接模式
        self.port = self.config['uart_port']  # UART3串口设备
        self.baudrate = self.config['baudrate']  # 波特率9600
        self.ser = None
        self.connected = False
        
        # 传感器数据
        self.distance = 0  # 当前距离值(毫米)
        self.valid = False  # 数据有效性标志
        self.timestamp = 0  # 数据时间戳
        self.last_distance = 0  # 上次测量距离
        self.measurement_count = 0  # 测量计数
        
        # 线程控制 - 复用GPS模块线程安全模式
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        
        # DYP-A02-V2.0参数配置
        self.safe_distance = self.config['safe_distance']  # 安全距离阈值(毫米)
        self.warning_distance = self.config['warning_distance']  # 警告距离阈值(毫米)
        self.measurement_range = self.config['measurement_range']  # 测量范围(30-4500mm)
        self.data_format = self.config['data_format']  # 数据格式标识
        
        # 避障策略配置
        self.avoidance_strategies = self.avoidance_config['avoidance_strategies']
        self.max_attempts = self.avoidance_config['max_avoidance_attempts']
        self.recovery_timeout = self.avoidance_config['recovery_timeout']
        
        # 数据缓冲区 - 用于滤波处理
        self.distance_buffer = []
        self.buffer_size = 5  # 缓冲区大小
        
        print(f"超声波传感器初始化完成 - {self.data_format} UART3:{self.port}")
    
    def connect(self):
        """连接超声波传感器串口 - 复用传感器连接模式"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.uart_config['timeout'],
                write_timeout=self.uart_config['write_timeout']
            )
            self.connected = self.ser.isOpen()
            if self.connected:
                print(f"超声波传感器已连接 {self.port} 波特率 {self.baudrate}")
                time.sleep(0.1)  # 等待串口稳定
            else:
                print("超声波传感器串口连接失败")
            return self.connected
        except Exception as e:
            print(f"超声波传感器连接错误: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开超声波传感器连接"""
        if self.ser and self.ser.isOpen():
            self.ser.close()
            self.connected = False
            print("超声波传感器已断开连接")
    
    def parse_distance_data(self, data):
        """解析DYP-A02-V2.0 UART自动输出数据格式: 0xFF+Data_H+Data_L+SUM"""
        if not data or len(data) != 4:
            return None
        
        # 检查帧头
        if data[0] != 0xFF:
            return None
        
        # 提取距离数据
        data_h = data[1]  # 距离数据高8位
        data_l = data[2]  # 距离数据低8位
        checksum = data[3]  # 校验和
        
        # 计算距离值(毫米)
        distance = (data_h << 8) + data_l
        
        # 校验和验证: SUM = (0xFF + Data_H + Data_L) & 0xFF
        calculated_checksum = (0xFF + data_h + data_l) & 0xFF
        
        if calculated_checksum == checksum:
            # 检查距离范围有效性
            if self.measurement_range[0] <= distance <= self.measurement_range[1]:
                return distance
            else:
                print(f"超声波距离超出范围: {distance}mm")
                return None
        else:
            print(f"超声波数据校验失败: 计算{calculated_checksum:02X} != 接收{checksum:02X}")
            return None
    
    def read_distance(self):
        """读取超声波距离数据 - DYP-A02-V2.0 UART自动输出模式"""
        if not self.connected:
            return None
        
        try:
            # DYP-A02-V2.0自动输出模式，每100ms输出一次数据
            if self.ser.in_waiting >= 4:
                data = self.ser.read(4)  # 读取4字节数据帧
                distance = self.parse_distance_data(data)
                
                if distance is not None:
                    with self._lock:
                        self.distance = distance
                        self.valid = True
                        self.timestamp = time.time()
                        self.measurement_count += 1
                        
                        # 更新距离缓冲区用于滤波
                        self.distance_buffer.append(distance)
                        if len(self.distance_buffer) > self.buffer_size:
                            self.distance_buffer.pop(0)
                    
                    return distance
                else:
                    self.valid = False
                    return None
            else:
                return None
                
        except Exception as e:
            print(f"超声波距离读取错误: {e}")
            self.valid = False
            return None
    
    def get_filtered_distance(self):
        """获取滤波后的距离数据 - 使用中值滤波减少噪声"""
        with self._lock:
            if len(self.distance_buffer) >= 3:
                # 使用中值滤波
                filtered_distance = statistics.median(self.distance_buffer)
                return filtered_distance
            elif self.valid:
                return self.distance
            else:
                return None
    
    def get_avoidance_action(self, distance=None):
        """根据距离判断避障动作 - 基于配置的避障策略"""
        if distance is None:
            distance = self.get_filtered_distance()
        
        if distance is None:
            return 'UNKNOWN'  # 无有效距离数据
        
        # 根据避障策略配置判断动作
        for strategy_name, strategy in self.avoidance_strategies.items():
            if distance <= strategy['distance']:
                return strategy['action']
        
        return 'NORMAL'  # 正常状态，无需避障
    
    def is_obstacle_detected(self, distance=None):
        """检测是否有障碍物 - 基于安全距离阈值"""
        if distance is None:
            distance = self.get_filtered_distance()
        
        if distance is None:
            return False
        
        return distance <= self.safe_distance
    
    def get_obstacle_level(self, distance=None):
        """获取障碍物威胁等级"""
        if distance is None:
            distance = self.get_filtered_distance()
        
        if distance is None:
            return 'UNKNOWN'
        
        if distance <= self.avoidance_strategies['immediate_stop']['distance']:
            return 'CRITICAL'  # 紧急停止
        elif distance <= self.avoidance_strategies['slow_approach']['distance']:
            return 'HIGH'  # 高威胁
        elif distance <= self.avoidance_strategies['turn_left']['distance']:
            return 'MEDIUM'  # 中等威胁
        elif distance <= self.warning_distance:
            return 'LOW'  # 低威胁
        else:
            return 'SAFE'  # 安全
    
    def start_monitoring(self):
        """启动超声波监测线程 - 复用传感器模块线程模式"""
        if self.running:
            return True
        
        if not self.connect():
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        print("超声波避障监测已启动")
        return True
    
    def stop_monitoring(self):
        """停止超声波监测"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=self.system_config['thread_timeout'])
        self.disconnect()
        print("超声波避障监测已停止")
    
    def _monitoring_loop(self):
        """超声波监测主循环 - 持续读取距离数据"""
        while self.running:
            try:
                distance = self.read_distance()
                if distance is not None:
                    action = self.get_avoidance_action(distance)
                    level = self.get_obstacle_level(distance)
                    
                    # 记录关键避障事件
                    if level in ['CRITICAL', 'HIGH']:
                        print(f"避障警告: 距离{distance}mm, 威胁等级{level}, 建议动作{action}")
                
                # 控制监测频率 - DYP-A02-V2.0自动输出100ms周期
                time.sleep(0.05)  # 50ms检查间隔，确保及时响应
                
            except Exception as e:
                print(f"超声波监测循环错误: {e}")
                time.sleep(0.1)
    
    def get_sensor_status(self):
        """获取传感器状态信息 - 复用传感器模块状态格式"""
        with self._lock:
            return {
                'connected': self.connected,
                'distance': self.distance,
                'valid': self.valid,
                'timestamp': self.timestamp,
                'measurement_count': self.measurement_count,
                'avoidance_action': self.get_avoidance_action(),
                'obstacle_level': self.get_obstacle_level(),
                'safe_distance': self.safe_distance,
                'warning_distance': self.warning_distance
            }
    
    def get_avoidance_api(self):
        """获取避障API接口 - 供导航系统调用"""
        return {
            'get_distance': self.get_filtered_distance,
            'get_action': self.get_avoidance_action,
            'is_obstacle': self.is_obstacle_detected,
            'get_level': self.get_obstacle_level,
            'get_status': self.get_sensor_status,
            'start': self.start_monitoring,
            'stop': self.stop_monitoring
        }

# 模块测试函数
def test_ultrasonic_sensor():
    """测试超声波传感器功能"""
    print("=== 超声波避障传感器测试 ===")
    
    sensor = UltrasonicSensor()
    
    # 测试连接
    if sensor.connect():
        print("✓ 串口连接成功")
        
        # 测试数据解析
        test_data = [0xFF, 0x07, 0xA1, 0xA7]  # 示例数据: 1953mm
        distance = sensor.parse_distance_data(test_data)
        print(f"✓ 数据解析测试: {distance}mm")
        
        # 测试避障策略
        test_distances = [500, 1000, 1500, 2000, 3000]
        for dist in test_distances:
            action = sensor.get_avoidance_action(dist)
            level = sensor.get_obstacle_level(dist)
            print(f"✓ 距离{dist}mm: 动作{action}, 威胁等级{level}")
        
        sensor.disconnect()
        print("✓ 测试完成")
    else:
        print("✗ 串口连接失败")

if __name__ == "__main__":
    test_ultrasonic_sensor()
