# coding: utf-8


import os
import sys

# 添加配置目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_dir = os.path.join(project_root, 'config')
sys.path.insert(0, config_dir)

# 导入全局配置管理
try:
    from config import get_module_config, get_config, CONFIG_IMPORT_SUCCESS
    GLOBAL_CONFIG_AVAILABLE = CONFIG_IMPORT_SUCCESS
except ImportError:
    GLOBAL_CONFIG_AVAILABLE = False

# 板端模块配置映射
BOARD_MODULE_CONFIG_MAP = {
    'sensor': {
        'config_section': 'sensor',
        'mqtt_data_topic': 'sensor/water_quality',
        'required_hardware': ['uart', 'i2c'],
        'startup_priority': 2
    },
    'positioning': {
        'config_section': 'positioning',
        'mqtt_data_topic': 'navigation/position',
        'required_hardware': ['uart', 'i2c'],
        'startup_priority': 3
    },
    'navigation': {
        'config_section': 'navigation',
        'mqtt_command_topics': ['control/navigation', 'control/emergency'],
        'mqtt_feedback_topic': 'feedback/navigation',
        'required_hardware': ['uart', 'gpio'],
        'startup_priority': 4
    },
    'ai_detection': {
        'config_section': 'ai_detection',
        'mqtt_data_topic': 'ai/detection',
        'required_hardware': ['camera'],
        'startup_priority': 5
    },
    'motor_control': {
        'config_section': 'motor_control',
        'mqtt_command_topics': ['control/medication', 'control/emergency'],
        'mqtt_feedback_topic': 'feedback/medication',
        'required_hardware': ['gpio', 'pwm'],
        'startup_priority': 1
    }
}

def get_board_module_config(module_id: str) -> dict:
    """获取板端模块配置"""
    if not GLOBAL_CONFIG_AVAILABLE:
        return _get_fallback_config(module_id)
    
    try:
        # 从全局配置获取模块配置
        module_config = get_module_config(module_id)
        
        # 添加板端特定配置
        board_config = BOARD_MODULE_CONFIG_MAP.get(module_id, {})
        module_config.update(board_config)
        
        return module_config
    except Exception:
        return _get_fallback_config(module_id)

def _get_fallback_config(module_id: str) -> dict:
    """备用配置（全局配置不可用时）"""
    base_config = {
        'hardware': {
            'platform': 'RDKX5',
            'board_type': 'Horizon_RDKX5',
            'gpio_library': 'Hobot.GPIO'
        },
        'system': {
            'sampling_interval': 1.0,
            'print_interval': 1.0,
            'log_interval': 10.0,
            'thread_timeout': 5.0
        },
        'uart': {
            'timeout': 1.0,
            'write_timeout': 1.0,
            'buffer_size': 1024,
            'retry_count': 3
        },
        'mqtt': {
            'broker': 'localhost',
            'port': 1883,
            'keepalive': 60,
            'qos': 1
        },
        'output': {
            'json_format': True,
            'timestamp_format': '%Y-%m-%d %H:%M:%S',
            'decimal_places': 2
        }
    }
    
    # 添加模块特定配置
    board_config = BOARD_MODULE_CONFIG_MAP.get(module_id, {})
    base_config.update(board_config)
    
    return base_config

def get_all_board_configs() -> dict:
    """获取所有板端模块配置"""
    configs = {}
    
    for module_id in BOARD_MODULE_CONFIG_MAP.keys():
        configs[module_id] = get_board_module_config(module_id)
    
    return configs

def get_mqtt_topics_for_module(module_id: str) -> dict:
    """获取模块的MQTT主题配置"""
    config = get_board_module_config(module_id)
    topics = {}
    
    # 数据上传主题
    if 'mqtt_data_topic' in config:
        topics['data_upload'] = config['mqtt_data_topic']
    
    # 指令订阅主题
    if 'mqtt_command_topics' in config:
        topics['command_subscribe'] = config['mqtt_command_topics']
    
    # 反馈发布主题
    if 'mqtt_feedback_topic' in config:
        topics['feedback_publish'] = config['mqtt_feedback_topic']
    
    return topics

def get_hardware_requirements(module_id: str) -> list:
    """获取模块的硬件需求"""
    config = get_board_module_config(module_id)
    return config.get('required_hardware', [])

def get_startup_priority(module_id: str) -> int:
    """获取模块启动优先级"""
    config = get_board_module_config(module_id)
    return config.get('startup_priority', 99)

def validate_board_config() -> bool:
    """验证板端配置"""
    try:
        # 检查所有模块配置
        for module_id in BOARD_MODULE_CONFIG_MAP.keys():
            config = get_board_module_config(module_id)

            # 检查必需的配置项
            required_sections = ['hardware', 'system']
            for section in required_sections:
                if section not in config:
                    print(f"模块 {module_id} 缺少配置节: {section}")
                    return False

            # 检查MQTT相关配置（可能在不同的键下）
            mqtt_keys = ['mqtt', 'mqtt_topics', 'mqtt_data_topic', 'mqtt_command_topics']
            has_mqtt_config = any(key in config for key in mqtt_keys)
            if not has_mqtt_config:
                print(f"模块 {module_id} 缺少MQTT配置")
                return False

        return True
    except Exception as e:
        print(f"配置验证失败: {e}")
        return False

def print_board_config_summary():
    """打印板端配置摘要"""
    print("\n" + "=" * 50)
    print("板端模块配置摘要")
    print("=" * 50)
    
    for module_id, board_config in BOARD_MODULE_CONFIG_MAP.items():
        config = get_board_module_config(module_id)
        
        print(f"\n模块: {module_id}")
        print(f"  启动优先级: {board_config.get('startup_priority', 'N/A')}")
        print(f"  硬件需求: {', '.join(board_config.get('required_hardware', []))}")
        
        # MQTT主题
        if 'mqtt_data_topic' in board_config:
            print(f"  数据主题: {board_config['mqtt_data_topic']}")
        if 'mqtt_command_topics' in board_config:
            print(f"  指令主题: {', '.join(board_config['mqtt_command_topics'])}")
        if 'mqtt_feedback_topic' in board_config:
            print(f"  反馈主题: {board_config['mqtt_feedback_topic']}")
    
    print("\n" + "=" * 50)

# 导出的公共接口
__all__ = [
    'get_board_module_config',
    'get_all_board_configs',
    'get_mqtt_topics_for_module',
    'get_hardware_requirements',
    'get_startup_priority',
    'validate_board_config',
    'print_board_config_summary',
    'BOARD_MODULE_CONFIG_MAP',
    'GLOBAL_CONFIG_AVAILABLE'
]
