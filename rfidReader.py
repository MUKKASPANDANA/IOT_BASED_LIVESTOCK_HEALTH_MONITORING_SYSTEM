import RPi.GPIO as GPIO
GPIO.setwarnings(False)
from mfrc522 import SimpleMFRC522
rfid=SimpleMFRC522()
while True:
    id, text= rfid.read()
    print(id)
    print(text)