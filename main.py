'''
Brandon Gant
Created: 2020-06-09
Updated: 2021-11-15

### Tested with:
    Espressif ESP32-PICO-KIT_V4.1 board with ESP32-PICO-D4 chip 
    SparkFun Thing
    TinyPICO

### Sensors:
    Milone Standard eTape assembly / 18-inch / Voltage divider / PN 12110215TC-AH
    Analog Devices TMP36
    SparkFun TMP102
    DHT22

### Software Installation on Linux:
mkdir ~/micropython-setup
cd ~/micropython-setup

python3 -m pip install pyvenv
python3 -m venv micropython-env
source micropython-env/bin/activate
python3 -m pip list | egrep -v "Package|----" | awk '{print $1}' | xargs -I {} python3 -m pip install --upgrade {}
python3 -m pip install esptool
python3 -m pip install mpremote
sudo usermod -aG `stat -c "%G" /dev/ttyUSB0` $USER  <-- May need to reboot PC
mpremote connect /dev/ttyUSB0                       <-- test connection / Ctrl-] to exit

wget https://micropython.org/resources/firmware/tinypico-20210902-v1.17.bin
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 tinypico-20210902-v1.17.bin

wget https://github.com/micropython/micropython-lib/raw/master/python-ecosys/urequests/urequests.py
mpremote u0 cp urequests.py :   <-- ESP32 has this module built-in but TinyPICO does not

git clone https://github.com/bgant/micropython-wifi
cd micropython-wifi/
mpremote u0 cp key_store.py :
mpremote u0 cp client_id.py :
mpremote u0 cp TinyPICO_RGB.py :
mpremote u0 cp boot.py :
mpremote u0 <-- to enter REPL
from machine import reset
reset()
<enter your Wifi SSID and Password and make sure it connects>
<if you made a mistake run import key_store and key_store.init() to change SSID and Password>
<Ctrl+] to exit REPL>

cd ../
git clone https://github.com/bgant/micropython-influxdb
cd micropython-influxdb/
mpremote u0 cp Milone_eTape.py :   <--  AnalogDevices_TMP36.py / SparkFun_TMP102.py / DHT22.py
mpremote u0 cp main.py :

mpremote u0  <-- to enter REPL
reset()   <-- boot.py and main.py should run
'''


#-----------------
# Import Modules
#-----------------

# Built-in Modules
from machine import reset, WDT
from time import sleep
from uos import uname, listdir
from sys import exit
import gc

wdt = WDT(timeout=600000)  # Set 10-minute Hardware Watchdog Timer

# A chance to hit Ctrl+C in REPL for Debugging
print('main.py: Press CTRL+C to enter REPL...')
print()
sleep(2)

# Downloaded Modules
import urequests
import key_store
from client_id import client_id

# Utilize LED if available
if 'TinyPICO' in uname().machine:
    import TinyPICO_RGB as led
    led.off()


#------------------------------------------------------------------
# Get InfluxDB server:port:database:measurement from key_store.db
#   i.e. influxdb.localdomain:8086:Garage:DHT22
#------------------------------------------------------------------
if key_store.get('influxdb') is None:
    print('Need to add settings to key_store.db...')
    key_store.set('influxdb', input('Enter InfluxDB server:port:database:measurement - '))
server,port,database,measurement = key_store.get('influxdb').split(':')

# Get Sleep Interval from key_store.db
if key_store.get('sleep_interval') is None:
    key_store.set('sleep_interval', input('How many seconds between sensor reads - '))
sleep_interval = int(key_store.get('sleep_interval')) 

# Set URL for Database Writes
if '443' in port:
    url = 'https://%s/influx/write?db=%s' % (server,database)
else:
    url = 'http://%s:%s/write?db=%s' % (server,port,database)

# Set JSON Web Token (JWT) from key_store.db
#
# If you enabled authentication in InfluxDB you need
# to create a JSON Web Token to write to a database:
#
#    https://www.unixtimestamp.com/index.php
#        Create a future Unix Timestamp expiration   
#
#    https://jwt.io/#debugger-io
#        HEADER
#            {
#              "alg": "HS256",
#              "typ": "JWT"
#             }
#        PAYLOAD
#            {
#              "username": "<InfluxDB username with WRITE to DATABASE>",
#              "exp": <Unix Timestamp expiration>
#            }
#        VERIFY SIGNATURE
#            HMACSHA256(
#              base64UrlEncode(header) + "." +
#              base64UrlEncode(payload),
#              <shared secret phrase set in InfluxDB>
#            )
#
# Source: https://docs.influxdata.com/influxdb/v1.8/administration/authentication_and_authorization/
#
headers = {
    'Content-type': 'application/x-www-form-urlencoded',
    'Authorization': ''
}
if key_store.get('jwt') is None:
    print('JSON Web Token can be blank if InfluxDB does not use authentication') 
    key_store.set('jwt', input('Enter JSON Web Token (JWT) - '))
