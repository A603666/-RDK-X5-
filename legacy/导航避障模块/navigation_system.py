# coding: utf-8
# 无人船自主定位导航系统主控制器 - 基于地平线RDKX5开发板
# 集成GPS-IMU定位、超声波避障、蓝牙通信、PID控制等子模块
# 实现状态机管理、任务优先级控制和系统协调，确保避障优先的安全导航

import time
import threading
import queue
import asyncio
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

# 导入MQTT客户端
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    print("警告: paho-mqtt库未安装，MQTT功能将不可用")
    MQTT_AVAILABLE = False

# 导入子模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '定位模块'))

from MAIN import FusionSystem  # GPS-IMU融合定位系统
from ultrasonic_sensor import UltrasonicSensor  # 超声波避障模块
from bluetooth_receiver import NavigationBluetoothReceiver  # 蓝牙坐标接收模块
from pid_controller import NavigationPIDController  # PID导航控制器
from config import (get_navigation_config, get_system_config, get_safety_config, 
                   get_state_machine_config, get_avoidance_config)

class NavigationState(Enum):
    """导航系统状态枚举 - 复用电机驱动模块状态管理模式"""
    IDLE = "待机状态"  # 系统待机
    INITIALIZING = "初始化状态"  # 系统初始化
    NAVIGATING = "导航状态"  # 正常导航
    AVOIDING = "避障状态"  # 避障模式
    ARRIVED = "到达目标状态"  # 到达目标
    ERROR = "错误状态"  # 系统错误
    EMERGENCY_STOP = "紧急停止状态"  # 紧急停止

@dataclass
class NavigationStats:
    """导航系统统计信息"""
    start_time: float = 0.0  # 启动时间
    uptime: float = 0.0  # 运行时间
    navigation_commands: int = 0  # 导航命令数
    avoidance_events: int = 0  # 避障事件数
    targets_reached: int = 0  # 到达目标数
    errors_count: int = 0  # 错误计数
    last_navigation_time: float = 0.0  # 最后导航时间
    total_distance: float = 0.0  # 总航行距离

