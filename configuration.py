from decimal import Decimal
from json import load, dump
from datetime import timedelta, datetime
from logger import Logger, to_timestamp

class Configuration:
    def __init__(self):
        try:
            with open('last_data.json', 'r') as last_data:
                
                configuration = load(last_data)
                
                self.start_at = configuration["last_height"] + 1 if "last_height" in configuration else 1
                self.expected_block_time = datetime.utcfromtimestamp(configuration["last_time"]) + timedelta(seconds=60) if "last_time" in configuration else datetime.fromtimestamp(0)
                self.logger = Logger(self.expected_block_time)
                self.stats = LiquidStats(configuration)
                self.continuing = True
             

        except IOError:
            self.continuing = False
            self.start_at = 1            
            self.expected_block_time = datetime.fromtimestamp(0)
            self.logger = Logger(self.expected_block_time)
            self.stats = LiquidStats()



    def save(self, last_height, last_time):
        configuration = {'last_height': last_height, 'fees_collected': str(self.stats.fee_total),
         'downtime': self.stats.total_downtime, 'amount_in': str(self.stats.amount_in), 
         'missed_round_count': self.stats.missed_rounds, 'last_time': to_timestamp(last_time) }

        with open('last_data.json', 'w+') as configuration_file:
            dump(configuration, configuration_file)


class LiquidStats:
    def __init__(self, configuration = {}):
        self.amount_in =  Decimal(configuration["amount_in"])  if "amount_in" in configuration else 0
        self.fee_total = Decimal(configuration["fees_collected"]) if "fees_collected" in configuration else 0
        self.total_downtime = configuration["downtime"] if "downtime" in configuration else 0
        self.missed_rounds = configuration["missed_round_count"] if "missed_round_count" in configuration else [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
 