from datetime import datetime, timedelta
import sqlite3
from utils import to_satoshis, to_timestamp, get_block_from_txid, get_json_from_url, get_block_from_hash

class Logger:

    SCHEMA_VERSION = 7 #Update this if the schema changes and the chain needs to be reindexed.

    def reindex(self):
        self.last_block = None
        self.last_time = None
        self.block_hash = None
        self.conn.execute('''DELETE FROM missing_blocks''')
        self.conn.execute('''DELETE FROM fees''')
        self.conn.execute('''DELETE FROM outages''')
        self.conn.execute('''DELETE FROM pegs''')
        self.conn.execute('''DELETE FROM issuances''')
        self.conn.execute('''DELETE FROM wallet''')

    def next_expected_block_time(self):
        if self.last_time is None:
            return datetime.fromtimestamp(0)
        else:
            return self.last_time + timedelta(seconds=60)

    def next_block_height(self):
        if self.last_block is None:
            return 1
        else:
            return self.last_block + 1

    def __init__(self, database, bitcoin_rpc, liquid_rpc):
        #Initialize Database if not created
        self.conn = sqlite3.connect(database)
        self.conn.execute('''CREATE TABLE if not exists schema_version (version int)''')

        self.bitcoin_rpc = bitcoin_rpc
        self.liquid_rpc = liquid_rpc

        schema_version = self.conn.execute("SELECT version FROM schema_version").fetchall()
        if len(schema_version) == 0:
            self.conn.execute('''CREATE TABLE if not exists missing_blocks (datetime int, functionary int)''')
            self.conn.execute('''CREATE TABLE if not exists fees (block int, datetime int, amount int)''')
            self.conn.execute('''CREATE TABLE if not exists outages (end_time int, length int)''')
            self.conn.execute('''CREATE TABLE if not exists pegs (block int, datetime int, amount int, txid string, txindex int)''')
            self.conn.execute('''CREATE TABLE if not exists issuances (block int, datetime int, asset text, amount int NULL, txid string, txindex int, token string NULL, tokenamount int NULL)''')
            self.conn.execute('''CREATE TABLE if not exists last_block (block int, datetime int, block_hash string)''')
            self.conn.execute('''CREATE TABLE if not exists wallet (txid string, txindex int, amount int, block_hash string, block_timestamp string, spent_txid string NULL, spent_index int NULL)''')
            self.reindex()
        else:
            if schema_version[0][0] < 2:
                self.conn.execute('DROP TABLE issuances')
                self.conn.execute('DROP TABLE pegs')
                self.conn.execute('''CREATE TABLE if not exists pegs (block int, datetime int, amount int, txid string. index int)''')
                self.conn.execute('''CREATE TABLE if not exists issuances (block int, datetime int, asset text, amount int NULL, txid string, txindex int)''')
            if schema_version[0][0] < 3:
                self.conn.execute('DROP TABLE issuances')
                self.conn.execute('''CREATE TABLE if not exists issuances (block int, datetime int, asset text, amount int NULL, txid string, txindex int, token string NULL, tokenamount int NULL)''')

            if schema_version[0][0] < 4:
                self.conn.execute("DROP TABLE last_block")
                self.conn.execute('''CREATE TABLE if not exists last_block (block int, datetime int, block_hash string)''')
            if schema_version[0][0] < 5:
                self.conn.execute('''CREATE TABLE if not exists wallet (txid string, txindex int, amount int, block_hash string, block_timestamp string, spent_txid string NULL, spent_index int NULL)''')
                self.reindex()
            if schema_version[0][0] == 5 or schema_version[0][0] == 6:
                self.reindex()
            else:
                configuration = self.conn.execute("SELECT block, datetime, block_hash FROM last_block").fetchall()
                should_reindex = False
                if len(configuration) == 0:
                    should_reindex = True
                else:
                    self.last_time = datetime.fromtimestamp(configuration[0][1])
                    self.last_block = configuration[0][0]
                    self.conn.execute('''DELETE FROM missing_blocks WHERE datetime >= ? ''', (to_timestamp(self.last_time),))
                    self.conn.execute('''DELETE FROM fees WHERE datetime >= ? ''', (to_timestamp(self.last_time),))
                    self.conn.execute('''DELETE FROM outages WHERE end_time >= ? ''', (to_timestamp(self.last_time),))
                    self.conn.execute('''DELETE FROM pegs WHERE datetime >= ? ''', (to_timestamp(self.last_time),))
                    self.conn.execute('''DELETE FROM issuances WHERE datetime >= ? ''', (to_timestamp(self.last_time),))
                    self.block_hash = configuration[0][2]

                    # Reindex if block hash doesn't check out
                    should_reindex = \
                        self.last_block is not None and self.block_hash is not None and \
                        self.liquid_rpc.getblockhash(self.last_block) != self.block_hash
                if should_reindex:
                    logger.reindex()
            self.conn.commit()

    def insert_issuance(self, block_height, block_time, asset_id, amount, txid, txindex, token, tokenamount):
        self.conn.execute("INSERT INTO issuances VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (block_height, to_timestamp(block_time), asset_id, amount, txid, txindex, token, tokenamount))

    def insert_peg(self, block_height, block_time, amount, txid, txindex):
        self.conn.execute("INSERT INTO pegs VALUES (?, ?, ?, ? , ?)", (block_height, to_timestamp(block_time), amount, txid, txindex))

    def insert_wallet_receieve(self, txid, txindex, amount, block_height, block_timestamp):
        cursor = self.conn.execute("SELECT COUNT(*) FROM wallet WHERE txid=? AND txindex=?", (txid ,txindex))
        if cursor.fetchone()[0] == 0:
            self.conn.execute("INSERT INTO wallet VALUES (?, ?, ?, ?, ?, ?, ?)",(txid, txindex, amount, block_height, block_timestamp, None, None))

    def insert_fee(self, block_height, block_time, amount):
        self.conn.execute("INSERT INTO fees VALUES (?, ?, ?)", (block_height, to_timestamp(block_time), amount))

    def insert_downtime(self, resume_time, downtime):
        self.conn.execute("INSERT INTO outages VALUES (?, ?)", (to_timestamp(resume_time), downtime))

    def insert_missed_block(self, expected_block_time, functionary):
        self.conn.execute("INSERT INTO missing_blocks VALUES (?, ?)", (to_timestamp(expected_block_time), functionary))

    def log_downtime(self, expected_block_time, block_time, functionary_order):
        downtime = 0
        if expected_block_time != datetime.fromtimestamp(0):
            while block_time > expected_block_time:
                functionary = functionary_order[expected_block_time.minute % 15]
                self.insert_missed_block(expected_block_time, functionary)
                expected_block_time += timedelta(seconds=60)
                downtime += 1
        if downtime >= 5:
            self.insert_downtime(block_time, downtime)

    def log_inputs(self, tx_full, block_time, block_height):
        for idx, input in enumerate(tx_full["vin"]):
            if "is_pegin" in input and input["is_pegin"]:
                mainchain = self.bitcoin_rpc.decoderawtransaction(input["pegin_witness"][4])
                self.insert_peg(block_height, block_time, to_satoshis(mainchain["vout"][input["vout"]]["value"]), tx_full["txid"],
                     idx)
                block_hash, block_timestamp = get_block_from_txid(input["txid"])
                self.insert_wallet_receieve(input["txid"], input["vout"], to_satoshis(mainchain["vout"][input["vout"]]["value"]),
                     block_hash, block_timestamp)
            if "issuance" in input:
                issuance = input["issuance"]
                if "assetamount" not in issuance:
                    assetamount = None
                else:
                    assetamount = to_satoshis(issuance["assetamount"])
                if "token" not in issuance:
                    token = None
                else:
                    token = issuance["token"]
                if "tokenamount" not in issuance:
                    tokenamount = None
                else:
                    tokenamount = to_satoshis(issuance["tokenamount"])
                self.insert_issuance(block_height, block_time, issuance["asset"], assetamount, tx_full["txid"], idx, token, tokenamount)

    def log_outputs(self, tx_full, block_time, block_height, liquid_fee_address, bitcoin_asset_hex):
         for idx, output in enumerate(tx_full["vout"]):
            if "pegout_chain" in output["scriptPubKey"]:
                self.insert_peg(block_height, block_time, (0-to_satoshis(output["value"])), tx_full["txid"], idx)
            if "addresses" in output["scriptPubKey"] and output["scriptPubKey"]["addresses"][0] == liquid_fee_address:
                self.insert_fee(block_height, block_time, to_satoshis(output["value"]))
            if output["scriptPubKey"]["asm"] == "OP_RETURN" and "asset" in output and output["asset"] != bitcoin_asset_hex and "value" in output and output["value"] > 0:
                self.insert_issuance(block_height, block_time, output["asset"], 0-to_satoshis(output["value"]), tx_full["txid"], idx, None, None)


    def save_progress(self, last_block, last_timestamp, last_hash):
        self.conn.execute("DELETE FROM last_block")
        self.conn.execute("INSERT INTO last_block VALUES (?, ?, ?) ", (last_block, to_timestamp(last_timestamp), last_hash))

        self.conn.execute("DELETE FROM schema_version")
        self.conn.execute("INSERT INTO schema_version VALUES (?) ", (Logger.SCHEMA_VERSION,))

        self.conn.commit()

    def get_wallet_utxos(self):
        result = self.conn.execute("SELECT txid, txindex FROM wallet WHERE spent_txid IS NULL")
        return result

    def spend_wallet_utxo(self, txid, txindex, spenttxid, spentindex):
        self.conn.execute("UPDATE wallet SET spent_txid=?, spent_index=? WHERE txid=? AND txindex=?", (spenttxid, spentindex, txid, txindex))

    outspend_template = "https://blockstream.info/api/tx/{0}/outspend/{1}"
    tx_template = "https://blockstream.info/api/tx/{0}"

    def update_wallet(self):
        #check what wallet transactions are spent
        for wallet_utxo in self.get_wallet_utxos():
            utxo_status = get_json_from_url(self.outspend_template.format(wallet_utxo[0], wallet_utxo[1]))
            if utxo_status["spent"]:
                self.spend_wallet_utxo(wallet_utxo[0], wallet_utxo[1], utxo_status["txid"], utxo_status["vin"])
                spent_tx = get_json_from_url(self.tx_template.format(utxo_status["txid"]))
                block_timestamp = get_block_from_hash(utxo_status["status"]["block_hash"])
                for idx, vout in enumerate(spent_tx["vout"]):
                    if vout["scriptpubkey_address"] == "3EiAcrzq1cELXScc98KeCswGWZaPGceT1d":
                        self.insert_wallet_receieve(utxo_status["txid"], idx, vout["value"], utxo_status["status"]["block_hash"], block_timestamp)
            self.conn.commit()