# coding: utf-8


import os
import logging
from typing import Dict, List, Any, Optional

# MQTT连接配置
MQTT_CONNECTION_CONFIG = {
    'broker': {
        'host': os.getenv('MQTT_BROKER_HOST', 'localhost'),  # MQTT broker地址
        'port': int(os.getenv('MQTT_BROKER_PORT', '1883')),  # MQTT broker端口
        'username': os.getenv('MQTT_USERNAME', ''),  # 用户名(可选)
        'password': os.getenv('MQTT_PASSWORD', ''),  # 密码(可选)
        'keepalive': 60,  # 保活时间(秒)
        'clean_session': True,  # 清理会话
        'protocol_version': 4  # MQTT协议版本(3.1.1)
    },
    'connection': {
        'timeout': 10,  # 连接超时时间(秒)
        'retry_count': 3,  # 连接重试次数
        'retry_delay': 5,  # 重试间隔(秒)
        'auto_reconnect': True,  # 自动重连
        'reconnect_delay': 10  # 重连延迟(秒)
    },
    'qos': {
        'data_upload': 1,  # 数据上传QoS等级
        'command_download': 2,  # 指令下发QoS等级
        'feedback': 1,  # 反馈消息QoS等级
        'status': 0  # 状态消息QoS等级
    }
}

# MQTT主题配置 - 四类数据源和三类控制指令
MQTT_TOPICS_CONFIG = {
    # 板端数据上传主题 (板端→PC端)
    'data_upload': {
        'sensor_data': 'sensor/water_quality',  # 传感器数据主题
        'position_data': 'navigation/position',  # 定位数据主题
        'ai_detection': 'ai/detection',  # AI检测数据主题
        'system_status': 'system/status'  # 系统状态数据主题
    },
    
    # PC端指令下发主题 (PC端→板端)
    'command_download': {
        'navigation_control': 'control/navigation',  # 导航控制指令
        'medication_control': 'control/medication',  # 投药控制指令
        'system_control': 'control/system',  # 系统控制指令
        'emergency_control': 'control/emergency'  # 紧急控制指令
    },
    
    # 板端反馈主题 (板端→PC端)
    'feedback': {
        'navigation_feedback': 'feedback/navigation',  # 导航执行反馈
        'medication_feedback': 'feedback/medication',  # 投药执行反馈
        'system_feedback': 'feedback/system',  # 系统执行反馈
        'emergency_feedback': 'feedback/emergency'  # 紧急处理反馈
    },
    
    # 系统状态主题 (双向)
    'status': {
        'board_heartbeat': 'status/board/heartbeat',  # 板端心跳
        'pc_heartbeat': 'status/pc/heartbeat',  # PC端心跳
        'module_status': 'status/modules',  # 模块状态
        'error_report': 'status/errors'  # 错误报告
    }
}

# 数据格式配置
MQTT_DATA_FORMAT_CONFIG = {
    'encoding': 'utf-8',  # 消息编码
    'timestamp_format': '%Y-%m-%d %H:%M:%S',  # 时间戳格式
    'decimal_precision': 6,  # 浮点数精度
    'coordinate_precision': 8,  # 坐标精度
    'include_metadata': True,  # 是否包含元数据
    'compress_data': False,  # 是否压缩数据
    'validate_json': True  # 是否验证JSON格式
}

# 传感器数据格式定义
SENSOR_DATA_FORMAT = {
    'message_type': 'sensor_data',
    'required_fields': ['timestamp', 'system', 'sensors'],
    'sensors_fields': {
        'ph': {'value': float, 'unit': str, 'status': str},
        'tds': {'value': float, 'unit': str, 'status': str},
        'turbidity': {'value': float, 'unit': str, 'status': str},
        'dissolved_oxygen': {'value': float, 'unit': str, 'status': str},
        'temperature': {'value': float, 'unit': str, 'status': str}
    }
}

# 定位数据格式定义
POSITION_DATA_FORMAT = {
    'message_type': 'position_data',
    'required_fields': ['timestamp', 'latitude', 'longitude', 'valid'],
    'optional_fields': ['altitude', 'speed', 'course', 'satellites', 'accuracy']
}

# AI检测数据格式定义
AI_DETECTION_DATA_FORMAT = {
    'message_type': 'ai_detection',
    'required_fields': ['timestamp', 'detection'],
    'detection_fields': {
        'disease_detected': bool,
        'detection_count': int,
        'detections': list,
        'confidence': float
    }
}

