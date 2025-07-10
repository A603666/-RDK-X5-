// 鱼群'视'卫智能渔业水环境管理系统 - 前端JavaScript
// 处理数据获取、图表渲染、用户交互等功能

// 全局变量
let waterQualityChart = null;
let positionMap = null;
let dataUpdateInterval = null;
let systemData = {
    waterQuality: [],
    position: {},
    aiDetection: {},
    systemStatus: {}
};

// API基础URL
const API_BASE = window.location.origin;

// 初始化函数
document.addEventListener('DOMContentLoaded', function() {
    console.log('鱼群视卫管理系统前端初始化...');
    
    // 初始化时间显示
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // 初始化数据更新
    startDataUpdate();
    
    // 初始化图表
    initializeCharts();
    
    // 初始化地图
    initializeMap();
    
    console.log('前端初始化完成');
});

// 更新当前时间显示
function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        timeElement.textContent = timeString;
    }
}

// 开始数据更新
function startDataUpdate() {
    // 立即获取一次数据
    fetchLatestData();
    
    // 设置定时更新（每5秒）
    dataUpdateInterval = setInterval(fetchLatestData, 5000);
}

// 获取最新数据
async function fetchLatestData() {
    try {
        const response = await fetch(`${API_BASE}/api/data/latest`);
        const result = await response.json();
        
        if (result.status === 'success') {
            systemData = result.data;
            updateUI();
            updateSystemStatus();
        } else {
            console.error('获取数据失败:', result.message);
            updateSystemStatus(false);
        }
    } catch (error) {
        console.error('数据获取错误:', error);
        updateSystemStatus(false);
    }
}

// 更新UI界面
function updateUI() {
    updateWaterQualityCards();
    updatePositionCards();
    updateAIDetectionCards();
    updateSystemCards();
    updateDataTable();
    updateCharts();
}

// 更新水质状态卡片
function updateWaterQualityCards() {
    const waterQuality = systemData.waterQuality;
    const statusElement = document.getElementById('water-quality-status');
    const scoreElement = document.getElementById('water-quality-score');
    
    if (waterQuality && waterQuality.length > 0) {
        const latest = waterQuality[waterQuality.length - 1];
        statusElement.textContent = '正常监测';
        
        // 计算综合评分（简化算法）
        const score = calculateWaterQualityScore(latest);
        scoreElement.textContent = score.toFixed(1);
        
        // 根据评分设置颜色
        if (score >= 8) {
            scoreElement.className = 'text-2xl font-bold text-green-600';
        } else if (score >= 6) {
            scoreElement.className = 'text-2xl font-bold text-yellow-600';
        } else {
            scoreElement.className = 'text-2xl font-bold text-red-600';
        }
    } else {
        statusElement.textContent = '无数据';
        scoreElement.textContent = '--';
    }
}

// 更新定位状态卡片
function updatePositionCards() {
    const position = systemData.position;
    const statusElement = document.getElementById('position-status');
    const coordsElement = document.getElementById('position-coords');
    
    if (position && position.valid) {
        statusElement.textContent = '定位正常';
        coordsElement.textContent = `${position.latitude.toFixed(6)}, ${position.longitude.toFixed(6)}`;
    } else {
        statusElement.textContent = '定位失效';
        coordsElement.textContent = '--';
    }
}

// 更新AI检测卡片
function updateAIDetectionCards() {
    const aiDetection = systemData.aiDetection;
    const statusElement = document.getElementById('ai-detection-status');
    const countElement = document.getElementById('ai-detection-count');
    
    if (aiDetection && aiDetection.detection) {
        const detection = aiDetection.detection;
        statusElement.textContent = detection.disease_detected ? '检测到异常' : '正常监测';
        countElement.textContent = detection.detection_count || 0;
        
        // 根据检测结果设置颜色
        if (detection.disease_detected) {
            countElement.className = 'text-2xl font-bold text-red-600';
        } else {
            countElement.className = 'text-2xl font-bold text-green-600';
        }
    } else {
        statusElement.textContent = '无数据';
        countElement.textContent = '0';
    }
}

// 更新系统状态卡片
function updateSystemCards() {
    const systemStatus = systemData.systemStatus;
    const statusElement = document.getElementById('system-running-status');
    const uptimeElement = document.getElementById('system-uptime');
    
    if (systemStatus && systemStatus.running) {
        statusElement.textContent = '运行正常';
        
        // 计算运行时间
        if (systemStatus.timestamp) {
            const uptime = Date.now() / 1000 - systemStatus.timestamp;
            uptimeElement.textContent = formatUptime(uptime);
        }
    } else {
        statusElement.textContent = '状态未知';
        uptimeElement.textContent = '--';
    }
}

// 更新系统状态指示器
function updateSystemStatus(isOnline = true) {
    const mqttStatus = document.getElementById('mqtt-status');
    const systemStatusIndicator = document.getElementById('system-status');
    
    if (isOnline) {
        mqttStatus.className = 'status-indicator status-online';
        systemStatusIndicator.className = 'status-indicator status-online';
    } else {
        mqttStatus.className = 'status-indicator status-offline';
        systemStatusIndicator.className = 'status-indicator status-offline';
    }
}

