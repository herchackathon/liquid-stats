from utils import to_satoshis, to_timestamp, get_block_from_txid, get_json_from_url, get_block_from_hash

class Parser:
    def __init__(self, start_block, bitcoin_rpc, liquid_rpc, logger):
        self.start_block = start_block
        self.bitcoin_rpc = bitcoin_rpc
        self.liquid_rpc = liquid_rpc
        self.logger = logger
        
        if logger.require_reindex:
            self.start_block = 0

        if logger.last_block is not None and logger.block_hash is not None and \
                self.liquid_rpc.getblockhash(logger.last_block) != logger.block_hash:
            self.start_block = 0
            logger.reindex()
           
    def log_inputs(self, tx_full, block_time, block_height):
        for idx, input in enumerate(tx_full["vin"]):
            if "is_pegin" in input and input["is_pegin"]:
                mainchain = self.bitcoin_rpc.decoderawtransaction(input["pegin_witness"][4])
                address = self.bitcoin_rpc.decodescript(input["pegin_witness"][3])["p2sh"]
                self.logger.insert_peg(block_height, block_time, to_satoshis(mainchain["vout"][input["vout"]]["value"]), tx_full["txid"],
                     idx, address, input["txid"], input["vout"])
                block_hash, block_timestamp = get_block_from_txid(input["txid"])
                self.logger.insert_peg.insert_wallet_receieve(input["txid"], input["vout"], to_satoshis(mainchain["vout"][input["vout"]]["value"]),
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
                self.logger.insert_peg.insert_issuance(block_height, block_time, issuance["asset"], assetamount, tx_full["txid"], idx, token, tokenamount)

    
    def log_outputs(self, tx_full, block_time, block_height, liquid_fee_address, bitcoin_asset_hex):
         for idx, output in enumerate(tx_full["vout"]):
            if "pegout_chain" in output["scriptPubKey"]:
                self.logger.insert_peg.insert_peg(block_height, block_time, (0-to_satoshis(output["value"])), tx_full["txid"], idx, output["scriptPubKey"]["pegout_addresses"][0], None, None)
            if "addresses" in output["scriptPubKey"] and output["scriptPubKey"]["addresses"][0] == liquid_fee_address:
                self.logger.insert_peg.insert_fee(block_height, block_time, to_satoshis(output["value"]))
            if output["scriptPubKey"]["asm"] == "OP_RETURN" and "asset" in output and output["asset"] != bitcoin_asset_hex and "value" in output and output["value"] > 0:
                self.logger.insert_peg.insert_issuance(block_height, block_time, output["asset"], 0-to_satoshis(output["value"]), tx_full["txid"], idx, None, None)
            if output["scriptPubKey"]["asm"] == "OP_RETURN" and "asset" in output and output["asset"] == bitcoin_asset_hex and "value" in output and output["value"] > 0:
                self.logger.insert_peg.insert_peg(block_height, block_time, (0 - to_satoshis(output["value"])), tx_full["txid"], idx, "", None, None)
