# coding: utf-8


import os
import sys
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# 日志级别映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# 默认日志配置
DEFAULT_LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'file_path': 'logs/system.log',
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 10,
    'console_output': True,
    'file_output': True,
    'encoding': 'utf-8'
}

# 模块特定日志配置
MODULE_LOG_CONFIG = {
    'sensor': {
        'file_path': 'logs/sensor.log',
        'level': 'INFO',
        'format': '%(asctime)s - [传感器] - %(levelname)s - %(message)s'
    },
    'positioning': {
        'file_path': 'logs/positioning.log',
        'level': 'INFO',
        'format': '%(asctime)s - [定位] - %(levelname)s - %(message)s'
    },
    'navigation': {
        'file_path': 'logs/navigation.log',
        'level': 'INFO',
        'format': '%(asctime)s - [导航] - %(levelname)s - %(message)s'
    },
    'ai_detection': {
        'file_path': 'logs/ai_detection.log',
        'level': 'INFO',
        'format': '%(asctime)s - [AI检测] - %(levelname)s - %(message)s'
    },
    'motor_control': {
        'file_path': 'logs/motor_control.log',
        'level': 'INFO',
        'format': '%(asctime)s - [电机控制] - %(levelname)s - %(message)s'
    },
    'web_server': {
        'file_path': 'logs/web_server.log',
        'level': 'INFO',
        'format': '%(asctime)s - [Web服务] - %(levelname)s - %(message)s'
    },
    'mqtt': {
        'file_path': 'logs/mqtt.log',
        'level': 'INFO',
        'format': '%(asctime)s - [MQTT] - %(levelname)s - %(message)s'
    },
    'integration': {
        'file_path': 'logs/integration.log',
        'level': 'INFO',
        'format': '%(asctime)s - [系统集成] - %(levelname)s - %(message)s'
    }
}

class SystemLogger:
    """系统日志管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or DEFAULT_LOG_CONFIG.copy()
        self.loggers = {}
        self._setup_log_directory()
    
    def _setup_log_directory(self):
        """创建日志目录"""
        log_dir = Path(self.config['file_path']).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 为模块日志创建目录
        for module_config in MODULE_LOG_CONFIG.values():
            module_log_dir = Path(module_config['file_path']).parent
            module_log_dir.mkdir(parents=True, exist_ok=True)
    
    def get_logger(self, name: str, module: Optional[str] = None) -> logging.Logger:
        """获取指定名称的日志记录器"""
        logger_key = f"{module}_{name}" if module else name
        
        if logger_key in self.loggers:
            return self.loggers[logger_key]
        
        # 创建新的日志记录器
        logger = logging.getLogger(logger_key)
        
        # 获取配置
        if module and module in MODULE_LOG_CONFIG:
            config = {**self.config, **MODULE_LOG_CONFIG[module]}
        else:
            config = self.config
        
        # 设置日志级别
        log_level = LOG_LEVELS.get(config['level'], logging.INFO)
        logger.setLevel(log_level)
        
        # 清除现有处理器
        logger.handlers.clear()
        
        # 创建格式化器
        formatter = logging.Formatter(
            config['format'],
            datefmt=config.get('date_format', '%Y-%m-%d %H:%M:%S')
        )
        
        # 添加控制台处理器
        if config.get('console_output', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # 添加文件处理器
        if config.get('file_output', True):
            file_handler = logging.handlers.RotatingFileHandler(
                config['file_path'],
                maxBytes=config.get('max_file_size', 10 * 1024 * 1024),
                backupCount=config.get('backup_count', 10),
                encoding=config.get('encoding', 'utf-8')
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # 防止日志重复
        logger.propagate = False
        
        # 缓存日志记录器
        self.loggers[logger_key] = logger
        
        return logger
    
    def set_log_level(self, level: str, module: Optional[str] = None):
        """设置日志级别"""
        if level not in LOG_LEVELS:
            raise ValueError(f"无效的日志级别: {level}")
        
        log_level = LOG_LEVELS[level]
        
        if module:
            # 设置特定模块的日志级别
            for logger_key, logger in self.loggers.items():
                if logger_key.startswith(f"{module}_"):
                    logger.setLevel(log_level)
                    for handler in logger.handlers:
                        handler.setLevel(log_level)
        else:
            # 设置所有日志记录器的级别
            for logger in self.loggers.values():
                logger.setLevel(log_level)
                for handler in logger.handlers:
                    handler.setLevel(log_level)
    
    def log_system_info(self, logger_name: str = 'system'):
        """记录系统信息"""
        logger = self.get_logger(logger_name)
        logger.info("=" * 60)
        logger.info("鱼群'视'卫智能渔业水环境管理系统启动")
        logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Python版本: {sys.version}")
        logger.info(f"工作目录: {os.getcwd()}")
        logger.info(f"日志级别: {self.config['level']}")
        logger.info("=" * 60)
    
    def log_module_status(self, module: str, status: str, message: str = ""):
        """记录模块状态"""
        logger = self.get_logger('module_status', module)
        status_emoji = {
            'starting': '🚀',
            'running': '✅',
            'stopped': '⏹️',
            'error': '❌',
            'warning': '⚠️'
        }
        emoji = status_emoji.get(status, '📝')
        logger.info(f"{emoji} {module}模块 - {status.upper()}: {message}")
    
    def log_mqtt_message(self, direction: str, topic: str, message_type: str, size: int):
        """记录MQTT消息"""
        logger = self.get_logger('mqtt_traffic', 'mqtt')
        direction_emoji = '📤' if direction == 'publish' else '📥'
        logger.info(f"{direction_emoji} {direction.upper()} - 主题: {topic}, 类型: {message_type}, 大小: {size}字节")
    
    def log_error_with_context(self, logger_name: str, error: Exception, context: Dict[str, Any]):
        """记录带上下文的错误信息"""
        logger = self.get_logger(logger_name)
        logger.error(f"错误: {str(error)}")
        logger.error(f"错误类型: {type(error).__name__}")
        for key, value in context.items():
            logger.error(f"上下文 - {key}: {value}")
    
    def cleanup(self):
        """清理日志资源"""
        for logger in self.loggers.values():
            for handler in logger.handlers:
                handler.close()
        self.loggers.clear()

# 全局系统日志管理器实例
system_logger = SystemLogger()

# 便捷函数
def get_logger(name: str, module: Optional[str] = None) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return system_logger.get_logger(name, module)

def set_log_level(level: str, module: Optional[str] = None):
    """设置日志级别的便捷函数"""
    system_logger.set_log_level(level, module)

def log_system_startup():
    """记录系统启动信息的便捷函数"""
    system_logger.log_system_info()

def log_module_status(module: str, status: str, message: str = ""):
    """记录模块状态的便捷函数"""
    system_logger.log_module_status(module, status, message)

def log_mqtt_traffic(direction: str, topic: str, message_type: str, size: int):
    """记录MQTT流量的便捷函数"""
    system_logger.log_mqtt_message(direction, topic, message_type, size)

def log_error_with_context(logger_name: str, error: Exception, context: Dict[str, Any]):
    """记录带上下文错误的便捷函数"""
    system_logger.log_error_with_context(logger_name, error, context)

def cleanup_loggers():
    """清理日志资源的便捷函数"""
    system_logger.cleanup()

# 设置根日志记录器
def setup_root_logger():
    """设置根日志记录器"""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)  # 只显示警告及以上级别的第三方库日志
    
    # 移除默认处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

# 初始化时设置根日志记录器
setup_root_logger()
