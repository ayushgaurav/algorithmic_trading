import re
import pdb
import logging
import time
from pprint import pprint
from kiteconnect import KiteConnect
from Utilities.logger import trades_logger
from Utilities.KiteCommands import *


# TODO: Do not Buy and Sell on the same day. Transact within given Day Limit.
# TODO: Executor must inform Analyzer about the list of Products that Executor will stop trading for the day


class Action:
    def __init__(self, tradingsymbol=None, exchange=None, order_type=None, transaction_type=None, quantity=None,
                 variety=None, price=0, trigger_price=0, budget=None, product=KiteConnect.PRODUCT_CNC):
        self.tradingsymbol = tradingsymbol  # 'CIPLA'
        self.exchange = exchange  # KiteConnect.EXCHANGE_NSE
        self.order_type = order_type  # KiteConnect.ORDER_TYPE_MARKET
        # TODO: Add support for "Hold". This will cancel any placed orders.
        self.transaction_type = transaction_type  # KiteConnect.TRANSACTION_TYPE_BUY
        self.quantity = quantity  # 1
        self.variety = variety  # KiteConnect.VARIETY_AMO
        self.product = product  # KiteConnect.PRODUCT_CNC
        self.price = price
        self.trigger_price = trigger_price
        self.budget = budget


class Executor:

    def __init__(self, kite: KiteConnect):
        self.kite = kite
        self.order_map = {
            KiteConnect.EXCHANGE_NSE: {},
            KiteConnect.EXCHANGE_BSE: {}
        }

        orders = KiteOrders(self.kite)
        while orders is None:
            orders = KiteOrders(self.kite)
            time.sleep(1)

        for order in orders:
            if re.search('OPEN', order['status']):
                self.order_map[order['exchange']][order['tradingsymbol']] = order['order_id']

    def _execute_action(self, action: Action):
        if action.transaction_type is None:
            return 0

        trades_logger.info(action.str)
        order_id = KitePlaceOrder(self.kite, tradingsymbol=action.tradingsymbol,
                                  exchange=action.exchange,
                                  order_type=action.order_type,
                                  transaction_type=action.transaction_type,
                                  quantity=action.quantity,
                                  variety=action.variety,
                                  product=action.product,
                                  price=action.price,
                                  trigger_price=action.trigger_price)
        if order_id is None:
            return 0

        self.order_map[action.exchange][action.tradingsymbol] = order_id
        return 1

    def _cancel_order(self, status, order_id, action):

        trades_logger.info(action.str)
        order_id = KiteCancel(self.kite, variety=status['variety'], order_id=order_id)
        if order_id is None:
            return 0

        del self.order_map[status['exchange']][status['tradingsymbol']]
        return 1

    def _modify_order(self, old_order_id, new_action: Action):
        old_status = KiteOrderHistory(self.kite, order_id=old_order_id)
        if old_status is None:
            return 0

        old_status = old_status[-1]
        if re.search('COMPLETE', old_status['status']) \
                or re.search('REJECTED', old_status['status']) \
                or re.search('CANCELLED', old_status['status']):

            trades_logger.info('Order Status of {} is {}'.format(old_order_id, old_status['status']))
            del self.order_map[old_status['exchange']][old_status['tradingsymbol']]
            return self._execute_action(new_action)

        elif old_status['transaction_type'] != new_action.transaction_type \
                or new_action.transaction_type is None:

            if not self._cancel_order(old_status, old_order_id, new_action):
                return 0

            return self._execute_action(new_action)

        elif old_status['variety'] == new_action.variety \
                and old_status['quantity'] == new_action.quantity \
                and old_status['order_type'] == new_action.order_type:

            if old_status['order_type'] == KiteConnect.ORDER_TYPE_LIMIT:
                if old_status['price'] == new_action.price:
                    return 0
            elif old_status['order_type'] == KiteConnect.ORDER_TYPE_SL:
                if old_status['price'] == new_action.price and \
                        old_status['trigger_price'] == new_action.trigger_price:
                    return 0
            elif old_status['order_type'] == KiteConnect.ORDER_TYPE_SLM:
                if old_status['trigger_price'] == new_action.trigger_price:
                    return 0
            else:
                return 0

        if not self._cancel_order(old_status, old_order_id, new_action):
            return 0

        return self._execute_action(new_action)
        # TODO: Modify Order is not showing modified quantity
        # try:
        #     self.kite.modify_order(variety=new_action.variety,
        #                            order_id=old_status[0]['order_id'],
        #                            quantity=new_action.quantity,
        #                            price=new_action.price,
        #                            order_type=new_action.order_type,
        #                            trigger_price=new_action.trigger_price
        #                            )
        #     return 1
        # except Exception as e:
        #     logger.exception('Got Exception'.format(e.__str__()))
        #     if re.search('Maximum allowed order modifications exceeded', e.__str__()):
        #         self.kite.cancel_order(variety=old_status[0]['variety'], order_id=old_order_id)
        #         del self.order_map[old_status[0]['exchange']][old_status[0]['tradingsymbol']]
        #         return self._execute_action(new_action)
        #
        #     return 0

    def execute(self, action: Action):

        # already_traded = 0.
        # trades = self.kite.trades()
        # for trade in trades:
        #     if trade['tradingsymbol'] == action.tradingsymbol and \
        #             trade['exchange'] == action.exchange and \
        #             trade['transaction_type'] == action.transaction_type:
        #         already_traded += trade['quantity'] * trade['average_price']
        #
        # if already_traded >= (0.95 * action.budget):
        #     return 0
        # else:
        #     action.quantity = action.get_quantity(action.budget - already_traded)
        #     if action.quantity == 0:
        #         return 0

        # If previous order of this Instrument is still not executed then it will be cancelled
        if action.tradingsymbol in self.order_map[action.exchange].keys():
            prev_order_id = self.order_map[action.exchange][action.tradingsymbol]
            return self._modify_order(prev_order_id, action)

        return self._execute_action(action)


