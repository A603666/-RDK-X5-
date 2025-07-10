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

# PC端配置映射
PC_CONFIG_MAP = {
    'web_server': {
        'host': '0.0.0.0',
        'port': 5001,
        'debug': False,
        'threaded': True,
        'static_folder': 'web/static',
        'template_folder': 'web/templates'
    },
    'api': {
        'cors_enabled': True,
        'rate_limiting': False,
        'auth_required': False,
        'max_content_length': 16 * 1024 * 1024,  # 16MB
        'json_sort_keys': False
    },
    'mqtt': {
        'data_topics': [
            'sensor/water_quality',
            'navigation/position',
            'ai/detection',
            'system/status'
        ],
        'command_topics': [
            'control/navigation',
            'control/medication',
            'control/system',
            'control/emergency'
        ],
        'feedback_topics': [
            'feedback/navigation',
            'feedback/medication',
            'feedback/system',
            'feedback/emergency'
        ]
    },
    'data_processing': {
        'max_water_quality_records': 1000,
        'data_retention_hours': 24,
        'update_interval': 5,  # 秒
        'chart_update_interval': 10,  # 秒
        'auto_cleanup_enabled': True
    },
    'ai_assistant': {
        'enabled': True,
        'provider': 'coze',
        'stream_response': True,
        'max_conversation_length': 50,
        'timeout': 30  # 秒
    },
    'prediction': {
        'enabled': True,
        'model_type': 'statistical',  # 'statistical' or 'ml'
        'prediction_horizon': 24,  # 小时
        'update_interval': 3600,  # 秒
        'confidence_threshold': 0.8
    },
    'security': {
        'cors_origins': ['*'],
        'max_request_size': 1024 * 1024,  # 1MB
        'rate_limit_per_minute': 100,
        'session_timeout': 3600  # 秒
    }
}

def get_pc_config(section: str = None) -> dict:
    """获取PC端配置"""
    if not GLOBAL_CONFIG_AVAILABLE:
        return _get_fallback_pc_config(section)
    
    try:
        # 从全局配置获取PC端配置
        pc_config = get_config('pc', default={})
        
        # 合并PC端特定配置
        merged_config = {}
        merged_config.update(pc_config)
        merged_config.update(PC_CONFIG_MAP)
        
        if section:
            return merged_config.get(section, {})
        
        return merged_config
    except Exception:
        return _get_fallback_pc_config(section)

def _get_fallback_pc_config(section: str = None) -> dict:
    """备用PC端配置（全局配置不可用时）"""
    fallback_config = {
        'web_server': PC_CONFIG_MAP['web_server'],
        'api': PC_CONFIG_MAP['api'],
        'mqtt': {
            'broker': 'localhost',
            'port': 1883,
            'keepalive': 60,
            'qos': 1,
            **PC_CONFIG_MAP['mqtt']
        },
        'data_processing': PC_CONFIG_MAP['data_processing'],
        'ai_assistant': PC_CONFIG_MAP['ai_assistant'],
        'prediction': PC_CONFIG_MAP['prediction'],
        'security': PC_CONFIG_MAP['security']
    }
    
    if section:
        return fallback_config.get(section, {})
    
    return fallback_config

def get_web_server_config() -> dict:
    """获取Web服务器配置"""
    return get_pc_config('web_server')

def get_api_config() -> dict:
    """获取API配置"""
    return get_pc_config('api')

def get_mqtt_config() -> dict:
    """获取MQTT配置"""
    config = get_pc_config('mqtt')
    
    # 如果全局配置可用，尝试获取MQTT连接配置
    if GLOBAL_CONFIG_AVAILABLE:
        try:
            from config import get_mqtt_connection_config
            mqtt_conn_config = get_mqtt_connection_config()
            if mqtt_conn_config:
                config.update(mqtt_conn_config['broker'])
        except:
            pass
    
    return config

def get_data_processing_config() -> dict:
    """获取数据处理配置"""
    return get_pc_config('data_processing')

