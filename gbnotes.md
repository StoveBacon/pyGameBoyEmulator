Added operands
- SP+r8

Modified instructions
* 0xE8 ADD SP,r8 -> LD SP,SP+r8
* 0xF8 LD HL,SP,r8 -> LD HL,SP+r8

Instructions
||||||
|-|-|-|-|-|
|ADC|ADD|AND|BIT|CALL|
|CCF|CP|CPL|DAA|DEC|
|DI|EI|HALT|INC|JP|
|JR|LD|LDH|NOP|OR|
|POP|PREFIX|PUSH|RES|RET|
|RETI|RL|RLA|RLC|RLCA|
|RR|RRA|RRC|RRCA|RST|
|SBC|SCF|SET|SLA|SRA|
|SRL|STOP|SUB|SWAP|XOR|


Illegal opcodes
|||||||
|-|-|-|-|-|-|
|D3|DB|DD|E3|E4|EB|
|EC|ED|F4|FC|FD|

Parameters
||||||
|-|-|-|-|-|
|0|1|2|3|4|
|5|6|7|A|B|
|C|D|E|H|L|
|Z|CY|NZ|NCY|AF|
|BC|DE|HL|SP|a8|
|a16|d8|d16|r8|00H|
|08H|10H|18H|20H|28H|
|30H|38H|SP+r8|||