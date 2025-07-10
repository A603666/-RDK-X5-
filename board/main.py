#!/usr/bin/env python3
# coding: utf-8


import os
import sys
import time
import signal
import threading
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

# 添加项目根目录和配置目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'config'))

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

class BoardModuleManager:
    """板端模块管理器 - 基于integration_main.py的ModuleManager架构优化"""
    
    def __init__(self):
        self.modules = {}  # 模块进程字典
        self.running = False  # 系统运行状态
        self.monitor_thread = None  # 监控线程
        self.mqtt_client = None  # MQTT客户端
        self.command_queue = []  # 指令队列
        self.command_lock = threading.Lock()  # 指令队列锁
        
        # 获取日志记录器
        if CONFIG_AVAILABLE:
            self.logger = get_logger('board_main', 'integration')
            board_modules_config = get_config('board_modules', default={})
            # 转换配置格式以兼容原有结构
            self.module_configs = {}
            for module_id, config in board_modules_config.items():
                if config.get('enabled', True):
                    self.module_configs[module_id] = {
                        'name': config.get('name', module_id),
                        'path': self._get_module_path(module_id),
                        'cwd': self._get_module_cwd(module_id),
                        'enabled': config.get('enabled', True),
                        'required': config.get('required', False),
                        'startup_delay': config.get('startup_delay', 0)
                    }
        else:
            import logging
            self.logger = logging.getLogger('board_main')
            self.module_configs = self._get_default_module_configs()
        
        # 初始化MQTT客户端
        if MQTT_AVAILABLE and CONFIG_AVAILABLE:
            self._init_mqtt_client()

    def _get_module_path(self, module_id: str) -> str:
        """获取模块路径"""
        module_paths = {
            'sensor': 'legacy/传感器/main.py',
            'positioning': 'legacy/定位模块 copy/MAIN.py',
            'navigation': 'legacy/导航避障模块/navigation_system.py',
            'ai_detection': 'legacy/目标检测/目标检测/针对HSV空间V通道的CLAHE增强.py',
            'motor_control': 'legacy/电机驱动可以运行版本 copy/main.py'
        }
        return module_paths.get(module_id, '')

    def _get_module_cwd(self, module_id: str) -> str:
        """获取模块工作目录"""
        module_cwds = {
            'sensor': 'legacy/传感器',
            'positioning': 'legacy/定位模块 copy',
            'navigation': 'legacy/导航避障模块',
            'ai_detection': 'legacy/目标检测/目标检测',
            'motor_control': 'legacy/电机驱动可以运行版本 copy'
        }
        return module_cwds.get(module_id, '')
    
    def _get_default_module_configs(self) -> Dict[str, Any]:
        """获取默认模块配置（配置系统不可用时的备用方案）"""
        return {
            'sensor': {
                'name': '传感器模块',
                'path': 'legacy/传感器/main.py',
                'cwd': 'legacy/传感器',
                'enabled': True,
                'required': True,
                'startup_delay': 2
            },
            'positioning': {
                'name': '定位模块',
                'path': 'legacy/定位模块 copy/MAIN.py',
                'cwd': 'legacy/定位模块 copy',
                'enabled': True,
                'required': True,
                'startup_delay': 3
            },
            'navigation': {
                'name': '导航避障模块',
                'path': 'legacy/导航避障模块/navigation_system.py',
                'cwd': 'legacy/导航避障模块',
                'enabled': True,
                'required': True,
                'startup_delay': 4
            },
            'ai_detection': {
                'name': 'AI检测模块',
                'path': 'legacy/目标检测/目标检测/针对HSV空间V通道的CLAHE增强.py',
                'cwd': 'legacy/目标检测/目标检测',
                'enabled': True,
                'required': False,
                'startup_delay': 5
            },
            'motor_control': {
                'name': '电机控制模块',
                'path': 'legacy/电机驱动可以运行版本 copy/main.py',
                'cwd': 'legacy/电机驱动可以运行版本 copy',
                'enabled': True,
                'required': True,
                'startup_delay': 1
            }
        }
    
    def _init_mqtt_client(self):
        """初始化MQTT客户端"""
        try:
            # 获取MQTT配置
            mqtt_config = get_mqtt_connection_config()
            client_config = get_client_config('board')
            
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
            
            self.logger.info(f"MQTT客户端初始化成功: {broker_config['host']}:{broker_config['port']}")
            
        except Exception as e:
            self.logger.error(f"MQTT客户端初始化失败: {e}")
            self.mqtt_client = None
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            self.logger.info("MQTT连接成功")
            
            # 订阅指令主题
            if CONFIG_AVAILABLE:
                client_config = get_client_config('board')
                if client_config and 'subscribe_topics' in client_config:
                    for topic in client_config['subscribe_topics']:
                        client.subscribe(topic, qos=1)
                        self.logger.info(f"订阅MQTT主题: {topic}")
        else:
            self.logger.error(f"MQTT连接失败，返回码: {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        if rc != 0:
            self.logger.warning("MQTT连接意外断开，尝试重连...")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # 记录MQTT流量
            if CONFIG_AVAILABLE:
                log_mqtt_traffic('subscribe', topic, 'command', len(payload))
            
            # 解析指令
            command_data = json.loads(payload)
            
            # 添加到指令队列
            with self.command_lock:
                self.command_queue.append({
                    'topic': topic,
                    'command': command_data,
                    'timestamp': time.time()
                })
            
            self.logger.info(f"收到指令: {topic} - {command_data.get('command', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"处理MQTT消息失败: {e}")
    
    def check_module_dependencies(self) -> bool:
        """检查模块依赖和文件存在性"""
        self.logger.info("检查模块依赖和文件...")
        
        missing_files = []
        enabled_modules = {
            k: v for k, v in self.module_configs.items() 
            if v.get('enabled', True)
        }
        
        for module_id, config in enabled_modules.items():
            module_path = config['path']
            if not os.path.exists(module_path):
                missing_files.append(f"{config['name']}: {module_path}")
                if config.get('required', False):
                    self.logger.error(f"必需模块文件不存在: {module_path}")
                else:
                    self.logger.warning(f"可选模块文件不存在: {module_path}")
        
        if missing_files:
            self.logger.warning("以下模块文件不存在:")
            for file in missing_files:
                self.logger.warning(f"  - {file}")
        
        # 检查必需模块
        required_missing = [
            config['name'] for module_id, config in enabled_modules.items()
            if config.get('required', False) and not os.path.exists(config['path'])
        ]
        
        if required_missing:
            self.logger.error(f"缺少必需模块: {', '.join(required_missing)}")
            return False
        
        self.logger.info("✓ 模块依赖检查完成")
        return True
    
    def start_module(self, module_id: str) -> bool:
        """启动单个模块"""
        if module_id not in self.module_configs:
            self.logger.error(f"未知模块: {module_id}")
            return False
        
        config = self.module_configs[module_id]
        
        # 检查模块是否启用
        if not config.get('enabled', True):
            self.logger.info(f"模块已禁用，跳过: {config['name']}")
            return True
        
        if not os.path.exists(config['path']):
            if config.get('required', False):
                self.logger.error(f"模块文件不存在: {config['path']}")
                return False
            else:
                self.logger.warning(f"可选模块文件不存在，跳过: {config['path']}")
                return True
        
        try:
            self.logger.info(f"启动模块: {config['name']}")
            
            # 记录模块状态
            if CONFIG_AVAILABLE:
                log_module_status(module_id, 'starting', f"正在启动{config['name']}")
            
            # 启动模块进程
            process = subprocess.Popen(
                [sys.executable, config['path']],
                cwd=config['cwd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            self.modules[module_id] = {
                'process': process,
                'config': config,
                'start_time': time.time(),
                'status': 'starting',
                'restart_count': 0
            }
            
            self.logger.info(f"✓ {config['name']} 启动成功 (PID: {process.pid})")
            
            # 记录模块状态
            if CONFIG_AVAILABLE:
                log_module_status(module_id, 'running', f"{config['name']}运行正常")
            
            return True
            
        except Exception as e:
            self.logger.error(f"启动模块失败 {config['name']}: {e}")
            
            # 记录错误
            if CONFIG_AVAILABLE:
                log_module_status(module_id, 'error', f"启动失败: {str(e)}")
                log_error_with_context('module_start', e, {
                    'module_id': module_id,
                    'module_name': config['name'],
                    'module_path': config['path']
                })
            
            return False

    def stop_module(self, module_id: str) -> bool:
        """停止单个模块"""
        if module_id not in self.modules:
            self.logger.warning(f"模块未运行: {module_id}")
            return True

        module_info = self.modules[module_id]
        process = module_info['process']
        config = module_info['config']

        try:
            self.logger.info(f"停止模块: {config['name']}")

            # 记录模块状态
            if CONFIG_AVAILABLE:
                log_module_status(module_id, 'stopping', f"正在停止{config['name']}")

            # 优雅停止
            process.terminate()

            # 等待进程结束
            try:
                process.wait(timeout=10)
                self.logger.info(f"✓ {config['name']} 已停止")
            except subprocess.TimeoutExpired:
                self.logger.warning(f"强制终止模块: {config['name']}")
                process.kill()
                process.wait()

            # 记录模块状态
            if CONFIG_AVAILABLE:
                log_module_status(module_id, 'stopped', f"{config['name']}已停止")

            del self.modules[module_id]
            return True

        except Exception as e:
            self.logger.error(f"停止模块失败 {config['name']}: {e}")

            # 记录错误
            if CONFIG_AVAILABLE:
                log_error_with_context('module_stop', e, {
                    'module_id': module_id,
                    'module_name': config['name']
                })

            return False

    def start_all_modules(self) -> bool:
        """启动所有模块"""
        self.logger.info("开始启动所有模块...")

        if not self.check_module_dependencies():
            return False

        # 获取启用的模块
        enabled_modules = {
            k: v for k, v in self.module_configs.items()
            if v.get('enabled', True)
        }

        success_count = 0
        total_count = len(enabled_modules)

        # 按启动延迟顺序启动模块
        sorted_modules = sorted(
            enabled_modules.items(),
            key=lambda x: x[1].get('startup_delay', 0)
        )

        for module_id, config in sorted_modules:
            if self.start_module(module_id):
                success_count += 1

                # 启动延迟
                startup_delay = config.get('startup_delay', 0)
                if startup_delay > 0:
                    self.logger.info(f"等待 {startup_delay} 秒后启动下一个模块...")
                    time.sleep(startup_delay)
            else:
                if config.get('required', False):
                    self.logger.error(f"必需模块启动失败: {config['name']}")
                    self.stop_all_modules()
                    return False

        self.logger.info(f"模块启动完成: {success_count}/{total_count}")

        # 启动监控线程
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_modules, daemon=True)
        self.monitor_thread.start()

        # 启动指令处理线程
        self.command_thread = threading.Thread(target=self._process_commands, daemon=True)
        self.command_thread.start()

        return success_count > 0

    def stop_all_modules(self):
        """停止所有模块"""
        self.logger.info("开始停止所有模块...")

        self.running = False

        # 停止监控线程
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

        # 停止指令处理线程
        if hasattr(self, 'command_thread') and self.command_thread.is_alive():
            self.command_thread.join(timeout=5)

        # 停止所有模块
        for module_id in list(self.modules.keys()):
            self.stop_module(module_id)

        # 停止MQTT客户端
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

        self.logger.info("所有模块已停止")

    def _monitor_modules(self):
        """监控模块状态"""
        self.logger.info("开始模块状态监控...")

        while self.running:
            try:
                for module_id, module_info in list(self.modules.items()):
                    process = module_info['process']
                    config = module_info['config']

                    # 检查进程状态
                    if process.poll() is not None:
                        # 进程已结束
                        return_code = process.returncode
                        self.logger.error(f"模块异常退出: {config['name']} (返回码: {return_code})")

                        # 读取错误输出
                        try:
                            stderr_output = process.stderr.read()
                            if stderr_output:
                                self.logger.error(f"错误输出: {stderr_output}")
                        except:
                            pass

                        # 记录模块状态
                        if CONFIG_AVAILABLE:
                            log_module_status(module_id, 'error', f"异常退出，返回码: {return_code}")

                        # 从监控列表中移除
                        del self.modules[module_id]

                        # 如果是必需模块，尝试重启
                        if config.get('required', False) and module_info['restart_count'] < 3:
                            self.logger.info(f"尝试重启必需模块: {config['name']}")
                            time.sleep(5)  # 等待5秒后重启
                            if self.start_module(module_id):
                                self.modules[module_id]['restart_count'] = module_info['restart_count'] + 1
                    else:
                        # 更新模块状态
                        module_info['status'] = 'running'

                time.sleep(10)  # 每10秒检查一次

            except Exception as e:
                self.logger.error(f"模块监控错误: {e}")
                time.sleep(5)

        self.logger.info("模块状态监控已停止")

    def _process_commands(self):
        """处理MQTT指令队列"""
        self.logger.info("开始指令处理...")

        while self.running:
            try:
                # 检查指令队列
                with self.command_lock:
                    if self.command_queue:
                        command_item = self.command_queue.pop(0)
                    else:
                        command_item = None

                if command_item:
                    self._handle_command(command_item)

                time.sleep(0.1)  # 100ms检查一次

            except Exception as e:
                self.logger.error(f"指令处理错误: {e}")
                time.sleep(1)

        self.logger.info("指令处理已停止")

    def _handle_command(self, command_item: Dict[str, Any]):
        """处理单个指令"""
        try:
            topic = command_item['topic']
            command_data = command_item['command']
            command = command_data.get('command', '')

            self.logger.info(f"处理指令: {command} (来源: {topic})")

            # 根据指令类型处理
            if 'emergency' in topic:
                self._handle_emergency_command(command_data)
            elif 'navigation' in topic:
                self._handle_navigation_command(command_data)
            elif 'medication' in topic:
                self._handle_medication_command(command_data)
            elif 'system' in topic:
                self._handle_system_command(command_data)
            else:
                self.logger.warning(f"未知指令主题: {topic}")

        except Exception as e:
            self.logger.error(f"指令处理失败: {e}")

    def _handle_emergency_command(self, command_data: Dict[str, Any]):
        """处理紧急指令"""
        command = command_data.get('command', '')

        if command == 'EMERGENCY_STOP':
            self.logger.warning("收到紧急停止指令")
            # 这里可以添加紧急停止逻辑
        elif command == 'EMERGENCY_RETURN':
            self.logger.warning("收到紧急返回指令")
            # 这里可以添加紧急返回逻辑

    def _handle_navigation_command(self, command_data: Dict[str, Any]):
        """处理导航指令"""
        command = command_data.get('command', '')
        self.logger.info(f"处理导航指令: {command}")
        # 这里可以添加导航指令转发逻辑

    def _handle_medication_command(self, command_data: Dict[str, Any]):
        """处理投药指令"""
        command = command_data.get('command', '')
        self.logger.info(f"处理投药指令: {command}")
        # 这里可以添加投药指令转发逻辑

    def _handle_system_command(self, command_data: Dict[str, Any]):
        """处理系统指令"""
        command = command_data.get('command', '')

        if command == 'GET_SYSTEM_STATUS':
            status = self.get_system_status()
            self.logger.info(f"系统状态: {status}")
        elif command == 'RESTART_MODULE':
            module_name = command_data.get('module_name', '')
            if module_name in self.modules:
                self.logger.info(f"重启模块: {module_name}")
                self.stop_module(module_name)
                time.sleep(2)
                self.start_module(module_name)

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        enabled_modules = {
            k: v for k, v in self.module_configs.items()
            if v.get('enabled', True)
        }

        status = {
            'timestamp': time.time(),
            'total_modules': len(enabled_modules),
            'running_modules': len(self.modules),
            'mqtt_connected': self.mqtt_client is not None and self.mqtt_client.is_connected(),
            'modules': {}
        }

        for module_id, config in enabled_modules.items():
            if module_id in self.modules:
                module_info = self.modules[module_id]
                uptime = time.time() - module_info['start_time']
                status['modules'][module_id] = {
                    'name': config['name'],
                    'status': module_info['status'],
                    'pid': module_info['process'].pid,
                    'uptime': uptime,
                    'restart_count': module_info.get('restart_count', 0)
                }
            else:
                status['modules'][module_id] = {
                    'name': config['name'],
                    'status': 'stopped',
                    'pid': None,
                    'uptime': 0,
                    'restart_count': 0
                }

        return status

    def print_system_status(self):
        """打印系统状态"""
        status = self.get_system_status()

        self.logger.info("\n" + "📊" * 20)
        self.logger.info("板端系统状态报告")
        self.logger.info("📊" * 20)
        self.logger.info(f"运行模块: {status['running_modules']}/{status['total_modules']}")
        self.logger.info(f"MQTT连接: {'✅' if status['mqtt_connected'] else '❌'}")

        for module_id, module_info in status['modules'].items():
            status_icon = "✅" if module_info['status'] == 'running' else "❌"
            uptime_str = f"{module_info['uptime']:.1f}s" if module_info['uptime'] > 0 else "N/A"
            pid_str = f"PID:{module_info['pid']}" if module_info['pid'] else "未运行"
            restart_str = f"重启:{module_info['restart_count']}次" if module_info['restart_count'] > 0 else ""

            self.logger.info(f"  {status_icon} {module_info['name']}: {module_info['status']} ({pid_str}, 运行时间:{uptime_str} {restart_str})")

class BoardMainSystem:
    """板端主系统控制器"""

    def __init__(self):
        self.module_manager = BoardModuleManager()
        self.running = False

        # 获取日志记录器
        if CONFIG_AVAILABLE:
            self.logger = get_logger('board_system', 'integration')
        else:
            import logging
            self.logger = logging.getLogger('board_system')

    def start(self) -> bool:
        """启动板端系统"""
        self.logger.info("🚀" * 20)
        self.logger.info("鱼群'视'卫智能渔业水环境管理系统 - 板端启动")
        self.logger.info("🚀" * 20)

        # 初始化配置系统
        if CONFIG_AVAILABLE:
            if not initialize_config_system():
                self.logger.error("配置系统初始化失败")
                return False

        # 启动所有模块
        if not self.module_manager.start_all_modules():
            self.logger.error("模块启动失败")
            return False

        self.running = True
        self.logger.info("✅ 板端系统启动成功")

        # 显示系统状态
        self.module_manager.print_system_status()

        return True

    def stop(self):
        """停止板端系统"""
        self.logger.info("开始停止板端系统...")

        self.running = False
        self.module_manager.stop_all_modules()

        self.logger.info("✅ 板端系统已停止")

    def run(self):
        """运行系统（阻塞模式）"""
        if not self.start():
            return False

        try:
            self.logger.info("板端系统运行中... (按 Ctrl+C 停止)")

            while self.running:
                time.sleep(30)  # 每30秒打印一次状态
                if self.running:
                    self.module_manager.print_system_status()

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

    print("鱼群'视'卫智能渔业水环境管理系统 - 板端主程序")
    print("=" * 60)

    # 创建并运行板端系统
    board_system = BoardMainSystem()
    success = board_system.run()

    if success:
        print("板端系统正常退出")
        return 0
    else:
        print("板端系统异常退出")
        return 1

if __name__ == "__main__":
    sys.exit(main())