def get_ai_assistant_config() -> dict:
    """获取AI助手配置"""
    config = get_pc_config('ai_assistant')
    
    # 从环境变量获取API密钥
    config['coze_auth_token'] = os.getenv('COZE_AUTH_TOKEN', '')
    config['coze_bot_id'] = os.getenv('COZE_BOT_ID', '')
    config['coze_user_id'] = os.getenv('COZE_USER_ID', 'default_user')
    
    return config

def get_prediction_config() -> dict:
    """获取预测配置"""
    return get_pc_config('prediction')

def get_security_config() -> dict:
    """获取安全配置"""
    return get_pc_config('security')

def validate_pc_config() -> bool:
    """验证PC端配置"""
    try:
        # 检查Web服务器配置
        web_config = get_web_server_config()
        if not web_config.get('host') or not web_config.get('port'):
            print("Web服务器配置不完整")
            return False
        
        # 检查MQTT配置
        mqtt_config = get_mqtt_config()
        if not mqtt_config.get('data_topics'):
            print("MQTT数据主题配置缺失")
            return False
        
        # 检查数据处理配置
        data_config = get_data_processing_config()
        if not data_config.get('max_water_quality_records'):
            print("数据处理配置不完整")
            return False
        
        return True
    except Exception as e:
        print(f"PC端配置验证失败: {e}")
        return False

def print_pc_config_summary():
    """打印PC端配置摘要"""
    print("\n" + "=" * 50)
    print("PC端配置摘要")
    print("=" * 50)
    
    # Web服务器配置
    web_config = get_web_server_config()
    print(f"\nWeb服务器:")
    print(f"  地址: {web_config['host']}:{web_config['port']}")
    print(f"  调试模式: {web_config.get('debug', False)}")
    print(f"  多线程: {web_config.get('threaded', True)}")
    
    # MQTT配置
    mqtt_config = get_mqtt_config()
    print(f"\nMQTT通讯:")
    print(f"  Broker: {mqtt_config.get('broker', 'localhost')}:{mqtt_config.get('port', 1883)}")
    print(f"  数据主题: {len(mqtt_config.get('data_topics', []))} 个")
    print(f"  指令主题: {len(mqtt_config.get('command_topics', []))} 个")
    
    # 数据处理配置
    data_config = get_data_processing_config()
    print(f"\n数据处理:")
    print(f"  最大记录数: {data_config.get('max_water_quality_records', 0)}")
    print(f"  数据保留: {data_config.get('data_retention_hours', 0)} 小时")
    print(f"  更新间隔: {data_config.get('update_interval', 0)} 秒")
    
    # AI助手配置
    ai_config = get_ai_assistant_config()
    print(f"\nAI助手:")
    print(f"  启用状态: {ai_config.get('enabled', False)}")
    print(f"  服务提供商: {ai_config.get('provider', 'unknown')}")
    print(f"  API密钥: {'已配置' if ai_config.get('coze_auth_token') else '未配置'}")
    
    # 预测功能配置
    pred_config = get_prediction_config()
    print(f"\n预测功能:")
    print(f"  启用状态: {pred_config.get('enabled', False)}")
    print(f"  模型类型: {pred_config.get('model_type', 'unknown')}")
    print(f"  预测时长: {pred_config.get('prediction_horizon', 0)} 小时")
    
    print("\n" + "=" * 50)

def get_environment_variables() -> dict:
    """获取环境变量配置"""
    return {
        'coze_auth_token': os.getenv('COZE_AUTH_TOKEN', ''),
        'coze_bot_id': os.getenv('COZE_BOT_ID', ''),
        'coze_user_id': os.getenv('COZE_USER_ID', 'default_user'),
        'amap_api_key': os.getenv('AMAP_API_KEY', ''),
        'flask_secret_key': os.getenv('FLASK_SECRET_KEY', 'dev-secret-key'),
        'debug_mode': os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    }

# 导出的公共接口
__all__ = [
    'get_pc_config',
    'get_web_server_config',
    'get_api_config',
    'get_mqtt_config',
    'get_data_processing_config',
    'get_ai_assistant_config',
    'get_prediction_config',
    'get_security_config',
    'validate_pc_config',
    'print_pc_config_summary',
    'get_environment_variables',
    'PC_CONFIG_MAP',
    'GLOBAL_CONFIG_AVAILABLE'
]
