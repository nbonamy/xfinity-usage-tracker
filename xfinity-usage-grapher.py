#!/usr/bin/env python3
import os
import json
import math
import utils
import datetime
from consts import *

# check cache file
data = utils.loadJson(CACHE_USAGE)
if not data:

	try:

		# get config
		gSheetId = utils.getConfigValue(None, XFINITY_GSHEET)
		gSheetUrl = utils.getGoogleSheetUrl(gSheetId)

		# update current usage
		book = utils.openGoogleSheet(gSheetId)
		dataSheet = book.get_worksheet(0)
		date = dataSheet.acell(DATE_CELL).value
		cap = int(dataSheet.acell(CAP_CELL).value.split()[0])
		target = int(dataSheet.acell(TARGET_CELL).value.split()[0])
		usage = int(dataSheet.acell(USAGE_CELL).value.split()[0])
		today = int(dataSheet.acell(TODAY_CELL).value.split()[0])

		# build data
		data = {
			'date': date,
			'cap': cap,
			'usage': usage,
			'today': today,
			'warning': int(target*GRAPH_WARNING),
			'error': target,
			'gsheet': gSheetUrl
		}

		# write cache
		utils.saveJson(CACHE_USAGE, data)

	except:
		data = None

# echo
print('Content-Type: application/json')
print()
print(json.dumps(data))
