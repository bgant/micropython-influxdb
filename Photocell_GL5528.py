'''
Brandon Gant
Created: 2020-08-11
Updated: 2020-09-09
'''

from machine import Pin,ADC
from time import sleep

bright = ADC(Pin(38))  #  1K voltage divider resistor
dark = ADC(Pin(37))    # 51K voltage divider resistor

bright.atten(ADC.ATTN_11DB)
bright.width(ADC.WIDTH_12BIT)

dark.atten(ADC.ATTN_11DB)
dark.width(ADC.WIDTH_12BIT)

while True:
    print("%s    %s" % (bright.read(),dark.read()))
    sleep(1)
