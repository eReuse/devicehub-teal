# Definitions
* A dpp is two hash strings joined by the character ":"
  We call the first chain chid and the second phid.

* The chid and phid are hash strings of certain values.
  We call the set of these values Documents.
  Here we define these values.
  
## Chid
The chid is the part of dpp that defines a device, be it a computer,
a hard drive, etc. The chid is the most important part of a dpp since
anyone who comes across a device should be able to play it.

The chid is made up of four values:
   * type
   * manufacturer
   * model
   * serial_number

type represents the device type according to the devicehub.

These values are always represented in lowercase.
These values have to be ordered and concatenated with the character "-"

So:

   {type}-{manufacturer}-{model}-{serial_number}

For example:
```
harddrive-seagate-st500lt0121dg15-s3p9a81f

```

In computer types this combination is not perfect and **can lead to collisions**.
That is why we need a value that is reliable and comes from the manufacturer.

## Phid
The values of the phid do not have to be reproducible. For this reason, each inventory can establish its own values and its order as a document.
It is important that each inventory store the document in string so that it can reproduce exactly the document that was hashed. So a document can be verifiable.

In the case of the DeviceHub, we use as the chid document all the values that the Workbench collects that describe the hardware's own data.
These data change depending on the version of the Workbench used.
