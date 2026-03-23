from .base_broker import BaseBroker, Order, Position, Balance
from .ccxt_broker import CCXTBroker
from .ibkr_broker import IBKRBroker
from .etrade_broker import ETradeBroker
from .schwab_broker import SchwabBroker
from .tradier_broker import TradierBroker

BROKER_REGISTRY: dict[str, type] = {
    "binance": CCXTBroker,
    "bybit": CCXTBroker,
    "coinbase": CCXTBroker,
    "kraken": CCXTBroker,
    "okx": CCXTBroker,
    "ibkr": IBKRBroker,
    "etrade": ETradeBroker,
    "schwab": SchwabBroker,
    "tradier": TradierBroker,
}

__all__ = [
    "BaseBroker", "Order", "Position", "Balance",
    "CCXTBroker", "IBKRBroker", "ETradeBroker", "SchwabBroker", "TradierBroker",
    "BROKER_REGISTRY",
]
