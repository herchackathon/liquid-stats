import json
import argparse
from datetime import datetime

class Configuration:
    def __init__(self):
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Liquid staticstics analyzes the Liquid blockchain and logs useful information to track fees collected, assets issued, and outages.')
        parser.add_argument("configfile", metavar='CONFIG', nargs='?', 
            type=argparse.FileType('r'), default="config.json",
            help="the configuration file to read from")
        args = parser.parse_args()
        config = json.load(args.configfile)
        
        self.liquidrpc = config["liquidrpc"]
        self.bitcoinrpc = config["bitcoinrpc"]
        self.database = config["database"]
        self.functionary_order = config["liquid"]["functionary_order"]
        self.fee_address = config["liquid"]["fee_address"]
        self.bitcoin_asset_hex = config["liquid"]["bitcoin_asset_id"]
        self.first_block_time = datetime.utcfromtimestamp(1538011800)
