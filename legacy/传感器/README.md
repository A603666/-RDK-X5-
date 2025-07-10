# 水质传感器监测系统

## 项目简介

水质传感器监测系统是专为地平线RDKX5开发板设计的多传感器集成解决方案。系统集成PH、TDS、浊度、溶解氧温度四种传感器，通过多线程架构实现实时数据采集、处理和标准化输出，适用于水产养殖、环境监测等应用场景。
### 核心功能
- **多传感器集成**: 同时监测PH、TDS、浊度、溶解氧、温度五项水质参数
- **实时数据采集**: 1秒采样间隔，支持并发数据读取
- **智能校准算法**: PH分段线性校准、TDS温度补偿、浊度温度校准
- **标准化输出**: JSON格式数据输出，兼容web_frontend系统
- **数据存储**: CSV文件自动记录，支持历史数据查询
- **API接口**: 提供标准接口供其他模块集成使用
- **异常处理**: 完善的错误处理和数据验证机制

### 技术特点
- **多协议通信**: 支持UART串口、I2C总线、RS485/Modbus-RTU协议
- **多线程架构**: 传感器数据采集、处理、存储独立运行
- **线程安全设计**: 使用锁机制确保多线程数据访问安全
- **模块化设计**: 传感器驱动、配置管理、主程序独立封装
- **架构复用**: 严格遵循现有项目的设计模式和编码规范

## 硬件配置要求

### 开发板
- **地平线RDKX5开发板** (ARM64架构Ubuntu系统)
- **串口接口**: UART2、UART6、UART7
- **I2C接口**: I2C0总线
- **GPIO接口**: GPIO26(复位控制)

### 传感器模块

#### PH传感器
- **连接方式**: UART2串口 + ADC模拟量读取
- **引脚连接**: 
  - 引脚15: UART2_TXD (发送数据)
  - 引脚22: UART2_RXD (接收数据)
- **测量范围**: 0-14 pH
- **精度**: ±0.1 pH
- **校准方式**: 三点校准(4.0/6.86/9.18标准液)

#### TDS传感器
- **连接方式**: UART7串口 + ADC模拟量读取
- **引脚连接**:
  - 引脚11: UART7_TXD (发送数据)
  - 引脚13: UART7_RXD (接收数据)
- **测量范围**: 0-2000 ppm
- **精度**: ±3%
- **特性**: 自动温度补偿

#### 浊度传感器
- **连接方式**: I2C总线 + ADC芯片
- **引脚连接**:
  - 引脚27: I2C_SDA (数据线)
  - 引脚28: I2C_SCL (时钟线)
- **设备文件**: /dev/i2c-2 (对应I2C2总线)
- **测量范围**: 0-3000 NTU
- **精度**: ±5%
- **特性**: 温度补偿算法

#### 溶解氧温度传感器
- **连接方式**: UART6串口 + RS485转TTL模块
- **引脚连接**:
  - 引脚16: UART6_TXD (发送数据)
  - 引脚36: UART6_RXD (接收数据)
  - 引脚37: GPIO26 (复位控制)
- **通信协议**: Modbus-RTU
- **测量范围**: 溶解氧0-20mg/L，温度0-50℃
- **精度**: 溶解氧±3%，温度±0.5℃

### 硬件连接示意图
```
RDKX5开发板
├── UART2 (引脚15,22) ──→ PH传感器
├── UART7 (引脚11,13) ──→ TDS传感器
├── I2C2 (引脚27,28)  ──→ 0x1c ADC芯片 ──→ 浊度传感器
├── UART6 (引脚16,36) ──→ RS485转TTL ──→ 溶解氧温度传感器
└── GPIO26 (引脚37)   ──→ 溶解氧传感器复位控制
```

## 安装部署步骤

### 1. 环境准备

确保RDKX5开发板已安装Ubuntu系统并配置好网络连接：

```bash
# 检查系统版本
cat /etc/os-release

# 更新软件包
sudo apt update && sudo apt upgrade -y

# 安装Python依赖
sudo apt install python3 python3-pip python3-dev -y
```

### 2. 安装Python依赖库

```bash
# 安装串口通信库
pip3 install pyserial

# 安装I2C通信库
pip3 install smbus2

# 安装Hobot.GPIO库(RDKX5专用)
# 注意：此库通常预装在RDKX5系统中
```

### 3. 硬件连接

按照上述硬件配置要求连接各传感器到RDKX5开发板对应引脚。

### 4. 配置串口权限

```bash
# 添加用户到dialout组
sudo usermod -a -G dialout $USER

# 重新登录或重启系统使权限生效
sudo reboot
```

### 5. 下载和配置系统

