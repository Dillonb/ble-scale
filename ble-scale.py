#!/usr/bin/env python3

# Research from:
# Neither source was completely correct, this script is a combination of knowledge from both
# https://www.cnblogs.com/wstong2052/p/17767538.html
# https://github.com/oliexdev/openScale/blob/master/android_app/app/src/main/java/com/health/openscale/core/bluetooth/BluetoothQNScale.java

import asyncio
import argparse
from bleak import BleakClient, BleakGATTCharacteristic
from bleak.exc import BleakDeviceNotFoundError
import datetime
import time
import requests
import sqlite3

parser = argparse.ArgumentParser(
        prog="ble-scale",
        description="Records data from a very specific BLE scale and sends it to the console, Discord, and a sqlite db."
        )


parser.add_argument('-d', '--discord-webhook-file', type=str)
parser.add_argument('-s', '--sqlite-path', type=str)

args = parser.parse_args()

hook = None

if args.discord_webhook_file is None:
    print("Not sending data to Discord.")
else:
    hook = open(args.discord_webhook_file, "r").read().strip()
    print(f"Will send data to discord through webhook")

def send_discord_message(msg):
    if hook is None:
        print("No webhook, not sending message!")
    else:
        msg_json = {
                'username': "Scale",
                'content': msg
                }
        requests.post(hook, json = msg_json)

sqlite_conn = None
def record_weight_sqlite(raw_weight, weight_kg, weight_lb):
    if sqlite_conn is None:
        print("Not saving to sqlite, no db path passed.")
    else:
        cur = sqlite_conn.cursor()
        cur.execute("INSERT INTO weights (date_iso8601, raw_weight, weight_kg, weight_lb) VALUES(:date_iso8601, :raw_weight, :weight_kg, :weight_lb)",
                    { "date_iso8601": datetime.datetime.now().isoformat(), "raw_weight": raw_weight, "weight_kg": weight_kg, "weight_lb": weight_lb })
        cur.close()
        sqlite_conn.commit()

if args.sqlite_path is None:
    print("Not saving data to sqlite")
else:
    print(f"Will record data to sqlite at {args.sqlite_path}")
    sqlite_conn = sqlite3.connect(args.sqlite_path)
    cur = sqlite_conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS weights(id INTEGER PRIMARY KEY AUTOINCREMENT, date_iso8601 STRING, raw_weight INTEGER, weight_kg REAL, weight_lb REAL)")
    cur.close()

class StabilizationTimeoutException(Exception):
    pass

def checksum(l):
    c = 0
    for x in l:
        c += x
        c &= 0xFF
    return c

address = "FF:03:00:38:F5:0B"
read_service = "0000fff1-0000-1000-8000-00805f9b34fb"
write_service = "0000fff2-0000-1000-8000-00805f9b34fb"

# 0x01 == kilograms 0x02 == pounds
# This byte appears to only affect the data displayed on screen, it has no effect on the data sent back over BLE.
unit_byte = 0x02

def kg_to_lb(kg):
    return round(kg * 2.20462, 1)

hello_magic = [0x13, 0x09, 0x15, unit_byte, 0x10, 0x00, 0x00, 0x00, 0x00]
hello_magic.append(checksum(hello_magic))

timestamp_int = int(time.time()) - 946702800 # time before 2000 did not exist
timestamp_bytes = [
        0x02,
        (timestamp_int >>  0) & 0xFF,
        (timestamp_int >>  8) & 0xFF,
        (timestamp_int >> 16) & 0xFF,
        (timestamp_int >> 32) & 0xFF,
        ]

goodbye_magic = [0x1F, 0x05, 0x21, 0x10, 0x49]

def print_hex(bytes):
    l = [hex(int(i)) for i in bytes]
    return " ".join(l)

def get_int16(data, index):
    a = data[index]
    b = data[index + 1]
    return (((a & 0xFF) << 8) + (b & 0xFF))

weight = 0
weight_kg = 0
weight_lb = 0

def callback(sender: BleakGATTCharacteristic, data: bytearray):
    global weight
    global weight_kg
    global weight_lb

    status = data[5]
    if status == 0:
        temp_weight = get_int16(data, 3) / 100
        temp_weight_lb = kg_to_lb(temp_weight)
        print(f"Weight still unsteady, hold on... {temp_weight_lb}lb")
    elif status == 1:
        weight = get_int16(data, 3)
        weight_kg = weight / 100
        weight_lb = kg_to_lb(weight_kg)
    else:
        print(f"Unknown status byte value {status:X}: data = {print_hex(data)}")


async def scan(address):
    global weight
    weight = 0
    print("Waiting for scale to appear...")
    async with BleakClient(address) as client:
        await client.start_notify(read_service, callback)

        await client.write_gatt_char(write_service, bytes(hello_magic))
        await client.write_gatt_char(write_service, bytes(timestamp_bytes))

        timeout = 10
        while weight == 0 and timeout > 0:
            await asyncio.sleep(1.0)
            timeout -= 1

        if timeout == 0:
            raise StabilizationTimeoutException

        await client.write_gatt_char(write_service, bytes(goodbye_magic))

        print(f"Weight: {weight_lb}lb")
        send_discord_message(f"Weight: Raw: {weight} {weight_kg}kg {weight_lb}lb")
        record_weight_sqlite(weight, weight_kg, weight_lb)


async def main():
    while True:
        try:
            await scan(address)
            print("Waiting 10 seconds before polling again")
            time.sleep(10)
        except BleakDeviceNotFoundError:
            print("Device not found, polling again...")
        except StabilizationTimeoutException:
            print("Timed out waiting for stabilization, starting over...")
        except Exception as e:
            print(f"Error, {e}")
            print("Waiting 10 seconds before polling again")
            time.sleep(10)

asyncio.run(main())
