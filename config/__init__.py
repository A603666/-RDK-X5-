# coding: utf-8

import os
import sys
from typing import Dict, Any, Optional

# 添加配置目录到Python路径
config_dir = os.path.dirname(os.path.abspath(__file__))
if config_dir not in sys.path:
    sys.path.insert(0, config_dir)

try:
    # 导入配置管理器
    from .global_config import (
        config_manager,
        get_config,
        set_config,
        validate_config,
        load_config_file,
        save_config_file,
        HARDWARE_CONFIG,
        SYSTEM_CONFIG,
        UART_CONFIG,
        I2C_CONFIG,
        GPIO_CONFIG,
        OUTPUT_CONFIG,
        SAFETY_CONFIG,
        LOGGING_CONFIG,
        BOARD_MODULES_CONFIG,
        PC_CONFIG
    )
    
    from .mqtt_config import (
        mqtt_config_manager,
        get_mqtt_connection_config,
        get_mqtt_topics,
        get_client_config,
        validate_message,
        validate_command,
        MQTT_CONNECTION_CONFIG,
        MQTT_TOPICS_CONFIG,
        MQTT_DATA_FORMAT_CONFIG,
        CONTROL_COMMAND_FORMAT,
        COMMAND_PRIORITY_CONFIG
    )
    
    from .system_logger import (
        system_logger,
        get_logger,
        set_log_level,
        log_system_startup,
        log_module_status,
        log_mqtt_traffic,
        log_error_with_context,
        cleanup_loggers,
        DEFAULT_LOG_CONFIG,
        MODULE_LOG_CONFIG
    )
    
    CONFIG_IMPORT_SUCCESS = True
    CONFIG_IMPORT_ERROR = None
    
except ImportError as e:
    CONFIG_IMPORT_SUCCESS = False
    CONFIG_IMPORT_ERROR = str(e)
    
    # 提供备用的空实现
    def get_config(*args, **kwargs):
        return {}
    
    def set_config(*args, **kwargs):
        return False
    
    def validate_config():
        return False
    
    def get_logger(name, module=None):
        import logging
        return logging.getLogger(name)

def initialize_config_system() -> bool:
    """初始化配置系统"""
    if not CONFIG_IMPORT_SUCCESS:
        print(f"配置系统导入失败: {CONFIG_IMPORT_ERROR}")
        return False
    
    try:
        # 验证全局配置
        if not validate_config():
            print("全局配置验证失败")
            return False
        
        # 初始化日志系统
        log_system_startup()
        logger = get_logger('config_init')
        logger.info("配置系统初始化成功")
        
        # 记录配置状态
        logger.info(f"硬件平台: {get_config('hardware', 'platform')}")
        logger.info(f"MQTT Broker: {get_mqtt_connection_config()['broker']['host']}")
        logger.info(f"日志级别: {get_config('logging', 'level')}")
        
        return True
        
    except Exception as e:
        print(f"配置系统初始化失败: {e}")
        return False

def get_module_config(module_name: str) -> Dict[str, Any]:
    """获取指定模块的完整配置"""
    if not CONFIG_IMPORT_SUCCESS:
        return {}
    
    try:
        # 基础配置
        config = {
            'hardware': get_config('hardware'),
            'system': get_config('system'),
            'uart': get_config('uart'),
            'i2c': get_config('i2c'),
            'gpio': get_config('gpio'),
            'output': get_config('output'),
            'safety': get_config('safety'),
            'logging': get_config('logging')
        }
        
        # 模块特定配置
        if module_name == 'sensor':
            # 传感器模块配置
            config.update({
                'mqtt_topics': {
                    'data_upload': get_mqtt_topics()['data_upload']['sensor_data']
                },
                'data_format': MQTT_DATA_FORMAT_CONFIG
            })
        
        elif module_name == 'positioning':
            # 定位模块配置
            config.update({
                'mqtt_topics': {
                    'data_upload': get_mqtt_topics()['data_upload']['position_data']
                },
                'data_format': MQTT_DATA_FORMAT_CONFIG
            })
        
        elif module_name == 'navigation':
            # 导航模块配置
            config.update({
                'mqtt_topics': {
                    'command_subscribe': [
                        get_mqtt_topics()['command_download']['navigation_control'],
                        get_mqtt_topics()['command_download']['emergency_control']
                    ],
                    'feedback_publish': get_mqtt_topics()['feedback']['navigation_feedback']
                },
                'command_format': CONTROL_COMMAND_FORMAT['navigation'],
                'priority_config': COMMAND_PRIORITY_CONFIG
            })
        
        elif module_name == 'ai_detection':
            # AI检测模块配置
            config.update({
                'mqtt_topics': {
                    'data_upload': get_mqtt_topics()['data_upload']['ai_detection']
                },
                'data_format': MQTT_DATA_FORMAT_CONFIG
            })
        
        elif module_name == 'motor_control':
            # 电机控制模块配置
            config.update({
                'mqtt_topics': {
                    'command_subscribe': [
                        get_mqtt_topics()['command_download']['medication_control'],
                        get_mqtt_topics()['command_download']['emergency_control']
                    ],
                    'feedback_publish': get_mqtt_topics()['feedback']['medication_feedback']
                },
                'command_format': CONTROL_COMMAND_FORMAT['medication'],
                'priority_config': COMMAND_PRIORITY_CONFIG
            })
        
        elif module_name == 'web_server':
            # Web服务器配置
            config.update({
                'pc_config': get_config('pc'),
                'mqtt_topics': get_mqtt_topics(),
                'client_config': get_client_config('pc')
            })
        
        return config
        
    except Exception as e:
        logger = get_logger('config_error')
        logger.error(f"获取模块配置失败: {module_name}, 错误: {e}")
        return {}

