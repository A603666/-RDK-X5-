# coding: utf-8
# 水质传感器监测系统统一配置文件 - 基于地平线RDKX5开发板
# 复用现有定位模块配置管理架构，确保参数集中管理和易于维护

# 传感器硬件配置 - 基于RDKX5引脚映射，支持多种串口设备路径
SENSOR_CONFIG = {
    'PH_SENSOR': {
        'uart_port': '/dev/ttyS2',  # UART2串口设备
        'baudrate': 9600,  # 串口波特率
        'pin_tx': 15,  # UART2_TXD引脚
        'pin_rx': 22,  # UART2_RXD引脚
        'adc_pin': 'A0',  # ADC模拟输入引脚
        'enabled': True  # 传感器使能状态
    },
    'TDS_SENSOR': {
        'uart_port': '/dev/ttyS7',  # UART7串口设备
        'baudrate': 9600,  # 串口波特率
        'pin_tx': 11,  # UART7_TXD引脚
        'pin_rx': 13,  # UART7_RXD引脚
        'adc_pin': 'A1',  # ADC模拟输入引脚
        'enabled': True  # 传感器使能状态
    },
    'TURBIDITY_SENSOR': {
        'i2c_bus': 2,  # I2C2总线，对应/dev/i2c-2 (实际硬件配置)
        'i2c_address': 0x1c,  # 实际ADC芯片I2C地址
        'pin_sda': 27,  # I2C_SDA引脚
        'pin_scl': 28,  # I2C_SCL引脚
        'enabled': True  # 传感器使能状态
    },
    'DO_TEMP_SENSOR': {
        'uart_port': '/dev/ttyS6',  # UART6串口设备
        'baudrate': 9600,  # 串口波特率(默认9600)
        'pin_tx': 16,  # UART6_TXD引脚
        'pin_rx': 36,  # UART6_RXD引脚
        'rst_pin': 26,  # GPIO26复位引脚
        'modbus_address': 0x01,  # Modbus设备地址
        'enabled': True  # 传感器使能状态
    }
}

# 串口通信配置 - 复用定位模块串口参数模式
UART_CONFIG = {
    'timeout': 1.0,  # 串口读取超时时间(秒)
    'write_timeout': 1.0,  # 串口写入超时时间(秒)
    'buffer_size': 1024,  # 串口缓冲区大小
    'retry_count': 3,  # 通信重试次数
    'retry_delay': 0.1  # 重试间隔时间(秒)
}

# I2C总线配置 - 基于RDKX5 I2C规范
I2C_CONFIG = {
    'frequency': 100000,  # I2C时钟频率(100kHz)
    'timeout': 1.0,  # I2C操作超时时间(秒)
    'retry_count': 3,  # I2C操作重试次数
    'retry_delay': 0.1  # 重试间隔时间(秒)
}

# 传感器校准配置 - 基于Arduino例程校准参数
CALIBRATION_CONFIG = {
    'PH_SENSOR': {
        'voltage_4_0': 2335,  # 4.0标准液对应电压(mV)
        'voltage_6_86': 2000,  # 6.86标准液对应电压(mV)
        'voltage_9_18': 1870,  # 9.18标准液对应电压(mV)
        'adc_resolution': 1024,  # ADC分辨率
        'reference_voltage': 5.0,  # ADC参考电压(V)
        'filter_samples': 100  # 滤波采样数量
    },
    'TDS_SENSOR': {
        'reference_voltage': 5.0,  # ADC参考电压(V)
        'adc_resolution': 1024,  # ADC分辨率
        'temp_coefficient': 0.02,  # 温度补偿系数
        'reference_temp': 25.0,  # 参考温度(℃)
        'conversion_factor': 0.5,  # TDS转换系数
        'filter_samples': 30  # 滤波采样数量
    },
    'TURBIDITY_SENSOR': {
        'reference_voltage': 3.3,  # 参考电压(V) - 根据实际硬件调整
        'adc_resolution': 4095,  # 12位ADC分辨率 (0x1c设备推测)
        'temp_coefficient': -0.0192,  # 温度补偿系数
        'reference_temp': 25.0,  # 参考温度(℃)
        'slope': -865.68,  # 线性转换斜率
        'offset': 3347.19,  # 线性转换偏移量
        'max_value': 3000  # 最大测量值(NTU)
    },
    'DO_TEMP_SENSOR': {
        'temp_register': 0x0001,  # 温度寄存器地址
        'do_register': 0x0002,  # 溶解氧寄存器地址
        'temp_scale': 0.1,  # 温度数据缩放因子(0.1℃)
        'do_scale': 0.01,  # 溶解氧数据缩放因子(0.01mg/L)
        'modbus_timeout': 1.0  # Modbus通信超时(秒)
    }
}

