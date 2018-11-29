from bitcoinrpc.authproxy import AuthServiceProxy
from datetime import datetime, timedelta

liquid_rpc_user = "rpcuser"
liquid_rpc_password = "rpcpassword"
liquid_port = 7041

def get_liquid_rpc():
	return AuthServiceProxy("http://{0}:{1}@localhost:{2}".format(liquid_rpc_user, liquid_rpc_password, liquid_port))

liquid_rpc = get_liquid_rpc()

bitcoin_rpc_user = "rpcuser"
bitcoin_rpc_password = "rpcpassword"
bitcoin_port = 8332

def get_bitcoin_rpc():
	return AuthServiceProxy("http://{0}:{1}@localhost:{2}".format(bitcoin_rpc_user, bitcoin_rpc_password, bitcoin_port))

bitcoin_rpc = get_bitcoin_rpc()

class LiquidConstants:
    btc_asset = "6f0279e9ed041c3d710a9f57d0c02928416460c4b722ae3457a11eec381c526d"
    liquid_fee_address = "QLFdUboUPJnUzvsXKu83hUtrQ1DuxyggRg"

    # Functionaries create blocks in this order
    functionary_mapping = [3, 10, 5, 8, 6, 11, 2, 15, 13, 9, 4, 12, 7, 14, 1]

    #TODO This gets lucky because 15 is a multiple of 60, ideally we should have a timestamp here.
    @staticmethod
    def get_functionary_by_minute(minute):
        return LiquidConstants.functionary_mapping[minute % 15]

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