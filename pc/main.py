#!/usr/bin/env python3
# coding: utf-8


import os
import sys
import time
import signal
import threading
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# 添加项目根目录和配置目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'config'))

# 导入Flask相关模块
try:
    from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError as e:
    print(f"警告: Flask库未安装: {e}")
    FLASK_AVAILABLE = False

# 导入统一配置管理
try:
    from config import (
        get_config, get_module_config, get_logger, 
        log_module_status, log_mqtt_traffic, log_error_with_context,
        get_mqtt_connection_config, get_mqtt_topics, get_client_config,
        validate_message, initialize_config_system
    )
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"警告: 配置系统不可用: {e}")
    CONFIG_AVAILABLE = False

# 导入MQTT客户端
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    print("警告: paho-mqtt库未安装，MQTT功能将不可用")
    MQTT_AVAILABLE = False

# 导入数据处理库
try:
    import pandas as pd
    import numpy as np
    from scipy.interpolate import interp1d
    DATA_PROCESSING_AVAILABLE = True
except ImportError:
    print("警告: 数据处理库未安装，部分功能将不可用")
    DATA_PROCESSING_AVAILABLE = False

# 导入机器学习库（可选）
try:
    import tensorflow as tf
    from sklearn.preprocessing import MinMaxScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# 导入环境变量管理
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class PCDataManager:
    """PC端数据管理器 - 管理所有接收的数据"""
    
    def __init__(self):
        self.water_quality_data = []  # 水质数据
        self.position_data = {}  # 定位数据
        self.ai_detection_data = {}  # AI检测数据
        self.system_status_data = {}  # 系统状态数据
        self.prediction_results = {}  # 预测结果
        self.cruise_status = {'active': False, 'current_position': None}  # 巡航状态
        self.data_lock = threading.Lock()  # 数据访问锁
        
        # 获取日志记录器
        if CONFIG_AVAILABLE:
            self.logger = get_logger('pc_data', 'web_server')
        else:
            self.logger = logging.getLogger('pc_data')
    
    def update_water_quality_data(self, data: Dict[str, Any]):
        """更新水质数据"""
        with self.data_lock:
            try:
                # 转换数据格式
                sensor_data = {
                    'timestamp': data.get('timestamp', time.time()),
                    'temperature': data['sensors']['temperature']['value'],
                    'oxygen': data['sensors']['dissolved_oxygen']['value'],
                    'ph': data['sensors']['ph']['value'],
                    'tds': data['sensors']['tds']['value'],
                    'turbidity': data['sensors']['turbidity']['value']
                }
                
                # 转换时间戳为ISO格式
                if isinstance(sensor_data['timestamp'], (int, float)):
                    sensor_data['timestamp'] = datetime.fromtimestamp(sensor_data['timestamp']).isoformat()
                
                self.water_quality_data.append(sensor_data)
                
                # 只保留最近24小时的数据
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.water_quality_data[:] = [d for d in self.water_quality_data
                                           if datetime.fromisoformat(d['timestamp']) > cutoff_time]
                
                self.logger.info("水质数据已更新")
                
            except Exception as e:
                self.logger.error(f"更新水质数据失败: {e}")
    
    def update_position_data(self, data: Dict[str, Any]):
        """更新定位数据"""
        with self.data_lock:
            try:
                self.position_data.update({
                    'timestamp': data.get('timestamp', time.time()),
                    'latitude': data.get('latitude', 0.0),
                    'longitude': data.get('longitude', 0.0),
                    'altitude': data.get('altitude', 0.0),
                    'speed': data.get('speed', 0.0),
                    'course': data.get('course', 0.0),
                    'roll': data.get('roll', 0.0),
                    'pitch': data.get('pitch', 0.0),
                    'yaw': data.get('yaw', 0.0),
                    'pos_accuracy': data.get('pos_accuracy', 0.0),
                    'heading_accuracy': data.get('heading_accuracy', 0.0),
                    'satellites': data.get('satellites', 0),
                    'valid': data.get('valid', False)
                })
                
                self.logger.info(f"定位数据已更新 - 位置: ({self.position_data['latitude']:.6f}, {self.position_data['longitude']:.6f})")
                
            except Exception as e:
                self.logger.error(f"更新定位数据失败: {e}")
    
    def update_ai_detection_data(self, data: Dict[str, Any]):
        """更新AI检测数据"""
        with self.data_lock:
            try:
                self.ai_detection_data.update({
                    'timestamp': data.get('timestamp', time.time()),
                    'detection': data.get('detection', {}),
                    'data_type': data.get('data_type', 'ai_detection')
                })
                
                self.logger.info("AI检测数据已更新")
                
            except Exception as e:
                self.logger.error(f"更新AI检测数据失败: {e}")
    
    def update_system_status_data(self, data: Dict[str, Any]):
        """更新系统状态数据"""
        with self.data_lock:
            try:
                self.system_status_data.update({
                    'timestamp': data.get('timestamp', time.time()),
                    'navigation_state': data.get('navigation_state', 'unknown'),
                    'running': data.get('running', False),
                    'modules': data.get('modules', {}),
                    'hardware': data.get('hardware', {}),
                    'data_type': data.get('data_type', 'system_status')
                })
                
                self.logger.info("系统状态数据已更新")
                
            except Exception as e:
                self.logger.error(f"更新系统状态数据失败: {e}")
    
    def get_latest_data(self) -> Dict[str, Any]:
        """获取最新数据"""
        with self.data_lock:
            return {
                'water_quality': self.water_quality_data[-10:] if self.water_quality_data else [],
                'position': self.position_data.copy(),
                'ai_detection': self.ai_detection_data.copy(),
                'system_status': self.system_status_data.copy(),
                'cruise_status': self.cruise_status.copy()
            }

