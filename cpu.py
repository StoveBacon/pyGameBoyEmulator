from typing import Final, Tuple

from byteops import uint8, uint16
from memory import Memory

ZERO_MASK: Final[uint8] = 0x80
SUBN_MASK: Final[uint8] = 0x40
HALFC_MASK: Final[uint8] = 0x20
CARRY_MASK: Final[uint8] = 0x10


class CPU:

    def __init__(self) -> None:
        self.reg = self.dmg_8bit_registers()
        self.pc, self.sp = self.dmg_16bit_registers()
        self.mem = Memory()
        self.cycles: int = 0

    # Register setup methods
    def dmg_8bit_registers(self) -> dict[str, uint8]:
        """Returns the 8-bit registers and their default values for the DMG."""
        return {
            "A": 0x01,
            "F": 0xB0,
            "B": 0x00,
            "C": 0x13,
            "D": 0x00,
            "E": 0xD8,
            "H": 0x01,
            "L": 0x4D
        }

    def dmg_16bit_registers(self) -> Tuple[uint16, uint16]:
        """Returns the 16-bit default values for the PC and SP"""
        return (0x0100, 0xFFFE)

    # Flag accessor methods
    def zero(self) -> uint8:
        return self.reg["F"] & ZERO_MASK

    def subn(self) -> uint8:
        return self.reg["F"] & SUBN_MASK

    def halfc(self) -> uint8:
        return self.reg["F"] & HALFC_MASK

    def carry(self) -> uint8:
        return self.reg["F"] & CARRY_MASK

    # Execution and opcode interpretation methods
    def execute_next_instruction(self) -> None:
        opcode: uint8 = self.mem.read(self.pc)
        self.pc += 1
        match opcode:
            # LD r,d8
            case 0x06:
                self.LD_reg_imd("B")
            case 0x0E:
                self.LD_reg_imd("C")
            case 0x16:
                self.LD_reg_imd("D")
            case 0x1E:
                self.LD_reg_imd("E")
            case 0x26:
                self.LD_reg_imd("H")
            case 0x2E:
                self.LD_reg_imd("L")
            # LD r1,r2
            case 0x7F:
                self.LD_reg8_reg8("A", "A")
            case 0x78:
                self.LD_reg8_reg8("A", "B")
            case 0x79:
                self.LD_reg8_reg8("A", "C")
            case 0x7A:
                self.LD_reg8_reg8("A", "D")
            case 0x7B:
                self.LD_reg8_reg8("A", "E")

    def LD_reg_imd(self, dest_reg: str) -> None:
        """Read the operand at pc and store it in dest_reg immediately"""
        self.reg[dest_reg] = self.mem.read(self.pc)
        self.pc += 1
        self.cycles = 8

    def LD_reg8_reg8(self, dest_reg: str, source_reg: str) -> None:
        """Transfer the contents of source_reg to dest_reg"""
        self.reg[dest_reg] = self.reg[source_reg]
        self.pc += 1
        self.cycles = 4
