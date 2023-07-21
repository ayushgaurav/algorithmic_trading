import os
import csv
import json
import math
import logging
import pdb
import sys
import time

import Common.Parameters as Parameters
from pprint import pprint
from kiteconnect import KiteConnect
from Executor.Executor import Executor, Action
from Utilities.logger import trades_logger
from Utilities.StocksInfo import StocksInfo
from Utilities.KiteCommands import *
from History.History import History


class InstrumentInfo:
    def __init__(self):
        self.tradingsymbol = None
        self.exchange = None
        self.budget = None
        self.tick_size = None
        self.last_price = None
        self.depth = None
        self.buy_quantity = None
        self.sell_quantity = None
        self.top5_buy_quantity = None
        self.top5_sell_quantity = None
        self.upper_circuit_limit = None
        self.lower_circuit_limit = None
        self.average_holding_price = 0  # Avg price of stocks in Holding
        self.holdings = 0
        self.t1_holdings = 0
        self.mode = 'M'  # 'M'/'A'
        self.day_buy_quantity = 0
        self.day_sell_quantity = 0
        self.day_buy_value = 0
        self.day_sell_value = 0
        self.str = ''

    def get_ideal_bid_price(self):
        # Ideal Bid price is the lowest price where it is possible to buy
        # Never BID at upper cicuit price (To avoid Trap)

        bought_first = 0
        bid_price = self.lower_circuit_limit
        for item in self.depth['buy']:
            bought_first += item['quantity']
            if bought_first >= self.sell_quantity:
                # bid_price is just enough to give me a chance to buy
                # TODO: (bought_first + buy_quantity) should be <= sell_quantity
                bid_price = round(item['price'] + self.tick_size, 2)
                bought_first -= item['quantity']
                break

        if bid_price >= self.upper_circuit_limit:
            bid_price = round(self.upper_circuit_limit - self.tick_size, 2)

            bought_first = 0
            for item in self.depth['buy']:
                if item['price'] >= bid_price:
                    bought_first += item['quantity']

        return bid_price, bought_first

    def get_ideal_ask_price(self):
        # Ideal Ask price is the highest price where it is possible to sell
        # Never ASK lower cicuit price (To avoid missing Bull run)

        sold_first = 0
        ask_price = self.upper_circuit_limit
        for item in self.depth['sell']:
            sold_first += item['quantity']
            if sold_first >= self.buy_quantity:
                # ask_price is just enough to give me a chance to sell
                # TODO: (sold_first + sell_quantity) should be <= buy_quantity
                ask_price = round(item['price'] - self.tick_size, 2)
                sold_first -= item['quantity']
                break

        if ask_price <= self.lower_circuit_limit:
            ask_price = round(self.lower_circuit_limit + self.tick_size, 2)

            sold_first = 0
            for item in self.depth['sell']:
                if item['price'] <= sold_first:
                    sold_first += item['quantity']

        return ask_price, sold_first


def _policy_A_manual(obj: InstrumentInfo):
    # A basic Manual policy

    action = Action(tradingsymbol=obj.tradingsymbol,
                    exchange=obj.exchange,
                    order_type=KiteConnect.ORDER_TYPE_LIMIT,
                    variety=KiteConnect.VARIETY_REGULAR,
                    product=KiteConnect.PRODUCT_CNC,
                    budget=obj.budget)
    action.transaction_type = None

    # pprint(json.dumps(obj.__dict__))
    if obj.sell_quantity > 0 and obj.buy_quantity > 0:

        buy_pressure = float(obj.top5_buy_quantity) / obj.sell_quantity
        sell_pressure = float(obj.top5_sell_quantity) / obj.buy_quantity
        if buy_pressure > Parameters.glob_pressure_threshold:
            action.price, obj.rank = obj.get_ideal_bid_price()
            action.transaction_type = KiteConnect.TRANSACTION_TYPE_BUY
        elif sell_pressure > Parameters.glob_pressure_threshold:
            action.price, obj.rank = obj.get_ideal_ask_price()
            action.transaction_type = KiteConnect.TRANSACTION_TYPE_SELL

    return action


