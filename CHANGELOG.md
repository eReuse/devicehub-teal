# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.ht
ml).

## testing

## [2.5.3] - 2023-05-13
- [added] #450 add new datawipe in csv.
- [changed] #447 Share a lot between 2 users, one is owner the other is read only.
- [changed] #448 enhancements in export lots.
- [changed] #449 remove button of submit in filter of list of devices.
- [changed] #452 New version of settings for workbench.
- [fixed] #445 required File for new documents bat optional for edit document.
- [fixed] #446 Fix id_supplier and id_internal in export devices.
- [fixed] #451 fix new datawipe in certificate erasure.
- [fixed] #453 fix value method in certificate erasure.
- [fixed] #454 remove validation of email for placeholders type mobile.
- [fixed] #455 add placeholders in csv metrics and pdf certificate.
- [fixed] #456 upload placeholders with type datastorage.
- [fixed] #457 change format erase datawipe.
- [fixed] #458 not datawipe for placeholders computers.

## [2.5.2] - 2023-04-20
- [added] #414 add new vars in the settings file for wb.
- [added] #440 add lots in export devices.
- [added] #441 allow remove documents.
- [added] #442 allow edit documents.
- [added] #443 add documents to devices.
- [added] #444 add new columns in list of documents.
- [changed] #439 move teal as internal module.
- [fixed] #437 replace names erasure by sanitization in templates.

## [2.5.1] - 2023-03-17
- [changed] #423 new hid.
- [changed] #426 new version of public page of device.
- [changed] #427 update links of terms and condotions.
- [changed] #428 only the data storage allow syncrinize, the rest are duplicate.
- [changed] #430 new version of erasure certificate.
- [fixed] #416 fix dhid in snapshot logs.
- [fixed] #419 fix settings version and template.
- [fixed] #420 not appear all lots in the dropdown menu for select the a lot.
- [fixed] #421 fix remove a placeholder from one old trade lot.
- [fixed] #422 fix simple datatables.
- [fixed] #424 fix new hid.
- [fixed] #431 fix forms for customer details.
- [fixed] #432 fix erasure certificate for a servers.
- [fixed] #433 fix get the last incoming for show customer datas in certificate.
- [fixed] #434 fix reopen transfer.
- [fixed] #436 fix hid in erasure certificate.

## [2.5.0] - 2022-11-30
- [added] #407 erasure section with tabs in top.
- [added] #411 add new generic device as Other.
- [changed] #409 add backend pagination instead of javascript.
- [changed] #410 change teh top search for advanced search.
- [fixed] #412 show in snapshots log, type upload correctly.
- [fixed] #413 put order in documents.
- [fixed] #415 put prefix of lot in result of search.

## [2.4.3] - 2022-11-18
- [added] #386 add registration module.
- [added] #387 add template settings for Secure Erasure.
- [added] #397 add obada standard export.
- [added] #402 add reset password module.
- [added] #406 add orphans disks page.
- [changed] #391 add dhid in table and export of Erasure section.
- [changed] #395 change response for the new api to workbench.
- [changed] #396 modularize commands.
- [fixed] #388 lock update different motherboard with the same id.
- [fixed] #389 some datastorage without placeholder.
- [fixed] #390 fix image in form edit device.
- [fixed] #398 placeholder in new components.
- [fixed] #399 add api_host in config.
- [fixed] #401 db_host need to be api address.
- [fixed] #403 change delimiter in obada export.
- [fixed] #404 javascript select all devices.
- [fixed] #405 update pillow.

## [2.4.2] - 2022-10-18
- [added] #373 Enhancement - UX Lots.
- [added] #377 add prefix in lots in device list.
- [added] #378 add new button transfer.
- [added] #381 add servers erase and show storage disk in list of device.
- [added] #383 new setup page and add server_erase in placeholder.
- [added] #384 add redirect snapshot to twin public page.
- [changed] #371 changes phid.
- [changed] #372 remove logo.
- [changed] #374 changes links UI management and Data Storage Erasure.
- [changed] #375 changes columns in snapshot logs.
- [changed] #379 changes representation date times.
- [fixed] #380 fix layout print label.
- [fixed] #382 fix template device list.
- [fixed] #385 components in unbinding process.

## [2.4.1] - 2022-10-05
- [added] #365 Manage dependencies using pip-tools.
- [added] #368 add migrations of monitors and mobiles.
- [changed]] #371 changes about phid, incremental per user.
- [fixed] #364 bad redirect to all devices.
- [fixed] #367 column PHID Erasure host.
- [fixed] #369 bug in test data storage.
- [fixed] #370 print label in details of the label.

