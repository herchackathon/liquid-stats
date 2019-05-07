from utils import get_json_from_url, get_transaction_from_blockstream_info
from liquid import BitcoinTransaction
from logger import Logger

class WalletManager():

    def __init__(self, minimum_confirms = 100,
        federation_address = "3G6neksSBMp51kHJ2if8SeDUrzT8iVETWT",
        change_address = "3EiAcrzq1cELXScc98KeCswGWZaPGceT1d"):

        self.minimum_confirms = minimum_confirms
        self.federation_address = federation_address
        self.change_address = change_address

    def update_wallet(self, logger):
        block_height = self.get_block_height()
        self.add_donation_utxos(logger, self.change_address, block_height)
        self.add_donation_utxos(logger, self.federation_address, block_height)
       
        #check what wallet transactions are spent
        print("Updating wallet spends")
        for tx in logger.get_unspent_transactions():
            outspend_tx = self.get_outspend(tx["txid"], tx["vout"])
            if outspend_tx["spent"] == True and self.has_sufficient_spends(outspend_tx, block_height):

                logger.spend_wallet_utxo(tx["txid"], tx["vout"], outspend_tx["txid"], outspend_tx["vin"])
                spent_tx = BitcoinTransaction(get_transaction_from_blockstream_info(outspend_tx["txid"]))

                for output in spent_tx.get_outputs():
                    if not output.address == self.change_address:
                        logger.set_pegout(outspend_tx["txid"], output.vout, output.value, output.address)
                        
            logger.conn.commit()

    @staticmethod
    def get_block_height():
        return get_json_from_url("https://blockstream.info/api/blocks/tip/height")

    @staticmethod
    def get_transactions(address):
        for tx in get_json_from_url("https://blockstream.info/api/address/{0}/txs".format(address)):
            yield BitcoinTransaction(tx)

    @staticmethod
    def get_transctions_after_txid(address, txid):
        for tx in get_json_from_url("https://blockstream.info/api/address/{0}/txs/chain/{1}".format(address, txid)):
            yield BitcoinTransaction(tx)

    def add_donation_utxos(self, logger, address, block_height):
        print("Adding TXOs from {0}".format(address))
        last_txid = None
        found_tx = False
        #TODO stop processing when we find a transaction we know about already
        while(last_txid == None or found_tx == True):
            if last_txid == None:
                txs = self.get_transactions(address)
            else:
                txs = self.get_transctions_after_txid(address, last_txid)
            found_tx = False
            for tx in txs:
                last_txid = tx.txid
                found_tx = True
                if self.has_sufficient_spends(tx.data, block_height):
                    for output in tx.get_outputs():
                        if output.address == address:
                            logger.insert_wallet_receive(output.transaction.txid, output.vout, output.value, output.transaction.block_hash, output.transaction.block_time)      

    def has_sufficient_spends(self, tx_data, block_height):
        return tx_data["status"]["confirmed"] == True and tx_data["status"]["block_height"]+ self.minimum_confirms <= block_height

    outspend_template = "https://blockstream.info/api/tx/{0}/outspend/{1}"

    def get_outspend(self, txid, vout):
        return get_json_from_url(self.outspend_template.format(txid, vout))