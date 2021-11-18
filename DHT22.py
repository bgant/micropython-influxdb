'''
Brandon Gant
Created: 2020-10-05

DHT22 temperature/humidity sensor (any GPIO pin should work)
'''

import dht
from machine import Pin

# Measurements should be at a minimum about 2 seconds apart 

def read_sensor(gpio_pin_number,scale='c'):
    sensor = dht.DHT22(Pin(gpio_pin_number))
    sensor.measure()
    if scale.lower() is 'c':
        return sensor.temperature(), sensor.humidity()  # Celsius
    elif scale.lower() is 'f':
        return sensor.temperature() * 9/5 + 32, sensor.humidity()  # Fahrenheit
    else:
        print('Unknown Temperature Scale')
