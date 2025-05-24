import smbus
import time

# ADXL345 Register Addresses
ADXL345_ADDRESS = 0x53
POWER_CTL = 0x2D
DATA_FORMAT = 0x31
DATAX0 = 0x32
DATAX1 = 0x33
DATAY0 = 0x34
DATAY1 = 0x35
DATAZ0 = 0x36
DATAZ1 = 0x37

# Initialize I2C (SMBus)
bus = smbus.SMBus(1)  # Use 1 for newer Raspberry Pi models

# ADXL345 Initialization
def initialize_adxl345():
    bus.write_byte_data(ADXL345_ADDRESS, POWER_CTL, 0x08)  # Wake up the ADXL345
    bus.write_byte_data(ADXL345_ADDRESS, DATA_FORMAT, 0x01)  # Set data format to 10-bit

def read_acceleration():
    x0 = bus.read_byte_data(ADXL345_ADDRESS, DATAX0)
    x1 = bus.read_byte_data(ADXL345_ADDRESS, DATAX1)
    y0 = bus.read_byte_data(ADXL345_ADDRESS, DATAY0)
    y1 = bus.read_byte_data(ADXL345_ADDRESS, DATAY1)
    z0 = bus.read_byte_data(ADXL345_ADDRESS, DATAZ0)
    z1 = bus.read_byte_data(ADXL345_ADDRESS, DATAZ1)

    x = (x1 << 8) | x0
    y = (y1 << 8) | y0
    z = (z1 << 8) | z0

    if x > 32767:
        x -= 65536
    if y > 32767:
        y -= 65536
    if z > 32767:
        z -= 65536

    return x, y, z

def is_moving(threshold):
    x, y, z = read_acceleration()
    magnitude = (x**2 + y**2 + z**2)**0.5
    return magnitude > threshold

# Initialization
initialize_adxl345()
motion_threshold = 100  # Adjust based on your application
motion_start_time = None
motion_end_time = None
total_motion_duration = 0
last_check_time = time.time()
last_print_time = time.time()  # Timer to display every 3 seconds

try:
    while True:
        current_time = time.time()
        
        if is_moving(motion_threshold):
            if motion_start_time is None:
                motion_start_time = current_time  # Motion started
            motion_end_time = None
        else:
            if motion_start_time is not None:  # Motion just ended
                motion_end_time = current_time
                duration = motion_end_time - motion_start_time  # Calculate motion duration
                total_motion_duration += duration  # Add to the total
                
                # Display motion duration every 3 seconds
            if current_time - last_print_time >= 3:
                #print(f"Total motion duration so far: {total_motion_duration:.2f} seconds")
                last_print_time = current_time  # Reset the 3-second timer
                print(f"Individual motion duration: {duration:.2f} seconds")  # Print the duration
                motion_start_time = None  # Reset motion start time

        # Check every 1 minutes
        if current_time - last_check_time >= 60:
            # Reset the timer
            last_check_time = current_time
            
            # Check if total duration is within the range
            if total_motion_duration < 45 or total_motion_duration > 55:
                print(f"Alert: Total motion duration outside of expected range: {total_motion_duration:.2f} seconds")
            
            # Print the total duration for the last 2 minutes
            print(f"Total motion duration in the last 1 minutes: {total_motion_duration:.2f} seconds")
            
            # Reset total motion duration for the next interval
            total_motion_duration = 0

        time.sleep(0.1)  # Adjust the delay as needed

except KeyboardInterrupt:
    print("Program interrupted")
