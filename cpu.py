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


# for id, get in c.gets.items():
#     id_string = "{0: <4}".format(id)
#     print(id_string + get())



# for id, f in c.make_get_table().items():
#     print("{0}: 0x{1:04X}".format(id, f()))

# c.make_opcode_dispatch_table(debug_print=True)


    # def dmg_16bit_registers(self) -> Tuple[uint16, uint16]:
    #     """Returns the 16-bit default values for the PC and SP"""
    #     return (0x0100, 0xFFFE)

    # # Flag accessor methods
    # def zero(self) -> uint8:
    #     return self.reg["F"] & ZERO_MASK

    # def subn(self) -> uint8:
    #     return self.reg["F"] & SUBN_MASK

    # def halfc(self) -> uint8:
    #     return self.reg["F"] & HALFC_MASK

    # def carry(self) -> uint8:
    #     return self.reg["F"] & CARRY_MASK

    # def register_16(self, regs: str) -> uint16:
    #     """Return the 16-bit value stored in the combined registers of regs"""
    #     high = regs[0]
    #     low = regs[1]
    #     return unsigned_16(self.reg[high], self.reg[low])

    # def address_range(self,
    #                   start: uint16,
    #                   end: uint16,
    #                   step: uint16,
    #                   exclusions: list[uint16] = []) -> list[uint16]:
    #     return [addr for addr in range(start, end + 1, step)
    #             if addr not in exclusions]

    # def letters(self, exclude: list[str] = []) -> list[str]:
    #     return [ltr for ltr in reg_ids
    #             if ltr not in exclude]

    # def pretty_print(self, instruction):
    #     opcode, part = instruction
    #     op_string = "0x{0:04X} ".format(opcode)
    #     ins_string = "| {1: <4} | {0}\n".format(part.func.__name__, ','.join(part.args))
    #     print(op_string + ins_string + "-"*30)

    # def make_opcode_dispatch_table(self, debug_print=False):
    #     instructions = {}
    #     instructions.update(self.dt_LD_r_d8())
    #     instructions.update(self.dt_LD_r_r())

    #     if debug_print:
    #         [self.pretty_print(ins) for ins in instructions.items()]
    #         print("{0}/501 ({1:.2%}) implemented".format(len(instructions), len(instructions)/501))

    # # Dispatch table construction methods
    # def dt_LD_r_d8(self) -> dict[uint16, partial]:
    #     # 8 instructions
    #     addr_range = self.address_range(0x06, 0x3E, 0x08)
    #     partials: list[partial] = []
    #     for letter in self.letters():
    #         func = (self.LD_reg16_direct8 if letter == "HL" else
    #                 self.LD_reg8_direct8)
    #         partials.append(partial(func, letter))
    #     return dict(zip(addr_range, partials))

    # def dt_LD_r_r(self) -> dict[uint16, partial]:
    #     # 62 instructions
    #     addr_range = self.address_range(0x40, 0x7F, 0x01, [0x76])
    #     partials: list[partial] = []
    #     for dest in self.letters():
    #         for src in self.letters():
    #             if dest == src == "HL":
    #                 continue
    #             func = (self.LD_reg16_reg8 if dest == "HL" else
    #                     self.LD_reg8_reg16 if src == "HL" else
    #                     self.LD_reg8_reg8)
    #             partials.append(partial(func, dest, src))
    #     return dict(zip(addr_range, partials))

    # # LD r,d8
    # def LD_reg8_direct8(self, dest_reg: str) -> None:
    #     """Read the operand at pc and store it in dest_reg immediately"""
    #     self.reg[dest_reg] = self.mem.read(self.pc)
    #     self.pc += 1
    #     self.cycles = 8

    # def LD_reg16_direct8(self, dest_reg: str) -> None:
    #     """Read the operand at pc and store it in the memory address from dest_reg immediately"""
    #     operand = self.mem.read(self.pc)
    #     dest_addr = self.register_16(dest_reg)
    #     self.mem.write(dest_addr, operand)
    #     self.pc += 1
    #     self.cycles = 12

    # # LD r,r
    # def LD_reg8_reg8(self, dest_reg: str, source_reg: str) -> None:
    #     """Transfer the contents of source_reg to dest_reg"""
    #     self.reg[dest_reg] = self.reg[source_reg]
    #     self.pc += 1
    #     self.cycles = 4

    # def LD_reg8_reg16(self, dest_reg: str, source_reg: str) -> None:
    #     """Store in dest_reg the contents of the address in source_reg"""
    #     source_addr = self.register_16(source_reg)
    #     self.reg[dest_reg] = self.mem.read(source_addr)
    #     self.pc += 1
    #     self.cycles = 8

    # def LD_reg16_reg8(self, dest_reg: str, source_reg: str) -> None:
    #     """Store the contents of source_reg in the address in dest_reg"""
    #     dest_addr = self.register_16(dest_reg)
    #     self.mem.write(dest_addr, self.reg[source_reg])
    #     self.pc += 1
    #     self.cycles = 8

    # # LD ra,A | A,ra
    # def LD_reg16_A(self, dest_reg, modifier=0):
    #     dest_addr = self.register_16(dest_reg)
    #     self.mem.write(dest_addr, self.reg["A"])
