# Network PVR Scripts
This is a collection of scripts for a network-accessible PVR running TVHeadend v4. It was designed and tested on a Raspberry Pi running Raspbian, but it should be straightforward to modify for other Unix-based systems running TVHeadend as well.

## Dependencies

The scripts are build on Python 2.7.x and require the `psutil` module.

## Usage

`PVRtransfer.py` is a script designed to be called by TVHeadend once a recording is complete. The recording is then transferred to a network share (i.e. NAS or a workstation where it can be edited). It can be called by TVHeadend as follows:

```
PVRtransfer.py %f %e
```


## History

* 2015-07-06 First developed PVR transfer script for TVHeadend v3.
* 2016-01-26 Overhauled PVR transfer script and separated email configuration into separate scripts.
* 2018-07-06 Migrated to Github, including historical script versions.

## Copyright and Licence

Unless otherwise stated, these scripts are Copyright © Joshua White and licensed under the GNU Lesser GPL v3.

* `oauth2.py` is Copyright © Google Inc. and licensed under the Apache License Version 2.0.
* HTSP client library is Copyright © Adam Sutton and licensed under the GNU GPL 3.0.
