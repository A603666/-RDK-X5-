# coding: utf-8
# 溶解氧温度传感器驱动模块 - 基于Modbus-RTU协议和RDKX5串口通信
# 实现UART6串口通信、RS485协议、Modbus-RTU数据解析、CRC校验和GPIO26复位控制

import time
import serial
import threading
try:
    import Hobot.GPIO as GPIO  # RDKX5 GPIO库
except ImportError:
    print("警告: Hobot.GPIO库未安装，GPIO功能将不可用")
    GPIO = None
from config import SENSOR_CONFIG, UART_CONFIG, CALIBRATION_CONFIG, DATA_VALIDATION_CONFIG

class DOTempSensor:
    """溶解氧温度传感器驱动类 - 基于Modbus-RTU协议和串口通信架构"""
    
    def __init__(self):
        # 传感器配置
        self.config = SENSOR_CONFIG['DO_TEMP_SENSOR']
        self.uart_config = UART_CONFIG
        self.calib_config = CALIBRATION_CONFIG['DO_TEMP_SENSOR']
        self.validation_config = DATA_VALIDATION_CONFIG
        
        # 串口连接参数
        self.port = self.config['uart_port']
        self.baudrate = self.config['baudrate']
        self.modbus_address = self.config['modbus_address']
        self.rst_pin = self.config['rst_pin']
        self.ser = None
        self.connected = False
        
        # 传感器数据
        self.dissolved_oxygen = 0.0  # 溶解氧值(mg/L)
        self.temperature = 0.0  # 温度值(℃)
        self.valid = False  # 数据有效性标志
        self.timestamp = 0  # 数据时间戳
        self.last_do_value = 0.0  # 上次溶解氧值
        self.last_temp_value = 0.0  # 上次温度值
        
        # 线程控制 - 复用GPS模块线程安全模式
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        
        # Modbus寄存器地址 - 基于说明书规范
        self.temp_register = self.calib_config['temp_register']  # 0x0001
        self.do_register = self.calib_config['do_register']  # 0x0002
        self.temp_scale = self.calib_config['temp_scale']  # 0.1℃
        self.do_scale = self.calib_config['do_scale']  # 0.01mg/L
        self.modbus_timeout = self.calib_config['modbus_timeout']
        
        # 初始化GPIO
        self._init_gpio()
    
    def _init_gpio(self):
        """初始化GPIO26复位引脚"""
        if GPIO is None:
            print("GPIO库不可用，跳过GPIO初始化")
            return
        
        try:
            GPIO.setmode(GPIO.BOARD)  # 使用BOARD编码模式
            GPIO.setup(self.rst_pin, GPIO.OUT, initial=GPIO.HIGH)  # 复位引脚设为输出高电平
            print(f"GPIO{self.rst_pin}复位引脚初始化成功")
        except Exception as e:
            print(f"GPIO初始化错误: {e}")
    
    def reset_sensor(self):
        """执行传感器复位操作"""
        if GPIO is None:
            print("GPIO库不可用，跳过复位操作")
            return
        
        try:
            GPIO.output(self.rst_pin, GPIO.LOW)  # 拉低复位引脚
            time.sleep(0.1)  # 保持100ms
            GPIO.output(self.rst_pin, GPIO.HIGH)  # 拉高复位引脚
            time.sleep(1.0)  # 等待传感器重启
            print("传感器复位完成")
        except Exception as e:
            print(f"传感器复位错误: {e}")
    
    def connect(self):
        """连接溶解氧温度传感器串口 - 复用GPS连接模式"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.uart_config['timeout'],
                write_timeout=self.uart_config['write_timeout'],
                bytesize=8,
                parity='N',
                stopbits=1
            )
            self.connected = self.ser.isOpen()
            if self.connected:
                print(f"溶解氧温度传感器已连接 {self.port} 波特率 {self.baudrate}")
                # 执行一次复位确保传感器正常
                self.reset_sensor()
            else:
                print("溶解氧温度传感器串口连接失败")
            return self.connected
        except Exception as e:
            print(f"溶解氧温度传感器连接错误: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开溶解氧温度传感器连接"""
        if self.ser and self.ser.isOpen():
            self.ser.close()
            self.connected = False
            print("溶解氧温度传感器已断开连接")
        
        # 清理GPIO资源
        if GPIO is not None:
            try:
                GPIO.cleanup()
            except:
                pass
    
    def crc_check(self, data):
        """CRC校验算法 - Modbus-RTU标准CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def modbus_read_registers(self, start_addr, count):
        """读取Modbus寄存器数据 - 基于说明书协议"""
        if not self.connected:
            return None

        try:
            # 构建Modbus读取命令帧
            cmd = bytearray([
                self.modbus_address,  # 设备地址
                0x03,  # 功能码(读保持寄存器)
                (start_addr >> 8) & 0xFF,  # 起始地址高字节
                start_addr & 0xFF,  # 起始地址低字节
                (count >> 8) & 0xFF,  # 寄存器数量高字节
                count & 0xFF  # 寄存器数量低字节
            ])

            # 计算CRC校验码
            crc = self.crc_check(cmd)
            cmd.append(crc & 0xFF)  # CRC低字节
            cmd.append((crc >> 8) & 0xFF)  # CRC高字节

            # 发送命令
            self.ser.write(cmd)
            time.sleep(0.1)  # 等待响应

            # 读取响应
            if self.ser.in_waiting:
                response = self.ser.read(self.ser.in_waiting)
                return self.parse_modbus_response(response)

            return None
        except Exception as e:
            print(f"Modbus读取错误: {e}")
            return None
    
    def parse_modbus_response(self, response):
        """解析Modbus响应数据"""
        if len(response) < 5:  # 最小响应长度
            return None
        
        try:
            # 检查设备地址和功能码
            if response[0] != self.modbus_address or response[1] != 0x03:
                return None
            
            # 获取数据字节数
            data_count = response[2]
            if len(response) < 3 + data_count + 2:  # 数据+CRC
                return None
            
            # 提取数据部分
            data_bytes = response[3:3+data_count]
            
            # 验证CRC
            crc_received = (response[-1] << 8) | response[-2]
            crc_calculated = self.crc_check(response[:-2])
            if crc_received != crc_calculated:
                print("CRC校验失败")
                return None
            
            # 解析16位寄存器数据
            registers = []
            for i in range(0, len(data_bytes), 2):
                if i + 1 < len(data_bytes):
                    reg_value = (data_bytes[i] << 8) | data_bytes[i + 1]
                    registers.append(reg_value)
            
            return registers
        except Exception as e:
            print(f"Modbus响应解析错误: {e}")
            return None
    
    def parse_do_temp_data(self, registers):
        """解析溶解氧和温度数据"""
        if not registers:
            return None, None
        
        try:
            if len(registers) >= 2:
                # 温度数据(寄存器0x0001) - 单位0.1℃
                temp_raw = registers[0]
                temperature = temp_raw * self.temp_scale
                
                # 溶解氧数据(寄存器0x0002) - 单位0.01mg/L
                do_raw = registers[1]
                dissolved_oxygen = do_raw * self.do_scale
                
                return dissolved_oxygen, temperature
            elif len(registers) == 1:
                # 单个寄存器数据
                return registers[0] * self.do_scale, None
            
            return None, None
        except Exception as e:
            print(f"数据解析错误: {e}")
            return None, None
    
    def data_validation(self, do_value, temp_value):
        """数据验证和异常值检测"""
        valid = True
        
        if do_value is not None:
            # 溶解氧范围检查
            min_do, max_do = self.validation_config['normal_ranges']['dissolved_oxygen']
            if not (min_do <= do_value <= max_do):
                print(f"溶解氧值超出正常范围: {do_value}")
                valid = False
            
            # 溶解氧变化率检查
            if self.last_do_value > 0:
                change_rate = abs(do_value - self.last_do_value)
                max_change = self.validation_config['max_change_rate']['dissolved_oxygen']
                if change_rate > max_change:
                    print(f"溶解氧值变化过快: {change_rate}")
                    valid = False
        
        if temp_value is not None:
            # 温度范围检查
            min_temp, max_temp = self.validation_config['normal_ranges']['temperature']
            if not (min_temp <= temp_value <= max_temp):
                print(f"温度值超出正常范围: {temp_value}")
                valid = False
            
            # 温度变化率检查
            if self.last_temp_value > 0:
                change_rate = abs(temp_value - self.last_temp_value)
                max_change = self.validation_config['max_change_rate']['temperature']
                if change_rate > max_change:
                    print(f"温度值变化过快: {change_rate}")
                    valid = False
        
        return valid
    
    def get_dissolved_oxygen(self):
        """获取溶解氧值 - 标准接口"""
        with self._lock:
            registers = self.modbus_read_registers(self.do_register, 1)
            if registers and len(registers) > 0:
                # 直接解析溶解氧数据
                do_raw = registers[0]
                do_value = do_raw * self.do_scale  # 0.01mg/L

                if do_value is not None and self.data_validation(do_value, None):
                    self.last_do_value = self.dissolved_oxygen
                    self.dissolved_oxygen = do_value
                    self.timestamp = time.time()
                    self.valid = True
                    return do_value
            self.valid = False
            return None
    
    def get_temperature(self):
        """获取温度值 - 标准接口"""
        with self._lock:
            registers = self.modbus_read_registers(self.temp_register, 1)
            if registers and len(registers) > 0:
                # 直接解析温度数据
                temp_raw = registers[0]
                temp_value = temp_raw * self.temp_scale  # 0.1℃

                if temp_value is not None and self.data_validation(None, temp_value):
                    self.last_temp_value = self.temperature
                    self.temperature = temp_value
                    self.timestamp = time.time()
                    self.valid = True
                    return temp_value
            self.valid = False
            return None
    
    def get_do_temp_values(self):
        """同时获取溶解氧和温度值 - 优化接口"""
        with self._lock:
            registers = self.modbus_read_registers(self.temp_register, 2)
            if registers and len(registers) >= 2:
                do_value, temp_value = self.parse_do_temp_data(registers)
                if (do_value is not None and temp_value is not None and
                    self.data_validation(do_value, temp_value)):
                    self.last_do_value = self.dissolved_oxygen
                    self.last_temp_value = self.temperature
                    self.dissolved_oxygen = do_value
                    self.temperature = temp_value
                    self.timestamp = time.time()
                    self.valid = True
                    return do_value, temp_value
            self.valid = False
            return None, None
    
    def get_sensor_data(self):
        """获取完整传感器数据 - 标准化接口"""
        with self._lock:
            return {
                'sensor': 'do_temp',
                'dissolved_oxygen': self.dissolved_oxygen,
                'temperature': self.temperature,
                'do_unit': 'mg/L',
                'temp_unit': '℃',
                'valid': self.valid,
                'timestamp': self.timestamp,
                'connected': self.connected
            }
    
    def start_monitoring(self):
        """启动传感器监测线程"""
        if not self.connected:
            print("溶解氧温度传感器未连接，无法启动监测")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        print("溶解氧温度传感器监测线程已启动")
        return True
    
    def stop_monitoring(self):
        """停止传感器监测"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        print("溶解氧温度传感器监测已停止")
    
    def _monitoring_loop(self):
        """传感器监测循环 - 后台线程"""
        while self.running and self.connected:
            try:
                self.get_do_temp_values()  # 同时更新溶解氧和温度值
                time.sleep(1.0)  # 1秒采样间隔
            except Exception as e:
                print(f"溶解氧温度传感器监测错误: {e}")
                time.sleep(1.0)
    
    def __del__(self):
        """析构函数 - 确保资源清理"""
        self.stop_monitoring()
        self.disconnect()
