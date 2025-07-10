// 初始化变量
let currentConversationId = null;
let backendUrl = 'http://localhost:5001';
let isUsingStreamResponse = true;

// 水质数据更新相关变量
let waterQualityUpdateInterval = null;
let chartUpdateInterval = null;
let currentWaterData = null;

// 安全的DOM元素获取函数
function safeGetElement(id, required = false) {
  const element = document.getElementById(id);
  if (!element && required) {
    console.warn(`⚠️ 必需的DOM元素未找到: ${id}`);
  }
  return element;
}

function safeQuerySelector(selector, required = false) {
  const element = document.querySelector(selector);
  if (!element && required) {
    console.warn(`⚠️ 必需的DOM元素未找到: ${selector}`);
  }
  return element;
}

// 等待DOM加载完成
document.addEventListener('DOMContentLoaded', function() {
  // 监听AI助手相关元素 - 增加安全检查
  const aiTab = safeGetElement('tab-ai');
  const aiTabContent = safeGetElement('ai-tab');
  const aiInput = safeGetElement('ai-input');
  const sendMessageBtn = safeGetElement('send-message-btn');
  const chatMessages = safeGetElement('chat-messages');
  const aiThinking = safeGetElement('ai-thinking');
  const quickQuestions = document.querySelectorAll('.quick-question');
  const streamToggle = safeGetElement('stream-toggle');
  const backendStatus = safeGetElement('backend-status');
  const backendSettingsDialog = safeGetElement('backend-settings-dialog');
  const backendSettingsBtn = safeQuerySelector('.backend-settings');
  const closeDialogBtn = safeQuerySelector('.close-dialog');
  const testConnectionBtn = safeQuerySelector('.test-connection');
  const saveSettingsBtn = safeQuerySelector('.save-settings');
  const backendUrlInput = safeGetElement('backend-url');
  const clearChatBtn = safeGetElement('clear-chat');
  
  // 初始化图标
  if (window.lucide) {
    lucide.createIcons();
  }
  
  // 从localStorage加载后端URL
  if (localStorage.getItem('backendUrl')) {
    backendUrl = localStorage.getItem('backendUrl');
    backendUrlInput.value = backendUrl;
  }
  
  // 检查后端连接状态
  checkBackendStatus();

  // 初始化水质数据更新
  initWaterQualityUpdates();

  // 初始化图表选择器
  initChartSelectors();

  // 初始化地图
  initMapWithConfig();

  // 切换流式响应
  if (streamToggle) {
    streamToggle.addEventListener('change', function() {
      isUsingStreamResponse = this.checked;
    });
  }
  
  // 打开设置对话框
  if (backendSettingsBtn) {
    backendSettingsBtn.addEventListener('click', function() {
      backendSettingsDialog.classList.remove('hidden');
    });
  }
  
  // 关闭设置对话框
  if (closeDialogBtn) {
    closeDialogBtn.addEventListener('click', function() {
      backendSettingsDialog.classList.add('hidden');
    });
  }
  
  // 测试连接
  if (testConnectionBtn) {
    testConnectionBtn.addEventListener('click', function() {
      const url = backendUrlInput.value.trim();
      checkBackendConnection(url);
    });
  }
  
  // 保存设置
  if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener('click', function() {
      const url = backendUrlInput.value.trim();
      if (url) {
        backendUrl = url;
        localStorage.setItem('backendUrl', url);
        checkBackendConnection(url);
        backendSettingsDialog.classList.add('hidden');
        showMessage('后端设置已保存', 'success');
      } else {
        showMessage('请输入有效的后端URL', 'warning');
      }
    });
  }
  
  // 清除聊天记录
  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', function() {
      // 仅保留欢迎消息
      const welcomeMessages = chatMessages.querySelectorAll('div.flex.flex-col.space-y-2.mb-6');
      
      // 删除所有消息
      while (chatMessages.firstChild) {
        chatMessages.removeChild(chatMessages.firstChild);
      }
      
      // 重新添加欢迎消息
      if (welcomeMessages.length > 0) {
        chatMessages.appendChild(welcomeMessages[0]);
      }
      
      // 重置会话ID
      currentConversationId = null;
      
      showMessage('聊天记录已清除', 'info');
    });
  }
  
  // 点击AI助手标签
  if (aiTab) {
    aiTab.addEventListener('click', function() {
      // 检查后端连接状态
      checkBackendStatus();
    });
  }
  
  // 发送消息按钮点击事件
  if (sendMessageBtn) {
    sendMessageBtn.addEventListener('click', function() {
      sendMessage();
    });
  }
  
  // 输入框回车事件
  if (aiInput) {
    aiInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        sendMessage();
      }
    });
  }
  
  // 快速问题点击事件
  if (quickQuestions.length > 0) {
    quickQuestions.forEach(btn => {
      btn.addEventListener('click', function() {
        const question = this.textContent.trim();
        aiInput.value = question;
        sendMessage();
      });
    });
  }
  
  // 发送消息函数
  function sendMessage() {
    const message = aiInput.value.trim();
    if (!message) return;
    
    // 显示用户消息
    displayUserMessage(message);
    
    // 清空输入框
    aiInput.value = '';
    
    // 显示AI思考状态
    aiThinking.classList.remove('hidden');
    
    // 滚动到底部
    scrollToBottom();
    
    // 发送消息到后端
    if (isUsingStreamResponse) {
      sendMessageStream(message);
    } else {
      sendMessageNonStream(message);
    }
  }
  
  // 使用流式响应发送消息
  function sendMessageStream(message) {
    const apiUrl = `${backendUrl}/api/chat`;
    
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: message,
        conversation_id: currentConversationId,
        stream: true
      })
    }).then(response => {
      if (!response.ok) {
        throw new Error('网络错误');
      }
      
      // 创建新的AI消息容器
      const aiMessageContainer = document.createElement('div');
      aiMessageContainer.className = 'flex items-start mb-4';
      
      const aiAvatar = document.createElement('div');
      aiAvatar.className = 'w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 flex items-center justify-center text-white shadow-md mr-2 flex-shrink-0';
      aiAvatar.innerHTML = '<i data-lucide="bot" class="w-5 h-5"></i>';
      
      const aiMessageBubble = document.createElement('div');
      aiMessageBubble.className = 'bg-white rounded-lg rounded-tl-none p-3 shadow-sm max-w-[85%] border border-gray-100';
      
      const aiMessageText = document.createElement('p');
      aiMessageText.className = 'text-gray-700 whitespace-pre-wrap';  // 添加whitespace-pre-wrap保持格式
      aiMessageText.textContent = '';
      
      aiMessageBubble.appendChild(aiMessageText);
      aiMessageContainer.appendChild(aiAvatar);
      aiMessageContainer.appendChild(aiMessageBubble);
      
      // 隐藏思考状态
      aiThinking.classList.add('hidden');
      
      // 添加到聊天区域
      chatMessages.appendChild(aiMessageContainer);
      
      // 初始化图标
      if (window.lucide) {
        lucide.createIcons({
          icons: {
            'bot': aiAvatar.querySelector('[data-lucide="bot"]')
          }
        });
      }
      
      // 滚动到底部
      scrollToBottom();
      
      // 处理SSE响应
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      function processStream({ done, value }) {
        if (done) {
          return;
        }
        
        buffer += decoder.decode(value, { stream: true });
        
        // 处理缓冲区中的所有完整行
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // 保留最后一个不完整的行
        
        lines.forEach(line => {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              
              // 处理事件
              if (data.event === 'conversation.chat.created' || data.event === 'conversation.chat.in_progress') {
                // 保存会话ID
                if (data.data && data.data.conversation_id) {
                  currentConversationId = data.data.conversation_id;
                }
              } else if (data.event === 'conversation.message.delta') {
                // 处理消息增量
                if (data.data && data.data.content && data.data.role === 'assistant') {
                  aiMessageText.textContent += data.data.content;
                  scrollToBottom();
                }
              } else if (data.event === 'conversation.message.completed') {
                // 消息完成
                if (data.data && data.data.content && data.data.role === 'assistant' && data.data.type === 'answer') {
                  // 完整消息已经通过增量更新，这里不需要再处理
                  // 消息完成后格式化内容，保持引用和列表格式
                  formatMessageContent(aiMessageText);
                }
              }
            } catch (e) {
              console.error('解析SSE数据错误:', e);
            }
          }
        });
        
        // 继续读取流
        return reader.read().then(processStream);
      }
      
      // 开始处理流
      reader.read().then(processStream);
      
    }).catch(error => {
      console.error('发送消息错误:', error);
      aiThinking.classList.add('hidden');
      showMessage('发送消息失败: ' + error.message, 'warning');
    });
  }
  
  // 格式化消息内容，处理markdown风格的文本
  function formatMessageContent(messageElement) {
    // 这里可以添加额外的格式化逻辑，例如处理Markdown风格的列表等
    // 已经通过CSS的whitespace-pre-wrap保持了基本格式
  }
  
  // 使用非流式响应发送消息
  function sendMessageNonStream(message) {
    const apiUrl = `${backendUrl}/api/chat`;
    
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: message,
        conversation_id: currentConversationId,
        stream: false
      })
    }).then(response => {
      if (!response.ok) {
        throw new Error('网络错误');
      }
      return response.json();
    }).then(data => {
      // 保存会话ID
      if (data.conversation_id) {
        currentConversationId = data.conversation_id;
      }
      
      // 获取消息内容
      let aiResponse = '很抱歉，无法获取回复';
      
      if (data.messages && data.messages.length > 0) {
        const assistantMessage = data.messages.find(msg => msg.role === 'assistant' && msg.type === 'answer');
        if (assistantMessage) {
          aiResponse = assistantMessage.content;
        }
      }
      
      // 隐藏思考状态
      aiThinking.classList.add('hidden');
      
      // 显示AI回复
      displayAIMessage(aiResponse);
      
    }).catch(error => {
      console.error('发送消息错误:', error);
      aiThinking.classList.add('hidden');
      showMessage('发送消息失败: ' + error.message, 'warning');
    });
  }
  
  // 显示用户消息
  function displayUserMessage(message) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'flex items-start justify-end mb-4';
    
    const messageBubble = document.createElement('div');
    messageBubble.className = 'bg-blue-50 rounded-lg rounded-tr-none p-3 shadow-sm max-w-[85%] border border-blue-100';
    
    const messageText = document.createElement('p');
    messageText.className = 'text-gray-800';
    messageText.textContent = message;
    
    const userAvatar = document.createElement('div');
    userAvatar.className = 'w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 shadow-sm ml-2 flex-shrink-0';
    userAvatar.innerHTML = '<i data-lucide="user" class="w-5 h-5"></i>';
    
    messageBubble.appendChild(messageText);
    messageContainer.appendChild(messageBubble);
    messageContainer.appendChild(userAvatar);
    
    chatMessages.appendChild(messageContainer);
    
    // 初始化图标
    if (window.lucide) {
      lucide.createIcons({
        icons: {
          'user': userAvatar.querySelector('[data-lucide="user"]')
        }
      });
    }
  }
  
  // 显示AI消息
  function displayAIMessage(message) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'flex items-start mb-4';
    
    const aiAvatar = document.createElement('div');
    aiAvatar.className = 'w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 flex items-center justify-center text-white shadow-md mr-2 flex-shrink-0';
    aiAvatar.innerHTML = '<i data-lucide="bot" class="w-5 h-5"></i>';
    
    const messageBubble = document.createElement('div');
    messageBubble.className = 'bg-white rounded-lg rounded-tl-none p-3 shadow-sm max-w-[85%] border border-gray-100';
    
    const messageText = document.createElement('p');
    messageText.className = 'text-gray-700 whitespace-pre-wrap';  // 添加whitespace-pre-wrap保持格式
    messageText.textContent = message;
    
    messageBubble.appendChild(messageText);
    messageContainer.appendChild(aiAvatar);
    messageContainer.appendChild(messageBubble);
    
    chatMessages.appendChild(messageContainer);
    
    // 初始化图标
    if (window.lucide) {
      lucide.createIcons({
        icons: {
          'bot': aiAvatar.querySelector('[data-lucide="bot"]')
        }
      });
    }
    
    // 滚动到底部
    scrollToBottom();
  }
  
  // 滚动到聊天区域底部
  function scrollToBottom() {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }
  
  // 检查后端连接状态
  function checkBackendStatus() {
    if (backendStatus) {
      backendStatus.innerHTML = '<i data-lucide="loader" class="w-3.5 h-3.5 mr-1 text-gray-400 animate-spin"></i><span>检查中...</span>';
      
      // 初始化图标
      if (window.lucide) {
        lucide.createIcons({
          icons: {
            'loader': backendStatus.querySelector('[data-lucide="loader"]')
          }
        });
      }
      
      checkBackendConnection(backendUrl);
    }
  }
  
  // 检查后端连接
  function checkBackendConnection(url) {
    fetch(`${url}/api/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    }).then(response => {
      if (!response.ok) {
        throw new Error('服务器响应错误');
      }
      return response.json();
    }).then(data => {
      if (data.status === 'ok') {
        updateBackendStatus(true);
      } else {
        updateBackendStatus(false);
      }
    }).catch(error => {
      console.error('后端连接错误:', error);
      updateBackendStatus(false);
    });
  }
  
  // 更新后端状态显示
  function updateBackendStatus(isConnected) {
    if (backendStatus) {
      if (isConnected) {
        backendStatus.innerHTML = '<i data-lucide="server" class="w-3.5 h-3.5 mr-1 text-green-500"></i><span class="text-green-500">已连接</span>';
      } else {
        backendStatus.innerHTML = '<i data-lucide="server-off" class="w-3.5 h-3.5 mr-1 text-red-500"></i><span class="text-red-500">未连接</span>';
      }
      
      // 初始化图标
      if (window.lucide) {
        lucide.createIcons({
          icons: {
            'server': backendStatus.querySelector('[data-lucide="server"]'),
            'server-off': backendStatus.querySelector('[data-lucide="server-off"]')
          }
        });
      }
    }
  }
  
  // 初始化鱼池点击事件 - 新添加的功能
  initPoolSelectors();
});

// 标签页切换
document.addEventListener('DOMContentLoaded', function() {
  // 初始化标签页
  const tabBtns = document.querySelectorAll('[id^="tab-"]');
  const tabContents = document.querySelectorAll('[id$="-tab"]');
  
  tabBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const tabName = this.id.replace('tab-', '');
      
      // 移除所有标签页的active样式
      tabBtns.forEach(tab => {
        tab.classList.remove('border-b-2', 'border-blue-600', 'text-blue-600');
        tab.classList.add('text-gray-500');
      });
      
      // 添加当前标签页的active样式
      this.classList.add('border-b-2', 'border-blue-600', 'text-blue-600');
      this.classList.remove('text-gray-500');
      
      // 隐藏所有内容
      tabContents.forEach(content => {
        content.classList.add('hidden');
      });
      
      // 显示当前内容
      document.getElementById(tabName + '-tab').classList.remove('hidden');
    });
  });
  
  // 初始化鱼池选择器和机体选择器
  initPoolSelectors();
});

// 鱼池和机体选择器初始化 - 新增的函数
function initPoolSelectors() {
  // 监控页面 - 鱼池选择器
  const monitoringPoolSelectors = document.querySelectorAll('#monitoring-tab .pool-selector');
  monitoringPoolSelectors.forEach(pool => {
    pool.addEventListener('click', function() {
      // 移除所有鱼池的active样式
      monitoringPoolSelectors.forEach(p => {
        p.classList.remove('ring-2', 'ring-blue-500', 'active');
      });
      
      // 添加当前鱼池的active样式
      this.classList.add('ring-2', 'ring-blue-500', 'active');
      
      // 更新鱼池信息
      updatePoolInfo(this.getAttribute('data-pool-id'));
    });
  });
  
  // 控制页面 - 机体选择器
  const controlPoolSelectors = document.querySelectorAll('#control-tab .pool-selector');
  controlPoolSelectors.forEach(device => {
    device.addEventListener('click', function() {
      // 移除所有机体的active样式
      controlPoolSelectors.forEach(d => {
        d.classList.remove('ring-2', 'ring-blue-500', 'active');
      });
      
      // 添加当前机体的active样式
      this.classList.add('ring-2', 'ring-blue-500', 'active');
      
      // 更新机体信息
      updateDeviceInfo(this.getAttribute('data-device-id'));
    });
  });
}

// 更新鱼池信息函数 - 新增的函数
function updatePoolInfo(poolId) {
  if (!poolId) return;
  
  // 更新鱼池编号显示
  const poolIdDisplay = document.getElementById('pool-id-display');
  if (poolIdDisplay) {
    poolIdDisplay.textContent = `鱼池编号: ${poolId}`;
  }
  
  // 更新鱼池监控显示
  const monitorDisplay = document.getElementById('monitor-display');
  if (monitorDisplay) {
    monitorDisplay.querySelector('span').textContent = `监控画面 - 鱼池 ${poolId}`;
  }
  
  // 更新水质状态显示
  const waterQualityBadge = document.getElementById('water-quality-badge');
  if (waterQualityBadge) {
    // 根据不同鱼池设置不同的水质状态
    switch(poolId) {
      case 'A-001':
        waterQualityBadge.className = 'px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800';
        waterQualityBadge.textContent = '良好';
        break;
      case 'A-002':
        waterQualityBadge.className = 'px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800';
        waterQualityBadge.textContent = '一般';
        break;
      case 'A-003':
        waterQualityBadge.className = 'px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800 animate-pulse';
        waterQualityBadge.textContent = '异常';
        break;
      case 'A-004':
        waterQualityBadge.className = 'px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800';
        waterQualityBadge.textContent = '良好';
        break;
    }
  }
  
  // 更新水质参数
  updateWaterParameters(poolId);
}

// 更新机体信息函数 - 新增的函数
function updateDeviceInfo(deviceId) {
  if (!deviceId) return;
  
  // 更新设备编号显示
  const deviceIdDisplay = document.getElementById('device-id-display');
  if (deviceIdDisplay) {
    deviceIdDisplay.textContent = `设备编号: ${deviceId}`;
  }
  
  // 更新设备状态显示
  const deviceStatusBadge = document.getElementById('device-status-badge');
  if (deviceStatusBadge) {
    // 根据不同设备设置不同的状态
    if (deviceId === '1号机') {
      deviceStatusBadge.className = 'px-3 py-1 rounded-full text-sm font-medium text-green-500 bg-green-50';
      deviceStatusBadge.innerHTML = '<span class="inline-block w-2 h-2 rounded-full bg-green-500 mr-1"></span>运行中';
    } else {
      deviceStatusBadge.className = 'px-3 py-1 rounded-full text-sm font-medium text-gray-500 bg-gray-50';
      deviceStatusBadge.innerHTML = '<span class="inline-block w-2 h-2 rounded-full bg-gray-500 mr-1"></span>离线';
    }
  }
  
  // 更新设备参数
  updateDeviceParameters(deviceId);
}

// 更新水质参数 - 修改为使用实时数据
function updateWaterParameters(poolId) {
  // 使用实时数据而不是硬编码数据
  if (currentWaterData) {
    updateWaterQualityDisplay(currentWaterData);
  } else {
    // 如果没有当前数据，获取最新数据
    fetchCurrentWaterQuality();
  }

  // 更新水质图表
  fetchWaterQualityHistory();
}

// 更新设备参数 - 新增的函数
function updateDeviceParameters(deviceId) {
  // 获取参数显示元素
  const deviceIp = document.getElementById('device-ip');
  const deviceBattery = document.getElementById('device-battery');
  const deviceBatteryBar = document.getElementById('device-battery-bar');
  const cruiseSpeed = document.getElementById('cruise-speed');
  
  // 根据不同的设备设置不同的参数
  switch(deviceId) {
    case '1号机':
      if (deviceIp) deviceIp.textContent = '192.168.1.101';
      if (deviceBattery) deviceBattery.textContent = '85%';
      if (deviceBatteryBar) deviceBatteryBar.style.width = '85%';
      if (cruiseSpeed) cruiseSpeed.textContent = '中速';
      // 更新速度选择按钮状态
      updateSpeedButtons('medium');
      break;
    case '2号机':
      if (deviceIp) deviceIp.textContent = '192.168.1.102';
      if (deviceBattery) deviceBattery.textContent = '72%';
      if (deviceBatteryBar) deviceBatteryBar.style.width = '72%';
      if (cruiseSpeed) cruiseSpeed.textContent = '低速';
      // 更新速度选择按钮状态
      updateSpeedButtons('low');
      break;
    case '3号机':
      if (deviceIp) deviceIp.textContent = '192.168.1.103';
      if (deviceBattery) deviceBattery.textContent = '63%';
      if (deviceBatteryBar) deviceBatteryBar.style.width = '63%';
      if (cruiseSpeed) cruiseSpeed.textContent = '高速';
      // 更新速度选择按钮状态
      updateSpeedButtons('high');
      break;
    case '4号机':
      if (deviceIp) deviceIp.textContent = '192.168.1.104';
      if (deviceBattery) deviceBattery.textContent = '91%';
      if (deviceBatteryBar) deviceBatteryBar.style.width = '91%';
      if (cruiseSpeed) cruiseSpeed.textContent = '中速';
      // 更新速度选择按钮状态
      updateSpeedButtons('medium');
      break;
  }
}

// 更新速度按钮状态 - 新增的函数
function updateSpeedButtons(speed) {
  const speedOptions = document.querySelectorAll('.speed-option');
  
  speedOptions.forEach(option => {
    // 移除所有选项的激活样式
    option.classList.remove('bg-amber-100', 'text-amber-800', 'border', 'border-amber-200');
    option.classList.add('bg-gray-100', 'hover:bg-amber-100');
    
    // 激活当前速度对应的按钮
    if (option.getAttribute('data-speed') === speed) {
      option.classList.remove('bg-gray-100', 'hover:bg-amber-100');
      option.classList.add('bg-amber-100', 'text-amber-800', 'border', 'border-amber-200');
    }
  });
}

// 更新水质图表 - 新增的函数
function updateWaterChart(poolId) {
  if (!window.Recharts) return;
  
  // 不同鱼池的水质数据
  const poolData = {
    'A-001': [
      {time: '00:00', value: 6.5},
      {time: '02:00', value: 6.7},
      {time: '04:00', value: 6.8},
      {time: '06:00', value: 6.6},
      {time: '08:00', value: 6.4},
      {time: '10:00', value: 6.7},
      {time: '12:00', value: 6.9},
      {time: '14:00', value: 7.0},
      {time: '16:00', value: 6.8},
      {time: '18:00', value: 6.7},
      {time: '20:00', value: 6.6},
      {time: '22:00', value: 6.5}
    ],
    'A-002': [
      {time: '00:00', value: 5.8},
      {time: '02:00', value: 5.7},
      {time: '04:00', value: 5.5},
      {time: '06:00', value: 5.3},
      {time: '08:00', value: 5.2},
      {time: '10:00', value: 5.0},
      {time: '12:00', value: 5.2},
      {time: '14:00', value: 5.3},
      {time: '16:00', value: 5.4},
      {time: '18:00', value: 5.4},
      {time: '20:00', value: 5.3},
      {time: '22:00', value: 5.2}
    ],
    'A-003': [
      {time: '00:00', value: 4.5},
      {time: '02:00', value: 4.3},
      {time: '04:00', value: 4.0},
      {time: '06:00', value: 3.8},
      {time: '08:00', value: 3.7},
      {time: '10:00', value: 3.5},
      {time: '12:00', value: 3.4},
      {time: '14:00', value: 3.3},
      {time: '16:00', value: 3.4},
      {time: '18:00', value: 3.5},
      {time: '20:00', value: 3.6},
      {time: '22:00', value: 3.5}
    ],
    'A-004': [
      {time: '00:00', value: 7.2},
      {time: '02:00', value: 7.3},
      {time: '04:00', value: 7.4},
      {time: '06:00', value: 7.3},
      {time: '08:00', value: 7.2},
      {time: '10:00', value: 7.1},
      {time: '12:00', value: 7.2},
      {time: '14:00', value: 7.3},
      {time: '16:00', value: 7.4},
      {time: '18:00', value: 7.3},
      {time: '20:00', value: 7.2},
      {time: '22:00', value: 7.2}
    ]
  };
  
  // 获取或创建图表容器
  const chartContainer = document.getElementById('water-chart');
  if (!chartContainer) return;
  
  // 清空图表容器
  while (chartContainer.firstChild) {
    chartContainer.removeChild(chartContainer.firstChild);
  }
  
  // 使用当前鱼池的数据
  const data = poolData[poolId] || poolData['A-001'];
  
  // 创建Recharts图表
  const { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } = Recharts;
  
  // 创建图表组件
  const chart = React.createElement(
    LineChart,
    { width: chartContainer.clientWidth, height: 200, data: data, margin: { top: 10, right: 30, left: 0, bottom: 0 } },
    [
      React.createElement(CartesianGrid, { strokeDasharray: '3 3', key: 'grid' }),
      React.createElement(XAxis, { dataKey: 'time', key: 'x-axis' }),
      React.createElement(YAxis, { key: 'y-axis' }),
      React.createElement(Tooltip, { key: 'tooltip' }),
      React.createElement(Line, { 
        type: 'monotone', 
        dataKey: 'value', 
        stroke: '#3b82f6', 
        activeDot: { r: 8 }, 
        key: 'line',
        name: '溶解氧 (mg/L)'
      })
    ]
  );
  
  // 渲染图表
  ReactDOM.render(chart, chartContainer);
}

// 通用消息提示函数
function showMessage(message, type = 'info') {
  // 创建消息元素
  const messageElement = document.createElement('div');
  messageElement.className = `fixed top-4 right-4 px-4 py-2 rounded-lg shadow-lg z-50 flex items-center transition-all duration-300 transform translate-x-full`;
  
  // 根据类型设置样式
  if (type === 'success') {
       messageElement.classList.add('bg-green-50', 'text-green-800', 'border-l-4', 'border-green-500');
  } else if (type === 'warning') {
    messageElement.classList.add('bg-yellow-50', 'text-yellow-800', 'border-l-4', 'border-yellow-500');
  } else if (type === 'error') {
    messageElement.classList.add('bg-red-50', 'text-red-800', 'border-l-4', 'border-red-500');
  } else {
    messageElement.classList.add('bg-blue-50', 'text-blue-800', 'border-l-4', 'border-blue-500');
  }
  
  // 设置消息图标
  let icon = '';
  if (type === 'success') {
    icon = '<i data-lucide="check-circle" class="w-5 h-5 mr-2"></i>';
  } else if (type === 'warning') {
    icon = '<i data-lucide="alert-triangle" class="w-5 h-5 mr-2"></i>';
  } else if (type === 'error') {
    icon = '<i data-lucide="x-circle" class="w-5 h-5 mr-2"></i>';
  } else {
    icon = '<i data-lucide="info" class="w-5 h-5 mr-2"></i>';
  }
  
  // 设置消息内容
  messageElement.innerHTML = `${icon}<span>${message}</span>`;
  
  // 添加到页面
  document.body.appendChild(messageElement);
  
  // 初始化图标
  if (window.lucide) {
    lucide.createIcons({
      icons: {
        'check-circle': messageElement.querySelector('[data-lucide="check-circle"]'),
        'alert-triangle': messageElement.querySelector('[data-lucide="alert-triangle"]'),
        'x-circle': messageElement.querySelector('[data-lucide="x-circle"]'),
        'info': messageElement.querySelector('[data-lucide="info"]')
      }
    });
  }
  
  // 显示消息
  setTimeout(() => {
    messageElement.classList.remove('translate-x-full');
  }, 10);
  
  // 自动关闭
  setTimeout(() => {
    messageElement.classList.add('translate-x-full');
    
    // 移除元素
    setTimeout(() => {
      if (messageElement.parentNode) {
        messageElement.parentNode.removeChild(messageElement);
      }
    }, 300);
  }, 3000);
}

// 连接控制事件监听器
document.addEventListener('DOMContentLoaded', function() {
  // 速度控制按钮
  const speedOptions = document.querySelectorAll('.speed-option');
  if (speedOptions.length > 0) {
    speedOptions.forEach(option => {
      option.addEventListener('click', function() {
        const speed = this.getAttribute('data-speed');
        
        // 更新速度按钮状态
        updateSpeedButtons(speed);
        
        // 显示操作消息
        const speedText = speed === 'low' ? '低速' : (speed === 'medium' ? '中速' : '高速');
        showMessage(`已设置速度为: ${speedText}`, 'success');
      });
    });
  }
  
  // 方向控制按钮
  const directionButtons = document.querySelectorAll('.direction-btn');
  if (directionButtons.length > 0) {
    directionButtons.forEach(btn => {
      btn.addEventListener('click', function() {
        const direction = this.getAttribute('data-direction');
        const deviceId = document.querySelector('#device-id-display')?.textContent.replace('设备编号: ', '') || '';
        
        if (!deviceId) {
          showMessage('请先选择一个设备', 'warning');
          return;
        }
        
        // 显示操作消息
        let directionText = '';
        switch(direction) {
          case 'forward': directionText = '前进'; break;
          case 'backward': directionText = '后退'; break;
          case 'left': directionText = '左转'; break;
          case 'right': directionText = '右转'; break;
          case 'stop': directionText = '停止'; break;
        }
        
        showMessage(`向${deviceId}发送指令: ${directionText}`, 'info');
      });
    });
  }
  
  // 功能按钮
  const functionButtons = document.querySelectorAll('.function-btn');
  if (functionButtons.length > 0) {
    functionButtons.forEach(btn => {
      btn.addEventListener('click', function() {
        const action = this.getAttribute('data-action');
        const deviceId = document.querySelector('#device-id-display')?.textContent.replace('设备编号: ', '') || '';
        
        if (!deviceId) {
          showMessage('请先选择一个设备', 'warning');
          return;
        }
        
        // 显示操作消息
        let actionText = '';
        switch(action) {
          case 'measure': actionText = '开始水质测量'; break;
          case 'return': actionText = '返回充电站'; break;
          case 'patrol': actionText = '开始巡航'; break;
          case 'feed': actionText = '开始喂食'; break;
        }
        
        showMessage(`向${deviceId}发送指令: ${actionText}`, 'success');
      });
    });
  }
  
  // 紧急停止按钮
  const emergencyStop = document.getElementById('emergency-stop');
  if (emergencyStop) {
    emergencyStop.addEventListener('click', function() {
      const deviceId = document.querySelector('#device-id-display')?.textContent.replace('设备编号: ', '') || '';
      
      if (!deviceId) {
        showMessage('请先选择一个设备', 'warning');
        return;
      }
      
      // 添加动画效果
      this.classList.add('animate-pulse');
      setTimeout(() => {
        this.classList.remove('animate-pulse');
      }, 2000);
      
      showMessage(`紧急停止指令已发送至${deviceId}!`, 'error');
    });
  }
  
  // 水池清理按钮
  const cleanPoolBtn = document.getElementById('clean-pool-btn');
  if (cleanPoolBtn) {
    cleanPoolBtn.addEventListener('click', function() {
      const deviceId = document.querySelector('#device-id-display')?.textContent.replace('设备编号: ', '') || '';
      
      if (!deviceId) {
        showMessage('请先选择一个设备', 'warning');
        return;
      }
      
      // 创建确认对话框
      const confirmDialog = document.createElement('div');
      confirmDialog.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
      confirmDialog.innerHTML = `
        <div class="bg-white rounded-lg shadow-xl p-6 max-w-sm mx-auto">
          <h3 class="text-lg font-medium text-gray-900 mb-4">确认操作</h3>
          <p class="text-gray-700 mb-6">确定要启动${deviceId}的水池清理模式吗?</p>
          <div class="flex justify-end space-x-3">
            <button id="cancel-clean" class="px-4 py-2 rounded bg-gray-200 text-gray-800 hover:bg-gray-300">取消</button>
            <button id="confirm-clean" class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">确定</button>
          </div>
        </div>
      `;
      
      document.body.appendChild(confirmDialog);
      
      // 取消按钮
      document.getElementById('cancel-clean').addEventListener('click', function() {
        document.body.removeChild(confirmDialog);
      });
      
      // 确认按钮
      document.getElementById('confirm-clean').addEventListener('click', function() {
        document.body.removeChild(confirmDialog);
        showMessage(`向${deviceId}发送指令: 开始水池清理`, 'success');
      });
    });
  }
  
  // 水质优化按钮
  const optimizeWaterBtn = document.getElementById('optimize-water-btn');
  if (optimizeWaterBtn) {
    optimizeWaterBtn.addEventListener('click', function() {
      const deviceId = document.querySelector('#device-id-display')?.textContent.replace('设备编号: ', '') || '';

      if (!deviceId) {
        showMessage('请先选择一个设备', 'warning');
        return;
      }

      // 显示提示信息
      optimizeWaterBtn.textContent = '优化中...';
      optimizeWaterBtn.disabled = true;

      // 模拟处理过程
      setTimeout(() => {
        optimizeWaterBtn.textContent = '水质优化';
        optimizeWaterBtn.disabled = false;
        showMessage(`水质优化指令已发送至${deviceId}，正在处理中`, 'success');
      }, 2000);
    });
  }

  // 预测水质按钮
  const predictWaterQualityBtn = document.getElementById('predict-water-quality-btn');
  if (predictWaterQualityBtn) {
    predictWaterQualityBtn.addEventListener('click', function() {
      // 添加loading状态
      this.classList.add('loading');
      const originalText = this.querySelector('span').textContent;
      this.querySelector('span').textContent = '预测中...';
      this.disabled = true;

      // 调用真实的预测API
      fetch(`${backendUrl}/api/water-quality/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      .then(response => response.json())
      .then(data => {
        // 移除loading状态
        this.classList.remove('loading');
        this.querySelector('span').textContent = originalText;
        this.disabled = false;

        if (data.status === 'success') {
          // 显示预测结果
          showPredictionResult(data.data);
          showMessage('水质预测完成！', 'success');
        } else {
          showMessage('预测失败：' + data.message, 'warning');
        }
      })
      .catch(error => {
        // 移除loading状态
        this.classList.remove('loading');
        this.querySelector('span').textContent = originalText;
        this.disabled = false;

        console.log('预测API调用失败:', error);
        showMessage('预测失败，请检查网络连接', 'warning');
      });
    });
  }
});

