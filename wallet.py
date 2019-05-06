from utils import get_json_from_url

class WalletManager():
    def __init__(self, logger):
        self.logger = logger


    def add_donation_utxos(self, address, block_height):
        print("Adding TXOs from {0}".format(address))
        txs = []
        last_txid = None
        #TODO stop processing when we find a transaction we know about already
        while(last_txid == None or len(txs) > 0):
            if last_txid == None:
                txs = get_json_from_url("https://blockstream.info/api/address/{0}/txs".format(address))
            else:
                txs = get_json_from_url("https://blockstream.info/api/address/{0}/txs/chain/{1}".format(address, last_txid))
            for tx in txs:
                last_txid = tx["txid"]
                if tx["status"]["confirmed"] == True and tx["status"]["block_height"]+100 <= block_height:
                    for idx, output in enumerate(tx["vout"]):
                        if output["scriptpubkey_address"] == address:
                            count = self.logger.conn.execute("SELECT COUNT(*) FROM wallet WHERE txid=? AND txindex=?", (tx["txid"], idx)).fetchone()[0]
                            if count == 0:
                                self.logger.insert_wallet_receieve(tx["txid"], idx, output["value"], tx["status"]["block_hash"], tx["status"]["block_time"])
                                self.logger.conn.commit()


    def update_wallet(self):

        block_height = get_json_from_url("https://blockstream.info/api/blocks/tip/height")
        self.add_donation_utxos("3EiAcrzq1cELXScc98KeCswGWZaPGceT1d", block_height)
        self.add_donation_utxos("3G6neksSBMp51kHJ2if8SeDUrzT8iVETWT", block_height)
       
        #check what wallet transactions are spent

        print("Updating wallet spends")
        txs = self.logger.conn.execute("SELECT txid, txindex FROM wallet WHERE spent_txid IS NULL")
        for tx in txs:
            tx_data = get_json_from_url(self.logger.outspend_template.format(tx[0], tx[1]))
            if tx_data["spent"] == True and tx_data["status"]["confirmed"] == True and tx_data["status"]["block_height"]+100 <= block_height:
                self.logger.spend_wallet_utxo(tx[0], tx[1], tx_data["txid"], tx_data["vin"])
                spent_tx = get_json_from_url(self.logger.tx_template.format(tx_data["txid"]))
                for idx, vout in enumerate(spent_tx["vout"]):
                    if not vout["scriptpubkey_address"] == "3EiAcrzq1cELXScc98KeCswGWZaPGceT1d":
                        self.logger.set_pegout(spent_tx["txid"], idx, vout["value"], vout["scriptpubkey_address"])
            self.logger.conn.commit()
