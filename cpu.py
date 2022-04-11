import json
from collections import namedtuple
from dataclasses import dataclass
from functools import partial
from operator import setitem

from bitarray import util

from memory import Memory
from registers import SUBN_MASK, carry

ZERO_MASK = 0x80
SUB_MASK = 0x40
HALFC_MASK = 0x20
CARRY_MASK = 0x10

reg_ids = [
    "A",
    "F",
    "B",
    "C",
    "D",
    "E",
    "H",
    "L"
]

nonsplit_addr_reg_ids = [
    "PC",
    "SP"
]

split_addr_reg_ids = [
    "AF",
    "BC",
    "DE",
    "HL"
]

direct_ids = [
    "a8",
    "a16",
    "d8",
    "d16",
    "r8"
]

all_reg_ids = reg_ids + nonsplit_addr_reg_ids + split_addr_reg_ids

# All registers that can have their contents directly read or set.
direct_access_reg_ids = nonsplit_addr_reg_ids + reg_ids

# All 16 bit registers. Can be used to read any memory address
all_addr_reg_ids = nonsplit_addr_reg_ids + split_addr_reg_ids

default_register_values = {
    # Order: PC, SP, A, F, B, C, D, E, H, L (direct_access_reg_ids)
    "DMG": [0x0100, 0xFFFE, 0x01, 0xB0, 0x00, 0x13, 0x00, 0xD8, 0x01, 0x4D]
}

Operand = namedtuple("Operand", ["get", "set"])

@dataclass(frozen=True)
class OperandKey:
    name: str
    immediate: bool = True
    increment: bool = False
    decrement: bool = False

    def __repr__(self):
        rep = self.name
        rep += "+" if self.increment else ""
        rep += "-" if self.decrement else ""
        if not self.immediate:
            rep = "(" + rep + ")"
        return rep

@dataclass
class Instruction:
    """Tracking for instrucion definition and metadata"""
    name: str
    operands: list[Operand]
    cycles: list[int]
    flag_strings: list[str]
    eval: partial

    def __post_init__(self):
        self.flags = list(self.flag_strings.values())

