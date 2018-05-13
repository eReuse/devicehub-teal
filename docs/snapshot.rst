Snapshot
========
The Snapshot updates the state of the device with information about its components and events
performed at them.

When receiving a Snapshot, the DeviceHub creates, adds and removes components to match the
Snapshot. For example, if a Snapshot of a computer contains a new component, the system will
search for the component in its database and, if not found, create it, and finally adding it
to the computer.

Snapshots can bundle some events, usually tests and hard-drive erasures. In such case the
DeviceHub will save those events.

A Snapshot is used with Remove to represent changes in components for a device:
1. A device is created in the database always with a Snapshot. If this device had components,
   they are created (if they did not existed before) in the same time with the same Snapshot.
2. Time after, a new Snapshot updates component information. If, for example, this new Snasphot
   doesn't have a component, it means that this component is not present anymore in the device,
   thus removing it from it. Then we have that:
     - Components to add: snapshot2.components - snapshot1.components
     - Components to remove: snapshot1.components - snapshot2.components
   When adding a component, there may be the case this component existed before and it was
   inside another device. In such case, DeviceHub will perform ``Remove`` on the old parent.
