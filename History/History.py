import os
import json
import datetime


class History:
    # FileName: Date_Token
    # DateTime: LastPrice, BuyQ[5], TBuyQ, SellQ[5], TSellQ

    def __init__(self):
        self.history = {}
        self.dump_folder = os.path.dirname(os.path.realpath(__file__)) + '/Records/'
        if not os.path.isdir(self.dump_folder):
            os.mkdir(self.dump_folder)

    def register_ticks(self, ticks):
        for tick in ticks:
            instrument_token = tick['instrument_token']
            if instrument_token not in self.history.keys():
                self.history[instrument_token] = []

            self.history[instrument_token].append(tick)

    def dump(self):
        today = datetime.date.today()
        for token in self.history.keys():
            filename = today.strftime('%m-%d-%Y') + '_{}.csv'.format(token)
            with open(self.dump_folder + filename, 'a') as file:
                file.write('\n')

                ticks = self.history[token]
                for tick in ticks:
                    row = [tick['timestamp'], tick['last_price'], tick['average_price'], tick['volume'],
                           tick['buy_quantity'], tick['sell_quantity'], tick['ohlc']['low'], tick['ohlc']['high']]
                    for order in tick['depth']['buy']:
                        row.append(order['quantity'])
                        row.append(order['price'])
                        row.append(order['orders'])
                    for order in tick['depth']['sell']:
                        row.append(order['quantity'])
                        row.append(order['price'])
                        row.append(order['orders'])

                    file.write(','.join(map(str, row)) + '\n')


if __name__ == '__main__':
    _ticks = [{'average_price': 0.0,
               'buy_quantity': 0,
               'change': -1.3412816691505196,
               'depth': {'buy': [{'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0}],
                         'sell': [{'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0}]},
               'instrument_token': 11,
               'last_price': 6.62,
               'last_quantity': 0,
               'mode': 'full',
               'ohlc': {'close': 6.71, 'high': 6.8, 'low': 6.5, 'open': 6.66},
               'oi': 0,
               'oi_day_high': 0,
               'oi_day_low': 0,
               'sell_quantity': 0,
               'timestamp': datetime.datetime(2021, 5, 21, 16, 0, 1),
               'tradable': True,
               'volume': 0},
              {'average_price': 0.0,
               'buy_quantity': 0,
               'change': 6.661379857256151,
               'depth': {'buy': [{'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0}],
                         'sell': [{'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0}]},
               'instrument_token': 11,
               'last_price': 134.5,
               'last_quantity': 0,
               'mode': 'full',
               'ohlc': {'close': 126.1, 'high': 136.0, 'low': 128.0, 'open': 128.8},
               'oi': 0,
               'oi_day_high': 0,
               'oi_day_low': 0,
               'sell_quantity': 0,
               'timestamp': datetime.datetime(2021, 5, 21, 16, 0, 1),
               'tradable': True,
               'volume': 0},
              {'average_price': 0.0,
               'buy_quantity': 0,
               'change': 2.4482109227871884,
               'depth': {'buy': [{'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0},
                                 {'orders': 0, 'price': 0.0, 'quantity': 0}],
                         'sell': [{'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0},
                                  {'orders': 0, 'price': 0.0, 'quantity': 0}]},
               'instrument_token': 12,
               'last_price': 27.2,
               'last_quantity': 0,
               'mode': 'full',
               'ohlc': {'close': 26.55, 'high': 27.4, 'low': 26.9, 'open': 27.25},
               'oi': 0,
               'oi_day_high': 0,
               'oi_day_low': 0,
               'sell_quantity': 0,
               'timestamp': datetime.datetime(2021, 5, 21, 16, 0, 1),
               'tradable': True,
               'volume': 0}]

    history = History()
    history.register_ticks(_ticks)
    history.dump()
