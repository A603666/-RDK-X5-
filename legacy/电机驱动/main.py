# main.py

import sys
import signal
import threading
from controllers import MotorController, PumpController, MedicineBay
import config

class UnmannedBoat:
    def __init__(self):
        print("Initializing Unmanned Boat Control System...")
        self.motor_controller = MotorController()
        self.pump_controller = PumpController()
        
        self.bays = {
            1: MedicineBay(1, "高效除藻剂", 2000),
            2: MedicineBay(2, "水体净化剂", 2000)
        }
        
        self.current_speed_level = config.DEFAULT_SPEED_LEVEL
        self.is_running = True
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        print("\nSystem ready. Use 'help' to see commands.")

    def signal_handler(self, signum, frame):
        print("\n\nExit signal received. Shutting down gracefully...")
        self.is_running = False

    def print_help(self):
        print("\n--- Unmanned Boat Control Console ---")
        print(f"Current Speed Tier: {self.current_speed_level} (1:Fast, 2:Med, 3:Slow)")
        print("Movement:  [W] Fwd  [S] Bwd  [A] Left  [D] Right  [X] Stop")
        print("Speed:     [1] Fast  [2] Medium  [3] Slow")
        print("Dispense:  bay_num,volume_ml (e.g., '1,500' for Bay 1, 500ml)")
        print("Commands:  [status]  [help]  [exit]")
        print("-------------------------------------")

    def handle_movement(self, command):
        speed_mult = config.SPEED_LEVELS.get(self.current_speed_level, 0.5)
        
        # Assuming Motor 1 is Left, Motor 2 is Right.
        # Differential Steering Logic:
        if command == 'w':   # Forward
            self.motor_controller.set_motor_speed(1, 1.0 * speed_mult)
            self.motor_controller.set_motor_speed(2, 1.0 * speed_mult)
        elif command == 's': # Backward
            self.motor_controller.set_motor_speed(1, -1.0 * speed_mult)
            self.motor_controller.set_motor_speed(2, -1.0 * speed_mult)
        elif command == 'a': # Left Turn (Right motor fwd, Left motor bwd)
            self.motor_controller.set_motor_speed(1, -1.0 * speed_mult)
            self.motor_controller.set_motor_speed(2, 1.0 * speed_mult)
        elif command == 'd': # Right Turn (Left motor fwd, Right motor bwd)
            self.motor_controller.set_motor_speed(1, 1.0 * speed_mult)
            self.motor_controller.set_motor_speed(2, -1.0 * speed_mult)
        elif command == 'x': # Stop
            self.motor_controller.stop_all()

    def handle_command(self, user_input):
        cmd = user_input.lower().strip()
        
        if not cmd:
            return
        elif cmd in ['w', 's', 'a', 'd', 'x']:
            self.handle_movement(cmd)
        elif cmd in ['1', '2', '3']:
            self.current_speed_level = int(cmd)
            print(f"Speed tier set to: {self.current_speed_level}")
        elif ',' in cmd:
            try:
                bay_id_str, vol_str = cmd.split(',')
                bay_id = int(bay_id_str.strip())
                volume = float(vol_str.strip())
                if bay_id in self.bays:
                    # Run dispense in a thread to avoid blocking main input loop
                    bay = self.bays[bay_id]
                    if bay.status == bay.status.DISPENSING:
                        print("Error: Bay is already busy dispensing.")
                    else:
                        dispense_thread = threading.Thread(
                            target=bay.start_dispensing,
                            args=(volume, self.pump_controller)
                        )
                        dispense_thread.start()
                else:
                    print("Error: Invalid bay number.")
            except (ValueError, IndexError):
                print("Error: Invalid dispense format. Use: bay_num,volume_ml")
        elif cmd == 'status':
            for bay in self.bays.values():
                bay.print_status()
        elif cmd == 'help':
            self.print_help()
        elif cmd == 'exit':
            self.is_running = False
        else:
            print(f"Unknown command: '{cmd}'. Type 'help' for options.")

    def run(self):
        self.print_help()
        try:
            while self.is_running:
                user_input = input("Enter command > ")
                self.handle_command(user_input)
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            self.is_running = False
        finally:
            self.cleanup()

    def cleanup(self):
        print("\nCleaning up all resources...")
        self.motor_controller.cleanup()
        self.pump_controller.cleanup()
        print("System shutdown complete.")

if __name__ == '__main__':
    boat = UnmannedBoat()
    boat.run()
