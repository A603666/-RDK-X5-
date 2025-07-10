# coding: utf-8
# Configuration file for GPS-IMU fusion system

# Serial port configuration
GPS_PORT = "/dev/ttyUSB0"
GPS_BAUDRATE = 9600
IMU_PORT = "/dev/ttyUSB1"
IMU_BAUDRATE = 115200

# Kalman filter parameters
# Process noise
Q_POS = 0.01      # Position process noise
Q_VEL = 0.1       # Velocity process noise
Q_ATT = 0.1       # Attitude process noise

# Measurement noise
R_GPS_POS = 5.0   # GPS position measurement noise (meters)
R_GPS_VEL = 1.0   # GPS velocity measurement noise (m/s)
R_IMU_ATT = 0.1   # IMU attitude measurement noise (degrees)

# Initial state covariance
P_INIT = 10.0

# Data validation thresholds
GPS_MIN_SATELLITES = 4
GPS_MAX_HDOP = 5.0
IMU_MAX_GYRO = 300.0  # deg/s
IMU_MAX_ACC = 10.0    # g

# Output configuration
PRINT_INTERVAL = 1.0  # seconds
