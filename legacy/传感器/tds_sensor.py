# coding: utf-8
# TDS传感器驱动模块 
# 实现UART7串口通信、ADC数据读取、温度补偿算法，简化数据处理优先响应速度

import time
import serial
import threading
from config import SENSOR_CONFIG, UART_CONFIG, CALIBRATION_CONFIG, DATA_VALIDATION_CONFIG

class TDSSensor:
    """TDS传感器驱动类 - 复用定位模块串口通信架构，简化算法优先响应速度"""
    
    def __init__(self):
        # 传感器配置
        self.config = SENSOR_CONFIG['TDS_SENSOR']
        self.uart_config = UART_CONFIG
        self.calib_config = CALIBRATION_CONFIG['TDS_SENSOR']
        self.validation_config = DATA_VALIDATION_CONFIG
        
        # 串口连接参数
        self.port = self.config['uart_port']
        self.baudrate = self.config['baudrate']
        self.ser = None
        self.connected = False
        
        # 传感器数据
        self.tds_value = 0.0  # 当前TDS值(ppm)
        self.raw_voltage = 0.0  # 原始电压值
        self.compensated_voltage = 0.0  # 温度补偿后电压
        self.temperature = 25.0  # 当前温度(℃)
        self.valid = False  # 数据有效性标志
        self.timestamp = 0  # 数据时间戳
        self.last_value = 0.0  # 上次测量值
        
        # 线程控制 - 复用IMU模块线程安全模式
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        
        # 校准参数 - 基于Arduino例程
        self.reference_voltage = self.calib_config['reference_voltage']
        self.adc_resolution = self.calib_config['adc_resolution']
        self.temp_coefficient = self.calib_config['temp_coefficient']
        self.reference_temp = self.calib_config['reference_temp']
        self.conversion_factor = self.calib_config['conversion_factor']
        self.filter_samples = self.calib_config['filter_samples']  # 简化采样数量
    
    def connect(self):
        """连接TDS传感器串口 - 复用IMU连接模式"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.uart_config['timeout'],
                write_timeout=self.uart_config['write_timeout']
            )
            self.connected = self.ser.isOpen()
            if self.connected:
                print(f"TDS传感器已连接 {self.port} 波特率 {self.baudrate}")
            else:
                print("TDS传感器串口连接失败")
            return self.connected
        except Exception as e:
            print(f"TDS传感器连接错误: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开TDS传感器连接"""
        if self.ser and self.ser.isOpen():
            self.ser.close()
            self.connected = False
            print("TDS传感器已断开连接")
    
    def read_analog_data(self):
        """读取ADC模拟数据 - 简化处理优先响应速度"""
        if not self.connected:
            return None

        try:
            # 发送ADC读取命令
            self.ser.write(b"READ_TDS_ADC\r\n")
            time.sleep(0.01)  # 等待响应

            if self.ser.in_waiting:
                response = self.ser.readline().decode('ascii', errors='ignore').strip()
                try:
                    adc_value = int(response)
                    return adc_value
                except ValueError:
                    return None
            return None
        except Exception as e:
            print(f"TDS传感器ADC读取错误: {e}")
            return None
    
    def read_temperature(self):
        """读取环境温度 - 用于温度补偿"""
        try:
            # 发送温度读取命令
            self.ser.write(b"READ_TEMP\r\n")
            time.sleep(0.01)

            if self.ser.in_waiting:
                response = self.ser.readline().decode('ascii', errors='ignore').strip()
                try:
                    temp_value = float(response)
                    return temp_value
                except ValueError:
                    return self.reference_temp  # 默认25℃
            return self.reference_temp
        except Exception:
            return self.reference_temp  # 异常时返回默认温度
    
    def read_filtered_data(self):
        """读取简化滤波数据 - 移除中值滤波，使用简单平均"""
        adc_values = []
        
        # 简化采样 - 减少样本数量提高响应速度
        for i in range(self.filter_samples):
            adc_value = self.read_analog_data()
            if adc_value is not None:
                adc_values.append(adc_value)
            time.sleep(0.001)  # 1ms延时
        
        if len(adc_values) < 5:  # 至少需要5个有效样本
            return None
        
        # 简单平均滤波 - 移除复杂的中值滤波算法
        return sum(adc_values) / len(adc_values)
    
    def temperature_compensation(self, voltage, temperature):
        """温度补偿算法 - 基于Arduino公式"""
        # 温度补偿系数计算
        compensation_coefficient = 1.0 + self.temp_coefficient * (temperature - self.reference_temp)
        
        # 温度补偿后的电压
        compensated_voltage = voltage / compensation_coefficient
        
        return compensated_voltage
    
    def voltage_to_tds(self, compensated_voltage):
        """电压到TDS值转换 - 基于Arduino三次多项式公式"""
        # 三次多项式转换公式
        tds_value = (133.42 * compensated_voltage**3 - 
                    255.86 * compensated_voltage**2 + 
                    857.39 * compensated_voltage) * self.conversion_factor
        
        # 确保TDS值为正数
        return max(0.0, tds_value)
    
    def data_validation(self, tds_value):
        """数据验证和异常值检测"""
        if tds_value is None:
            return False
        
        # 范围检查
        min_tds, max_tds = self.validation_config['normal_ranges']['tds']
        if not (min_tds <= tds_value <= max_tds):
            print(f"TDS值超出正常范围: {tds_value}")
            return False
        
        # 变化率检查
        if self.last_value > 0:
            change_rate = abs(tds_value - self.last_value)
            max_change = self.validation_config['max_change_rate']['tds']
            if change_rate > max_change:
                print(f"TDS值变化过快: {change_rate}")
                return False
        
        return True
    
    def get_tds_value(self):
        """获取校准后的TDS值 - 标准接口"""
        with self._lock:  # 线程安全访问
            if not self.connected:
                return None
            
            # 读取温度
            self.temperature = self.read_temperature()
            
            # 读取滤波ADC数据
            adc_average = self.read_filtered_data()
            if adc_average is None:
                self.valid = False
                return None
            
            # ADC转电压
            voltage = adc_average * self.reference_voltage / self.adc_resolution
            self.raw_voltage = voltage
            
            # 温度补偿
            self.compensated_voltage = self.temperature_compensation(voltage, self.temperature)
            
            # 电压转TDS值
            tds_value = self.voltage_to_tds(self.compensated_voltage)
            
            # 数据验证
            if not self.data_validation(tds_value):
                self.valid = False
                return None
            
            # 更新传感器状态
            self.last_value = self.tds_value
            self.tds_value = tds_value
            self.timestamp = time.time()
            self.valid = True
            
            return tds_value
    
    def get_sensor_data(self):
        """获取完整传感器数据 - 标准化接口"""
        with self._lock:
            return {
                'sensor': 'tds',
                'value': self.tds_value,
                'unit': 'ppm',
                'temperature': self.temperature,
                'raw_voltage': self.raw_voltage,
                'compensated_voltage': self.compensated_voltage,
                'valid': self.valid,
                'timestamp': self.timestamp,
                'connected': self.connected
            }
    
    def start_monitoring(self):
        """启动TDS传感器监测线程"""
        if not self.connected:
            print("TDS传感器未连接，无法启动监测")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        print("TDS传感器监测线程已启动")
        return True
    
    def stop_monitoring(self):
        """停止TDS传感器监测"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        print("TDS传感器监测已停止")
    
    def _monitoring_loop(self):
        """TDS传感器监测循环 - 后台线程"""
        while self.running and self.connected:
            try:
                self.get_tds_value()  # 更新TDS值
                time.sleep(1.0)  # 1秒采样间隔
            except Exception as e:
                print(f"TDS传感器监测错误: {e}")
                time.sleep(1.0)
    
    def __del__(self):
        """析构函数 - 确保资源清理"""
        self.stop_monitoring()
        self.disconnect()
