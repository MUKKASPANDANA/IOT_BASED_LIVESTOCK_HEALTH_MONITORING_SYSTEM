import os
import glob
import time
from datetime import datetime
import pytz
import json
import max30102
import hrcalc
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import smbus

#lcd
import time
from RPLCD.i2c import CharLCD
lcd = CharLCD('PCF8574', 0x27, cols=20, rows=4)

# GPIO setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(15, GPIO.OUT)
GPIO.output(15, GPIO.LOW)

# RFID setup
rfid = SimpleMFRC522()

# Load the necessary kernel modules for the temperature sensor
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# Path to the temperature sensor
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

def read_temp_raw():
    """Read raw temperature data from the sensor."""
    with open(device_file, 'r') as f:
        lines = f.readlines()
    return lines

def read_temp():
    """Parse the raw temperature data and return the temperature in Celsius and Fahrenheit."""
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f
    
    
# Function to display heart rate and SpO2 on LCD
def display_on_lcd(hr, spo2,temp_c,temp_f=""):
    lcd.clear()  # Clear the display before writing
    # Write heart rate on the first line
    lcd.write_string(f"Heart Rate: {hr} bpm")
    lcd.cursor_pos = (1, 0)  # Move to the second line
    # Write SpO2 on the second line
    lcd.write_string(f"O(sub)2 Saturation: {spo2}%")
    lcd.cursor_pos = (2, 0) 
    lcd.write_string(f"Temperature: {temp_c:.2f} C")
    lcd.cursor_pos = (3, 0) 
    lcd.write_string(f"Temperature: {temp_f:.2f} F")
    
# Define the temperature range
TEMP_MIN = 38.0
TEMP_MAX = 39.10

# Heart rate and SpO2 ranges
HR_MIN = 60
HR_MAX = 100
SPO2_MIN = 95

# Timezone setup for IST
ist = pytz.timezone('Asia/Kolkata')

# AWS IoT details
ENDPOINT = "a2xnqgya26d77b-ats.iot.us-east-1.amazonaws.com"  # Replace with your AWS IoT endpoint
CLIENT_ID = "RaspberryPi"
TOPIC = "raspberrypi/sensor"

# Path to AWS certificates
CA_PATH = "/home/pi/LIVESTOCK/AmazonRootCA1.pem"
CERT_PATH = "/home/pi/LIVESTOCK/50d987c40db0cbede8e7350192bde11acd5efff2f0957022e29ed74689b92320-certificate.pem.crt"
PRIVATE_KEY_PATH = "/home/pi/LIVESTOCK/50d987c40db0cbede8e7350192bde11acd5efff2f0957022e29ed74689b92320-private.pem.key"

# Configure MQTT client
mqtt_client = AWSIoTMQTTClient(CLIENT_ID)
mqtt_client.configureEndpoint(ENDPOINT, 8883)
mqtt_client.configureCredentials(CA_PATH, PRIVATE_KEY_PATH, CERT_PATH)
mqtt_client.configureOfflinePublishQueueing(-1)  # Infinite offline publish queueing
mqtt_client.configureDrainingFrequency(2)  # Draining: 2 Hz
mqtt_client.configureConnectDisconnectTimeout(10)  # 10 sec
mqtt_client.configureMQTTOperationTimeout(5)  # 5 sec

# Connect to AWS IoT Core
mqtt_client.connect()
print("Connected to AWS IoT Core")

# Initialize MAX30102 sensor
m = max30102.MAX30102()

def read_sensor_data():
    """Reads heart rate and SpO2 data from the MAX30102 sensor."""
    red, ir = m.read_sequential()  # Read the red and IR data
    hr2 = 0
    sp2 = 0
    hr, hrb, sp, spb = hrcalc.calc_hr_and_spo2(ir, red)
    if hrb and hr != -999 and hr < 105:
        hr2 = int(hr)

    if spb and sp != -999 and sp < 100:
        sp2 = int(sp)

    return hr2, sp2

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
start_minute_time = time.time() 
last_print_time = time.time()  # Timer to display every 3 seconds

