#!/usr/bin/env python3
import json
import utils
from consts import *

# get config
gSheetId = utils.getConfigValue(None, XFINITY_GSHEET)

# update current usage
book = utils.openGoogleSheet(gSheetId)
dataSheet = book.get_worksheet(0)
cap = int(dataSheet.acell(CAP_CELL).value.split()[0])
target = int(dataSheet.acell(TARGET_CELL).value.split()[0])
usage = int(dataSheet.acell(USAGE_CELL).value.split()[0])

# echo
print('Content-Type: application/json')
print()
print(json.dumps({
	'cap': cap,
	'usage': usage,
	'warning': target*GRAPH_WARNING,
	'error': target
}))
