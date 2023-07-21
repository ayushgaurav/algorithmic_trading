import re
import os
import pdb
import logging
import time
from pprint import pprint
from kiteconnect import KiteTicker, KiteConnect
from Utilities.StocksInfo import StocksInfo
from Utilities.logger import TRADES_LOG_FILE
from multiprocessing import Process, Queue
from Analyzer.Analyzer import Launch_Analyzer

logging.basicConfig(level=logging.DEBUG)

# TODO: Analyze interaction between UserTrades and AlgoTrades
# TODO: Launch set of Analyzers, each in separate Process
# TODO: Launch Executor in separate Process
# TODO: Automatically discover Potential stocks to trade
# TODO: Update Algo's Profit/Loss at the end of day
# TODO: At max one Buy/Sell per Instrument in a Day
# TODO: Before Buy/Sell verify that you are allowed to do that
# TODO: A separate utility to call Kite APIs. This is to manage exceptions at one place.
'''
TODO: Handle this error
kiteconnect.exceptions.InputException: This stock is traded in [periodic call auction for illiquid securities](https://support.zerodha.com/category/trading-and-markets/trading-faqs/articles/periodic-call-auction). The fifth session of periodic call auction is open from 1.30 PM to 2.15 PM. Place your orders in this window.
kiteconnect.exceptions.InputException: Order cannot be cancelled as it is being processed. Try later.
urllib3.exceptions.ReadTimeoutError: HTTPSConnectionPool(host='api.kite.trade', port=443): Read timed out. (read timeout=7)

File "/home/agaurav/PycharmProjects/AlgoTrading/Analyzer/Analyzer.py", line 166, in analyze
    quote = self.kite.quote([quote_input])
requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='api.kite.trade', port=443): Read timed out. (read timeout=7)

'''
# https://docs.python.org/3/library/multiprocessing.html
# https://stackoverflow.com/questions/11515944/how-to-use-multiprocessing-queue-in-python
# https://blog.muya.co.ke/configuring-multiple-loggers-python/

# TODO: Keep them in a File
api_key = 'x5gp1v3ua5s47zm3'
api_secret = 't73uxlbv627phq4wz4hvca2a3gngbe5v'
kite = KiteConnect(api_key=api_key)

# print(kite.login_url())
# exit(0)

# request_token = 'Y6TilnBs6ugOSaJWtUIwvtsKPQoTnWUK'
# data = kite.generate_session(request_token, api_secret=api_secret)
# pprint(data)
# os.system('rm ' + TRADES_LOG_FILE)
# exit(0)

access_token = 'zF07RlRnd3CrPjAdMeXVysbRa2HAcePX'
kite.set_access_token(access_token)
try:
    profile = kite.profile()
    print('Welcome {}'.format(profile['user_name']))
except Exception as e:
    print('Incorrect Access Key {}'.format(e.__class__))
    exit(1)


def get_KiteTicker(token_list, pqueue):
    global api_key, access_token

    kws = KiteTicker(api_key, access_token)

    def on_ticks(ws, ticks):
        pqueue.put(ticks)
        # logger.info('Received Tick')

    def on_connect(ws, response):
        ws.subscribe(token_list)
        ws.set_mode(ws.MODE_FULL, token_list)

    def on_close(ws, code, reason):
        ws.stop()

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close

    return kws


def TickerManager(pqueue, manual_config_file):
    stocks_info = StocksInfo(kite, manual_config_file)
    stocks_info.parse_manual_config_file()
    token_list = stocks_info.get_user_instrument_token_list()
    kws = get_KiteTicker(token_list, pqueue)
    kws.connect(threaded=True)

    while True:
        if stocks_info.manual_config_file_mtime != os.stat(stocks_info.manual_config_file).st_mtime:
            old_token_list = stocks_info.get_user_instrument_token_list()
            stocks_info.parse_manual_config_file()
            new_token_list = stocks_info.get_user_instrument_token_list()

            old_set = set(old_token_list)
            new_set = set(new_token_list)

            del_tokens = list(old_set.difference(new_set))
            add_tokens = list(new_set.difference(old_set))

            if del_tokens:
                kws.unsubscribe(del_tokens)
            if add_tokens:
                kws.subscribe(add_tokens)
                kws.set_mode(kws.MODE_FULL, add_tokens)

        time.sleep(1)
        # TODO: This process can be used to explore new stocks


def main():
    manual_config_file = 'ManualInput.csv'
    pqueue = Queue()

    # TickerManager(pqueue)
    p_ticker = Process(target=TickerManager, args=(pqueue, manual_config_file, ))
    p_ticker.start()

    Launch_Analyzer(kite, pqueue, manual_config_file)


main()
