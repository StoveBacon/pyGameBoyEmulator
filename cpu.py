from functools import partial
from operator import setitem
from typing import Final, Tuple

from byteops import uint8, uint16, unsigned_16
from memory import Memory

ZERO_MASK: Final[uint8] = 0x80
SUBN_MASK: Final[uint8] = 0x40
HALFC_MASK: Final[uint8] = 0x20
CARRY_MASK: Final[uint8] = 0x10

reglst = Final[list[str]]

reg_ids: reglst = [
    "B",
    "C",
    "D",
    "E",
    "H",
    "L",
    "A"
]

nonsplit_addr_reg_ids: reglst = [
    "PC",
    "SP"
]

split_addr_reg_ids: reglst = [
    "BC",
    "DE",
    "HL"
]

all_reg_ids: reglst = reg_ids + nonsplit_addr_reg_ids + split_addr_reg_ids

# All registers that can have their contents directly read or set.
direct_access_reg_ids: reglst = reg_ids + nonsplit_addr_reg_ids

# All 16 bit registers. Can be used to read any memory address
all_addr_reg_ids: reglst = nonsplit_addr_reg_ids + split_addr_reg_ids


class CPU:

    def __init__(self) -> None:
        self.reg = self.dmg_8bit_registers()
        self.mem = Memory()
        self.cycles: int = 0

    # Register setup methods
    def dmg_8bit_registers(self) -> dict[str, uint8]:
        """Returns the 8-bit registers and their default values for the DMG."""
        return {
            "PC": 0x0100,
            "SP": 0xFFFE,
            "A": 0x01,
            "F": 0xB0,
            "B": 0x00,
            "C": 0x13,
            "D": 0x00,
            "E": 0xD8,
            "H": 0x01,
            "L": 0x4D
        }

    # Flag accessor methods
    def zero(self) -> uint8:
        return self.reg["F"] & ZERO_MASK

    def subn(self) -> uint8:
        return self.reg["F"] & SUBN_MASK

    def halfc(self) -> uint8:
        return self.reg["F"] & HALFC_MASK

    def carry(self) -> uint8:
        return self.reg["F"] & CARRY_MASK

    def make_parameter_table(self):
        self.make_access_table()
        self.make_nudge_table()

    def make_access_table(self):
        gets = {}
        sets = {}
        for rid in direct_access_reg_ids:
            gets[rid] = partial(self.reg.get, rid)
            sets[rid] = partial(setitem, self.reg, rid)

        def make_addr(high, low):
            return (high() << 8) | low()
        def set_addr(set_high, set_low, value):
            set_high(value >> 8)
            set_low(value & 0xFF)

        addr_gets = {}
        addr_sets = {}
        for arid in split_addr_reg_ids:
            high, low = arid
            addr_gets[arid] = partial(make_addr, gets[high], gets[low])
            addr_sets[arid] = partial(set_addr, sets[high], sets[low])

        gets.update(addr_gets)
        sets.update(addr_sets)
        self.gets = gets
        self.sets = sets

    def make_nudge_table(self):
        # Uniary increment or decrement - a "nudge"
        def nudge(get, set, nudge_amt):
            val = get()
            set(val + nudge_amt)
            return val

        nudges = {}
        for arid in all_addr_reg_ids:
            get_arid = self.gets[arid]
            set_arid = self.sets[arid]
            nudges[arid+"+"] = partial(nudge, get_arid, set_arid, 1)
            nudges[arid+"-"] = partial(nudge, get_arid, set_arid, -1)

        self.gets.update(nudges)


c = CPU()
c.make_parameter_table()
