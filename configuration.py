from decimal import Decimal
from json import load, dump
from datetime import timedelta, datetime
from logger import Logger, to_timestamp

class Configuration:
    def __init__(self):
        self.logger = Logger()
        self.start_at = self.logger.last_block + 1
        self.expected_block_time = self.logger.last_time + timedelta(seconds=60) if self.logger.last_time != None else datetime.fromtimestamp(0)

    def save(self, last_height, last_time, last_hash):
        self.logger.save_progress(last_height, last_time, last_hash)
