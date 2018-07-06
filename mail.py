#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:        mail
# Purpose:     Send emails using smtplib. Can use oauth2 to send via Gmail.
#
# Author:      Joshua White
#
# Created:     26/01/2016
# Copyright:   (c) Joshua White 2016-2018
# Licence:     GNU Lesser GPL v3
#-------------------------------------------------------------------------------

'''
In order to use OAuth 2.0, you need to follow the instructions found at:
https://github.com/google/gmail-oauth2-tools/wiki/OAuth2DotPyRunThrough

1. You must register your application through the Google APIs Console:

https://code.google.com/apis/console

2. Use the API Console to create a client id.
3. Enter the client id and client secret into mailConfig.py.
4. Run this script with -i to initialise the tokens. This will automatically 
get the refresh and access tokens, as well as the expiry date and save these.
It will enable automatic regeneration of access tokens.

If you wish to do the steps manually:

4. Create a token:

python oauth2.py --generate_oauth2_token --client_id=ID --client_secret=SECRET

5. Authorise the token.
6. Copy both the access and refresh tokens.
7. Create an OAuth2 authentication string:

python oauth2.py --generate_oauth2_string --access_token=ACCESS_TOKEN --user=USER_EMAIL

8. Test SMTP:

python oauth2.py --test_smtp_authentication --access_token=ACCESS_TOKEN --user=USER_EMAIL

9. Use the authentication string for accessing Gmail.

Note that the access token expires after 1 hour. Your application needs to save 
the refresh token and generate a new access token as required.

Put your Gmail address, client id, client secret and refresh token into mailConfig.py.
Access tokens will be generated every time using this method.
'''

import os
import sys
import datetime
import mailConfig
from optparse import OptionParser

try:
	import smtplib
	useSMTP = True and mailConfig.smtp_en
except ImportError, err:
	useSMTP = False

try:
	import oauth2
	useOAuth = True
except ImportError, err:
	useOAuth = False

try:
	import json
except ImportError, err:
	import simplejson as json
	
try:
	#Python 2.6+
	from email.mime.multipart import MIMEMultipart
	from email.mime.text import MIMEText
except ImportError, err:
	#Python 2.4
	from email.MIMEMultipart import MIMEMultipart
	from email.MIMEText import MIMEText

if not useSMTP and not useOAuth:
	import subprocess
	
PATH = os.path.abspath(os.path.dirname(__file__))
SCRIPTNAME = os.path.splitext(os.path.basename(__file__))[0]
LOGFILE = os.path.join(PATH, '%s.log' % SCRIPTNAME)
EMAILFILE = os.path.join(PATH, '%s.email' % SCRIPTNAME)
TOKENFILE = os.path.join(PATH, '%s.token' % SCRIPTNAME)
opts = None

class DateEncoder(json.JSONEncoder):
	'''Class to extend JSON encoder, courtesy of http://stackoverflow.com/questions/12316638/psycopg2-execute-returns-datetime-instead-of-a-string'''
	def default(self, obj):
		'''Internal function for <DateEncoder>. Converts a datetime object to a string.'''
		if isinstance(obj, datetime.date):
			return obj.strftime('%Y-%m-%d %H:%M:%S') # Do this instead of returning str(obj) to avoid timezone field
		return json.JSONEncoder.default(self, obj)
		

def logPrint(text):
	'''Print to the screen and write to the log file.'''

	now = datetime.datetime.now()
	nowstr = now.strftime('%Y-%m-%d %H:%M:%S')

	f = open(LOGFILE, 'a')
	f.write('%s\t%s\n' % (nowstr, text))
	f.close()
	
	
