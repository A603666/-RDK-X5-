# coding: utf-8
# 无人船自主定位导航系统统一配置文件 - 基于地平线RDKX5开发板
# 复用现有传感器模块和电机驱动模块配置管理架构，确保参数集中管理和易于维护

# 导航系统硬件配置 - 基于RDKX5引脚映射和硬件规格
NAVIGATION_CONFIG = {
    'GPS_IMU': {
        'gps_port': '/dev/ttyUSB0',  # GPS串口设备(USB0)
        'gps_baudrate': 9600,  # GPS波特率
        'imu_port': '/dev/ttyUSB1',  # IMU串口设备(USB1)
        'imu_baudrate': 115200,  # IMU波特率
        'fusion_frequency': 100,  # 融合算法频率(Hz)
        'enabled': True  # GPS-IMU融合使能状态
    },
    'ULTRASONIC': {
        'uart_port': '/dev/ttyS3',  # UART3串口设备
        'baudrate': 9600,  # 串口波特率
        'pin_tx': 3,  # UART3_TXD引脚
        'pin_rx': 5,  # UART3_RXD引脚
        'data_format': 'DYP-A02-V2.0',  # 超声波模块型号
        'safe_distance': 1500,  # 安全距离阈值(毫米)
        'warning_distance': 3000,  # 警告距离阈值(毫米)
        'measurement_range': (30, 4500),  # 测量范围(毫米)
        'enabled': True  # 超声波避障使能状态
    },
    'BLUETOOTH': {
        'service_name': 'RDKX5_Navigation_Control',  # 蓝牙服务名称
        'device_path': '/dev/rfcomm0',  # 蓝牙设备路径
        'baudrate': 9600,  # 蓝牙串口波特率
        'timeout': 10.0,  # 通信超时时间(秒)
        'buffer_size': 1024,  # 通信缓冲区大小
        'coordinate_format': 'json',  # 坐标数据格式(json/text)
        'command_formats': {  # 支持的命令格式
            'text': ['TARGET:39.9142,116.4174,100', 'NAVIGATE:START', 'NAVIGATE:STOP'],
            'json': {'command': 'SET_TARGET', 'params': {'lat': 39.9142, 'lng': 116.4174, 'alt': 100}}
        },
        'enabled': True  # 蓝牙通信使能状态
    },
    'MOTOR_INTERFACE': {
        'api_module': '电机驱动模块.motor_control',  # 电机控制API模块路径
        'control_timeout': 5.0,  # 控制命令超时时间(秒)
        'emergency_stop_enabled': True,  # 紧急停止使能
        'speed_levels': ['FAST', 'MEDIUM', 'SLOW'],  # 支持的速度等级
        'directions': ['FORWARD', 'BACKWARD', 'LEFT', 'RIGHT', 'STOP'],  # 支持的运动方向
        'enabled': True  # 电机接口使能状态
    }
}

# PID控制器配置 - 导航控制算法参数
PID_CONFIG = {
    'HEADING_PID': {
        'kp': 1.0,  # 比例系数
        'ki': 0.1,  # 积分系数
        'kd': 0.05,  # 微分系数
        'output_limit': (-100, 100),  # 输出限制范围
        'integral_limit': (-50, 50),  # 积分限制范围
        'deadband': 2.0,  # 死区范围(度)
        'sample_time': 0.1  # 采样时间(秒)
    },
    'SPEED_PID': {
        'kp': 0.8,  # 比例系数
        'ki': 0.05,  # 积分系数
        'kd': 0.02,  # 微分系数
        'output_limit': (0, 100),  # 输出限制范围
        'integral_limit': (-30, 30),  # 积分限制范围
        'deadband': 0.5,  # 死区范围(米)
        'sample_time': 0.1  # 采样时间(秒)
    }
}

# 导航算法配置 - 路径规划和导航参数
NAVIGATION_ALGORITHM_CONFIG = {
    'target_precision': 5.0,  # 目标到达精度(米)
    'max_navigation_distance': 10000.0,  # 最大导航距离(米)
    'course_correction_threshold': 10.0,  # 航向修正阈值(度)
    'speed_reduction_distance': 50.0,  # 减速距离(米)
    'waypoint_tolerance': 10.0,  # 航点容差(米)
    'max_heading_error': 45.0,  # 最大航向误差(度)
    'coordinate_validation': {  # 坐标验证范围
        'latitude_range': (-90.0, 90.0),  # 纬度范围
        'longitude_range': (-180.0, 180.0),  # 经度范围
        'altitude_range': (-100.0, 1000.0)  # 高度范围(米)
    }
}

