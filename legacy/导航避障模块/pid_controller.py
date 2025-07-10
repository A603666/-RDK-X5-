# coding: utf-8
# PID导航控制器模块 - 基于地平线RDKX5开发板导航系统
# 实现PID控制算法用于航向和速度控制，复用定位模块数学计算功能，集成现有电机控制API

import time
import math
import threading
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# 导入现有模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '定位模块'))
sys.path.append(os.path.join(os.path.dirname(__file__), '电机驱动模块'))

from fusion import KalmanFilter  # 复用定位模块的数学计算功能
from motor_control import get_motor_control_api  # 复用电机控制API
from config import get_pid_config, get_algorithm_config, get_system_config

class NavigationMath:
    """导航数学计算工具类 - 复用定位模块的数学功能"""
    
    def __init__(self):
        self.EARTH_RADIUS = 6378137.0  # 地球半径(米)
    
    def haversine_distance(self, pos1: Dict[str, float], pos2: Dict[str, float]) -> float:
        """计算两点间的Haversine距离 - 复用定位模块算法"""
        lat1, lng1 = math.radians(pos1['lat']), math.radians(pos1['lng'])
        lat2, lng2 = math.radians(pos2['lat']), math.radians(pos2['lng'])
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return self.EARTH_RADIUS * c  # 距离(米)
    
    def calculate_bearing(self, pos1: Dict[str, float], pos2: Dict[str, float]) -> float:
        """计算两点间的方位角 - 复用定位模块算法"""
        lat1, lng1 = math.radians(pos1['lat']), math.radians(pos1['lng'])
        lat2, lng2 = math.radians(pos2['lat']), math.radians(pos2['lng'])
        
        dlng = lng2 - lng1
        
        y = math.sin(dlng) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        
        # 转换为0-360度范围
        return (bearing + 360) % 360
    
    def normalize_angle(self, angle: float) -> float:
        """角度归一化到-180到180度范围"""
        while angle > 180:
            angle -= 360
        while angle < -180:
            angle += 360
        return angle

class PIDController:
    """PID控制器基类"""
    
    def __init__(self, kp: float, ki: float, kd: float, 
                 output_limit: Tuple[float, float] = (-100, 100),
                 integral_limit: Tuple[float, float] = (-50, 50),
                 deadband: float = 0.0,
                 sample_time: float = 0.1):
        """初始化PID控制器"""
        self.kp = kp  # 比例系数
        self.ki = ki  # 积分系数
        self.kd = kd  # 微分系数
        
        self.output_limit = output_limit  # 输出限制
        self.integral_limit = integral_limit  # 积分限制
        self.deadband = deadband  # 死区范围
        self.sample_time = sample_time  # 采样时间
        
        # PID状态变量
        self.last_error = 0.0  # 上次误差
        self.integral = 0.0  # 积分累积
        self.last_time = 0.0  # 上次更新时间
        
        # 统计信息
        self.update_count = 0  # 更新次数
        self.last_output = 0.0  # 上次输出
        
        self._lock = threading.Lock()  # 线程安全锁
    
    def update(self, error: float, current_time: float = None) -> float:
        """更新PID控制器"""
        if current_time is None:
            current_time = time.time()
        
        with self._lock:
            # 死区处理
            if abs(error) < self.deadband:
                error = 0.0
            
            # 计算时间间隔
            if self.last_time == 0.0:
                dt = self.sample_time
            else:
                dt = current_time - self.last_time
                if dt <= 0:
                    dt = self.sample_time
            
            # 比例项
            proportional = self.kp * error
            
            # 积分项
            self.integral += error * dt
            # 积分限幅
            self.integral = max(min(self.integral, self.integral_limit[1]), self.integral_limit[0])
            integral = self.ki * self.integral
            
            # 微分项
            derivative = self.kd * (error - self.last_error) / dt
            
            # PID输出
            output = proportional + integral + derivative
            
            # 输出限幅
            output = max(min(output, self.output_limit[1]), self.output_limit[0])
            
            # 更新状态
            self.last_error = error
            self.last_time = current_time
            self.last_output = output
            self.update_count += 1
            
            return output
    
    def reset(self):
        """重置PID控制器状态"""
        with self._lock:
            self.last_error = 0.0
            self.integral = 0.0
            self.last_time = 0.0
            self.last_output = 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """获取PID控制器状态"""
        with self._lock:
            return {
                'kp': self.kp, 'ki': self.ki, 'kd': self.kd,
                'last_error': self.last_error,
                'integral': self.integral,
                'last_output': self.last_output,
                'update_count': self.update_count
            }