def initOptions():
	'''System argument processing.'''
	global opts

	usage = "usage: %prog [options]"
	parser = OptionParser(usage=usage)

	parser.add_option("-g", "--generate",
					  action="store_true", dest="initialise", default=False,
					  help="Generate the OAuth tokens (requires OAuth Client ID & Secret to be entered into mailConfig.py)")
	parser.add_option("-i", "--isp",
					  action="store_true", dest="useISP", default=False,
					  help="Send email via ISP relay (must be specified in mailConfig)")
	parser.add_option("-t", "--test",
					  action="store_true", dest="test", default=False,
					  help="Run email test (sends to address specified in mailConfig)")
	parser.add_option("-s", "--subject",
					  dest="subject", default="No Subject Specified",
					  help="Specify the subject string for the email.")
	parser.add_option("-r", "--recipient",
					  dest="recipient", default=mailConfig.user,
					  help="Specify the recipient for the email.")
	parser.add_option("-f", "--file",
					  dest="textfile", default=None,
					  help="Specify a plain-text file to use for the text content of the email.")
	parser.add_option("-l", "--html",
					  dest="htmlfile", default=None,
					  help="Specify a html file to use for the html content of the email.")

	(opts, args) = parser.parse_args()
	return opts, args
	

def sendEmail(recipient=mailConfig.user, subject='No Subject Specified', bodytext=None, bodyhtml=None):
	'''Send an email via Gmail using OAuth authentication.
	Requires mailConfig.py is appropriately pre-filled with user data.'''

	# Check to see if we're using the ISP relay options
	relay = ((opts and opts.useISP) or mailConfig.isp_en) and len(mailConfig.isp_relay) > 0

	# Set the subject and body for test purposes
	if opts and opts.test:
		subject = "Test Email"
		bodytext = "This is a test email."
		logPrint("Preparing to send a test email.")
	
	# Send the message via the selected SMTP server
	if relay:
		smtp_conn = smtplib.SMTP(mailConfig.isp_relay)
		logPrint("Connected to SMTP server (ISP relay).")

	# Use OAuth 2.0
	elif useOAuth:
		# Check for a token file
		if os.path.exists(TOKENFILE):
			f = open(TOKENFILE, 'r')
			tokendata = json.load(f)
			expiry = datetime.datetime.strptime(tokendata['expiry'], '%Y-%m-%d %H:%M:%S')
			f.close()
			
			# Check for expired access token
			now = datetime.datetime.now()
			if expiry < now:
				logPrint("Access token expired. Generating a new token.")
				response = oauth2.RefreshToken(mailConfig.client_id, mailConfig.client_secret, tokendata['refresh'])
				tokendata['access'] = response['access_token']
				tokendata['expiry'] = now + datetime.timedelta(seconds=response['expires_in'])
				
				# Update the saved token data
				f = open(TOKENFILE, 'w')
				json.dump(tokendata, f, cls=DateEncoder)
				f.close()
				
			access_token = tokendata['access']
				
		# Otherwise just generate a new access token each time
		else:
			response = oauth2.RefreshToken(mailConfig.client_id, mailConfig.client_secret, mailConfig.refresh_token)
			access_token = response['access_token']
			
		# Prepare for authentication
		oauth2_string = oauth2.GenerateOAuth2String(mailConfig.user, access_token)
		logPrint("Authentication string generated.")
		
		# Set up the connection
		smtp_conn = smtplib.SMTP('smtp.gmail.com', 587)
		if opts and opts.test:
			smtp_conn.set_debuglevel(True)
		smtp_conn.ehlo()
		smtp_conn.starttls()
		smtp_conn.docmd('AUTH', 'XOAUTH2 ' + oauth2_string)
		logPrint("Connected to SMTP server using OAuth.")
		
	# Use smtplib manually with username and password (not recommended)
	elif useSMTP and mailConfig.smtp_en:
		# Use mail server
		smtp_conn = smtplib.SMTP(mailConfig.smtp_server, mailConfig.smtp_port)
		smtp_conn.ehlo()
		if mailConfig.smtp_starttls:
			smtp_conn.starttls()
			smtp_conn.ehlo()
			
		smtp_conn.login(mailConfig.smtp_username, mailConfig.smtp_password)
		logPrint("Connected to SMTP server using account credentials.")

	# Use subprocess and rely on system-configured SSMTP
	else:
		logPrint("Preparing to send email via ssmtp subprocess.")

		# Prepare email header
		email = '''MIME-Version: 1.0\nContent-Type: text/html\nTo: <%s>\nFrom: "%s" <%s>\nReply-To: "%s" <%s>\nSubject: %s\n\n%s''' % (recipient, mailConfig.sender, mailConfig.sender, mailConfig.replytoname, mailConfig.replyto, subject, bodytext)
		email = email.encode('ascii')

		# Have to write contents to a file. Won't work if you try to echo or cat it.
		f = open(EMAILFILE,'w')
		f.write(email)
		f.close()

		cmdstr = '%s %s < "%s"' % (mailConfig.ssmtp_binary, recipient, EMAILFILE)
		try:
			subprocess.call(cmdstr, shell=True)
			os.remove(EMAILFILE)
			logPrint('Email sent.')

		except Exception, err:
			logPrint('Error sending email:\n%s' % str(err))
			
		return
	
	# Assemble the email
	msg = MIMEMultipart('alternative')
	msg['From'] = "%s <%s>" % (mailConfig.username, mailConfig.sender)
	msg['Reply-To'] = "%s <%s>" % (mailConfig.replytoname, mailConfig.replyto)
	msg['To'] = recipient
	msg['Subject'] = subject

	if bodytext is not None:
		textBody = MIMEText(bodytext, 'plain')
		msg.attach(textBody)

	if bodyhtml is not None:
		htmlBody = MIMEText(bodyhtml, 'html')
		msg.attach(htmlBody)

	# Send the email
	smtp_conn.sendmail(mailConfig.user, recipient, msg.as_string())
	smtp_conn.close()
	logPrint("Email sent.")