class NavigationSystem:
    """无人船自主定位导航系统主控制器 - 复用电机驱动模块多线程架构"""
    
    def __init__(self, config_path: str = None):
        """初始化导航系统"""
        # 加载配置
        self.nav_config = get_navigation_config()
        self.system_config = get_system_config()
        self.safety_config = get_safety_config()
        self.state_config = get_state_machine_config()
        self.avoidance_config = get_avoidance_config()
        
        # 子系统模块初始化
        self.fusion_system = FusionSystem()  # GPS-IMU融合定位系统
        self.ultrasonic = UltrasonicSensor()  # 超声波避障传感器
        self.bluetooth = NavigationBluetoothReceiver()  # 蓝牙坐标接收器
        self.pid_controller = NavigationPIDController()  # PID导航控制器
        
        # 系统状态管理 - 复用电机驱动模块状态管理模式
        self.state = NavigationState.IDLE  # 当前系统状态
        self.stats = NavigationStats()  # 系统统计信息
        self.running = False  # 运行状态标志
        self.emergency_stopped = False  # 紧急停止标志
        
        # 导航任务管理
        self.target_coordinates = None  # 目标坐标
        self.target_set = False  # 目标是否已设置
        self.current_position = None  # 当前位置
        self.last_position = None  # 上次位置
        
        # 线程管理 - 复用电机驱动模块多线程架构
        self.navigation_thread = None  # 导航控制线程
        self.avoidance_thread = None  # 避障监测线程
        self.communication_thread = None  # 通信处理线程
        self.position_thread = None  # 位置更新线程
        
        # 线程安全机制
        self.state_lock = threading.RLock()  # 状态访问锁
        self.position_lock = threading.RLock()  # 位置数据锁
        self.command_queue = queue.Queue(maxsize=self.system_config['command_queue_size'])  # 命令队列
        
        # 任务优先级配置 - 避障 > 导航 > 通信
        self.priority_levels = self.avoidance_config['priority_levels']
        
        # 最新系统状态 - 线程安全访问
        self._latest_status = {
            'timestamp': 0.0,
            'state': self.state.value,
            'position': None,
            'target': None,
            'obstacle_distance': None,
            'navigation_command': None,
            'stats': asdict(self.stats),
            'valid': False
        }
        
        # 设置子模块回调函数
        self._setup_module_callbacks()

        # MQTT客户端配置
        self.mqtt_client = None
        self.mqtt_command_client = None  # 专用于接收指令的MQTT客户端
        self.mqtt_enabled = MQTT_AVAILABLE
        self.mqtt_broker = 'localhost'  # MQTT broker地址
        self.mqtt_port = 1883  # MQTT broker端口
        self.mqtt_topic = 'system/status'  # 系统状态主题
        self.mqtt_control_topics = ['control/navigation', 'control/medication', 'control/system', 'control/emergency']  # 控制指令主题
        self._init_mqtt_client()
        self._init_mqtt_command_client()

        print("无人船自主定位导航系统主控制器初始化完成")

    def _init_mqtt_client(self):
        """初始化MQTT客户端"""
        if not self.mqtt_enabled:
            print("MQTT功能不可用，跳过MQTT客户端初始化")
            return

        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()  # 启动后台线程处理网络流量
            print(f"导航系统MQTT客户端已连接到 {self.mqtt_broker}:{self.mqtt_port}")
        except Exception as e:
            print(f"导航系统MQTT客户端连接失败: {e}")
            self.mqtt_enabled = False

    def _init_mqtt_command_client(self):
        """初始化MQTT指令接收客户端"""
        if not self.mqtt_enabled:
            print("MQTT功能不可用，跳过MQTT指令客户端初始化")
            return

        try:
            self.mqtt_command_client = mqtt.Client()
            self.mqtt_command_client.on_message = self.handle_mqtt_command
            self.mqtt_command_client.connect(self.mqtt_broker, self.mqtt_port, 60)

            # 订阅所有控制指令主题
            for topic in self.mqtt_control_topics:
                self.mqtt_command_client.subscribe(topic)
                print(f"已订阅MQTT控制主题: {topic}")

            self.mqtt_command_client.loop_start()  # 启动后台线程处理网络流量
            print(f"导航系统MQTT指令客户端已连接到 {self.mqtt_broker}:{self.mqtt_port}")
        except Exception as e:
            print(f"导航系统MQTT指令客户端连接失败: {e}")
            self.mqtt_enabled = False

    def _setup_module_callbacks(self):
        """设置子模块回调函数 - 连接各模块与主控制器"""
        # 设置蓝牙通信回调
        self.bluetooth.set_navigation_callbacks(
            target_cb=self._handle_target_received,
            nav_start_cb=self._handle_navigation_start,
            nav_stop_cb=self._handle_navigation_stop,
            position_cb=self._handle_position_query
        )
        
        # 启用PID控制器
        self.pid_controller.enable_control()
        
        print("子模块回调函数已设置")

    def handle_mqtt_command(self, client, userdata, message):
        """处理MQTT控制指令 - 复用蓝牙指令处理架构"""
        try:
            topic = message.topic
            command_data = json.loads(message.payload.decode())

            print(f"收到MQTT控制指令 - 主题: {topic}, 数据: {command_data}")

            # 根据主题分类处理指令
            if topic == 'control/navigation':
                result = self._handle_navigation_command(command_data)
            elif topic == 'control/medication':
                result = self._handle_medication_command(command_data)
            elif topic == 'control/system':
                result = self._handle_system_command(command_data)
            elif topic == 'control/emergency':
                result = self._handle_emergency_command(command_data)
            else:
                result = {'status': 'error', 'message': f'未知的控制主题: {topic}'}

            # 发送执行结果反馈
            self._send_command_feedback(topic, command_data, result)

        except Exception as e:
            print(f"MQTT指令处理错误: {e}")
            error_result = {'status': 'error', 'message': f'指令处理异常: {e}'}
            self._send_command_feedback(topic, {}, error_result)

    def _handle_navigation_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理导航控制指令 - 复用现有导航API"""
        try:
            command = command_data.get('command', '').upper()
            params = command_data.get('params', {})

            # 检查指令优先级
            if not self._check_command_priority('navigation_control'):
                return {'status': 'rejected', 'message': '当前状态不允许执行导航指令'}

            if command == 'SET_TARGET':
                coords = {
                    'lat': params.get('lat'),
                    'lng': params.get('lng'),
                    'alt': params.get('alt', 0.0)
                }
                result = self._handle_target_received(coords)
                return {'status': 'success' if result else 'error', 'message': '目标坐标设置' + ('成功' if result else '失败')}

            elif command == 'NAVIGATE_START':
                result = self._handle_navigation_start({})  # 传入空字典作为参数
                return {'status': 'success' if result else 'error', 'message': '导航启动' + ('成功' if result else '失败')}

            elif command == 'NAVIGATE_STOP':
                result = self._handle_navigation_stop()
                return {'status': 'success' if result else 'error', 'message': '导航停止' + ('成功' if result else '失败')}

            elif command == 'GET_POSITION':
                position = self._handle_position_query()
                return {'status': 'success', 'message': '位置查询成功', 'data': position}

            else:
                return {'status': 'error', 'message': f'未知的导航指令: {command}'}

        except Exception as e:
            return {'status': 'error', 'message': f'导航指令处理错误: {e}'}

    def _handle_medication_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理投药控制指令"""
        try:
            command = command_data.get('command', '').upper()

            # 检查指令优先级和前置条件
            if not self._check_command_priority('medication_control'):
                return {'status': 'rejected', 'message': '当前状态不允许执行投药指令'}

            # 检查导航状态是否稳定
            if self.state in [NavigationState.AVOIDING, NavigationState.EMERGENCY_STOP]:
                return {'status': 'rejected', 'message': '避障或紧急状态下无法投药'}

            if command == 'START_MEDICATION':
                bay_id = command_data.get('bay_id', 1)
                volume = command_data.get('volume', 100)
                duration = command_data.get('duration', 30)

                # 模拟投药操作（实际应调用电机控制API）
                print(f"开始投药 - 药仓{bay_id}, 投药量{volume}ml, 持续{duration}秒")
                # TODO: 调用实际的投药控制API
                # result = self.medication_controller.start_dispensing(bay_id, volume, duration)

                return {'status': 'success', 'message': f'投药已启动 - 药仓{bay_id}'}

            elif command == 'STOP_MEDICATION':
                bay_id = command_data.get('bay_id', 1)
                print(f"停止投药 - 药仓{bay_id}")
                # TODO: 调用实际的投药停止API
                # result = self.medication_controller.stop_dispensing(bay_id)

                return {'status': 'success', 'message': f'投药已停止 - 药仓{bay_id}'}

            elif command == 'GET_MEDICATION_STATUS':
                # 模拟投药状态查询
                status = {
                    'bay1': {'level': 80, 'status': 'idle'},
                    'bay2': {'level': 65, 'status': 'idle'}
                }
                return {'status': 'success', 'message': '投药状态查询成功', 'data': status}

            else:
                return {'status': 'error', 'message': f'未知的投药指令: {command}'}

        except Exception as e:
            return {'status': 'error', 'message': f'投药指令处理错误: {e}'}

    def _handle_system_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理系统控制指令"""
        try:
            command = command_data.get('command', '').upper()

            if command == 'START_MODULE':
                module = command_data.get('module', '')
                print(f"启动模块: {module}")
                # TODO: 实现模块启动逻辑
                return {'status': 'success', 'message': f'模块{module}启动成功'}

            elif command == 'STOP_MODULE':
                module = command_data.get('module', '')
                print(f"停止模块: {module}")
                # TODO: 实现模块停止逻辑
                return {'status': 'success', 'message': f'模块{module}停止成功'}

            elif command == 'GET_SYSTEM_STATUS':
                status = self.get_system_status()
                return {'status': 'success', 'message': '系统状态查询成功', 'data': status}

            else:
                return {'status': 'error', 'message': f'未知的系统指令: {command}'}

        except Exception as e:
            return {'status': 'error', 'message': f'系统指令处理错误: {e}'}

    def _handle_emergency_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理紧急控制指令"""
        try:
            command = command_data.get('command', '').upper()

            if command == 'EMERGENCY_STOP':
                print("执行紧急停止指令")
                result = self._handle_emergency_stop()
                return {'status': 'success' if result else 'error', 'message': '紧急停止' + ('成功' if result else '失败')}

            else:
                return {'status': 'error', 'message': f'未知的紧急指令: {command}'}

        except Exception as e:
            return {'status': 'error', 'message': f'紧急指令处理错误: {e}'}

    def _check_command_priority(self, command_category: str) -> bool:
        """检查指令优先级 - 基于现有优先级配置"""
        try:
            from config import AVOIDANCE_CONFIG
            priority_levels = AVOIDANCE_CONFIG['priority_levels']

            command_priority = priority_levels.get(command_category, 10)

            # 紧急停止：最高优先级，总是允许
            if command_category == 'emergency_stop':
                return True

            # 避障状态：只允许紧急停止
            if self.state == NavigationState.AVOIDING:
                return command_priority <= priority_levels['obstacle_avoidance']

            # 其他状态：根据优先级判断
            return True  # 简化实现，实际可根据当前操作优先级判断

        except Exception as e:
            print(f"优先级检查错误: {e}")
            return True  # 默认允许执行

    def _send_command_feedback(self, topic: str, command_data: Dict[str, Any], result: Dict[str, Any]):
        """发送指令执行反馈"""
        if not self.mqtt_enabled or not self.mqtt_client:
            return

        try:
            feedback_topic = topic.replace('control/', 'feedback/')
            feedback_data = {
                'timestamp': time.time(),
                'original_command': command_data,
                'result': result
            }

            self.mqtt_client.publish(feedback_topic, json.dumps(feedback_data))
            print(f"指令执行反馈已发送到: {feedback_topic}")

        except Exception as e:
            print(f"指令反馈发送错误: {e}")

    def _handle_target_received(self, target_coords: Dict[str, Any]) -> bool:
        """处理接收到的目标坐标"""
        try:
            with self.state_lock:
                self.target_coordinates = target_coords
                self.target_set = True
                print(f"目标坐标已设置: ({target_coords['lat']:.6f}, {target_coords['lng']:.6f})")
                return True
        except Exception as e:
            print(f"目标坐标设置错误: {e}")
            return False
    
    def _handle_navigation_start(self, target_coords: Dict[str, Any]) -> bool:
        """处理开始导航命令"""
        try:
            if self.state == NavigationState.IDLE and self.target_set:
                with self.state_lock:
                    self.state = NavigationState.NAVIGATING
                print("导航已启动")
                return True
            else:
                print(f"无法启动导航，当前状态: {self.state.value}")
                return False
        except Exception as e:
            print(f"导航启动错误: {e}")
            return False
    
    def _handle_navigation_stop(self) -> bool:
        """处理停止导航命令"""
        try:
            with self.state_lock:
                self.state = NavigationState.IDLE
                self.target_set = False
                self.target_coordinates = None
            self.pid_controller.disable_control()
            print("导航已停止")
            return True
        except Exception as e:
            print(f"导航停止错误: {e}")
            return False
    
    def _handle_position_query(self) -> Dict[str, Any]:
        """处理位置查询命令"""
        with self.position_lock:
            return self.current_position.copy() if self.current_position else {}

    def _handle_emergency_stop(self) -> bool:
        """处理紧急停止命令 - 调用现有emergency_stop方法"""
        return self.emergency_stop()

    def _position_update_loop(self):
        """位置更新循环线程 - 持续获取GPS-IMU融合定位数据"""
        print("位置更新线程启动")
        
        while self.running:
            try:
                # 获取融合定位数据
                position_data = self.fusion_system.get_position()
                
                if position_data and position_data.get('valid', False):
                    with self.position_lock:
                        self.last_position = self.current_position
                        self.current_position = position_data
                        
                        # 计算航行距离
                        if self.last_position and self.current_position:
                            distance_delta = self._calculate_distance_delta()
                            self.stats.total_distance += distance_delta
                
                time.sleep(0.1)  # 10Hz更新频率
                
            except Exception as e:
                print(f"位置更新错误: {e}")
                time.sleep(1.0)
        
        print("位置更新线程结束")
    
    def _avoidance_monitor_loop(self):
        """避障监测循环线程 - 最高优先级任务"""
        print("避障监测线程启动")
        
        while self.running:
            try:
                # 获取超声波距离数据
                obstacle_distance = self.ultrasonic.get_filtered_distance()
                
                if obstacle_distance is not None:
                    # 检查是否需要避障
                    if self.ultrasonic.is_obstacle_detected(obstacle_distance):
                        with self.state_lock:
                            if self.state == NavigationState.NAVIGATING:
                                self.state = NavigationState.AVOIDING
                                self.stats.avoidance_events += 1
                                print(f"检测到障碍物，距离: {obstacle_distance}mm，进入避障模式")
                        
                        # 执行避障动作
                        avoidance_action = self.ultrasonic.get_avoidance_action(obstacle_distance)
                        self._execute_avoidance_action(avoidance_action)
                    
                    elif self.state == NavigationState.AVOIDING:
                        # 障碍物消失，恢复导航
                        with self.state_lock:
                            if self.target_set:
                                self.state = NavigationState.NAVIGATING
                                print("障碍物已清除，恢复导航模式")
                            else:
                                self.state = NavigationState.IDLE
                
                time.sleep(self.system_config['avoidance_check_interval'])  # 50ms检查间隔
                
            except Exception as e:
                print(f"避障监测错误: {e}")
                time.sleep(0.1)
        
        print("避障监测线程结束")
    
    def _navigation_control_loop(self):
        """导航控制循环线程 - 执行PID导航控制"""
        print("导航控制线程启动")
        
        while self.running:
            try:
                # 只在导航状态下执行导航控制
                if self.state == NavigationState.NAVIGATING and self.target_set and self.current_position:
                    # 执行PID导航控制
                    nav_result = self.pid_controller.navigate_to_target(
                        self.current_position, self.target_coordinates
                    )
                    
                    # 检查是否到达目标
                    if nav_result.get('arrived', False):
                        with self.state_lock:
                            self.state = NavigationState.ARRIVED
                            self.stats.targets_reached += 1
                            print(f"已到达目标位置，距离: {nav_result.get('distance', 0):.2f}米")
                    
                    self.stats.navigation_commands += 1
                    self.stats.last_navigation_time = time.time()
                
                time.sleep(self.system_config['navigation_loop_interval'])  # 100ms控制间隔
                
            except Exception as e:
                print(f"导航控制错误: {e}")
                self.stats.errors_count += 1
                time.sleep(0.5)
        
        print("导航控制线程结束")
    
    def _execute_avoidance_action(self, action: str):
        """执行避障动作 - 最高优先级"""
        try:
            # 临时禁用PID控制器
            self.pid_controller.disable_control()
            
            # 根据避障动作执行相应操作
            motor_api = self.pid_controller.motor_api
            
            if action == 'STOP':
                motor_api['emergency_stop']()
            elif action == 'LEFT':
                motor_api['move']('LEFT', 'SLOW')
            elif action == 'RIGHT':
                motor_api['move']('RIGHT', 'SLOW')
            elif action == 'SLOW':
                motor_api['move']('FORWARD', 'SLOW')
            
            # 重新启用PID控制器
            if self.state == NavigationState.NAVIGATING:
                self.pid_controller.enable_control()
                
        except Exception as e:
            print(f"避障动作执行错误: {e}")
    
    def _calculate_distance_delta(self) -> float:
        """计算位置变化距离"""
        if not self.last_position or not self.current_position:
            return 0.0
        
        try:
            from pid_controller import NavigationMath
            nav_math = NavigationMath()
            return nav_math.haversine_distance(self.last_position, self.current_position)
        except:
            return 0.0
    
    async def start_system(self) -> bool:
        """启动导航系统 - 复用电机驱动模块启动模式"""
        try:
            print("启动无人船自主定位导航系统...")
            self.state = NavigationState.INITIALIZING
            self.stats.start_time = time.time()
            
            # 启动子系统
            if not self.fusion_system.start():
                print("GPS-IMU融合定位系统启动失败")
                return False
            
            if not self.ultrasonic.start_monitoring():
                print("超声波避障系统启动失败")
                return False
            
            if not self.bluetooth.start_communication():
                print("蓝牙通信系统启动失败")
                return False
            
            # 启动线程
            self.running = True
            
            self.position_thread = threading.Thread(target=self._position_update_loop, daemon=True)
            self.avoidance_thread = threading.Thread(target=self._avoidance_monitor_loop, daemon=True)
            self.navigation_thread = threading.Thread(target=self._navigation_control_loop, daemon=True)
            
            self.position_thread.start()
            self.avoidance_thread.start()
            self.navigation_thread.start()
            
            # 等待系统稳定
            await asyncio.sleep(2.0)
            
            self.state = NavigationState.IDLE
            print("无人船自主定位导航系统启动成功")
            return True
            
        except Exception as e:
            print(f"导航系统启动错误: {e}")
            self.state = NavigationState.ERROR
            return False
    
    def stop_system(self) -> bool:
        """停止导航系统 - 优雅关闭"""
        try:
            print("停止无人船自主定位导航系统...")
            self.running = False
            
            # 停止子系统
            self.fusion_system.stop()
            self.ultrasonic.stop_monitoring()
            self.bluetooth.stop_communication()
            self.pid_controller.disable_control()
            
            # 等待线程结束
            threads = [self.position_thread, self.avoidance_thread, self.navigation_thread]
            for thread in threads:
                if thread and thread.is_alive():
                    thread.join(timeout=5.0)

            # 清理MQTT客户端
            self._cleanup_mqtt_client()
            self._cleanup_mqtt_command_client()

            self.state = NavigationState.IDLE
            print("无人船自主定位导航系统已停止")
            return True

        except Exception as e:
            print(f"导航系统停止错误: {e}")
            return False

    def _cleanup_mqtt_client(self):
        """清理MQTT客户端资源"""
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()  # 停止后台线程
                self.mqtt_client.disconnect()  # 断开连接
                print("导航系统MQTT客户端已断开连接")
            except Exception as e:
                print(f"导航系统MQTT客户端清理错误: {e}")

    def _cleanup_mqtt_command_client(self):
        """清理MQTT指令客户端资源"""
        if self.mqtt_command_client:
            try:
                self.mqtt_command_client.loop_stop()  # 停止后台线程
                self.mqtt_command_client.disconnect()  # 断开连接
                print("导航系统MQTT指令客户端已断开连接")
            except Exception as e:
                print(f"导航系统MQTT指令客户端清理错误: {e}")
    
    def emergency_stop(self) -> bool:
        """全系统紧急停止"""
        try:
            with self.state_lock:
                print("执行导航系统紧急停止...")
                self.state = NavigationState.EMERGENCY_STOP
                self.emergency_stopped = True
                
                # 停止所有运动
                self.pid_controller.disable_control()
                motor_api = self.pid_controller.motor_api
                motor_api['emergency_stop']()
                
                print("导航系统紧急停止完成")
                return True
                
        except Exception as e:
            print(f"导航系统紧急停止错误: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态信息"""
        with self.state_lock, self.position_lock:
            self.stats.uptime = time.time() - self.stats.start_time if self.stats.start_time > 0 else 0

            status_data = {
                'timestamp': time.time(),
                'state': self.state.value,
                'running': self.running,
                'target_set': self.target_set,
                'target_coordinates': self.target_coordinates,
                'current_position': self.current_position,
                'obstacle_distance': self.ultrasonic.get_filtered_distance(),
                'stats': asdict(self.stats),
                'subsystems': {
                    'fusion_system': self.fusion_system.get_status(),
                    'ultrasonic': self.ultrasonic.get_sensor_status(),
                    'bluetooth': self.bluetooth.get_navigation_status(),
                    'pid_controller': self.pid_controller.get_controller_status()
                }
            }

            # 发送系统状态到MQTT
            self._send_mqtt_status(status_data)

            return status_data

    def _send_mqtt_status(self, status_data: Dict[str, Any]):
        """发送系统状态到MQTT主题"""
        if not self.mqtt_enabled or not self.mqtt_client:
            return

        try:
            # 简化状态数据，只发送关键信息
            mqtt_status = {
                'timestamp': status_data['timestamp'],
                'data_type': 'system_status',
                'navigation_state': status_data['state'],
                'running': status_data['running'],
                'target_set': status_data['target_set'],
                'obstacle_distance': status_data['obstacle_distance'],
                'modules': {
                    'sensor': {'status': 'running' if status_data['running'] else 'stopped', 'error': None},
                    'navigation': {
                        'status': status_data['state'],
                        'target_distance': self._calculate_target_distance() if status_data['target_set'] else None
                    },
                    'medication': {'status': 'idle', 'bay1_level': 80, 'bay2_level': 65},  # 模拟投药状态
                    'ai_detection': {'status': 'running', 'fps': 15}  # 模拟AI检测状态
                },
                'hardware': {
                    'battery_level': 85,  # 模拟电池电量
                    'cpu_usage': 45,      # 模拟CPU使用率
                    'memory_usage': 60,   # 模拟内存使用率
                    'temperature': 42     # 模拟温度
                }
            }

            # 发送到MQTT主题
            result = self.mqtt_client.publish(self.mqtt_topic, json.dumps(mqtt_status))

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"系统状态已发送到MQTT主题: {self.mqtt_topic}")
            else:
                print(f"系统状态MQTT发送失败，错误码: {result.rc}")

        except Exception as e:
            print(f"系统状态MQTT发送错误: {e}")

    def _calculate_target_distance(self) -> Optional[float]:
        """计算到目标的距离"""
        if not self.target_set or not self.current_position or not self.target_coordinates:
            return None

        try:
            # 简单的距离计算（实际应用中可能需要更精确的地理距离计算）
            lat_diff = self.target_coordinates['lat'] - self.current_position['latitude']
            lng_diff = self.target_coordinates['lng'] - self.current_position['longitude']
            distance = (lat_diff**2 + lng_diff**2)**0.5 * 111000  # 粗略转换为米
            return distance
        except:
            return None

    def get_navigation_api(self):
        """获取导航系统API接口 - 供其他模块调用"""
        return {
            'start': self.start_system,
            'stop': self.stop_system,
            'emergency_stop': self.emergency_stop,
            'set_target': self._handle_target_received,
            'start_navigation': self._handle_navigation_start,
            'stop_navigation': self._handle_navigation_stop,
            'get_status': self.get_system_status,
            'get_position': self._handle_position_query
        }

# 模块测试函数
def test_navigation_system():
    """测试导航系统功能"""
    print("=== 无人船自主定位导航系统测试 ===")
    
    nav_system = NavigationSystem()
    
    # 测试系统状态
    print(f"1. 初始状态: {nav_system.state.value}")
    
    # 测试目标设置
    test_target = {'lat': 39.9150, 'lng': 116.4180, 'alt': 0.0}
    result = nav_system._handle_target_received(test_target)
    print(f"2. 目标设置: {result}, 目标: {nav_system.target_coordinates}")
    
    # 测试系统状态查询
    status = nav_system.get_system_status()
    print(f"3. 系统状态: {status['state']}, 运行: {status['running']}")
    
    print("\n=== 无人船自主定位导航系统测试完成 ===")

if __name__ == "__main__":
    test_navigation_system()
