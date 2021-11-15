# Sending Micropython data to InfluxDB

After setting up a some sensors and doing data collection first with MQTT and later with custom Python Flask HTTP calls, I settled on sending the data to an InfluxDB time series database so that I could view the data in pretty Grafana graphs.

These scripts are my initial attempt at coming up with a way to send the sensor data in a common InfluxDB format.

![Image](images/micropython-analog-devices-tmp36.png)
