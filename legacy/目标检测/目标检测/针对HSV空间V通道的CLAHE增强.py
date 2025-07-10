#!/usr/bin/env python
# Copyright (c) 2024，WuChao D-Robotics.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# 注意: 此程序在RDK板端端运行
# Attention: This program runs on RDK board.

import cv2
import numpy as np
from scipy.special import softmax
from hobot_dnn import pyeasy_dnn as dnn  # BSP Python API

from time import time
import argparse
import logging
import threading
import socket
import json
from flask import Flask, Response, render_template_string

# 导入MQTT客户端
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    print("警告: paho-mqtt库未安装，MQTT功能将不可用")
    MQTT_AVAILABLE = False

# 日志模块配置
logging.basicConfig(
    level = logging.INFO,
    format = '[%(name)s] [%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S')
logger = logging.getLogger("RDK_YOLO_WEBCAM")

# Flask app
app = Flask(__name__)
output_frame = None
lock = threading.Lock()

# MQTT客户端全局变量
mqtt_client = None
mqtt_enabled = MQTT_AVAILABLE
mqtt_broker = 'localhost'
mqtt_port = 1883
mqtt_topic = 'ai/detection'

def init_mqtt_client():
    """初始化MQTT客户端"""
    global mqtt_client, mqtt_enabled

    if not mqtt_enabled:
        logger.info("MQTT功能不可用，跳过MQTT客户端初始化")
        return

    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(mqtt_broker, mqtt_port, 60)
        mqtt_client.loop_start()  # 启动后台线程处理网络流量
        logger.info(f"AI检测模块MQTT客户端已连接到 {mqtt_broker}:{mqtt_port}")
    except Exception as e:
        logger.error(f"AI检测模块MQTT客户端连接失败: {e}")
        mqtt_enabled = False

