import MetaTrader5 as mt5
import time
try:
    from config import (
        MASTER_LOGIN, MASTER_PASSWORD, MASTER_SERVER,
        SLAVE_LOGIN, SLAVE_PASSWORD, SLAVE_SERVER
    )
except ImportError:
    print("❌ config.py not found.")
    print("👉 Copy config.example.py to config.py and fill credentials.")
    exit()
MAGIC = 555555

def connect(login, password, server):
    if not mt5.initialize(login=login, password=password, server=server):
        print(f"❌ Failed to connect: {mt5.last_error()}")
        return False
    print(f"✅ Connected to account {login}")
    return True

def get_positions():
    positions = mt5.positions_get()
    return positions if positions else []

def open_slave_trade(master_pos):
    symbol = master_pos.symbol
    volume = master_pos.volume
    sl = master_pos.sl
    tp = master_pos.tp

    mt5.symbol_select(symbol, True)
    tick = mt5.symbol_info_tick(symbol)

    order_type = mt5.ORDER_TYPE_BUY if master_pos.type == 0 else mt5.ORDER_TYPE_SELL
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": MAGIC,
        "comment": f"COPIED#{master_pos.ticket}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    result = mt5.order_send(request)
    print("Copied trade:", result.retcode)

def close_slave_trade(pos):
    tick = mt5.symbol_info_tick(pos.symbol)
    price = tick.bid if pos.type == 0 else tick.ask
    order_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": MAGIC,
        "comment": "Closed by copier"
    }

    mt5.order_send(request)

print("🚀 TRADE COPIER STARTED")

copied = {}

while True:
    # MASTER
    if not connect(MASTER_LOGIN, MASTER_PASSWORD, MASTER_SERVER):
        time.sleep(2)
        continue

    master_positions = get_positions()
    master_tickets = [p.ticket for p in master_positions]

    # COPY NEW TRADES
    for p in master_positions:
        if p.ticket not in copied:
            connect(SLAVE_LOGIN, SLAVE_PASSWORD, SLAVE_SERVER)
            open_slave_trade(p)
            copied[p.ticket] = True

    # CLOSE REMOVED TRADES
    connect(SLAVE_LOGIN, SLAVE_PASSWORD, SLAVE_SERVER)
    slave_positions = get_positions()

    for sp in slave_positions:
        if sp.magic == MAGIC:
            master_ticket = int(sp.comment.split("#")[-1])
            if master_ticket not in master_tickets:
                close_slave_trade(sp)
                copied.pop(master_ticket, None)

    time.sleep(1)