# 避障策略配置 - 安全避障参数
AVOIDANCE_CONFIG = {
    'priority_levels': {  # 任务优先级
        'emergency_stop': 1,  # 紧急停止(最高优先级)
        'obstacle_avoidance': 2,  # 避障
        'navigation_control': 3,  # 导航控制
        'medication_control': 4,  # 投药控制
        'system_management': 5,  # 系统管理
        'status_query': 6,  # 状态查询
        'communication': 7  # 通信(最低优先级)
    },
    'avoidance_strategies': {  # 避障策略
        'immediate_stop': {'distance': 500, 'action': 'STOP'},  # 立即停止(500mm)
        'slow_approach': {'distance': 1000, 'action': 'SLOW'},  # 减速接近(1000mm)
        'turn_left': {'distance': 1500, 'action': 'LEFT'},  # 左转避让(1500mm)
        'turn_right': {'distance': 1500, 'action': 'RIGHT'}  # 右转避让(1500mm)
    },
    'recovery_timeout': 10.0,  # 避障恢复超时时间(秒)
    'max_avoidance_attempts': 3  # 最大避障尝试次数
}

# 串口通信配置 - 复用传感器模块串口参数模式
UART_CONFIG = {
    'timeout': 1.0,  # 串口读取超时时间(秒)
    'write_timeout': 1.0,  # 串口写入超时时间(秒)
    'buffer_size': 1024,  # 串口缓冲区大小
    'retry_count': 3,  # 通信重试次数
    'retry_delay': 0.1,  # 重试间隔时间(秒)
    'connection_check_interval': 5.0  # 连接状态检查间隔(秒)
}

# 系统运行配置 - 复用电机驱动模块系统配置模式
SYSTEM_CONFIG = {
    'navigation_loop_interval': 0.1,  # 导航循环间隔(秒)
    'avoidance_check_interval': 0.05,  # 避障检查间隔(秒)
    'status_update_interval': 1.0,  # 状态更新间隔(秒)
    'log_interval': 10.0,  # 日志记录间隔(秒)
    'max_log_files': 10,  # 最大日志文件数量
    'log_file_size': 10485760,  # 单个日志文件大小(10MB)
    'thread_timeout': 5.0,  # 线程操作超时时间(秒)
    'max_runtime': 7200,  # 最大连续运行时间(秒)
    'command_queue_size': 100  # 命令队列大小
}

# 安全配置 - 系统安全参数和限制
SAFETY_CONFIG = {
    'emergency_stop_enabled': True,  # 启用紧急停止功能
    'max_speed_level': 'MEDIUM',  # 最大允许速度等级
    'safe_operation_radius': 1000.0,  # 安全操作半径(米)
    'collision_prevention': True,  # 启用碰撞预防
    'auto_return_enabled': True,  # 启用自动返回功能
    'battery_low_threshold': 20.0,  # 低电量阈值(%)
    'signal_loss_timeout': 30.0,  # 信号丢失超时时间(秒)
    'watchdog_timeout': 60.0  # 看门狗超时时间(秒)
}

# 状态机配置 - 导航系统状态管理
STATE_MACHINE_CONFIG = {
    'states': {  # 系统状态定义
        'IDLE': '待机状态',
        'INITIALIZING': '初始化状态',
        'NAVIGATING': '导航状态',
        'AVOIDING': '避障状态',
        'ARRIVED': '到达目标状态',
        'ERROR': '错误状态',
        'EMERGENCY_STOP': '紧急停止状态'
    },
    'state_transitions': {  # 状态转换规则
        'IDLE': ['INITIALIZING', 'ERROR'],
        'INITIALIZING': ['NAVIGATING', 'ERROR'],
        'NAVIGATING': ['AVOIDING', 'ARRIVED', 'ERROR', 'EMERGENCY_STOP'],
        'AVOIDING': ['NAVIGATING', 'ERROR', 'EMERGENCY_STOP'],
        'ARRIVED': ['IDLE', 'NAVIGATING'],
        'ERROR': ['IDLE'],
        'EMERGENCY_STOP': ['IDLE']
    },
    'default_state': 'IDLE',  # 默认状态
    'state_timeout': 300.0  # 状态超时时间(秒)
}

# 输出数据格式配置 - 确保与web_frontend兼容
OUTPUT_CONFIG = {
    'json_format': True,  # 启用JSON格式输出
    'timestamp_format': '%Y-%m-%d %H:%M:%S',  # 时间戳格式
    'decimal_places': 6,  # 坐标保留小数位数
    'include_status': True,  # 是否包含系统状态
    'include_debug_info': False,  # 是否包含调试信息
    'response_format': {  # API响应格式
        'success': {'status': 'success', 'data': {}, 'message': ''},
        'error': {'status': 'error', 'error_code': '', 'message': ''}
    }
}

# GPIO配置 - 基于Hobot.GPIO库规范
GPIO_CONFIG = {
    'mode': 'BOARD',  # GPIO编码模式(BOARD/BCM)
    'warnings': False,  # 禁用GPIO警告
    'cleanup_on_exit': True,  # 退出时清理GPIO
    'pin_validation': True  # 启用引脚验证
}

# 配置管理函数 - 复用电机驱动模块配置管理模式
def get_config():
    """获取完整配置字典 - 复用现有配置管理模式"""
    return {
        'navigation': NAVIGATION_CONFIG,
        'pid': PID_CONFIG,
        'algorithm': NAVIGATION_ALGORITHM_CONFIG,
        'avoidance': AVOIDANCE_CONFIG,
        'uart': UART_CONFIG,
        'system': SYSTEM_CONFIG,
        'safety': SAFETY_CONFIG,
        'state_machine': STATE_MACHINE_CONFIG,
        'output': OUTPUT_CONFIG,
        'gpio': GPIO_CONFIG
    }

