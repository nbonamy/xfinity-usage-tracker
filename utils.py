import os
import json
import gspread
import smtplib
import logging as log
from consts import *
from oauth2client.service_account import ServiceAccountCredentials

# to get configuration values
def getConfigValue(args, name, default=False):

	# first check args
	if args and name in vars(args).keys():
		value = vars(args)[name]
		if value:
			return value

	# now environment variable
	value = os.getenv(name)
	if value:
		return value

	# if not found look in config
	config = loadJson(CONFIG_FILE)
	if config and name in config:
		value = config[name]
		return value

	# fallback to default
	return default

# get google sheer url
def getGoogleSheetUrl(sheetId):
	return 'https://docs.google.com/spreadsheets/d/{0}'.format(sheetId)

# to open a google sheet
def openGoogleSheet(sheetId):

	# use creds to create a client to interact with the Google Drive API
	scope = ['https://spreadsheets.google.com/feeds']
	creds = ServiceAccountCredentials.from_json_keyfile_name(GSHEET_SECRET, scope)
	client = gspread.authorize(creds)

	# now open
	book = client.open_by_key(sheetId)
	return book

# send mail
def sendMail(mailFrom, mailTo, subject, body):

	smtpUser = getConfigValue(None, XFINITY_SMTP_USER)
	smtpHost = getConfigValue(None, XFINITY_SMTP_HOST) or SMTP_GMAIL if smtpUser.endswith('@gmail.com') else ''
	if not smtpHost:
		log.warn('Should warn but SMTP host not defined')
		return False

	try:
		# connect to smtp server
		smtpPort = getConfigValue(None, XFINITY_SMTP_PORT)
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
			server.login(smtpUser, getConfigValue(None, XFINITY_SMTP_PASS))

		# build and send email
		emailText  = 'From: {0}\n'.format(mailFrom)
		emailText += 'To: {0}\n'.format(mailTo)
		emailText += 'Subject: {0}\n\n{1}'.format(subject, body)
		server.sendmail(mailFrom, mailTo, emailText)

		# done
		server.close()
		log.info('Warning mail sent')

	except Exception as e:
		log.error(e)
		pass

def deleteFile(file):
	try:
		os.remove(file)
		return True
	except:
		return False

def loadJson(file):
	try:
		return json.load(open(file))
	except:
		return None

def saveJson(file, data):
	try:
		with open(file, 'w') as f:
			json.dump(data, f)
		return True
	except:
		return False

