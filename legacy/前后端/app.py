from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import requests
import json
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import schedule
from scipy.interpolate import interp1d
from dotenv import load_dotenv
import logging
import warnings
warnings.filterwarnings('ignore')

# 导入MQTT客户端
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
    print("✓ MQTT库加载成功")
except ImportError as e:
    MQTT_AVAILABLE = False
    print(f"⚠️ MQTT库未安装: {e}")
    print("MQTT数据接收功能将不可用")

# 尝试导入机器学习库
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from sklearn.preprocessing import MinMaxScaler
    ML_AVAILABLE = True
    print("✓ 机器学习库加载成功")
except ImportError as e:
    ML_AVAILABLE = False
    print(f"⚠️ 机器学习库未安装: {e}")
    print("使用统计预测模型替代")

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)  # 启用CORS以允许从网页调用API

# Coze API凭证 - 优化安全性
COZE_AUTH_TOKEN = os.getenv('COZE_AUTH_TOKEN')
COZE_BOT_ID = os.getenv('COZE_BOT_ID')
COZE_USER_ID = os.getenv('COZE_USER_ID', 'default_user')

# 验证必要的环境变量
if not COZE_AUTH_TOKEN or not COZE_BOT_ID:
    logger.warning("⚠️ Coze API凭证未配置，AI助手功能将不可用")

# 高德地图API配置
AMAP_API_KEY = os.getenv('AMAP_API_KEY', '88c9218baacddcea12c7004d66c17b4c')  # 临时默认值，生产环境需配置
if AMAP_API_KEY == '88c9218baacddcea12c7004d66c17b4c':
    logger.warning("⚠️ 使用默认高德地图API密钥，生产环境请配置AMAP_API_KEY环境变量")

# API端点
COZE_API_BASE = 'https://api.coze.cn/v3'

# 存储会话ID的字典
conversations = {}

# 全局变量
water_quality_data = []  # 存储水质数据
prediction_results = {}  # 存储预测结果
cruise_status = {'active': False, 'current_position': None}  # 巡航状态
scalers = {}  # 数据标准化器

# MQTT数据存储变量
position_data = {}  # 存储定位数据
ai_detection_data = {}  # 存储AI检测数据
system_status_data = {}  # 存储系统状态数据
mqtt_client = None  # MQTT客户端
mqtt_enabled = MQTT_AVAILABLE  # MQTT功能是否可用

