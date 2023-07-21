from kiteconnect import KiteTicker, KiteConnect
from Utilities.logger import trades_logger


def KitePlaceOrder(kite: KiteConnect, tradingsymbol, exchange, order_type, transaction_type, quantity, variety,
                   product, price, trigger_price):
    try:
        order_id = kite.place_order(tradingsymbol=tradingsymbol,
                                    exchange=exchange,
                                    order_type=order_type,
                                    transaction_type=transaction_type,
                                    quantity=quantity,
                                    variety=variety,
                                    product=product,
                                    price=price,
                                    trigger_price=trigger_price)
        trades_logger.info('Success place_order: {}, {}, {}, {}, {}, {}'.format(order_id, tradingsymbol, exchange,
                                                                                transaction_type, quantity, price))
        return order_id

    except Exception as e:
        trades_logger.error('Cannot place_order {}: {}, {}, {}, {}, {}'.format(e.__str__(), tradingsymbol, exchange,
                                                                               transaction_type, quantity, price))
        return None


def KiteCancel(kite: KiteConnect, variety, order_id):
    try:
        kite.cancel_order(variety=variety, order_id=order_id)
        trades_logger.info('Success cancel_order: {}, {}, {}, {}, {}, {}'.format(order_id))
        return order_id
    except Exception as e:
        trades_logger.error('Cannot cancel_order {}: {}'.format(e.__str__(), order_id))
        return None


def KiteOrderHistory(kite: KiteConnect, order_id):
    try:
        status = kite.order_history(order_id=order_id)
        return status
    except Exception as e:
        trades_logger.error('Cannot get order_history {}: {}'.format(e.__str__(), order_id))
        return None


def KiteOrders(kite: KiteConnect):
    try:
        orders = kite.orders()
        return orders
    except Exception as e:
        trades_logger.error('Cannot get orders {}'.format(e.__str__()))
        return None


def KiteQuote(kite: KiteConnect, quote_input):
    try:
        quote = kite.quote(quote_input)
        return quote
    except Exception as e:
        trades_logger.error('Cannot get quotes {}'.format(e.__str__()))
        return None
