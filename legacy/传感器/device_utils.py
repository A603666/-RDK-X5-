# coding: utf-8
# 设备检测和诊断工具模块 - RDKX5开发板专用
# 提供串口设备自动检测、权限检查、错误诊断和修复功能

import os
import stat
import subprocess
import serial
import time
import grp
import pwd
from typing import List, Dict, Optional, Tuple
from config import DEVICE_DETECTION_CONFIG

class DeviceDetector:
    """设备检测和诊断工具类"""
    
    def __init__(self):
        self.config = DEVICE_DETECTION_CONFIG
        self.available_ports = []  # 可用串口设备列表
        self.permission_issues = []  # 权限问题列表
        self.diagnostic_info = {}  # 诊断信息
    
    def detect_serial_ports(self) -> List[str]:
        """检测RDKX5开发板中可用的串口设备"""
        available_ports = []

        print("正在检测可用串口设备...")

        for port_path in self.config['common_serial_paths']:
            if self._check_port_exists(port_path):
                if self._test_port_access(port_path):
                    available_ports.append(port_path)
                    print(f"✓ 发现可用串口: {port_path}")
                else:
                    print(f"✗ 串口存在但无法访问: {port_path}")
                    self.permission_issues.append(port_path)

        self.available_ports = available_ports
        print(f"检测完成，共发现 {len(available_ports)} 个可用串口设备")
        return available_ports
    
    def _check_port_exists(self, port_path: str) -> bool:
        """检查串口设备是否存在"""
        return os.path.exists(port_path) and stat.S_ISCHR(os.stat(port_path).st_mode)
    
    def _test_port_access(self, port_path: str) -> bool:
        """测试串口设备访问权限"""
        try:
            # 尝试打开串口设备进行读写测试
            with serial.Serial(port_path, 9600, timeout=0.1) as ser:
                return True
        except (serial.SerialException, PermissionError, OSError):
            return False
    
    def check_user_permissions(self) -> Dict[str, bool]:
        """检查当前用户的串口访问权限"""
        permission_status = {}
        current_user = pwd.getpwuid(os.getuid()).pw_name
        user_groups = [g.gr_name for g in grp.getgrall() if current_user in g.gr_mem]

        print(f"当前用户: {current_user}")
        print(f"用户组: {', '.join(user_groups)}")

        for required_group in self.config['required_groups']:
            has_permission = required_group in user_groups
            permission_status[required_group] = has_permission
            status_symbol = "✓" if has_permission else "✗"
            print(f"{status_symbol} {required_group}组权限: {'有' if has_permission else '无'}")

        return permission_status
    
    def fix_permissions(self) -> bool:
        """尝试修复串口设备权限问题"""
        if not self.config['fix_permissions']:
            return False

        print("尝试修复串口设备权限...")
        current_user = pwd.getpwuid(os.getuid()).pw_name

        try:
            # 尝试将用户添加到dialout组
            for group in self.config['required_groups']:
                cmd = f"sudo usermod -a -G {group} {current_user}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✓ 已将用户 {current_user} 添加到 {group} 组")
                else:
                    print(f"✗ 无法添加用户到 {group} 组: {result.stderr}")

            print("权限修复完成，请重新登录或重启系统使权限生效")
            return True
        except Exception as e:
            print(f"权限修复失败: {e}")
            return False
    
    def find_best_port(self, preferred_ports: List[str]) -> Optional[str]:
        """从首选端口列表中找到最佳可用端口"""
        # 首先检测所有可用端口
        if not self.available_ports:
            self.detect_serial_ports()
        
        # 按优先级查找可用端口
        for preferred_port in preferred_ports:
            if preferred_port in self.available_ports:
                print(f"找到首选串口设备: {preferred_port}")
                return preferred_port
        
        # 如果首选端口都不可用，返回第一个可用端口
        if self.available_ports:
            fallback_port = self.available_ports[0]
            print(f"使用备用串口设备: {fallback_port}")
            return fallback_port
        
        print("未找到任何可用的串口设备")
        return None
    
    def run_diagnostics(self) -> Dict[str, str]:
        """运行系统诊断命令"""
        print("运行系统诊断...")
        diagnostic_results = {}
        
        for cmd in self.config['diagnostic_commands']:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                diagnostic_results[cmd] = result.stdout if result.returncode == 0 else result.stderr
                print(f"✓ 执行命令: {cmd}")
            except subprocess.TimeoutExpired:
                diagnostic_results[cmd] = "命令执行超时"
                print(f"✗ 命令超时: {cmd}")
            except Exception as e:
                diagnostic_results[cmd] = f"命令执行错误: {e}"
                print(f"✗ 命令错误: {cmd}")
        
        self.diagnostic_info = diagnostic_results
        return diagnostic_results
    
    def generate_diagnostic_report(self) -> str:
        """生成详细的诊断报告"""
        report = []
        report.append("=== RDKX5串口设备诊断报告 ===")
        report.append(f"检测时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 可用端口信息
        report.append("可用串口设备:")
        if self.available_ports:
            for port in self.available_ports:
                report.append(f"  ✓ {port}")
        else:
            report.append("  ✗ 未发现可用串口设备")
        report.append("")
        
        # 权限问题
        if self.permission_issues:
            report.append("权限问题:")
            for port in self.permission_issues:
                report.append(f"  ✗ {port} - 权限不足")
            report.append("")
        
        # 用户权限状态
        permission_status = self.check_user_permissions()
        report.append("用户权限状态:")
        for group, has_permission in permission_status.items():
            status = "✓" if has_permission else "✗"
            report.append(f"  {status} {group}组权限")
        report.append("")
        
        # 系统诊断信息
        if self.diagnostic_info:
            report.append("系统诊断信息:")
            for cmd, output in self.diagnostic_info.items():
                report.append(f"命令: {cmd}")
                report.append(f"输出: {output[:200]}...")  # 限制输出长度
                report.append("")
        
        # 解决建议
        report.append("解决建议:")
        if not self.available_ports:
            report.append("  1. 检查串口硬件连接")
            report.append("  2. 确认设备树配置正确")
            report.append("  3. 检查内核串口驱动模块")

        if self.permission_issues:
            report.append("  4. 运行权限修复: sudo usermod -a -G dialout $USER")
            report.append("  5. 添加tty组权限: sudo usermod -a -G tty $USER")
            report.append("  6. 重新登录或重启系统")

        report.append("  7. 联系技术支持获取RDKX5专用配置")
        report.append("  8. 启用模拟数据模式进行测试")
        
        return "\n".join(report)
    
    def save_diagnostic_report(self, filename: str = "serial_diagnostic_report.txt"):
        """保存诊断报告到文件"""
        report = self.generate_diagnostic_report()
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"诊断报告已保存到: {filename}")
            return True
        except Exception as e:
            print(f"保存诊断报告失败: {e}")
            return False



