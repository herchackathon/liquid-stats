# About

This tool analyzes the Liquid blockchain and logs useful information to track fees collected, assets issued, and outages.

# Setup

You must have a Liquid node and Bitcoin node running. The Liquid node running should be synchronized. The Bitcoin node can be running with -connect=0 and listen=0 as it is just used to parse transactions.

This example assumes that the rpcuser and rpcpassword is rpcuser and rpcpassword. Change these inside liquidutils.py if you have a different user/password, or use a non-standard port for Liquid or Bitcoin.

# Running

Run get-peg-in-stats.py to parse the Liquid chain. Results are logged to "liquid.db", an sqlite3 database. 

# Schema

## fees
Records fees collected each block.

* block - height of block
* datetime - timestamp of block, rounded to the nearest minute, in UNIX format
* amount - amount of fees collected, in Satoshis of the block

## issuances
Tracks issuances, re-issuances, and burns of assets.
* block - height of block
* datetime - timestamp of block, rounded to the nearest minute, in UNIX format
* asset - assetid of asset being issued being issued or burned
* amount - amount of asset issued or burned (negative for burns)
* txid - the txid that the issuance or burn occurs in
* txindex - the index of the input (for issuances) or output (for burns)
* token - the reissuance token, only used when the asset is first issued
* tokenamount - the amount of the reissuance token issued, only used when the asset is first issued

## last_block
Tracks the last block processed to determine where to resume parsing
* block - height of block
* datetime - timestamp of block, rounded to the nearest minute, in UNIX format
* block_hash - hash of block, used to determine if there has been a re-organization

## missing_blocks
Tracks blocks that were not produced
* datetime - timestamp of a block should have been found, rounded to the nearest minute, in UNIX format
* functionary - the functionary responsible for being the master of the missed round

## outages
Tracks periods 5 minutes or greater without blocks in Liquid
* end_time - the timestamp when of the first block after a lack 
* length - the amount of time since the last block

## pegs
Tracks peg-ins and peg-outs
* block - height of block
* datetime - timestamp of block, rounded to the nearest minute, in UNIX format
* amount - amount of peg-in or peg-out (negative values represent peg-outs)
* txid - Liquid transaction id of the peg-in or peg-out
* txindex - The index of the input or output for the peg-in or peg-out
* bitcoinaddress - The address associaetd with the peg-in or peg-out
* bitcointxid - The Bitcoin transaction id of the peg-in or peg-out
* bitcoindex - The index of the input or output for the peg-in or peg-out in the Bitcoin transaction

## schema_version
* version - used to track the version of the schema to know what to migrate during ugprades.

## wallet
Tracks UTXOs associated with the federation wallet
* txid - The Bitcoin transaction id of the transaction in the wallet
* txindex - The index of the output of the transaction
* amount - The amount of the output
* block_hash - The block that the transaction is included in
* block_timestamp - The timestamp of the block in UNIX format
* spent_txid - The transaction that spends this transaction
* spent_index - The index of the input in the transaction that spends this output

## tx_spends
* txid - The Bitcoin transaction id of a spend of the federation wallet
* fee - The amount of the transaction fee in satoshis
* block_hash - The Bitcoin block that contains the transaction
* datetime - The datetime of the Bitcoin block

# systemd

## `liquid-stats.service`

This systemd service file is used to control the liquid-stats container. Before
running, it first pulls the latest version, which allows us to simply push a new
container to the registry without having to SSH into any boxes to deploy.

It mounts `/home/bs/liquid.db` as the DB file, which allows us to use this file
for other services.

## `liquid-stats.timer`

This systemd timer simply triggers the service with the same name every 5 mins.
A `systemctl enable liquid-stats.timer && systemctl start liquid-stats.timer`
makes sure the timer is started, even after reboots.


