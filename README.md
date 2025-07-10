# Fish Swarm Vision Guard Intelligent Fishery Water Environment Management System

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Platform](https://img.shields.io/badge/platform-RDKX5-orange.svg)
![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)

**Intelligent Fishery Water Environment Management System Based on Horizon RDKX5 Development Board**

*Protecting Aquatic Ecosystems with Smart Technology* 🐟🌊

</div>

## 📖 Project Overview

The Fish Swarm Vision Guard Intelligent Fishery Water Environment Management System is a comprehensive intelligent fishery solution based on the Horizon RDKX5 development board. The system integrates real-time water quality monitoring, GPS-IMU fusion positioning, AI intelligent detection, autonomous navigation and obstacle avoidance, medication dispensing control, and other functions, achieving a complete closed-loop control from data collection to intelligent decision-making.

### 🌟 Core Features

- **🔄 Complete Closed-Loop Control**: Monitor→Locate→Analyze→Decide→Execute→Feedback
- **📡 MQTT Bidirectional Communication**: Board-side data upload + PC-side command dispatch
- **🤖 AI Intelligent Detection**: Deep learning-based fish disease detection
- **🧭 Precise Positioning Navigation**: GPS-IMU fusion positioning + ultrasonic obstacle avoidance
- **💊 Smart Medication System**: Automated drug dispensing and dosage control
- **📊 Real-time Data Monitoring**: Web interface real-time system status display
- **🔧 Modular Design**: Loosely coupled architecture, easy to extend and maintain

## 🏗️ System Architecture

### Technology Stack
- **Hardware Platform**: Horizon RDKX5 Development Board
- **Programming Language**: Python 3.8+
- **Communication Protocol**: MQTT (Message Queuing Telemetry Transport)
- **Web Framework**: Flask + HTML5 + CSS3 + JavaScript
- **Data Processing**: NumPy + Pandas + SciPy
- **Machine Learning**: TensorFlow + OpenCV
- **Database**: SQLite (extensible)

### System Components
```
┌─────────────────┐    MQTT    ┌─────────────────┐
│   Board System  │ ◄────────► │   PC System     │
│    (RDKX5)     │            │ (Control Center) │
├─────────────────┤            ├─────────────────┤
│ • Sensor Module │            │ • Web Interface │
│ • Position Module│            │ • Data Processing│
│ • Navigation Mod│            │ • AI Assistant  │
│ • AI Detection  │            │ • Command Control│
│ • Motor Control │            │ • Data Storage  │
└─────────────────┘            └─────────────────┘
```

## 📁 Project Structure

```
Fish-Swarm-Vision-Guard-System/
├── board/                      # Board-side programs
│   ├── main.py                 # Board main program entry
│   ├── config.py               # Board configuration management
│   └── modules/                # Functional modules package
├── pc/                         # PC-side programs
│   ├── main.py                 # PC main program entry
│   ├── config.py               # PC configuration management
│   └── web/                    # Web interface
│       ├── index.html          # Main interface
│       └── static/             # Static resources
├── config/                     # Global configuration
│   ├── global_config.py        # Global configuration management
│   ├── mqtt_config.py          # MQTT configuration
│   └── system_logger.py        # Logging configuration
├── docs/                       # Project documentation
│   ├── README.md               # Documentation directory
│   ├── dependencies.md         # Dependency management docs
│   └── api.md                  # API interface documentation
├── tests/                      # Test files
├── scripts/                    # Utility scripts
│   └── verify_dependencies.py  # Dependency verification script
├── legacy/                     # Original modules (reference)
├── logs/                       # Log files
├── requirements.txt            # Unified dependency management
├── board_requirements.txt      # Board-side dependencies
├── pc_requirements.txt         # PC-side dependencies
├── dev-requirements.txt        # Development dependencies
├── LICENSE                     # Open source license
├── .gitignore                  # Git ignore file
├── CONTRIBUTING.md             # Contribution guidelines
├── README.md                   # English documentation
└── README_cn.md               # Chinese documentation
```

## 🚀 Quick Start

### Requirements

**Hardware Requirements:**
- Horizon RDKX5 Development Board
- Water quality sensor set (pH, TDS, turbidity, dissolved oxygen, temperature)
- GPS module + IMU module
- Ultrasonic obstacle avoidance sensor
- Motor drive module
- Camera module

**Software Requirements:**
- Python 3.8+
- MQTT Broker (Mosquitto recommended)
- Operating System: Ubuntu 20.04+ (board-side), Windows 10+ / Linux (PC-side)

### Installation Steps

#### 1. Clone Project
```bash
git clone https://github.com/your-repo/fishery-management-system.git
cd fishery-management-system
```

#### 2. Install MQTT Broker
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients

# Start MQTT service
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

#### 3. Board-side Installation (Horizon RDKX5)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
pip3 install -r board_requirements.txt

# Install Horizon-specific libraries
sudo apt install python3-hobot-gpio python3-hobot-dnn

# Configure user permissions
sudo usermod -a -G gpio,i2c,spi,dialout $USER

# Reboot system
sudo reboot
```

#### 4. PC-side Installation
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install PC-side dependencies
pip install -r pc_requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env file and fill in relevant configurations
```

#### 5. Verify Installation
```bash
# Run dependency verification script
python scripts/verify_dependencies.py
```

### Running the System

#### Start Board-side System
```bash
# Run on RDKX5 development board
cd board/
python main.py
```

#### Start PC-side System
```bash
# Run on PC
cd pc/
python main.py

# Access Web interface
# Open browser and visit: http://localhost:5001
```

## 📡 MQTT Communication Protocol

### Data Transmission Topics (Board→PC)

| Topic | Description | Data Format |
|-------|-------------|-------------|
| `sensor/water_quality` | Water quality sensor data | JSON |
| `navigation/position` | GPS-IMU positioning data | JSON |
| `ai/detection` | AI detection results | JSON |
| `system/status` | System status information | JSON |

### Control Command Topics (PC→Board)

| Topic | Description | Command Format |
|-------|-------------|----------------|
| `control/navigation` | Navigation control commands | JSON |
| `control/medication` | Medication control commands | JSON |
| `control/system` | System control commands | JSON |
| `control/emergency` | Emergency control commands | JSON |

### Data Format Examples

**Water Quality Data:**
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

**Navigation Control Command:**
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

## 🔧 Configuration

### Global Configuration (config/global_config.py)
- System basic configuration
- Module enable/disable settings
- Performance parameter tuning

### MQTT Configuration (config/mqtt_config.py)
- Broker connection parameters
- Topic definition and mapping
- Message format validation

### Logging Configuration (config/system_logger.py)
- Log level settings
- File output configuration
- Module log separation


## 🔧 Troubleshooting

### Common Issues

**1. MQTT Connection Failure**
```bash
# Check MQTT service status
sudo systemctl status mosquitto

# Restart MQTT service
sudo systemctl restart mosquitto

# Check firewall settings
sudo ufw status

# Test MQTT connection
mosquitto_pub -h localhost -t test -m "hello"
mosquitto_sub -h localhost -t test
```

**2. Board-side Module Startup Failure**
```bash
# Check hardware connections
ls /dev/ttyUSB*  # Check serial devices
i2cdetect -y 1   # Check I2C devices

# Check permission settings
groups $USER     # Confirm user is in relevant groups

# View detailed error logs
tail -f logs/board.log

# Check GPIO permissions
gpio readall     # Display GPIO status
```

**3. PC-side Web Interface Inaccessible**
```bash
# Check port usage
netstat -tulpn | grep :5001

# Check firewall settings
sudo ufw allow 5001

# Restart PC-side service
python pc/main.py

# Check Flask application status
curl http://localhost:5001/api/health
```

**4. Dependency Installation Issues**
```bash
# Run dependency verification
python scripts/verify_dependencies.py

# Clear pip cache
pip cache purge

# Use domestic mirror source
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# Check Python version
python --version  # Requires 3.8+
```

**5. Sensor Data Anomalies**
```bash
# Check sensor connections
sudo i2cdetect -y 1

# Check serial devices
ls -la /dev/ttyUSB*

# Test sensor reading
cd legacy/传感器
python main.py --test
```

**6. AI Detection Module Issues**
```bash
# Check camera devices
ls /dev/video*

# Test camera
v4l2-ctl --list-devices

# Check DNN library
python -c "import hobot_dnn; print('DNN library OK')"
```

### Log Analysis

System logs are located in the `logs/` directory:
- `board.log` - Board-side system logs
- `pc.log` - PC-side system logs
- `mqtt.log` - MQTT communication logs
- `sensor.log` - Sensor data logs

```bash
# Real-time log viewing
tail -f logs/board.log

# Search for error information
grep -i error logs/*.log

# View recent warnings
grep -i warning logs/*.log | tail -20
```

## 🚀 Deployment Guide

### Production Environment Deployment

#### Board-side Deployment (RDKX5)
```bash
# 1. System optimization
sudo systemctl disable unnecessary-services
sudo cpufreq-set -g performance

# 2. Auto-start configuration
sudo cp scripts/fishery-board.service /etc/systemd/system/
sudo systemctl enable fishery-board
sudo systemctl start fishery-board

# 3. Monitoring configuration
sudo cp scripts/watchdog.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/watchdog.sh
```

#### PC-side Deployment
```bash
# Using Gunicorn (Linux)
gunicorn --bind 0.0.0.0:5001 --workers 4 pc.main:app

# Using Waitress (Windows)
waitress-serve --host=0.0.0.0 --port=5001 pc.main:app

# Using Docker
docker build -t fishery-pc .
docker run -p 5001:5001 fishery-pc
```

### System Monitoring

#### Performance Monitoring
```bash
# System resource monitoring
htop
iotop
nethogs

# Application performance monitoring
python scripts/performance_monitor.py

# Log monitoring
tail -f logs/*.log | grep -E "(ERROR|WARNING)"
```

#### Health Checks
```bash
# System health check
curl http://localhost:5001/api/health

# MQTT connection check
mosquitto_pub -h localhost -t health/check -m "ping"

# Sensor status check
python scripts/sensor_health_check.py
```
