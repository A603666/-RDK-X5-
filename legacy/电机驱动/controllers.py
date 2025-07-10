# controllers.py

import os
import time
from enum import Enum, auto
import math
import Hobot.GPIO as GPIO
import config

# Helper function to safely write to sysfs files
def write_sysfs(path, value):
    """Safely writes a value to a sysfs file, handling permissions errors."""
    try:
        with open(path, 'w') as f:
            f.write(str(value))
        return True
    except (IOError, PermissionError) as e:
        print(f"Error writing to {path}: {e}. Please run the script with 'sudo'.")
        return False

class MotorController:
    """
    螺旋桨电机控制器
    通过Linux sysfs接口直接控制RDKX5的板载PWM。
    """
    def __init__(self):
        print("Initializing on-board PWM motor controller via sysfs...")
        self.motor1_path = os.path.join(config.PWM_CHIP_PATH, f"pwm{config.MOTOR_1_CHANNEL}")
        self.motor2_path = os.path.join(config.PWM_CHIP_PATH, f"pwm{config.MOTOR_2_CHANNEL}")

        # Export PWM channels if they don't exist
        if not os.path.exists(self.motor1_path):
            print(f"Exporting PWM channel {config.MOTOR_1_CHANNEL}...")
            write_sysfs(os.path.join(config.PWM_CHIP_PATH, "export"), config.MOTOR_1_CHANNEL)
        if not os.path.exists(self.motor2_path):
            print(f"Exporting PWM channel {config.MOTOR_2_CHANNEL}...")
            write_sysfs(os.path.join(config.PWM_CHIP_PATH, "export"), config.MOTOR_2_CHANNEL)
        
        time.sleep(0.5)  # Give sysfs time to create directories

        self._setup_motor(self.motor1_path, "Motor 1")
        self._setup_motor(self.motor2_path, "Motor 2")
        self.stop_all()

    def _setup_motor(self, motor_path, name):
        print(f"Configuring {name} at {motor_path}...")
        if not os.path.exists(motor_path):
            print(f"ERROR: PWM path {motor_path} does not exist. Aborting.")
            return
        write_sysfs(os.path.join(motor_path, "period"), config.PERIOD_NS)
        write_sysfs(os.path.join(motor_path, "duty_cycle"), config.STOP_PULSE_NS)
        write_sysfs(os.path.join(motor_path, "enable"), 1)

    def _speed_to_duty_ns(self, speed):
        """Converts normalized speed (-1.0 to 1.0) to nanosecond pulse width."""
        if speed == 0:
            return config.STOP_PULSE_NS
        elif speed > 0:  # Forward
            return int(config.STOP_PULSE_NS + (config.MAX_FORWARD_PULSE_NS - config.STOP_PULSE_NS) * speed)
        else:  # Reverse
            return int(config.STOP_PULSE_NS - (config.STOP_PULSE_NS - config.MAX_REVERSE_PULSE_NS) * abs(speed))

    def set_motor_speed(self, motor_num, speed):
        """Sets the speed of a single motor."""
        if not -1.0 <= speed <= 1.0:
            print(f"Warning: Speed {speed} is out of range [-1.0, 1.0]. Clamping.")
            speed = max(-1.0, min(1.0, speed))

        duty_ns = self._speed_to_duty_ns(speed)
        motor_path = self.motor1_path if motor_num == 1 else self.motor2_path
        
        print(f"Setting Motor {motor_num}: Speed={speed:.2f}, Pulse={duty_ns / 1_000_000:.2f}ms")
        write_sysfs(os.path.join(motor_path, "duty_cycle"), duty_ns)

    def stop_all(self):
        self.set_motor_speed(1, 0)
        self.set_motor_speed(2, 0)
        print("All motors stopped.")

    def cleanup(self):
        print("Cleaning up motor controller...")
        if os.path.exists(self.motor1_path):
            write_sysfs(os.path.join(self.motor1_path, "enable"), 0)
            write_sysfs(os.path.join(config.PWM_CHIP_PATH, "unexport"), config.MOTOR_1_CHANNEL)
        if os.path.exists(self.motor2_path):
            write_sysfs(os.path.join(self.motor2_path, "enable"), 0)
            write_sysfs(os.path.join(config.PWM_CHIP_PATH, "unexport"), config.MOTOR_2_CHANNEL)
        print("Motor controller cleaned up.")

