#!/usr/bin/env python3
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# some constants
CONFIG_FILE = 'config.json'
GSHEET_SECRET = 'client_secret.json'
XFINITY_GSHEET = 'XFINITY_GSHEET'
TMPL_FILE = 'tmpl/graph.tmpl'
WARNING_THRESHOLD = 0.9
CAP_CELL = 'B2'
TARGET_CELL = 'B6'
USAGE_CELL = 'B7'

# to get configuration
def getConfigValue(name, default=False):

	# environment variable
	value = os.getenv(name)
	if value:
		return value

	# if not found look in config
	config = json.load(open(CONFIG_FILE))
	if name in config:
		value = config[name]

	# fallback to default
	return value if value else default

# get config
gSheetId = getConfigValue(XFINITY_GSHEET)

# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name(GSHEET_SECRET, scope)
client = gspread.authorize(creds)

# update current usage
book = client.open_by_key(gSheetId)
dataSheet = book.get_worksheet(0)
cap = int(dataSheet.acell(CAP_CELL).value.split()[0])
target = int(dataSheet.acell(TARGET_CELL).value.split()[0])
usage = int(dataSheet.acell(USAGE_CELL).value.split()[0])

# now replace
with open(TMPL_FILE, 'r') as file:
	tmpl = file.read()
	print(tmpl.format(cap, round(target*WARNING_THRESHOLD/cap*100), round(target/cap*100), round(usage/cap*100), usage))
