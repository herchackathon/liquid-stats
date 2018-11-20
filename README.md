# About

This tool analyzes the Liquid blockchain and logs useful information to track fees collected, assets issued, and outages.

# Setup

You must have a Liquid node and Bitcoin node running. The Liquid node running should be synchronized. The Bitcoin node can be running with -connect=0 and listen=0 as it is just used to parse transactions.

This example assumes that the rpcuser and rpcpassword is rpcuser and rpcpassword. Change these inside liquidutils.py if you have a different user/password, or use a non-standard port for Liquid or Bitcoin.

# Running

Run get-peg-in-stats.py to parse the Liquid chain. Results are logged to "liquid.db", an sqlite3 database. There are 5 tables:

* pegs - tracks peg-in and peg-out transactions
* issuances - tracks asset issuance
* outages - tracks intervals greater than 15 minutes where the network is not operational.
* missing_blocks - tracks blocks that were not generated and determines which functionary failed to create the block
* fees - tracks fees collected in each block