headers['Authorization'] = 'Bearer %s' % key_store.get('jwt')


#--------------------------------------------------------------
# Create database if it does not already exist
#    WARNING: This only works without InfluxDB authentication
#--------------------------------------------------------------
if key_store.get('jwt') is '':
    def create_database():
        # Using a function to avoid overwriting variables above with same names
        if '443' in port:
            url = 'https://%s/query' % (server)
        else:
            url = 'http://%s:%s/query' % (server,port)
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        data = 'q=SHOW DATABASES'
        response = urequests.post(url,headers=headers,data=data)
        if not database in response.text:
            print('Creating Database: %s' % (database))
            data = 'q=CREATE DATABASE "%s"' % (database)  # DROP DATABASE to remove
            response = urequests.post(url,headers=headers,data=data)
        else:
            print('Using Database: %s' % (database))
    create_database()
    print()


#-----------------------------
# Which Sensor are we using?
#-----------------------------
if key_store.get('SENSOR_PIN') is None:
    key_store.set('SENSOR_PIN', input('Enter Sensor Pin Number - '))
SENSOR_PIN = int(key_store.get('SENSOR_PIN'))

if 'Milone_eTape.py' in listdir():
    sensor = 'Milone eTape Water Level'
    import Milone_eTape  # Pin Number 32 hard-coded in module
    def read_sensor():
        return "%s,device=%s inches=%.1f" % (measurement, client_id, Milone_eTape.inches())

elif 'SparkFun_TMP102.py' in listdir():
    sensor = 'SparkFun TMP102 Temperature'
    import SparkFun_TMP102
    def read_sensor():
        return "%s,device=%s fahrenheit=%.1f" % (measurement, client_id, SparkFun_TMP102.read_temp('F')) 

elif 'DHT22.py' in listdir():
    sensor = 'DHT22 Temperature and Humidity'
    import DHT22
    def read_sensor():
        temp,humidity = DHT22.read_sensor(SENSOR_PIN,'F')
        return "%s,device=%s fahrenheit=%.1f,humidity=%.1f" % (measurement, client_id, temp, humidity)

elif 'AnalogDevices_TMP36.py' in listdir():
    sensor = 'Analog Devices TMP36 Temperature'
    import AnalogDevices_TMP36
    # Calibrate TMP36 Sensor?
    if key_store.get('tmp36') is None:
        print('This field can be blank to use read sensor without calibration')
        key_store.set('tmp36', input('Enter adc_min:adc_max:temp_min:temp_max - '))
    if key_store.get('tmp36') is '':  # Blank string
        def read_sensor():
            return "%s,clientid=%s fahrenheit=%.1f" % (measurement, client_id, AnalogDevices_TMP36.read_temp(int(SENSOR_PIN)))
    else:
        adc_min,adc_max,temp_min,temp_max = key_store.get('tmp36').split(':')
        def read_sensor():
            return "%s,clientid=%s fahrenheit=%.1f" % (measurement, client_id, AnalogDevices_TMP36.temp_calibrated(int(SENSOR_PIN),int(adc_min),int(adc_max),float(temp_min),float(temp_max)))

else:
    print('Missing Sensor Module... Exiting main.py')
    print()
    wdt = WDT(timeout=86400000)  # Watchdog Timer cannot be disabled, so set to expire in 1 day
    exit(1)


#----------------------------------
# Print some helpful information:
#----------------------------------
print()
print('Sensor:          %s' % sensor)
print('Sensor Pin:      %s' % SENSOR_PIN)
print('Read Interval:   %s seconds' % sleep_interval)
print('Client ID:       %s' % client_id)
print('InfluxDB Server: %s:%s' % (server,port))
print('Database Name:   %s' % database)
print('Measurement:     %s' % measurement)
print()
print('=' * 45)
print()


#-------------------
# Define Functions
#-------------------

def main():
    gc.collect()  # Loop runs device out of memory without this
    #print('Free Memory: %sKB' % int(gc.mem_free()/1024)) 

    # Send the Data to Server
    data = read_sensor()
    print(data)
    response = urequests.post(url,headers=headers,data=data)
    if '204' in str(response.status_code):  # HTTP Status 204 (No Content) indicates server fulfilled request
        print('InfluxDB write: Success')
        print()
        if 'TinyPICO' in uname().machine:
            led.blink(0,255,0,ms=2500,i=1) # Green
    else:
        print('InfluxDB write: Failed (%s)' % (response.status_code))
        if 'TinyPICO' in uname().machine:
            led.solid(255,127,0)  # Orange
        sleep(sleep_interval)
        reset()

#------------
# Main Loop
#------------

while True:
    try:
        main()
        wdt.feed()  # Reset Hardware Watchdog Timer
        sleep(sleep_interval)
    except KeyboardInterrupt:
        wdt = WDT(timeout=86400000)  # Watchdog Timer cannot be disabled, so set to expire in 1 day
        exit()
    except:
        sleep(sleep_interval)
        reset()

