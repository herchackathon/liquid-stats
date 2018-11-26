import sqlite3
from datetime import datetime

def to_timestamp(time_as_datetime):
    return int((time_as_datetime - datetime.fromtimestamp(0)).total_seconds())

class Logger:

    SCHEMA_VERSION = 4 #Update this if the schema changes and the chain needs to be reindexed.
    
    def reindex(self):
        self.last_block = 0
        self.last_time = None
        self.block_hash = None
        self.conn.execute('''DELETE FROM missing_blocks''')
        self.conn.execute('''DELETE FROM fees''')
        self.conn.execute('''DELETE FROM outages''')
        self.conn.execute('''DELETE FROM pegs''')
        self.conn.execute('''DELETE FROM issuances''')
    
    def __init__(self):
        #Initialize Database if not created
        self.conn = sqlite3.connect('liquid.db')
        self.conn.execute('''CREATE TABLE if not exists schema_version (version int)''')
        schema_version = self.conn.execute("SELECT version FROM schema_version").fetchall()
        if len(schema_version) == 0:
            self.conn.execute('''CREATE TABLE if not exists missing_blocks (datetime int, functionary int)''')
            self.conn.execute('''CREATE TABLE if not exists fees (block int, datetime int, amount int)''')
            self.conn.execute('''CREATE TABLE if not exists outages (end_time int, length int)''')
            self.conn.execute('''CREATE TABLE if not exists pegs (block int, datetime int, amount int, txid string, txindex int)''')
            self.conn.execute('''CREATE TABLE if not exists issuances (block int, datetime int, asset text, amount int NULL, txid string, txindex int, token string NULL, tokenamount int NULL)''')
            self.conn.execute('''CREATE TABLE if not exists last_block (block int, datetime int, block_hash string)''')
            self.reindex()

        else:
            if schema_version[0][0] < 2:
                self.reindex()
                self.conn.execute('DROP TABLE issuances')
                self.conn.execute('DROP TABLE pegs')
                self.conn.execute('''CREATE TABLE if not exists pegs (block int, datetime int, amount int, txid string. index int)''')
                self.conn.execute('''CREATE TABLE if not exists issuances (block int, datetime int, asset text, amount int NULL, txid string, txindex int)''')
            if schema_version[0][0] < 3:
                self.reindex()
                self.conn.execute('DROP TABLE issuances')
                self.conn.execute('''CREATE TABLE if not exists issuances (block int, datetime int, asset text, amount int NULL, txid string, txindex int, token string NULL, tokenamount int NULL)''')
            
            if schema_version[0][0] < 4:
                self.reindex()
                self.conn.execute("DROP TABLE last_block")
                self.conn.execute('''CREATE TABLE if not exists last_block (block int, datetime int, block_hash string)''')
                
            else:
                configuration = self.conn.execute("SELECT block, datetime, block_hash FROM last_block").fetchall()
                if len(configuration) == 0:      
                    self.reindex()
                else:
                    self.last_time = datetime.fromtimestamp(configuration[0][1])
                    self.last_block = configuration[0][0]
                    self.conn.execute('''DELETE FROM missing_blocks WHERE datetime >= ? ''', (to_timestamp(self.last_time),))
                    self.conn.execute('''DELETE FROM fees WHERE datetime >= ? ''', (to_timestamp(self.last_time),))
                    self.conn.execute('''DELETE FROM outages WHERE end_time >= ? ''', (to_timestamp(self.last_time),))
                    self.conn.execute('''DELETE FROM pegs WHERE datetime >= ? ''', (to_timestamp(self.last_time),))
                    self.conn.execute('''DELETE FROM issuances WHERE datetime >= ? ''', (to_timestamp(self.last_time),)) 
                    self.block_hash = configuration[0][2]
            self.conn.commit()

    def log_issuance(self, block_height, block_time, asset_id, amount, txid, txindex, token, tokenamount):
         self.conn.execute("INSERT INTO issuances VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (block_height, to_timestamp(block_time), asset_id, amount, txid, txindex, token, tokenamount))

    def log_peg(self, block_height, block_time, amount, txid, txindex):
         self.conn.execute("INSERT INTO pegs VALUES (?, ?, ?, ? , ?)", (block_height, to_timestamp(block_time), amount, txid, txindex))

    def log_fee(self, block_height, block_time, amount):
        self.conn.execute("INSERT INTO fees VALUES (?, ?, ?)", (block_height, to_timestamp(block_time), amount))

    def log_downtime(self, resume_time, downtime):
        self.conn.execute("INSERT INTO outages VALUES (?, ?)", (to_timestamp(resume_time), downtime))

    def log_missed_block(self, expected_block_time, functionary):
        self.conn.execute("INSERT INTO missing_blocks VALUES (?, ?)", (to_timestamp(expected_block_time), functionary))
        
    def save_progress(self, last_block, last_timestamp, last_hash):
        self.conn.execute("DELETE FROM last_block")
        self.conn.execute("INSERT INTO last_block VALUES (?, ?, ?) ", (last_block, to_timestamp(last_timestamp), last_hash))

        self.conn.execute("DELETE FROM schema_version")
        self.conn.execute("INSERT INTO schema_version VALUES (?) ", (Logger.SCHEMA_VERSION,))

        self.conn.commit()