#!/usr/bin/env python
# coding: utf-8
"""
水质传感器监测系统主程序 - 基于地平线RDKX5开发板
集成PH、TDS、浊度、溶解氧温度四种传感器，实现实时数据采集和标准化JSON输出
复用现有定位模块多线程架构和data_aggregator数据聚合模式
Copyright (c) 2025, RDKX5 Water Quality Team.
"""

import time
import threading
import json
import csv
import os
import sys
import signal
from datetime import datetime
from typing import Dict, Any, Optional

# 导入传感器驱动模块
from ph_sensor import PHSensor
from tds_sensor import TDSSensor
from turbidity_sensor import TurbiditySensor
from do_temp_sensor import DOTempSensor
from config import SYSTEM_CONFIG, OUTPUT_CONFIG, GPIO_CONFIG

# 导入MQTT客户端
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    print("警告: paho-mqtt库未安装，MQTT功能将不可用")
    MQTT_AVAILABLE = False

class WaterQualitySystem:
    """水质监测系统核心类 - 复用定位模块多线程架构"""
    
    def __init__(self):
        # 初始化传感器模块
        self.ph_sensor = PHSensor()  # PH传感器(UART2)
        self.tds_sensor = TDSSensor()  # TDS传感器(UART7)
        self.turbidity_sensor = TurbiditySensor()  # 浊度传感器(I2C0)
        self.do_temp_sensor = DOTempSensor()  # 溶解氧温度传感器(UART6/RS485)
        
        # 系统运行状态
        self.running = False  # 系统运行标志
        self.monitoring_thread = None  # 监测线程
        self.last_print_time = 0  # 上次打印时间戳
        
        # 线程安全数据访问 - 复用定位模块模式
        self._lock = threading.Lock()  # 数据访问锁
        self._latest_data = {  # 最新传感器数据
            'timestamp': 0,  # 时间戳
            'system': 'WaterQuality',  # 系统标识
            'ph': {'value': 0.0, 'unit': 'pH', 'valid': False},
            'tds': {'value': 0.0, 'unit': 'ppm', 'valid': False},
            'turbidity': {'value': 0.0, 'unit': 'NTU', 'valid': False},
            'dissolved_oxygen': {'value': 0.0, 'unit': 'mg/L', 'valid': False},
            'temperature': {'value': 0.0, 'unit': '℃', 'valid': False},
            'status': 'stopped'  # 系统状态
        }
        
        # 数据存储配置 - 修复文件权限问题
        self.data_dir = self._get_writable_data_dir()  # 获取可写数据目录
        self.data_file = os.path.join(self.data_dir, 'water_quality_data.csv')
        self.log_file = os.path.join(self.data_dir, 'water_quality.log')
        
        # 系统配置
        self.sampling_interval = SYSTEM_CONFIG['sampling_interval']
        self.print_interval = SYSTEM_CONFIG['print_interval']
        self.log_interval = SYSTEM_CONFIG['log_interval']

        # MQTT客户端配置
        self.mqtt_client = None
        self.mqtt_enabled = MQTT_AVAILABLE
        self.mqtt_broker = 'localhost'  # MQTT broker地址
        self.mqtt_port = 1883  # MQTT broker端口
        self.mqtt_topic = 'sensor/water_quality'  # 传感器数据主题
        self._init_mqtt_client()

    def _get_writable_data_dir(self):
        """获取可写的数据目录 - 修复文件权限问题"""
        # 尝试多个可能的数据目录
        possible_dirs = [
            '/tmp/water_quality',  # 临时目录
            os.path.expanduser('~/water_quality_data'),  # 用户主目录
            '/var/log/water_quality',  # 系统日志目录
            '.'  # 当前目录作为最后选择
        ]

        for data_dir in possible_dirs:
            try:
                # 创建目录（如果不存在）
                os.makedirs(data_dir, exist_ok=True)

                # 测试写入权限
                test_file = os.path.join(data_dir, 'test_write.tmp')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)

                print(f"使用数据目录: {data_dir}")
                return data_dir

            except (OSError, PermissionError) as e:
                print(f"目录 {data_dir} 不可写: {e}")
                continue

        # 如果所有目录都不可写，使用/tmp作为最后选择
        fallback_dir = '/tmp'
        print(f"警告: 使用备用目录 {fallback_dir}")
        return fallback_dir

    def _init_mqtt_client(self):
        """初始化MQTT客户端"""
        if not self.mqtt_enabled:
            print("MQTT功能不可用，跳过MQTT客户端初始化")
            return

        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()  # 启动后台线程处理网络流量
            print(f"MQTT客户端已连接到 {self.mqtt_broker}:{self.mqtt_port}")
        except Exception as e:
            print(f"MQTT客户端连接失败: {e}")
            self.mqtt_enabled = False

    def start(self):
        """启动水质监测系统 - 复用定位模块启动模式"""
        print("启动水质传感器监测系统...")
        
        # 初始化GPIO配置
        self._init_gpio()
        
        # 启动PH传感器
        if not self.ph_sensor.connect():
            print("PH传感器连接失败")
            return False
        
        # 启动TDS传感器
        if not self.tds_sensor.connect():
            print("TDS传感器连接失败")
            self.ph_sensor.disconnect()
            return False

        # 启动浊度传感器
        if not self.turbidity_sensor.connect():
            print("浊度传感器连接失败")
            self.ph_sensor.disconnect()
            self.tds_sensor.disconnect()
            return False

        # 启动溶解氧温度传感器
        if not self.do_temp_sensor.connect():
            print("溶解氧温度传感器连接失败")
            self.ph_sensor.disconnect()
            self.tds_sensor.disconnect()
            self.turbidity_sensor.disconnect()
            return False
        
        # 启动各传感器监测线程
        self.ph_sensor.start_monitoring()
        self.tds_sensor.start_monitoring()
        self.turbidity_sensor.start_monitoring()
        self.do_temp_sensor.start_monitoring()
        
        # 启动主监测线程 - 复用定位模块线程模式
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        # 初始化数据存储文件
        self._init_data_storage()
        
        print("水质传感器监测系统启动成功")
        return True
    
    def stop(self):
        """停止水质监测系统 - 复用定位模块停止模式"""
        print("停止水质传感器监测系统...")
        self.running = False
        
        # 等待主监测线程安全退出
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)
        
        # 停止各传感器监测
        self.ph_sensor.stop_monitoring()
        self.tds_sensor.stop_monitoring()
        self.turbidity_sensor.stop_monitoring()
        self.do_temp_sensor.stop_monitoring()
        
        # 断开传感器连接
        self.ph_sensor.disconnect()
        self.tds_sensor.disconnect()
        self.turbidity_sensor.disconnect()
        self.do_temp_sensor.disconnect()
        
        # 清理GPIO资源
        self._cleanup_gpio()

        # 清理MQTT客户端
        self._cleanup_mqtt_client()

        print("水质传感器监测系统已停止")
    
    def _init_gpio(self):
        """初始化GPIO配置"""
        try:
            import Hobot.GPIO as GPIO
            GPIO.setmode(getattr(GPIO, GPIO_CONFIG['mode']))
            GPIO.setwarnings(GPIO_CONFIG['warnings'])
            print("GPIO初始化成功")
        except ImportError:
            print("警告: Hobot.GPIO库未安装，GPIO功能将不可用")
        except Exception as e:
            print(f"GPIO初始化错误: {e}")
    
    def _cleanup_gpio(self):
        """清理GPIO资源"""
        if GPIO_CONFIG['cleanup_on_exit']:
            try:
                import Hobot.GPIO as GPIO
                GPIO.cleanup()
                print("GPIO资源清理完成")
            except:
                pass

    def _cleanup_mqtt_client(self):
        """清理MQTT客户端资源"""
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()  # 停止后台线程
                self.mqtt_client.disconnect()  # 断开连接
                print("MQTT客户端已断开连接")
            except Exception as e:
                print(f"MQTT客户端清理错误: {e}")
    
    def _init_data_storage(self):
        """初始化数据存储文件"""
        try:
            # 创建CSV文件头
            if not os.path.exists(self.data_file):
                with open(self.data_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'timestamp', 'datetime', 'ph_value', 'ph_valid',
                        'tds_value', 'tds_valid', 'turbidity_value', 'turbidity_valid',
                        'dissolved_oxygen', 'do_valid', 'temperature', 'temp_valid'
                    ])
            print(f"数据存储文件初始化: {self.data_file}")
        except Exception as e:
            print(f"数据存储初始化错误: {e}")
    
    def _monitoring_loop(self):
        """主监测循环 - 复用定位模块监测模式"""
        last_log_time = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # 收集所有传感器数据
                ph_data = self.ph_sensor.get_sensor_data()
                tds_data = self.tds_sensor.get_sensor_data()
                turbidity_data = self.turbidity_sensor.get_sensor_data()
                do_temp_data = self.do_temp_sensor.get_sensor_data()
                
                # 更新系统数据 - 线程安全访问
                with self._lock:
                    self._latest_data.update({
                        'timestamp': current_time,
                        'ph': {
                            'value': ph_data['value'],
                            'unit': ph_data['unit'],
                            'valid': ph_data['valid']
                        },
                        'tds': {
                            'value': tds_data['value'],
                            'unit': tds_data['unit'],
                            'valid': tds_data['valid']
                        },
                        'turbidity': {
                            'value': turbidity_data['value'],
                            'unit': turbidity_data['unit'],
                            'valid': turbidity_data['valid']
                        },
                        'dissolved_oxygen': {
                            'value': do_temp_data['dissolved_oxygen'],
                            'unit': do_temp_data['do_unit'],
                            'valid': do_temp_data['valid']
                        },
                        'temperature': {
                            'value': do_temp_data['temperature'],
                            'unit': do_temp_data['temp_unit'],
                            'valid': do_temp_data['valid']
                        },
                        'status': 'running'
                    })
                
                # 定时打印数据和发送MQTT数据
                if current_time - self.last_print_time >= self.print_interval:
                    self._print_data()
                    self._send_mqtt_data()  # 发送MQTT数据
                    self.last_print_time = current_time
                
                # 定时记录数据
                if current_time - last_log_time >= self.log_interval:
                    self._log_data()
                    last_log_time = current_time
                
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                print(f"监测循环错误: {e}")
                time.sleep(1.0)
    
    def _print_data(self):
        """打印当前传感器数据"""
        with self._lock:
            data = self._latest_data.copy()
        
        print(f"\n=== 水质监测数据 {datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')} ===")
        print(f"PH值: {data['ph']['value']:.2f} {data['ph']['unit']} ({'有效' if data['ph']['valid'] else '无效'})")
        print(f"TDS值: {data['tds']['value']:.0f} {data['tds']['unit']} ({'有效' if data['tds']['valid'] else '无效'})")
        print(f"浊度: {data['turbidity']['value']:.1f} {data['turbidity']['unit']} ({'有效' if data['turbidity']['valid'] else '无效'})")
        print(f"溶解氧: {data['dissolved_oxygen']['value']:.2f} {data['dissolved_oxygen']['unit']} ({'有效' if data['dissolved_oxygen']['valid'] else '无效'})")
        print(f"温度: {data['temperature']['value']:.1f} {data['temperature']['unit']} ({'有效' if data['temperature']['valid'] else '无效'})")
    
    def _log_data(self):
        """记录数据到CSV文件"""
        try:
            with self._lock:
                data = self._latest_data.copy()
            
            with open(self.data_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    data['timestamp'],
                    datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                    data['ph']['value'], data['ph']['valid'],
                    data['tds']['value'], data['tds']['valid'],
                    data['turbidity']['value'], data['turbidity']['valid'],
                    data['dissolved_oxygen']['value'], data['dissolved_oxygen']['valid'],
                    data['temperature']['value'], data['temperature']['valid']
                ])
        except Exception as e:
            print(f"数据记录错误: {e}")

    def _send_mqtt_data(self):
        """发送传感器数据到MQTT主题"""
        if not self.mqtt_enabled or not self.mqtt_client:
            return

        try:
            # 获取JSON格式数据
            json_data = self.get_json_data()

            # 发送到MQTT主题
            result = self.mqtt_client.publish(self.mqtt_topic, json.dumps(json_data))

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"传感器数据已发送到MQTT主题: {self.mqtt_topic}")
            else:
                print(f"MQTT数据发送失败，错误码: {result.rc}")

        except Exception as e:
            print(f"MQTT数据发送错误: {e}")

    def get_latest_data(self):
        """获取最新传感器数据 - 标准API接口供其他模块使用"""
        with self._lock:
            return self._latest_data.copy()
    
    def get_json_data(self):
        """获取JSON格式数据 - 复用data_aggregator格式供web_frontend使用"""
        data = self.get_latest_data()
        
        # 转换为web_frontend兼容的JSON格式
        json_data = {
            'timestamp': data['timestamp'],
            'system': data['system'],
            'sensors': {
                'ph': {
                    'name': 'PH传感器',
                    'value': data['ph']['value'],
                    'unit': data['ph']['unit'],
                    'status': 'normal' if data['ph']['valid'] else 'error'
                },
                'tds': {
                    'name': 'TDS传感器',
                    'value': data['tds']['value'],
                    'unit': data['tds']['unit'],
                    'status': 'normal' if data['tds']['valid'] else 'error'
                },
                'turbidity': {
                    'name': '浊度传感器',
                    'value': data['turbidity']['value'],
                    'unit': data['turbidity']['unit'],
                    'status': 'normal' if data['turbidity']['valid'] else 'error'
                },
                'dissolved_oxygen': {
                    'name': '溶解氧传感器',
                    'value': data['dissolved_oxygen']['value'],
                    'unit': data['dissolved_oxygen']['unit'],
                    'status': 'normal' if data['dissolved_oxygen']['valid'] else 'error'
                },
                'temperature': {
                    'name': '温度传感器',
                    'value': data['temperature']['value'],
                    'unit': data['temperature']['unit'],
                    'status': 'normal' if data['temperature']['valid'] else 'error'
                }
            },
            'status': data['status']
        }
        
        return json_data
    
    def get_sensor_status(self):
        """获取传感器连接状态 - API接口"""
        return {
            'ph_sensor': self.ph_sensor.connected,
            'tds_sensor': self.tds_sensor.connected,
            'turbidity_sensor': self.turbidity_sensor.connected,
            'do_temp_sensor': self.do_temp_sensor.connected,
            'system_running': self.running
        }


