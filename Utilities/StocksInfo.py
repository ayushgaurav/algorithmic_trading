import os
from kiteconnect import KiteConnect


class StockInfo:
    def __init__(self):
        self.instrument_token = None
        self.budget = None
        self.tick_size = None
        self.mode = None


class StocksInfo:
    def __init__(self, kite: KiteConnect, manual_config_file):
        file_dir = os.path.dirname(os.path.realpath(__file__))
        stock_dict = {
            KiteConnect.EXCHANGE_NSE: {},
            KiteConnect.EXCHANGE_BSE: {}
        }

        self.kite = kite
        self.stock_dict = stock_dict            # Info of tracked Instruments
        self.manual_config_file = file_dir + '/../' + manual_config_file
        self.manual_config_file_mtime = None

        self.holdings = self.kite.holdings()

        self.token_map = {}                     # Maps instrument_token to [tradingsymbol, exchange]
        self.instruments = []                   # Populating NSE, BSE instruments
        for instrument in self.kite.instruments():
            if instrument['exchange'] in [kite.EXCHANGE_NSE, kite.EXCHANGE_BSE]:
                self.instruments.append(instrument)
                self.token_map[instrument['instrument_token']] = [instrument['tradingsymbol'], instrument['exchange']]

    def parse_manual_config_file(self):
        # Read file to get money limit per Instrument

        if self.manual_config_file_mtime != os.stat(self.manual_config_file).st_mtime:
            self.manual_config_file_mtime = os.stat(self.manual_config_file).st_mtime

        with open(self.manual_config_file, 'r') as file:
            lines = file.readlines()

        for line in lines[1:]:
            split_line = line.split(',')  # [tradingsymbol, exchange, budget]
            tradingsymbol = split_line[0]
            exchange = split_line[1]
            budget = split_line[2]
            mode = split_line[3]

            if line[0] == '#':
                tradingsymbol = tradingsymbol[1:].strip()
                if tradingsymbol in self.stock_dict[exchange].keys():
                    del self.stock_dict[exchange][tradingsymbol]
            elif tradingsymbol in self.stock_dict[exchange].keys():
                self.stock_dict[exchange][tradingsymbol].budget = float(budget)
                self.stock_dict[exchange][tradingsymbol].mode = mode
            else:
                self.stock_dict[exchange][tradingsymbol] = StockInfo()
                for instrument in self.instruments:
                    if instrument['tradingsymbol'] == tradingsymbol and instrument['exchange'] == exchange:
                        self.stock_dict[exchange][tradingsymbol].instrument_token = instrument['instrument_token']
                        self.stock_dict[exchange][tradingsymbol].budget = float(budget)
                        self.stock_dict[exchange][tradingsymbol].tick_size = instrument['tick_size']
                        self.stock_dict[exchange][tradingsymbol].mode = mode
                        break
                # TODO: What if the symbol is not found ???

    def get_user_instrument_token_list(self):
        token_list = []
        for exchange in self.stock_dict.keys():
            for tradingsymbol in self.stock_dict[exchange].keys():
                token_list.append(self.stock_dict[exchange][tradingsymbol].instrument_token)
        return token_list


