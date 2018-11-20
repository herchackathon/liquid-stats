from liquidutils import LiquidConstants, get_liquid_rpc, get_bitcoin_rpc, round_time
from configuration import Configuration
import json
import os.path
import decimal
from datetime import datetime, timedelta

def log_downtime(configuration, block_time):
    downtime = 0
    if configuration.expected_block_time != datetime.fromtimestamp(0):
        while block_time > configuration.expected_block_time:
            functionary = LiquidConstants.get_functionary_by_minute(configuration.expected_block_time.minute)
            configuration.logger.log_missed_block(configuration.expected_block_time, functionary)
            configuration.stats.missed_rounds[functionary - 1] = configuration.stats.missed_rounds[functionary - 1] + 1
            configuration.expected_block_time = configuration.expected_block_time + timedelta(seconds=60)
            downtime = downtime + 1
    if downtime > 15:
        configuration.stats.total_downtime = configuration.stats.total_downtime + downtime

def log_inputs(configuration, tx_full, block_time, block_height):
    for input in tx_full["vin"]:
        if "is_pegin" in input and input["is_pegin"]:
            mainchain = get_bitcoin_rpc().decoderawtransaction(input["pegin_witness"][4])
            configuration.logger.log_peg(block_height, block_time, int(decimal.Decimal(10e8) * mainchain["vout"][input["vout"]]["value"]))
            configuration.stats.amount_in = configuration.stats.amount_in + mainchain["vout"][input["vout"]]["value"]
        if "issuance" in input:
            issuance = input["issuance"]
            if "assetamount" in issuance:          
                configuration.logger.log_issuance(block_height, block_time, issuance["asset"], int(decimal.Decimal(10e8) * issuance["assetamount"]))
            else:
                configuration.logger.log_issuance(block_height, block_time, issuance["asset"], None)
                
def log_outputs(configuration, tx_full, block_time, block_height):
     for output in tx_full["vout"]:
        if "pegout_chain" in output["scriptPubKey"]:
            configuration.logger.log_peg(block_height, block_time, int(decimal.Decimal(10e8)*(0-output["value"])))
            configuration.stats.amount_in = configuration.stats.amount_in - output["value"]
        if "addresses" in output["scriptPubKey"] and output["scriptPubKey"]["addresses"][0] == LiquidConstants.liquid_fee_address:
            configuration.stats.fee_total = configuration.stats.fee_total + output["value"]
            configuration.logger.log_fee(block_height, block_time, int(decimal.Decimal(10e8) * output["value"]))
      

def print_stats(stats, block_height, last_block_time):
    print "amount in : {0}".format(stats.amount_in)
    print "fees collected: {0}".format(stats.fee_total)
    print "missed round count: {0}".format(stats.missed_rounds)
    print "total downtime: {0}".format(stats.total_downtime)
    print "last block: {0}".format(block_height)
    print "last block time: {0}".format(last_block_time)

def write_headers(peg_writer, fee_writer, issuance_writer, outages_writer, missing_rounds_writer):
    peg_writer.writerow(['Direction', 'Block','Date', 'Amount'])
    fee_writer.writerow(['Block','Date', 'Amount'])
    issuance_writer.writerow(['Block','Date', 'Asset', 'Amount'])
    outages_writer.writerow(['Outage End','Length'])
    missing_rounds_writer.writerow(['Missing Time', 'Functionary Id'])


def remove_if_exists(path):
    if os.path.exists(path):
        os.remove(path)

def main():
    configuration = Configuration()

    if not configuration.continuing:
        remove_if_exists("peg.csv")
        remove_if_exists("fee.csv")
        remove_if_exists("issuance.csv")
        remove_if_exists("outages.csv")
        remove_if_exists("missing_rounds.csv")


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
                print_stats(configuration.stats, i, block_time)
                configuration.logger.conn.commit()

            log_downtime(configuration, block_time)
            liquid_rpc = get_liquid_rpc()
            for tx in block["tx"]:
                tx_full = liquid_rpc.getrawtransaction(tx, True)
                log_inputs(configuration, tx_full, block_time, i)
                log_outputs(configuration, tx_full, block_time, i)
            configuration.expected_block_time = block_time + timedelta(seconds=60)

        configuration.save(last_height, block_time)
        print_stats(configuration.stats, i, block_time)
    else:
        print "Nothing new to parse."

main()