class Analyzer:

    def __init__(self, kite: KiteConnect, manual_config_file):
        # Read file to get money limit per Instrument
        file_dir = os.path.dirname(os.path.realpath(__file__))
        self.manual_config_file = file_dir + '/../' + manual_config_file

        self.budget = {}
        self.instrument_map = {
            KiteConnect.EXCHANGE_NSE: {},
            KiteConnect.EXCHANGE_BSE: {}
        }
        self.kite = kite
        self.stocks_info = StocksInfo(kite, manual_config_file)
        self.history = History()

    def analyze(self, ticks):
        # TODO: Add more policies in future

        self.history.register_ticks(ticks)
        if self.stocks_info.manual_config_file_mtime != os.stat(self.stocks_info.manual_config_file).st_mtime:
            old_set = set(self.stocks_info.get_user_instrument_token_list())
            self.stocks_info.parse_manual_config_file()
            new_set = set(self.stocks_info.get_user_instrument_token_list())

            del_tokens = list(old_set.difference(new_set))
            add_tokens = list(new_set.difference(old_set))
            com_tokens = list(new_set.intersection(old_set))

            for token in del_tokens:
                del self.budget[token]

            for token in add_tokens:
                tradingsymbol, exchange = self.stocks_info.token_map[token]
                self.budget[token] = InstrumentInfo()
                self.budget[token].tradingsymbol = tradingsymbol
                self.budget[token].exchange = exchange
                self.budget[token].budget = self.stocks_info.stock_dict[exchange][tradingsymbol].budget
                self.budget[token].tick_size = self.stocks_info.stock_dict[exchange][tradingsymbol].tick_size
                self.budget[token].mode = self.stocks_info.stock_dict[exchange][tradingsymbol].mode

                for holding in self.stocks_info.holdings:
                    if holding['tradingsymbol'] == tradingsymbol and holding['exchange'] == exchange:
                        self.budget[token].average_holding_price = holding['average_price']
                        self.budget[token].holdings = holding['quantity']
                        self.budget[token].t1_holdings = holding['t1_quantity']
                        break

            for token in com_tokens:
                tradingsymbol, exchange = self.stocks_info.token_map[token]
                assert (token in self.budget.keys()), 'Invalid Token {}'.format(token)
                self.budget[token].budget = self.stocks_info.stock_dict[exchange][tradingsymbol].budget

        # Fetch current ownership of Instruments
        positions = self.kite.positions()
        for position in positions['day']:
            instrument_token = position['instrument_token']
            if instrument_token in self.budget.keys():
                self.budget[instrument_token].day_buy_quantity = position['day_buy_quantity']
                self.budget[instrument_token].day_sell_quantity = position['day_sell_quantity']
                self.budget[instrument_token].day_buy_value = position['day_buy_value']
                self.budget[instrument_token].day_sell_value = position['day_sell_value']

        actions = []
        for tick in ticks:
            instrument_token = tick['instrument_token']
            if instrument_token not in self.budget.keys():
                continue

            quote_input = self.budget[instrument_token].exchange + ':' + self.budget[instrument_token].tradingsymbol
            quote = KiteQuote(self.kite, [quote_input])
            while quote is None:
                time.sleep(0.5)
                quote = KiteQuote(self.kite, [quote_input])
            if quote_input not in quote.keys():
                trades_logger.error('Quote does not contain this instrument {}'.format(quote_input))
                return None

            self.budget[instrument_token].last_price = tick['last_price']
            self.budget[instrument_token].depth = tick['depth']
            self.budget[instrument_token].buy_quantity = tick['buy_quantity']
            self.budget[instrument_token].top5_buy_quantity = 0
            for buy_order in tick['depth']['buy']:
                self.budget[instrument_token].top5_buy_quantity += buy_order['quantity']
            self.budget[instrument_token].sell_quantity = tick['sell_quantity']
            self.budget[instrument_token].top5_sell_quantity = 0
            for sell_order in tick['depth']['sell']:
                self.budget[instrument_token].top5_sell_quantity += sell_order['quantity']
            self.budget[instrument_token].upper_circuit_limit = quote[quote_input]['upper_circuit_limit']
            self.budget[instrument_token].lower_circuit_limit = quote[quote_input]['lower_circuit_limit']
            # pprint(json.dumps(self.budget[instrument_token].__dict__))

            obj = self.budget[instrument_token]
            action = _policy_A_manual(obj)
            # Decide quantity here
            if action is not None:
                if action.transaction_type == self.kite.TRANSACTION_TYPE_BUY:
                    # You can not buy more than the given budget (including Holdings)
                    already_bought = ((obj.holdings + obj.t1_holdings) * obj.average_holding_price) + obj.day_buy_value
                    balance = obj.budget - already_bought
                    assert (action.price > 0.)
                    action.quantity = math.floor(balance / action.price)
                    if action.quantity <= 0:
                        continue
                    action.str = 'Buy {} {} LL:{} Bid:{} UL:{} Bought:Rs{} Bal:Rs{} BuyQ:{} Rank:{} M5BuyQ:{} ' \
                                 'MSellQ:{}'.format(obj.tradingsymbol, obj.exchange, obj.lower_circuit_limit,
                                                    action.price, obj.upper_circuit_limit, already_bought,
                                                    balance, action.quantity, obj.rank, obj.top5_buy_quantity,
                                                    obj.sell_quantity)

                elif action.transaction_type == self.kite.TRANSACTION_TYPE_SELL:
                    # TODO: Check if sale of t1_holding is allowed or not
                    max_sellable_quantity = (obj.holdings + obj.day_buy_quantity) - obj.day_sell_quantity
                    if max_sellable_quantity <= 0:
                        continue

                    already_sold = obj.day_sell_value
                    balance = obj.budget - already_sold
                    assert (obj.average_holding_price > 0.)
                    action.quantity = math.floor(balance / obj.average_holding_price)
                    action.quantity = min(action.quantity, max_sellable_quantity)
                    if action.quantity <= 0:
                        continue
                    action.str = 'Sell {} {} LL:{} Ask:{} UL:{} Sold:Rs{} Bal:Rs{} AvgBuy:Rs{} MaxSellQ={} ' \
                                 'SellQ:{} Rank:{} MBuyQ:{} M5SellQ:{}'.format(obj.tradingsymbol, obj.exchange,
                                                                               obj.lower_circuit_limit, action.price,
                                                                               obj.upper_circuit_limit,
                                                                               already_sold, balance,
                                                                               obj.average_holding_price,
                                                                               max_sellable_quantity, action.quantity,
                                                                               obj.rank, obj.buy_quantity,
                                                                               obj.top5_sell_quantity)
                else:
                    action.str = 'None {} {} MBuyQ:{} MSellQ:{}'.format(
                        obj.tradingsymbol, obj.exchange, obj.buy_quantity, obj.sell_quantity)

                actions.append(action)

        return actions


def Launch_Analyzer(kite: KiteConnect, queue, manual_config_file):
    max_queue_size = 3

    analyzer = Analyzer(kite, manual_config_file)
    executor = Executor(kite)

    try:
        while True:
            dropped_packets = 0
            while queue.qsize() > max_queue_size:
                queue.get()
                dropped_packets += 1

            if dropped_packets:
                print('Dropped {} packets'.format(dropped_packets))

            print('Waiting for Tick')
            ticks = queue.get()
            print('Processing Tick')
            actions = analyzer.analyze(ticks)
            for action in actions:
                if executor.execute(action):
                    print('Queued request to {} {}. Price={} TriggerPrice={} Quantity={} OrderType={} '
                          'Exchange={}'.format(action.transaction_type, action.tradingsymbol, action.price,
                                               action.quantity, action.trigger_price, action.order_type,
                                               action.exchange))
    except KeyboardInterrupt:
        analyzer.history.dump()
        sys.exit()