```bash
# 进入传感器目录
cd 传感器/

# 检查配置文件
cat config.py

# 根据实际硬件配置修改参数(如需要)
nano config.py
```

### 6. 测试浊度传感器I2C连接

```bash
# 简化测试程序 (推荐)
python3 test_i2c_simple.py

# 完整测试程序
python3 test_turbidity_i2c.py

# 预期输出:
# ✅ I2C连接成功
# ADC原始值: 1024 (12位: 0-4095)
# 电压值: 0.8250V
# 浊度值: 2633.45 NTU
```

## 使用说明

### 基本使用

#### 1. 传感器调试诊断 (推荐首次运行)
```bash
# 进入传感器目录
cd 传感器/

# 运行传感器调试诊断工具
python3 sensor_debug.py
```

**调试工具功能**:
- 检查串口设备是否存在和可访问
- 验证I2C设备状态和地址
- 测试传感器通信协议
- 提供具体的故障排除建议

#### 2. 启动系统
```bash
# 启动水质监测系统
python3 main.py
```

#### 2. 系统输出示例
```
启动水质传感器监测系统...
PH传感器已连接 /dev/ttyS2 波特率 9600
TDS传感器已连接 /dev/ttyS7 波特率 9600
浊度传感器已连接 I2C2(/dev/i2c-2) 地址 0x1c
溶解氧温度传感器已连接 /dev/ttyS6 波特率 9600
水质传感器监测系统启动成功

=== 水质监测数据 2025-06-28 19:45:30 ===
PH值: 7.25 pH (有效)
TDS值: 350 ppm (有效)
浊度: 12.5 NTU (有效)
溶解氧: 8.45 mg/L (有效)
温度: 25.3 ℃ (有效)
```

#### 3. 停止系统
```bash
# 按Ctrl+C优雅停止系统
^C
接收到停止信号，正在关闭系统...
水质传感器监测系统已停止
```

### 高级使用

#### 1. 作为模块导入使用
```python
# 导入水质监测系统
from main import get_water_quality_system

# 获取系统实例
wq_system = get_water_quality_system()

# 启动系统
if wq_system.start():
    # 获取最新数据
    data = wq_system.get_latest_data()
    print(f"PH值: {data['ph']['value']}")
    
    # 获取JSON格式数据
    json_data = wq_system.get_json_data()
    
    # 获取传感器状态
    status = wq_system.get_sensor_status()
    
    # 停止系统
    wq_system.stop()
```

#### 2. 配置参数调整
```python
# 修改config.py中的参数
SYSTEM_CONFIG = {
    'sampling_interval': 0.5,  # 采样间隔改为0.5秒
    'print_interval': 2.0,     # 打印间隔改为2秒
    'log_interval': 30.0       # 记录间隔改为30秒
}
```

## API接口规范

### 数据格式

#### 标准数据格式
```json
{
  "timestamp": 1640995200.123,
  "system": "WaterQuality",
  "ph": {
    "value": 7.25,
    "unit": "pH",
    "valid": true
  },
  "tds": {
    "value": 350.0,
    "unit": "ppm", 
    "valid": true
  },
  "turbidity": {
    "value": 12.5,
    "unit": "NTU",
    "valid": true
  },
  "dissolved_oxygen": {
    "value": 8.45,
    "unit": "mg/L",
    "valid": true
  },
  "temperature": {
    "value": 25.3,
    "unit": "℃",
    "valid": true
  },
  "status": "running"
}
```

#### Web前端兼容格式
```json
{
  "timestamp": 1640995200.123,
  "system": "WaterQuality",
  "sensors": {
    "ph": {
      "name": "PH传感器",
      "value": 7.25,
      "unit": "pH",
      "status": "normal"
    }
  },
  "status": "running"
}
```

### API接口

#### get_latest_data()
- **功能**: 获取最新传感器数据
- **返回**: dict - 标准数据格式
- **线程安全**: 是

#### get_json_data()
- **功能**: 获取Web前端兼容的JSON数据
- **返回**: dict - Web前端格式
- **用途**: 供web_frontend系统使用

#### get_sensor_status()
- **功能**: 获取传感器连接状态
- **返回**: dict - 连接状态信息
- **示例**: 
```json
{
  "ph_sensor": true,
  "tds_sensor": true,
  "turbidity_sensor": true,
  "do_temp_sensor": true,
  "system_running": true
}
```

## 故障排除

### 常见问题

