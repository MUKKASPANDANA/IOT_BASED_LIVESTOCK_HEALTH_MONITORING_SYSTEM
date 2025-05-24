import RPi.GPIO as GPIO
import max30102
import hrcalc
import time

# Set up GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(18, GPIO.IN)

# Initialize MAX30102
print("[INFO] MAX30102 Channel & I2C Address.")
m = max30102.MAX30102()

hr2 = 0
sp2 = 0

# Flag to alternate between heart rate and oxygen saturation
toggle_display = True

try:
    while True:
        if GPIO.input(18) == 0:
            # Read data from the sensor
            red, ir = m.read_sequential()
            hr, hrb, sp, spb = hrcalc.calc_hr_and_spo2(ir, red)

            if hrb and hr != -999 and hr < 105:
                hr2 = int(hr)

            if spb and sp != -999 and sp < 100:
                sp2 = int(sp)

            # Alternate the display between heart rate and oxygen saturation
            if toggle_display:
                print("Heart Pulse Rate    : {} bpm".format(hr2))
            else:
                print("Oxygen Saturation   : {}%".format(sp2))

            # Toggle the flag for the next iteration
            toggle_display = not toggle_display

        # Sleep for a while to avoid excessive CPU usage
        time.sleep(1)

except KeyboardInterrupt:
    print("Program terminated")

finally:
    GPIO.cleanup()

