# coding: utf-8


import os
import json
import logging
from typing import Dict, Any, Optional, Union

# 硬件平台配置 - 基于地平线RDKX5开发板
HARDWARE_CONFIG = {
    'platform': 'RDKX5',  # 硬件平台标识
    'board_type': 'Horizon_RDKX5',  # 开发板型号
    'gpio_library': 'Hobot.GPIO',  # GPIO库
    'pwm_chip_path': '/sys/class/pwm/pwmchip3/',  # PWM控制路径
    'i2c_buses': [0, 1, 2, 3],  # 可用I2C总线
    'uart_devices': [  # 可用UART设备
        '/dev/ttyS0', '/dev/ttyS1', '/dev/ttyS2', '/dev/ttyS3',
        '/dev/ttyS4', '/dev/ttyS5', '/dev/ttyS6', '/dev/ttyS7',
        '/dev/ttyAMA0', '/dev/ttyAMA1', '/dev/ttyAMA2', '/dev/ttyAMA3',
        '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyUSB3'
    ]
}

# 系统运行配置 - 统一各模块的系统配置
SYSTEM_CONFIG = {
    'sampling_interval': 1.0,  # 数据采样间隔(秒)
    'print_interval': 1.0,  # 数据打印间隔(秒)
    'log_interval': 10.0,  # 数据记录间隔(秒)
    'max_log_files': 10,  # 最大日志文件数量
    'log_file_size': 10485760,  # 单个日志文件大小(10MB)
    'data_buffer_size': 1000,  # 数据缓冲区大小
    'thread_timeout': 5.0,  # 线程操作超时时间(秒)
    'max_runtime': 7200,  # 最大连续运行时间(秒)
    'command_queue_size': 100,  # 命令队列大小
    'navigation_loop_interval': 0.1,  # 导航循环间隔(秒)
    'avoidance_check_interval': 0.05,  # 避障检查间隔(秒)
    'status_update_interval': 1.0  # 状态更新间隔(秒)
}

# 串口通信配置 - 统一各模块的串口参数
UART_CONFIG = {
    'timeout': 1.0,  # 串口读取超时时间(秒)
    'write_timeout': 1.0,  # 串口写入超时时间(秒)
    'buffer_size': 1024,  # 串口缓冲区大小
    'retry_count': 3,  # 通信重试次数
    'retry_delay': 0.1,  # 重试间隔时间(秒)
    'connection_check_interval': 5.0  # 连接状态检查间隔(秒)
}

# I2C通信配置 - 统一I2C总线参数
I2C_CONFIG = {
    'frequency': 100000,  # I2C时钟频率(100kHz)
    'timeout': 1.0,  # I2C操作超时时间(秒)
    'retry_count': 3,  # I2C操作重试次数
    'retry_delay': 0.1  # 重试间隔时间(秒)
}

# GPIO配置 - 基于Hobot.GPIO库规范
GPIO_CONFIG = {
    'mode': 'BOARD',  # GPIO编码模式(BOARD/BCM)
    'warnings': False,  # 禁用GPIO警告
    'cleanup_on_exit': True,  # 退出时清理GPIO
    'pin_validation': True  # 启用引脚验证
}