class CPU:

    def __init__(self):
        self.reg = self.make_registers(model="DMG")
        self.mem = Memory()
        self.operands: dict[OperandKey, Operand | str] = {}
        self.opcodes: dict[int, Instruction] = {}
        self.prefixed: dict[int, Instruction] = {}
        self.instruction: Instruction = None
        self.make_parameter_table()
        self.cycles = 0

    def make_registers(self, model):
        """Take a model number and return an initialized registry dict"""
        values = default_register_values[model]
        return dict(zip(direct_access_reg_ids, values))

    def make_dispatch_table(self):
        """Creates a dispatch table mapping opcodes to instructions.

        opcodes.json structure:
        unprefixed
            opcode
                mnemonic
                cycles
                operands
            ...
        prefixed
            (same as unprefixed)
        """
        f = open("opcodes.json")
        opcode_data = json.load(f)
        for prefix_type, instructions in opcode_data.items():
            for opcode, data in instructions.items():
                opcode = int(opcode, 16)
                name = data["mnemonic"]
                cycles = data["cycles"] # Will be unused for now
                flags = data["flags"]
                ins_operands = []
                for operand in data["operands"]:
                    opr_name = operand["name"]
                    opr_imm = operand["immediate"]
                    # First two are guaranteed, these two might not be
                    opr_inc = operand.get("increment", False)
                    opr_dec = operand.get("decrement", False)
                    opr_key = OperandKey(opr_name, opr_imm, opr_inc, opr_dec)
                    ins_operands.append(self.operands[opr_key])
                # ins_fn = partial(getattr(self, name), *ins_operands)
                ins_fn = "ins_fn"
                instruction = Instruction(name, ins_operands, cycles, flags, ins_fn)
                if prefix_type == "unprefixed":
                    self.opcodes[opcode] = instruction
                else:
                    self.prefixed[opcode] = instruction

    def make_parameter_table(self):
        self.make_access_table()
        self.make_nudge_table()
        self.make_immediate_table()
        self.make_indirect_table()
        self.make_flag_table()
        self.make_raw_table()

    def make_access_table(self):
        for rid in direct_access_reg_ids:
            getter = partial(self.reg.get, rid)
            setter = partial(setitem, self.reg, rid)
            key = OperandKey(rid)
            self.operands[key] = Operand(getter, setter)

        def make_16bit(high, low):
            return (high() << 8) | low()

        def set_16bit(set_high, set_low, value):
            set_high(value >> 8)
            set_low(value & 0xFF)

        for arid in split_addr_reg_ids:
            high = self.operands[OperandKey(arid[0])]
            low = self.operands[OperandKey(arid[1])]
            getter = partial(make_16bit, high.get, low.get)
            setter = partial(set_16bit, high.set, low.set)
            key = OperandKey(arid)
            self.operands[key] = Operand(getter, setter)

    def make_nudge_table(self):
        # Uniary increment or decrement - a "nudge"
        def nudge(get, set, nudge_amt):
            val = get()
            set(val + nudge_amt)
            return self.mem.read(val)

        for arid in all_addr_reg_ids:
            get_arid, set_arid = self.operands[OperandKey(arid)]
            inc_get = partial(nudge, get_arid, set_arid, 1)
            dec_get = partial(nudge, get_arid, set_arid, -1)
            inc_key = OperandKey(arid, immediate=False, increment=True)
            dec_key = OperandKey(arid, immediate=False, decrement=True)
            self.operands[inc_key] = Operand(inc_get, None)
            self.operands[dec_key] = Operand(dec_get, None)

    def make_immediate_table(self):
        # Both d8 and a8 are essentially aliases for (PC+)
        imm_key = OperandKey("PC", immediate=False, increment=True)
        imm_operand = self.operands[imm_key]
        self.operands[OperandKey("d8")] = imm_operand
        self.operands[OperandKey("a8")] = imm_operand

        # r8 needs to be read as a two's complement signed integer
        def signed_read(get):
            val = get()
            if val >> 7:
                return val - 0xFF - 1
            return val
        signed_get = partial(signed_read, imm_operand)
        self.operands[OperandKey("r8")] = Operand(signed_get, None)

        def sp_signed_add(get):
            sp_get = self.operands[OperandKey("SP")].get
            val = sp_get() + get()
            self.set_flag(ZERO_MASK, 0)
            self.set_flag(SUB_MASK, 0)
            self.half_carry(val)
            return self.carry(val, True)
        sp_get = partial(sp_signed_add, signed_get)
        self.operands[OperandKey("SP+r8")] = Operand(sp_get, None)

        def imm16_read(get):
            val = get()
            val += get() << 8
            return get() | (get() << 8)
        imm16_get = partial(imm16_read, imm_operand.get)
        self.operands[OperandKey("d16")] = Operand(imm16_get, None)
        self.operands[OperandKey("a16")] = Operand(imm16_get, None)

    def make_indirect_table(self):
        def make_ind_read(get):
            return self.mem.read(get)

        def make_ind_write(get, value):
            self.mem.write(get, value)

        # Final page read/write
        def make_fpage_read(get):
            return self.mem.read(0xFF00 + get())

        def make_fpage_write(get, value):
            self.mem.write(0xFF00 + get(), value)

        fpage_regs = ["C", "a8"]
        for id in split_addr_reg_ids + fpage_regs + ["a16"]:
            id_key = OperandKey(id)
            id_get = self.operands[id_key].get
            # FPage operations are 8 bit so they need different handling
            is_fpage = id in fpage_regs
            func_get = make_fpage_read if is_fpage else make_ind_read
            func_set = make_fpage_write if is_fpage else make_ind_write
            ind_get = partial(func_get, id_get)
            ind_set = partial(func_set, id_get)
            ind_key = OperandKey(id, immediate=False)
            self.operands[ind_key] = Operand(ind_get, ind_set)

    def make_flag_table(self):
        flags = [("Z", ZERO_MASK), ("CY", CARRY_MASK)]
        for id, mask in flags:
            flag_get = partial(self.get_flag, mask)
            flag_get_neg = partial(self.get_flag, mask, True)
            flag_key = OperandKey(id)
            flag_key_neg = OperandKey("N" + id)
            self.operands[flag_key] = Operand(flag_get, None)
            self.operands[flag_key_neg] = Operand(flag_get_neg, None)

    def make_raw_table(self):
        # Bit designator for some 16-bit operations
        for num in range(8):
            num_key = OperandKey(str(num))
            self.operands[num_key] = num

        # Hex designator for some 16-bit operations
        for hex_num in range(0x00, 0x38 + 1, 8):
            hex_num_id = "{0:02X}H".format(hex_num)
            hex_num_key = OperandKey(hex_num_id)
            self.operands[hex_num_key] = hex_num


    # Instructions and register operations
    def apply_flags(self):
        for index, flag in enumerate(self.instruction.flags):
            if flag == "0":
                self.reg["F"] &= ~(1 << (3 - index))
            elif flag == "1":
                self.reg["F"] |= (1 << (3 - index))

    def get_flag(self, mask, negated=False):
        return bool(self.reg["F"] & mask) is not negated

    def set_flag(self, mask, val):
        if val:
            self.reg["F"] |= mask
        else:
            self.reg["F"] &= ~mask

    def zero(self, value):
        self.set_flag(ZERO_MASK, not value)

    def is_subtraction(self, is_sub):
        self.set_flag(SUBN_MASK, is_sub)

    def half_carry(self, oper1, oper2, carry=0, is16bit=False):
        mask = 0xFFF if is16bit else 0xF
        check = 0x1000 if is16bit else 0x10
        half_carry = ((oper1 & mask) + (oper2 & mask) + carry) & check
        self.set_flag(HALFC_MASK, half_carry)

    def carry(self, value, is16bit=False):
        max = 0xFFFF if is16bit else 0xFF
        self.set_flag(CARRY_MASK, 0 < value < max)

    def ADC(self, operand):
        """Add with carry."""
        A = self.reg["A"]
        val = operand.get()
        carry = self.get_flag(CARRY_MASK)
        result = A + val + carry
        self.reg["A"] = result & 0xFF
        self.zero(result)
        self.half_carry(A, val, carry)
        self.carry(result)

    def ADD(self, oper1, oper2=None):
        """Add. 8-bit or 16-bit if 2 values are provided."""
        is16bit = oper2 is not None
        if is16bit:
            val1 = oper1.get()
            val2 = oper2.get()
            result = val1 + val2
            oper1.set(result & 0xFFFF)
        else:
            val1 = self.reg["A"]
            val2 = oper1.get()
            result = val1 + val2
            self.reg["A"] = result & 0xFF
            self.zero(result)
        self.half_carry(val1, val2, is16bit=is16bit)
        self.carry(result, is16bit)

    def AND(self, operand):
        result = self.reg["A"] & operand.get()
        self.reg["A"] = result
        self.zero(result)

    def BIT(self, bit, operand):
        result = (1 << bit.get()) & operand.get()
        self.zero(result)

class Instruction:
    def __init__(self, mnemonic, cycles, flags, operands):
        self.mnemonic = mnemonic
        self.cycles = cycles
        self.flags = flags
        self.operands = operands

class Arithmetic(Instruction):
    def __init__(self, mnemonic, cycles, flags, operands):
        super().__init__(mnemonic, cycles, flags, operands)
