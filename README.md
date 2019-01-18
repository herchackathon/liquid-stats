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

The tool remembers where it last ran and can be run periodically to get more recent updates.

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
