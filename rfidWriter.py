import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.OUT)
GPIO.output(22,GPIO.LOW)

rfid= SimpleMFRC522()
while True:
    try:
        # Read RFID tag
        id, text = rfid.read()
        print(id)

        # Check if the RFID ID matches the valid ID
        if str(id).strip() =="757628282329":
            GPIO.output(22, GPIO.HIGH)  # Turn on LED
            time.sleep(5)  # Keep LED on for 10 seconds
            GPIO.output(22, GPIO.LOW)  # Turn off LED
        else:
            GPIO.output(22, GPIO.LOW)  # Ensure LED is off
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Small delay to avoid excessive polling
        time.sleep(10)