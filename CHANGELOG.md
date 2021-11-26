# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.ht
ml).

## master
  [1.0.11-beta]

## testing
  [1.0.12-beta]

## [1.0.12-beta]
- [changes] #187 now is possible duplicate slots of RAM.

## [1.0.11-beta]
- [addend] #186 adding property power_on_hours.

## [1.0.10-beta]
- [addend] #170 can delete/deactivate devices.
- [bugfix] #168 can to do a trade without devices.
- [added] #167 new actions of status devices: use, recycling, refurbish and management.
- [changes] #177 new structure of trade.
- [bugfix] #184 clean nested of schemas of lot
- [added] #182 adding power on hours

## [1.0.9-beta]
- [added] #159 external document as proof of erase of disk
- [added] #162 adding lot for devices unassigned


## [1.0.8-beta]
- [bugfix] #161 fixing DataStorage with bigInteger

## [1.0.7-beta]
- [added] #158 support for encrypted snapshots data
- [added] #135 adding trade system
- [added] #140 adding endpoint for download the settings for usb workbench

## [1.0.6-beta]
- [bugfix] #143 biginteger instead of integer in TestDataStorage

## [1.0.5-beta]
- [added] #124 adding endpoint for extract the internal stats of use
- [added] #122 system for verify all documents that it's produced from devicehub
- [added] #127 add one code for every named tag
- [added] #131 add one code for every device
- [bugfix] #138 search device with devicehubId

## [1.0.4-beta]
- [added] #95 adding endpoint for check the hash of one report
- [added] #98 adding endpoint for insert a new live
- [added] #98 adding endpoint for get all licences in one query
- [added] #102 adding endpoint for download metrics
- [bugfix] #100 fixing bug of scheme live
- [bugfix] #101 fixing bug when 2 users have one device and launch one live
- [changes] #114 clean blockchain of all models
- [changes] #118 deactivate manual merge
- [changes] #118 clean datas of public information of devices
- [remove] #114 remove proof system 

## [1.0.3-beta]
- [added] #85 add mac of network adapter to device hid
- [changed] #94 change form of snapshot manual

## [1.0.2-beta]
- [added] #87 allocate, deallocate and live actions
- [fixed] #89 save json on disk only for shapshots
- [added] #83 add owner_id in all kind of device
- [fixed] #91 The most old time allow is 1970-01-01
