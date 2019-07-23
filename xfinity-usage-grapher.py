#!/usr/bin/env python3
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

# now replace
with open(TMPL_FILE, 'r') as file:
	tmpl = file.read()
	print(tmpl.format(cap, round(target*GRAPH_WARNING/cap*100), round(target/cap*100), round(usage/cap*100), usage))
