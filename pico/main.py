# Bibliotheken laden
from machine import Pin, I2C, ADC
from time import sleep, sleep_ms
from onewire import OneWire
from ds18x20 import DS18X20
from pico_i2c_lcd import I2cLcd
import network
import socket
import time
import ntptime
from umqtt.simple import MQTTClient
import gc

#wifi credentials
ssid='UPC3915714'
password='fpF8ctsuccHp'

#basic connection test
#led_onboard = Pin("LED", Pin.OUT)
#for i in range(2):
#    led_onboard.on()
#    sleep(1)
#    led_onboard.off()
#    sleep(1)

#Initialize wifi
#http://www.hivemq.com/demos/websocket-client/
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
time.sleep(10)
print(wlan.isconnected())

#Initialize mqtt connection
mqtt_server = 'broker.hivemq.com'
mqtt_server = "2617098e38f84eaa9f31afa1df7c8952.s1.eu.hivemq.cloud"
client_id = 'jackys_id'
topic_pub = b'Wormbox'

#Initialize fan
fan_on = "fan_off"

ntptime.settime()

def sub_cb(topic_re, msg):
    msg = msg.decode('utf-8')
    global fan_on
    if msg == "fan_on":
        fan_on = "fan_on"
    if msg == "fan_off":
        fan_on = "fan_off"

def connectMQTT():
    """
    Connect to MQTT Server
    """
    client = MQTTClient(client_id=b"jackys_id",
    server=b"2617098e38f84eaa9f31afa1df7c8952.s1.eu.hivemq.cloud",
    port=0,
    user=b"jackycolamitice",
    password=b"!fS;r3sQrp9.~-+v~oSQH\G,&~0G3BK/",
    keepalive=7200,
    ssl=True,
    ssl_params={'server_hostname':'2617098e38f84eaa9f31afa1df7c8952.s1.eu.hivemq.cloud'}
    )
    client.connect()
    return client

#Initialize MQTT client
client = connectMQTT()
client.set_callback(sub_cb)    

#Initialize temperature sensors
#DS18B20
sensor_soil= DS18X20(OneWire(Pin(18)))
device_soil = sensor_soil.scan()
sensor_air = DS18X20(OneWire(Pin(16)))
device_air = sensor_air.scan() 
sensor_out = DS18X20(OneWire(Pin(20)))
device_out = sensor_out.scan()
print(device_soil, device_air, device_out)


#Initialize display
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
I2C_ADDR = i2c.scan()[0]
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)

#Initialize manual fan on/off switch
switch = Pin(19, mode=Pin.OUT)

#Initialize humidity sensor
hum_sensor = ADC(Pin(26))
hum_list = []

while True:
    if not wlan.isconnected():
        wlan.active(True)
        wlan.connect(ssid, password)
        time.sleep(60)
        try:
            time.sleep(0.5)
            client = connectMQTT()
            time.cleep(1)
            client.set_callback(sub_cb)
        except:
            continue

    time.sleep(1)

    #read humidity
    hum_list.append(hum_sensor.read_u16())
    if len(hum_list)>50: hum_list.pop(0)
    humidity = int(sum(hum_list)/len(hum_list))
    
    #read temperatures
    sensor_soil.convert_temp()
    sensor_air.convert_temp()
    sensor_out.convert_temp()
    t_soil = float(sensor_soil.read_temp(device_soil[0]))
    t_air = float(sensor_air.read_temp(device_air[0]))
    t_out = float(sensor_out.read_temp(device_out[0]))
    
    #print temperatures to display
    try:
        lcd.putstr("Ts, Ta, To [C]\n")
        lcd.putstr("%1.1f, %1.1f, %1.1f\n"%(t_soil, t_air, t_out))  
    except:
        continue
    

    #publish information to MQTT Server
    try:
        year, month, mday, hour, minute, second, weekday, yearday = time.localtime() 
        #client.publish(topic_pub, "%02d:%02d:%02d: T soil = %1.1f C, T air = %1.1f C, T out = %1.1f C"%(hour, minute, second,t_soil, t_air, t_out))
        #client.publish(topic_pub, "%02d:%02d:%02d: Humidity = %i"%(hour-2, minute, second, humidity))
        client.publish(b"latest_update", "%02d:%02d:%02d"%(hour+2, minute, second))
        client.publish(b"T_soil", "%1.1f C"%t_soil)
        client.publish(b"T_air", "%1.1f C"%t_air)
        client.publish(b"T_out", "%1.1f C"%t_out)
        client.publish(b"Humidity", "%i"%(humidity))
        client.subscribe("Fan")
    except:
        client = connectMQTT()
        client.set_callback(sub_cb)
        time.sleep(5)

    if fan_on=="fan_on":
        switch.value(1)
    if fan_on=="fan_off":
        switch.value(0)
            
    #sleep whole while loop
    time.sleep(5)
    


