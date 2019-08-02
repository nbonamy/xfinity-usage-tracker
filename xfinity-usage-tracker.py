#!/usr/bin/env python3
import os
import sys
import json
import time
import utils
import datetime
import argparse
import webbrowser
import logging as log
from consts import *
from calendar import monthrange
from xfinity_usage.xfinity_usage import XfinityUsage

def parse_args(argv):
	p = argparse.ArgumentParser(description='Track Xfinity data usage', prog='xfinity-usage-tracker')
	p.add_argument('-l', '--log', action='store_const', const=True, help='log to file')
	p.add_argument('-d', '--debug', action='store_const', const=True, help='log debug traces')
	p.add_argument('-j', '--json', action='store_const', const=True, help='display json')
	p.add_argument('-o', '--offset', action='store', dest='XFINITY_OFFSET', default=0, help='time offset')
	p.add_argument('-u', '--username', action='store', dest='XFINITY_USER', help='Xfinity username')
	p.add_argument('-p', '--password', action='store', dest='XFINITY_PASS', help='Xfinity password')
	p.add_argument('-g', '--gsheet', action='store', dest='XFINITY_GSHEET', help='Google Spreasheet Id')
	args = p.parse_args(argv)
	return args

def finish(args, usageData, sheetUrl):

	# cgi requires header
	if isCgi:
		print('Status: 200 OK')
		if args.json:
			print('Content-Type: application/json')
		elif sheetUrl:
			print('Location: index.html')
		print()

	# now content
	if args.json:
		print(json.dumps(usageData))
	elif not isCgi and sheetUrl:
		webbrowser.open_new_tab(gSheetUrl)

	# done
	log.info('Done!')
	exit()

# get context
isCgi = 'GATEWAY_INTERFACE' in os.environ
args = parse_args(sys.argv[1:])

# logging: we need to remove handlers as xfinity-usage lib defined its own
for handler in log.root.handlers[:]:
	log.root.removeHandler(handler)

# add our now
logLevel = log.DEBUG if args.debug else log.INFO
if isCgi or args.log:
	log.basicConfig(filename='./xfinity-usage-tracker.log', filemode='w', level=logLevel)
else:
	log.basicConfig(level=logLevel)

# get config
xfinityUser = utils.getConfigValue(args, XFINITY_USER)
xfinityPass = utils.getConfigValue(args, XFINITY_PASS)
xfinityOffset = int(utils.getConfigValue(args, XFINITY_OFFSET, 0))
xfinityBrowser = utils.getConfigValue(args, XFINITY_BROWSER, 'chrome-headless')
dateFormat = utils.getConfigValue(args, DATE_FORMAT, DEFAULT_DATE_FORMAT)
warnThreshold = utils.getConfigValue(args, XFINITY_WARNING, -1)
gSheetId = utils.getConfigValue(args, XFINITY_GSHEET)
gSheetUrl = utils.getGoogleSheetUrl(gSheetId)

# default
warnThreshold = 0.90 if warnThreshold < 0 else float(warnThreshold)

# check
if not xfinityUser or not xfinityPass:
	log.critical('Environment not properly setup. Aborting')
	if isCgi:
		print('Status: 500 Server Error')
	print()
	print('You must define the environment variables {0} and {1} for this script to work'.format(XFINITY_USER, XFINITY_PASS))
	print('Also remember to define {0} if you want your tracking spreadsheet to be updated'.format(XFINITY_GSHEET))
	print('And to setup email settings if you want to be notified of over usage (see README.md)')
	exit(1)

# log
#print()
#print('Getting usage data from xfinity (this can take some time)')

# get the data
log.info('Getting usage data from xfinity')
#usageData = { JSON_CAP: 1024, JSON_USAGE: 482, JSON_NOW: int(time.time()) }
#usageData = json.load(open('data/sample.json'))
xfinityUsage = XfinityUsage(xfinityUser, xfinityPass, browser_name=xfinityBrowser)
usageData = xfinityUsage.run()

# log
log.debug(json.dumps(usageData))

# get basic data
usedData = usageData[JSON_USAGE]
capValue = usageData[JSON_CAP]
log.info('Monthly cap = {0} GB'.format(capValue))

# get timestamp
jsonTimestamp = usageData[JSON_NOW]
execDate = datetime.datetime.fromtimestamp(jsonTimestamp).strftime(dateFormat)
log.info('Execution date = {0}'.format(execDate))

# offset
if xfinityOffset != 0:
	log.info('Offsetting timestamp by {0} hour(s)'.format(xfinityOffset))
	jsonTimestamp = jsonTimestamp + xfinityOffset * 60 * 60

