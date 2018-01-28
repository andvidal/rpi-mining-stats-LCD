import stats
import datetime
import logging
import logging.handlers
import os

from lcd import (lcd_init,
                 lcd_string,
                 lcd_clear,
                 LCD_LINE_1,
                 LCD_LINE_2,
                 LCD_LINE_3,
                 LCD_LINE_4)


line_wait = {
    1: {
        0: 10,
        1: 5,
        2: 5,
    },
    2: {
        0: 5,
        1: 5,
        2: 5,
    },
    3: {
        0: 5,
        1: 5,
    },
    4: {
        0 : 5,
        1 : 3,
        2 : 3,
        3 : 3,
        4 : 3
    }
}
init_start = datetime.datetime.now()
line_state = {
    1: {'current_state': 0, 'current_timer': init_start},
    2: {'current_state': 0, 'current_timer': init_start},
    3: {'current_state': 0, 'current_timer': init_start},
    4: {'current_state': 0, 'current_timer': init_start}
}


def update_line_states():
    current_time = datetime.datetime.now()
    for line in line_wait.keys():
        current_state = line_state[line]['current_state']
        if (datetime.datetime.now() - line_state[line]['current_timer']).seconds >= line_wait[line][current_state]:
            current_state = current_state +1 if (current_state +1) in line_wait[line].keys() else 0
            line_state[line]['current_state'] = current_state
            line_state[line]['current_timer'] = current_time


def get_logger():
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-14.14s] [%(levelname)-5.5s]    %(message)s")
    abs_log_dir = os.path.join( os.path.dirname(os.path.realpath(__file__)), 'logs')
    log_filename = os.path.join(abs_log_dir,"log.txt")

    if os.path.exists(abs_log_dir) is False:
            os.makedirs(abs_log_dir)

    logger = logging.getLogger('LCD')
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(log_filename, maxBytes=50*1024, backupCount=100)
    file_handler.setFormatter(logFormatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logFormatter)
    logger.addHandler(console_handler)

    logger.addHandler(file_handler)

    return logger


def main():
    logger = get_logger()
    lcd_init()
    logger.info("LCD Initialized")

    try:
        status = stats.Stats(logger)
    except Exception as e:
        logger.exception("Leaving... could not create stats object")


    while True:
        try:
            # LINE 1
            if line_state[1]['current_state'] == 0:
                lcd_string("Mining Stats v1",LCD_LINE_1,2)
            elif line_state[1]['current_state'] == 1:
                lcd_string("Started {}/{} {}:{} ".format(init_start.day, init_start.month, str(init_start.hour).zfill(2), str(init_start.minute).zfill(2)),LCD_LINE_1,2)
            elif line_state[1]['current_state'] == 2:
                time_diff = datetime.datetime.now() - init_start
                last_checked_hours = time_diff.seconds//3600
                last_checked_minutes = (time_diff).seconds // 60 % 60
                lcd_string("Up {}d {}h{}m{}s".format( time_diff.days,
                                                    str(last_checked_hours).zfill(2),
                                                    str(last_checked_minutes).zfill(2),
                                                    str(time_diff.seconds%60).zfill(2) ),LCD_LINE_1,2)



            # LINE 2
            if 'chip_temp' in status.stats:
                if line_state[2]['current_state'] == 0:
                    lcd_string("Chip " + chr(223) + "{} {} {} {} " .format(    *status.stats['chip_temp'].values() ), LCD_LINE_2, 2)
                elif line_state[2]['current_state'] == 1:
                    lcd_string("PCB " + chr(223) + "{} {} {} {} " .format(    *status.stats['pcb_temp'].values() ), LCD_LINE_2, 2)
                elif line_state[2]['current_state'] == 2:
                    lcd_string("G5s {}|Gav {}" .format(    round( float(status.stats['miner_speed']['GHS 5s']), 1), round( float(status.stats['miner_speed']['GHS av']),1) ), LCD_LINE_2, 2)
            else:
                lcd_string("!! NO TEMPS AVAIL !!", LCD_LINE_2, 2)



            # LINE 3
            if line_state[3]['current_state'] == 0:
                ip_addr = status.stats['miner_ip']
                if ip_addr is None:
                    lcd_string("!! MINER NOT FOUND !!", LCD_LINE_3, 2)
                else:
                    time_diff = datetime.datetime.now() - status.stats['miner_ip_last_checked']
                    last_checked_minutes = (time_diff).seconds // 60 % 60
                    lcd_string(str(ip_addr) + " ({}:{})".format(last_checked_minutes, str(time_diff.seconds%60).zfill(2)), LCD_LINE_3, 2)
            elif line_state[3]['current_state'] == 1:
                if status.stats['ambient_temp']:
                    time_diff = datetime.datetime.now() - status.stats['ambient_last_checked']
                    lcd_string( "{}".format(status.stats['ambient_temp']) +
                                             chr(223) + "C | " +
                                            "{}%".format(status.stats['ambient_humidity']) +
                                            " ({}s)".format(time_diff.seconds), LCD_LINE_3, 2)
                else:
                    lcd_string("Ambient Temp Not avail",LCD_LINE_3, 2)



            # LINE 4
            btc_eur_rate = status.stats['btc_eur_rate']
            ltc_eur_rate = status.stats['ltc_eur_rate']
            engine = status.stats['engine']
            if engine in ["nicehash", "mininpoolhub"]:
                eur_rate = btc_eur_rate
                displayed_cryptocurrency = "BTC"
            elif engine == "litecoinpool":
                eur_rate = ltc_eur_rate
                displayed_cryptocurrency = "LTC"

            if line_state[4]['current_state'] == 0:
                if engine == "auto":
                    lcd_string("Balance N/A", LCD_LINE_4, 2)
                else:
                    balance_num = status.stats['balance']
                    if balance_num:
                        balance_num = round(balance_num, 7)
                    eur_balance = eur_rate*balance_num if (eur_rate and balance_num) else 0
                    lcd_string("{}{} [{}E]".format(balance_num, displayed_cryptocurrency, round(eur_balance,1)), LCD_LINE_4, 2)
            elif line_state[4]['current_state'] == 1:
                if engine == "auto":
                    lcd_string("Detecting pool...", LCD_LINE_4, 2)
                else:
                    lcd_string("{}".format(status.stats['engine']), LCD_LINE_4, 2)
            elif line_state[4]['current_state'] == 2:
                if engine == "auto":
                    lcd_string("Rate N/A", LCD_LINE_4, 2)
                else:
                    btc_day = status.stats['btc_day']
                    eur_day = btc_day*eur_rate if (btc_day and eur_rate) else 0
                    lcd_string("{} {}/d[{}E]".format(btc_day,displayed_cryptocurrency,    round(eur_day,2)), LCD_LINE_4, 2)
            elif line_state[4]['current_state'] == 3:
                lcd_string("1BTC = {}eur".format(int(btc_eur_rate)), LCD_LINE_4, 2)
            elif line_state[4]['current_state'] == 4:
                lcd_string("1LTC = {}eur".format(int(ltc_eur_rate)), LCD_LINE_4, 2)


            update_line_states()
        except Exception as e:
                logger.exception("Leaving... Error while refreshing LCD")
                break

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        lcd_clear()