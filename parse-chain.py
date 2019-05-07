from datetime import datetime, timedelta
from logger import Logger
from utils import round_time, get_rpc_proxy
from config import Configuration
from parser import Parser
from wallet import WalletManager
from liquid import LiquidNetworkParameters

def main():
    
    config = Configuration()
    logger = Logger(config.database)

    network_parameters = LiquidNetworkParameters(config.functionary_order, config.first_block_time)
    Parser(config, network_parameters).parse(logger)

    WalletManager().update_wallet(logger)
    
if __name__ == "__main__":
    main()