#### 0. 传感器读取数据为0或无效 (当前主要问题)
**现象**: 系统启动成功，但PH、TDS、溶解氧传感器都显示0值且状态为error，只有浊度传感器正常
**原因**: 传感器通信协议不匹配或硬件连接问题
**解决方案**:
```bash
# 1. 运行调试诊断工具
python3 sensor_debug.py

# 2. 检查传感器硬件连接
# - 确认传感器供电正常(通常5V或3.3V)
# - 检查串口线连接是否正确(TX-RX交叉连接)
# - 验证传感器是否支持当前通信协议

# 3. 检查传感器通信协议
# PH传感器: 可能需要特定的查询命令而非"READ_ADC"
# TDS传感器: 可能需要特定的查询命令而非"READ_TDS_ADC"
# 溶解氧传感器: 检查Modbus地址和寄存器地址是否正确

# 4. 使用示波器或逻辑分析仪检查信号
# - 验证串口波特率设置
# - 检查数据格式(8N1等)
# - 确认传感器响应时间
```

#### 1. 传感器连接失败
**现象**: 启动时显示"传感器连接失败"
**原因**: 串口设备不存在或权限不足
**解决方案**:
```bash
# 检查串口设备
ls /dev/ttyS*

# 检查用户权限
groups $USER

# 添加串口权限
sudo usermod -a -G dialout $USER
sudo reboot
```

#### 2. I2C设备无响应 (Remote I/O error)
**现象**: 浊度传感器初始化失败，错误 `[Errno 121] Remote I/O error`
**原因**: I2C设备地址错误、硬件连接问题或总线配置错误

**快速诊断**:
```bash
# 运行简化测试程序
python3 test_i2c_simple.py

# 手动检查I2C设备
ls /dev/i2c*

# 扫描I2C2总线 (RDKX5浊度传感器连接)
sudo i2cdetect -y 2

# 预期结果: 在地址0x1c处看到设备
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 10: -- -- -- -- -- -- -- -- -- -- -- -- 1c -- -- --
```

**详细故障排除**:
```bash
# 1. 检查硬件连接
# 确认ADS1110A0连接到RDKX5 I2C0:
# - SDA → 引脚27
# - SCL → 引脚28
# - VCC → 3.3V
# - GND → GND

# 2. 检查I2C权限
sudo usermod -a -G i2c $USER
sudo reboot

# 3. 测试I2C通信
sudo i2cget -y 0 0x48

# 4. 检查设备文件权限
ls -l /dev/i2c-0
```

**常见问题解决**:
- **设备文件不存在**: 检查I2C接口是否启用
- **权限拒绝**: 添加用户到i2c组并重启
- **地址冲突**: 确认ADS1110A0地址为0x48
- **硬件故障**: 检查线缆连接和芯片供电

#### 3. 数据读取异常
**现象**: 传感器数据显示"无效"
**原因**: 传感器校准问题或硬件故障
**解决方案**:
- 检查传感器校准参数
- 重新校准传感器
- 检查硬件连接

#### 4. GPIO权限错误
**现象**: GPIO初始化失败
**原因**: Hobot.GPIO库未安装或权限不足
**解决方案**:
```bash
# 检查GPIO库
python3 -c "import Hobot.GPIO"

# 以root权限运行(如需要)
sudo python3 main.py
```

### 调试模式

启用详细日志输出：
```python
# 在main.py中添加日志配置
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 系统维护

### 传感器校准

#### PH传感器校准
1. 准备4.0、6.86、9.18标准缓冲液
2. 依次将传感器放入标准液中
3. 记录对应的电压值
4. 更新config.py中的校准参数

#### TDS传感器校准
1. 使用已知TDS值的标准液
2. 测量温度补偿系数
3. 调整转换公式参数

### 定期维护

#### 每日检查
- 检查传感器连接状态
- 查看数据记录文件
- 确认系统运行正常

#### 每周维护
- 清洁传感器探头
- 检查校准精度
- 备份数据文件

#### 每月维护
- 重新校准传感器
- 更新系统软件
- 检查硬件连接

## 性能优化

### 系统优化建议

1. **采样频率调整**: 根据应用需求调整采样间隔
2. **数据缓存**: 实现数据缓存减少I/O操作
3. **异步处理**: 使用异步I/O提高响应速度
4. **内存管理**: 定期清理历史数据避免内存泄漏

### 扩展功能

1. **远程监控**: 集成MQTT或HTTP API
2. **报警系统**: 添加阈值报警功能
3. **数据分析**: 集成数据分析和趋势预测
4. **移动端**: 开发移动端监控应用

## 技术支持

### 联系方式
- 项目仓库: [GitHub链接]
- 技术文档: [文档链接]
- 问题反馈: [Issue链接]

### 版本信息
- 当前版本: v1.0.0
- 更新日期: 2025-06-28
- 兼容性: RDKX5开发板 + Ubuntu系统

---

*本文档提供了水质传感器监测系统的完整使用指南*
*如有问题请参考故障排除章节或联系技术支持*