class PCMQTTManager:
    """PC端MQTT管理器 - 处理MQTT数据接收和指令发送"""
    
    def __init__(self, data_manager: PCDataManager):
        self.data_manager = data_manager
        self.mqtt_client = None
        self.running = False
        
        # 获取日志记录器
        if CONFIG_AVAILABLE:
            self.logger = get_logger('pc_mqtt', 'mqtt')
        else:
            self.logger = logging.getLogger('pc_mqtt')
        
        # 初始化MQTT客户端
        if MQTT_AVAILABLE and CONFIG_AVAILABLE:
            self._init_mqtt_client()
    
    def _init_mqtt_client(self):
        """初始化MQTT客户端"""
        try:
            # 获取MQTT配置
            mqtt_config = get_mqtt_connection_config()
            client_config = get_client_config('pc')
            
            if not mqtt_config or not client_config:
                self.logger.warning("MQTT配置不完整，跳过MQTT初始化")
                return
            
            # 创建MQTT客户端
            client_id = f"{client_config['client_id_prefix']}{int(time.time())}"
            self.mqtt_client = mqtt.Client(client_id=client_id)
            
            # 设置连接参数
            broker_config = mqtt_config['broker']
            if broker_config.get('username'):
                self.mqtt_client.username_pw_set(
                    broker_config['username'], 
                    broker_config.get('password', '')
                )
            
            # 设置回调函数
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            self.mqtt_client.on_message = self._on_mqtt_message
            
            # 连接到MQTT broker
            self.mqtt_client.connect(
                broker_config['host'], 
                broker_config['port'], 
                broker_config['keepalive']
            )
            
            # 启动MQTT循环
            self.mqtt_client.loop_start()
            self.running = True
            
            self.logger.info(f"PC端MQTT客户端初始化成功: {broker_config['host']}:{broker_config['port']}")
            
        except Exception as e:
            self.logger.error(f"PC端MQTT客户端初始化失败: {e}")
            self.mqtt_client = None
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            self.logger.info("PC端MQTT连接成功")
            
            # 订阅数据主题
            if CONFIG_AVAILABLE:
                client_config = get_client_config('pc')
                if client_config and 'subscribe_topics' in client_config:
                    for topic in client_config['subscribe_topics']:
                        client.subscribe(topic, qos=1)
                        self.logger.info(f"订阅MQTT主题: {topic}")
        else:
            self.logger.error(f"PC端MQTT连接失败，返回码: {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        if rc != 0:
            self.logger.warning("PC端MQTT连接意外断开，尝试重连...")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            
            # 记录MQTT流量
            if CONFIG_AVAILABLE:
                log_mqtt_traffic('subscribe', topic, 'data', len(payload))
            
            self.logger.info(f"收到MQTT数据 - 主题: {topic}")
            
            # 根据主题分发数据
            if topic == 'sensor/water_quality':
                self.data_manager.update_water_quality_data(data)
            elif topic == 'navigation/position':
                self.data_manager.update_position_data(data)
            elif topic == 'ai/detection':
                self.data_manager.update_ai_detection_data(data)
            elif topic == 'system/status':
                self.data_manager.update_system_status_data(data)
            else:
                self.logger.warning(f"未知数据主题: {topic}")
            
        except Exception as e:
            self.logger.error(f"处理MQTT消息失败: {e}")
    
    def publish_command(self, topic: str, command: Dict[str, Any]) -> bool:
        """发布指令到板端"""
        try:
            if not self.mqtt_client or not self.running:
                self.logger.error("MQTT客户端未连接")
                return False
            
            payload = json.dumps(command, ensure_ascii=False)
            result = self.mqtt_client.publish(topic, payload, qos=2)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # 记录MQTT流量
                if CONFIG_AVAILABLE:
                    log_mqtt_traffic('publish', topic, 'command', len(payload))
                
                self.logger.info(f"指令发送成功 - 主题: {topic}, 指令: {command.get('command', 'Unknown')}")
                return True
            else:
                self.logger.error(f"指令发送失败 - 返回码: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"发送指令失败: {e}")
            return False
    
    def stop(self):
        """停止MQTT客户端"""
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.logger.info("PC端MQTT客户端已停止")

class PCWebServer:
    """PC端Web服务器 - 基于Flask提供Web界面和API接口"""

    def __init__(self, data_manager: PCDataManager, mqtt_manager: PCMQTTManager):
        self.data_manager = data_manager
        self.mqtt_manager = mqtt_manager
        self.app = None
        self.running = False

        # 获取日志记录器
        if CONFIG_AVAILABLE:
            self.logger = get_logger('pc_web', 'web_server')
            self.web_config = get_config('pc', 'web_server', {})
        else:
            self.logger = logging.getLogger('pc_web')
            self.web_config = {
                'host': '0.0.0.0',
                'port': 5001,
                'debug': False,
                'threaded': True
            }

        # 初始化Flask应用
        if FLASK_AVAILABLE:
            self._init_flask_app()

    def _init_flask_app(self):
        """初始化Flask应用"""
        try:
            self.app = Flask(__name__,
                           static_folder='web/static',
                           template_folder='web/templates')

            # 启用CORS
            CORS(self.app)

            # 注册路由
            self._register_routes()

            self.logger.info("Flask应用初始化成功")

        except Exception as e:
            self.logger.error(f"Flask应用初始化失败: {e}")
            self.app = None

    def _register_routes(self):
        """注册路由"""

        @self.app.route('/')
        def index():
            """主页"""
            return send_from_directory('web', 'index.html')

        @self.app.route('/api/data/latest')
        def get_latest_data():
            """获取最新数据API"""
            try:
                data = self.data_manager.get_latest_data()
                return jsonify({
                    'status': 'success',
                    'data': data,
                    'timestamp': time.time()
                })
            except Exception as e:
                self.logger.error(f"获取最新数据失败: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        @self.app.route('/api/data/water_quality')
        def get_water_quality_data():
            """获取水质数据API"""
            try:
                with self.data_manager.data_lock:
                    data = self.data_manager.water_quality_data.copy()

                return jsonify({
                    'status': 'success',
                    'data': data,
                    'count': len(data)
                })
            except Exception as e:
                self.logger.error(f"获取水质数据失败: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        @self.app.route('/api/data/position')
        def get_position_data():
            """获取定位数据API"""
            try:
                with self.data_manager.data_lock:
                    data = self.data_manager.position_data.copy()

                return jsonify({
                    'status': 'success',
                    'data': data
                })
            except Exception as e:
                self.logger.error(f"获取定位数据失败: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        @self.app.route('/api/command/navigation', methods=['POST'])
        def send_navigation_command():
            """发送导航指令API"""
            try:
                command_data = request.get_json()

                if not command_data or 'command' not in command_data:
                    return jsonify({
                        'status': 'error',
                        'message': '缺少指令参数'
                    }), 400

                # 添加时间戳
                command_data['timestamp'] = time.time()

                # 发送指令
                success = self.mqtt_manager.publish_command('control/navigation', command_data)

                if success:
                    return jsonify({
                        'status': 'success',
                        'message': '导航指令发送成功'
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': '导航指令发送失败'
                    }), 500

            except Exception as e:
                self.logger.error(f"发送导航指令失败: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        @self.app.route('/api/command/medication', methods=['POST'])
        def send_medication_command():
            """发送投药指令API"""
            try:
                command_data = request.get_json()

                if not command_data or 'command' not in command_data:
                    return jsonify({
                        'status': 'error',
                        'message': '缺少指令参数'
                    }), 400

                # 添加时间戳
                command_data['timestamp'] = time.time()

                # 发送指令
                success = self.mqtt_manager.publish_command('control/medication', command_data)

                if success:
                    return jsonify({
                        'status': 'success',
                        'message': '投药指令发送成功'
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': '投药指令发送失败'
                    }), 500

            except Exception as e:
                self.logger.error(f"发送投药指令失败: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        @self.app.route('/api/command/emergency', methods=['POST'])
        def send_emergency_command():
            """发送紧急指令API"""
            try:
                command_data = request.get_json()

                if not command_data or 'command' not in command_data:
                    return jsonify({
                        'status': 'error',
                        'message': '缺少指令参数'
                    }), 400

                # 添加时间戳
                command_data['timestamp'] = time.time()

                # 发送指令
                success = self.mqtt_manager.publish_command('control/emergency', command_data)

                if success:
                    return jsonify({
                        'status': 'success',
                        'message': '紧急指令发送成功'
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': '紧急指令发送失败'
                    }), 500

            except Exception as e:
                self.logger.error(f"发送紧急指令失败: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        @self.app.route('/api/system/status')
        def get_system_status():
            """获取系统状态API"""
            try:
                with self.data_manager.data_lock:
                    system_data = self.data_manager.system_status_data.copy()

                # 添加PC端状态信息
                pc_status = {
                    'pc_running': True,
                    'mqtt_connected': self.mqtt_manager.running,
                    'web_server_running': self.running,
                    'data_count': {
                        'water_quality': len(self.data_manager.water_quality_data),
                        'position': 1 if self.data_manager.position_data else 0,
                        'ai_detection': 1 if self.data_manager.ai_detection_data else 0,
                        'system_status': 1 if self.data_manager.system_status_data else 0
                    }
                }

                return jsonify({
                    'status': 'success',
                    'data': {
                        'board_status': system_data,
                        'pc_status': pc_status
                    }
                })
            except Exception as e:
                self.logger.error(f"获取系统状态失败: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        # 静态文件路由
        @self.app.route('/web/<path:filename>')
        def serve_web_files(filename):
            """提供Web文件"""
            return send_from_directory('web', filename)

    def start(self) -> bool:
        """启动Web服务器"""
        if not self.app:
            self.logger.error("Flask应用未初始化")
            return False

        try:
            self.running = True
            self.logger.info(f"启动Web服务器: {self.web_config['host']}:{self.web_config['port']}")

            # 在单独线程中启动Flask应用
            def run_flask():
                self.app.run(
                    host=self.web_config['host'],
                    port=self.web_config['port'],
                    debug=self.web_config.get('debug', False),
                    threaded=self.web_config.get('threaded', True),
                    use_reloader=False
                )

            self.flask_thread = threading.Thread(target=run_flask, daemon=True)
            self.flask_thread.start()

            self.logger.info("Web服务器启动成功")
            return True

        except Exception as e:
            self.logger.error(f"Web服务器启动失败: {e}")
            self.running = False
            return False

    def stop(self):
        """停止Web服务器"""
        self.running = False
        self.logger.info("Web服务器已停止")

class PCMainSystem:
    """PC端主系统控制器"""

    def __init__(self):
        self.data_manager = PCDataManager()
        self.mqtt_manager = PCMQTTManager(self.data_manager)
        self.web_server = PCWebServer(self.data_manager, self.mqtt_manager)
        self.running = False

        # 获取日志记录器
        if CONFIG_AVAILABLE:
            self.logger = get_logger('pc_system', 'integration')
        else:
            self.logger = logging.getLogger('pc_system')

    def start(self) -> bool:
        """启动PC端系统"""
        self.logger.info("🚀" * 20)
        self.logger.info("鱼群'视'卫智能渔业水环境管理系统 - PC端启动")
        self.logger.info("🚀" * 20)

        # 初始化配置系统
        if CONFIG_AVAILABLE:
            if not initialize_config_system():
                self.logger.error("配置系统初始化失败")
                return False

        # 检查必要的依赖
        if not FLASK_AVAILABLE:
            self.logger.error("Flask库未安装，Web服务器无法启动")
            return False

        # 启动Web服务器
        if not self.web_server.start():
            self.logger.error("Web服务器启动失败")
            return False

        # 等待Web服务器启动
        time.sleep(2)

        self.running = True
        self.logger.info("✅ PC端系统启动成功")

        # 显示系统状态
        self._print_system_status()

        return True

    def stop(self):
        """停止PC端系统"""
        self.logger.info("开始停止PC端系统...")

        self.running = False

        # 停止Web服务器
        self.web_server.stop()

        # 停止MQTT管理器
        self.mqtt_manager.stop()

        self.logger.info("✅ PC端系统已停止")

    def _print_system_status(self):
        """打印系统状态"""
        self.logger.info("\n" + "📊" * 20)
        self.logger.info("PC端系统状态报告")
        self.logger.info("📊" * 20)

        # Web服务器状态
        web_status = "✅" if self.web_server.running else "❌"
        self.logger.info(f"  {web_status} Web服务器: {self.web_server.web_config['host']}:{self.web_server.web_config['port']}")

        # MQTT状态
        mqtt_status = "✅" if self.mqtt_manager.running else "❌"
        self.logger.info(f"  {mqtt_status} MQTT客户端: {'已连接' if self.mqtt_manager.running else '未连接'}")

        # 数据状态
        data = self.data_manager.get_latest_data()
        self.logger.info(f"  📊 数据状态:")
        self.logger.info(f"    - 水质数据: {len(data['water_quality'])} 条")
        self.logger.info(f"    - 定位数据: {'有效' if data['position'].get('valid') else '无效'}")
        self.logger.info(f"    - AI检测: {'有数据' if data['ai_detection'] else '无数据'}")
        self.logger.info(f"    - 系统状态: {'运行中' if data['system_status'].get('running') else '未知'}")

        # 功能模块状态
        self.logger.info(f"  🔧 功能模块:")
        self.logger.info(f"    - Flask: {'✅' if FLASK_AVAILABLE else '❌'}")
        self.logger.info(f"    - MQTT: {'✅' if MQTT_AVAILABLE else '❌'}")
        self.logger.info(f"    - 数据处理: {'✅' if DATA_PROCESSING_AVAILABLE else '❌'}")
        self.logger.info(f"    - 机器学习: {'✅' if ML_AVAILABLE else '❌'}")
        self.logger.info(f"    - 配置系统: {'✅' if CONFIG_AVAILABLE else '❌'}")

    def run(self):
        """运行系统（阻塞模式）"""
        if not self.start():
            return False

        try:
            self.logger.info("PC端系统运行中... (按 Ctrl+C 停止)")
            self.logger.info(f"Web界面访问地址: http://{self.web_server.web_config['host']}:{self.web_server.web_config['port']}")

            while self.running:
                time.sleep(30)  # 每30秒打印一次状态
                if self.running:
                    self._print_system_status()

        except KeyboardInterrupt:
            self.logger.info("收到停止信号...")
        finally:
            self.stop()

        return True

def signal_handler(signum, frame):
    """信号处理器"""
    print(f"收到信号 {signum}，准备停止系统...")
    sys.exit(0)

def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("鱼群'视'卫智能渔业水环境管理系统 - PC端主程序")
    print("=" * 60)

    # 创建并运行PC端系统
    pc_system = PCMainSystem()
    success = pc_system.run()

    if success:
        print("PC端系统正常退出")
        return 0
    else:
        print("PC端系统异常退出")
        return 1

if __name__ == "__main__":
    sys.exit(main())