class NavigationPIDController:
    """导航PID控制器 - 集成航向和速度控制"""
    
    def __init__(self):
        """初始化导航PID控制器"""
        # 加载配置
        self.pid_config = get_pid_config()
        self.algorithm_config = get_algorithm_config()
        self.system_config = get_system_config()
        
        # 初始化数学计算工具
        self.nav_math = NavigationMath()
        
        # 初始化PID控制器
        heading_config = self.pid_config['HEADING_PID']
        self.heading_pid = PIDController(
            kp=heading_config['kp'],
            ki=heading_config['ki'],
            kd=heading_config['kd'],
            output_limit=heading_config['output_limit'],
            integral_limit=heading_config['integral_limit'],
            deadband=heading_config['deadband'],
            sample_time=heading_config['sample_time']
        )
        
        speed_config = self.pid_config['SPEED_PID']
        self.speed_pid = PIDController(
            kp=speed_config['kp'],
            ki=speed_config['ki'],
            kd=speed_config['kd'],
            output_limit=speed_config['output_limit'],
            integral_limit=speed_config['integral_limit'],
            deadband=speed_config['deadband'],
            sample_time=speed_config['sample_time']
        )
        
        # 获取电机控制API
        self.motor_api = get_motor_control_api()
        
        # 导航参数
        self.target_precision = self.algorithm_config['target_precision']  # 目标精度(米)
        self.speed_reduction_distance = self.algorithm_config['speed_reduction_distance']  # 减速距离(米)
        self.max_heading_error = self.algorithm_config['max_heading_error']  # 最大航向误差(度)
        
        # 控制状态
        self.enabled = False  # 控制器使能状态
        self.last_control_time = 0  # 上次控制时间
        self.control_count = 0  # 控制次数
        
        print("导航PID控制器初始化完成")
    
    def calculate_navigation_command(self, current_pos: Dict[str, float], 
                                   target_pos: Dict[str, float]) -> Dict[str, Any]:
        """计算导航控制命令 - 核心导航算法"""
        try:
            # 计算距离和方位角
            distance = self.nav_math.haversine_distance(current_pos, target_pos)
            target_bearing = self.nav_math.calculate_bearing(current_pos, target_pos)
            
            # 获取当前航向
            current_heading = current_pos.get('course', 0.0)
            
            # 计算航向误差
            heading_error = self.nav_math.normalize_angle(target_bearing - current_heading)
            
            # 检查是否到达目标
            if distance <= self.target_precision:
                return {
                    'arrived': True,
                    'distance': distance,
                    'heading_error': heading_error,
                    'direction': 'STOP',
                    'speed': 'STOP'
                }
            
            # 航向PID控制
            heading_output = self.heading_pid.update(heading_error)
            
            # 速度PID控制 - 基于距离误差
            distance_error = distance - self.target_precision
            speed_output = self.speed_pid.update(distance_error)
            
            # 转换为电机控制命令
            direction = self._heading_to_direction(heading_output, heading_error)
            speed = self._distance_to_speed(speed_output, distance)
            
            return {
                'arrived': False,
                'distance': distance,
                'target_bearing': target_bearing,
                'heading_error': heading_error,
                'heading_output': heading_output,
                'speed_output': speed_output,
                'direction': direction,
                'speed': speed
            }
            
        except Exception as e:
            print(f"导航命令计算错误: {e}")
            return {
                'error': str(e),
                'direction': 'STOP',
                'speed': 'STOP'
            }
    
    def _heading_to_direction(self, heading_output: float, heading_error: float) -> str:
        """将航向PID输出转换为方向命令"""
        # 检查航向误差是否过大
        if abs(heading_error) > self.max_heading_error:
            # 大角度转向，停止前进
            return 'LEFT' if heading_error > 0 else 'RIGHT'
        
        # 根据PID输出确定方向
        if abs(heading_output) < 10:  # 小误差，直行
            return 'FORWARD'
        elif heading_output > 0:  # 左转
            return 'LEFT'
        else:  # 右转
            return 'RIGHT'
    
    def _distance_to_speed(self, speed_output: float, distance: float) -> str:
        """将速度PID输出转换为速度等级"""
        # 根据距离调整速度
        if distance < self.speed_reduction_distance:
            # 接近目标，减速
            return 'SLOW'
        elif speed_output > 60:
            return 'FAST'
        elif speed_output > 30:
            return 'MEDIUM'
        else:
            return 'SLOW'
    
    def execute_navigation_command(self, nav_command: Dict[str, Any]) -> Dict[str, Any]:
        """执行导航控制命令 - 调用电机控制API"""
        try:
            if 'error' in nav_command:
                return {'status': 'error', 'message': nav_command['error']}
            
            direction = nav_command['direction']
            speed = nav_command['speed']
            
            # 调用电机控制API
            if direction == 'STOP' or speed == 'STOP':
                result = self.motor_api['emergency_stop']()
            else:
                result = self.motor_api['move'](direction, speed)
            
            self.control_count += 1
            self.last_control_time = time.time()
            
            return {
                'status': 'success',
                'motor_result': result,
                'direction': direction,
                'speed': speed,
                'control_count': self.control_count
            }
            
        except Exception as e:
            print(f"导航命令执行错误: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def navigate_to_target(self, current_pos: Dict[str, float], 
                          target_pos: Dict[str, float]) -> Dict[str, Any]:
        """完整的导航控制流程 - 计算并执行导航命令"""
        # 计算导航命令
        nav_command = self.calculate_navigation_command(current_pos, target_pos)
        
        # 执行导航命令
        if self.enabled:
            execution_result = self.execute_navigation_command(nav_command)
            nav_command['execution'] = execution_result
        else:
            nav_command['execution'] = {'status': 'disabled', 'message': '控制器未使能'}
        
        return nav_command
    
    def enable_control(self):
        """使能PID控制器"""
        self.enabled = True
        self.heading_pid.reset()
        self.speed_pid.reset()
        print("导航PID控制器已使能")
    
    def disable_control(self):
        """禁用PID控制器"""
        self.enabled = False
        # 发送停止命令
        try:
            self.motor_api['emergency_stop']()
        except:
            pass
        print("导航PID控制器已禁用")
    
    def get_controller_status(self) -> Dict[str, Any]:
        """获取控制器状态信息"""
        return {
            'enabled': self.enabled,
            'last_control_time': self.last_control_time,
            'control_count': self.control_count,
            'heading_pid': self.heading_pid.get_status(),
            'speed_pid': self.speed_pid.get_status(),
            'target_precision': self.target_precision,
            'speed_reduction_distance': self.speed_reduction_distance,
            'max_heading_error': self.max_heading_error
        }
    
    def get_navigation_api(self):
        """获取导航控制API接口 - 供导航系统调用"""
        return {
            'navigate': self.navigate_to_target,
            'calculate': self.calculate_navigation_command,
            'execute': self.execute_navigation_command,
            'enable': self.enable_control,
            'disable': self.disable_control,
            'get_status': self.get_controller_status,
            'reset': lambda: (self.heading_pid.reset(), self.speed_pid.reset())
        }