def get_navigation_config():
    """获取导航硬件配置"""
    return NAVIGATION_CONFIG.copy()

def get_gps_imu_config():
    """获取GPS-IMU配置"""
    return NAVIGATION_CONFIG['GPS_IMU'].copy()

def get_ultrasonic_config():
    """获取超声波配置"""
    return NAVIGATION_CONFIG['ULTRASONIC'].copy()

def get_bluetooth_config():
    """获取蓝牙配置"""
    return NAVIGATION_CONFIG['BLUETOOTH'].copy()

def get_motor_interface_config():
    """获取电机接口配置"""
    return NAVIGATION_CONFIG['MOTOR_INTERFACE'].copy()

def get_pid_config():
    """获取PID控制器配置"""
    return PID_CONFIG.copy()

def get_heading_pid_config():
    """获取航向PID配置"""
    return PID_CONFIG['HEADING_PID'].copy()

def get_speed_pid_config():
    """获取速度PID配置"""
    return PID_CONFIG['SPEED_PID'].copy()

def get_algorithm_config():
    """获取导航算法配置"""
    return NAVIGATION_ALGORITHM_CONFIG.copy()

def get_avoidance_config():
    """获取避障配置"""
    return AVOIDANCE_CONFIG.copy()

def get_system_config():
    """获取系统配置"""
    return SYSTEM_CONFIG.copy()

def get_safety_config():
    """获取安全配置"""
    return SAFETY_CONFIG.copy()

def get_state_machine_config():
    """获取状态机配置"""
    return STATE_MACHINE_CONFIG.copy()

def get_uart_config():
    """获取串口配置"""
    return UART_CONFIG.copy()

def get_output_config():
    """获取输出配置"""
    return OUTPUT_CONFIG.copy()

def get_gpio_config():
    """获取GPIO配置"""
    return GPIO_CONFIG.copy()

def validate_config():
    """验证配置参数有效性"""
    try:
        # 验证GPS-IMU配置
        gps_imu = NAVIGATION_CONFIG['GPS_IMU']
        assert gps_imu['gps_port'].startswith('/dev/'), "GPS端口路径无效"
        assert gps_imu['imu_port'].startswith('/dev/'), "IMU端口路径无效"
        assert 1 <= gps_imu['fusion_frequency'] <= 1000, "融合频率必须在1-1000Hz范围内"

        # 验证超声波配置
        ultrasonic = NAVIGATION_CONFIG['ULTRASONIC']
        assert ultrasonic['uart_port'] == '/dev/ttyS3', "超声波必须使用UART3"
        assert ultrasonic['pin_tx'] == 3 and ultrasonic['pin_rx'] == 5, "超声波引脚配置错误"
        assert 100 <= ultrasonic['safe_distance'] <= 5000, "安全距离必须在100-5000mm范围内"

        # 验证PID参数
        for pid_type in ['HEADING_PID', 'SPEED_PID']:
            pid = PID_CONFIG[pid_type]
            assert 0 < pid['kp'] <= 10, f"{pid_type} Kp参数超出范围"
            assert 0 <= pid['ki'] <= 5, f"{pid_type} Ki参数超出范围"
            assert 0 <= pid['kd'] <= 2, f"{pid_type} Kd参数超出范围"

        # 验证坐标范围
        coord_val = NAVIGATION_ALGORITHM_CONFIG['coordinate_validation']
        assert coord_val['latitude_range'] == (-90.0, 90.0), "纬度范围配置错误"
        assert coord_val['longitude_range'] == (-180.0, 180.0), "经度范围配置错误"

        return True
    except AssertionError as e:
        print(f"配置验证失败: {e}")
        return False
    except Exception as e:
        print(f"配置验证异常: {e}")
        return False

def update_config(section, key, value):
    """动态更新配置参数"""
    config_map = {
        'navigation': NAVIGATION_CONFIG,
        'pid': PID_CONFIG,
        'algorithm': NAVIGATION_ALGORITHM_CONFIG,
        'avoidance': AVOIDANCE_CONFIG,
        'uart': UART_CONFIG,
        'system': SYSTEM_CONFIG,
        'safety': SAFETY_CONFIG,
        'state_machine': STATE_MACHINE_CONFIG,
        'output': OUTPUT_CONFIG,
        'gpio': GPIO_CONFIG
    }

    if section in config_map and key in config_map[section]:
        config_map[section][key] = value
        return True
    return False

def load_custom_config(config_file_path):
    """加载自定义配置文件"""
    try:
        import json
        with open(config_file_path, 'r', encoding='utf-8') as f:
            custom_config = json.load(f)

        # 合并自定义配置
        for section, params in custom_config.items():
            if section in get_config():
                for key, value in params.items():
                    update_config(section, key, value)

        return True
    except Exception as e:
        print(f"加载自定义配置失败: {e}")
        return False
