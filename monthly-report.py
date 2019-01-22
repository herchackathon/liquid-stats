from datetime import datetime, timedelta, timezone
import sqlite3

db_location = "liquid.db"

def get_uptime(start_time, end_time):
    connection = sqlite3.connect(db_location)
    minutes = (end_time - start_time).total_seconds() / 60
    result = connection.execute("""
        SELECT SUM(period_end_time - period_start_time)/60 FROM (SELECT MAX(?, start_time) AS period_start_time, 
        MIN(?, end_time) AS period_end_time FROM (SELECT end_time - (length * 60) as start_time, end_time FROM outages)
        WHERE period_start_time >=? AND period_end_time <=? AND end_time>? AND start_time<?
        ORDER BY period_start_time)""", 
        (start_time.timestamp(), end_time.timestamp(), start_time.timestamp(), end_time.timestamp(), start_time.timestamp(), end_time.timestamp()))
    downtime_sum = result.fetchone()
    if downtime_sum[0] == None:
        return 1
    return (1 - (downtime_sum[0] / minutes))

def get_block_efficiency(start_time, end_time):
    connection = sqlite3.connect(db_location)
    minutes = (end_time - start_time).total_seconds() / 60
    result = connection.execute("""SELECT COUNT(*) FROM missing_blocks WHERE datetime >=? AND datetime<?""", (start_time.timestamp(), end_time.timestamp()))
    missing_blocks = result.fetchone()
    if missing_blocks[0] == None:
        return 1
    return (1 - missing_blocks[0] / minutes)

def get_wallet_balance(end_time):
    connection = sqlite3.connect(db_location)
    result = connection.execute("SELECT SUM(amount) FROM pegs WHERE datetime < ?", (end_time.timestamp(),))
    wallet = result.fetchone()
    if wallet[0] == None:
        return 0
    return wallet[0]/1e8


final_report = datetime(2018, 10, 1, tzinfo=timezone.utc)

def get_last_month_and_year(current_year, current_month):
    previous_month = current_month - 1
    previous_month = 12 if previous_month == 0 else previous_month
    previous_year = current_year if previous_month != 12 else current_year-1
    return previous_year, previous_month


now = datetime.utcnow()
current_year = now.year
current_month = now.month
previous_year, previous_month = get_last_month_and_year(now.year, now.month)
start_time = datetime(previous_year, previous_month, 1, tzinfo=timezone.utc)

print("Start Time\tEnd Time\tUptime\tEfficiency\tWallet Balance\t")
while start_time >= final_report: 
    start_time = datetime(previous_year, previous_month, 1, tzinfo=timezone.utc)
    end_time = datetime(current_year, current_month, 1, tzinfo=timezone.utc)

    print("{0:%Y-%m-%d}\t{1:%Y-%m-%d}\t{2:%}\t{3:%}\t{4} BTC\t".format(start_time, end_time, get_uptime(start_time, end_time), 
        get_block_efficiency(start_time, end_time), get_wallet_balance(end_time)))

    current_month = previous_month
    current_year = previous_year
    previous_year, previous_month = get_last_month_and_year(current_year, current_month)

    #Value By Month