def prepEmail(subject=None, recipient=None, textfile=None, htmlfile=None):
	'''Check for body content to read in and send.'''
	
	bodytext = None
	bodyhtml = None

	# Choose between the arguments to this function and the option parser
	textpath = textfile or (opts and opts.textfile)
	htmlpath = htmlfile or (opts and opts.htmlfile)
	subject = subject or (opts and opts.subject)
	recipient = recipient or (opts and opts.recipient)
	
	# Check if there's a text file to use for the body
	if textpath is not None and os.path.exists(textpath):
		f = open(textpath, 'r')
		bodytext = f.read()
		f.close()
	
	# Check if there's a HTML file to use for the body
	if htmlpath is not None and os.path.exists(htmlpath):
		f = open(htmlpath, 'r')
		bodyhtml = f.read()
		f.close()

	sendEmail(subject=subject, recipient=recipient, bodytext=bodytext, bodyhtml=bodyhtml)


def initialiseOAuth():
	'''Initialise the OAuth token file using the client id and secret.'''
	
	# Authorise the app
	print 'Visit the following URL to authorise the token:'
	print oauth2.GeneratePermissionUrl(mailConfig.client_id, 'https://mail.google.com/')
	print 
	authorisation_code = raw_input('Enter verification code: ')
	
	# Get the access and refresh tokens
	response = oauth2.AuthorizeTokens(mailConfig.client_id, mailConfig.client_secret, authorisation_code)
	print 'Refresh Token: %s' % response['refresh_token']
	print 'Access Token: %s' % response['access_token']
	
	# Calculate the expiry for the access token
	expiry = datetime.datetime.now() + datetime.timedelta(seconds=response['expires_in'])
	tokendata = {
		'refresh': response['refresh_token'],
		'access': response['access_token'],
		'expiry': expiry,
	}
	
	f = open(TOKENFILE, 'w')
	json.dump(tokendata, f, cls=DateEncoder)
	f.close()
	
if __name__ == '__main__':
	initOptions() # Parse command-line parameters

	if opts.initialise:
		logPrint('Command-line request for OAuth initialisation.')
		initialiseOAuth()
	elif opts.test:
		logPrint('Command-line request for test email.')
		sendEmail()
	else:
		logPrint('Command-line request for email.')
		prepEmail()