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

def publish_data():
    """Reads sensor data and publishes it to AWS IoT Core."""
    last_check_time = time.time()

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

    # Prepare data payload
    data = {
        "ID":757628282329,
        "timestamp": current_time_ist,
        "temperature_c": temp_c,
        "temperature_f": temp_f,
        "heart_rate": heart_rate,
        "spo2": spo2,
        "alerts": {
            "temperature_alert": temperature_alert,
            "heart_rate_alert": heart_rate_alert,
            "spo2_alert": spo2_alert
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
            
            # Keep LED on for a few seconds after reading
            #time.sleep(3)
            #GPIO.output(15, GPIO.LOW)  # Turn off LED

            while True:                
                # Publish data to AWS
                publish_data()
                
                
        else:
            print("Unauthorized RFID No data will be published.")
            GPIO.output(15, GPIO.LOW)  # Ensure LED is off

        # Small delay to avoid excessive polling
        time.sleep(3)

except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on exit
    mqtt_client.disconnect()
    print("Disconnected from AWS IoT Core")
