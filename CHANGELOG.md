# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.ht
ml).

## master

## testing

## [2.0.0] - 2022-03-15
First server render HTML version. Completely rewrites views of angular JS client on flask.
- [added] #193 render on backend devices and lots
- [added] #195 render on backend tags system
- [added] #196 render on backend action system
- [added] #201 render on backend Data Wipe action
- [added] #203 render on backend Trade action
- [added] #204 render on backend export files
- [added] #205 UX improvements
- [added] #208 render on backend filter for type of devices in the general list
- [changed] #191 pass to drop teal and use the pure flask and use render from flask
- [changed] #207 Create automatic tag only for Computers.
- [changed] #209 adding a new device in a lot if it is created from a lot
- [fixed] #206 fix 2 bugs about visibility devices when you are not the owner

## [1.0.12-beta]
- [changed] #187 now is possible duplicate slots of RAM.
- [changed] #188 Excel report devices allow to see device to old owners.

## [1.0.11-beta]
- [added] #186 adding property power_on_hours.

## [1.0.10-beta]
- [added] #170 can delete/deactivate devices.
- [added] #167 new actions of status devices: use, recycling, refurbish and management.
- [added] #182 adding power on hours
- [changed] #177 new structure of trade.
- [fixed] #168 can to do a trade without devices.
- [fixed] #184 clean nested of schemas of lot

## [1.0.9-beta]
- [added] #159 external document as proof of erase of disk
- [added] #162 adding lot for devices unassigned


## [1.0.8-beta]
- [fixed] #161 fixing DataStorage with bigInteger

## [1.0.7-beta]
- [added] #158 support for encrypted snapshots data
- [added] #135 adding trade system
- [added] #140 adding endpoint for download the settings for usb workbench

## [1.0.6-beta]
- [fixed] #143 biginteger instead of integer in TestDataStorage

## [1.0.5-beta]
- [added] #124 adding endpoint for extract the internal stats of use
- [added] #122 system for verify all documents that it's produced from devicehub
- [added] #127 add one code for every named tag
- [added] #131 add one code for every device
- [fixed] #138 search device with devicehubId

## [1.0.4-beta]
- [added] #95 adding endpoint for check the hash of one report
- [added] #98 adding endpoint for insert a new live
- [added] #98 adding endpoint for get all licences in one query
- [added] #102 adding endpoint for download metrics
- [changed] #114 clean blockchain of all models
- [changed] #118 deactivate manual merge
- [changed] #118 clean datas of public information of devices
- [fixed] #100 fixing bug of scheme live
- [fixed] #101 fixing bug when 2 users have one device and launch one live
- [removed] #114 remove proof system

## [1.0.3-beta]
- [added] #85 add mac of network adapter to device hid
- [changed] #94 change form of snapshot manual

## [1.0.2-beta]
- [added] #87 allocate, deallocate and live actions
- [added] #83 add owner_id in all kind of device
- [fixed] #89 save json on disk only for shapshots
- [fixed] #91 The most old time allow is 1970-01-01
