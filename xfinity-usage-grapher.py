#!/usr/bin/env python3
import json
import math
import utils
import datetime
from consts import *

# get config
gSheetId = utils.getConfigValue(None, XFINITY_GSHEET)
gSheetUrl = utils.getGoogleSheetUrl(gSheetId)

# update current usage
book = utils.openGoogleSheet(gSheetId)
dataSheet = book.get_worksheet(0)
now = float(dataSheet.acell(NOW_CELL, value_render_option='UNFORMATTED_VALUE').value)
cap = int(dataSheet.acell(CAP_CELL).value.split()[0])
target = int(dataSheet.acell(TARGET_CELL).value.split()[0])
usage = int(dataSheet.acell(USAGE_CELL).value.split()[0])

# translate now back to timestamp
today = datetime.datetime.today()
today = datetime.datetime(today.year, today.month, today.day)
now = math.modf(now)[0] * 24 * 60 * 60
now = today.timestamp() + round(now, 0)

# compensate offset
xfinityOffset = int(utils.getConfigValue(None, XFINITY_OFFSET, 0))
now = now - xfinityOffset * 60 * 60

# echo
print('Content-Type: application/json')
print()
print(json.dumps({
	'now': now,
	'cap': cap,
	'usage': usage,
	'warning': target*GRAPH_WARNING,
	'error': target,
	'gsheet': gSheetUrl
}))