// 生成风险评估
function generateRiskAssessment(predictions) {
  const risks = [];
  let riskLevel = 'low';

  // 检查各项参数风险
  const tempRange = [Math.min(...predictions.temperature), Math.max(...predictions.temperature)];
  const oxygenRange = [Math.min(...predictions.oxygen), Math.max(...predictions.oxygen)];
  const phRange = [Math.min(...predictions.ph), Math.max(...predictions.ph)];
  const tdsRange = [Math.min(...predictions.tds), Math.max(...predictions.tds)];
  const turbidityRange = [Math.min(...predictions.turbidity), Math.max(...predictions.turbidity)];

  // 水温风险评估
  if (tempRange[1] > 32 || tempRange[0] < 22) {
    risks.push('水温可能超出适宜范围，注意调节');
    riskLevel = 'medium';
  }

  // 溶解氧风险评估
  if (oxygenRange[0] < 5.0) {
    risks.push('溶解氧可能偏低，建议增加增氧设备运行时间');
    riskLevel = 'high';
  }

  // pH值风险评估
  if (phRange[0] < 6.5 || phRange[1] > 8.5) {
    risks.push('pH值可能异常，建议检查水质调节剂');
    riskLevel = riskLevel === 'high' ? 'high' : 'medium';
  }

  // TDS风险评估
  if (tdsRange[1] > 500) {
    risks.push('TDS值可能过高，考虑部分换水');
    riskLevel = riskLevel === 'high' ? 'high' : 'medium';
  }

  // 浊度风险评估
  if (turbidityRange[1] > 5) {
    risks.push('浊度可能过高，建议投放絮凝剂');
    riskLevel = riskLevel === 'high' ? 'high' : 'medium';
  }

  // 如果没有风险，给出正面建议
  if (risks.length === 0) {
    risks.push('水质预测状况良好，继续保持当前管理措施');
    risks.push('建议定期监测，预防性维护设备');
  }

  const riskColors = {
    'low': 'green',
    'medium': 'yellow',
    'high': 'red'
  };

  const riskLabels = {
    'low': '低风险',
    'medium': '中等风险',
    'high': '高风险'
  };

  return {
    level: riskLabels[riskLevel],
    color: riskColors[riskLevel],
    recommendations: risks
  };
}

