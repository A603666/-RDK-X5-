# 鱼群'视'卫智能渔业水环境管理系统

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Platform](https://img.shields.io/badge/platform-RDKX5-orange.svg)
![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)

**基于地平线RDKX5开发板的智能渔业水环境管理系统**

*让智能科技守护水域生态* 🐟🌊

</div>

## 📖 项目简介

鱼群'视'卫智能渔业水环境管理系统是一个基于地平线RDKX5开发板的完整智能渔业解决方案。系统集成了实时水质监测、GPS-IMU融合定位、AI智能检测、自主导航避障、药物投放控制等功能，实现了从数据采集到智能决策的完整闭环控制。

### 🌟 核心特性

- **🔄 完整闭环控制**: 监测→定位→分析→决策→执行→反馈
- **📡 MQTT双向通讯**: 板端数据上传 + PC端指令下发
- **🤖 AI智能检测**: 基于深度学习的鱼类疾病检测
- **🧭 精准定位导航**: GPS-IMU融合定位 + 超声波避障
- **💊 智能投药系统**: 自动化药物投放和剂量控制
- **📊 实时数据监控**: Web界面实时显示系统状态
- **🔧 模块化设计**: 松耦合架构，易于扩展和维护

## 🏗️ 系统架构

### 技术栈
- **硬件平台**: 地平线RDKX5开发板
- **开发语言**: Python 3.8+
- **通讯协议**: MQTT (Message Queuing Telemetry Transport)
- **Web框架**: Flask + HTML5 + CSS3 + JavaScript
- **数据处理**: NumPy + Pandas + SciPy
- **机器学习**: TensorFlow + OpenCV
- **数据库**: SQLite (可扩展)

### 系统组成
```
┌─────────────────┐    MQTT    ┌─────────────────┐
│   板端系统       │ ◄────────► │   PC端系统       │
│  (RDKX5)       │            │  (监控中心)      │
├─────────────────┤            ├─────────────────┤
│ • 传感器模块     │            │ • Web界面       │
│ • 定位模块       │            │ • 数据处理      │
│ • 导航模块       │            │ • AI助手        │
│ • AI检测模块     │            │ • 指令控制      │
│ • 电机控制模块   │            │ • 数据存储      │
└─────────────────┘            └─────────────────┘
```

## 📁 项目结构

```
鱼群视卫智能渔业水环境管理系统/
├── board/                      # 板端程序
│   ├── main.py                 # 板端主程序入口
│   ├── config.py               # 板端配置管理
│   └── modules/                # 功能模块包
├── pc/                         # PC端程序
│   ├── main.py                 # PC端主程序入口
│   ├── config.py               # PC端配置管理
│   └── web/                    # Web界面
│       ├── index.html          # 主界面
│       └── static/             # 静态资源
├── config/                     # 全局配置
│   ├── global_config.py        # 全局配置管理
│   ├── mqtt_config.py          # MQTT配置
│   └── system_logger.py        # 日志配置
├── docs/                       # 项目文档
│   ├── README.md               # 文档目录
│   ├── dependencies.md         # 依赖管理文档
│   └── api.md                  # API接口文档
├── tests/                      # 测试文件
├── scripts/                    # 实用脚本
│   └── verify_dependencies.py  # 依赖验证脚本
├── legacy/                     # 原始模块（参考）
├── logs/                       # 日志文件
├── requirements.txt            # 统一依赖管理
├── board_requirements.txt      # 板端依赖
├── pc_requirements.txt         # PC端依赖
├── dev-requirements.txt        # 开发依赖
├── LICENSE                     # 开源许可证
├── .gitignore                  # Git忽略文件
├── CONTRIBUTING.md             # 贡献指南
└── README_cn.md               # 中文说明文档
```

## 🚀 快速开始

### 环境要求

**硬件要求:**
- 地平线RDKX5开发板
- 水质传感器组 (pH, TDS, 浊度, 溶氧, 温度)
- GPS模块 + IMU模块
- 超声波避障传感器
- 电机驱动模块
- 摄像头模块

**软件要求:**
- Python 3.8+
- MQTT Broker (推荐 Mosquitto)
- 操作系统: Ubuntu 20.04+ (板端), Windows 10+ / Linux (PC端)

### 安装步骤

#### 1. 克隆项目
```bash
git clone https://github.com/your-repo/fishery-management-system.git
cd fishery-management-system
```

#### 2. 安装MQTT Broker
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients

# 启动MQTT服务
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

#### 3. 板端安装 (地平线RDKX5)
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python依赖
pip3 install -r board_requirements.txt

# 安装地平线特定库
sudo apt install python3-hobot-gpio python3-hobot-dnn

# 配置用户权限
sudo usermod -a -G gpio,i2c,spi,dialout $USER

# 重启系统
sudo reboot
```

#### 4. PC端安装
```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装PC端依赖
pip install -r pc_requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，填入相关配置
```

#### 5. 验证安装
```bash
# 运行依赖验证脚本
python scripts/verify_dependencies.py
```

### 运行系统

#### 启动板端系统
```bash
# 在RDKX5开发板上运行
cd board/
python main.py
```

#### 启动PC端系统
```bash
# 在PC上运行
cd pc/
python main.py

# 访问Web界面
# 打开浏览器访问: http://localhost:5001
```

## 📡 MQTT通讯协议

### 数据传输主题 (板端→PC端)

| 主题 | 描述 | 数据格式 |
|------|------|----------|
| `sensor/water_quality` | 水质传感器数据 | JSON |
| `navigation/position` | GPS-IMU定位数据 | JSON |
| `ai/detection` | AI检测结果 | JSON |
| `system/status` | 系统状态信息 | JSON |

### 控制指令主题 (PC端→板端)

| 主题 | 描述 | 指令格式 |
|------|------|----------|
| `control/navigation` | 导航控制指令 | JSON |
| `control/medication` | 投药控制指令 | JSON |
| `control/system` | 系统控制指令 | JSON |
| `control/emergency` | 紧急控制指令 | JSON |

### 数据格式示例

**水质数据:**
```json
{
  "timestamp": 1704067200,
  "sensors": {
    "temperature": {"value": 25.5, "unit": "°C"},
    "ph": {"value": 7.2, "unit": "pH"},
    "dissolved_oxygen": {"value": 8.5, "unit": "mg/L"},
    "tds": {"value": 150, "unit": "ppm"},
    "turbidity": {"value": 5.2, "unit": "NTU"}
  }
}
```

**导航控制指令:**
```json
{
  "command": "START_NAVIGATION",
  "parameters": {
    "target_coordinates": [30.123456, 120.654321],
    "speed": 1.5,
    "mode": "AUTO"
  },
  "timestamp": 1704067200
}
```

## 🔧 配置说明

### 全局配置 (config/global_config.py)
- 系统基础配置
- 模块启用/禁用设置
- 性能参数调优

### MQTT配置 (config/mqtt_config.py)
- Broker连接参数
- 主题定义和映射
- 消息格式验证

### 日志配置 (config/system_logger.py)
- 日志级别设置
- 文件输出配置
- 模块日志分离

## 🧪 测试验证

### 功能测试
```bash
# 运行单元测试
pytest tests/

# 运行集成测试
pytest tests/test_integration/

# 运行性能测试
pytest tests/test_performance/
```

### 系统测试
- ✅ 四类数据源MQTT传输测试
- ✅ 三类控制指令处理测试
- ✅ 指令优先级和冲突处理测试
- ✅ 闭环控制机制测试
- ✅ 性能和稳定性测试

### 性能指标
- **数据传输延迟**: < 100ms
- **指令响应时间**: < 1s
- **系统稳定性**: 24小时连续运行
- **MQTT连接稳定性**: > 99.9%

## 🔬 功能模块详解

### 传感器模块
**位置**: `board/modules/sensors/`
**功能**: 实时采集水质参数
- **pH传感器**: 测量水体酸碱度 (6.0-9.0 pH)
- **TDS传感器**: 测量总溶解固体 (0-2000 ppm)
- **浊度传感器**: 测量水体透明度 (0-100 NTU)
- **溶氧传感器**: 测量溶解氧含量 (0-20 mg/L)
- **温度传感器**: 测量水温 (0-50°C)

### 定位模块
**位置**: `board/modules/positioning/`
**功能**: GPS-IMU融合定位
- **GPS定位**: 提供绝对位置信息
- **IMU姿态**: 提供加速度和角速度
- **卡尔曼滤波**: 融合多传感器数据
- **坐标转换**: 支持多种坐标系统

### 导航避障模块
**位置**: `board/modules/navigation/`
**功能**: 自主导航和避障
- **路径规划**: A*算法路径规划
- **PID控制**: 精确运动控制
- **超声波避障**: 实时障碍物检测
- **紧急制动**: 安全保护机制

### AI检测模块
**位置**: `board/modules/ai_detection/`
**功能**: 智能图像识别
- **鱼类检测**: 识别鱼类种类和数量
- **疾病诊断**: 检测鱼类健康状况
- **行为分析**: 分析鱼群行为模式
- **预警系统**: 异常情况自动报警

### 电机控制模块
**位置**: `board/modules/motor_control/`
**功能**: 运动和投药控制
- **推进器控制**: 前进、后退、转向
- **投药器控制**: 精确药物投放
- **速度调节**: 多档位速度控制
- **故障保护**: 过载和短路保护

## 📚 API文档

### REST API接口

#### 数据获取接口
- `GET /api/data/latest` - 获取最新数据
- `GET /api/data/history?hours=24` - 获取历史数据
- `GET /api/system/status` - 获取系统状态
- `GET /api/sensors/calibration` - 获取传感器校准状态

#### 控制指令接口
- `POST /api/command/navigation` - 发送导航指令
- `POST /api/command/medication` - 发送投药指令
- `POST /api/command/emergency` - 发送紧急指令
- `POST /api/command/calibration` - 传感器校准指令

#### AI助手接口
- `POST /api/chat` - AI对话接口
- `GET /api/prediction` - 获取预测结果
- `POST /api/analysis` - 数据分析请求

#### 系统管理接口
- `GET /api/health` - 健康检查
- `POST /api/config` - 配置更新
- `GET /api/logs` - 获取系统日志

详细API文档请参考: [docs/api.md](docs/api.md)

## 🔧 故障排除

### 常见问题

**1. MQTT连接失败**
```bash
# 检查MQTT服务状态
sudo systemctl status mosquitto

# 重启MQTT服务
sudo systemctl restart mosquitto

# 检查防火墙设置
sudo ufw status

# 测试MQTT连接
mosquitto_pub -h localhost -t test -m "hello"
mosquitto_sub -h localhost -t test
```

**2. 板端模块启动失败**
```bash
# 检查硬件连接
ls /dev/ttyUSB*  # 检查串口设备
i2cdetect -y 1   # 检查I2C设备

# 检查权限设置
groups $USER     # 确认用户在相关组中

# 查看详细错误日志
tail -f logs/board.log

# 检查GPIO权限
gpio readall     # 显示GPIO状态
```

**3. PC端Web界面无法访问**
```bash
# 检查端口占用
netstat -tulpn | grep :5001

# 检查防火墙设置
sudo ufw allow 5001

# 重启PC端服务
python pc/main.py

# 检查Flask应用状态
curl http://localhost:5001/api/health
```

**4. 依赖安装问题**
```bash
# 运行依赖验证
python scripts/verify_dependencies.py

# 清理pip缓存
pip cache purge

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 检查Python版本
python --version  # 需要3.8+
```

**5. 传感器数据异常**
```bash
# 检查传感器连接
sudo i2cdetect -y 1

# 检查串口设备
ls -la /dev/ttyUSB*

# 测试传感器读取
cd legacy/传感器
python main.py --test
```

**6. AI检测模块问题**
```bash
# 检查摄像头设备
ls /dev/video*

# 测试摄像头
v4l2-ctl --list-devices

# 检查DNN库
python -c "import hobot_dnn; print('DNN库正常')"
```

### 日志分析

系统日志位于 `logs/` 目录下：
- `board.log` - 板端系统日志
- `pc.log` - PC端系统日志
- `mqtt.log` - MQTT通讯日志
- `sensor.log` - 传感器数据日志

```bash
# 实时查看日志
tail -f logs/board.log

# 搜索错误信息
grep -i error logs/*.log

# 查看最近的警告
grep -i warning logs/*.log | tail -20
```

## 🚀 部署指南

### 生产环境部署

#### 板端部署 (RDKX5)
```bash
# 1. 系统优化
sudo systemctl disable unnecessary-services
sudo cpufreq-set -g performance

# 2. 自动启动配置
sudo cp scripts/fishery-board.service /etc/systemd/system/
sudo systemctl enable fishery-board
sudo systemctl start fishery-board

# 3. 监控配置
sudo cp scripts/watchdog.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/watchdog.sh
```

#### PC端部署
```bash
# 使用Gunicorn (Linux)
gunicorn --bind 0.0.0.0:5001 --workers 4 pc.main:app

# 使用Waitress (Windows)
waitress-serve --host=0.0.0.0 --port=5001 pc.main:app

# 使用Docker
docker build -t fishery-pc .
docker run -p 5001:5001 fishery-pc
```

### 系统监控

#### 性能监控
```bash
# 系统资源监控
htop
iotop
nethogs

# 应用性能监控
python scripts/performance_monitor.py

# 日志监控
tail -f logs/*.log | grep -E "(ERROR|WARNING)"
```

#### 健康检查
```bash
# 系统健康检查
curl http://localhost:5001/api/health

# MQTT连接检查
mosquitto_pub -h localhost -t health/check -m "ping"

# 传感器状态检查
python scripts/sensor_health_check.py
```

## 🔧 运维管理

### 数据备份
```bash
# 配置文件备份
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/

# 日志文件备份
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/

# 数据库备份（如果使用）
sqlite3 data/fishery.db ".backup backup_$(date +%Y%m%d).db"
```

### 系统更新
```bash
# 代码更新
git pull origin main

# 依赖更新
pip install -r requirements.txt --upgrade

# 重启服务
sudo systemctl restart fishery-board
sudo systemctl restart fishery-pc
```

### 故障恢复
```bash
# 重置配置
cp config/default_config.py config/global_config.py

# 清理日志
find logs/ -name "*.log" -mtime +7 -delete

# 重启所有服务
sudo systemctl restart mosquitto
sudo systemctl restart fishery-board
sudo systemctl restart fishery-pc
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！请参考 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细的贡献流程。

### 开发环境设置
```bash
# 安装开发依赖
pip install -r dev-requirements.txt

# 设置pre-commit钩子
pre-commit install

# 运行代码检查
flake8 .
black --check .
mypy board/ pc/ config/
```

### 提交规范
- 使用清晰的提交信息
- 遵循代码风格规范
- 添加必要的测试
- 更新相关文档

### 代码审查
- 所有PR需要至少一人审查
- 确保测试通过
- 检查文档更新
- 验证向后兼容性

## 📋 更新日志

### v1.0.0 (2025-01-10)
**🎉 首次发布**
- ✅ 完整的板端和PC端主程序
- ✅ 统一的MQTT双向通讯架构
- ✅ 模块化设计和配置管理
- ✅ Web界面和API接口
- ✅ 完整的文档和测试

**新功能:**
- 🔄 完整闭环控制系统
- 📡 MQTT双向通讯协议
- 🤖 AI智能检测模块
- 🧭 GPS-IMU融合定位
- 💊 智能投药控制系统
- 📊 实时数据监控界面

**技术改进:**
- 🏗️ 重构项目文件结构
- 📦 统一依赖管理系统
- 🔧 全局配置管理
- 📝 完整的中英文文档
- 🧪 自动化测试框架

### 路线图

#### v1.1.0 (计划中)
- 🔮 增强AI预测模型
- 📱 移动端应用支持
- 🌐 多语言界面支持
- 📈 高级数据分析功能

#### v1.2.0 (计划中)
- ☁️ 云端数据同步
- 🔔 智能报警系统
- 📊 数据可视化增强
- 🔐 用户权限管理

#### v2.0.0 (长期规划)
- 🤖 深度学习模型优化
- 🌊 多船协同作业
- 🛰️ 卫星通讯支持
- 🏭 工业级部署方案

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

### 开源声明
本项目基于以下开源技术构建：
- Flask (BSD License)
- TensorFlow (Apache 2.0 License)
- OpenCV (Apache 2.0 License)
- MQTT (Eclipse Public License)
- NumPy (BSD License)

## 📞 技术支持

- **项目主页**: https://github.com/your-repo/fishery-management-system
- **问题反馈**: https://github.com/your-repo/fishery-management-system/issues
- **文档中心**: [docs/](docs/)
- **开发者社区**: [Discussions](https://github.com/your-repo/fishery-management-system/discussions)

## 🙏 致谢

感谢以下开源项目和技术支持：
- [地平线RDKX5开发板](https://developer.horizon.ai/)
- [Flask Web框架](https://flask.palletsprojects.com/)
- [MQTT协议](https://mqtt.org/)
- [TensorFlow深度学习框架](https://tensorflow.org/)
- [OpenCV计算机视觉库](https://opencv.org/)

---

<div align="center">

**鱼群'视'卫智能渔业水环境管理系统** - 让智能科技守护水域生态 🐟🌊

Made with ❤️ by 开发团队

</div>
