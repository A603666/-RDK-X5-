# config.py

# -- 硬件接口配置 --

# 药品投放水泵 (使用RDKX5的GPIO)
PUMP_1_PIN = 29  # BOARD 编码, 对应 GPIO5
PUMP_2_PIN = 31  # BOARD 编码, 对应 GPIO6

# 螺旋桨电机 (通过 sysfs 控制板载PWM)
# 根据文档，Pin 32/33 属于 pwmchip3
PWM_CHIP_PATH = "/sys/class/pwm/pwmchip3/"
# Pin 32 是 pwm6(channel 0 on chip 3), Pin 33 是 pwm7(channel 1 on chip 3)
MOTOR_1_CHANNEL = 0
MOTOR_2_CHANNEL = 1

# -- 控制参数 --

# PWM 控制规范 (单位：纳秒)
PWM_FREQUENCY_HZ = 50
PERIOD_NS = int(1 / PWM_FREQUENCY_HZ * 1_000_000_000)  # 20,000,000 ns for 50Hz

# 脉冲宽度定义 (单位：纳秒)
STOP_PULSE_NS = 1_500_000  # 1.5ms for stop
MAX_FORWARD_PULSE_NS = 2_000_000  # 2.0ms for max forward
MAX_REVERSE_PULSE_NS = 1_000_000  # 1.0ms for max reverse

# 航行速度等级 (油门百分比)
SPEED_LEVELS = {
    1: 1.0,   # 快速 (100% 油门)
    2: 0.75,  # 中速 (75% 油门)
    3: 0.5,   # 慢速 (50% 油门)
}
DEFAULT_SPEED_LEVEL = 3  # 默认慢速

# 药品投放系统参数
PUMP_FLOW_RATE_ML_PER_SEC = 80.0  # 水泵流量 ml/秒
DISPENSE_PULSE_DURATION_S = 0.5   # 每次投放的运行时间 (秒)
DISPENSE_PULSE_PAUSE_S = 2.0      # 每轮投放后的暂停时间 (秒)
DISPENSE_ITERATIONS = 10          # 将总投放任务分为10轮
