from datetime import datetime, timedelta
import decimal
from bitcoinrpc.authproxy import AuthServiceProxy
import requests
import argparse
import json

def get_block_from_txid(txid):
    tx_template = "https://blockstream.info/api/tx/{0}"
    tx_info = get_json_from_url(tx_template.format(txid))
    return tx_info["status"]["block_hash"], get_block_from_hash(tx_info["status"]["block_hash"])

def get_block_from_hash(block_hash):
    if block_hash == None:
        return None
    block_template = "https://blockstream.info/api/block/{0}"
    block_info = get_json_from_url(block_template.format(block_hash))
    return block_info["timestamp"]

def get_json_from_url(url):
    response = requests.get(url)
    if (response.ok):
        return response.json()
    else:
        raise SystemError("No response from server.")

def get_rpc(user, password, port):
    return AuthServiceProxy("http://{}:{}@localhost:{}".format(user, password, port))

def to_satoshis(btc_amt):
    return int(btc_amt * decimal.Decimal(1e8))

def to_timestamp(time_as_datetime):
    return int((time_as_datetime - datetime.fromtimestamp(0)).total_seconds())

def round_time(dt=None, round_to=60, round_point=15):
    """Round a datetime object to any time lapse in seconds
    dt : datetime.datetime object, default now.
    roundTo : Closest number of seconds to round to, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
    """
    if dt == None : dt = datetime.now()
    seconds = (dt.replace(tzinfo=None) - dt.min).seconds
    rounding = (seconds+round_to-round_point) // round_to * round_to
    return dt + timedelta(0,rounding-seconds,-dt.microsecond)

def get_config():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Liquid staticstics analyzes the Liquid blockchain and logs useful information to track fees collected, assets issued, and outages.')
    parser.add_argument("configfile", metavar='CONFIG', nargs='?', 
        type=argparse.FileType('r'), default="config.json",
         help="the configuration file to read from")
    args = parser.parse_args()
    config = json.load(args.configfile)
    return config

def get_rpc_proxy(config):
    
    # Setup RPCs and logger
    liquid_rpc = get_rpc(config["liquidrpc"]["user"],
                        config["liquidrpc"]["password"],
                        config["liquidrpc"]["port"])
    bitcoin_rpc = get_rpc(config["bitcoinrpc"]["user"],
                        config["bitcoinrpc"]["password"],
                        config["bitcoinrpc"]["port"])
    return liquid_rpc, bitcoin_rpc