# 数据验证配置 - 复用web_frontend的阈值设置
DATA_VALIDATION_CONFIG = {
    'normal_ranges': {  # 正常数据范围
        'temperature': (0.0, 50.0),  # 温度范围(℃)
        'ph': (0.0, 14.0),  # pH范围
        'dissolved_oxygen': (0.0, 25.0),  # 溶解氧范围(mg/L)
        'tds': (0.0, 2000.0),  # TDS范围(ppm)
        'turbidity': (0.0, 4000.0)  # 浊度范围(NTU)
    },
    'alert_thresholds': {  # 告警阈值
        'temperature': (15.0, 35.0),  # 温度告警阈值
        'ph': (6.0, 9.0),  # pH告警阈值
        'dissolved_oxygen': (3.0, 20.0),  # 溶解氧告警阈值
        'tds': (50.0, 1000.0),  # TDS告警阈值
        'turbidity': (0.0, 100.0)  # 浊度告警阈值
    },
    'max_change_rate': {  # 最大变化率(每秒) - 调整为更宽松的阈值
        'temperature': 10.0,  # 温度最大变化率(℃/s)
        'ph': 3.0,  # pH最大变化率
        'dissolved_oxygen': 10.0,  # 溶解氧最大变化率(mg/L/s)
        'tds': 500.0,  # TDS最大变化率(ppm/s)
        'turbidity': 500.0  # 浊度最大变化率(NTU/s) - 大幅放宽
    }
}

# 系统运行配置 - 复用定位模块输出配置模式
SYSTEM_CONFIG = {
    'sampling_interval': 1.0,  # 数据采样间隔(秒)
    'print_interval': 1.0,  # 数据打印间隔(秒)
    'log_interval': 10.0,  # 数据记录间隔(秒)
    'max_log_files': 10,  # 最大日志文件数量
    'log_file_size': 10485760,  # 单个日志文件大小(10MB)
    'data_buffer_size': 1000,  # 数据缓冲区大小
    'thread_timeout': 5.0  # 线程操作超时时间(秒)
}

# 输出数据格式配置 - 确保与web_frontend兼容
OUTPUT_CONFIG = {
    'json_format': True,  # 启用JSON格式输出
    'timestamp_format': '%Y-%m-%d %H:%M:%S',  # 时间戳格式
    'decimal_places': 2,  # 数值保留小数位数
    'include_raw_data': False,  # 是否包含原始数据
    'include_status': True  # 是否包含传感器状态
}

# GPIO配置 - 基于Hobot.GPIO库规范
GPIO_CONFIG = {
    'mode': 'BOARD',  # GPIO编码模式(BOARD/BCM)
    'warnings': False,  # 禁用GPIO警告
    'cleanup_on_exit': True  # 退出时清理GPIO
}

# 设备检测和诊断配置 - RDKX5开发板专用
DEVICE_DETECTION_CONFIG = {
    'auto_detect_ports': True,  # 自动检测可用串口设备
    'check_permissions': True,  # 检查串口设备权限
    'fix_permissions': True,  # 自动修复权限问题
    'detection_timeout': 2.0,  # 设备检测超时时间(秒)
    'common_serial_paths': [  # RDKX5串口设备路径
        '/dev/ttyS0', '/dev/ttyS1', '/dev/ttyS2', '/dev/ttyS3', '/dev/ttyS4', '/dev/ttyS5', '/dev/ttyS6', '/dev/ttyS7',
        '/dev/ttyAMA0', '/dev/ttyAMA1', '/dev/ttyAMA2', '/dev/ttyAMA3', '/dev/ttyAMA4', '/dev/ttyAMA5', '/dev/ttyAMA6', '/dev/ttyAMA7',
        '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyUSB3'
    ],
    'required_groups': ['dialout', 'tty'],  # 串口访问所需的用户组
    'diagnostic_commands': [  # 诊断命令
        'ls -la /dev/tty*',
        'groups',
        'dmesg | grep -i serial',
        'lsmod | grep -i serial'
    ]
}
