import os
import re
import sys
import math
from pprint import pprint
from multiprocessing import Queue
from kiteconnect import KiteConnect, KiteTicker

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + '/..')
import Common.Parameters as Parameters


def get_KiteTicker(api_key, access_token, token_list, pqueue):
    kws = KiteTicker(api_key, access_token)

    def on_ticks(ws, ticks):
        pqueue.put(ticks)

    def on_connect(ws, response):
        ws.subscribe(token_list)

    def on_close(ws, code, reason):
        ws.stop()

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close

    return kws


class Explorer:
    def __init__(self, api_key, access_token, kite, pqueue):
        self.kite = kite
        self.pqueue = pqueue
        self.kws = get_KiteTicker(api_key, access_token, [], pqueue)
        self.kws.connect(threaded=True)
        self.last_subscription = []

        self.stock_dict = {
            KiteConnect.EXCHANGE_NSE: [],
            KiteConnect.EXCHANGE_BSE: []
        }

        self.token_map = {}  # Maps instrument_token to [tradingsymbol, exchange]
        for instrument in self.kite.instruments():
            if instrument['exchange'] in [kite.EXCHANGE_NSE, kite.EXCHANGE_BSE]:
                if instrument['instrument_type'] == 'EQ':
                    if re.search('-', instrument['tradingsymbol']) or re.search('\d', instrument['tradingsymbol']):
                        # TODO: This condition is excluding some valid stocks like 'BAJAJ-AUTO'
                        continue
                    self.stock_dict[instrument['exchange']].append(instrument['instrument_token'])
                    self.token_map[instrument['instrument_token']] = [instrument['tradingsymbol'],
                                                                      instrument['exchange']]

    def _subscribe(self, tokens):
        self.kws.subscribe(tokens)
        # self.kws.set_mode(self.kws.MODE_QUOTE, tokens)
        self.last_subscription = tokens

    def _unsubscribe(self, tokens):
        self.kws.unsubscribe(tokens)
        self.last_subscription = []

    def explore(self):
        batch = 500
        actions = {
            KiteConnect.EXCHANGE_NSE: {},
            KiteConnect.EXCHANGE_BSE: {}
        }

        for exchange in self.stock_dict.keys():
            num_stocks = len(self.stock_dict[exchange])
            for itr in range(math.ceil(num_stocks / batch)):
                beg = itr * batch
                end = min((itr + 1) * batch, num_stocks)
                batch_stocks = self.stock_dict[exchange][beg:end]
                self._unsubscribe(self.last_subscription)
                while self.pqueue.qsize() > 0:
                    self.pqueue.get()
                self._subscribe(batch_stocks)

                print('Hi', exchange, beg, end, len(batch_stocks))
                count = 0
                NUM_COUNT = 1
                while count < NUM_COUNT:
                    count += 1
                    ticks = self.pqueue.get()
                    for tick in ticks:
                        if 'buy_quantity' not in tick.keys() or 'sell_quantity' not in tick.keys():
                            continue
                        instrument_token = tick['instrument_token']
                        buy_quantity = tick['buy_quantity']
                        sell_quantity = tick['sell_quantity']
                        if buy_quantity > 0 and sell_quantity > 0:
                            buy_pressure = float(buy_quantity) / sell_quantity
                            sell_pressure = float(sell_quantity) / buy_quantity

                            if buy_pressure > Parameters.glob_pressure_threshold:
                                tradingsymbol, _ = self.token_map[instrument_token]
                                actions[exchange][tradingsymbol] = [buy_pressure, 'B']
                            elif sell_pressure > Parameters.glob_pressure_threshold:
                                tradingsymbol, _ = self.token_map[instrument_token]
                                actions[exchange][tradingsymbol] = [sell_pressure, 'S']

        self._unsubscribe(self.last_subscription)

        for exchange in actions.keys():
            quote_tokens = []
            for tradingsymbol in actions[exchange].keys():
                quote_tokens.append(exchange + ':' + tradingsymbol)

            num_stocks = len(quote_tokens)
            for itr in range(math.ceil(num_stocks / batch)):
                beg = itr * batch
                end = min((itr + 1) * batch, num_stocks)
                batch_stocks = quote_tokens[beg:end]

                quotes = self.kite.quote(batch_stocks)
                for quote_input in quotes.keys():
                    last_price = quotes[quote_input]['last_price']
                    if last_price <= 0.:
                        del actions[exchange][quote_input.split(':')[-1]]
                        continue
                    lower_circuit_limit = quotes[quote_input]['lower_circuit_limit']
                    upper_circuit_limit = quotes[quote_input]['upper_circuit_limit']
                    potential = (upper_circuit_limit - last_price) / last_price
                    actions[exchange][quote_input.split(':')[-1]].append(potential)

        demand_nse = [[k, v] for k, v in
                      sorted(actions[KiteConnect.EXCHANGE_NSE].items(), key=lambda item: item[1][0], reverse=True)]
        demand_bse = [[k, v] for k, v in
                      sorted(actions[KiteConnect.EXCHANGE_BSE].items(), key=lambda item: item[1][0], reverse=True)]

        print('******  NSE', len(actions[KiteConnect.EXCHANGE_NSE].items()))
        demand_nse_buy = list(filter(lambda s: s[1][1] == 'B', demand_nse))
        demand_nse_buy = sorted(demand_nse_buy, key=lambda s: s[1][2], reverse=True)
        pprint(demand_nse_buy[:10])

        print('******  BSE', len(actions[KiteConnect.EXCHANGE_BSE].items()))
        demand_bse_buy = list(filter(lambda s: s[1][1] == 'B', demand_bse))
        demand_bse_buy = sorted(demand_bse_buy, key=lambda s: s[1][2], reverse=True)
        pprint(demand_bse_buy[:10])

        # Add selected stocks in Manual Config file


if __name__ == '__main__':
    from kiteconnect import KiteConnect

    _api_key = 'x5gp1v3ua5s47zm3'
    _api_secret = 't73uxlbv627phq4wz4hvca2a3gngbe5v'
    _access_token = 'z0NKzoKYJBuZrPdA0kaO1FS9jtEpcL5e'
    _kite = KiteConnect(api_key=_api_key)
    _kite.set_access_token(_access_token)

    _pqueue = Queue()
    _exp = Explorer(_api_key, _access_token, _kite, _pqueue)
    _exp.explore()