def create_config_backup(backup_path: str = 'config_backup.json') -> bool:
    """创建配置备份"""
    if not CONFIG_IMPORT_SUCCESS:
        return False

    try:
        # 收集所有配置 - 只保存可序列化的数据
        backup_config = {
            'global_config': config_manager.get_all_config(),
            'mqtt_config': {
                'connection': get_mqtt_connection_config(),
                'topics': get_mqtt_topics()
            }
        }

        # 保存备份
        import json
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_config, f, ensure_ascii=False, indent=2, default=str)

        logger = get_logger('config_backup')
        logger.info(f"配置备份已保存到: {backup_path}")
        return True

    except Exception as e:
        logger = get_logger('config_error')
        logger.error(f"创建配置备份失败: {e}")
        return False

def restore_config_from_backup(backup_path: str) -> bool:
    """从备份恢复配置"""
    if not CONFIG_IMPORT_SUCCESS:
        return False
    
    try:
        import json
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_config = json.load(f)
        
        # 恢复全局配置
        global_config = backup_config.get('global_config', {})
        for section, params in global_config.items():
            if isinstance(params, dict):
                for key, value in params.items():
                    set_config(section, key, value)
        
        logger = get_logger('config_restore')
        logger.info(f"配置已从备份恢复: {backup_path}")
        return True
        
    except Exception as e:
        logger = get_logger('config_error')
        logger.error(f"从备份恢复配置失败: {e}")
        return False

def print_config_summary():
    """打印配置摘要"""
    if not CONFIG_IMPORT_SUCCESS:
        print("配置系统不可用")
        return
    
    print("\n" + "=" * 60)
    print("鱼群'视'卫智能渔业水环境管理系统 - 配置摘要")
    print("=" * 60)
    
    # 硬件配置
    hardware = get_config('hardware')
    print(f"硬件平台: {hardware.get('platform', 'Unknown')}")
    print(f"开发板型号: {hardware.get('board_type', 'Unknown')}")
    
    # 系统配置
    system = get_config('system')
    print(f"采样间隔: {system.get('sampling_interval', 0)}秒")
    print(f"日志间隔: {system.get('log_interval', 0)}秒")
    
    # MQTT配置
    mqtt_conn = get_mqtt_connection_config()
    print(f"MQTT Broker: {mqtt_conn['broker']['host']}:{mqtt_conn['broker']['port']}")
    
    # 模块配置
    modules = get_config('board_modules')
    enabled_modules = [name for name, config in modules.items() if config.get('enabled', False)]
    print(f"启用模块: {', '.join(enabled_modules)}")
    
    print("=" * 60 + "\n")

# 导出的公共接口
__all__ = [
    # 配置管理
    'get_config',
    'set_config',
    'validate_config',
    'load_config_file',
    'save_config_file',
    'get_module_config',
    
    # MQTT配置
    'get_mqtt_connection_config',
    'get_mqtt_topics',
    'get_client_config',
    'validate_message',
    'validate_command',
    
    # 日志管理
    'get_logger',
    'set_log_level',
    'log_system_startup',
    'log_module_status',
    'log_mqtt_traffic',
    'log_error_with_context',
    'cleanup_loggers',
    
    # 系统管理
    'initialize_config_system',
    'create_config_backup',
    'restore_config_from_backup',
    'print_config_summary',
    
    # 配置常量
    'CONFIG_IMPORT_SUCCESS'
]
