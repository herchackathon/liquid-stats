import argparse
import configparser
from datetime import datetime, timedelta

from logger import Logger
from utils import get_rpc, round_time

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Liquid staticstics analyzes the Liquid blockchain and logs useful information to track fees collected, assets issued, and outages.')
    parser.add_argument("configfile", metavar='CONFIG', nargs='?', type=argparse.FileType('r'), default="config.ini", help="the configuration file to read from")
    args = parser.parse_args()

    # Parse config file
    config = configparser.ConfigParser()
    config.read_file(args.configfile)

    # Setup RPCs and logger
    liquid_rpc = get_rpc(config["Liquid RPC"]["user"],
                         config["Liquid RPC"]["password"],
                         config["Liquid RPC"]["port"])
    bitcoin_rpc = get_rpc(config["Bitcoin RPC"]["user"],
                          config["Bitcoin RPC"]["password"],
                          config["Bitcoin RPC"]["port"])
    logger = Logger(config["General"]["database"], bitcoin_rpc, liquid_rpc)

    # Parse functionary order from config
    functionary_order = [int(i.strip()) for i in config["Liquid"]["functionary_order"].split(",")]

    # Determine range of blocks to log
    next_block_height = logger.next_block_height()
    end_block_height = liquid_rpc.getblockcount()

    # Used to determine downtime
    next_expected_block_time = logger.next_expected_block_time()

    # Get last known block again and see if it matches the hash, otherwise set it to 0
    if next_block_height <= end_block_height:
        for curr_block_height in range(next_block_height, end_block_height+1):
            curr_block_hash = liquid_rpc.getblockhash(curr_block_height)
            curr_block = liquid_rpc.getblock(curr_block_hash)
            curr_block_time = round_time(datetime.utcfromtimestamp(curr_block["time"]))

            # Log to console and save progress every 1000 blocks
            if curr_block_height % 1000 == 0:
                print("Block {0}".format(curr_block_height))
                logger.save_progress(curr_block_height, curr_block_time, curr_block_hash)

            logger.log_downtime(next_expected_block_time, curr_block_time, functionary_order)
            for tx_full in [liquid_rpc.getrawtransaction(tx, True) for tx in curr_block["tx"]]:
                logger.log_inputs(tx_full, curr_block_time, curr_block_height)
                logger.log_outputs(tx_full, curr_block_time, curr_block_height, config["Liquid"]["fee_address"], config["Liquid"]["bitcoin_asset_hex"])

            # Expect the next block to be 60 seconds from current one
            next_expected_block_time = curr_block_time + timedelta(seconds=60)

        logger.save_progress(end_block_height, curr_block_time, curr_block_hash)
        print("Complete at block {0}".format(end_block_height))
    else:
        print("Nothing new to parse.")

if __name__ == "__main__":
    main()
