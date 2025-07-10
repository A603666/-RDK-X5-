# coding: utf-8


import os
import sys

# 添加各模块路径到Python路径
module_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(module_dir))

# 添加原始模块路径
original_modules = [
    '传感器',
    '定位模块',
    '导航避障模块',
    '目标检测/目标检测',
    '电机驱动'
]

for module_path in original_modules:
    full_path = os.path.join(project_root, module_path)
    if os.path.exists(full_path) and full_path not in sys.path:
        sys.path.insert(0, full_path)

# 模块映射 - 将原始模块映射到新的模块名称
MODULE_MAPPING = {
    'sensor': {
        'name': '传感器模块',
        'original_path': '传感器',
        'main_file': 'main.py',
        'description': '水质传感器监测系统，集成PH、TDS、浊度、溶解氧温度四种传感器'
    },
    'positioning': {
        'name': '定位模块',
        'original_path': '定位模块 copy',
        'main_file': 'MAIN.py',
        'description': 'GPS+IMU融合定位系统，提供高精度位置和姿态信息'
    },
    'navigation': {
        'name': '导航避障模块',
        'original_path': '导航避障模块',
        'main_file': 'navigation_system.py',
        'description': '自主导航和超声波避障系统，实现智能路径规划'
    },
    'ai_detection': {
        'name': 'AI检测模块',
        'original_path': '目标检测/目标检测',
        'main_file': '针对HSV空间V通道的CLAHE增强.py',
        'description': 'YOLOv11鱼类病害识别系统，实现智能疾病检测'
    },
    'motor_control': {
        'name': '电机控制模块',
        'original_path': '电机驱动可以运行版本 copy',
        'main_file': 'main.py',
        'description': '推进器控制系统，实现精确的运动控制'
    }
}

def get_module_info(module_id: str) -> dict:
    """获取模块信息"""
    return MODULE_MAPPING.get(module_id, {})

def get_all_modules() -> dict:
    """获取所有模块信息"""
    return MODULE_MAPPING.copy()

def get_module_path(module_id: str) -> str:
    """获取模块路径"""
    module_info = MODULE_MAPPING.get(module_id, {})
    if module_info:
        return os.path.join(project_root, module_info['original_path'])
    return ""

def get_module_main_file(module_id: str) -> str:
    """获取模块主文件路径"""
    module_info = MODULE_MAPPING.get(module_id, {})
    if module_info:
        module_path = get_module_path(module_id)
        return os.path.join(module_path, module_info['main_file'])
    return ""

def check_module_availability() -> dict:
    """检查模块可用性"""
    availability = {}
    
    for module_id, module_info in MODULE_MAPPING.items():
        main_file = get_module_main_file(module_id)
        availability[module_id] = {
            'name': module_info['name'],
            'available': os.path.exists(main_file),
            'path': main_file,
            'description': module_info['description']
        }
    
    return availability

# 导出的公共接口
__all__ = [
    'MODULE_MAPPING',
    'get_module_info',
    'get_all_modules',
    'get_module_path',
    'get_module_main_file',
    'check_module_availability'
]
