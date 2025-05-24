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

try:
    while True:
        if is_moving(motion_threshold):
            if motion_start_time is None:
                motion_start_time = time.time()
            motion_end_time = None
        else:
            if motion_start_time is not None:
                motion_end_time = time.time()
                duration = motion_end_time - motion_start_time
                print(f"Motion duration: {duration:.2f} seconds")
                motion_start_time = None

        time.sleep(0.1)  # Adjust the delay as needed

except KeyboardInterrupt:
    print("Program interrupted")