# 输出数据格式配置 - 统一各模块的输出格式
OUTPUT_CONFIG = {
    'json_format': True,  # 启用JSON格式输出
    'timestamp_format': '%Y-%m-%d %H:%M:%S',  # 时间戳格式
    'decimal_places': 2,  # 数值保留小数位数
    'coordinate_decimal_places': 6,  # 坐标保留小数位数
    'include_raw_data': False,  # 是否包含原始数据
    'include_status': True,  # 是否包含传感器状态
    'include_debug_info': False,  # 是否包含调试信息
    'response_format': {  # API响应格式
        'success': {'status': 'success', 'data': {}, 'message': ''},
        'error': {'status': 'error', 'error_code': '', 'message': ''}
    }
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

# 日志配置 - 统一日志管理
LOGGING_CONFIG = {
    'level': 'INFO',  # 日志级别
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 日志格式
    'file_path': 'logs/system.log',  # 日志文件路径
    'max_file_size': 10485760,  # 最大文件大小(10MB)
    'backup_count': 10,  # 备份文件数量
    'console_output': True,  # 是否输出到控制台
    'file_output': True  # 是否输出到文件
}

# 板端模块配置 - 整合各功能模块
BOARD_MODULES_CONFIG = {
    'sensor': {
        'name': '传感器模块',
        'enabled': True,
        'startup_delay': 2,
        'required': True,
        'config_section': 'sensors'
    },
    'positioning': {
        'name': '定位模块',
        'enabled': True,
        'startup_delay': 3,
        'required': True,
        'config_section': 'positioning'
    },
    'navigation': {
        'name': '导航避障模块',
        'enabled': True,
        'startup_delay': 4,
        'required': True,
        'config_section': 'navigation'
    },
    'ai_detection': {
        'name': 'AI检测模块',
        'enabled': True,
        'startup_delay': 5,
        'required': False,
        'config_section': 'ai_detection'
    },
    'motor_control': {
        'name': '电机控制模块',
        'enabled': True,
        'startup_delay': 1,
        'required': True,
        'config_section': 'motor_control'
    }
}

# PC端配置 - Web服务和API配置
PC_CONFIG = {
    'web_server': {
        'host': '0.0.0.0',  # Web服务器地址
        'port': 5001,  # Web服务器端口
        'debug': False,  # 调试模式
        'threaded': True  # 多线程模式
    },
    'api': {
        'cors_enabled': True,  # 启用CORS
        'rate_limiting': False,  # 速率限制
        'auth_required': False  # 是否需要认证
    },
    'ai_assistant': {
        'enabled': True,  # 启用AI助手
        'provider': 'coze',  # AI服务提供商
        'stream_response': True  # 流式响应
    },
    'data_processing': {
        'prediction_enabled': True,  # 启用预测功能
        'model_type': 'auto',  # 预测模型类型
        'update_interval': 60  # 数据更新间隔(秒)
    }
}

class ConfigManager:
    """配置管理器 - 提供配置加载、验证、环境变量覆盖功能"""
    
    def __init__(self):
        self.config = {}
        self.env_prefix = 'FISHERY_'  # 环境变量前缀
        self.logger = logging.getLogger(__name__)
        self._load_default_config()
        self._load_env_overrides()
    
    def _load_default_config(self):
        """加载默认配置"""
        self.config = {
            'hardware': HARDWARE_CONFIG,
            'system': SYSTEM_CONFIG,
            'uart': UART_CONFIG,
            'i2c': I2C_CONFIG,
            'gpio': GPIO_CONFIG,
            'output': OUTPUT_CONFIG,
            'safety': SAFETY_CONFIG,
            'logging': LOGGING_CONFIG,
            'board_modules': BOARD_MODULES_CONFIG,
            'pc': PC_CONFIG
        }
    
    def _load_env_overrides(self):
        """加载环境变量覆盖配置"""
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                config_key = key[len(self.env_prefix):].lower()
                try:
                    # 尝试解析为JSON
                    parsed_value = json.loads(value)
                    self._set_nested_config(config_key, parsed_value)
                except json.JSONDecodeError:
                    # 作为字符串处理
                    self._set_nested_config(config_key, value)
    
    def _set_nested_config(self, key_path: str, value: Any):
        """设置嵌套配置值"""
        keys = key_path.split('_')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """获取配置值"""
        try:
            if key is None:
                return self.config.get(section, default)
            return self.config.get(section, {}).get(key, default)
        except Exception as e:
            self.logger.error(f"获取配置失败: {section}.{key}, 错误: {e}")
            return default
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """设置配置值"""
        try:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
            return True
        except Exception as e:
            self.logger.error(f"设置配置失败: {section}.{key}, 错误: {e}")
            return False
    
    def validate(self) -> bool:
        """验证配置有效性"""
        try:
            # 验证硬件配置
            hardware = self.get('hardware')
            assert hardware['platform'] == 'RDKX5', "硬件平台配置错误"
            
            # 验证系统配置
            system = self.get('system')
            assert system['sampling_interval'] > 0, "采样间隔必须大于0"
            assert system['thread_timeout'] > 0, "线程超时时间必须大于0"
            
            # 验证串口配置
            uart = self.get('uart')
            assert uart['timeout'] > 0, "串口超时时间必须大于0"
            assert uart['retry_count'] >= 0, "重试次数不能为负数"
            
            return True
        except AssertionError as e:
            self.logger.error(f"配置验证失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"配置验证异常: {e}")
            return False
    
    def load_from_file(self, config_file: str) -> bool:
        """从文件加载配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # 合并配置
            for section, params in file_config.items():
                if section in self.config:
                    if isinstance(params, dict):
                        self.config[section].update(params)
                    else:
                        self.config[section] = params
                else:
                    self.config[section] = params
            
            return True
        except Exception as e:
            self.logger.error(f"从文件加载配置失败: {e}")
            return False
    
    def save_to_file(self, config_file: str) -> bool:
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"保存配置到文件失败: {e}")
            return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self.config.copy()

# 全局配置管理器实例
config_manager = ConfigManager()

# 便捷函数
def get_config(section: str, key: Optional[str] = None, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return config_manager.get(section, key, default)

def set_config(section: str, key: str, value: Any) -> bool:
    """设置配置值的便捷函数"""
    return config_manager.set(section, key, value)

def validate_config() -> bool:
    """验证配置的便捷函数"""
    return config_manager.validate()

def load_config_file(config_file: str) -> bool:
    """加载配置文件的便捷函数"""
    return config_manager.load_from_file(config_file)

def save_config_file(config_file: str) -> bool:
    """保存配置文件的便捷函数"""
    return config_manager.save_to_file(config_file)
