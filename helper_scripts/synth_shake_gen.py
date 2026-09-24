import numpy as np
import pandas as pd

def generate_running_imu_data(duration_sec=10.0, sample_rate_hz=100.0, step_freq_hz=2.5, base_uptime_sec=630567.829612):
    """
    Generates synthetic iOS CoreMotion IMU data with a realistic system uptime timestamp.
    """
    # Relative time vector (0 to duration)
    t = np.arange(0, duration_sec, 1.0 / sample_rate_hz)
    
    # iOS uses system uptime. We add the relative time to a realistic base uptime.
    uptime_t = base_uptime_sec + t
    
    # Base angular frequencies
    w_step = 2 * np.pi * step_freq_hz           
    w_stride = 2 * np.pi * (step_freq_hz / 2.0) 
    
    # --- 1. ATTITUDE (Radians) ---
    pitch_amp = np.radians(6) 
    pitch = pitch_amp * np.sin(w_step * t) + np.random.normal(0, 0.01, len(t))
    
    roll_amp = np.radians(4)
    roll = roll_amp * np.sin(w_stride * t) + np.random.normal(0, 0.01, len(t))
    
    yaw_amp = np.radians(3)
    yaw = yaw_amp * np.cos(w_stride * t) + np.random.normal(0, 0.01, len(t))
    
    # --- 2. ROTATION RATE (rad/s) ---
    rot_x = pitch_amp * w_step * np.cos(w_step * t) + np.random.normal(0, 0.08, len(t))
    rot_y = yaw_amp * w_stride * -np.sin(w_stride * t) + np.random.normal(0, 0.08, len(t))
    rot_z = roll_amp * w_stride * np.cos(w_stride * t) + np.random.normal(0, 0.08, len(t))
    
    # --- 3. USER ACCELERATION (G's) ---
    accel_y = (0.7 * np.sin(w_step * t - np.pi/2) + 
               0.3 * np.sin(2 * w_step * t) + 
               np.random.normal(0, 0.15, len(t)))
    
    accel_z = 0.35 * np.sin(w_step * t) + np.random.normal(0, 0.1, len(t))
    accel_x = 0.25 * np.sin(w_stride * t) + np.random.normal(0, 0.08, len(t))
    
    # --- Assemble DataFrame ---
    df = pd.DataFrame({
        'motionTimestamp_sinceReboot(s)': uptime_t,  # Updated column name and data
        'motionYaw(rad)': yaw,
        'motionPitch(rad)': pitch,
        'motionRoll(rad)': roll,
        'motionRotationRateX(rad/s)': rot_x,
        'motionRotationRateY(rad/s)': rot_y,
        'motionRotationRateZ(rad/s)': rot_z,
        'motionUserAccelerationX(G)': accel_x,
        'motionUserAccelerationY(G)': accel_y,
        'motionUserAccelerationZ(G)': accel_z
    })
    
    return df


def main():
    synthetic_df = generate_running_imu_data(duration_sec=5.0,sample_rate_hz=30)
    csv_filename = 'synth_shake.csv'
    synthetic_df.to_csv(csv_filename, index=False)


if __name__=="__main__":
    main()