# xfinity-usage-tracker
This tool tracks your Xfinity usage and:

 - Can notify you if your are using more than you should during the month
 - Update a Google Spreadsheet that gives you an overview of your monthly usage

## Requirements

 - Python3
 - xfinity-usage ([https://github.com/jantman/xfinity-usage](https://github.com/jantman/xfinity-usage))
- gspread ([https://github.com/burnash/gspread](https://github.com/burnash/gspread))

Dependencies can be installed using

    pip install -r requirements.txt

## Setup
The script requires a number of configuration values to be defined. You can define them as environment variables or in a JSON configuration file. It should be named `config.json` and placed in the same folder as the script.
### Xfinity data collection
Xfinity data collection requires two variables:

 - `XFINITY_USER`: your Xfinity username
 - `XFINITY_PASS`: your Xfinity account password

### Mail alert
The script can alert you if your data usage is above a certain threshold of what it should be. For instance, if your data cap is 1024 GB, and today is half month, you should have used no more than 512 GB. The script can alert you if you used more than 90% (can be changed) of those 512 GB so far.
Configuration values are:

 - `XFINITY_SMTP_HOST`: Hostname of your SMTP server
 - `XFINITY_SMTP_PORT`: Port of your SMTP server
 - `XFINITY_SMTP_USER`: Username to authenticate on your SMTP server
 - `XFINITY_SMTP_PASS`: Password to authenticate on your SMTP server
 - `XFINITY_EMAIL_FROM`: Email of the sender of the message
 - `XFINITY_EMAIL_TO`: Email of the recipient of the message
 - `XFINITY_WARNING`: Change the warning threshold. Default value is 0.9. Set it to 0 to always send a mail.

If you use a gmail account, you can only setup `XFINITY_SMTP_USER` and `XFINITY_SMTP_PASS`. All other parameters will be set automatically. It is recommended to generate an App Password ([https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)).

### Tracking spreadsheet
![google spreadsheet](img/gsheet.jpg?s=200)
To automatically update the tracking spreadsheet, first make a copy of the [template spreadsheet](https://docs.google.com/spreadsheets/d/1qOlky2kmSPPd09E3s1AzVnfBIbZUpi5MOuvAiip2MWs) in your Google Drive.

You then need then to enable API access to this copy. Please follow the instructions here: [https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html](https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html). Save the JSON credentials as `client_secret.json` in the same folder as the script. Do not forget to share the spreadsheet with the email address specified in `client_secret.json` (`client_email` key).

Once this is done, you need to define the following configuration:

 - `XFINITY_GSHEET`: id of your Google spreadsheet. You can extract that from the URL displayed by your browser when you view the file. If the URL is `https://docs.google.com/spreadsheets/d/abcd8673ef/edit#gid=0` then the ID is `abcd8673ef`.

## Scheduling
You can use your favorite scheduler (cron or Windows Task Scheduler) to automatically launch the script. It is recommended to run it once a day around 1am but you can run it more often if desired. Please check the disclaimer on [https://github.com/jantman/xfinity-usage](https://github.com/jantman/xfinity-usage): it is also valid for xfinity-usage-tracker.

## As a webserver
Configuring your favorite webserver (Apache or Nginx) is not documented here. You need to run the script as a CGI script.
As the process can take some time, a waiting page (`index.html`) is provided.
