from datetime import datetime, timedelta
import sqlite3
from utils import get_json_from_url, to_timestamp, get_transaction_from_blockstream_info
from cursor import Cursor

class Logger:

    SCHEMA_VERSION = 11 #Update this if the schema changes.

    def __init__(self, database):
        self.conn = sqlite3.connect(database)
        if not self.migrate_db():
            last_logged_data = self.conn.execute("SELECT block, datetime, block_hash FROM last_block").fetchone()
            last_time = datetime.fromtimestamp(last_logged_data[1])
            self.cursor = Cursor(last_logged_data[0], last_logged_data[2], last_time)
            self.remove_new_data(last_logged_data[0],  last_time)
        else:
            self.cursor = Cursor()
    
    def __del__(self):
        self.conn.close()
       
    def remove_new_data(self, last_liquid_block_height, last_liquid_block_time):
        self.conn.execute('''DELETE FROM missing_blocks WHERE datetime >= ? ''', (to_timestamp(last_liquid_block_time),))
        self.conn.execute('''DELETE FROM fees WHERE block >= ? ''', (last_liquid_block_height,))
        self.conn.execute('''DELETE FROM outages WHERE end_time >= ? ''', (to_timestamp(last_liquid_block_time),))
        self.conn.execute('''DELETE FROM pegs WHERE block >= ? ''', (last_liquid_block_height,))
        self.conn.execute('''DELETE FROM issuances WHERE block >= ? ''', (last_liquid_block_height,))
        #TOOD handle deleting transaction tracing here

    def create_tables(self):
        self.conn.execute('''CREATE TABLE if not exists missing_blocks (datetime int, functionary int)''')
        self.conn.execute('''CREATE TABLE if not exists fees (block int, datetime int, amount int)''')
        self.conn.execute('''CREATE TABLE if not exists outages (end_time int, length int)''')
        self.conn.execute('''CREATE TABLE if not exists pegs (block int, datetime int, amount int, txid string, txindex int, bitcoinaddress string, bitcointxid string NULL, bitcoinindex int NULL)''')
        self.conn.execute('''CREATE TABLE if not exists issuances (block int, datetime int, asset text, amount int NULL, txid string, txindex int, token string NULL, tokenamount int NULL)''')
        self.conn.execute('''CREATE TABLE if not exists last_block (block int, datetime int, block_hash string)''')
        self.conn.execute('''CREATE TABLE if not exists wallet (txid string, txindex int, amount int, block_hash string, block_timestamp string, spent_txid string NULL, spent_index int NULL)''')
        self.conn.execute('''CREATE TABLE if not exists txspends (txid string, fee int, block_hash string, datetime int)''')
    
    @staticmethod
    def get_current_schema_version(connection):
        connection.execute('''CREATE TABLE if not exists schema_version (version int)''')
        schema_version = connection.execute("SELECT version FROM schema_version").fetchall()
        if len(schema_version) == 0:
            return None
        return schema_version[0][0]

    def migrate_db(self):
        schema_version = self.get_current_schema_version(self.conn)
        should_reindex = True
        if schema_version == None:
            self.create_tables()
        else:
            if schema_version < 3:
                self.conn.execute('DROP TABLE issuances')
                self.conn.execute('''CREATE TABLE if not exists issuances (block int, datetime int, asset text, amount int NULL, txid string, txindex int, token string NULL, tokenamount int NULL)''')
            if schema_version < 4:
                self.conn.execute("DROP TABLE last_block")
                self.conn.execute('''CREATE TABLE if not exists last_block (block int, datetime int, block_hash string)''')
            if schema_version < 5:
                self.conn.execute('''CREATE TABLE if not exists wallet (txid string, txindex int, amount int, block_hash string, block_timestamp string, spent_txid string NULL, spent_index int NULL)''')
            if schema_version < 9:
                self.conn.execute('DROP TABLE pegs')
                self.conn.execute('''CREATE TABLE if not exists pegs (block int, datetime int, amount int, txid string, txindex int, bitcoinaddress string, bitcointxid string NULL, bitcoinindex int NULL)''')
            if schema_version < 10:
                self.conn.execute('''CREATE TABLE if not exists txspends (txid string, fee int, block_hash string, datetime int)''')
            elif schema_version == self.SCHEMA_VERSION:
                should_reindex = False
                
            self.conn.commit()

        return should_reindex

    def reset(self):
        self.conn.execute('''DELETE FROM missing_blocks''')
        self.conn.execute('''DELETE FROM fees''')
        self.conn.execute('''DELETE FROM outages''')
        self.conn.execute('''DELETE FROM pegs''')
        self.conn.execute('''DELETE FROM issuances''')
        self.conn.execute('''DELETE FROM wallet''')

    def insert_issuance(self, block_height, block_time, asset_id, amount, txid, txindex, token, tokenamount):
        self.conn.execute("INSERT INTO issuances VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (block_height, to_timestamp(block_time), asset_id, amount, txid, txindex, token, tokenamount))

    def insert_peg(self, block_height, block_time, amount, txid, txindex, bitcoinaddress, bitcointxid=None, bitcointxindex=None):
        self.conn.execute("INSERT INTO pegs VALUES (?, ?, ?, ? , ?, ?, ?, ?)", (block_height, to_timestamp(block_time), amount, txid, txindex, bitcoinaddress, bitcointxid, bitcointxindex))

    def insert_wallet_receive(self, txid, txindex, amount, block_height, block_timestamp):
        if block_height == None:
            return
        cursor = self.conn.execute("SELECT COUNT(*) FROM wallet WHERE txid=? AND txindex=?", (txid ,txindex))
        if cursor.fetchone()[0] == 0:
            self.conn.execute("INSERT INTO wallet VALUES (?, ?, ?, ?, ?, ?, ?)",(txid, txindex, amount, block_height, block_timestamp, None, None))

    def insert_fee(self, block_height, block_time, amount):
        self.conn.execute("INSERT INTO fees VALUES (?, ?, ?)", (block_height, to_timestamp(block_time), amount))

    def insert_downtime(self, resume_time, downtime):
        self.conn.execute("INSERT INTO outages VALUES (?, ?)", (to_timestamp(resume_time), downtime))

    def insert_missed_block(self, expected_block_time, functionary):
        self.conn.execute("INSERT INTO missing_blocks VALUES (?, ?)", (to_timestamp(expected_block_time), functionary))

    def insert_processed_peg_out(self, address, amount, txid, txindex):
        return NotImplementedError()

    def save_progress(self, cursor):
        self.conn.execute("DELETE FROM last_block")
        self.conn.execute("INSERT INTO last_block VALUES (?, ?, ?) ", (cursor.last_block_height, to_timestamp(cursor.last_block_time), cursor.last_block_hash))

        self.conn.execute("DELETE FROM schema_version")
        self.conn.execute("INSERT INTO schema_version VALUES (?) ", (Logger.SCHEMA_VERSION,))

        self.conn.commit()

    def get_wallet_utxos(self):
        result = self.conn.execute("SELECT txid, txindex FROM wallet WHERE spent_txid IS NULL")
        return result


    def spend_wallet_utxo(self, txid, txindex, spenttxid, spentindex):
        self.conn.execute("UPDATE wallet SET spent_txid=?, spent_index=? WHERE txid=? AND txindex=?", (spenttxid, spentindex, txid, txindex))
        matching_transactions = self.conn.execute("SELECT COUNT(*) FROM txspends WHERE txid=?", (spenttxid,)).fetchone()[0]
        if matching_transactions == 0:
            tx_details = get_transaction_from_blockstream_info(spenttxid)
            self.conn.execute("INSERT INTO txspends (txid, fee, block_hash, datetime) VALUES (?, ?, ?, ?)", (spenttxid, tx_details["fee"], tx_details["status"]["block_hash"], tx_details["status"]["block_time"]))

    def get_unconfirmed(self):
        result = self.conn.execute("SELECT txid, txindex FROM wallet WHERE block_hash IS NULL")
        return result

    def set_pegout(self, txid, idx, value, address):
        #is this utxo already accounted for?
        processed = self.conn.execute("SELECT COUNT(*) FROM pegs WHERE amount < 0 AND bitcointxid=? AND bitcoinindex=? AND bitcoinaddress=?", (txid, idx, address)).fetchone()[0]
        if processed > 0:
            return 
        tx = self.conn.execute("SELECT txid, txindex FROM pegs WHERE bitcoinaddress=? AND amount=? AND bitcointxid IS NULL ORDER BY datetime DESC LIMIT 1", (address, 0-value)).fetchone()
        print("Processing pegout to {0}, amount: {1} from Liquidtxid {2}:{3}".format(address, value, tx[0], tx[1]))
        self.conn.execute("UPDATE pegs SET bitcointxid=?, bitcoinindex=? WHERE txid=? AND txindex=?", (txid, idx, tx[0], tx[1]))

    def get_unspent_transactions(self):
        values = self.conn.execute("SELECT txid, txindex FROM wallet WHERE spent_txid IS NULL")
        for value in values:
            yield {"txid": value[0], "vout": value[1]}
            