// 显示预测结果弹窗
function showPredictionResult(predictionData) {
  if (!predictionData) {
    showMessage('没有预测数据', 'warning');
    return;
  }

  const predictions = predictionData.predictions;
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';

  // 计算预测范围
  const getRange = (values) => {
    const min = Math.min(...values);
    const max = Math.max(...values);
    return `${min.toFixed(1)}-${max.toFixed(1)}`;
  };

  // 生成风险评估和建议
  const riskAssessment = generateRiskAssessment(predictions);

  modal.innerHTML = `
    <div class="bg-white rounded-lg shadow-xl p-6 max-w-lg mx-auto m-4">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-medium text-gray-900">水质预测结果</h3>
        <button class="close-prediction text-gray-400 hover:text-gray-600">
          <i data-lucide="x" class="w-5 h-5"></i>
        </button>
      </div>
      <div class="space-y-4">
        <div class="bg-blue-50 p-4 rounded-lg">
          <h4 class="font-medium text-blue-900 mb-2">未来24小时预测范围</h4>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-600">水温:</span>
              <span class="text-blue-700 font-medium">${getRange(predictions.temperature)} °C</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">溶解氧含量:</span>
              <span class="text-blue-700 font-medium">${getRange(predictions.oxygen)} mg/L</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">pH值:</span>
              <span class="text-blue-700 font-medium">${getRange(predictions.ph)}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">TDS值:</span>
              <span class="text-blue-700 font-medium">${getRange(predictions.tds)} ppm</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">浊度:</span>
              <span class="text-blue-700 font-medium">${getRange(predictions.turbidity)} NTU</span>
            </div>
          </div>
        </div>
        <div class="bg-${riskAssessment.color}-50 p-4 rounded-lg">
          <h4 class="font-medium text-${riskAssessment.color}-900 mb-2">风险评估</h4>
          <div class="flex items-center mb-2">
            <span class="px-2 py-1 rounded text-xs font-medium bg-${riskAssessment.color}-100 text-${riskAssessment.color}-800">
              ${riskAssessment.level}
            </span>
          </div>
          <ul class="text-sm text-${riskAssessment.color}-700 space-y-1">
            ${riskAssessment.recommendations.map(rec => `<li>• ${rec}</li>`).join('')}
          </ul>
        </div>
      </div>
      <div class="mt-6 flex justify-end">
        <button class="close-prediction px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          确定
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // 重新初始化图标
  if (window.lucide) {
    lucide.createIcons();
  }

  // 关闭弹窗事件
  modal.querySelectorAll('.close-prediction').forEach(btn => {
    btn.addEventListener('click', () => {
      document.body.removeChild(modal);
    });
  });

  // 点击背景关闭
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      document.body.removeChild(modal);
    }
  });
}

// ==================== 水质数据实时更新功能 ====================

// 初始化水质数据更新
function initWaterQualityUpdates() {
  // 立即获取一次数据
  fetchCurrentWaterQuality();
  fetchWaterQualityHistory();

  // 设置定时更新 - 每30秒更新一次当前数据
  waterQualityUpdateInterval = setInterval(() => {
    fetchCurrentWaterQuality();
  }, 30000);

  // 设置图表数据更新 - 每2分钟更新一次历史数据
  chartUpdateInterval = setInterval(() => {
    fetchWaterQualityHistory();
  }, 120000);
}

// 获取当前水质数据 - 增强错误处理
function fetchCurrentWaterQuality() {
  fetch(`${backendUrl}/api/water-quality/current`)
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.status === 'success') {
        updateWaterQualityDisplay(data.data);
        currentWaterData = data.data;
      } else {
        throw new Error(data.message || '获取数据失败');
      }
    })
    .catch(error => {
      console.error('获取水质数据失败:', error);
      showMessage(`获取水质数据失败: ${error.message}`, 'warning');

      // 显示离线状态
      const waterQualityCards = document.querySelectorAll('.water-quality-card');
      waterQualityCards.forEach(card => {
        card.classList.add('offline');
      });
    });
}

// 获取历史水质数据用于图表 - 增强错误处理
function fetchWaterQualityHistory() {
  fetch(`${backendUrl}/api/water-quality/history?hours=24`)
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.status === 'success') {
        updateWaterQualityChart(data.data);
      } else {
        throw new Error(data.message || '获取历史数据失败');
      }
    })
    .catch(error => {
      console.error('获取历史数据失败:', error);
      showMessage(`获取历史数据失败: ${error.message}`, 'warning');

      // 显示图表错误状态
      const chartContainer = document.getElementById('water-chart');
      if (chartContainer) {
        chartContainer.innerHTML = `
          <div class="flex items-center justify-center h-48 text-gray-400">
            <div class="text-center">
              <i data-lucide="wifi-off" class="w-8 h-8 mx-auto mb-2"></i>
              <p>数据加载失败</p>
              <button onclick="fetchWaterQualityHistory()" class="mt-2 text-blue-500 hover:text-blue-700">重试</button>
            </div>
          </div>
        `;

        // 重新初始化图标
        if (window.lucide) {
          lucide.createIcons();
        }
      }
    });
}

// 更新水质数据显示
function updateWaterQualityDisplay(data) {
  // 更新温度
  const temperature = document.getElementById('temperature');
  if (temperature) {
    temperature.innerHTML = `${data.temperature}<span class="water-quality-unit">°C</span>`;
  }

  // 更新溶解氧
  const oxygen = document.getElementById('oxygen');
  if (oxygen) {
    oxygen.innerHTML = `${data.oxygen}<span class="water-quality-unit">mg/L</span>`;
  }

  // 更新pH值
  const phValue = document.getElementById('ph-value');
  if (phValue) {
    phValue.textContent = data.ph;
  }

  // 更新TDS值
  const tdsValue = document.getElementById('tds-value');
  if (tdsValue) {
    tdsValue.innerHTML = `${data.tds}<span class="water-quality-unit">ppm</span>`;
  }

  // 更新浊度
  const turbidity = document.getElementById('turbidity');
  if (turbidity) {
    turbidity.innerHTML = `${data.turbidity}<span class="water-quality-unit">NTU</span>`;
  }

  // 更新水质状态徽章
  updateWaterQualityBadge(data);
}

// 更新水质状态徽章
function updateWaterQualityBadge(data) {
  const badge = document.getElementById('water-quality-badge');
  if (!badge) return;

  // 根据水质参数判断状态
  let status = 'good';
  let issues = [];

  if (data.temperature < 25 || data.temperature > 33) {
    issues.push('水温异常');
    status = 'warning';
  }
  if (data.oxygen < 6) {
    issues.push('溶解氧偏低');
    status = 'danger';
  }
  if (data.ph < 7.0 || data.ph > 7.5) {
    issues.push('pH值异常');
    status = 'warning';
  }
  if (data.tds > 400) {
    issues.push('TDS过高');
    status = 'warning';
  }
  if (data.turbidity > 4) {
    issues.push('浊度过高');
    status = 'warning';
  }

  // 设置徽章样式和文本
  badge.className = 'px-3 py-1 rounded-full text-sm font-medium';

  switch(status) {
    case 'good':
      badge.classList.add('bg-green-100', 'text-green-800');
      badge.textContent = '良好';
      break;
    case 'warning':
      badge.classList.add('bg-yellow-100', 'text-yellow-800');
      badge.textContent = '注意';
      break;
    case 'danger':
      badge.classList.add('bg-red-100', 'text-red-800', 'animate-pulse');
      badge.textContent = '异常';
      break;
  }
}

// 更新水质图表（使用实时数据）
function updateWaterQualityChart(historyData) {
  if (!historyData || historyData.length === 0) return;

  // 获取图表容器
  const chartContainer = document.getElementById('water-chart');
  if (!chartContainer) return;

  // 获取当前选择的参数
  const paramSelector = document.querySelector('.chart-selector');
  let selectedParam = 'oxygen'; // 默认显示溶解氧

  if (paramSelector) {
    const selectedText = paramSelector.value || paramSelector.textContent;
    if (selectedText.includes('水温')) selectedParam = 'temperature';
    else if (selectedText.includes('溶解氧')) selectedParam = 'oxygen';
    else if (selectedText.includes('pH')) selectedParam = 'ph';
    else if (selectedText.includes('TDS')) selectedParam = 'tds';
    else if (selectedText.includes('浊度')) selectedParam = 'turbidity';
  }

  // 转换数据格式
  const chartData = historyData.slice(-12).map(item => {
    const time = new Date(item.timestamp);
    return {
      time: time.getHours().toString().padStart(2, '0') + ':' + time.getMinutes().toString().padStart(2, '0'),
      value: item[selectedParam]
    };
  });

  // 清空图表容器
  chartContainer.innerHTML = '';

  // 尝试使用Recharts，如果失败则使用简单的SVG图表
  if (window.Recharts && window.React && window.ReactDOM) {
    try {
      const { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } = Recharts;

      const chart = React.createElement(
        LineChart,
        {
          width: chartContainer.clientWidth || 400,
          height: 200,
          data: chartData,
          margin: { top: 10, right: 30, left: 0, bottom: 0 }
        },
        [
          React.createElement(CartesianGrid, { strokeDasharray: '3 3', key: 'grid' }),
          React.createElement(XAxis, { dataKey: 'time', key: 'x-axis' }),
          React.createElement(YAxis, { key: 'y-axis' }),
          React.createElement(Tooltip, { key: 'tooltip' }),
          React.createElement(Line, {
            type: 'monotone',
            dataKey: 'value',
            stroke: '#3b82f6',
            activeDot: { r: 8 },
            key: 'line'
          })
        ]
      );

      ReactDOM.render(chart, chartContainer);
    } catch (error) {
      console.log('Recharts渲染失败，使用简单图表:', error);
      createSimpleChart(chartContainer, chartData, selectedParam);
    }
  } else {
    console.log('Recharts未加载，使用简单图表');
    createSimpleChart(chartContainer, chartData, selectedParam);
  }
}

// 创建简单的SVG图表
function createSimpleChart(container, data, paramName) {
  if (data.length === 0) return;

  const width = container.clientWidth || 400;
  const height = 200;
  const margin = { top: 20, right: 30, bottom: 40, left: 50 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;

  // 创建SVG元素
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', width);
  svg.setAttribute('height', height);
  svg.style.background = '#f9fafb';
  svg.style.border = '1px solid #e5e7eb';
  svg.style.borderRadius = '8px';

  // 计算数据范围
  const values = data.map(d => d.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const valueRange = maxValue - minValue || 1;

  // 创建路径
  const pathData = data.map((d, i) => {
    const x = margin.left + (i / (data.length - 1)) * chartWidth;
    const y = margin.top + (1 - (d.value - minValue) / valueRange) * chartHeight;
    return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
  }).join(' ');

  // 添加网格线
  for (let i = 0; i <= 4; i++) {
    const y = margin.top + (i / 4) * chartHeight;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', margin.left);
    line.setAttribute('y1', y);
    line.setAttribute('x2', margin.left + chartWidth);
    line.setAttribute('y2', y);
    line.setAttribute('stroke', '#e5e7eb');
    line.setAttribute('stroke-dasharray', '3,3');
    svg.appendChild(line);
  }

  // 添加折线
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', pathData);
  path.setAttribute('stroke', '#3b82f6');
  path.setAttribute('stroke-width', '2');
  path.setAttribute('fill', 'none');
  svg.appendChild(path);

  // 添加数据点
  data.forEach((d, i) => {
    const x = margin.left + (i / (data.length - 1)) * chartWidth;
    const y = margin.top + (1 - (d.value - minValue) / valueRange) * chartHeight;

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', x);
    circle.setAttribute('cy', y);
    circle.setAttribute('r', '4');
    circle.setAttribute('fill', '#3b82f6');
    circle.setAttribute('stroke', 'white');
    circle.setAttribute('stroke-width', '2');

    // 添加悬停效果
    circle.addEventListener('mouseenter', function() {
      this.setAttribute('r', '6');

      // 显示数值
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', x);
      text.setAttribute('y', y - 10);
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('fill', '#374151');
      text.setAttribute('font-size', '12');
      text.textContent = `${d.value}`;
      text.setAttribute('id', 'tooltip-text');
      svg.appendChild(text);
    });

    circle.addEventListener('mouseleave', function() {
      this.setAttribute('r', '4');
      const tooltip = svg.querySelector('#tooltip-text');
      if (tooltip) tooltip.remove();
    });

    svg.appendChild(circle);
  });

  // 添加Y轴标签
  const yLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  yLabel.setAttribute('x', 15);
  yLabel.setAttribute('y', margin.top + chartHeight / 2);
  yLabel.setAttribute('text-anchor', 'middle');
  yLabel.setAttribute('fill', '#6b7280');
  yLabel.setAttribute('font-size', '12');
  yLabel.setAttribute('transform', `rotate(-90, 15, ${margin.top + chartHeight / 2})`);
  yLabel.textContent = getParamUnit(paramName);
  svg.appendChild(yLabel);

  container.appendChild(svg);
}

// 获取参数单位
function getParamUnit(param) {
  const units = {
    'temperature': '水温 (°C)',
    'oxygen': '溶解氧 (mg/L)',
    'ph': 'pH值',
    'tds': 'TDS (ppm)',
    'turbidity': '浊度 (NTU)'
  };
  return units[param] || param;
}

// 初始化图表选择器
function initChartSelectors() {
  const chartSelectors = document.querySelectorAll('.chart-selector');

  chartSelectors.forEach(selector => {
    selector.addEventListener('change', function() {
      // 当选择器改变时，重新获取历史数据并更新图表
      fetchWaterQualityHistory();
    });
  });
}

// 初始化地图配置
function initMapWithConfig() {
  fetch(`${backendUrl}/api/config/map`)
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.status === 'success') {
        const config = data.data;

        // 动态加载高德地图API
        let script = document.getElementById('amap-script');
        if (!script) {
          // 如果script标签不存在，创建一个新的
          script = document.createElement('script');
          script.id = 'amap-script';
          document.head.appendChild(script);
        }

        if (config.amap_api_key) {
          script.src = `https://webapi.amap.com/maps?v=2.0&key=${config.amap_api_key}`;
          script.onload = function() {
            console.log('✓ 高德地图API加载成功');
            // 稍等一下再初始化地图，确保API完全加载
            setTimeout(() => {
              initMapInstance(config);
            }, 500);
          };
          script.onerror = function() {
            console.error('✗ 高德地图API加载失败');
            showMessage('地图服务加载失败，请检查网络连接', 'error');
          };
        } else {
          throw new Error('API密钥未配置');
        }
      } else {
        throw new Error(data.message || '获取地图配置失败');
      }
    })
    .catch(error => {
      console.error('获取地图配置失败:', error);
      showMessage(`地图配置加载失败: ${error.message}`, 'warning');
    });
}