# 系统状态数据格式定义
SYSTEM_STATUS_DATA_FORMAT = {
    'message_type': 'system_status',
    'required_fields': ['timestamp', 'modules', 'hardware'],
    'modules_fields': ['sensor', 'positioning', 'navigation', 'ai_detection', 'motor_control'],
    'hardware_fields': ['cpu_usage', 'memory_usage', 'temperature', 'battery_level']
}

# 控制指令格式定义
CONTROL_COMMAND_FORMAT = {
    'navigation': {
        'SET_TARGET': {
            'required_fields': ['command', 'params', 'timestamp'],
            'params_fields': {'lat': float, 'lng': float, 'alt': float}
        },
        'START_NAVIGATION': {
            'required_fields': ['command', 'timestamp']
        },
        'STOP_NAVIGATION': {
            'required_fields': ['command', 'timestamp']
        },
        'SET_SPEED': {
            'required_fields': ['command', 'params', 'timestamp'],
            'params_fields': {'speed_level': int}
        }
    },
    'medication': {
        'START_MEDICATION': {
            'required_fields': ['command', 'bay_id', 'volume', 'timestamp'],
            'optional_fields': ['duration', 'flow_rate']
        },
        'STOP_MEDICATION': {
            'required_fields': ['command', 'timestamp']
        },
        'SET_MEDICATION_PARAMS': {
            'required_fields': ['command', 'params', 'timestamp'],
            'params_fields': {'bay_id': int, 'volume': float, 'flow_rate': float}
        }
    },
    'system': {
        'GET_SYSTEM_STATUS': {
            'required_fields': ['command', 'timestamp']
        },
        'RESTART_MODULE': {
            'required_fields': ['command', 'module_name', 'timestamp']
        },
        'UPDATE_CONFIG': {
            'required_fields': ['command', 'config_section', 'config_data', 'timestamp']
        }
    },
    'emergency': {
        'EMERGENCY_STOP': {
            'required_fields': ['command', 'timestamp'],
            'priority': 'emergency'
        },
        'EMERGENCY_RETURN': {
            'required_fields': ['command', 'timestamp'],
            'priority': 'emergency'
        }
    }
}

# 指令优先级配置
COMMAND_PRIORITY_CONFIG = {
    'priority_levels': {
        'emergency': 1,  # 紧急指令(最高优先级)
        'safety': 2,  # 安全相关指令
        'navigation': 3,  # 导航控制指令
        'medication': 4,  # 投药控制指令
        'system': 5,  # 系统管理指令
        'status': 6,  # 状态查询指令
        'normal': 7  # 普通指令(最低优先级)
    },
    'command_mapping': {
        'EMERGENCY_STOP': 'emergency',
        'EMERGENCY_RETURN': 'emergency',
        'SET_TARGET': 'navigation',
        'START_NAVIGATION': 'navigation',
        'STOP_NAVIGATION': 'navigation',
        'START_MEDICATION': 'medication',
        'STOP_MEDICATION': 'medication',
        'GET_SYSTEM_STATUS': 'status',
        'RESTART_MODULE': 'system',
        'UPDATE_CONFIG': 'system'
    },
    'timeout_config': {
        'emergency': 1.0,  # 紧急指令超时时间(秒)
        'safety': 2.0,  # 安全指令超时时间
        'navigation': 5.0,  # 导航指令超时时间
        'medication': 10.0,  # 投药指令超时时间
        'system': 15.0,  # 系统指令超时时间
        'status': 30.0,  # 状态查询超时时间
        'normal': 60.0  # 普通指令超时时间
    }
}

# 客户端配置
MQTT_CLIENT_CONFIG = {
    'board_client': {
        'client_id_prefix': 'board_',  # 板端客户端ID前缀
        'subscribe_topics': [  # 订阅的主题
            'control/navigation',
            'control/medication', 
            'control/system',
            'control/emergency'
        ],
        'publish_topics': [  # 发布的主题
            'sensor/water_quality',
            'navigation/position',
            'ai/detection',
            'system/status',
            'feedback/navigation',
            'feedback/medication',
            'feedback/system',
            'feedback/emergency'
        ]
    },
    'pc_client': {
        'client_id_prefix': 'pc_',  # PC端客户端ID前缀
        'subscribe_topics': [  # 订阅的主题
            'sensor/water_quality',
            'navigation/position',
            'ai/detection',
            'system/status',
            'feedback/navigation',
            'feedback/medication',
            'feedback/system',
            'feedback/emergency'
        ],
        'publish_topics': [  # 发布的主题
            'control/navigation',
            'control/medication',
            'control/system',
            'control/emergency'
        ]
    }
}