// 更新数据表格
function updateDataTable() {
    const tableBody = document.getElementById('data-table-body');
    const waterQuality = systemData.waterQuality;
    
    if (!tableBody || !waterQuality || waterQuality.length === 0) {
        return;
    }
    
    // 清空现有行
    tableBody.innerHTML = '';
    
    // 显示最近10条数据
    const recentData = waterQuality.slice(-10).reverse();
    
    recentData.forEach(data => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50';
        
        const time = new Date(data.timestamp).toLocaleTimeString('zh-CN');
        
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${time}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${data.temperature.toFixed(1)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${data.ph.toFixed(2)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${data.oxygen.toFixed(2)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${data.tds.toFixed(0)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${data.turbidity.toFixed(1)}</td>
        `;
        
        tableBody.appendChild(row);
    });
}

// 初始化图表
function initializeCharts() {
    // 这里可以初始化图表库
    console.log('初始化图表...');
}

// 更新图表
function updateCharts() {
    updateWaterQualityChart();
}

// 更新水质数据图表
function updateWaterQualityChart() {
    const chartContainer = document.getElementById('water-quality-chart');
    const waterQuality = systemData.waterQuality;
    
    if (!chartContainer || !waterQuality || waterQuality.length === 0) {
        chartContainer.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500">暂无数据</div>';
        return;
    }
    
    // 简化的图表显示（实际项目中可以使用Chart.js或其他图表库）
    const latest = waterQuality[waterQuality.length - 1];
    chartContainer.innerHTML = `
        <div class="grid grid-cols-2 gap-4 h-full">
            <div class="bg-blue-50 p-4 rounded">
                <div class="text-sm text-gray-600">水温</div>
                <div class="text-2xl font-bold text-blue-600">${latest.temperature.toFixed(1)}°C</div>
            </div>
            <div class="bg-green-50 p-4 rounded">
                <div class="text-sm text-gray-600">pH值</div>
                <div class="text-2xl font-bold text-green-600">${latest.ph.toFixed(2)}</div>
            </div>
            <div class="bg-purple-50 p-4 rounded">
                <div class="text-sm text-gray-600">溶解氧</div>
                <div class="text-2xl font-bold text-purple-600">${latest.oxygen.toFixed(2)}mg/L</div>
            </div>
            <div class="bg-orange-50 p-4 rounded">
                <div class="text-sm text-gray-600">浊度</div>
                <div class="text-2xl font-bold text-orange-600">${latest.turbidity.toFixed(1)}NTU</div>
            </div>
        </div>
    `;
}

// 初始化地图
function initializeMap() {
    const mapContainer = document.getElementById('position-map');
    
    // 简化的地图显示
    mapContainer.innerHTML = `
        <div class="text-center">
            <i data-lucide="map" class="h-16 w-16 text-gray-400 mx-auto mb-2"></i>
            <div class="text-gray-500">地图功能</div>
            <div class="text-sm text-gray-400">显示设备位置和轨迹</div>
        </div>
    `;
    
    // 重新初始化图标
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

// 发送导航指令
async function sendNavigationCommand(command) {
    try {
        const response = await fetch(`${API_BASE}/api/command/navigation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ command: command })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification(`导航指令 ${command} 发送成功`, 'success');
        } else {
            showNotification(`导航指令发送失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('发送导航指令错误:', error);
        showNotification('导航指令发送失败', 'error');
    }
}

// 发送投药指令
async function sendMedicationCommand(command) {
    try {
        const response = await fetch(`${API_BASE}/api/command/medication`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ command: command })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification(`投药指令 ${command} 发送成功`, 'success');
        } else {
            showNotification(`投药指令发送失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('发送投药指令错误:', error);
        showNotification('投药指令发送失败', 'error');
    }
}

// 发送紧急指令
async function sendEmergencyCommand(command) {
    if (!confirm(`确定要执行紧急指令 ${command} 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/command/emergency`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ command: command })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification(`紧急指令 ${command} 发送成功`, 'warning');
        } else {
            showNotification(`紧急指令发送失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('发送紧急指令错误:', error);
        showNotification('紧急指令发送失败', 'error');
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    // 简化的通知显示
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${getNotificationClass(type)}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
}

// 获取通知样式类
function getNotificationClass(type) {
    switch (type) {
        case 'success':
            return 'bg-green-500 text-white';
        case 'error':
            return 'bg-red-500 text-white';
        case 'warning':
            return 'bg-yellow-500 text-white';
        default:
            return 'bg-blue-500 text-white';
    }
}

// 计算水质综合评分
function calculateWaterQualityScore(data) {
    // 简化的评分算法
    let score = 10;
    
    // 水温评分 (25-30°C为最佳)
    if (data.temperature < 20 || data.temperature > 35) {
        score -= 2;
    } else if (data.temperature < 25 || data.temperature > 30) {
        score -= 1;
    }
    
    // pH值评分 (6.5-8.5为最佳)
    if (data.ph < 6.0 || data.ph > 9.0) {
        score -= 3;
    } else if (data.ph < 6.5 || data.ph > 8.5) {
        score -= 1;
    }
    
    // 溶解氧评分 (>5mg/L为最佳)
    if (data.oxygen < 3) {
        score -= 3;
    } else if (data.oxygen < 5) {
        score -= 1;
    }
    
    // 浊度评分 (<10NTU为最佳)
    if (data.turbidity > 20) {
        score -= 2;
    } else if (data.turbidity > 10) {
        score -= 1;
    }
    
    return Math.max(0, score);
}

// 格式化运行时间
function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) {
        return `${days}天${hours}小时`;
    } else if (hours > 0) {
        return `${hours}小时${minutes}分钟`;
    } else {
        return `${minutes}分钟`;
    }
}

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    if (dataUpdateInterval) {
        clearInterval(dataUpdateInterval);
    }
});
