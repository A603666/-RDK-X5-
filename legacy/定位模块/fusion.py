# coding: utf-8
import numpy as np
import time
import math
import CONFIG

class KalmanFilter:
    def __init__(self):
        # State vector: [x, y, z, vx, vy, vz, roll, pitch, yaw]
        self.state = np.zeros(9)
        
        # State covariance matrix
        self.P = np.eye(9) * CONFIG.P_INIT
        
        # Process noise covariance
        self.Q = np.diag([
            CONFIG.Q_POS, CONFIG.Q_POS, CONFIG.Q_POS,
            CONFIG.Q_VEL, CONFIG.Q_VEL, CONFIG.Q_VEL,
            CONFIG.Q_ATT, CONFIG.Q_ATT, CONFIG.Q_ATT
        ])
        
        # GPS measurement noise covariance
        self.R_gps = np.diag([
            CONFIG.R_GPS_POS, CONFIG.R_GPS_POS, CONFIG.R_GPS_POS,
            CONFIG.R_GPS_VEL, CONFIG.R_GPS_VEL, CONFIG.R_GPS_VEL
        ])
        
        # IMU measurement noise covariance
        self.R_imu = np.diag([
            CONFIG.R_IMU_ATT, CONFIG.R_IMU_ATT, CONFIG.R_IMU_ATT
        ])
        
        # Timestamps for delta time calculation
        self.last_time = 0
        self.initialized = False
        
        # Earth radius in meters
        self.EARTH_RADIUS = 6378137.0
        
        # Reference position for local coordinate conversion
        self.ref_lat = None
        self.ref_lon = None
        self.ref_alt = None
        
        # Uncertainty estimates
        self.pos_uncertainty = 10.0  # meters
        self.heading_uncertainty = 5.0  # degrees
    
    def _set_reference_position(self, lat, lon, alt):
        self.ref_lat = lat
        self.ref_lon = lon
        self.ref_alt = alt
    
    def _geo_to_local(self, lat, lon, alt):
        """Convert geodetic coordinates to local ENU coordinates"""
        if self.ref_lat is None:
            self._set_reference_position(lat, lon, alt)
            return 0.0, 0.0, 0.0
        
        # Calculate distance using Haversine formula
        lat1, lon1 = np.radians(self.ref_lat), np.radians(self.ref_lon)
        lat2, lon2 = np.radians(lat), np.radians(lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # East component
        east = dlon * np.cos((lat1 + lat2) / 2) * self.EARTH_RADIUS
        # North component
        north = dlat * self.EARTH_RADIUS
        # Up component
        up = alt - self.ref_alt
        
        return east, north, up
    
    def _local_to_geo(self, east, north, up):
        """Convert local ENU coordinates to geodetic"""
        if self.ref_lat is None:
            return 0.0, 0.0, 0.0
        
        lat1, lon1 = np.radians(self.ref_lat), np.radians(self.ref_lon)
        
        dlat = north / self.EARTH_RADIUS
        dlon = east / (self.EARTH_RADIUS * np.cos(lat1))
        
        lat2 = lat1 + dlat
        lon2 = lon1 + dlon
        alt = self.ref_alt + up
        
        return np.degrees(lat2), np.degrees(lon2), alt
    
    def predict(self, current_time):
        if not self.initialized:
            self.last_time = current_time
            self.initialized = True
            return
        
        # Calculate time delta
        dt = current_time - self.last_time
        if dt <= 0:
            return
        
        # State transition matrix
        F = np.eye(9)
        F[0, 3] = dt  # x += vx * dt
        F[1, 4] = dt  # y += vy * dt
        F[2, 5] = dt  # z += vz * dt
        
        # Predict state
        self.state = F @ self.state
        
        # Predict covariance
        self.P = F @ self.P @ F.T + self.Q * dt
        
        # Update position uncertainty based on diagonal of covariance matrix
        self.pos_uncertainty = np.sqrt(np.mean([self.P[0,0], self.P[1,1]]))
        self.heading_uncertainty = np.sqrt(self.P[8,8])
        
        self.last_time = current_time
    
    def update_gps(self, lat, lon, alt, speed, course, valid=True):
        if not valid:
            return
        
        # Convert geodetic coordinates to local ENU
        x, y, z = self._geo_to_local(lat, lon, alt)
        
        # Convert speed and course to velocity components
        course_rad = np.radians(course)
        vx = speed * np.sin(course_rad)  # East component
        vy = speed * np.cos(course_rad)  # North component
        vz = 0.0  # Assuming no vertical velocity from GPS
        
        # GPS measurement vector [x, y, z, vx, vy, vz]
        z_gps = np.array([x, y, z, vx, vy, vz])
        
        # Measurement matrix for GPS (position and velocity)
        H_gps = np.zeros((6, 9))
        H_gps[0, 0] = 1.0  # x
        H_gps[1, 1] = 1.0  # y
        H_gps[2, 2] = 1.0  # z
        H_gps[3, 3] = 1.0  # vx
        H_gps[4, 4] = 1.0  # vy
        H_gps[5, 5] = 1.0  # vz
        
        # Innovation (measurement residual)
        y = z_gps - H_gps @ self.state
        
        # Innovation covariance
        S = H_gps @ self.P @ H_gps.T + self.R_gps
        
        # Kalman gain
        K = self.P @ H_gps.T @ np.linalg.inv(S)
        
        # Update state
        self.state = self.state + K @ y
        
        # Update covariance
        I = np.eye(9)
        self.P = (I - K @ H_gps) @ self.P
        
        # Update position uncertainty
        self.pos_uncertainty = np.sqrt(np.mean([self.P[0,0], self.P[1,1]]))
    
    def update_imu(self, roll, pitch, yaw, valid=True):
        if not valid:
            return
        
        # IMU measurement vector [roll, pitch, yaw]
        z_imu = np.array([roll, pitch, yaw])
        
        # Measurement matrix for IMU (attitude only)
        H_imu = np.zeros((3, 9))
        H_imu[0, 6] = 1.0  # roll
        H_imu[1, 7] = 1.0  # pitch
        H_imu[2, 8] = 1.0  # yaw
        
        # Innovation (measurement residual)
        y = z_imu - H_imu @ self.state
        
        # Special handling for yaw angle wrap-around
        if y[2] > 180:
            y[2] -= 360
        elif y[2] < -180:
            y[2] += 360
        
        # Innovation covariance
        S = H_imu @ self.P @ H_imu.T + self.R_imu
        
        # Kalman gain
        K = self.P @ H_imu.T @ np.linalg.inv(S)
        
        # Update state
        self.state = self.state + K @ y
        
        # Update covariance
        I = np.eye(9)
        self.P = (I - K @ H_imu) @ self.P
        
        # Update heading uncertainty
        self.heading_uncertainty = np.sqrt(self.P[8,8])
    
    def get_state(self):
        # Convert local ENU coordinates back to geodetic
        lat, lon, alt = self._local_to_geo(self.state[0], self.state[1], self.state[2])
        
        # Calculate speed from velocity components
        vx, vy, vz = self.state[3], self.state[4], self.state[5]
        speed = np.sqrt(vx**2 + vy**2)
        
        # Calculate course from velocity components
        course = np.degrees(np.arctan2(vx, vy))
        if course < 0:
            course += 360.0
            
        # Get attitude angles
        roll, pitch, yaw = self.state[6], self.state[7], self.state[8]
        
        return {
            'latitude': lat,
            'longitude': lon,
            'altitude': alt,
            'speed': speed,
            'course': course,
            'roll': roll,
            'pitch': pitch,
            'yaw': yaw,
            'pos_accuracy': self.pos_uncertainty,
            'heading_accuracy': self.heading_uncertainty,
            'valid': self.initialized
        }
