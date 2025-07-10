#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鱼群'视'卫智能渔业水环境管理系统 - 系统集成主程序
统一启动所有板端模块，集成MQTT通信和数据传输，提供系统状态监控和日志记录

"""

import os
import sys
import time
import signal
import threading
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integration_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('IntegrationMain')

class ModuleManager:
    """模块管理器 - 统一管理所有板端模块"""
    
    def __init__(self):
        self.modules = {}  # 模块进程字典
        self.module_configs = {
            'sensor': {
                'name': '传感器模块',
                'path': '传感器/main.py',
                'cwd': '传感器',
                'required': True,
                'startup_delay': 2
            },
            'positioning': {
                'name': '定位模块',
                'path': '定位模块 copy/MAIN.py',
                'cwd': '定位模块 copy',
                'required': True,
                'startup_delay': 3
            },
            'navigation': {
                'name': '导航避障模块',
                'path': '导航避障模块/navigation_system.py',
                'cwd': '导航避障模块',
                'required': True,
                'startup_delay': 4
            },
            'ai_detection': {
                'name': 'AI检测模块',
                'path': '目标检测/目标检测/针对HSV空间V通道的CLAHE增强.py',
                'cwd': '目标检测/目标检测',
                'required': False,  # AI检测模块可选
                'startup_delay': 5
            }
        }
        self.running = False
        self.monitor_thread = None
        
    def check_module_dependencies(self) -> bool:
        """检查模块依赖和文件存在性"""
        logger.info("检查模块依赖和文件...")
        
        missing_files = []
        for module_id, config in self.module_configs.items():
            module_path = config['path']
            if not os.path.exists(module_path):
                missing_files.append(f"{config['name']}: {module_path}")
                if config['required']:
                    logger.error(f"必需模块文件不存在: {module_path}")
                else:
                    logger.warning(f"可选模块文件不存在: {module_path}")
        
        if missing_files:
            logger.warning("以下模块文件不存在:")
            for file in missing_files:
                logger.warning(f"  - {file}")
        
        # 检查必需模块
        required_missing = [
            config['name'] for module_id, config in self.module_configs.items()
            if config['required'] and not os.path.exists(config['path'])
        ]
        
        if required_missing:
            logger.error(f"缺少必需模块: {', '.join(required_missing)}")
            return False
        
        logger.info("✓ 模块依赖检查完成")
        return True
    
    def start_module(self, module_id: str) -> bool:
        """启动单个模块"""
        if module_id not in self.module_configs:
            logger.error(f"未知模块: {module_id}")
            return False
        
        config = self.module_configs[module_id]
        
        if not os.path.exists(config['path']):
            if config['required']:
                logger.error(f"模块文件不存在: {config['path']}")
                return False
            else:
                logger.warning(f"可选模块文件不存在，跳过: {config['path']}")
                return True
        
        try:
            logger.info(f"启动模块: {config['name']}")
            
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
                'status': 'starting'
            }
            
            logger.info(f"✓ {config['name']} 启动成功 (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"启动模块失败 {config['name']}: {e}")
            return False
    
    def stop_module(self, module_id: str) -> bool:
        """停止单个模块"""
        if module_id not in self.modules:
            logger.warning(f"模块未运行: {module_id}")
            return True
        
        module_info = self.modules[module_id]
        process = module_info['process']
        config = module_info['config']
        
        try:
            logger.info(f"停止模块: {config['name']}")
            
            # 优雅停止
            process.terminate()
            
            # 等待进程结束
            try:
                process.wait(timeout=10)
                logger.info(f"✓ {config['name']} 已停止")
            except subprocess.TimeoutExpired:
                logger.warning(f"强制终止模块: {config['name']}")
                process.kill()
                process.wait()
            
            del self.modules[module_id]
            return True
            
        except Exception as e:
            logger.error(f"停止模块失败 {config['name']}: {e}")
            return False
    
    def start_all_modules(self) -> bool:
        """启动所有模块"""
        logger.info("开始启动所有模块...")
        
        if not self.check_module_dependencies():
            return False
        
        success_count = 0
        total_count = len(self.module_configs)
        
        # 按启动延迟顺序启动模块
        sorted_modules = sorted(
            self.module_configs.items(),
            key=lambda x: x[1]['startup_delay']
        )
        
        for module_id, config in sorted_modules:
            if self.start_module(module_id):
                success_count += 1
                
                # 启动延迟
                if config['startup_delay'] > 0:
                    logger.info(f"等待 {config['startup_delay']} 秒后启动下一个模块...")
                    time.sleep(config['startup_delay'])
            else:
                if config['required']:
                    logger.error(f"必需模块启动失败: {config['name']}")
                    self.stop_all_modules()
                    return False
        
        logger.info(f"模块启动完成: {success_count}/{total_count}")
        
        # 启动监控线程
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_modules, daemon=True)
        self.monitor_thread.start()
        
        return success_count > 0
    
    def stop_all_modules(self):
        """停止所有模块"""
        logger.info("开始停止所有模块...")
        
        self.running = False
        
        # 停止监控线程
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        # 停止所有模块
        for module_id in list(self.modules.keys()):
            self.stop_module(module_id)
        
        logger.info("所有模块已停止")
    
    def _monitor_modules(self):
        """监控模块状态"""
        logger.info("开始模块状态监控...")
        
        while self.running:
            try:
                for module_id, module_info in list(self.modules.items()):
                    process = module_info['process']
                    config = module_info['config']
                    
                    # 检查进程状态
                    if process.poll() is not None:
                        # 进程已结束
                        return_code = process.returncode
                        logger.error(f"模块异常退出: {config['name']} (返回码: {return_code})")
                        
                        # 读取错误输出
                        try:
                            stderr_output = process.stderr.read()
                            if stderr_output:
                                logger.error(f"错误输出: {stderr_output}")
                        except:
                            pass
                        
                        # 从监控列表中移除
                        del self.modules[module_id]
                        
                        # 如果是必需模块，尝试重启
                        if config['required']:
                            logger.info(f"尝试重启必需模块: {config['name']}")
                            time.sleep(5)  # 等待5秒后重启
                            self.start_module(module_id)
                    else:
                        # 更新模块状态
                        module_info['status'] = 'running'
                
                time.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                logger.error(f"模块监控错误: {e}")
                time.sleep(5)
        
        logger.info("模块状态监控已停止")
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        status = {
            'timestamp': time.time(),
            'total_modules': len(self.module_configs),
            'running_modules': len(self.modules),
            'modules': {}
        }
        
        for module_id, config in self.module_configs.items():
            if module_id in self.modules:
                module_info = self.modules[module_id]
                uptime = time.time() - module_info['start_time']
                status['modules'][module_id] = {
                    'name': config['name'],
                    'status': module_info['status'],
                    'pid': module_info['process'].pid,
                    'uptime': uptime
                }
            else:
                status['modules'][module_id] = {
                    'name': config['name'],
                    'status': 'stopped',
                    'pid': None,
                    'uptime': 0
                }
        
        return status

class IntegrationSystem:
    """系统集成主控制器"""
    
    def __init__(self):
        self.module_manager = ModuleManager()
        self.running = False
        
    def start(self) -> bool:
        """启动集成系统"""
        logger.info("🚀" * 20)
        logger.info("鱼群'视'卫智能渔业水环境管理系统启动")
        logger.info("🚀" * 20)
        
        # 启动所有模块
        if not self.module_manager.start_all_modules():
            logger.error("模块启动失败")
            return False
        
        self.running = True
        logger.info("✅ 系统集成启动成功")
        
        # 显示系统状态
        self.print_system_status()
        
        return True
    
    def stop(self):
        """停止集成系统"""
        logger.info("开始停止系统集成...")
        
        self.running = False
        self.module_manager.stop_all_modules()
        
        logger.info("✅ 系统集成已停止")
    
    def print_system_status(self):
        """打印系统状态"""
        status = self.module_manager.get_system_status()
        
        logger.info("\n" + "📊" * 20)
        logger.info("系统状态报告")
        logger.info("📊" * 20)
        logger.info(f"运行模块: {status['running_modules']}/{status['total_modules']}")
        
        for module_id, module_info in status['modules'].items():
            status_icon = "✅" if module_info['status'] == 'running' else "❌"
            uptime_str = f"{module_info['uptime']:.1f}s" if module_info['uptime'] > 0 else "N/A"
            pid_str = f"PID:{module_info['pid']}" if module_info['pid'] else "未运行"
            
            logger.info(f"  {status_icon} {module_info['name']}: {module_info['status']} ({pid_str}, 运行时间:{uptime_str})")
    
    def run(self):
        """运行系统（阻塞模式）"""
        if not self.start():
            return False
        
        try:
            logger.info("系统运行中... (按 Ctrl+C 停止)")
            
            while self.running:
                time.sleep(30)  # 每30秒打印一次状态
                if self.running:
                    self.print_system_status()
                    
        except KeyboardInterrupt:
            logger.info("收到停止信号...")
        finally:
            self.stop()
        
        return True

def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"收到信号 {signum}，准备停止系统...")
    sys.exit(0)

def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("鱼群'视'卫智能渔业水环境管理系统 - 集成主程序")
    print("=" * 60)
    
    # 创建并运行集成系统
    integration_system = IntegrationSystem()
    success = integration_system.run()
    
    if success:
        logger.info("系统正常退出")
        return 0
    else:
        logger.error("系统异常退出")
        return 1

if __name__ == "__main__":
    sys.exit(main())
