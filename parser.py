from utils import to_satoshis, to_timestamp, get_block_from_txid, get_json_from_url, get_block_from_hash, round_time, get_rpc_proxy
from datetime import datetime
from liquid import LiquidTransaction, LiquidBlock

class Parser:
    def __init__(self, config):
        
        self.config = config

    def parse(self, logger):
        
        liquid_rpc, bitcoin_rpc = get_rpc_proxy(self.config)
        cursor = logger.cursor

        if self.block_not_in_best_chain(cursor, liquid_rpc):
            cursor.reset()
            logger.reset_data()

        starting_block = cursor.get_next_block_height()
        ending_block = liquid_rpc.getblockcount()

        if starting_block <= ending_block:
            for curr_block_height in range(starting_block, ending_block+1):
                self.parse_block(curr_block_height, logger, cursor, liquid_rpc, bitcoin_rpc)

                # Log to console and save progress every 1000 blocks
                if curr_block_height % 1000 == 0:
                    self.save_progress(cursor, logger)
                    liquid_rpc, bitcoin_rpc = get_rpc_proxy(self.config)
        else:
            print("Nothing new to parse.")

        self.save_progress(cursor, logger)
        print("Complete at block {0}".format(ending_block))

    @staticmethod
    def block_not_in_best_chain(cursor, liquid_rpc):
        cursor.last_block_height is not None and cursor.last_block_hash is not None and \
            liquid_rpc.getblockhash(cursor.last_block_height) != cursor.last_block_hash

    def parse_block(self, height, logger, cursor, liquid_rpc, bitcoin_rpc):

        liquid_block = LiquidBlock(liquid_rpc, height)
        next_expected_block_time = cursor.get_next_expected_block_time()

        #In case rounding doesn't work when clocks get out of sync, and we get two blocks for the same time, we should assume
        #the next block is for the next minute
        if next_expected_block_time != None and liquid_block.block_time < next_expected_block_time:
            liquid_block.block_time = next_expected_block_time
       
        logger.log_downtime(next_expected_block_time, liquid_block.block_time, self.config.functionary_order)

        for tx in liquid_block.get_transactions():
            self.parse_inputs(logger, tx, bitcoin_rpc)
            self.parse_outputs(logger, tx)
        cursor.advance(liquid_block)

    def parse_inputs(self, logger, tx, bitcoin_rpc):

        for input in tx.get_inputs():
            if input.is_pegin():
                self.parse_peg_in(logger, input, bitcoin_rpc)

            if input.is_issuance():
                self.parse_issuance(logger, input)

    def parse_peg_in(self, logger, input, bitcoin_rpc):
        mainchain_tx = input.get_mainchain_transaction(bitcoin_rpc)
        logger.insert_peg(input.transaction.block.block_height, input.transaction.block.block_time, mainchain_tx.get_amount_from_output(input.vout),
            input.transaction.txid, input.vin, input.get_pegin_address(bitcoin_rpc), input.transaction.txid, input.vout)
                
        block_hash, block_timestamp = get_block_from_txid(mainchain_tx.txid)

        logger.insert_wallet_receieve(input.txid, input.vout, to_satoshis(mainchain_tx.get_amount_from_output(input.vout)),
                block_hash, block_timestamp)

    def parse_issuance(self, logger, input):
        assetamount = input.get_asset_amount()
        token = input.get_token()
        tokenamount = input.get_token_amount()
        logger.insert_issuance(input.transaction.block.block_height, input.transaction.block.block_time, input.asset, assetamount, input.txid, input.vin, token, tokenamount)

    def parse_outputs(self, logger, tx):
         for output in tx.get_outputs():
            if output.is_pegout():
                logger.insert_peg(output.transaction.block.block_height, output.transaction.block.block_time, (0-to_satoshis(output.value)), output.transaction.txid, output.vout, output.data["scriptPubKey"]["pegout_addresses"][0], None, None)
            if output.is_fee(self.config.fee_address):
                logger.insert_fee(output.transaction.block.block_height, output.transaction.block.block_time, to_satoshis(output.value))
            if output.is_asset_burn(self.config.bitcoin_asset_hex):
                logger.insert_issuance(output.transaction.block.block_height, output.transaction.block.block_time, output["asset"], 0-to_satoshis(output["value"]), output.transaction.txid, output.vout, None, None)
            if output.is_lbtc_burn(self.config.bitcoin_asset_hex):
                logger.insert_peg(output.transaction.block.block_height, output.transaction.block.block_time, (0 - to_satoshis(output["value"])), output.transaction.txid, output.vout, "", None, None)
 
    def save_progress(self, cursor, logger):
        print("Block {0}".format(cursor.last_block_height))
        logger.save_progress(cursor)
