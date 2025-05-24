import max30102
import hrcalc

import os
import glob
import time
from datetime import datetime
import pytz


# Load the necessary kernel modules
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# Path to the temperature sensor
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'




m = max30102.MAX30102()

hr2 = 0
sp2 = 0



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

# ANSI escape codes for styling
RED_BOLD = '\033[1;31m'
RESET = '\033[0m'

# Timezone setup for IST
ist = pytz.timezone('Asia/Kolkata')

# Initial time setup for periodic range checking
last_check_time = time.time()

# Print the introductory statement once
print("Monitoring temperature...")




while True:
    red, ir = m.read_sequential()
    
    hr,hrb,sp,spb = hrcalc.calc_hr_and_spo2(ir, red)

    print("hr detected:",hrb)
    print("sp detected:",spb)
    
    
    # Read and display the current temperature
    temp_c, temp_f = read_temp()
    # Get current time in IST for display
    current_time_ist = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{current_time_ist}] Temperature: {temp_c:.2f} C and {temp_f:.2f} F")

    # Get the current time
    current_time_seconds = time.time()
    
    
    
    
    
    
    if(hrb == True and hr != -999):
        hr2 = int(hr)
        print("Heart Rate : ",hr2)
    if(spb == True and sp != -999):
        sp2 = int(sp)
        print("SPO2       : ",sp2)
        
        
        
        
    # Check if it is time to perform a range check
    if current_time_seconds - last_check_time >= 60:  # 60 seconds = 1 minute
        if temp_c < TEMP_MIN or temp_c > TEMP_MAX:
            print(f"{RED_BOLD}Warning: Temperature is abnormal!{RESET}")
        # Update the last check time
        last_check_time = current_time_seconds

    # Sleep for a short interval before the next temperature measurement
    time.sleep(3)  # Adjust the interval as needed
        