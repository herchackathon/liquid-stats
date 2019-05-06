from utils import round_time, to_satoshis
from datetime import datetime

class LiquidBlock:
    def __init__(self, liquid_rpc, height):
        self.block_hash = liquid_rpc.getblockhash(height)
        self.block = liquid_rpc.getblock(self.block_hash)
        self.block_height = height
        self.block_time = round_time(datetime.utcfromtimestamp(self.block["time"]))
        self.liquid_rpc = liquid_rpc

    def get_transactions(self):
        for tx in [self.liquid_rpc.getrawtransaction(tx, True) for tx in self.block["tx"]]:
            yield LiquidTransaction(tx, self)

class LiquidTransaction:
    def __init__(self, transaction, block):
        self.transaction = transaction
        self.txid = transaction["txid"]
        self.inputs = transaction["vin"]
        self.outputs = transaction["vout"]
        self.block = block

    def get_inputs(self):
        for idx, input in enumerate(self.inputs):
            yield LiquidInput(input, self, idx)

    def get_outputs(self):
        for idx, output in enumerate(self.outputs):
            yield LiquidOutput(output, self, idx)

class LiquidInput:
    def __init__(self, input, transaction, index):
        self.data = input
        self.transaction = transaction
        self.vin = index
        self.txid = None if not "txid" in input else input["txid"]
        self.vout = None if not "vout" in self.data else self.data["vout"]
        self.asset = None if not "issuance" in self.data else self.data["issuance"]["asset"]
    
    def is_pegin(self):
        return "is_pegin" in self.data and self.data["is_pegin"]

    def get_mainchain_transaction(self, bitcoin_rpc):
        return BitcoinTransaction(bitcoin_rpc.decoderawtransaction(self.data["pegin_witness"][4]))

    def is_issuance(self):
        return "issuance" in self.data

    def get_pegin_address(self, bitcoin_rpc):
        return bitcoin_rpc.decodescript(self.data["pegin_witness"][3])["p2sh"]

    def get_asset_amount(self):
        return None if "assetamount" not in self.data["issuance"] else to_satoshis(self.data["issuance"]["assetamount"])

    def get_token(self):
        return None if "token" not in self.data["issuance"] else self.data["issuance"]["token"]

    def get_token_amount(self):
        return None if "tokenamount" not in self.data["issuance"] else self.data["issuance"]["tokenamount"]

class LiquidOutput:
    def __init__(self, output, transaction, index):
        self.data = output
        self.transaction = transaction
        self.vout = index
        self.value = output["value"]

    def is_pegout(self):
        return "pegout_chain" in self.data["scriptPubKey"]

    def is_fee(self, fee_address):
        return "addresses" in self.data["scriptPubKey"] and self.data["scriptPubKey"]["addresses"][0] == fee_address

    def is_burn(self):
        return self.data["scriptPubKey"]["asm"] == "OP_RETURN" and "asset" in self.data and "value" in self.data and self.data["value"] > 0

    def is_asset_burn(self, bitcoin_asset_hex):
        return self.is_burn() and self.data["asset"] != bitcoin_asset_hex

    def is_lbtc_burn(self, bitcoin_asset_hex):
        return self.is_burn() and self.data["asset"] == bitcoin_asset_hex
    
class BitcoinTransaction:
    def __init__(self, data):
        self.data = data
        self.txid = data["txid"]
    
    def get_amount_from_output(self, vout):
        return to_satoshis(self.data["vout"][vout]["value"])
    