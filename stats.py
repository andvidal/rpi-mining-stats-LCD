import requests
import time
from socket import *
import threading, Queue
import json
import datetime
import miner_perf
import os
import dht11

class Stats:
    def __init__(self, logger):
        self.configs = json.load(open( os.path.join( os.path.dirname(os.path.realpath(__file__)), 'config.json')))

        self.stats = {
            'balance' : None,
            'miner_ip': None,
            'miner_ip_last_checked': None,
            'btc_day': None,
            'btc_eur_rate': None,
            'ltc_eur_rate': None,
            'ambient_temp': None,
            'ambient_humidity': None,
            'ambient_last_checked': None,
            'engine' : self.configs['mining_engine']
        }
        self.logger = logger

        if self.stats['engine'] != 'auto':
            self.logger.info("Not using engine detector. Starting balance thread with engine: '{}'".format(self.stats['engine']))
            threading.Thread(target=self.refresh_balance, name='BalanceThread').start()
        else:
            self.logger.info("Starting engine detector thread because 'engine' is set to '{}'".format(self.stats['engine']))
            threading.Thread(target=self.engine_guesser, name='EngineGuesserThread').start()
        threading.Thread(target=self.miner_heartbeat, name='MinerHeartbeat').start()
        threading.Thread(target=self.bitcoin_price ,name='CryptoPrices').start()
        threading.Thread(target=self.external_temp_and_humidity, name='TempHumidity').start()

    def parse_nicehash_balance(self, response_result):
        balance = float(response_result['result']['stats'][0]['balance'])
        if 'payments' in response_result:
            for past_payment in response_result['payments']:
                balance+=float(past_payment['amount'])

        return balance

    def parse_litecoinpool_balance(self, response_result):
        return float(response_result['user']['unpaid_rewards'])

    def parse_miningpoolhub_balance(self, response_result):
        return float(response_result['getuserallbalances']['data'][0]['confirmed'])

    def engine_guesser(self):
        urls = [
                (self.configs['nicehash_api'], self.parse_nicehash_balance, 'nicehash' ),
                (self.configs['litecoinpool_api'], self.parse_litecoinpool_balance, 'litecoinpool'),
                (self.configs['miningpoolhub_api'], self.parse_miningpoolhub_balance, 'miningpoolhub')
                ]
        balances = [[None]*len(urls), [None]*len(urls)]
        balance_thread = threading.Thread(target=self.refresh_balance, name='BalanceThread')
        started = False

        try:
            while True:
                for (idx, (url, parser, engine)) in enumerate(urls):
                    try:
                        r = requests.get(url)
                        response_result = r.json()
                    except:
                        self.logger.warning("Could not get balance for {}".format(engine))
                        balances[0][idx] = None
                        balances[1][idx] = None
                        continue
                    balance = parser(response_result)
                    if None in balances[0]:
                        balances[0][idx] = balance
                    else:
                        balances[1][idx] = balance
                        diff = balances[1][idx] - balances[0][idx]
                        if diff > 0:
                            balances = [[None]*len(urls), [None]*len(urls)]
                            if started is False:
                                self.logger.info('Detected work on {}. Updating settings and starting balance thread.'.format(engine))
                                with threading.Lock():
                                    self.configs['mining_engine'] = engine
                                    self.stats['engine'] = engine
                                balance_thread.start()
                                started=True
                            else:
                                if (engine != self.stats['engine']):
                                    self.logger.info('Started doing work on a different service! {} is no longer used and has been swapped by {}. '
                                                'Updating settings. [diff={}]'.format(self.stats['engine'], engine, diff))
                                    with threading.Lock():
                                        self.configs['mining_engine'] = engine
                                        self.stats['engine'] = engine
                                        self.balances_queue.queue.clear()
                time_sleep = 30 if started is False else 30*60
                self.logger.info('Wainting {} secs before checking balances again'.format(time_sleep))
                time.sleep(time_sleep)
        except:
            self.logger.exception("Error in engine guesser thread")

    def bitcoin_price(self):
        try:
            time_check_interval = self.configs['crypto_price_check_interval']
            while True:
                try:
                    bitcoin_price_request = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json")
                    btc_eur_rate= bitcoin_price_request.json()['bpi']['EUR']['rate_float']
                    self.logger.info("Refreshed BTC rate. 1 BTC = {} eur".format(btc_eur_rate))
                except Exception as e:
                    self.logger.error("Could not get bitcoin rate: {}".format(e))

                try:
                    litecoin_price_request = requests.get("https://api.coinmarketcap.com/v1/ticker/litecoin/?convert=EUR")
                    ltc_eur_rate= float(litecoin_price_request.json()[0]['price_eur'])
                    self.logger.info("Refreshed LTC rate. 1 LTC = {} eur".format(ltc_eur_rate))
                except Exception as e:
                    self.logger.error("Could not get litecoin rate: {}".format(e))

                with threading.Lock():
                    self.stats['btc_eur_rate'] = btc_eur_rate
                    self.stats['ltc_eur_rate'] = ltc_eur_rate
                time.sleep(time_check_interval)
        except:
            self.logger.exception("Error in crypto prices thread")


    def refresh_balance(self):
        try:

            balances_history_size = 10
            self.balances_queue = Queue.Queue(balances_history_size)

            while True:
                if self.configs['mining_engine'] == "nicehash":
                    url = self.configs['nicehash_api']
                elif self.configs['mining_engine'] == "litecoinpool":
                    url = self.configs['litecoinpool_api']
                elif self.configs['mining_engine'] == "miningpoolhub":
                    url = self.configs['miningpoolhub_api']


                balance_not_avail = True
                while balance_not_avail is True:
                    try:
                        r = requests.get(url)
                        response_result = r.json()
                        if self.configs['mining_engine'] == "nicehash":
                            latest_balance = self.parse_nicehash_balance(response_result)
                            self.logger.info("Got new BTC balance: {}BTC (nicehash)".format(latest_balance))
                        elif self.configs['mining_engine'] == "litecoinpool":
                            latest_balance = self.parse_litecoinpool_balance(response_result)
                            self.logger.info("Got new LTC balance: {}LTC (litecoinpool)".format(latest_balance))
                        elif self.configs['mining_engine'] == "miningpoolhub":
                            latest_balance = self.parse_miningpoolhub_balance(response_result)
                            self.logger.info("Got new BTC balance (mining pool hub): {}BTC".format(latest_balance))

                        balance_not_avail = False

                    except:
                        self.logger.exception("Could not refresh mining balance. ")
                        balance_not_avail = True
                        time.sleep( self.configs['balance_check_interval'] )

                current_time = datetime.datetime.now()
                oldest_balance, _ = self.balances_queue.queue[0] if (self.balances_queue.qsize() > 0) else (None,None) #workaround, just in case the balance is updated very slowly (miningpoolhub)
                if (self.balances_queue.qsize() < balances_history_size ) or ((self.balances_queue.qsize() >= balances_history_size) and (oldest_balance != latest_balance)):
                    if self.balances_queue.qsize() < balances_history_size:
                        previous_balance = None
                    else:
                        previous_balance, previous_balance_timestamp = self.balances_queue.get()
                        if latest_balance < previous_balance: #if there was a cashout, start estimating from scratch
                            self.balances_queue.queue.clear()
                            previous_balance = None
                            self.logger.info("There was a cashout, because most the recent balance ({}) is lower than"
                                             "first balance in the queue ({}).Estimation has been reset.".format(latest_balance, previous_balance))


                    self.balances_queue.put( (latest_balance, current_time ) )

                    rate = None
                    if previous_balance:
                        balances_diff = latest_balance - previous_balance
                        time_diff = (current_time - previous_balance_timestamp).seconds
                        rate = round(balances_diff * 3600*24/time_diff, 4)
                        self.logger.info("Refreshed rate per day: {}".format(rate))
                    else:
                        self.logger.info("Rate per day not yet available.")



                    with threading.Lock():
                        self.stats['balance'] = latest_balance
                        self.stats['btc_day'] = rate
                else:
                    if oldest_balance == latest_balance:
                        self.logger.info("Rate has not been refreshed, because the most recent balance ({}) is the same as the"
                                         " first balance in the queue ({}). Lileky slow refreshment rate.".format(latest_balance, self.balances_queue.queue[0][0]))

                time.sleep( self.configs['balance_check_interval'] )
        except:
            self.logger.exception("Error in balances thread")

    def external_temp_and_humidity(self):
        dht11_pin = 2
        dht = dht11.DHT11(pin=dht11_pin)
        self.logger.info("DHT11 Module Init..")
        time.sleep(2)

        while True:
            if True:

                result = dht.read()
                if result.is_valid():
                    self.logger.info("Got ambient temperature and humidity: {}C | {}%".format(result.temperature, result.humidity))
                    with threading.Lock():
                        self.stats['ambient_temp'] = result.temperature
                        self.stats['ambient_humidity'] = result.humidity
                        self.stats['ambient_last_checked'] = datetime.datetime.now()
            time.sleep( self.configs['ambient_temp_interval'] )

    def miner_heartbeat(self):
        try:
            network = self.configs['subnet']
            sleep_secs = self.configs['miner_heartbeat_interval']

            while True:
                found_ip = False
                for ip in range(2,256):
                    addr = network + str(ip)
                    s = socket(AF_INET, SOCK_STREAM)
                    s.settimeout(0.01)
                    is_connected = False
                    if not s.connect_ex((addr,22)):
                        s.close()
                        is_connected = True
                    else:
                        s.close()


                    if is_connected:
                        miner_performance_getter = miner_perf.MinerPerf(addr)
                        performance = miner_performance_getter.get()
                        with threading.Lock():
                            self.stats['miner_ip'] = addr
                            self.stats['miner_ip_last_checked'] = datetime.datetime.now()
                            if performance:
                                self.stats.update(performance)
                        found_ip = True
                        self.logger.info("Found miner ip in {}. Checking again in {} secs".format(addr, sleep_secs))
                        break
                if found_ip is False:
                    self.logger.error("Could not find miner in subnet: {} Retrying in 5 secs".format(self.configs['subnet']))
                    with threading.Lock():
                        self.stats['miner_ip'] = None
                        self.stats['miner_ip_last_checked'] = datetime.datetime.now()

                    time.sleep(5)
                else:
                    time.sleep(sleep_secs)
        except:
            self.logger.exception("Error miner heartbeat thread")
