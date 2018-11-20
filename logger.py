import sqlite3
from datetime import datetime

def to_timestamp(time_as_datetime):
    return int((time_as_datetime - datetime.fromtimestamp(0)).total_seconds())

class Logger:
    def __init__(self, start_time= None):
        #Initialize Database if not created
        self.conn = sqlite3.connect('liquid.db')
        self.conn.execute('''CREATE TABLE if not exists missing_blocks (datetime int, functionary int)''')
        self.conn.execute('''CREATE TABLE if not exists fees (block int, datetime int, amount int)''')
        self.conn.execute('''CREATE TABLE if not exists outages (end_time int, length int)''')
        self.conn.execute('''CREATE TABLE if not exists pegs (block int, datetime int, amount int)''')
        self.conn.execute('''CREATE TABLE if not exists issuances (datetime int, block int, asset text, amount int NULL)''')

        if start_time == None:
            self.conn.execute('''DELETE FROM missing_blocks''')
            self.conn.execute('''DELETE FROM fees''')
            self.conn.execute('''DELETE FROM outages''')
            self.conn.execute('''DELETE FROM pegs''')
            self.conn.execute('''DELETE FROM issuances''')
        else:
            self.conn.execute('''DELETE FROM missing_blocks WHERE datetime >= ? ''', (to_timestamp(start_time),))
            self.conn.execute('''DELETE FROM fees WHERE datetime >= ? ''', (to_timestamp(start_time),))
            self.conn.execute('''DELETE FROM outages WHERE end_time >= ? ''', (to_timestamp(start_time),))
            self.conn.execute('''DELETE FROM pegs WHERE datetime >= ? ''', (to_timestamp(start_time),))
            self.conn.execute('''DELETE FROM issuances WHERE datetime >= ? ''', (to_timestamp(start_time),))
        
        self.conn.commit()

    def log_issuance(self, block_height, block_time, asset_id, amount):
         self.conn.execute("INSERT INTO issuances VALUES (?, ?, ?, ?)", (block_height, to_timestamp(block_time), asset_id, amount))

    def log_burn(self):
        print "burn"

    def log_peg(self, block_height, block_time, amount):
         self.conn.execute("INSERT INTO pegs VALUES (?, ?, ?)", (block_height, to_timestamp(block_time), amount))

    def log_fee(self, block_height, block_time, amount):
        self.conn.execute("INSERT INTO fees VALUES (?, ?, ?)", (block_height, to_timestamp(block_time), amount))


    def log_downtime(self, resume_time, downtime):
        self.conn.execute("INSERT INTO outages VALUES (?, ?)", (to_timestamp(resume_time), downtime))

    def log_missed_block(self, expected_block_time, functionary):
        self.conn.execute("INSERT INTO missing_blocks VALUES (?, ?)", (to_timestamp(expected_block_time), functionary))
        