# 模块测试函数
def test_pid_controller():
    """测试PID导航控制器功能"""
    print("=== PID导航控制器测试 ===")
    
    controller = NavigationPIDController()
    
    # 测试数学计算
    print("1. 数学计算测试:")
    pos1 = {'lat': 39.9142, 'lng': 116.4174}
    pos2 = {'lat': 39.9150, 'lng': 116.4180}
    
    distance = controller.nav_math.haversine_distance(pos1, pos2)
    bearing = controller.nav_math.calculate_bearing(pos1, pos2)
    print(f"   距离: {distance:.2f}米, 方位角: {bearing:.2f}度")
    
    # 测试导航命令计算
    print("\n2. 导航命令计算测试:")
    current_pos = {'lat': 39.9142, 'lng': 116.4174, 'course': 45.0}
    target_pos = {'lat': 39.9150, 'lng': 116.4180}
    
    nav_command = controller.calculate_navigation_command(current_pos, target_pos)
    print(f"   导航命令: {nav_command}")
    
    # 测试PID控制器
    print("\n3. PID控制器测试:")
    for error in [30, 15, 5, -10, -25]:
        output = controller.heading_pid.update(error)
        print(f"   航向误差{error}° -> PID输出{output:.2f}")
    
    print("\n=== PID导航控制器测试完成 ===")

if __name__ == "__main__":
    test_pid_controller()