// 初始化地图实例
function initMapInstance(config) {
  // 检查是否有地图容器
  const mapContainer = document.getElementById('map-container');
  if (!mapContainer) {
    console.log('地图容器未找到，跳过地图初始化');
    return;
  }

  try {
    console.log('开始初始化地图实例...');

    // 创建地图实例
    const map = new AMap.Map('map-container', {
      zoom: config.zoom_level || 16,
      center: [config.map_center.longitude, config.map_center.latitude],
      viewMode: '2D',
      mapStyle: 'amap://styles/normal'
    });

    console.log('✓ 地图实例创建成功');

    // 地图加载完成事件
    map.on('complete', function() {
      console.log('✓ 地图加载完成');
    });

    // 地图错误事件
    map.on('error', function(error) {
      console.error('✗ 地图加载错误:', error);
      showMessage('地图加载错误', 'error');
    });

    // 添加地图控件
    map.plugin(['AMap.ToolBar', 'AMap.Scale'], function() {
      map.addControl(new AMap.ToolBar({
        position: 'RB'
      }));
      map.addControl(new AMap.Scale());
    });

    // 华中科技大学渔场边界（多边形）
    const pondPath = [
      [114.431280, 30.514498],
      [114.431341, 30.514523],
      [114.431376, 30.514591],
      [114.431389, 30.514617],
      [114.431405, 30.514683],
      [114.431350, 30.514646],
      [114.431314, 30.514584],
      [114.431280, 30.514498]
    ];

    // 绘制鱼池边界
    const pondPolygon = new AMap.Polygon({
      path: pondPath,
      strokeColor: '#3880ff',
      strokeWeight: 3,
      strokeOpacity: 0.8,
      fillColor: '#87CEFA',
      fillOpacity: 0.3,
      zIndex: 10
    });

    // 将鱼池边界添加到地图
    map.add(pondPolygon);

    // 自适应视野到鱼池边界
    map.setFitView([pondPolygon]);

    // 初始化巡航功能
    initCruiseFeatures(map);

    // 存储地图实例供其他函数使用
    window.fisheryMap = map;

    console.log('✓ 地图初始化成功');
    showMessage('地图加载成功', 'success');

  } catch (error) {
    console.error('地图初始化失败:', error);
    mapContainer.innerHTML = `
      <div class="flex items-center justify-center h-full text-gray-500">
        <div class="text-center">
          <i data-lucide="map-pin-off" class="w-12 h-12 mx-auto mb-4"></i>
          <p class="text-lg font-medium">地图初始化失败</p>
          <p class="text-sm">${error.message}</p>
          <button onclick="location.reload()" class="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
            重新加载
          </button>
        </div>
      </div>
    `;

    // 重新初始化图标
    if (window.lucide) {
      lucide.createIcons();
    }

    showMessage('地图初始化失败', 'error');
  }
}

