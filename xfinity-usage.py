#!C:\Program Files\Python37\Python.exe
import os
import ssl
import json
import time
import gspread
import smtplib
import datetime
import webbrowser
import logging as log
from calendar import monthrange
from xfinity_usage.xfinity_usage import XfinityUsage
from oauth2client.service_account import ServiceAccountCredentials

# some constants
CONFIG_FILE = "config.json"
XFINITY_USER = 'XFINITY_USER'
XFINITY_PASS = 'XFINITY_PASS'
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
def getConfigValue(name, default=False):
	value = os.getenv(name)
	if not value:
		config = json.load(open(CONFIG_FILE))
		if name in config:
			value = config[name]
	if not value and default:
		value = default
	return value
	
# get context
isCgi = 'GATEWAY_INTERFACE' in os.environ
xfinityUser = getConfigValue(XFINITY_USER)
xfinityPass = getConfigValue(XFINITY_PASS)
xfinityBrowser = getConfigValue(XFINITY_BROWSER)
warnThreshold = getConfigValue(XFINITY_WARNING)
gSheetId = getConfigValue(XFINITY_GSHEET)
gSheetUrl = 'https://docs.google.com/spreadsheets/d/{0}'.format(gSheetId)

# default
xfinityBrowser = xfinityBrowser or 'chrome-headless'
warnThreshold = 0.90 if not warnThreshold else float(warnThreshold)

# logging: we need to remove handlers as xfinity-usage lib defined its own
for handler in log.root.handlers[:]:
	log.root.removeHandler(handler)
log.basicConfig(filename='./xfinity-usage.log', filemode='w', level=log.INFO)

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
#usageData = json.load(open('sample.json'))
xfinityUsage = XfinityUsage(xfinityUser, xfinityPass, browser_name=xfinityBrowser)
usageData = xfinityUsage.run()

# log
log.debug(json.dumps(usageData))

# get basic data
usedData = usageData[JSON_USAGE]
capValue = usageData[JSON_CAP]
log.info('Monthly cap = {0} GB'.format(capValue))

# get timestamp and extract some values
now = datetime.datetime.fromtimestamp(usageData[JSON_NOW])
year = now.year
month = now.month
day = now.day - 1
hour = now.hour
minute = now.minute
now = round(day + (hour * 60 + minute) / (24 * 60), 2)
log.info('Date = {}/{}/{} {}:{}'.format(year,month, day+1, hour, minute))
log.info('Now = {0}'.format(now))

# if warning enabled calc target and compare
if day == 0:
	log.info('Current usage = {0}. Fisrt day of month: skipping over usage check'.format(usedData))
else:
	days = monthrange(year, month)[1]
	targetData = int(capValue) / days * now
	log.info('Current usage = {0}, target = {1}, threshold={2}'.format(usedData, targetData, targetData * warnThreshold))
	if usedData > targetData * warnThreshold:
		smtpUser = getConfigValue(XFINITY_SMTP_USER)
		warnEmailTo = getConfigValue(XFINITY_EMAIL_TO) or smtpUser
		if not warnEmailTo:
			log.warn('Mail disabled: no recipient email setup')
		else:

			smtpHost = getConfigValue(XFINITY_SMTP_HOST) or SMTP_GMAIL if smtpUser.endswith('@gmail.com') else ''
			if not smtpHost:
				log.warn('Should warn but SMTP host not defined')
			else:

				try:
					# connect to smtp server
					smtpPort = getConfigValue(XFINITY_SMTP_PORT)
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
						server.login(smtpUser, getConfigValue(XFINITY_SMTP_PASS))

					# build and send email
					warnEmailFrom = getConfigValue(XFINITY_EMAIL_FROM) or warnEmailTo
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
	if isCgi:
		print('Status: 200 OK')
		print('Content-Type: application/json')
		print()
	print(json.dumps(usageData))
	exit()

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
if day > 0 and not historySheet.cell(day + HIST_START_ROW - 1, HIST_START_COL).value:
	log.info('Updating history sheet')
	historySheet.update_cell(day + HIST_START_ROW - 1, HIST_START_COL, usedData)

# redirect or open
if isCgi:
	print('Location: {0}'.format(gSheetUrl))
	print()
else:
	webbrowser.open_new_tab(gSheetUrl)

# done
log.info('Done!')
