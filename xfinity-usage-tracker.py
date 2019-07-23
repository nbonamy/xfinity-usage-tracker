#!/usr/bin/env python3
import os
import sys
import ssl
import json
import time
import gspread
import smtplib
import datetime
import argparse
import webbrowser
import logging as log
from calendar import monthrange
from xfinity_usage.xfinity_usage import XfinityUsage
from oauth2client.service_account import ServiceAccountCredentials

# some constants
CONFIG_FILE = 'config.json'
XFINITY_USER = 'XFINITY_USER'
XFINITY_PASS = 'XFINITY_PASS'
XFINITY_OFFSET = 'XFINITY_OFFSET'
XFINITY_BROWSER = 'XFINITY_BROWSER'
XFINITY_GSHEET = 'XFINITY_GSHEET'
XFINITY_WARNING = 'XFINITY_WARNING'
XFINITY_SMTP_HOST = 'XFINITY_SMTP_HOST'
XFINITY_SMTP_PORT = 'XFINITY_SMTP_PORT'
XFINITY_SMTP_USER = 'XFINITY_SMTP_USER'
XFINITY_SMTP_PASS = 'XFINITY_SMTP_PASS'
XFINITY_EMAIL_FROM = 'XFINITY_EMAIL_FROM'
XFINITY_EMAIL_TO = 'XFINITY_EMAIL_TO'
SMTP_GMAIL = 'smtp.gmail.com'
SMTP_PORT = 25
SMTP_PORT_SSL = 465
SMTP_PORT_TLS = 587
JSON_USAGE = 'used'
JSON_CAP = 'total'
JSON_NOW = 'data_timestamp'
GSHEET_SECRET = 'client_secret.json'
DATA_SHEET_INDEX = 0
CAP_CELL = 'B2'
NOW_CELL = 'B5'
USAGE_CELL = 'B7'
HIST_SHEET_INDEX = 1
HIST_MONTH_CELL = 'B1'
HIST_START_ROW = 4
HIST_START_COL = 2

# to get configuration
def getConfigValue(args, name, default=False):

	# first check args
	if name in vars(args).keys():
		value = vars(args)[name]
		if value:
			return value

	# now environment variable
	value = os.getenv(name)
	if value:
		return value

	# if not found look in config
	config = json.load(open(CONFIG_FILE))
	if name in config:
		value = config[name]

	# fallback to default
	return value if value else default

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
			print('Location: {0}'.format(sheetUrl))
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
xfinityUser = getConfigValue(args, XFINITY_USER)
xfinityPass = getConfigValue(args, XFINITY_PASS)
xfinityOffset = int(getConfigValue(args, XFINITY_OFFSET, 0))
xfinityBrowser = getConfigValue(args, XFINITY_BROWSER, 'chrome-headless')
warnThreshold = getConfigValue(args, XFINITY_WARNING)
gSheetId = getConfigValue(args, XFINITY_GSHEET)
gSheetUrl = 'https://docs.google.com/spreadsheets/d/{0}'.format(gSheetId)

# default
warnThreshold = 0.90 if not warnThreshold else float(warnThreshold)

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

# offset
if xfinityOffset != 0:
	log.info('Offsetting timestamp by {0} hour(s)'.format(xfinityOffset))
	jsonTimestamp = jsonTimestamp + xfinityOffset * 60 * 60

# now get some value
now = datetime.datetime.fromtimestamp(jsonTimestamp)
year = now.year
month = now.month
day = now.day
hour = now.hour
minute = now.minute
now = round((day - 1) + (hour * 60 + minute) / (24 * 60), 2)
log.info('Date = {}/{:02d}/{:02d} {:02d}:{:02d}'.format(year,month, day, hour, minute))
log.info('Now = {0}'.format(now))

# if warning enabled calc target and compare
days = monthrange(year, month)[1]
targetData = int(capValue) / days * now
log.info('Current usage = {0}, target = {1}, threshold={2}'.format(usedData, targetData, targetData * warnThreshold))
if usedData > targetData * warnThreshold:
	smtpUser = getConfigValue(args, XFINITY_SMTP_USER)
	warnEmailTo = getConfigValue(args, XFINITY_EMAIL_TO) or smtpUser
	if not warnEmailTo:
		log.warn('Mail disabled: no recipient email setup')
	else:

		smtpHost = getConfigValue(args, XFINITY_SMTP_HOST) or SMTP_GMAIL if smtpUser.endswith('@gmail.com') else ''
		if not smtpHost:
			log.warn('Should warn but SMTP host not defined')
		else:

			try:
				# connect to smtp server
				smtpPort = getConfigValue(args, XFINITY_SMTP_PORT)
				smtpPort = int(smtpPort) if smtpPort else (SMTP_PORT_SSL if smtpHost == SMTP_GMAIL else SMTP_PORT)
				log.debug('SMTP: Connecting to server {}:{}'.format(smtpHost, smtpPort))
				server = smtplib.SMTP_SSL(smtpHost, smtpPort)
				server.ehlo()
				if smtpPort == SMTP_PORT_TLS:
					log.debug('SMTP: Enabling TLS')
					server.starttls()
					server.ehlo()
				if smtpUser:
					log.debug('SMTP: Authenticating')
					server.login(smtpUser, getConfigValue(args, XFINITY_SMTP_PASS))

				# build and send email
				warnEmailFrom = getConfigValue(args, XFINITY_EMAIL_FROM) or warnEmailTo
				emailText  = 'From: {0}\n'.format(warnEmailFrom)
				emailText += 'To: {0}\n'.format(warnEmailTo)
				emailText += 'Subject: Xfinity usage = {0:.0f} GB (target is {1:.0f} GB)\n\n'.format(usedData, targetData)
				emailText += gSheetUrl if gSheetId else ''
				server.sendmail(warnEmailFrom, warnEmailTo, emailText)

				# done
				server.close()
				log.info('Warning mail sent')

			except Exception as e:
				log.error(e)
				pass

# if we have no spreadsheet, simply output the json
if not gSheetId:
	log.info('No Google spreadsheet specified.')
	finish(args, usageData, False)

# use creds to create a client to interact with the Google Drive API
log.info('Connecting to Google spreadsheet')
scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name(GSHEET_SECRET, scope)
client = gspread.authorize(creds)

# update current usage
log.info('Updating data sheet')
book = client.open_by_key(gSheetId)
dataSheet = book.get_worksheet(DATA_SHEET_INDEX)
dataSheet.update_acell(NOW_CELL, now)
dataSheet.update_acell(CAP_CELL, capValue)
dataSheet.update_acell(USAGE_CELL, usedData)

# update history
historySheet = book.get_worksheet(HIST_SHEET_INDEX)

# check month
historyMonth = int(historySheet.acell(HIST_MONTH_CELL).value)
log.debug('Spreadsheet month history = {}'.format(historyMonth))
if month != historyMonth:
	log.info('Clearing previous month history')
	# clear previous month history
	for d in range(1,32):
		historySheet.update_cell(d + HIST_START_ROW - 1, HIST_START_COL, '')
	historySheet.update_acell(HIST_MONTH_CELL, month)

# now update daily value if not done yet
# when run on first day of month this does not make sense as monthly usage has just been reset to 0
# so we cannot even record usage as of last day of previous month...
log.info('Updating history sheet')
historySheet.update_cell(day + HIST_START_ROW - 1, HIST_START_COL, usedData)

# done
finish(args, usageData, gSheetUrl)