// 初始化巡航功能
function initCruiseFeatures(map) {
  // 巡航点标记数组
  let cruiseMarkers = [];
  let isSettingPath = false;
  let cruisePath = null;
  let cruiseMarker = null;
  let cruiseInterval = null;
  let currentPathIndex = 0;

  // 获取按钮元素
  const setPathBtn = document.getElementById('set-path-btn');
  const startCruiseBtn = document.getElementById('start-cruise-btn');

  // 设置路径按钮点击事件
  if (setPathBtn) {
    setPathBtn.addEventListener('click', function() {
      isSettingPath = !isSettingPath;

      if (isSettingPath) {
        // 开始设置路径模式
        this.classList.remove('btn-secondary');
        this.classList.add('btn-primary');
        this.querySelector('span').textContent = '完成设置';

        // 显示提示信息
        const infoWindow = new AMap.InfoWindow({
          content: '点击地图添加巡航点',
          offset: new AMap.Pixel(0, -25)
        });

        infoWindow.open(map, map.getCenter());

        // 2秒后关闭提示
        setTimeout(() => {
          infoWindow.close();
        }, 2000);
      } else {
        // 完成设置路径模式
        this.classList.remove('btn-primary');
        this.classList.add('btn-secondary');
        this.querySelector('span').textContent = '设置路径';

        // 如果有足够的巡航点，绘制路径
        if (cruiseMarkers.length > 1) {
          drawCruisePath();
          showMessage(`巡航路径设置完成，共${cruiseMarkers.length}个点`, 'success');
        } else {
          showMessage('请至少设置2个巡航点', 'warning');
        }
      }
    });
  }

  // 地图点击事件
  map.on('click', function(e) {
    if (isSettingPath) {
      // 创建标记
      const marker = new AMap.Marker({
        position: e.lnglat,
        icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
        label: {
          content: `点${cruiseMarkers.length + 1}`,
          direction: 'top'
        },
        draggable: true,
        cursor: 'move'
      });

      // 将标记添加到地图
      map.add(marker);

      // 将标记添加到巡航标记数组
      cruiseMarkers.push(marker);

      // 标记拖拽结束后重绘路径
      marker.on('dragend', function() {
        if (cruiseMarkers.length > 1) {
          drawCruisePath();
        }
      });

      showMessage(`已添加巡航点${cruiseMarkers.length}`, 'info');
    }
  });

  // 绘制巡航路径
  function drawCruisePath() {
    // 如果存在旧路径，先移除
    if (cruisePath) {
      map.remove(cruisePath);
    }

    // 获取所有标记的位置
    const path = cruiseMarkers.map(marker => marker.getPosition());

    // 创建路径
    cruisePath = new AMap.Polyline({
      path: path,
      strokeColor: '#22c55e',
      strokeWeight: 4,
      strokeOpacity: 0.7,
      zIndex: 5,
      strokeStyle: 'dashed',
      strokeDasharray: [10, 5]
    });

    // 将路径添加到地图
    map.add(cruisePath);
  }

  // 开始巡航按钮点击事件
  if (startCruiseBtn) {
    startCruiseBtn.addEventListener('click', function() {
      if (cruiseMarkers.length < 2) {
        showMessage('请先设置至少2个巡航点', 'warning');
        return;
      }

      // 开始巡航
      startCruise();
    });
  }

  // 开始巡航函数
  function startCruise() {
    // 调用后端API
    const cruiseData = {
      location: '华中科技大学渔场',
      coordinates: cruiseMarkers.map(marker => {
        const pos = marker.getPosition();
        return { longitude: pos.lng, latitude: pos.lat };
      }),
      timestamp: new Date().toISOString(),
      deviceId: 'RDKX5-001'
    };

    // 发送API请求
    fetch(`${backendUrl}/api/cruise/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(cruiseData)
    }).then(response => {
      if (response.ok) {
        return response.json();
      }
      throw new Error('API调用失败');
    }).then(data => {
      console.log('巡航API响应:', data);
      showMessage('巡航指令已发送到RDKX5设备', 'success');
      startCruiseAnimation();
    }).catch(error => {
      console.log('API调用失败，使用模拟模式:', error);
      showMessage('API调用失败，使用模拟模式', 'warning');
      startCruiseAnimation();
    });
  }

  // 开始巡航动画
  function startCruiseAnimation() {
    // 如果存在旧的巡航标记，先移除
    if (cruiseMarker) {
      map.remove(cruiseMarker);
    }

    // 如果存在旧的巡航定时器，先清除
    if (cruiseInterval) {
      clearInterval(cruiseInterval);
    }

    // 创建巡航标记
    cruiseMarker = new AMap.Marker({
      position: cruiseMarkers[0].getPosition(),
      icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png',
      zIndex: 20
    });

    // 将巡航标记添加到地图
    map.add(cruiseMarker);

    // 重置当前路径索引
    currentPathIndex = 0;

    // 开始巡航动画
    cruiseInterval = setInterval(() => {
      // 获取下一个点的索引
      currentPathIndex = (currentPathIndex + 1) % cruiseMarkers.length;

      // 获取下一个点的位置
      const nextPosition = cruiseMarkers[currentPathIndex].getPosition();

      // 移动巡航标记
      cruiseMarker.setPosition(nextPosition);

      // 显示水质监测信息
      showWaterQualityInfo(nextPosition);
    }, 3000);
  }

  // 显示水质监测信息
  function showWaterQualityInfo(position) {
    // 使用当前水质数据或生成模拟数据
    let temperature, oxygen, ph;

    if (currentWaterData) {
      temperature = currentWaterData.temperature;
      oxygen = currentWaterData.oxygen;
      ph = currentWaterData.ph;
    } else {
      // 生成模拟数据
      temperature = (22 + Math.random() * 8).toFixed(1);
      oxygen = (5 + Math.random() * 3).toFixed(1);
      ph = (6.5 + Math.random()).toFixed(1);
    }

    // 创建信息窗口内容
    const content = `
      <div class="p-3 min-w-48">
        <div class="text-blue-600 font-medium mb-2">水质监测点${currentPathIndex + 1}</div>
        <div class="space-y-1 text-sm">
          <div class="flex justify-between">
            <span>水温:</span>
            <span class="font-medium">${temperature}°C</span>
          </div>
          <div class="flex justify-between">
            <span>溶氧:</span>
            <span class="font-medium">${oxygen}mg/L</span>
          </div>
          <div class="flex justify-between">
            <span>pH值:</span>
            <span class="font-medium">${ph}</span>
          </div>
        </div>
      </div>
    `;

    // 创建信息窗口
    const infoWindow = new AMap.InfoWindow({
      content: content,
      offset: new AMap.Pixel(0, -30)
    });

    // 打开信息窗口
    infoWindow.open(map, position);

    // 2秒后关闭信息窗口
    setTimeout(() => {
      infoWindow.close();
    }, 2000);
  }
}

