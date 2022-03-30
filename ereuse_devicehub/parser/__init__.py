from pathlib import Path

from pint import UnitRegistry

# Sets up the unit handling
unit_registry = Path(__file__).parent / 'unit_registry'

unit = UnitRegistry()
unit.load_definitions(str(unit_registry / 'quantities.txt'))
TB = unit.TB
GB = unit.GB
MB = unit.MB
Mbs = unit.Mbit / unit.s
MBs = unit.MB / unit.s
Hz = unit.Hz
GHz = unit.GHz
MHz = unit.MHz
Inch = unit.inch
mAh = unit.hour * unit.mA
mV = unit.mV

base2 = UnitRegistry()
base2.load_definitions(str(unit_registry / 'base2.quantities.txt'))

GiB = base2.GiB
