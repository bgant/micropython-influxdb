'''
Brandon Gant
Created: 2019-12-18
Updated: 2020-09-24

temp_celsius = (millivolts - 500) / 10  # Example: 25C = (750mV - 500) / 10
temp_fahrenheit = (temp_celsius * 9/5) + 32

Calibration Data:
   According to Datasheet:
        750mV should be  25C /  77F 
        100mV should be -40C / -40F 
   Long Probe measured datapoints:
       AnalogDevices_TMP36.temp_calibrated(32,1350,1702,59.7,82.5)
   Short Probe measured datapoints:
       AnalogDevices_TMP36.temp_calibreated(32,1430,1784,59.5,74.3)
'''

from sys import exit
from machine import ADC
from uos import uname
from time import sleep


def read_adc(gpio_pin_number):
    '''Read the Raw ADC value one time'''
    if 'esp32' in uname().sysname:
        # Source: https://docs.micropython.org/en/latest/esp32/quickref.html#adc-analog-to-digital-conversion
        from machine import Pin
        adc = ADC(Pin(gpio_pin_number)) # Pins 32-39 are valid
        adc.atten(ADC.ATTN_6DB)         # 0-2V since the TMP36 data pin is min 0.1V and max 1.75V
        adc.width(ADC.WIDTH_12BIT)      # 0-4095 values
        # millivolts = average_adc * (2000/4095)  # Example: 750mV = 1535.6 * (2000/4095)
    elif 'esp8266' in uname().sysname:
        adc = ADC(0)  # gpio_pin_number is ignored since there is only one ADC on ESP8266
        # ADC values from 0 to 1023
        # millivolts = average_adc * (3300/1023)  # Example: 750mV =  232.5 * (3300/1023)
    else:
        print('unknown hardware')
        exit(1)
    return adc.read()


def read_adc_average(gpio_pin_number):
    '''Multiple rapid ADC readings dropping high/low values and averaging remaining'''
    adc_sample = []
    for x in range(80):
        adc_sample.append(read_adc(gpio_pin_number))
        sleep(0.01)
    remove_high_low = sorted(adc_sample)[20:-20]
    adc_average = sum(remove_high_low) / len(remove_high_low)
    return adc_average


def read_millivolts(gpio_pin_number):
    '''Calculate the voltage based on the ADC reading'''
    return read_adc_average(gpio_pin_number) * (2000/4095)  # 2000mV Max / 4095 ADC Max


def read_temp(gpio_pin_number,scale='f'):
    temp_celsius = (read_millivolts(gpio_pin_number) - 500) / 10  # Example: 25C = (750mV - 500) / 10
    temp_fahrenheit = (temp_celsius * 9/5) + 32
    if scale.lower() is 'f':
        return temp_fahrenheit
    elif scale.lower() is 'c':
        return temp_celsius
    else:
        print('unknown temperature scale')
        exit(1)


# Source: https://www.arduino.cc/reference/en/language/functions/math/map/
def range_map(x, in_min, in_max, out_min, out_max):
    '''Python equivalent to Arduino map() function.'''
    return (x-in_min) * (out_max-out_min) / (in_max-in_min) + out_min


def temp_calibrated(gpio_pin_number,adc_min,adc_max,temp_min,temp_max):
    '''Use external accurate Temperature device to measure high/low ADC and Temperature values to calibrate sensor.'''
    return range_map(read_adc_average(gpio_pin_number),in_min=adc_min,in_max=adc_max,out_min=temp_min,out_max=temp_max)

