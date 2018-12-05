from datetime import datetime, timedelta

from bitcoinrpc.authproxy import AuthServiceProxy

def get_rpc(user, password, port):
    return AuthServiceProxy("http://{}:{}@localhost:{}".format(user, password, port))

def to_satoshis(btc_amt):
    return int(btc_amt * decimal.Decimal(10e8))

def to_timestamp(time_as_datetime):
    return int((time_as_datetime - datetime.fromtimestamp(0)).total_seconds())

def round_time(dt=None, round_to=60):
    """Round a datetime object to any time lapse in seconds
    dt : datetime.datetime object, default now.
    roundTo : Closest number of seconds to round to, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
    """
    if dt == None : dt = datetime.now()
    seconds = (dt.replace(tzinfo=None) - dt.min).seconds
    rounding = (seconds+round_to/2) // round_to * round_to
    return dt + timedelta(0,rounding-seconds,-dt.microsecond)
