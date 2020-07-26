#! /usr/bin/python

import datetime
import socket
import sys


def make_serial_number(now):
  serial = now.year - 2020
  serial *= 12
  serial += now.month - 1
  serial *= 31
  serial += now.day
  serial *= 12
  serial += now.hour
  serial *= 60
  serial += now.minute
  serial *= 60
  serial += now.second
  return str(serial)

sub = sys.argv[1]
domain = sys.argv[2]
serial_idx = int(sys.argv[3]) if len(sys.argv) > 3 else 1

# open a connection to something external to get our IP address
address = socket.gethostbyname(socket.gethostname())

# create the serial number
serial = make_serial_number(datetime.datetime.now())

with open("/root/host-domain.tplt", "r") as fh:
  text = fh.read().format(sub=sub, domain=domain, ip=address, serial=serial)
  print(text)
