# coding: utf-8
# PH传感器驱动模块
# 实现UART2串口通信、ADC数据读取、分段线性校准算法和异常值过滤

import time
import serial
import threading
import statistics
from config import SENSOR_CONFIG, UART_CONFIG, CALIBRATION_CONFIG, DATA_VALIDATION_CONFIG

class PHSensor:
    """PH传感器驱动类 - 复用定位模块串口通信架构"""
    
    def __init__(self):
        # 传感器配置
        self.config = SENSOR_CONFIG['PH_SENSOR']
        self.uart_config = UART_CONFIG
        self.calib_config = CALIBRATION_CONFIG['PH_SENSOR']
        self.validation_config = DATA_VALIDATION_CONFIG
        
        # 串口连接参数
        self.port = self.config['uart_port']
        self.baudrate = self.config['baudrate']
        self.ser = None
        self.connected = False
        
        # 传感器数据
        self.ph_value = 0.0  # 当前PH值
        self.raw_voltage = 0.0  # 原始电压值
        self.valid = False  # 数据有效性标志
        self.timestamp = 0  # 数据时间戳
        self.last_value = 0.0  # 上次测量值
        
        # 线程控制 - 复用GPS模块线程安全模式
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        
        # 校准参数 - 基于Arduino例程
        self.voltage_4_0 = self.calib_config['voltage_4_0']  # 4.0标准液电压
        self.voltage_6_86 = self.calib_config['voltage_6_86']  # 6.86标准液电压
        self.voltage_9_18 = self.calib_config['voltage_9_18']  # 9.18标准液电压
        self.adc_resolution = self.calib_config['adc_resolution']
        self.reference_voltage = self.calib_config['reference_voltage']
        self.filter_samples = self.calib_config['filter_samples']
    
    def connect(self):
        """连接PH传感器串口"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.uart_config['timeout'],
                write_timeout=self.uart_config['write_timeout']
            )
            self.connected = self.ser.isOpen()
            if self.connected:
                print(f"PH传感器已连接 {self.port} 波特率 {self.baudrate}")
            else:
                print("PH传感器串口连接失败")
            return self.connected
        except Exception as e:
            print(f"PH传感器连接错误: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开PH传感器连接"""
        if self.ser and self.ser.isOpen():
            self.ser.close()
            self.connected = False
            print("PH传感器已断开连接")
    
    def read_raw_data(self):
        """读取ADC原始数据 - 模拟Arduino的analogRead"""
        if not self.connected:
            return None

        try:
            # 模拟ADC读取 - 实际应用中需要通过串口或I2C读取ADC值
            # 这里使用串口发送命令获取ADC数据
            self.ser.write(b"READ_ADC\r\n")
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
            print(f"PH传感器ADC读取错误: {e}")
            return None
    
    def read_filtered_data(self):
        """读取滤波后的ADC数据 - 基于Arduino滤波算法"""
        adc_values = []
        
        # 采集多个样本进行滤波
        for i in range(self.filter_samples):
            adc_value = self.read_raw_data()
            if adc_value is not None:
                adc_values.append(adc_value)
            time.sleep(0.001)  # 1ms延时
        
        if len(adc_values) < 10:  # 至少需要10个有效样本
            return None
        
        # 排序并去除极值 - 复用Arduino算法
        adc_values.sort()
        # 去除前后20%的极值
        trim_count = len(adc_values) // 5
        if trim_count > 0:
            filtered_values = adc_values[trim_count:-trim_count]
        else:
            filtered_values = adc_values
        
        # 计算平均值
        return sum(filtered_values) / len(filtered_values)
    
    def calibrate_ph(self, adc_average):
        """PH值校准算法 - 严格按照Arduino例程实现"""
        if adc_average is None:
            return None
        
        # ADC转电压 - 基于Arduino公式
        voltage_mv = adc_average * self.reference_voltage * 1000 / self.adc_resolution
        self.raw_voltage = voltage_mv
        
        # 分段线性校准 - 复用Arduino分段算法
        if voltage_mv < self.voltage_6_86:
            # 大于6.86段的斜率计算
            k1 = 100 * (9.18 - 6.86) / (self.voltage_6_86 - self.voltage_9_18)
            ph_value = (self.voltage_6_86 - voltage_mv) * k1 + 686
        else:
            # 小于等于6.86段的斜率计算
            k2 = 100 * (6.86 - 4.0) / (self.voltage_4_0 - self.voltage_6_86)
            ph_value = 686 - (voltage_mv - self.voltage_6_86) * k2
        
        # 数值范围限制 - 复用Arduino边界检查
        if ph_value > 1410:  # 14.1*100
            ph_value = 1400
        if ph_value < 0:
            ph_value = 0
        
        return ph_value / 100.0  # 转换为实际PH值
    
    def data_validation(self, ph_value):
        """数据验证和异常值检测"""
        if ph_value is None:
            return False
        
        # 范围检查
        min_ph, max_ph = self.validation_config['normal_ranges']['ph']
        if not (min_ph <= ph_value <= max_ph):
            print(f"PH值超出正常范围: {ph_value}")
            return False
        
        # 变化率检查
        if self.last_value > 0:
            change_rate = abs(ph_value - self.last_value)
            max_change = self.validation_config['max_change_rate']['ph']
            if change_rate > max_change:
                print(f"PH值变化过快: {change_rate}")
                return False
        
        return True
    
    def get_ph_value(self):
        """获取校准后的PH值 - 标准接口"""
        with self._lock:  # 线程安全访问
            if not self.connected:
                return None
            
            # 读取滤波数据
            adc_average = self.read_filtered_data()
            if adc_average is None:
                self.valid = False
                return None
            
            # 校准PH值
            ph_value = self.calibrate_ph(adc_average)
            if ph_value is None:
                self.valid = False
                return None
            
            # 数据验证
            if not self.data_validation(ph_value):
                self.valid = False
                return None
            
            # 更新传感器状态
            self.last_value = self.ph_value
            self.ph_value = ph_value
            self.timestamp = time.time()
            self.valid = True
            
            return ph_value
    
    def get_sensor_data(self):
        """获取完整传感器数据 - 标准化接口"""
        with self._lock:
            return {
                'sensor': 'ph',
                'value': self.ph_value,
                'unit': 'pH',
                'raw_voltage': self.raw_voltage,
                'valid': self.valid,
                'timestamp': self.timestamp,
                'connected': self.connected
            }
    
    def start_monitoring(self):
        """启动PH传感器监测线程"""
        if not self.connected:
            print("PH传感器未连接，无法启动监测")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        print("PH传感器监测线程已启动")
        return True
    
    def stop_monitoring(self):
        """停止PH传感器监测"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        print("PH传感器监测已停止")
    
    def _monitoring_loop(self):
        """PH传感器监测循环 - 后台线程"""
        while self.running and self.connected:
            try:
                self.get_ph_value()  # 更新PH值
                time.sleep(1.0)  # 1秒采样间隔
            except Exception as e:
                print(f"PH传感器监测错误: {e}")
                time.sleep(1.0)
    
    def __del__(self):
        """析构函数 - 确保资源清理"""
        self.stop_monitoring()
        self.disconnect()
