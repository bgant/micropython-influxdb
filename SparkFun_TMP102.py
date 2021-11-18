'''
SparkFun TMP102:      https://www.sparkfun.com/products/13314
SparkFun ESP32 Thing: https://www.sparkfun.com/products/13907
MicroPython:          https://docs.micropython.org/en/latest/
Source Tutorial:
   https://learn.sparkfun.com/tutorials/micropython-programming-tutorial-getting-started-with-the-esp32-thing

Brandon Gant
Created: 2019-02-11

Usage:
   import SparkFun_TMP102 as tmp102
   tmp102.read_temp()
   tmp102.read_temp('F')
   tmp102.reset()

This module just gets a reading from the temperature sensor.
'''

import machine

# Pin Definitions - There is only one I2C bus on the ESP32
sda_pin = machine.Pin(21)
scl_pin = machine.Pin(22)

# Create an I2C object out of the SDA and SCL pin objects
i2c = machine.I2C(sda=sda_pin, scl=scl_pin)

# Scan the I2C bus for device addresses
i2c_addresses = i2c.scan()

# TMP102 address on the I2C bus (set by manufacturer)
tmp102_address = 0x48

if tmp102_address not in i2c_addresses:
    raise Exception('No TMP102 device found on the I2C bus')

# TMP102 register addresses
reg_temp = 0x00
reg_config = 0x01


# Calculate the 2's complement of a number
def twos_comp(val, bits):
    if (val & (1 << (bits -1))) !=0:
        val = val - (1 << bits)
    return val


# Read temperature registers and calculate Celsius
def read_temp(scale='C'):  # Defaults to [C]elsius

    # Read temperature registers
    val = i2c.readfrom_mem(tmp102_address, reg_temp, 2)
    celsius = (val[0] << 4) | (val[1] >> 5)

    # Covert to 2's complement (temperatures can be negative)
    celsius = twos_comp(celsius, 12)

    # Convert registers value to temperature (C)
    celsius = celsius * 0.0625

    # Outputs Celius by default, but you can specify other scales
    if scale.lower() == 'c':
        return celsius
    elif scale.lower() == 'f':
        fahrenheit = (celsius * 9/5) + 32 
        return fahrenheit
    elif scale.lower() == 'k':
        kelvin = celsius + 273.15
        return kelvin
    else:
        print("valid values are [C]elsius, [F]ahrenheit, or [K]elvin")


# Reset TMP102 configuration settings
def reset():

    # Read CONFIG register (2 bytes) and convert to list
    val = i2c.readfrom_mem(tmp102_address, reg_config, 2)
    val = list(val)
    print("Old CONFIG:", val, [bin(x) for x in val])

    # Set to 4Hz sampling (CR1, CR0 = 0b10)
    val[1] = val[1] & 0b00111111
    val[1] = val[1] | (0b10 << 6)

    # Write 4Hz sampling back to CONFIG
    i2c.writeto_mem(tmp102_address, reg_config, bytearray(val))

    # Check that new config is in place
    val = i2c.readfrom_mem(tmp102_address, reg_config, 2)
    val = list(val)
    print("New CONFIG:", val, [bin(x) for x in val])

