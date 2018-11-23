from liquidutils import LiquidConstants, get_liquid_rpc, get_bitcoin_rpc, round_time
from configuration import Configuration
import json
import os.path
import decimal
from datetime import datetime, timedelta

def to_satoshis(amount):
    return int(amount * decimal.Decimal(10e8))

def log_downtime(configuration, block_time):
    downtime = 0
    if configuration.expected_block_time != datetime.fromtimestamp(0):
        while block_time > configuration.expected_block_time:
            functionary = LiquidConstants.get_functionary_by_minute(configuration.expected_block_time.minute)
            configuration.logger.log_missed_block(configuration.expected_block_time, functionary)
            configuration.expected_block_time = configuration.expected_block_time + timedelta(seconds=60)
            downtime = downtime + 1
    if downtime > 15:
        configuration.logger.log_downtime(block_time, downtime)

def log_inputs(configuration, tx_full, block_time, block_height):
    for idx, input in enumerate(tx_full["vin"]):
        if "is_pegin" in input and input["is_pegin"]:
            mainchain = get_bitcoin_rpc().decoderawtransaction(input["pegin_witness"][4])
            configuration.logger.log_peg(block_height, block_time, to_satoshis(mainchain["vout"][input["vout"]]["value"]), tx_full["txid"], idx)
        if "issuance" in input:
            issuance = input["issuance"]
            if "assetamount" in issuance:          
                configuration.logger.log_issuance(block_height, block_time, issuance["asset"], to_satoshis(issuance["assetamount"]), tx_full["txid"], idx)
            else:
                configuration.logger.log_issuance(block_height, block_time, issuance["asset"], None, tx_full["txid"], idx)
                
def log_outputs(configuration, tx_full, block_time, block_height):
     for idx, output in enumerate(tx_full["vout"]):
        if "pegout_chain" in output["scriptPubKey"]:
            configuration.logger.log_peg(block_height, block_time, (0-to_satoshis(output["value"])), tx_full["txid"], idx)
        if "addresses" in output["scriptPubKey"] and output["scriptPubKey"]["addresses"][0] == LiquidConstants.liquid_fee_address:
            configuration.logger.log_fee(block_height, block_time, to_satoshis(output["value"]))
        if output["scriptPubKey"]["asm"] == "OP_RETURN" and "asset" in output and output["asset"] != LiquidConstants.btc_asset and "value" in output and output["value"] > 0:
            configuration.logger.log_issuance(block_height, block_time, output["asset"], 0-to_satoshis(output["value"]), tx_full["txid"], idx)       

def main():
    configuration = Configuration()

    liquid_rpc = get_liquid_rpc()

    i = configuration.start_at
    last_height = liquid_rpc.getblockcount()

    if configuration.start_at <= last_height:
        for i in range(configuration.start_at, last_height+1):
            block_hash = liquid_rpc.getblockhash(i)
            block = liquid_rpc.getblock(block_hash)
            block_time = round_time(datetime.utcfromtimestamp(block["time"]))

            if i % 1000 == 0:
                print "Block {0}".format(i)
                configuration.save(i, block_time)

            log_downtime(configuration, block_time)
            liquid_rpc = get_liquid_rpc()
            for tx in block["tx"]:
                tx_full = liquid_rpc.getrawtransaction(tx, True)
                log_inputs(configuration, tx_full, block_time, i)
                log_outputs(configuration, tx_full, block_time, i)
            configuration.expected_block_time = block_time + timedelta(seconds=60)
            
        configuration.save(last_height, block_time)
        print "Complete at block {0}".format(last_height)
    else:
        print "Nothing new to parse."

main()