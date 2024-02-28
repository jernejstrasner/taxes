from dataclasses import dataclass
from typing import Literal

@dataclass
class KDVPSecurity:
    date: str
    quantity: int
    value: float
    stock: int


@dataclass
class KDVPSecurityOpen(KDVPSecurity):
    acquisition_type: Literal["A", "B"]  # Nacin pridobitve (there's more than A and B)


@dataclass
class KDVPSecurityClose(KDVPSecurity):
    loss_transfer: bool


@dataclass
class KDVPItem:
    name: str
    is_fond: bool
    securities: list[KDVPSecurityOpen | KDVPSecurityClose]

    def update_trade(self, trade: KDVPSecurityOpen | KDVPSecurityClose) -> bool:
        # Check if a trade with the same date and price already exists and join them
        for s in self.securities:
            if s.date == trade.date and s.value == trade.value and type(s) == type(trade):
                if isinstance(s, KDVPSecurityOpen) and s.acquisition_type == trade.acquisition_type:
                    s.quantity += trade.quantity
                    return True
                if isinstance(s, KDVPSecurityClose) and s.loss_transfer == trade.loss_transfer:
                    s.quantity += trade.quantity
                    return True
        return False

    def add_trade(self, trade: KDVPSecurityOpen | KDVPSecurityClose):
        if not self.update_trade(trade):
          self.securities.append(trade)
          self.securities.sort(key=lambda x: x.date, reverse=False)
        # Now go through and calculate the total stock value for each date
        stock = 0
        for s in self.securities:
            if isinstance(s, KDVPSecurityOpen):
                stock += s.quantity
            else:
                stock -= s.quantity
            s.stock = stock


class DohKDVP:
    items: dict[str, KDVPItem]

    def __init__(self) -> None:
        self.items = {}

    # WARNING: The way the trades are exported from Saxo and then imported to FURS it complicates
    # handling of opening and closing positions. This is a simple way to handle it which
    # might not work for some cases.
    def add_trade(self, symbol: str, trade: KDVPSecurityOpen | KDVPSecurityClose, is_fond: bool = False):
        if symbol not in self.items:
            self.items[symbol] = KDVPItem(symbol, is_fond, [])
        self.items[symbol].add_trade(trade)