class PumpController:
    """
    药品投放水泵控制器
    使用Hobot.GPIO进行开关控制。
    """
    def __init__(self):
        print("Initializing pump controller using Hobot.GPIO...")
        self.pins = {1: config.PUMP_1_PIN, 2: config.PUMP_2_PIN}
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(list(self.pins.values()), GPIO.OUT, initial=GPIO.LOW)
        print("Pump controller initialized, all pumps off.")

    def dispense_volume(self, pump_number, volume_ml):
        """Dispenses a specific volume of liquid using a pulsed, iterative method."""
        if pump_number not in self.pins:
            print(f"Error: Invalid pump number {pump_number}.")
            return 0

        volume_per_pulse = config.PUMP_FLOW_RATE_ML_PER_SEC * config.DISPENSE_PULSE_DURATION_S
        total_pulses_needed = math.ceil(volume_ml / volume_per_pulse)
        pulses_per_iteration = math.ceil(total_pulses_needed / config.DISPENSE_ITERATIONS)
        
        print(f"\n--- Dispensing Task Start ---")
        print(f"Pump: {pump_number}, Target Volume: {volume_ml}ml")
        print(f"Total pulses required: {total_pulses_needed} ({volume_per_pulse:.1f}ml per pulse)")
        print(f"Task split into {config.DISPENSE_ITERATIONS} iterations of ~{pulses_per_iteration} pulses each.")
        
        total_dispensed_ml = 0
        for i in range(config.DISPENSE_ITERATIONS):
            print(f"\nRunning iteration {i+1}/{config.DISPENSE_ITERATIONS}...")
            for p in range(pulses_per_iteration):
                if (i * pulses_per_iteration + p) >= total_pulses_needed:
                    break # Stop if we have completed all required pulses
                
                GPIO.output(self.pins[pump_number], GPIO.HIGH)
                time.sleep(config.DISPENSE_PULSE_DURATION_S)
                GPIO.output(self.pins[pump_number], GPIO.LOW)
                total_dispensed_ml += volume_per_pulse

            if i < config.DISPENSE_ITERATIONS - 1:
                print(f"Iteration {i+1} complete. Pausing for {config.DISPENSE_PULSE_PAUSE_S}s...")
                time.sleep(config.DISPENSE_PULSE_PAUSE_S)

        print("\n--- Dispensing Task Complete ---")
        print(f"Estimated volume dispensed: {total_dispensed_ml:.2f}ml")
        return total_dispensed_ml

    def cleanup(self):
        print("Cleaning up pump controller...")
        GPIO.cleanup(list(self.pins.values()))
        print("Pump controller cleaned up.")

class MedicineStatus(Enum):
    FILLED = "药品已填充"
    DISPENSING = "正在投药"
    DONE = "投药完成"

class CapacityLevel(Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"
    EMPTY = "空"

class MedicineBay:
    """Manages the state and logic of a single medicine bay."""
    def __init__(self, bay_id, drug_name, total_capacity_ml):
        self.bay_id = bay_id
        self.drug_name = drug_name
        self.total_capacity_ml = total_capacity_ml
        self.current_volume_ml = total_capacity_ml
        self.dispensed_volume_ml = 0
        self.status = MedicineStatus.FILLED

    @property
    def capacity_level(self):
        if self.current_volume_ml <= 0: return CapacityLevel.EMPTY
        ratio = self.current_volume_ml / self.total_capacity_ml
        if ratio <= 0.3: return CapacityLevel.LOW
        if ratio <= 0.7: return CapacityLevel.MEDIUM
        return CapacityLevel.HIGH
            
    def start_dispensing(self, volume_to_dispense, pump_controller):
        if self.capacity_level == CapacityLevel.EMPTY:
            print(f"Error: Bay {self.bay_id} is empty and cannot dispense.")
            return

        self.status = MedicineStatus.DISPENSING
        self.print_status()
        
        actual_dispensed = pump_controller.dispense_volume(self.bay_id, volume_to_dispense)
        
        self.dispensed_volume_ml += actual_dispensed
        self.current_volume_ml -= actual_dispensed
        
        if self.current_volume_ml <= 0:
            self.current_volume_ml = 0
            self.status = MedicineStatus.DONE
        else:
            self.status = MedicineStatus.FILLED
        
        self.print_status()

    def print_status(self):
        print(f"--- Bay {self.bay_id} Status ---")
        print(f"  Drug Name:      {self.drug_name}")
        print(f"  Status:         {self.status.value}")
        print(f"  Capacity Level: {self.capacity_level.value}")
        print(f"  Current Volume: {self.current_volume_ml:.1f}/{self.total_capacity_ml:.1f} ml")
        print(f"  Total Dispensed: {self.dispensed_volume_ml:.1f} ml")
        print("--------------------")
