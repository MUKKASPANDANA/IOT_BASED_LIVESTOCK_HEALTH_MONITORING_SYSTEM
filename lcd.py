import time
from RPLCD.i2c import CharLCD

# Configure your LCD, ensure your I2C address is correct
# Address is typically 0x27 or 0x3F. Run `sudo i2cdetect -y 1` to find the address.
lcd = CharLCD('PCF8574', 0x27, cols=20, rows=4)

try:
    # Clear the display
    lcd.clear()
    
    # Write to LCD
    lcd.write_string('Hello, World!')

    # Move to next line after 2 seconds
    time.sleep(2)
    lcd.cursor_pos = (1, 0)  # Row 1, Col 0
    lcd.write_string('This is line 2')
    
    time.sleep(5)
    
finally:
    # Clear the display when finished
    lcd.clear()
