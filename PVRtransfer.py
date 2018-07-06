#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:        PVR Transfer v2
# Purpose:     Process finished TVHeadEnd recordings and transfer them to 
#              a NFS share.
#
# Author:      Joshua White
#
# Created:     26/01/2016
# Copyright:   (c) Joshua White 2016-2018
# Licence:     GNU Lesser GPL v3
#-------------------------------------------------------------------------------

"""
	Network PVR Transfer Script.

	Arguments:
		- full path to recording file
		- error string

	TVHeadEnd Example:
		RPiPVR.py %f %e

"""

import os
import sys
import datetime
import hashlib # Python 2.5+
import shutil
import signal
import mail
try:
	import json # Python 2.5+
except ImportError, err:
	import simplejson as json # Python 2.4
	
PATH = os.path.abspath(os.path.dirname(__file__))
SCRIPT = os.path.splitext(os.path.basename(__file__))
LOGFILE = os.path.join(PATH, '%s.log' % SCRIPT[0])
EMAILFILE = os.path.join(PATH, '%s.email' % SCRIPT[0])

# GLOBAL VARIABLES
nfs_share = '/mnt/nas-pvr/' # NFS share to be used as destination for completed recordings
tvh = '/home/hts/.hts/tvheadend/dvr/log' # Path to scheduled recordings (JSON)
recompute = False # Recompute checksums if checksum file found
pvr_interval = datetime.timedelta(hours = 1) # Minimum time between finished recording and next recording required for processing
recipient = '' # Email recipient


def logPrint(text):
	'''Print to the screen and write to the log file.'''

	now = datetime.datetime.now()
	nowstr = now.strftime('%Y-%m-%d %H:%M:%S')

	f = open(LOGFILE, 'a')
	f.write('%s\t%s\n' % (nowstr, text))
	f.close()


def sendEmail(subject, text=None, html=None):
	'''Send the email using the mail module.'''
	
	mail.sendEmail(recipient=recipient, subject=subject, bodytext=text, bodyhtml=html)

	
def alertNFS(msg):
	'''Send an email alert that the NFS share is down.'''

	message = 'The NFS share was not accessible: %s' % msg
	sendEmail('NFS share not accessible', text=message)


def alertTransfer(recording, checksum, error):
	'''Send an email that a file transfer failed.'''

	message = 'The transfer of file recording %s or checksum file %s to the NFS \
share failed due to an error: \n\n%s' % (recording, checksum, error)
	sendEmail('File transfer failed', text=message)


def alertTVHError(recording, error):
	'''Send an email that TVHeadEnd posted an error.'''

	logPrint('TVHeadend Error: %s' % error)
	message = 'TVHeadend reported an error with the recording %s: \n\n%s' % (recording, error)
	sendEmail('TVHeadend Error', text=message)

	# Do not exit here - still need to process old recordings.


def handleShareError(signum, frame):
	'''Alert if the NFS mount times out.'''

	msg = "Stale NFS mount!"
	logPrint(msg)
	alertNFS(msg)
	sys.exit(1)


def generateFileChecksum(filepath, blockscale=2048):
	'''File checksum, based on
	http://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python
	http://stackoverflow.com/questions/3431825/generating-a-md5-checksum-of-a-file

	Default block size is 2048 * 64 = 128K for SHA256. This seems to be optimal
	for the RPi Model 1B.'''

	# Checksum algorithm
	# Prefer SHA256 over MD5 due to poor collision resistance in MD5
	a = hashlib.sha256()
	b = blockscale*a.block_size

	with open(filepath, "rb") as f:
		for chunk in iter(lambda: f.read(b), b''):
			a.update(chunk)
	return a.hexdigest()


def generateChecksum(filepath):
	'''Create a checksum and write it to a file.'''

	fname = os.path.basename(filepath)
	(fn, ext) = os.path.splitext(filepath)
	chkfile = '%s.sha2' % fn

	# Check if file already exists
	existing = os.path.exists(chkfile)

	if not existing or recompute:
		chksum = generateFileChecksum(filepath)
		logPrint('Generated SHA256 checksum for %s: %s' % (fname, chksum))

		f = open(chkfile, 'w')
		f.write("%s *%s" % (chksum, fname))
		f.close()

	return chkfile


def checkShare(report=True):
	'''Check if the NFS share is mounted correctly.'''

	mounted = False
	writable = False

	try:
		# Use a signal alarm as a timeout to prevent stale NFS mounts hanging
		signal.signal(signal.SIGALRM, handleShareError)
		signal.alarm(15)

		# First check if the path is mounted
		mounted = os.path.ismount(nfs_share)

		if mounted:
			signal.alarm(0) # Disable the alarm
			testfile = os.path.join(nfs_share, '.rpi.pvr')

			# If the path is mounted, test writing to it
			try:
				handle = open(testfile, 'w')
				writable = True
				handle.close()

				# Clean up the test file
				os.remove(testfile)

			except IOError, err:
				msg = 'Unable to write to NFS share.'
				logPrint(msg)
				if report:
					alertNFS(msg)
					sys.exit(1)

	except Exception, err:
		signal.alarm(0) # Disable the alarm
		msg = 'Error checking NFS share.'
		logPrint(msg)
		if report:
			alertNFS(msg)
			sys.exit(1)

	logPrint('NFS share mounted = %s, writable = %s' % (mounted, writable))

	return (mounted, writable)