# now get some value
now = datetime.datetime.fromtimestamp(jsonTimestamp)
measureDate = now.strftime(dateFormat)
year = now.year
month = now.month
day = now.day
hour = now.hour
minute = now.minute
now = round((day - 1) + (hour * 60 + minute) / (24 * 60), 3)
log.info('Measure Date = {0}'.format(measureDate))
log.info('Month progress = {0}'.format(now))

# if warning enabled calc target and compare
days = monthrange(year, month)[1]
targetData = int(capValue) / days * now
log.info('Current usage = {0}, target = {1}, threshold={2}'.format(usedData, targetData, targetData * warnThreshold))
if usedData > targetData * warnThreshold:
	smtpUser = utils.getConfigValue(args, XFINITY_SMTP_USER)
	warnEmailTo = utils.getConfigValue(args, XFINITY_EMAIL_TO) or smtpUser
	warnEmailFrom = utils.getConfigValue(args, XFINITY_EMAIL_FROM) or warnEmailTo
	if not warnEmailTo:
		log.warn('Mail disabled: no recipient email setup')
	else:
		utils.sendMail(
			warnEmailFrom,
			warnEmailTo,
			'Xfinity usage = {0:.0f} GB (target is {1:.0f} GB)\n\n'.format(usedData, targetData),
			gSheetUrl if gSheetId else ''
		)

# if we have no spreadsheet, simply output the json
if not gSheetId:
	log.info('No Google spreadsheet specified.')
	finish(args, usageData, False)

# use creds to create a client to interact with the Google Drive API
log.info('Connecting to Google spreadsheet')
book = utils.openGoogleSheet(gSheetId)

# update current usage
log.info('Updating data sheet')
dataSheet = book.get_worksheet(DATA_SHEET_INDEX)
dataSheet.update_acell(DATE_CELL, execDate)
dataSheet.update_acell(NOW_CELL, now)
dataSheet.update_acell(CAP_CELL, capValue)
dataSheet.update_acell(USAGE_CELL, usedData)

# update history
historySheet = book.get_worksheet(HIST_SHEET_INDEX)

# check month
historyMonth = int(historySheet.acell(HIST_MONTH_CELL).value)
log.debug('Spreadsheet month history = {0}'.format(historyMonth))
if month != historyMonth:

	# if 1st of month
	if day == 1:

		# get previous month
		log.debug('1st day of month: checking previous month final number')
		prevYear = year if month > 1 else year - 1
		prevMonth = month if month > 1 else 12
		prevMonthDays = monthrange(prevYear, prevMonth)[1]
		prevHistUsage = historySheet.cell(prevMonthDays + HIST_START_ROW - 1, HIST_START_COL).value
		if prevHistUsage:
			log.debug('Previous month last day already has data. Not updating.')
		else:
			usageMonths = usageData[JSON_DETAILS][JSON_HISTORY]
			prevMonthUsage = int(usageMonths[len(usageMonths)-1-1][JSON_HIST_USAGE])
			historySheet.update_cell(prevMonthDays + HIST_START_ROW - 1, HIST_START_COL, prevMonthUsage)
			log.info('Updating previous month last day usage: {0}'.format(prevMonthUsage))

	# copy or not
	if utils.getConfigValue(args, XFINITY_SAVE_HISTORY, False):
		log.info('Archiving previous month history')
		year = year-1 if historyMonth == 12 else year
		title = 'History {:02d}/{:02d}'.format(historyMonth, year-int(year/100)*100)
		book.duplicate_sheet(historySheet.id, HIST_SHEET_INDEX+1, new_sheet_name=title)

		# now freeze values
		log.info('Freezing values in archive')
		archiveSheet = book.get_worksheet(HIST_SHEET_INDEX+1)
		historyCells = archiveSheet.range(HIST_START_ROW, HIST_START_COL-1, HIST_START_ROW+31-1, HIST_END_COL)
		archiveSheet.update_cells(historyCells, value_input_option='USER_ENTERED')

	# clear previous month history
	log.info('Clearing previous month history')
	for d in range(1,32):
		historySheet.update_cell(d + HIST_START_ROW - 1, HIST_START_COL, '')
	historySheet.update_acell(HIST_MONTH_CELL, month)

# now update daily value
log.info('Updating history sheet')
historySheet.update_cell(day + HIST_START_ROW - 1, HIST_START_COL, usedData)

# delete cache
utils.deleteFile(CACHE_USAGE)

# done
finish(args, usageData, gSheetUrl)