def publish_data():
    motion_start_time = None
    """Reads sensor data and publishes it to AWS IoT Core."""
    # Get the current date and time in IST
    current_time_ist = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\nDate and Time: {current_time_ist}")

    # Read temperature data
    temp_c, temp_f = read_temp()
    print(f"Temperature: {temp_c:.2f} C / {temp_f:.2f} F")

    # Initialize alert messages
    temperature_alert = ""
    heart_rate_alert = ""
    spo2_alert = ""
    motion_alert = ""

    # Check temperature range
    if temp_c < TEMP_MIN or temp_c > TEMP_MAX:
        temperature_alert = "Warning: Temperature is abnormal!"
        print(f"\033[1;31m{temperature_alert}\033[0m")

    # Read heart rate and SpO2 data
    heart_rate, spo2 = read_sensor_data()
    print(f"Heart Rate: {heart_rate} bpm")
    print(f"SpO2: {spo2}%")

    # Check heart rate range
    if heart_rate < HR_MIN or heart_rate > HR_MAX:
        heart_rate_alert = "Warning: Heart rate is out of normal range!"
        print(f"\033[1;31m{heart_rate_alert}\033[0m")

    # Check SpO2 range
    if spo2 < SPO2_MIN:
        spo2_alert = "Warning: SpO2 is below normal levels!"
        print(f"\033[1;31m{spo2_alert}\033[0m")

    # Read motion data
    global total_motion_duration, start_minute_time
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
            motion_start_time = None  # Reset motion start time

    if current_time - start_minute_time >= 60:
        print(f"Total motion duration so far: {total_motion_duration:.2f} seconds")

    # Every 1 minute
        if total_motion_duration < 45 or total_motion_duration > 55:
            motion_alert = "Alert: Motion duration outside of expected range!"
            
        start_minute_time = current_time
        total_motion_duration = 0

    #Prepare data payload
    data = {
        "timestamp": current_time_ist,
        "temperature_c": temp_c,
        "temperature_f": temp_f,
        "heart_rate": heart_rate,
        "spo2": spo2,
        "motion_duration": total_motion_duration,
        "alerts": {
            "temperature_alert": temperature_alert,
            "heart_rate_alert": heart_rate_alert,
            "spo2_alert": spo2_alert,
            "motion_alert": motion_alert
        }
    }

    # Convert data to JSON format
    message = json.dumps(data)

    # Publish the data to AWS IoT Core
    mqtt_client.publish(TOPIC, message, 1)
    print(f"Published: {message} to topic: {TOPIC}")
    time.sleep(3)

try:
    while True:
        
        # Read RFID tag
        id, text = rfid.read()
        print(f"RFID ID: {id}")

        # Check if the RFID ID matches the valid ID
        if str(id).strip() == "757628282329":
            print("Authorized RFID detected. Reading sensor data...")
            GPIO.output(15, GPIO.HIGH)  # Turn on LED
        # Publish and print data multiple times
        # Change this range to control how many times the data is printed
        while True:
            hr,spo2=read_sensor_data()
            temp_c,temp_f=read_temp()
            display_on_lcd(hr, spo2,temp_c,temp_f)
            
            publish_data()


            # Turn off the LED after reading
            #GPIO.output(15, GPIO.LOW)
        else:
            print("Unauthorized RFID. No data will be published.")
            GPIO.output(15, GPIO.LOW)  # Ensure LED is off

        # Small delay to avoid excessive polling
        time.sleep(3)

except KeyboardInterrupt:
    lcd.clear()  # Clear LCD display on exit
    GPIO.cleanup()  # Clean up GPIO on exit
    mqtt_client.disconnect()
    print("Disconnected from AWS IoT Core")