def send_mqtt_detection(detection_results):
    """发送AI检测结果到MQTT主题"""
    global mqtt_client, mqtt_enabled

    if not mqtt_enabled or not mqtt_client:
        return

    try:
        # 构建检测结果数据
        mqtt_data = {
            'timestamp': time(),
            'data_type': 'ai_detection',
            'detection': {
                'disease_detected': len(detection_results) > 0,
                'detection_count': len(detection_results),
                'detections': []
            }
        }

        # 添加检测详情
        for class_id, score, bbox in detection_results:
            detection_info = {
                'class_id': int(class_id),
                'confidence': float(score),
                'bbox': {
                    'x': int(bbox[0]),
                    'y': int(bbox[1]),
                    'width': int(bbox[2] - bbox[0]),
                    'height': int(bbox[3] - bbox[1])
                },
                'disease_type': '鱼类病害' if class_id > 0 else '正常',  # 简化的疾病类型
                'urgency_level': 'high' if score > 0.8 else 'medium' if score > 0.5 else 'low'
            }
            mqtt_data['detection']['detections'].append(detection_info)

        # 发送到MQTT主题
        result = mqtt_client.publish(mqtt_topic, json.dumps(mqtt_data))

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"AI检测结果已发送到MQTT主题: {mqtt_topic}")
        else:
            logger.error(f"AI检测结果MQTT发送失败，错误码: {result.rc}")

    except Exception as e:
        logger.error(f"AI检测结果MQTT发送错误: {e}")

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>YOLOv11 RDK X5 实时检测</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            text-align: center;
            background-color: #f0f0f0;
        }
        h1 {
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .video-container {
            margin-top: 20px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>YOLOv11 on RDK X5 实时目标检测</h1>
        <div class="video-container">
            <img src="{{ url_for('video_feed') }}" width="100%">
        </div>
    </div>
</body>
</html>
'''

def get_local_ip():
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

class BaseModel:
    def __init__(
        self,
        model_file: str
        ) -> None:
        # 加载BPU的bin模型, 打印相关参数
        try:
            begin_time = time()
            self.quantize_model = dnn.load(model_file)
            logger.debug("\033[1;31m" + "Load D-Robotics Quantize model time = %.2f ms"%(1000*(time() - begin_time)) + "\033[0m")
        except Exception as e:
            logger.error("❌ Failed to load model file: %s"%(model_file))
            logger.error("You can download the model file from the following docs: ./models/download.md") 
            logger.error(e)
            exit(1)

        logger.info("\033[1;32m" + "-> input tensors" + "\033[0m")
        for i, quantize_input in enumerate(self.quantize_model[0].inputs):
            logger.info(f"intput[{i}], name={quantize_input.name}, type={quantize_input.properties.dtype}, shape={quantize_input.properties.shape}")

        logger.info("\033[1;32m" + "-> output tensors" + "\033[0m")
        for i, quantize_input in enumerate(self.quantize_model[0].outputs):
            logger.info(f"output[{i}], name={quantize_input.name}, type={quantize_input.properties.dtype}, shape={quantize_input.properties.shape}")

        self.model_input_height, self.model_input_weight = self.quantize_model[0].inputs[0].properties.shape[2:4]

    def resizer(self, img: np.ndarray)->np.ndarray:
        img_h, img_w = img.shape[0:2]
        self.y_scale, self.x_scale = img_h/self.model_input_height, img_w/self.model_input_weight
        return cv2.resize(img, (self.model_input_weight, self.model_input_height), interpolation=cv2.INTER_NEAREST) # 利用resize重新开辟内存
    
    def bgr2nv12(self, bgr_img: np.ndarray) -> np.ndarray:
        """
        Convert a BGR image to the NV12 format.
        """
        begin_time = time()
        bgr_img = self.resizer(bgr_img)
        height, width = bgr_img.shape[0], bgr_img.shape[1]
        area = height * width
        yuv420p = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2YUV_I420).reshape((area * 3 // 2,))
        y = yuv420p[:area]
        uv_planar = yuv420p[area:].reshape((2, area // 4))
        uv_packed = uv_planar.transpose((1, 0)).reshape((area // 2,))
        nv12 = np.zeros_like(yuv420p)
        nv12[:height * width] = y
        nv12[height * width:] = uv_packed

        logger.debug("\033[1;31m" + f"bgr8 to nv12 time = {1000*(time() - begin_time):.2f} ms" + "\033[0m")
        return nv12

    def forward(self, input_tensor: np.array) -> list[dnn.pyDNNTensor]:
        begin_time = time()
        quantize_outputs = self.quantize_model[0].forward(input_tensor)
        logger.debug("\033[1;31m" + f"forward time = {1000*(time() - begin_time):.2f} ms" + "\033[0m")
        return quantize_outputs

    def c2numpy(self, outputs) -> list[np.array]:
        begin_time = time()
        outputs = [dnnTensor.buffer for dnnTensor in outputs]
        logger.debug("\033[1;31m" + f"c to numpy time = {1000*(time() - begin_time):.2f} ms" + "\033[0m")
        return outputs

class YOLO11_Detect(BaseModel):
    def __init__(self, 
                model_file: str, 
                conf: float, 
                iou: float,
                classes_num: int = 22  # 添加类别数参数，默认为22
                ):
        super().__init__(model_file)
        # 量化模型相关处理 - 注释掉可能不存在的scale_data属性
        # self.s_bboxes_scale = self.quantize_model[0].outputs[0].properties.scale_data[np.newaxis, :]
        # self.m_bboxes_scale = self.quantize_model[0].outputs[1].properties.scale_data[np.newaxis, :]
        # self.l_bboxes_scale = self.quantize_model[0].outputs[2].properties.scale_data[np.newaxis, :]
        # logger.info(f"{self.s_bboxes_scale.shape=}, {self.m_bboxes_scale.shape=}, {self.l_bboxes_scale.shape=}")

        # DFL求期望的系数, 只需要生成一次
        self.weights_static = np.array([i for i in range(16)]).astype(np.float32)[np.newaxis, np.newaxis, :]
        logger.info(f"{self.weights_static.shape = }")

        # anchors, 只需要生成一次
        self.s_anchor = np.stack([np.tile(np.linspace(0.5, 79.5, 80), reps=80), 
                            np.repeat(np.arange(0.5, 80.5, 1), 80)], axis=0).transpose(1,0)
        self.m_anchor = np.stack([np.tile(np.linspace(0.5, 39.5, 40), reps=40), 
                            np.repeat(np.arange(0.5, 40.5, 1), 40)], axis=0).transpose(1,0)
        self.l_anchor = np.stack([np.tile(np.linspace(0.5, 19.5, 20), reps=20), 
                            np.repeat(np.arange(0.5, 20.5, 1), 20)], axis=0).transpose(1,0)
        logger.info(f"{self.s_anchor.shape = }, {self.m_anchor.shape = }, {self.l_anchor.shape = }")

        # 输入图像大小, 一些阈值, 提前计算好
        self.input_image_size = 640
        self.conf = conf
        self.iou = iou
        self.classes_num = classes_num  # 保存类别数
        self.conf_inverse = -np.log(1/conf - 1)
        logger.info("iou threshol = %.2f, conf threshol = %.2f"%(iou, conf))
        logger.info("sigmoid_inverse threshol = %.2f"%self.conf_inverse)
        logger.info(f"类别数: {self.classes_num}")
    
    def postProcess(self, outputs: list[np.ndarray], class_offset: int = 0) -> tuple[list]:
        begin_time = time()
        # reshape - 调整索引顺序以适应当前模型输出
        s_clses = outputs[0].reshape(-1, self.classes_num)  # 小尺度类别信息
        s_bboxes = outputs[1].reshape(-1, 64)               # 小尺度边界框信息
        m_clses = outputs[2].reshape(-1, self.classes_num)  # 中尺度类别信息
        m_bboxes = outputs[3].reshape(-1, 64)               # 中尺度边界框信息
        l_clses = outputs[4].reshape(-1, self.classes_num)  # 大尺度类别信息
        l_bboxes = outputs[5].reshape(-1, 64)               # 大尺度边界框信息

        # classify: 利用numpy向量化操作完成阈值筛选(优化版 2.0)
        s_max_scores = np.max(s_clses, axis=1)
        s_valid_indices = np.flatnonzero(s_max_scores >= self.conf_inverse)  # 得到大于阈值分数的索引，此时为小数字
        s_ids = np.argmax(s_clses[s_valid_indices, : ], axis=1)
        s_scores = s_max_scores[s_valid_indices]

        m_max_scores = np.max(m_clses, axis=1)
        m_valid_indices = np.flatnonzero(m_max_scores >= self.conf_inverse)  # 得到大于阈值分数的索引，此时为小数字
        m_ids = np.argmax(m_clses[m_valid_indices, : ], axis=1)
        m_scores = m_max_scores[m_valid_indices]

        l_max_scores = np.max(l_clses, axis=1)
        l_valid_indices = np.flatnonzero(l_max_scores >= self.conf_inverse)  # 得到大于阈值分数的索引，此时为小数字
        l_ids = np.argmax(l_clses[l_valid_indices, : ], axis=1)
        l_scores = l_max_scores[l_valid_indices]

        # 3个Classify分类分支：Sigmoid计算
        s_scores = 1 / (1 + np.exp(-s_scores))
        m_scores = 1 / (1 + np.exp(-m_scores))
        l_scores = 1 / (1 + np.exp(-l_scores))

        # 3个Bounding Box分支：筛选
        s_bboxes_float32 = s_bboxes[s_valid_indices,:]
        m_bboxes_float32 = m_bboxes[m_valid_indices,:]
        l_bboxes_float32 = l_bboxes[l_valid_indices,:]

        # 3个Bounding Box分支：dist2bbox (ltrb2xyxy)
        s_ltrb_indices = np.sum(softmax(s_bboxes_float32.reshape(-1, 4, 16), axis=2) * self.weights_static, axis=2)
        s_anchor_indices = self.s_anchor[s_valid_indices, :]
        s_x1y1 = s_anchor_indices - s_ltrb_indices[:, 0:2]
        s_x2y2 = s_anchor_indices + s_ltrb_indices[:, 2:4]
        s_dbboxes = np.hstack([s_x1y1, s_x2y2])*8

        m_ltrb_indices = np.sum(softmax(m_bboxes_float32.reshape(-1, 4, 16), axis=2) * self.weights_static, axis=2)
        m_anchor_indices = self.m_anchor[m_valid_indices, :]
        m_x1y1 = m_anchor_indices - m_ltrb_indices[:, 0:2]
        m_x2y2 = m_anchor_indices + m_ltrb_indices[:, 2:4]
        m_dbboxes = np.hstack([m_x1y1, m_x2y2])*16

        l_ltrb_indices = np.sum(softmax(l_bboxes_float32.reshape(-1, 4, 16), axis=2) * self.weights_static, axis=2)
        l_anchor_indices = self.l_anchor[l_valid_indices,:]
        l_x1y1 = l_anchor_indices - l_ltrb_indices[:, 0:2]
        l_x2y2 = l_anchor_indices + l_ltrb_indices[:, 2:4]
        l_dbboxes = np.hstack([l_x1y1, l_x2y2])*32

        # 大中小特征层阈值筛选结果拼接
        dbboxes = np.concatenate((s_dbboxes, m_dbboxes, l_dbboxes), axis=0)
        scores = np.concatenate((s_scores, m_scores, l_scores), axis=0)
        ids = np.concatenate((s_ids, m_ids, l_ids), axis=0)

        # nms
        indices = cv2.dnn.NMSBoxes(dbboxes, scores, self.conf, self.iou)

        # 还原到原始的img尺度
        bboxes = dbboxes[indices] * np.array([self.x_scale, self.y_scale, self.x_scale, self.y_scale])
        bboxes = bboxes.astype(np.int32)
        
        # 在返回结果前应用类别ID偏移
        if class_offset != 0 and len(indices) > 0:
            # 首先获取索引后的结果
            result_ids = ids[indices]
            # 应用偏移并确保在有效范围内
            result_ids = (result_ids + class_offset) % self.classes_num
            logger.debug(f"应用类别ID偏移: {class_offset}, 调整前: {ids[indices]}, 调整后: {result_ids}")
            # 更新返回值
            ids_to_return = result_ids
        else:
            ids_to_return = ids[indices]

        # 输出类别ID的统计信息，帮助诊断问题
        if len(indices) > 0:
            logger.info(f"检测到 {len(indices)} 个目标")
            unique_ids = np.unique(ids_to_return)
            logger.info(f"检测到的类别ID: {unique_ids}")
            for id in unique_ids:
                count = np.sum(ids_to_return == id)
                if 0 <= id < len(coco_names):
                    logger.info(f"类别 {id} ({coco_names[id]}): {count}个")
                else:
                    logger.warning(f"类别 {id} (超出范围): {count}个")

        logger.debug("\033[1;31m" + f"Post Process time = {1000*(time() - begin_time):.2f} ms" + "\033[0m")

        return ids_to_return, scores[indices], bboxes

coco_names = [
    "气单胞菌败血症", "柱状病", "细菌性红斑病", "流行性溃疡", 
    "细菌性鳃病", "真菌腐皮病", "健康鱼", "白点病",
    "寄生虫病", "链球菌", "罗湖病", "溃疡",
    "烂鳃", "气损伤", "眼病", "金鱼",
    "金鱼水肿", "金鱼白点病", "金鱼败血症", "黑斑病",
    "黑鳃病", "白斑综合征"
]

# 添加英文名称列表用于解决可能的中文编码问题
english_names = [
    "Aeromonas", "Columnaris", "BacterialRed", "EUS", 
    "BacterialGill", "Fungal", "Healthy", "WhiteSpots",
    "Parasitic", "Streptococcus", "TiLV", "Kuiyang",
    "Lansai", "Qisunshang", "Yanbing", "Goldfish",
    "GoldfishDropsy", "GoldfishIch", "GoldfishSepticemia", "BlackSpots",
    "Blackgill", "WSSV"
]

rdk_colors = [
    (56, 56, 255), (151, 157, 255), (31, 112, 255), (29, 178, 255),(49, 210, 207), (10, 249, 72), (23, 204, 146), (134, 219, 61),
    (52, 147, 26), (187, 212, 0), (168, 153, 44), (255, 194, 0),(147, 69, 52), (255, 115, 100), (236, 24, 0), (255, 56, 132),
    (133, 0, 82), (255, 56, 203), (200, 149, 255), (199, 55, 255)]

def draw_detection(img: np.array, 
                   bbox: tuple[int, int, int, int],
                   score: float, 
                   class_id: int,
                   use_english: bool = False) -> None:
    """
    Draws a detection bounding box and label on the image.
    """
    x1, y1, x2, y2 = bbox
    color = rdk_colors[class_id%20]
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    
    # 添加类别ID边界检查
    if 0 <= class_id < len(coco_names):
        if use_english and class_id < len(english_names):
            class_name = english_names[class_id]
        else:
            class_name = coco_names[class_id]
    else:
        # 如果类别ID超出范围，则显示ID值
        logger.warning(f"类别ID {class_id} 超出范围(0-{len(coco_names)-1})!")
        class_name = f"Unknown{class_id}"
    
    label = f"{class_name}: {score:.2f}"
    logger.debug(f"检测到: 类别={class_id}, 名称={class_name}, 置信度={score:.2f}")
    
    (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    label_x, label_y = x1, y1 - 10 if y1 - 10 > label_height else y1 + 10
    cv2.rectangle(
        img, (label_x, label_y - label_height), (label_x + label_width, label_y + label_height), color, cv2.FILLED
    )
    cv2.putText(img, label, (label_x, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

def apply_clahe_to_v_channel(image, clip_limit=2.0, grid_size=8):
    """对HSV空间的V通道应用CLAHE增强"""
    # 转换图像到HSV颜色空间
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 分离H, S, V通道
    h, s, v = cv2.split(hsv)
    
    # 创建CLAHE对象并应用于V通道
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    v_enhanced = clahe.apply(v)
    
    # 合并增强后的V通道与原始的H和S通道
    hsv_enhanced = cv2.merge([h, s, v_enhanced])
    
    # 转换回BGR颜色空间
    result = cv2.cvtColor(hsv_enhanced, cv2.COLOR_HSV2BGR)
    
    return result

def detect_video():
    """
    实时视频推理主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-path', type=str, default='models/yolo11n_detect_bayese_640x640_nv12.bin', 
                        help='BPU量化模型路径')
    parser.add_argument('--camera-id', type=int, default=0, help='摄像头ID')
    parser.add_argument('--port', type=int, default=8080, help='Web服务器端口')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='置信度阈值')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='IoU阈值')
    parser.add_argument('--classes-num', type=int, default=22, help='类别数')
    parser.add_argument('--class-offset', type=int, default=0, help='类别ID偏移量，用于修正模型输出的类别ID')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，输出更多日志信息')
    parser.add_argument('--use-english', action='store_true', help='使用英文类别名称，用于解决中文显示问题')
    # 添加CLAHE增强相关参数
    parser.add_argument('--clahe', action='store_true', help='启用HSV空间V通道的CLAHE增强')
    parser.add_argument('--clahe-clip', type=float, default=2.0, help='CLAHE算法的对比度限制参数')
    parser.add_argument('--clahe-grid', type=int, default=8, help='CLAHE算法的网格大小')
    opt = parser.parse_args()
    
    # 如果启用调试模式，设置日志级别为DEBUG
    if opt.debug:
        logger.setLevel(logging.DEBUG)
        logger.info("已启用调试模式")

    # 如果启用CLAHE增强，显示相关信息
    if opt.clahe:
        logger.info(f"已启用HSV空间V通道CLAHE增强 (clipLimit={opt.clahe_clip}, gridSize={opt.clahe_grid}x{opt.clahe_grid})")

    # 获取本机IP地址
    local_ip = get_local_ip()
    
    # 初始化模型
    logger.info(f"正在加载模型: {opt.model_path}")
    model = YOLO11_Detect(opt.model_path, opt.conf_thres, opt.iou_thres, opt.classes_num)

    # 初始化MQTT客户端
    init_mqtt_client()
    
    # 打开摄像头
    logger.info(f"正在打开摄像头 ID: {opt.camera_id}")
    cap = cv2.VideoCapture(opt.camera_id)
    
    if not cap.isOpened():
        logger.error(f"无法打开摄像头 ID: {opt.camera_id}")
        exit(1)
    
    # 设置摄像头分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    global output_frame, lock
    
    # 主循环
    while True:
        ret, frame = cap.read()
        if not ret:
            logger.error("无法读取摄像头帧")
            break
        
        # 垂直翻转图像，修正摄像头上下方向装反的问题
        frame = cv2.flip(frame, 0)  # 0表示绕x轴翻转（上下翻转）
        
        # 如果启用了CLAHE增强，应用CLAHE到HSV的V通道
        if opt.clahe:
            frame = apply_clahe_to_v_channel(frame, opt.clahe_clip, opt.clahe_grid)
        
        # 执行推理
        input_tensor = model.bgr2nv12(frame)
        outputs = model.c2numpy(model.forward(input_tensor))
        ids, scores, bboxes = model.postProcess(outputs, opt.class_offset)
        
        # 在图像上绘制检测结果
        for class_id, score, bbox in zip(ids, scores, bboxes):
            draw_detection(frame, bbox, score, class_id, opt.use_english)

        # 发送检测结果到MQTT（如果有检测到目标）
        if len(ids) > 0:
            detection_results = list(zip(ids, scores, bboxes))
            send_mqtt_detection(detection_results)

        # 更新输出帧
        with lock:
            output_frame = frame.copy()
    
    # 释放资源
    cap.release()

def generate():
    """
    生成视频流
    """
    global output_frame, lock
    
    while True:
        # 等待锁以保证线程安全
        with lock:
            if output_frame is None:
                continue
            
            # 编码为JPEG
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            
            if not flag:
                continue
        
        # 生成HTTP响应
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')

@app.route("/")
def index():
    """
    渲染主页
    """
    return render_template_string(HTML_PAGE)

@app.route("/video_feed")
def video_feed():
    """
    视频流端点
    """
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    # 启动视频检测线程
    video_thread = threading.Thread(target=detect_video)
    video_thread.daemon = True
    video_thread.start()
    
    # 启动Flask Web服务器
    ip = get_local_ip()
    port = 8080
    logger.info(f"启动Web服务器在 http://{ip}:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True, use_reloader=False)
