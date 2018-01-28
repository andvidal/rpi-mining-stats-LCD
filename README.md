# About

This repository allows to display crypto currencies mining stats on a 20 Characters x 4 Lines LCD Display using a Raspberry Pi (I'm using a Pi 1 Model B, but should work on the most recent models as well). It was specifically made for a Bitmain ASIC miner. However, it should be straightforward to support other platforms, such as GPU rigs, so feel free to contribute! It was initially developed for nicehash only, but later two more mining pools have been added. 
[Here's how it looks like in action](https://i.imgur.com/MgarjIc.gif)

# Features

Each line of the LCD displays different metrics:
  - **Line 1:** 
    - Welcome text
    - Start date & hour
    - Uptime
  - **Line 2:**
    - ASIC chip temperatures
    - ASIC PCB temperatures
    > **Note:** In my case I have 4 temperatures for each line, which is different for each type of miner.
  - **Line 3:**
    - Miner LAN ip
    - Room temperature & humidity (using a DHT11 sensor, see below)
    > **Note:** My Rpi is also serving as an AP to the miner. So that the miner has access to the internet, the Rpi has a wifi dongle and then runs a dhcp server to be used by the miner. This ip refers to the ip of the miner in this dhcp server.
  - **Line 4:**
    - Current balance 
    - Current pool
    - Current rate: btc/day (or ltc/day, depending on the pool in use) and eur/day
    - BTC/EUR rate
    - LTC/EUR rate
    > **Note:** The rate/day is calculated by this program, i.e. it doesn't use any other estimator that the pools normally provide.



# Wiring
Wiring the LCD and temperature/humidity sensors is relatevly simple. I didn't want to reinvent the wheel and deal with low-level firmware to control these devices, so I used 3rd party guides/code as much as possible.

##### LCD
I relied heavily on this [guide](https://www.raspberrypi-spy.co.uk/2012/08/20x4-lcd-module-control-using-python/). I simplified the code slightly and put everything on [lcd.py](lcd.py). I used the exact pinout as mentioned in this article, but that can easily be changed (check top of the file)

##### DHT11 - Humidity and Temperature Sensor
This sensor is very cheap and servers its purpose really well (you can find it on ebay about €1). I used some code a user posted on the [Raspberry Pi Forum](https://www.raspberrypi.org/forums/viewtopic.php?f=32&t=69427&sid=2fe65603b2a6a54879cb1da5756b7d7f&start=25#p1173387). I connected data pin 2 of the sensor to GPIO pin 2 (via a pullup resistor to VCC). The pinout of the sensor is as follows:

<img src="http://embedded-lab.com/blog/wp-content/uploads/2012/07/DHT11_Pins.png" width="200">

The [dht11.py](dht11.py) file available here is exactly as posted by the user. 

> **Note:** If you don't have one, the program still runs, you simply don't have that information :)


# Dependencies
 - [Raspian Os](https://www.raspberrypi.org/downloads/) - I'm using Raspbian Stretch Lite version 2017-09-07. I haven't tried but other OSes should work too.
 - python 2.7 (pre-installed on raspian)
 - python requests library:


    sudo apt-get update 
    sudo apt-get install python-requests
 This should be enough, but if there's anything missing, check the  [requirements.txt](requirements.txt) file
 
 # Configuration
 Edit the [config.json](config.json) file with the details of your pool (e.g. replace <YOUR_BTC_ADDRESS> with your nicehash btc address on the "nicehash_api" line). If your only interested in nicehash you can ignore the other APIs.
 
 > **Note:** If you use more than one pool, such as miningpoolhub and nicehash, you don't have to tell the system which pool you are currently mining on. By setting ` "mining_engine": "auto" ` the program  automatically detects which pool you are currently mining on by checking if there's an increase in balance in one of the configured pools. However, it will take longer to see the balance on the LCD after starting the program. If you only care about one pool, simply replace ` "mining_engine" ` to the pool you are mining on, e.g. ` "mining_engine": "nicehash" `.
 
 
 # Run
 - Copy all the files to your Pi to a directory of your choice
  - To start:


    python main.py

- Ideally you'd want to run in daemon mode:


    nohup python ~/LCD/main.py >/dev/null 2>&1 &
    
    
Logs will be created inside a folder called "logs".