## [2.4.0] - 2022-09-23
- [added] #312 Placeholder: new, edit, update. (manually and with excel).
- [added] #316 Placeholder: binding/unbinding. (manually).
- [added] #319 Add command report cli.
- [added] #326 settings for user demo.
- [added] #327 add Binding.
- [added] #328 export placeholders.
- [added] #330 workbench page.
- [added] #334 backup dhid and phid.
- [added] #340 add parth number for placeholders.
- [added] #349 add a new columns in report.
- [added] #356 new export hdds.
- [added] #362 add new columns in a snapshot log.
- [changed] #329 update Binding.
- [changed] #331 update workbench page.
- [changed] #338 change labels when add a new device.
- [changed] #339 change description upload placeholders page.
- [changed] #342 change concepts for binding, (Twin).
- [changed] #344 add "Ods File" as description in Placeholders Logs.
- [changed] #345 remove generation concept of device.
- [changed] #346 change editable device page.
- [changed] #347 change snapshot instead of abstract and placeholder instead of real.
- [changed] #348 change buttons new device.
- [changed] #355 changes links.
- [changed] #357 change button "New Actions".
- [changed] #358 change report device.
- [changed] #360 add placeholder device in lot instead of devices.
- [changed] #361 change message in form add device.
- [fixed] #313 Bump numpy from 1.21.6 to 1.22.0.
- [fixed] #314 bugs create placeholder from lot.
- [fixed] #317 bugs about exports placeholders.
- [fixed] #318 bugs about unlink tag of device.
- [fixed] #321 bugs in labels of serial number.
- [fixed] #322 validation imei for mobil.
- [fixed] #323 bug export devices.
- [fixed] #335 bugs in excel phid with nan.
- [fixed] #336 bugs Unassigned is visualized in all device view.
- [fixed] #337 bugs upload csv placeholders.
- [fixed] #343 forze Phid to by a string.
- [fixed] #350 bugs in certificates.
- [fixed] #351 bugs devices without phid.
- [fixed] #352 export certificate for placeholders.
- [fixed] #353 get the last update of the one device twin.
- [fixed] #354 titles of table.
- [fixed] #359 fix backup dhid.
- [fixed] #363 problems with render add documents in a transfer lot.

## [2.3.0] - 2022-07-12
- [added] #281 Add selenium test.
- [added] #305 Add button to download ISO Workbench.
- [added] #306 Add link to download JSON snapshot.
- [added] #308 Add sentry.
- [changed] #302 Add system uuid to check the identity of one device.
- [fixed] #309 Column lifecycle status is always empty.

**IMPORTANT**: PR #302 involves some changes in the deployment process:
```bash
# First, run script `extract_uuids.sh` before applying alembic migrations (e.g. with schema `dbtest`)
sh scripts/extract_uuids.sh

# Then, apply alembic migrations
alembic -x inventory=dbtest upgrade head
```

**NOTE**: If you forget (or don't need) to run this script before applying new migration it will work but any device will be updated.

## [2.2.0] - 2022-06-24
- [changed] #304 change anchor of link devices lots.
- [fixed] #315 create in a lot a new placeholder.

## [2.2.0 rc2] - 2022-06-22
- [added] #299 Multiselect with Shift.
- [added] #300 Add Sid in label.
- [added] #301 Add logo in label.
- [added] #303 Add export Lots.
- [added] #303 Add export relating lots with devices.
- [added] #303 To do possible add and remove one device in one lot transfer.

## [2.2.0 rc1] - 2022-06-07
- [added] #212 Server side render parser Workbench Snapshots.
- [added] #225 List of snapshots.
- [added] #265 Add feature for download Workbench settings.
- [added] #268 Add column created in device list.
- [added] #270 Add tags in device list.
- [added] #271 Add view for show all devices.
- [added] #272 Show lots on deviceList.
- [added] #273 Allow search/filter lots on lots management component.
- [added] #274 Add columns status in device list.
- [added] #277 Add developement build & precomit build.
- [added] #289 Add transfer.
- [added] #290 Add advanced search.
- [added] #291 SnapshotLog in old api.
- [added] #292 Add delivery note and receiver note.
- [changed] #275 remove all components in the filter of the device list.
- [changed] #282 upgrade dependencies pyjwt from 2.0.0a1 to 2.4.0.
- [changed] #283 Change visual format for dates in device list.
- [changed] #293 add options in select number of items per page. (50, 100)
- [fixed] #263 Fix select All devices options in select filter.
- [fixed] #267 ESLint ignore builded JS files.
- [fixed] #269 Allocate bugs.
- [fixed] #276 Create Computer Monitor instead of Monitor in form of create a new device.
- [fixed] #280 fix enums in migration process.
- [fixed] #284 Allocate bugs.
- [fixed] #285 lots search not working.
- [fixed] #287 apply button out of card.

## [2.1.1] - 2022-05-11
Hot fix release.
- [fixed] #256 JS support to old browsers using babel.
- [fixed] #266 Fix error when trade.document.url is None on device_list.html

## [2.1.0] - 2022-05-11
- [added] #219 Add functionality to searchbar (Lots and devices).
- [added] #222 Allow user to update its password.
- [added] #233 Filter in out trades from lots selector.
- [added] #236 Allow select multiple devices in multiple pages.
- [added] #237 Confirmation dialog on apply lots changes.
- [added] #238 Customize labels.
- [added] #242 Add icons in list of devices.
- [added] #244 Select full devices.
- [added] #257 Add functionality to search generic categories like all components.
- [added] #252 new tabs lots and public link in details of one device.
- [changed] #211 Print DHID-QR label for selected devices.
- [changed] #218 Add reactivity to device lots.
- [changed] #220 Add reactive lots list.
- [changed] #232 Set max lots list to 20.
- [changed] #235 Hide trade buttons.
- [changed] #239 Change Tags for Unique Identifier.
- [changed] #247 Change colors.
- [changed] #253 Drop download public links.
- [fixed] #214 Login workflow
- [fixed] #221 Fix responsive issues on frontend.
- [fixed] #223 fix trade lots modal.
- [fixed] #224 fix clickable lots selector not working when click in text.
- [fixed] #254 Fix minor types in frontend.
- [fixed] #255 Fix status column on device list.


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