class MQTTConfigManager:
    """MQTT配置管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_connection_config(self) -> Dict[str, Any]:
        """获取MQTT连接配置"""
        return MQTT_CONNECTION_CONFIG.copy()
    
    def get_topics_config(self) -> Dict[str, Any]:
        """获取MQTT主题配置"""
        return MQTT_TOPICS_CONFIG.copy()
    
    def get_data_format_config(self) -> Dict[str, Any]:
        """获取数据格式配置"""
        return MQTT_DATA_FORMAT_CONFIG.copy()
    
    def get_command_format(self, command_type: str) -> Optional[Dict[str, Any]]:
        """获取指定类型的指令格式"""
        return CONTROL_COMMAND_FORMAT.get(command_type)
    
    def get_command_priority(self, command: str) -> int:
        """获取指令优先级"""
        priority_name = COMMAND_PRIORITY_CONFIG['command_mapping'].get(command, 'normal')
        return COMMAND_PRIORITY_CONFIG['priority_levels'].get(priority_name, 7)
    
    def get_command_timeout(self, command: str) -> float:
        """获取指令超时时间"""
        priority_name = COMMAND_PRIORITY_CONFIG['command_mapping'].get(command, 'normal')
        return COMMAND_PRIORITY_CONFIG['timeout_config'].get(priority_name, 60.0)
    
    def get_client_config(self, client_type: str) -> Optional[Dict[str, Any]]:
        """获取客户端配置"""
        return MQTT_CLIENT_CONFIG.get(f'{client_type}_client')
    
    def validate_message_format(self, message_type: str, data: Dict[str, Any]) -> bool:
        """验证消息格式"""
        try:
            format_map = {
                'sensor_data': SENSOR_DATA_FORMAT,
                'position_data': POSITION_DATA_FORMAT,
                'ai_detection': AI_DETECTION_DATA_FORMAT,
                'system_status': SYSTEM_STATUS_DATA_FORMAT
            }
            
            if message_type not in format_map:
                return False
            
            format_config = format_map[message_type]
            
            # 检查必需字段
            for field in format_config['required_fields']:
                if field not in data:
                    self.logger.error(f"缺少必需字段: {field}")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"消息格式验证失败: {e}")
            return False
    
    def validate_command_format(self, command_type: str, command: str, data: Dict[str, Any]) -> bool:
        """验证指令格式"""
        try:
            if command_type not in CONTROL_COMMAND_FORMAT:
                return False
            
            if command not in CONTROL_COMMAND_FORMAT[command_type]:
                return False
            
            format_config = CONTROL_COMMAND_FORMAT[command_type][command]
            
            # 检查必需字段
            for field in format_config['required_fields']:
                if field not in data:
                    self.logger.error(f"指令缺少必需字段: {field}")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"指令格式验证失败: {e}")
            return False

# 全局MQTT配置管理器实例
mqtt_config_manager = MQTTConfigManager()

# 便捷函数
def get_mqtt_connection_config() -> Dict[str, Any]:
    """获取MQTT连接配置的便捷函数"""
    return mqtt_config_manager.get_connection_config()

def get_mqtt_topics() -> Dict[str, Any]:
    """获取MQTT主题配置的便捷函数"""
    return mqtt_config_manager.get_topics_config()

def get_client_config(client_type: str) -> Optional[Dict[str, Any]]:
    """获取客户端配置的便捷函数"""
    return mqtt_config_manager.get_client_config(client_type)

def validate_message(message_type: str, data: Dict[str, Any]) -> bool:
    """验证消息格式的便捷函数"""
    return mqtt_config_manager.validate_message_format(message_type, data)

def validate_command(command_type: str, command: str, data: Dict[str, Any]) -> bool:
    """验证指令格式的便捷函数"""
    return mqtt_config_manager.validate_command_format(command_type, command, data)