def checkRecordings():
	'''Check for upcoming recordings.'''

	now = datetime.datetime.now()
	limit = now + pvr_interval

	# Get list of current scheduled recordings
	schedules = [ f for f in os.listdir(tvh) if os.path.isfile(os.path.join(tvh,f)) ]

	for s in schedules:
		# Read the schedule
		handle = open(os.path.join(tvh,s), 'r')
		content = json.load(handle)
		handle.close()

		# Check the start and end timestamps
		dts = datetime.datetime.fromtimestamp(content['start'])
		dte = datetime.datetime.fromtimestamp(content['stop'])

		if (dts < now < dte):
			logPrint('Aborted due to conflict with current recording.')
			sys.exit(0)

		elif (now < dts < limit):
			logPrint('Aborted due to conflict with next scheduled recording.')
			sys.exit(0)

	logPrint('No conflicting recordings found, proceeding...')


def moveRecording(recording, chkfile):
	'''Move the recording and the checksum file to the NFS share.'''

	# Generate the full destination paths
	r = os.path.basename(recording)
	dest_r = os.path.abspath(os.path.join(nfs_share, r))
	dest_c = os.path.abspath(os.path.join(nfs_share, os.path.basename(chkfile)))

	# Attempt to move the recording and checksum to the NAS
	try:
		shutil.move(recording, dest_r)
		shutil.move(chkfile, dest_c)
		logPrint('Successfully transferred recording (%s) to NFS share.' % (r))

	except shutil.Error, err:
		e = str(err)
		alertTransfer(recording, chkfile, e)
		logPrint('Error transferring recording (%s) to NFS share:\n%s' % (r, e))


def processRecording(recording):
	'''Main thread to process a recording file.'''

	logPrint('About to process recording %s' % recording)

	# Check for any upcoming recordings
	checkRecordings()

	# Check for NFS share access
	checkShare()

	# Generate the checksum for the recording
	chkfile = generateChecksum(recording)

	# Move the recording and checksum file to the share
	moveRecording(recording, chkfile)


def checkForRecordings(abort=True):
	'''Check for any old recordings that weren't transferred for some reason;
	i.e. back-to-back recordings.'''

	now = datetime.datetime.now()
	limit = now + pvr_interval
	upcoming = None
	completed = {}

	# Get list of current scheduled recordings
	schedules = [ f for f in os.listdir(tvh) if os.path.isfile(os.path.join(tvh,f)) ]

	for s in schedules:

		# Read the schedule
		handle = open(os.path.join(tvh,s), 'r')
		content = json.load(handle)
		handle.close()

		# Check the start and end timestamps
		dts = datetime.datetime.fromtimestamp(content['start'])
		dte = datetime.datetime.fromtimestamp(content['stop'])

		# We have a completed recording
		if dte < now and content.has_key('filename') and os.path.exists(content['filename']):
			completed[s] = content['filename']

		# Check when the next recording is
		if dts > now:
			if upcoming is None or dts < upcoming:
				upcoming = dts

		# Check for ongoing recording
		if (dts < now < dte) and abort:
			logPrint('Aborted due to conflict with current recording.')
			sys.exit(0)

	# Check time to next recording
	if (upcoming < limit) and abort:
		logPrint('Aborted due to conflict with next scheduled recording.')
		sys.exit(0)

	# Exit if there were no previous recordings to process
	if len(completed.keys()) < 1 and abort:
		sys.exit(0)

	return (completed, upcoming)


def processPreviousRecordings():
	'''Process any previous recordings that might still be on the local HDD.'''

	# Check for recordings
	(recordings, nextrec) = checkForRecordings()

	# Check for NFS share access
	checkShare()

	# Process each completed recording
	for r in recordings:
		recfile = recordings[r]

		# Check current time to next recording
		now = datetime.datetime.now()
		limit = now + pvr_interval

		if nextrec < limit:
			logPrint('Skipped unprocessed recordings due to next scheduled recording.')
			sys.exit(0)

		# Generate the checksum and move the recording
		chkfile = generateChecksum(recfile)
		moveRecording(recfile, chkfile)


def scriptTest():
	'''Test some of the script functionality.'''

	# Test checksum functionality
	try:
		scriptChksum = generateFileChecksum(__file__)
	except Exception, err:
		scriptChksum = 'Unable to generate the checksum for the script: %s' % str(err)

	# Test NFS share access
	try:
		(nfs_mount, nfs_write) = checkShare(False)
		nfs_msg = 'NFS share mounted = %s, writable = %s.' % (nfs_mount, nfs_write)
	except Exception, err:
		nfs_msg = 'Error checking NFS share: %s' % str(err)

	# Test checking for recordings
	try:
		(completed, upcoming) = checkForRecordings(False)
		rec_msg = '%s completed recordings; next recording scheduled for %s.' % (len(completed.keys()), upcoming)
	except Exception, err:
		rec_msg = 'Unable to check for recordings: %s' % str(err)

	# Assemble the message
	message = '''This is a test email from the Network PVR script.
		<br />Checksum: %s<br />%s<br />%s''' % (scriptChksum, nfs_msg, rec_msg)
	txt = message.replace('<br />', '\n\n')
	sendEmail('Network PVR Test Email', text=txt, html=message)



if __name__ == '__main__':
	args = len(sys.argv)

	if '-t' in sys.argv:
		scriptTest() # Script testing

	else:
		if args > 2: # Error specified
			hts_err = sys.argv[2]
			recording = sys.argv[1]

			if hts_err.strip() == 'OK':
				processRecording(recording)
			else:
				alertTVHError(recording, hts_err)

		elif args > 1: # Recording name specified
			recording = sys.argv[1]
			processRecording(recording)

		try:
		   # Check for any old recordings
			processPreviousRecordings()

		except Exception, err:
			logPrint(str(err))
