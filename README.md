# Network PVR Scripts
This is a collection of scripts for a network-accessible PVR running TVHeadend v4. It was designed and tested on a Raspberry Pi running Raspbian, but it should be straightforward to modify for other Unix-based systems running TVHeadend as well.

## Dependencies

The scripts are built on Python 2.7.x and require the `psutil` module.

## Installation and Configuration

1. Download or clone a copy of the repository to your preferred location. 
2. Copy `mailConfig.template` to `mailConfig.py` and populate the parameters as required (this is required for email functionality).
3. Edit `PVRtransfer.py` and add your email address and TVHeadend account details.
4. Test the script using the `-t` option.


## Usage

### PVRtransfer.py

This script is designed to be called by TVHeadend once a recording is complete. All completed recordings are then transferred to a network share (i.e. NAS or a workstation where they can be edited). The script can be called by TVHeadend as follows:

```
PVRtransfer.py %f %e
```

Existing recordings can be manually processed using the `-p` option, rather than waiting for the next recording to complete. **Note**: when called by TVHeadend, the script will not transfer recordings if another recording is underway or about to begin.

The script includes a test option (`PVRtransfer.py -t`) to do a complete check of the script and parts of the system:

- test ability to generate checksums
- test network share access
- check completed and scheduled recordings
- check if TVHeadend is running
- test HTSP connectivity
- check free space
- email the results to test email functionality

It also has a basic system check option (`PVRtransfer.py -c`) that can be used for debugging (or in a cron job) and will run a subset of the above tests:

- check free space
- check if TVHeadend is running
- send an email if a problem is found


## History

* 2015-07-06 First developed PVR transfer script for TVHeadend v3.
* 2016-01-26 Overhauled PVR transfer script and separated email configuration into separate scripts.
* 2018-07-06 Migrated to Github, including historical script versions.

## Copyright and Licence

Unless otherwise stated, these scripts are Copyright © Joshua White and licensed under the GNU Lesser GPL v3.

* `oauth2.py` is Copyright © Google Inc. and licensed under the Apache License Version 2.0.
* HTSP client library is Copyright © Adam Sutton and licensed under the GNU GPL 3.0.
