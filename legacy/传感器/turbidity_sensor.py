# coding: utf-8
# 浊度传感器驱动模块 
# 实现I2C ADC数据读取、温度校准算法和线性转换公式

import time
import threading
try:
    from i2cdev import I2C  # RDKX5专用I2C库
except ImportError:
    try:
        import smbus as smbus_fallback  # 备用smbus库
        I2C = None
        print("警告: 未找到i2cdev库，使用smbus备用方案")
    except ImportError:
        print("错误: 未找到i2cdev或smbus库")
        raise
from config import SENSOR_CONFIG, I2C_CONFIG, CALIBRATION_CONFIG, DATA_VALIDATION_CONFIG

class TurbiditySensor:
    """浊度传感器驱动类 - 基于I2C2和0x1c ADC芯片"""

    def __init__(self):
        # 传感器配置
        self.config = SENSOR_CONFIG['TURBIDITY_SENSOR']
        self.i2c_config = I2C_CONFIG
        self.calib_config = CALIBRATION_CONFIG['TURBIDITY_SENSOR']
        self.validation_config = DATA_VALIDATION_CONFIG

        # I2C连接参数 - 0x1c ADC芯片
        self.i2c_bus = self.config.get('i2c_bus', 2)  # I2C2总线
        self.i2c_address = self.config.get('i2c_address', 0x1c)  # 实际ADC地址
        self.i2c = None  # I2C设备对象
        self.connected = False
        
        # 传感器数据
        self.turbidity_value = 0.0  # 当前浊度值(NTU)
        self.raw_voltage = 0.0  # 原始电压值
        self.calibrated_voltage = 0.0  # 温度校准后电压
        self.temperature = 25.0  # 当前温度(℃)
        self.valid = False  # 数据有效性标志
        self.timestamp = 0  # 数据时间戳
        self.last_value = 0.0  # 上次测量值
        
        # 线程控制 - 复用现有线程安全模式
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        
        # 校准参数 - 基于Arduino例程
        self.reference_voltage = self.calib_config['reference_voltage']
        self.adc_resolution = self.calib_config['adc_resolution']
        self.temp_coefficient = self.calib_config['temp_coefficient']
        self.reference_temp = self.calib_config['reference_temp']
        self.slope = self.calib_config['slope']  # -865.68
        self.offset = self.calib_config['offset']  # 3347.19
        self.max_value = self.calib_config['max_value']  # 3000 NTU
    
    def connect(self):
        """连接浊度传感器I2C总线 - 0x1c ADC芯片"""
        try:
            # 使用RDKX5推荐的i2cdev库
            if I2C is not None:
                # 使用i2cdev库 (RDKX5推荐方式)
                self.i2c = I2C(self.i2c_address, self.i2c_bus)
                # 测试连接 - 尝试读取1字节数据
                test_data = self.i2c.read(1)
                print(f"浊度传感器已连接 I2C{self.i2c_bus}(/dev/i2c-{self.i2c_bus}) 地址 0x{self.i2c_address:02X}")
            else:
                # 备用smbus方案
                self.i2c = smbus_fallback.SMBus(self.i2c_bus)
                test_data = self.i2c.read_byte(self.i2c_address)
                print(f"浊度传感器已连接(备用) I2C{self.i2c_bus} 地址 0x{self.i2c_address:02X}")

            self.connected = True
            return True
        except Exception as e:
            print(f"浊度传感器I2C连接错误: {e}")
            print(f"请检查: 1)硬件连接 2)I2C地址(0x{self.i2c_address:02X}) 3)I2C总线(/dev/i2c-{self.i2c_bus})")
            print(f"故障排除: 运行 'i2cdetect -y {self.i2c_bus}' 检查I2C设备")
            self.connected = False
            return False

    def disconnect(self):
        """断开浊度传感器I2C连接"""
        if self.i2c:
            if hasattr(self.i2c, 'close'):
                self.i2c.close()
            self.connected = False
            print("浊度传感器I2C已断开连接")
    
    def read_analog_value(self):
        """读取0x1c ADC数据 - 根据实际设备调整"""
        if not self.connected:
            return None

        try:
            if I2C is not None:
                # 使用i2cdev库读取数据
                # 先尝试读取2字节，如果失败则读取1字节
                try:
                    data = self.i2c.read(2)  # 尝试读取2字节
                    if len(data) >= 2:
                        adc_value = (data[0] << 8) | data[1]  # 16位数据
                    else:
                        adc_value = data[0]  # 8位数据
                except:
                    data = self.i2c.read(1)  # 备用：读取1字节
                    adc_value = data[0]
            else:
                # 备用smbus方案
                try:
                    data = self.i2c.read_i2c_block_data(self.i2c_address, 0x00, 2)
                    adc_value = (data[0] << 8) | data[1]
                except:
                    adc_value = self.i2c.read_byte(self.i2c_address)

            return adc_value
        except Exception as e:
            print(f"浊度传感器ADC读取错误: {e}")
            return None
    
    def read_temperature(self):
        """读取环境温度 - 用于温度校准，默认使用25℃"""
        # ADS1110A0仅提供ADC功能，温度需要外部传感器
        # 这里使用默认温度25℃，实际应用中可集成温度传感器
        return self.reference_temp  # 默认25℃
    
    def temperature_calibration(self, voltage, temperature):
        """温度校准算法 - 基于Arduino公式"""
        # 温度校准公式: TU_calibration = -0.0192*(temp_data-25) + TU
        calibrated_voltage = self.temp_coefficient * (temperature - self.reference_temp) + voltage
        
        return calibrated_voltage
    
    def voltage_to_ntu(self, calibrated_voltage):
        """电压到浊度值转换 - 基于Arduino线性公式"""
        # 线性转换公式: TU_value = -865.68 * TU_calibration + 3347.19
        turbidity_value = self.slope * calibrated_voltage + self.offset
        
        # 边界限制 - 复用Arduino边界检查
        if turbidity_value <= 0:
            turbidity_value = 0.0
        if turbidity_value >= self.max_value:
            turbidity_value = self.max_value
        
        return turbidity_value
    
    def data_validation(self, turbidity_value):
        """数据验证和异常值检测"""
        if turbidity_value is None:
            return False
        
        # 范围检查
        min_turbidity, max_turbidity = self.validation_config['normal_ranges']['turbidity']
        if not (min_turbidity <= turbidity_value <= max_turbidity):
            print(f"浊度值超出正常范围: {turbidity_value}")
            return False
        
        # 变化率检查
        if self.last_value > 0:
            change_rate = abs(turbidity_value - self.last_value)
            max_change = self.validation_config['max_change_rate']['turbidity']
            if change_rate > max_change:
                print(f"浊度值变化过快: {change_rate}")
                return False
        
        return True
    
    def get_turbidity_value(self):
        """获取校准后的浊度值 - 标准接口"""
        with self._lock:  # 线程安全访问
            if not self.connected:
                return None
            
            # 读取温度
            self.temperature = self.read_temperature()
            
            # 读取ADC数据
            adc_value = self.read_analog_value()
            if adc_value is None:
                self.valid = False
                return None
            
            # ADC转电压 - 根据实际设备规格调整
            voltage = adc_value * self.reference_voltage / self.adc_resolution
            self.raw_voltage = voltage
            
            # 温度校准
            self.calibrated_voltage = self.temperature_calibration(voltage, self.temperature)
            
            # 电压转浊度值
            turbidity_value = self.voltage_to_ntu(self.calibrated_voltage)
            
            # 数据验证
            if not self.data_validation(turbidity_value):
                self.valid = False
                return None
            
            # 更新传感器状态
            self.last_value = self.turbidity_value
            self.turbidity_value = turbidity_value
            self.timestamp = time.time()
            self.valid = True
            
            return turbidity_value
    
    def get_sensor_data(self):
        """获取完整传感器数据 - 标准化接口"""
        with self._lock:
            return {
                'sensor': 'turbidity',
                'value': self.turbidity_value,
                'unit': 'NTU',
                'temperature': self.temperature,
                'raw_voltage': self.raw_voltage,
                'calibrated_voltage': self.calibrated_voltage,
                'valid': self.valid,
                'timestamp': self.timestamp,
                'connected': self.connected
            }
    
    def start_monitoring(self):
        """启动浊度传感器监测线程"""
        if not self.connected:
            print("浊度传感器未连接，无法启动监测")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        print("浊度传感器监测线程已启动")
        return True
    
    def stop_monitoring(self):
        """停止浊度传感器监测"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        print("浊度传感器监测已停止")
    
    def _monitoring_loop(self):
        """浊度传感器监测循环 - 后台线程"""
        while self.running and self.connected:
            try:
                self.get_turbidity_value()  # 更新浊度值
                time.sleep(1.0)  # 1秒采样间隔
            except Exception as e:
                print(f"浊度传感器监测错误: {e}")
                time.sleep(1.0)
    
    def __del__(self):
        """析构函数 - 确保资源清理"""
        self.stop_monitoring()
        self.disconnect()
