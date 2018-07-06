#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:        mailConfig
# Purpose:     User configuration variables for gmail XOAuth script.
#
# Author:      Joshua White
#
# Created:     26/01/2016
# Copyright:   (c) Joshua White 2016-2018
# Licence:     GNU Lesser GPL v3
#-------------------------------------------------------------------------------

# GMAIL OAUTH
# Fill out the fields below to config sending via a Gmail account

# User puts their client id, client secret and refresh token here
client_id = ''
client_secret = ''
refresh_token = ''

# User puts their email address and the name they want to appear as here
user = ''
username = ''

# MAIL PLAINTEXT AUTHENTICATION
# Set smtp_en = True and populate these fields to directly 
# authenticate with your mail server using a username and password
# This is NOT recommended

smtp_en = False # Default False
smtp_server = ''
smtp_port = ''
smtp_starttls = True # Default True
smtp_username = ''
smtp_password = ''

# SSMTP ALTERNATIVE
# Enter the path to your ssmtp binary here

ssmtp_binary = '/usr/sbin/ssmtp'

# ISP RELAY ALTERNATIVE
# Enable/disable use of the ISP relay
# Enter your ISP relay address here
isp_en = False # Default False
isp_relay = ''

# GENERAL SETTINGS
# The user may leave these as default or customise the values
replyto = user # Default is user
replytoname = username # Default is username
sender = user # Default is user
