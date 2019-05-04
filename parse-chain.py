from datetime import datetime, timedelta
from logger import Logger
from utils import round_time, get_rpc_proxy
from config import Configuration
from parser import Parser

def main():
    config = Configuration()
    liquid_rpc, bitcoin_rpc = get_rpc_proxy(config)
    logger = Logger(config.database)
  
    # Determine range of blocks to log
    next_block_height = logger.next_block_height()
    end_block_height = liquid_rpc.getblockcount()

    # Used to determine downtime
    next_expected_block_time = logger.next_expected_block_time()
    parser = Parser(next_block_height, bitcoin_rpc, liquid_rpc, logger)

    # Get last known block again and see if it matches the hash, otherwise set it to 0
    if next_block_height <= end_block_height:
        for curr_block_height in range(next_block_height, end_block_height+1):
            curr_block_hash = liquid_rpc.getblockhash(curr_block_height)
            curr_block = liquid_rpc.getblock(curr_block_hash)
            curr_block_time = round_time(datetime.utcfromtimestamp(curr_block["time"]))
            #In case rounding doesn't work when clocks get out of sync, and we get two blocks for the same time, we should assume
            #the next block is for the next minute
            if next_expected_block_time != None and curr_block_time < next_expected_block_time:
                curr_block_time = next_expected_block_time
            # Log to console and save progress every 1000 blocks
            if curr_block_height % 1000 == 0:
                print("Block {0}".format(curr_block_height))
                logger.save_progress(curr_block_height, curr_block_time, curr_block_hash)

                #Reload RPCs since timeout frequently

                # Setup RPCs and logger
                logger.liquid_rpc, logger.bitcoin_rpc = get_rpc_proxy(config)

            logger.log_downtime(next_expected_block_time, curr_block_time, config.functionary_order)

            for tx_full in [liquid_rpc.getrawtransaction(tx, True) for tx in curr_block["tx"]]:
                parser.log_inputs(tx_full, curr_block_time, curr_block_height)
                parser.log_outputs(tx_full, curr_block_time, curr_block_height, config["liquid"]["fee_address"], config["liquid"]["bitcoin_asset_id"])

            # Expect the next block to be 60 seconds from current one
            next_expected_block_time = curr_block_time + timedelta(seconds=60)

        logger.save_progress(end_block_height, curr_block_time, curr_block_hash)
        print("Complete at block {0}".format(end_block_height))
    else:
        print("Nothing new to parse.")

    print("Updating Federation Wallet")
    logger.update_wallet()

   
if __name__ == "__main__":
    main()
