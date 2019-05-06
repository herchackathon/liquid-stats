from datetime import datetime, timedelta
from logger import Logger
from utils import round_time, get_rpc_proxy
from config import Configuration
from parser import Parser
from wallet import WalletManager

def main():
    
    config = Configuration()
    logger = Logger(config.database)

    Parser(config).parse(logger)

    WalletManager(logger).update_wallet()
    
if __name__ == "__main__":
    main()