def on_mqtt_message(client, userdata, message):
    """处理MQTT消息 - 接收板端四类数据源"""
    global water_quality_data, position_data, ai_detection_data, system_status_data

    try:
        topic = message.topic
        data = json.loads(message.payload.decode())

        logger.info(f"收到MQTT数据 - 主题: {topic}")

        if topic == 'sensor/water_quality':
            # 处理传感器数据 - 复用现有water_quality_data格式
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

            water_quality_data.append(sensor_data)

            # 只保留最近24小时的数据
            cutoff_time = datetime.now() - timedelta(hours=24)
            water_quality_data[:] = [d for d in water_quality_data
                                   if datetime.fromisoformat(d['timestamp']) > cutoff_time]

            logger.info("传感器数据已更新")

        elif topic == 'navigation/position':
            # 处理定位数据 - 重点关注
            position_data.update({
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

            logger.info(f"定位数据已更新 - 位置: ({position_data['latitude']:.6f}, {position_data['longitude']:.6f})")

        elif topic == 'ai/detection':
            # 处理AI检测数据
            ai_detection_data.update({
                'timestamp': data.get('timestamp', time.time()),
                'detection': data.get('detection', {}),
                'data_type': data.get('data_type', 'ai_detection')
            })

            logger.info("AI检测数据已更新")

        elif topic == 'system/status':
            # 处理系统状态数据
            system_status_data.update({
                'timestamp': data.get('timestamp', time.time()),
                'navigation_state': data.get('navigation_state', 'unknown'),
                'running': data.get('running', False),
                'modules': data.get('modules', {}),
                'hardware': data.get('hardware', {}),
                'data_type': data.get('data_type', 'system_status')
            })

            logger.info("系统状态数据已更新")

    except Exception as e:
        logger.error(f"MQTT消息处理错误: {e}")

def init_mqtt_client():
    """初始化MQTT客户端"""
    global mqtt_client, mqtt_enabled

    if not mqtt_enabled:
        logger.info("MQTT功能不可用，跳过MQTT客户端初始化")
        return

    try:
        mqtt_client = mqtt.Client()
        mqtt_client.on_message = on_mqtt_message
        mqtt_client.connect('localhost', 1883, 60)

        # 订阅四个数据主题
        data_topics = [
            'sensor/water_quality',
            'navigation/position',
            'ai/detection',
            'system/status'
        ]

        for topic in data_topics:
            mqtt_client.subscribe(topic)
            logger.info(f"已订阅MQTT数据主题: {topic}")

        mqtt_client.loop_start()  # 启动后台线程处理网络流量
        logger.info("PC端MQTT数据接收客户端启动成功")

    except Exception as e:
        logger.error(f"MQTT客户端初始化失败: {e}")
        mqtt_enabled = False

# 水质数据配置 - 统一配置管理
WATER_QUALITY_CONFIG = {
    'temperature': {
        'min': 20, 'max': 35, 'optimal_min': 25, 'optimal_max': 30,
        'variation': 0.5, 'unit': '°C', 'name': '水温'
    },
    'oxygen': {
        'min': 4, 'max': 12, 'optimal_min': 6, 'optimal_max': 8,
        'variation': 0.3, 'unit': 'mg/L', 'name': '溶解氧'
    },
    'ph': {
        'min': 6.0, 'max': 9.0, 'optimal_min': 7.0, 'optimal_max': 7.5,
        'variation': 0.2, 'unit': '', 'name': 'pH值'
    },
    'tds': {
        'min': 200, 'max': 600, 'optimal_min': 300, 'optimal_max': 400,
        'variation': 20, 'unit': 'ppm', 'name': 'TDS值'
    },
    'turbidity': {
        'min': 1, 'max': 10, 'optimal_min': 2, 'optimal_max': 4,
        'variation': 0.5, 'unit': 'NTU', 'name': '浊度'
    }
}

# 坐标转换函数 - 解决坐标系不一致问题
def wgs84_to_gcj02(lng, lat):
    """WGS84坐标转GCJ02坐标（火星坐标系）"""
    import math

    def out_of_china(lng, lat):
        return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)

    def transform_lat(lng, lat):
        ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
        ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
        return ret

    def transform_lng(lng, lat):
        ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
        ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lng * math.pi) + 40.0 * math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(lng / 12.0 * math.pi) + 300.0 * math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
        return ret

    if out_of_china(lng, lat):
        return lng, lat

    dlat = transform_lat(lng - 105.0, lat - 35.0)
    dlng = transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - 0.00669342162296594323 * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((6378245.0 * (1 - 0.00669342162296594323)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (6378245.0 / sqrtmagic * math.cos(radlat) * math.pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return mglng, mglat

# 巡航路径GPS坐标 - 使用GCJ02坐标系（高德地图坐标系）
CRUISE_PATH_WGS84 = [
    {'longitude': 114.431280, 'latitude': 30.514498, 'sequence': 1},
    {'longitude': 114.431341, 'latitude': 30.514523, 'sequence': 2},
    {'longitude': 114.431376, 'latitude': 30.514591, 'sequence': 3},
    {'longitude': 114.431389, 'latitude': 30.514617, 'sequence': 4},
    {'longitude': 114.431405, 'latitude': 30.514683, 'sequence': 5},
    {'longitude': 114.431350, 'latitude': 30.514646, 'sequence': 6},
    {'longitude': 114.431314, 'latitude': 30.514584, 'sequence': 7},
    {'longitude': 114.431280, 'latitude': 30.514498, 'sequence': 8}
]

# 转换为GCJ02坐标系
CRUISE_PATH = []
for point in CRUISE_PATH_WGS84:
    gcj_lng, gcj_lat = wgs84_to_gcj02(point['longitude'], point['latitude'])
    CRUISE_PATH.append({
        'longitude': round(gcj_lng, 6),
        'latitude': round(gcj_lat, 6),
        'sequence': point['sequence']
    })

def init_data_files():
    """初始化数据文件"""
    # 创建巡航路径CSV文件
    cruise_df = pd.DataFrame(CRUISE_PATH)
    cruise_df.to_csv('cruise_path.csv', index=False)

    # 初始化水质数据文件
    if not os.path.exists('water_quality_data.csv'):
        df = pd.DataFrame(columns=['timestamp', 'temperature', 'oxygen', 'ph', 'tds', 'turbidity'])
        df.to_csv('water_quality_data.csv', index=False)

def validate_water_quality_value(param, value, config):
    """验证水质参数值的合理性"""
    if value < config['min']:
        logger.warning(f"⚠️ {config['name']}值过低: {value} < {config['min']}")
        return config['min']
    elif value > config['max']:
        logger.warning(f"⚠️ {config['name']}值过高: {value} > {config['max']}")
        return config['max']
    return value

def generate_water_quality_data():
    """生成虚拟水质数据 - 增强数据验证"""
    global water_quality_data

    current_time = datetime.now()

    try:
        # 如果是第一次生成数据，创建基础值
        if not water_quality_data:
            base_data = {}
            for param, config in WATER_QUALITY_CONFIG.items():
                # 在最优范围内生成初始值
                value = np.random.uniform(config['optimal_min'], config['optimal_max'])
                base_data[param] = validate_water_quality_value(param, value, config)
        else:
            # 基于上一次数据生成新数据（模拟缓慢变化）
            last_data = water_quality_data[-1]
            base_data = {}

            for param, config in WATER_QUALITY_CONFIG.items():
                # 在上次值基础上添加小幅变化
                variation = np.random.uniform(-config['variation'], config['variation'])
                new_value = last_data[param] + variation

                # 验证并修正值
                base_data[param] = validate_water_quality_value(param, new_value, config)

        # 添加时间戳
        data_point = {
            'timestamp': current_time.isoformat(),
            **base_data
        }

        water_quality_data.append(data_point)

        # 保存到CSV文件
        try:
            df = pd.DataFrame(water_quality_data)
            df.to_csv('water_quality_data.csv', index=False)
        except Exception as e:
            logger.error(f"保存水质数据失败: {e}")

        # 只保留最近24小时的数据在内存中
        cutoff_time = current_time - timedelta(hours=24)
        water_quality_data[:] = [d for d in water_quality_data
                               if datetime.fromisoformat(d['timestamp']) > cutoff_time]

        return data_point

    except Exception as e:
        logger.error(f"生成水质数据失败: {e}")
        # 返回默认数据
        return {
            'timestamp': current_time.isoformat(),
            'temperature': 25.0,
            'oxygen': 7.0,
            'ph': 7.2,
            'tds': 350,
            'turbidity': 3.0
        }

# 添加静态文件和首页路由
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

def create_lstm_model(input_shape):
    """创建LSTM预测模型"""
    if not ML_AVAILABLE:
        return None

    try:
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')
        return model
    except Exception as e:
        logger.error(f"创建LSTM模型失败: {e}")
        return None

def predict_with_lstm(data, param_name):
    """使用LSTM进行预测"""
    if not ML_AVAILABLE or len(data) < 60:
        return None

    try:
        # 数据预处理
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(data.reshape(-1, 1))

        # 创建训练数据
        X, y = [], []
        for i in range(60, len(scaled_data)):
            X.append(scaled_data[i-60:i, 0])
            y.append(scaled_data[i, 0])

        if len(X) < 10:  # 需要足够的训练数据
            return None

        X, y = np.array(X), np.array(y)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))

        # 创建并训练模型
        model = create_lstm_model((X.shape[1], 1))
        if model is None:
            return None

        model.fit(X, y, batch_size=1, epochs=1, verbose=0)

        # 预测未来24小时
        last_60_days = scaled_data[-60:]
        predictions = []

        for _ in range(24):
            X_test = np.array([last_60_days[-60:, 0]])
            X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
            pred = model.predict(X_test, verbose=0)
            predictions.append(pred[0, 0])
            last_60_days = np.append(last_60_days, pred)
            last_60_days = last_60_days[1:]

        # 反向缩放
        predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
        return predictions.flatten()

    except Exception as e:
        logger.error(f"LSTM预测失败 ({param_name}): {e}")
        return None

def predict_water_quality_advanced():
    """使用高级算法预测水质 - 优先使用LSTM，备用统计模型"""
    global prediction_results

    try:
        # 读取历史数据
        if os.path.exists('water_quality_data.csv'):
            df = pd.read_csv('water_quality_data.csv')
        else:
            return {"error": "没有足够的历史数据进行预测"}

        if len(df) < 10:  # 需要至少10个数据点
            return {"error": "历史数据不足，需要至少10个数据点"}

        predictions = {}
        current_time = datetime.now()
        model_used = "Statistical Model"

        # 为每个参数创建预测
        for param in ['temperature', 'oxygen', 'ph', 'tds', 'turbidity']:
            if param not in df.columns:
                continue

            # 获取历史数据
            param_data = df[param].values
            config = WATER_QUALITY_CONFIG[param]

            # 尝试使用LSTM预测
            lstm_predictions = predict_with_lstm(param_data, param)

            if lstm_predictions is not None and len(lstm_predictions) == 24:
                # LSTM预测成功
                future_predictions = [validate_water_quality_value(param, pred, config)
                                    for pred in lstm_predictions]
                model_used = "LSTM Neural Network"
            else:
                # 使用统计模型备用
                recent_data = param_data[-min(10, len(param_data)):]
                trend = np.polyfit(range(len(recent_data)), recent_data, 1)[0]
                std_value = np.std(recent_data)

                future_predictions = []
                for hour in range(1, 25):
                    # 基础预测值（基于趋势）
                    base_prediction = recent_data[-1] + trend * hour

                    # 添加周期性变化（模拟日夜变化）
                    cycle_factor = np.sin(2 * np.pi * hour / 24) * std_value * 0.3

                    # 添加随机噪声
                    noise = np.random.normal(0, std_value * 0.1)

                    # 综合预测值
                    prediction = base_prediction + cycle_factor + noise
                    prediction = validate_water_quality_value(param, prediction, config)
                    future_predictions.append(prediction)

            predictions[param] = [round(pred, 2) for pred in future_predictions]

        # 生成时间序列
        time_series = [(current_time + timedelta(hours=i)).isoformat()
                      for i in range(1, 25)]

        prediction_results = {
            'timestamp': current_time.isoformat(),
            'predictions': predictions,
            'time_series': time_series,
            'status': 'success',
            'model': model_used,
            'data_points': len(df)
        }

        logger.info(f"✓ 水质预测完成，使用模型: {model_used}")
        return prediction_results

    except Exception as e:
        logger.error(f"预测过程中出现错误: {e}")
        return {"error": f"预测过程中出现错误: {str(e)}"}

def schedule_prediction():
    """定时预测任务"""
    schedule.every().day.at("00:00").do(predict_water_quality_advanced)

def run_scheduler():
    """运行定时任务"""
    while True:
        schedule.run_pending()
        time.sleep(60)

# ==================== 水质监测API ====================

@app.route('/api/water-quality/current', methods=['GET'])
def get_current_water_quality():
    """获取当前水质数据"""
    try:
        # 生成最新数据
        current_data = generate_water_quality_data()

        return jsonify({
            "status": "success",
            "data": {
                "timestamp": current_data['timestamp'],
                "temperature": round(current_data['temperature'], 1),
                "oxygen": round(current_data['oxygen'], 1),
                "ph": round(current_data['ph'], 1),
                "tds": round(current_data['tds']),
                "turbidity": round(current_data['turbidity'], 1)
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/water-quality/history', methods=['GET'])
def get_water_quality_history():
    """获取历史水质数据"""
    try:
        hours = int(request.args.get('hours', 24))

        # 从CSV文件读取数据
        if os.path.exists('water_quality_data.csv'):
            df = pd.read_csv('water_quality_data.csv')

            # 过滤指定时间范围的数据
            cutoff_time = datetime.now() - timedelta(hours=hours)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df[df['timestamp'] > cutoff_time]

            # 转换为前端需要的格式
            history_data = []
            for _, row in df.iterrows():
                history_data.append({
                    "timestamp": row['timestamp'].isoformat(),
                    "temperature": round(row['temperature'], 1),
                    "oxygen": round(row['oxygen'], 1),
                    "ph": round(row['ph'], 1),
                    "tds": round(row['tds']),
                    "turbidity": round(row['turbidity'], 1)
                })

            return jsonify({
                "status": "success",
                "data": history_data,
                "count": len(history_data)
            })
        else:
            return jsonify({
                "status": "success",
                "data": [],
                "count": 0
            })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/water-quality/predict', methods=['POST'])
def trigger_water_quality_prediction():
    """触发水质预测"""
    try:
        result = predict_water_quality_advanced()

        if "error" in result:
            return jsonify({"status": "error", "message": result["error"]}), 400

        return jsonify({
            "status": "success",
            "message": "水质预测完成",
            "data": result
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/water-quality/prediction', methods=['GET'])
def get_water_quality_prediction():
    """获取预测结果"""
    try:
        if not prediction_results:
            # 如果没有预测结果，生成一次演示预测
            demo_prediction = generate_demo_prediction()
            return jsonify({
                "status": "success",
                "data": demo_prediction
            })

        return jsonify({
            "status": "success",
            "data": prediction_results
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== MQTT数据接收API ====================

@app.route('/api/position', methods=['GET'])
def get_position_data():
    """获取定位数据 - 重点关注"""
    try:
        global position_data

        if not position_data:
            return jsonify({
                "status": "success",
                "data": {
                    "timestamp": time.time(),
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "altitude": 0.0,
                    "speed": 0.0,
                    "course": 0.0,
                    "roll": 0.0,
                    "pitch": 0.0,
                    "yaw": 0.0,
                    "pos_accuracy": 0.0,
                    "heading_accuracy": 0.0,
                    "satellites": 0,
                    "valid": False,
                    "message": "等待定位数据"
                }
            })

        return jsonify({
            "status": "success",
            "data": position_data
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ai_detection', methods=['GET'])
def get_ai_detection_data():
    """获取AI检测数据"""
    try:
        global ai_detection_data

        if not ai_detection_data:
            return jsonify({
                "status": "success",
                "data": {
                    "timestamp": time.time(),
                    "detection": {
                        "disease_detected": False,
                        "detection_count": 0,
                        "detections": []
                    },
                    "message": "等待AI检测数据"
                }
            })

        return jsonify({
            "status": "success",
            "data": ai_detection_data
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/system_status', methods=['GET'])
def get_system_status_data():
    """获取系统状态数据"""
    try:
        global system_status_data

        if not system_status_data:
            return jsonify({
                "status": "success",
                "data": {
                    "timestamp": time.time(),
                    "navigation_state": "unknown",
                    "running": False,
                    "modules": {},
                    "hardware": {},
                    "message": "等待系统状态数据"
                }
            })

        return jsonify({
            "status": "success",
            "data": system_status_data
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== MQTT控制指令发送API ====================

@app.route('/api/control/navigation', methods=['POST'])
def send_navigation_control():
    """发送导航控制指令"""
    try:
        global mqtt_client, mqtt_enabled

        if not mqtt_enabled or not mqtt_client:
            return jsonify({"status": "error", "message": "MQTT功能不可用"}), 500

        data = request.get_json()
        command = data.get('command', '').upper()
        params = data.get('params', {})

        # 构建MQTT指令数据
        mqtt_command = {
            'command': command,
            'params': params,
            'timestamp': time.time(),
            'source': 'pc_control'
        }

        # 发送到MQTT主题
        result = mqtt_client.publish('control/navigation', json.dumps(mqtt_command))

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"导航控制指令已发送: {command}")
            return jsonify({
                "status": "success",
                "message": f"导航指令 {command} 发送成功",
                "command": command,
                "params": params
            })
        else:
            return jsonify({"status": "error", "message": f"MQTT发送失败，错误码: {result.rc}"}), 500

    except Exception as e:
        logger.error(f"导航控制指令发送错误: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/control/medication', methods=['POST'])
def send_medication_control():
    """发送投药控制指令"""
    try:
        global mqtt_client, mqtt_enabled

        if not mqtt_enabled or not mqtt_client:
            return jsonify({"status": "error", "message": "MQTT功能不可用"}), 500

        data = request.get_json()
        command = data.get('command', '').upper()

        # 构建MQTT指令数据
        mqtt_command = {
            'command': command,
            'bay_id': data.get('bay_id', 1),
            'volume': data.get('volume', 100),
            'duration': data.get('duration', 30),
            'timestamp': time.time(),
            'source': 'pc_control'
        }

        # 发送到MQTT主题
        result = mqtt_client.publish('control/medication', json.dumps(mqtt_command))

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"投药控制指令已发送: {command}")
            return jsonify({
                "status": "success",
                "message": f"投药指令 {command} 发送成功",
                "command": command,
                "bay_id": mqtt_command['bay_id'],
                "volume": mqtt_command['volume']
            })
        else:
            return jsonify({"status": "error", "message": f"MQTT发送失败，错误码: {result.rc}"}), 500

    except Exception as e:
        logger.error(f"投药控制指令发送错误: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/control/system', methods=['POST'])
def send_system_control():
    """发送系统控制指令"""
    try:
        global mqtt_client, mqtt_enabled

        if not mqtt_enabled or not mqtt_client:
            return jsonify({"status": "error", "message": "MQTT功能不可用"}), 500

        data = request.get_json()
        command = data.get('command', '').upper()

        # 构建MQTT指令数据
        mqtt_command = {
            'command': command,
            'module': data.get('module', ''),
            'timestamp': time.time(),
            'source': 'pc_control'
        }

        # 发送到MQTT主题
        result = mqtt_client.publish('control/system', json.dumps(mqtt_command))

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"系统控制指令已发送: {command}")
            return jsonify({
                "status": "success",
                "message": f"系统指令 {command} 发送成功",
                "command": command,
                "module": mqtt_command['module']
            })
        else:
            return jsonify({"status": "error", "message": f"MQTT发送失败，错误码: {result.rc}"}), 500

    except Exception as e:
        logger.error(f"系统控制指令发送错误: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/control/emergency', methods=['POST'])
def send_emergency_control():
    """发送紧急控制指令"""
    try:
        global mqtt_client, mqtt_enabled

        if not mqtt_enabled or not mqtt_client:
            return jsonify({"status": "error", "message": "MQTT功能不可用"}), 500

        data = request.get_json()
        command = data.get('command', 'EMERGENCY_STOP').upper()

        # 构建MQTT指令数据
        mqtt_command = {
            'command': command,
            'timestamp': time.time(),
            'source': 'pc_control',
            'priority': 'emergency'
        }

        # 发送到MQTT主题
        result = mqtt_client.publish('control/emergency', json.dumps(mqtt_command))

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"紧急控制指令已发送: {command}")
            return jsonify({
                "status": "success",
                "message": f"紧急指令 {command} 发送成功",
                "command": command
            })
        else:
            return jsonify({"status": "error", "message": f"MQTT发送失败，错误码: {result.rc}"}), 500

    except Exception as e:
        logger.error(f"紧急控制指令发送错误: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def generate_demo_prediction():
    """生成演示预测数据"""
    current_time = datetime.now()

    # 生成未来24小时的预测数据
    predictions = {}
    time_series = []

    for i in range(1, 25):
        time_series.append((current_time + timedelta(hours=i)).isoformat())

    # 为每个参数生成预测值
    for param, config in WATER_QUALITY_CONFIG.items():
        base_value = (config['min'] + config['max']) / 2
        predictions[param] = []

        for i in range(24):
            # 添加一些随机变化和趋势
            trend = np.sin(i * np.pi / 12) * config['variation'] * 0.5  # 12小时周期
            noise = np.random.uniform(-config['variation'] * 0.3, config['variation'] * 0.3)
            value = base_value + trend + noise

            # 确保值在合理范围内
            value = max(config['min'], min(config['max'], value))
            predictions[param].append(round(value, 2))

    return {
        'timestamp': current_time.isoformat(),
        'predictions': predictions,
        'time_series': time_series,
        'status': 'success',
        'note': '这是演示预测数据'
    }

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({"status": "ok", "message": "后端服务运行正常"})

@app.route('/api/config/map', methods=['GET'])
def get_map_config():
    """获取地图配置信息"""
    try:
        return jsonify({
            "status": "success",
            "data": {
                "amap_api_key": AMAP_API_KEY,
                "map_center": {
                    "longitude": 114.431280,
                    "latitude": 30.514498
                },
                "zoom_level": 18
            }
        })
    except Exception as e:
        logger.error(f"获取地图配置失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """处理与Coze机器人的对话"""
    data = request.json
    message = data.get('message', '')
    conversation_id = data.get('conversation_id')
    stream = data.get('stream', True)  # 默认使用流式响应
    
    # 准备Coze API请求头
    headers = {
        'Authorization': f'Bearer {COZE_AUTH_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # 准备Coze API请求体
    payload = {
        'bot_id': COZE_BOT_ID,
        'user_id': COZE_USER_ID,
        'stream': stream,
        'auto_save_history': True,
        'additional_messages': [
            {
                'role': 'user',
                'content': message,
                'content_type': 'text'
            }
        ]
    }
    
    # 如果有会话ID，添加到URL
    if conversation_id:
        url = f"{COZE_API_BASE}/chat?conversation_id={conversation_id}"
    else:
        url = f"{COZE_API_BASE}/chat"
    
    # 如果是流式响应
    if stream:
        def generate():
            response = requests.post(url, headers=headers, json=payload, stream=True)
            
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    
                    # 提取事件和数据
                    if line_text.startswith('event:'):
                        event = line_text[6:].strip()
                        continue
                    
                    if line_text.startswith('data:'):
                        data = line_text[5:].strip()
                        
                        # 解析JSON数据
                        try:
                            json_data = json.loads(data)
                            
                            # 保存会话ID
                            if 'id' in json_data and 'conversation_id' in json_data:
                                conversations[json_data['conversation_id']] = json_data['id']
                                
                            # 转发事件和数据
                            yield f"data: {json.dumps({'event': event, 'data': json_data})}\n\n"
                            
                        except json.JSONDecodeError:
                            # 处理非JSON数据
                            yield f"data: {json.dumps({'event': event, 'data': data})}\n\n"
            
            # 结束流
            yield "data: [DONE]\n\n"
        
        return Response(stream_with_context(generate()), content_type='text/event-stream')
    
    # 如果是非流式响应
    else:
        response = requests.post(url, headers=headers, json=payload)
        return jsonify(response.json())

@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """列出已知的会话"""
    return jsonify(conversations)

@app.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
def get_conversation_messages(conversation_id):
    """获取特定会话的消息"""
    if conversation_id not in conversations:
        return jsonify({"error": "Conversation not found"}), 404
    
    chat_id = conversations[conversation_id]
    
    headers = {
        'Authorization': f'Bearer {COZE_AUTH_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    url = f"{COZE_API_BASE}/chat/message/list?chat_id={chat_id}&conversation_id={conversation_id}"
    
    response = requests.get(url, headers=headers)
    return jsonify(response.json())

@app.route('/api/submit_tool_outputs', methods=['POST'])
def submit_tool_outputs():
    """提交工具执行结果"""
    data = request.json
    chat_id = data.get('chat_id')
    conversation_id = data.get('conversation_id')
    tool_outputs = data.get('tool_outputs', [])
    
    if not chat_id or not conversation_id:
        return jsonify({"error": "Missing chat_id or conversation_id"}), 400
    
    headers = {
        'Authorization': f'Bearer {COZE_AUTH_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    url = f"{COZE_API_BASE}/chat/submit_tool_outputs?chat_id={chat_id}&conversation_id={conversation_id}"
    
    payload = {
        'tool_outputs': tool_outputs
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return jsonify(response.json())

@app.route('/api/cancel_chat', methods=['POST'])
def cancel_chat():
    """取消进行中的对话"""
    data = request.json
    chat_id = data.get('chat_id')
    conversation_id = data.get('conversation_id')

    if not chat_id or not conversation_id:
        return jsonify({"error": "Missing chat_id or conversation_id"}), 400

    headers = {
        'Authorization': f'Bearer {COZE_AUTH_TOKEN}',
        'Content-Type': 'application/json'
    }

    url = f"{COZE_API_BASE}/chat/cancel"

    payload = {
        'chat_id': chat_id,
        'conversation_id': conversation_id
    }

    response = requests.post(url, headers=headers, json=payload)
    return jsonify(response.json())

# ==================== 巡航控制API ====================

def smooth_path_bezier(points, num_points=100):
    """使用贝塞尔曲线平滑路径"""
    if len(points) < 2:
        return points

    # 提取经纬度
    lons = [p['longitude'] for p in points]
    lats = [p['latitude'] for p in points]

    # 创建参数t
    t_original = np.linspace(0, 1, len(points))
    t_smooth = np.linspace(0, 1, num_points)

    # 使用三次样条插值
    try:
        f_lon = interp1d(t_original, lons, kind='cubic', bounds_error=False, fill_value='extrapolate')
        f_lat = interp1d(t_original, lats, kind='cubic', bounds_error=False, fill_value='extrapolate')

        smooth_lons = f_lon(t_smooth)
        smooth_lats = f_lat(t_smooth)

        smooth_points = []
        for i, (lon, lat) in enumerate(zip(smooth_lons, smooth_lats)):
            smooth_points.append({
                'longitude': round(float(lon), 6),
                'latitude': round(float(lat), 6),
                'sequence': i + 1
            })

        return smooth_points
    except:
        # 如果插值失败，返回原始点
        return points

@app.route('/api/cruise/start', methods=['POST'])
def start_cruise():
    """开始巡航任务"""
    global cruise_status

    try:
        data = request.json
        location = data.get('location', '华中科技大学渔场')
        coordinates = data.get('coordinates', [])
        device_id = data.get('deviceId', 'RDKX5-001')
        timestamp = data.get('timestamp', datetime.now().isoformat())

        # 如果没有提供坐标，使用默认路径
        if not coordinates:
            coordinates = CRUISE_PATH

        # 生成平滑路径
        smooth_coordinates = smooth_path_bezier(coordinates, num_points=50)

        # 更新巡航状态
        cruise_status = {
            'active': True,
            'current_position': coordinates[0] if coordinates else None,
            'path': smooth_coordinates,
            'start_time': timestamp,
            'device_id': device_id
        }

        # 模拟RDKX5设备API调用
        cruise_response = {
            "status": "success",
            "message": "巡航任务已启动",
            "task_id": f"cruise_{int(time.time())}",
            "device_id": device_id,
            "location": location,
            "original_coordinates": coordinates,
            "smooth_path": smooth_coordinates,
            "start_time": timestamp,
            "estimated_duration": f"{len(coordinates) * 2}分钟",
            "path_points": len(smooth_coordinates)
        }

        return jsonify(cruise_response)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cruise/status', methods=['GET'])
def get_cruise_status():
    """获取当前巡航状态"""
    try:
        return jsonify({
            "status": "success",
            "data": cruise_status
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cruise/stop', methods=['POST'])
def stop_cruise():
    """停止巡航"""
    global cruise_status

    try:
        cruise_status['active'] = False

        return jsonify({
            "status": "success",
            "message": "巡航已停止",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cruise/speed', methods=['POST'])
def set_cruise_speed():
    """设置巡航速度"""
    try:
        data = request.get_json()
        speed = data.get('speed', 'medium')
        device_id = data.get('deviceId', 'RDKX5-001')

        # 验证速度值
        valid_speeds = ['low', 'medium', 'high']
        if speed not in valid_speeds:
            return jsonify({"status": "error", "message": "无效的速度设置"}), 400

        # 速度映射
        speed_mapping = {
            'low': {'value': 1.0, 'name': '低速'},
            'medium': {'value': 2.0, 'name': '中速'},
            'high': {'value': 3.0, 'name': '高速'}
        }

        speed_info = speed_mapping[speed]

        # 更新全局巡航状态
        global cruise_status
        if 'speed_settings' not in cruise_status:
            cruise_status['speed_settings'] = {}

        cruise_status['speed_settings'] = {
            'speed': speed,
            'speed_value': speed_info['value'],
            'speed_name': speed_info['name'],
            'device_id': device_id,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"巡航速度已设置为: {speed_info['name']} ({speed_info['value']} m/s)")

        return jsonify({
            "status": "success",
            "message": f"巡航速度已设置为{speed_info['name']}",
            "data": {
                "speed": speed,
                "speed_value": speed_info['value'],
                "speed_name": speed_info['name'],
                "device_id": device_id,
                "timestamp": datetime.now().isoformat()
            }
        })

    except Exception as e:
        logger.error(f"设置巡航速度失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cruise/speed', methods=['GET'])
def get_cruise_speed():
    """获取当前巡航速度"""
    try:
        global cruise_status
        speed_settings = cruise_status.get('speed_settings', {
            'speed': 'medium',
            'speed_value': 2.0,
            'speed_name': '中速',
            'device_id': 'RDKX5-001',
            'timestamp': datetime.now().isoformat()
        })

        return jsonify({
            "status": "success",
            "data": speed_settings
        })

    except Exception as e:
        logger.error(f"获取巡航速度失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cruise/path', methods=['GET'])
def get_cruise_path():
    """获取巡航路径点"""
    try:
        # 读取巡航路径CSV文件
        if os.path.exists('cruise_path.csv'):
            df = pd.read_csv('cruise_path.csv')
            path_data = df.to_dict('records')
        else:
            path_data = CRUISE_PATH

        # 生成平滑路径
        smooth_path = smooth_path_bezier(path_data, num_points=50)

        return jsonify({
            "status": "success",
            "data": {
                "original_path": path_data,
                "smooth_path": smooth_path,
                "total_points": len(smooth_path)
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/medicine/deploy', methods=['POST'])
def deploy_medicine():
    """药品投放API"""
    data = request.json
    medicine_1 = data.get('medicine_1', {})
    medicine_2 = data.get('medicine_2', {})
    location = data.get('location', '')

    deploy_response = {
        "status": "success",
        "message": "药品投放指令已发送",
        "task_id": f"medicine_{int(time.time())}",
        "location": location,
        "medicines": []
    }

    if medicine_1.get('name'):
        deploy_response["medicines"].append({
            "tank": "1号药仓",
            "name": medicine_1.get('name'),
            "dosage": medicine_1.get('dosage'),
            "unit": "ml/亩米"
        })

    if medicine_2.get('name'):
        deploy_response["medicines"].append({
            "tank": "2号药仓",
            "name": medicine_2.get('name'),
            "dosage": medicine_2.get('dosage'),
            "unit": "ml/亩米"
        })

    return jsonify(deploy_response)

@app.route('/api/predict/water-quality', methods=['POST'])
def predict_water_quality():
    """水质预测API"""
    data = request.json
    temperature = data.get('temperature', 0)
    oxygen = data.get('oxygen', 0)
    ph = data.get('ph', 0)
    tds = data.get('tds', 0)
    turbidity = data.get('turbidity', 0)
    timestamp = data.get('timestamp', '')

    # 模拟AI预测算法
    import random

    # 基于当前数据生成预测值
    predicted_temp = temperature + random.uniform(-2, 2)
    predicted_oxygen = max(0, oxygen + random.uniform(-1, 1))
    predicted_ph = max(0, ph + random.uniform(-0.5, 0.5))
    predicted_tds = max(0, tds + random.uniform(-50, 50))
    predicted_turbidity = max(0, turbidity + random.uniform(-0.5, 0.5))

    # 风险评估
    risk_factors = []
    if predicted_oxygen < 5.0:
        risk_factors.append('溶解氧偏低')
    if predicted_temp > 28 or predicted_temp < 18:
        risk_factors.append('水温异常')
    if predicted_ph < 6.5 or predicted_ph > 8.5:
        risk_factors.append('pH值异常')
    if predicted_tds > 500:
        risk_factors.append('TDS值过高')
    if predicted_turbidity > 5:
        risk_factors.append('浊度过高')

    # 确定风险等级
    if len(risk_factors) >= 3:
        risk_level = 'high'
    elif len(risk_factors) >= 1:
        risk_level = 'medium'
    else:
        risk_level = 'low'

    # 生成建议
    recommendations = []
    if predicted_oxygen < 5.0:
        recommendations.append('建议增加增氧设备运行时间')
    if predicted_temp > 28:
        recommendations.append('注意降低水温，增加遮阳措施')
    elif predicted_temp < 18:
        recommendations.append('考虑加温措施')
    if predicted_ph < 6.5:
        recommendations.append('建议投放石灰调节pH值')
    elif predicted_ph > 8.5:
        recommendations.append('建议投放酸性调节剂')
    if predicted_tds > 500:
        recommendations.append('建议更换部分水体')
    if predicted_turbidity > 5:
        recommendations.append('建议投放絮凝剂澄清水质')

    if not recommendations:
        recommendations = ['水质状况良好，继续保持当前管理措施']

    prediction_response = {
        "status": "success",
        "message": "水质预测完成",
        "prediction": {
            "next_24h": {
                "temperature": round(predicted_temp, 1),
                "oxygen": round(predicted_oxygen, 1),
                "ph": round(predicted_ph, 1),
                "tds": round(predicted_tds),
                "turbidity": round(predicted_turbidity, 1)
            },
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendations": recommendations,
            "confidence": round(random.uniform(0.75, 0.95), 2)
        },
        "timestamp": timestamp
    }

    return jsonify(prediction_response)

# ==================== 应用初始化和启动 ====================

def initialize_app():
    """初始化应用"""
    print("正在初始化渔场管理系统后端...")

    # 初始化数据文件
    init_data_files()
    print("✓ 数据文件初始化完成")

    # 生成初始水质数据
    for _ in range(10):  # 生成10个初始数据点
        generate_water_quality_data()
        time.sleep(0.1)  # 避免时间戳重复
    print("✓ 初始水质数据生成完成")

    # 生成演示预测数据
    global prediction_results
    prediction_results = generate_demo_prediction()
    print("✓ 演示预测数据生成完成")

    # 启动定时任务线程
    schedule_prediction()
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("✓ 定时预测任务启动完成")

    # 启动数据生成定时器
    def generate_data_periodically():
        while True:
            generate_water_quality_data()
            time.sleep(60)  # 每分钟生成一次数据

    data_thread = threading.Thread(target=generate_data_periodically, daemon=True)
    data_thread.start()
    print("✓ 水质数据定时生成启动完成")

    # 初始化MQTT数据接收客户端
    init_mqtt_client()
    print("✓ MQTT数据接收客户端启动完成")

    print("🚀 渔场管理系统后端初始化完成！")
    print("📊 监测功能：实时水质数据生成和LSTM预测")
    print("🚢 控制功能：巡航路径管理和平滑算法")
    print("🤖 AI助手：Coze API集成")
    print("🌐 访问地址：http://localhost:5001")

if __name__ == '__main__':
    # 初始化应用
    initialize_app()

    # 启动Flask应用
    app.run(debug=True, port=5001, host='0.0.0.0')