if __name__ == '__main__':
    FORMAT = '%(funcName)s(%(lineno)d): %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    trades_logger = logging.getLogger("my logger")

    api_key = ''
    api_secret = ''
    _kite = KiteConnect(api_key=api_key)

    access_token = ''
    _kite.set_access_token(access_token)

    _executor = Executor(_kite)

    _actions = [
        Action('CIPLA', KiteConnect.EXCHANGE_NSE, KiteConnect.ORDER_TYPE_MARKET, KiteConnect.TRANSACTION_TYPE_BUY, 1,
               KiteConnect.VARIETY_AMO, price=1, trigger_price=1),
        # Buy to Sell transition
        Action('CIPLA', KiteConnect.EXCHANGE_NSE, KiteConnect.ORDER_TYPE_MARKET, KiteConnect.TRANSACTION_TYPE_SELL, 1,
               KiteConnect.VARIETY_AMO, price=1, trigger_price=1),
        # Check duplicate Actions
        Action('CIPLA', KiteConnect.EXCHANGE_NSE, KiteConnect.ORDER_TYPE_MARKET, KiteConnect.TRANSACTION_TYPE_SELL, 1,
               KiteConnect.VARIETY_AMO, price=1, trigger_price=1),
        # Sell to Buy transition
        Action('CIPLA', KiteConnect.EXCHANGE_NSE, KiteConnect.ORDER_TYPE_MARKET, KiteConnect.TRANSACTION_TYPE_BUY, 1,
               KiteConnect.VARIETY_AMO, price=1, trigger_price=1),
        # AMO to Regular
        Action('CIPLA', KiteConnect.EXCHANGE_NSE, KiteConnect.ORDER_TYPE_MARKET, KiteConnect.TRANSACTION_TYPE_BUY, 1,
               KiteConnect.VARIETY_REGULAR, price=1, trigger_price=1),
        # Regular to AMO
        Action('CIPLA', KiteConnect.EXCHANGE_NSE, KiteConnect.ORDER_TYPE_MARKET, KiteConnect.TRANSACTION_TYPE_BUY, 1,
               KiteConnect.VARIETY_AMO, price=1, trigger_price=1),
        # Change in quantity
        Action('CIPLA', KiteConnect.EXCHANGE_NSE, KiteConnect.ORDER_TYPE_MARKET, KiteConnect.TRANSACTION_TYPE_BUY, 5,
               KiteConnect.VARIETY_AMO, price=1, trigger_price=1),
        # Market to SLM
        Action('CIPLA', KiteConnect.EXCHANGE_NSE, KiteConnect.ORDER_TYPE_SLM, KiteConnect.TRANSACTION_TYPE_BUY, 5,
               KiteConnect.VARIETY_AMO, price=1, trigger_price=1),
        # Change in Price
        Action('CIPLA', KiteConnect.EXCHANGE_NSE, KiteConnect.ORDER_TYPE_SLM, KiteConnect.TRANSACTION_TYPE_BUY, 10,
               KiteConnect.VARIETY_AMO, price=10, trigger_price=1),
        # Added TriggerPrice and also changed Price
        Action('CIPLA', KiteConnect.EXCHANGE_NSE, KiteConnect.ORDER_TYPE_SLM, KiteConnect.TRANSACTION_TYPE_BUY, 10,
               KiteConnect.VARIETY_AMO, price=10, trigger_price=25),
    ]

    for _action in _actions:
        if _executor.execute(action=_action):
            print('Executed')
        else:
            print('Not Executed')