# 全局系统实例 - 供其他模块导入使用
water_quality_system = None


def get_water_quality_system():
    """获取水质监测系统实例 - 供其他模块使用的标准接口"""
    global water_quality_system
    if water_quality_system is None:
        water_quality_system = WaterQualitySystem()
    return water_quality_system


def signal_handler(signum, frame):
    """信号处理函数 - 优雅关闭系统"""
    global water_quality_system
    print("\n接收到停止信号，正在关闭系统...")
    if water_quality_system:
        water_quality_system.stop()
    sys.exit(0)


def main():
    """主程序入口"""
    global water_quality_system
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建系统实例
    water_quality_system = WaterQualitySystem()
    
    try:
        # 启动系统
        if water_quality_system.start():
            print("系统启动成功，按Ctrl+C停止")
            print("JSON数据输出示例:")
            
            # 主循环 - 定时输出JSON数据供其他模块使用
            while True:
                time.sleep(5)  # 每5秒输出一次JSON数据
                json_data = water_quality_system.get_json_data()
                print(json.dumps(json_data, ensure_ascii=False, indent=2))
        else:
            print("系统启动失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n用户中断，正在关闭系统...")
    except Exception as e:
        print(f"系统运行错误: {e}")
    finally:
        if water_quality_system:
            water_quality_system.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
