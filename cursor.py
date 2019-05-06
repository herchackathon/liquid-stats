from datetime import datetime, timedelta

class Cursor:

    def __init__(self, last_block_height = 0, last_block_hash = None, last_block_time = None):
        self.last_block_height = last_block_height
        self.last_block_hash = last_block_hash
        self.last_block_time = last_block_time

    def get_next_expected_block_time(self):
        if self.last_block_time is None:
            return datetime.fromtimestamp(0)
        else:
            return self.last_block_time + timedelta(seconds=60)

    def get_next_block_height(self):
        if self.last_block_height is None:
            return 1
        else:
            return self.last_block_height + 1

    def reset(self):
        self.last_block_hash = None
        self.last_block_parsed = None
        self.last_block_time = None

    def advance(self, block):
        self.last_block_height = self.get_next_block_height()
        self.last_block_hash = block.block_hash
        self.last_block_time = block.block_time

