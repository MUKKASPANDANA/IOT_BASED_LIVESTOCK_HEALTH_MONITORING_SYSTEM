import time
from RPLCD.i2c import CharLCD
import RPi.GPIO as GPIO
import max30102
import hrcalc

# Initialize the I2C LCD (make sure the I2C address is correct for your setup)
lcd = CharLCD('PCF8574', 0x27, cols=20, rows=4)

# Initialize MAX30102 sensor
print("[INFO] Initializing MAX30102 sensor")
m = max30102.MAX30102()

hr2 = 0
sp2 = 0

# Define the ranges for heart rate and SpO2
#HR_MIN = 60
#HR_MAX = 100
#SPO2_MIN = 98

# Function to display heart rate and SpO2 on LCD
def display_on_lcd(hr, spo2=""):
    lcd.clear()  # Clear the display before writing
    # Write heart rate on the first line
    lcd.write_string(f"HR: {hr} bpm")
    lcd.cursor_pos = (1, 0)  # Move to the second line
    # Write SpO2 on the second line
    lcd.write_string(f"SpO2: {spo2}%")
    
    #if alert_message:
        #lcd.cursor_pos = (0, 0)  # Move to the first line
        #lcd.write_string(alert_message)  # Display the alert message

try:
    while True:
        # Read data from the MAX30102 sensor
        red, ir = m.read_sequential()
        hr, hrb, sp, spb = hrcalc.calc_hr_and_spo2(ir, red)

        # Process heart rate and SpO2 values
        if hrb and hr != -999 and hr < 105:
            hr2 = int(hr)

        if spb and sp != -999 and sp < 100:
            sp2 = int(sp)

        # Check the ranges and prepare alert messages
        #alert_message = ""
        #if hr2 < HR_MIN or hr2 > HR_MAX:
            #alert_message += "HR Alert! "
        #if sp2 < SPO2_MIN:
            #alert_message += "SpO2 Alert!"

        # Display both heart rate and SpO2 simultaneously on the LCD with alerts
        print(f"Heart Rate: {hr2} bpm, SpO2: {sp2}%")
        display_on_lcd(hr2, sp2)

        # Sleep for a while to avoid excessive CPU usage
        time.sleep(3)

except KeyboardInterrupt:
    print("Program terminated")

finally:
    lcd.clear()  # Clear LCD display on exit
    GPIO.cleanup()  # Clean up GPIO on exit
