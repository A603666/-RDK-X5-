# coding: utf-8
# 蓝牙坐标接收模块 - 基于地平线RDKX5开发板导航系统
# 扩展现有蓝牙通信架构，添加目标坐标接收、解析、验证和格式标准化功能
# 兼容现有电机控制蓝牙协议，支持JSON和文本两种坐标输入格式

import time
import json
import re
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

# 导入现有蓝牙通信架构
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '电机驱动模块'))
from bluetooth_comm import BluetoothComm, CommandType, ProtocolType

from config import get_navigation_config, get_bluetooth_config, get_algorithm_config

class NavigationCommandType(Enum):
    """导航命令类型枚举 - 扩展现有命令类型"""
    SET_TARGET = "SET_TARGET"  # 设置目标坐标
    NAVIGATE_START = "NAVIGATE_START"  # 开始导航
    NAVIGATE_STOP = "NAVIGATE_STOP"  # 停止导航
    GET_POSITION = "GET_POSITION"  # 获取当前位置
    GET_TARGET = "GET_TARGET"  # 获取目标坐标

class NavigationBluetoothReceiver(BluetoothComm):
    """导航蓝牙坐标接收器 - 继承现有蓝牙通信架构"""
    
    def __init__(self, config_path: str = None):
        """初始化导航蓝牙接收器"""
        # 调用父类初始化
        super().__init__(config_path)
        
        # 导航系统配置
        self.nav_config = get_navigation_config()
        self.bluetooth_nav_config = self.nav_config['BLUETOOTH']
        self.algorithm_config = get_algorithm_config()
        
        # 坐标验证配置
        self.coord_validation = self.algorithm_config['coordinate_validation']
        self.lat_range = self.coord_validation['latitude_range']  # (-90.0, 90.0)
        self.lng_range = self.coord_validation['longitude_range']  # (-180.0, 180.0)
        self.alt_range = self.coord_validation['altitude_range']  # (-100.0, 1000.0)
        
        # 目标坐标数据
        self.target_coordinates = None  # 当前目标坐标
        self.target_set = False  # 目标是否已设置
        self.target_timestamp = 0  # 目标设置时间戳
        
        # 扩展命令处理器 - 添加导航命令支持
        self.command_handlers.update({
            NavigationCommandType.SET_TARGET.value: self._handle_set_target_command,
            NavigationCommandType.NAVIGATE_START.value: self._handle_navigate_start_command,
            NavigationCommandType.NAVIGATE_STOP.value: self._handle_navigate_stop_command,
            NavigationCommandType.GET_POSITION.value: self._handle_get_position_command,
            NavigationCommandType.GET_TARGET.value: self._handle_get_target_command
        })
        
        # 导航回调函数 - 用于与导航系统交互
        self.target_callback = None  # 目标坐标设置回调
        self.navigate_start_callback = None  # 开始导航回调
        self.navigate_stop_callback = None  # 停止导航回调
        self.position_callback = None  # 位置查询回调
        
        # 坐标格式支持
        self.supported_formats = self.bluetooth_nav_config['command_formats']
        
        print(f"导航蓝牙接收器初始化完成 - 服务名: {self.bluetooth_nav_config['service_name']}")
    
    def _parse_text_command(self, text: str) -> Dict[str, Any]:
        """扩展文本格式命令解析 - 添加坐标命令支持"""
        try:
            # 首先尝试解析导航相关命令
            if text.upper().startswith('TARGET:'):
                return self._parse_target_text_command(text)
            elif text.upper().startswith('NAVIGATE:'):
                return self._parse_navigate_text_command(text)
            elif text.upper().startswith('POSITION'):
                return {'command': 'GET_POSITION'}
            else:
                # 调用父类方法处理其他命令
                return super()._parse_text_command(text)
                
        except Exception as e:
            return {'error': f'导航命令解析错误: {e}'}
    
    def _parse_target_text_command(self, text: str) -> Dict[str, Any]:
        """解析目标坐标文本命令 - 格式: TARGET:lat,lng[,alt]"""
        try:
            # 提取坐标部分: TARGET:39.9142,116.4174,100
            coords_str = text[7:].strip()  # 去掉"TARGET:"前缀
            
            if not coords_str:
                return {'error': '目标坐标为空'}
            
            # 分割坐标参数
            coord_parts = coords_str.split(',')
            if len(coord_parts) < 2:
                return {'error': '坐标格式错误，至少需要纬度和经度'}
            
            # 解析坐标值
            lat = float(coord_parts[0].strip())
            lng = float(coord_parts[1].strip())
            alt = float(coord_parts[2].strip()) if len(coord_parts) > 2 else 0.0
            
            return {
                'command': 'SET_TARGET',
                'lat': lat,
                'lng': lng,
                'alt': alt
            }
            
        except ValueError as e:
            return {'error': f'坐标数值转换错误: {e}'}
        except Exception as e:
            return {'error': f'目标坐标解析错误: {e}'}
    
    def _parse_navigate_text_command(self, text: str) -> Dict[str, Any]:
        """解析导航控制文本命令 - 格式: NAVIGATE:START/STOP"""
        try:
            # 提取导航动作: NAVIGATE:START
            action_str = text[9:].strip().upper()  # 去掉"NAVIGATE:"前缀
            
            if action_str == 'START':
                return {'command': 'NAVIGATE_START'}
            elif action_str == 'STOP':
                return {'command': 'NAVIGATE_STOP'}
            else:
                return {'error': f'不支持的导航动作: {action_str}'}
                
        except Exception as e:
            return {'error': f'导航命令解析错误: {e}'}
    
    def _parse_json_command(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """扩展JSON格式命令解析 - 添加坐标命令支持"""
        try:
            command = json_data.get('command', '').upper()
            
            # 处理导航相关JSON命令
            if command == 'SET_TARGET':
                params = json_data.get('params', {})
                return {
                    'command': 'SET_TARGET',
                    'lat': params.get('lat'),
                    'lng': params.get('lng'),
                    'alt': params.get('alt', 0.0)
                }
            elif command in ['NAVIGATE_START', 'NAVIGATE_STOP', 'GET_POSITION', 'GET_TARGET']:
                return {'command': command}
            else:
                # 调用父类方法处理其他命令
                return super()._parse_json_command(json_data)
                
        except Exception as e:
            return {'error': f'导航JSON命令解析错误: {e}'}
    
    def validate_coordinates(self, lat: float, lng: float, alt: float = 0.0) -> Dict[str, Any]:
        """验证坐标数据有效性"""
        try:
            # 纬度范围检查
            if not (self.lat_range[0] <= lat <= self.lat_range[1]):
                return {'valid': False, 'error': f'纬度超出范围 {self.lat_range}: {lat}'}
            
            # 经度范围检查
            if not (self.lng_range[0] <= lng <= self.lng_range[1]):
                return {'valid': False, 'error': f'经度超出范围 {self.lng_range}: {lng}'}
            
            # 高度范围检查
            if not (self.alt_range[0] <= alt <= self.alt_range[1]):
                return {'valid': False, 'error': f'高度超出范围 {self.alt_range}: {alt}'}
            
            return {'valid': True}
            
        except Exception as e:
            return {'valid': False, 'error': f'坐标验证错误: {e}'}
    
    def standardize_coordinates(self, lat: float, lng: float, alt: float = 0.0) -> Dict[str, Any]:
        """标准化坐标格式"""
        return {
            'lat': round(float(lat), 6),  # 纬度保留6位小数
            'lng': round(float(lng), 6),  # 经度保留6位小数
            'alt': round(float(alt), 2),  # 高度保留2位小数
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat()
        }
    
    def _handle_set_target_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理设置目标坐标命令"""
        try:
            lat = params.get('lat')
            lng = params.get('lng')
            alt = params.get('alt', 0.0)
            
            # 检查必需参数
            if lat is None or lng is None:
                return self._create_error_response('SET_TARGET', '缺少纬度或经度参数')
            
            # 坐标验证
            validation = self.validate_coordinates(lat, lng, alt)
            if not validation['valid']:
                return self._create_error_response('SET_TARGET', validation['error'])
            
            # 标准化坐标格式
            standardized_coords = self.standardize_coordinates(lat, lng, alt)
            
            # 更新目标坐标
            with self._lock:
                self.target_coordinates = standardized_coords
                self.target_set = True
                self.target_timestamp = time.time()
            
            # 调用外部回调函数
            if self.target_callback:
                result = self.target_callback(standardized_coords)
                if result:
                    return self._create_success_response(
                        'SET_TARGET', 
                        f'目标坐标已设置: ({lat:.6f}, {lng:.6f}, {alt:.2f})',
                        standardized_coords
                    )
                else:
                    return self._create_error_response('SET_TARGET', '目标坐标设置失败')
            else:
                return self._create_success_response(
                    'SET_TARGET',
                    f'目标坐标已接收: ({lat:.6f}, {lng:.6f}, {alt:.2f})',
                    standardized_coords
                )
                
        except Exception as e:
            return self._create_error_response('SET_TARGET', f'目标坐标处理错误: {e}')
    
    def _handle_navigate_start_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理开始导航命令"""
        try:
            if not self.target_set:
                return self._create_error_response('NAVIGATE_START', '未设置目标坐标')
            
            if self.navigate_start_callback:
                result = self.navigate_start_callback(self.target_coordinates)
                if result:
                    return self._create_success_response('NAVIGATE_START', '导航已启动')
                else:
                    return self._create_error_response('NAVIGATE_START', '导航启动失败')
            else:
                return self._create_error_response('NAVIGATE_START', '导航启动回调未设置')
                
        except Exception as e:
            return self._create_error_response('NAVIGATE_START', f'导航启动处理错误: {e}')
    
    def _handle_navigate_stop_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理停止导航命令"""
        try:
            if self.navigate_stop_callback:
                result = self.navigate_stop_callback()
                if result:
                    return self._create_success_response('NAVIGATE_STOP', '导航已停止')
                else:
                    return self._create_error_response('NAVIGATE_STOP', '导航停止失败')
            else:
                return self._create_error_response('NAVIGATE_STOP', '导航停止回调未设置')
                
        except Exception as e:
            return self._create_error_response('NAVIGATE_STOP', f'导航停止处理错误: {e}')
    
    def _handle_get_position_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取当前位置命令"""
        try:
            if self.position_callback:
                position_data = self.position_callback()
                return self._create_success_response('GET_POSITION', '位置查询成功', position_data)
            else:
                return self._create_error_response('GET_POSITION', '位置查询回调未设置')
                
        except Exception as e:
            return self._create_error_response('GET_POSITION', f'位置查询处理错误: {e}')
    
    def _handle_get_target_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取目标坐标命令"""
        try:
            with self._lock:
                if self.target_set and self.target_coordinates:
                    return self._create_success_response(
                        'GET_TARGET', 
                        '目标坐标查询成功', 
                        self.target_coordinates
                    )
                else:
                    return self._create_error_response('GET_TARGET', '未设置目标坐标')
                    
        except Exception as e:
            return self._create_error_response('GET_TARGET', f'目标坐标查询错误: {e}')
    
    def set_navigation_callbacks(self, target_cb=None, nav_start_cb=None, 
                               nav_stop_cb=None, position_cb=None):
        """设置导航回调函数"""
        self.target_callback = target_cb
        self.navigate_start_callback = nav_start_cb
        self.navigate_stop_callback = nav_stop_cb
        self.position_callback = position_cb
        print("导航蓝牙回调函数已设置")
    
    def get_target_coordinates(self) -> Optional[Dict[str, Any]]:
        """获取当前目标坐标"""
        with self._lock:
            return self.target_coordinates.copy() if self.target_coordinates else None
    
    def clear_target(self):
        """清除目标坐标"""
        with self._lock:
            self.target_coordinates = None
            self.target_set = False
            self.target_timestamp = 0
        print("目标坐标已清除")
    
    def get_navigation_status(self) -> Dict[str, Any]:
        """获取导航状态信息"""
        base_status = self.get_status()
        with self._lock:
            base_status.update({
                'target_set': self.target_set,
                'target_coordinates': self.target_coordinates,
                'target_timestamp': self.target_timestamp,
                'coordinate_validation': self.coord_validation
            })
        return base_status
    
    def get_coordinate_api(self):
        """获取坐标接收API接口 - 供导航系统调用"""
        return {
            'get_target': self.get_target_coordinates,
            'clear_target': self.clear_target,
            'get_status': self.get_navigation_status,
            'validate_coords': self.validate_coordinates,
            'standardize_coords': self.standardize_coordinates,
            'start_comm': self.start_communication,
            'stop_comm': self.stop_communication
        }

# 模块测试函数
def test_navigation_bluetooth():
    """测试导航蓝牙接收器功能"""
    print("=== 导航蓝牙坐标接收器测试 ===")
    
    receiver = NavigationBluetoothReceiver()
    
    # 测试坐标验证
    print("1. 坐标验证测试:")
    test_coords = [
        (39.9142, 116.4174, 100),  # 有效坐标
        (91.0, 116.4174, 100),     # 纬度超出范围
        (39.9142, 181.0, 100),     # 经度超出范围
        (39.9142, 116.4174, 1500)  # 高度超出范围
    ]
    
    for lat, lng, alt in test_coords:
        result = receiver.validate_coordinates(lat, lng, alt)
        print(f"   ({lat}, {lng}, {alt}) -> {result}")
    
    # 测试命令解析
    print("\n2. 命令解析测试:")
    test_commands = [
        'TARGET:39.9142,116.4174,100',
        'NAVIGATE:START',
        'NAVIGATE:STOP',
        'POSITION',
        '{"command": "SET_TARGET", "params": {"lat": 39.9142, "lng": 116.4174, "alt": 100}}',
        '{"command": "GET_TARGET"}'
    ]
    
    for cmd in test_commands:
        result = receiver.parse_command(cmd)
        print(f"   '{cmd}' -> {result}")
    
    print("\n=== 导航蓝牙坐标接收器测试完成 ===")

if __name__ == "__main__":
    test_navigation_bluetooth()
