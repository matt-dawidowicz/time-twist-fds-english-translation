"""Small read-only 6502 disassembler used for Time Twist engine analysis."""

from __future__ import annotations

import argparse
from pathlib import Path


OPS = {
    0x00:("BRK","imp"),0x01:("ORA","inx"),0x05:("ORA","zp"),0x06:("ASL","zp"),0x08:("PHP","imp"),0x09:("ORA","imm"),0x0A:("ASL","acc"),0x0D:("ORA","abs"),0x0E:("ASL","abs"),
    0x10:("BPL","rel"),0x11:("ORA","iny"),0x15:("ORA","zpx"),0x16:("ASL","zpx"),0x18:("CLC","imp"),0x19:("ORA","aby"),0x1D:("ORA","abx"),0x1E:("ASL","abx"),
    0x20:("JSR","abs"),0x21:("AND","inx"),0x24:("BIT","zp"),0x25:("AND","zp"),0x26:("ROL","zp"),0x28:("PLP","imp"),0x29:("AND","imm"),0x2A:("ROL","acc"),0x2C:("BIT","abs"),0x2D:("AND","abs"),0x2E:("ROL","abs"),
    0x30:("BMI","rel"),0x31:("AND","iny"),0x35:("AND","zpx"),0x36:("ROL","zpx"),0x38:("SEC","imp"),0x39:("AND","aby"),0x3D:("AND","abx"),0x3E:("ROL","abx"),
    0x40:("RTI","imp"),0x41:("EOR","inx"),0x45:("EOR","zp"),0x46:("LSR","zp"),0x48:("PHA","imp"),0x49:("EOR","imm"),0x4A:("LSR","acc"),0x4C:("JMP","abs"),0x4D:("EOR","abs"),0x4E:("LSR","abs"),
    0x50:("BVC","rel"),0x51:("EOR","iny"),0x55:("EOR","zpx"),0x56:("LSR","zpx"),0x58:("CLI","imp"),0x59:("EOR","aby"),0x5D:("EOR","abx"),0x5E:("LSR","abx"),
    0x60:("RTS","imp"),0x61:("ADC","inx"),0x65:("ADC","zp"),0x66:("ROR","zp"),0x68:("PLA","imp"),0x69:("ADC","imm"),0x6A:("ROR","acc"),0x6C:("JMP","ind"),0x6D:("ADC","abs"),0x6E:("ROR","abs"),
    0x70:("BVS","rel"),0x71:("ADC","iny"),0x75:("ADC","zpx"),0x76:("ROR","zpx"),0x78:("SEI","imp"),0x79:("ADC","aby"),0x7D:("ADC","abx"),0x7E:("ROR","abx"),
    0x81:("STA","inx"),0x84:("STY","zp"),0x85:("STA","zp"),0x86:("STX","zp"),0x88:("DEY","imp"),0x8A:("TXA","imp"),0x8C:("STY","abs"),0x8D:("STA","abs"),0x8E:("STX","abs"),
    0x90:("BCC","rel"),0x91:("STA","iny"),0x94:("STY","zpx"),0x95:("STA","zpx"),0x96:("STX","zpy"),0x98:("TYA","imp"),0x99:("STA","aby"),0x9A:("TXS","imp"),0x9D:("STA","abx"),
    0xA0:("LDY","imm"),0xA1:("LDA","inx"),0xA2:("LDX","imm"),0xA4:("LDY","zp"),0xA5:("LDA","zp"),0xA6:("LDX","zp"),0xA8:("TAY","imp"),0xA9:("LDA","imm"),0xAA:("TAX","imp"),0xAC:("LDY","abs"),0xAD:("LDA","abs"),0xAE:("LDX","abs"),
    0xB0:("BCS","rel"),0xB1:("LDA","iny"),0xB4:("LDY","zpx"),0xB5:("LDA","zpx"),0xB6:("LDX","zpy"),0xB8:("CLV","imp"),0xB9:("LDA","aby"),0xBA:("TSX","imp"),0xBC:("LDY","abx"),0xBD:("LDA","abx"),0xBE:("LDX","aby"),
    0xC0:("CPY","imm"),0xC1:("CMP","inx"),0xC4:("CPY","zp"),0xC5:("CMP","zp"),0xC6:("DEC","zp"),0xC8:("INY","imp"),0xC9:("CMP","imm"),0xCA:("DEX","imp"),0xCC:("CPY","abs"),0xCD:("CMP","abs"),0xCE:("DEC","abs"),
    0xD0:("BNE","rel"),0xD1:("CMP","iny"),0xD5:("CMP","zpx"),0xD6:("DEC","zpx"),0xD8:("CLD","imp"),0xD9:("CMP","aby"),0xDD:("CMP","abx"),0xDE:("DEC","abx"),
    0xE0:("CPX","imm"),0xE1:("SBC","inx"),0xE4:("CPX","zp"),0xE5:("SBC","zp"),0xE6:("INC","zp"),0xE8:("INX","imp"),0xE9:("SBC","imm"),0xEA:("NOP","imp"),0xEC:("CPX","abs"),0xED:("SBC","abs"),0xEE:("INC","abs"),
    0xF0:("BEQ","rel"),0xF1:("SBC","iny"),0xF5:("SBC","zpx"),0xF6:("INC","zpx"),0xF8:("SED","imp"),0xF9:("SBC","aby"),0xFD:("SBC","abx"),0xFE:("INC","abx"),
}

SIZES = {"imp":1,"acc":1,"imm":2,"zp":2,"zpx":2,"zpy":2,"inx":2,"iny":2,"rel":2,"abs":3,"abx":3,"aby":3,"ind":3}


def operand(mode: str, raw: bytes, pc: int) -> str:
    """Format one decoded 6502 operand using conventional assembly syntax.

    Args:
        mode: Addressing-mode key from :data:`OPS`.
        raw: Complete instruction bytes, including the opcode.
        pc: Runtime address of the opcode.

    Returns:
        Empty text for implied mode, ``A`` for accumulator mode, or a formatted
        immediate, zero-page, indirect, indexed, branch, or absolute operand.

    Raises:
        IndexError: If ``raw`` is shorter than the supplied mode requires.

    Note:
        Relative displacements are sign-extended and resolved to a 16-bit target.
        The final indirect fallback is valid only for the known ``ind`` mode.
    """

    if mode == "imp": return ""
    if mode == "acc": return "A"
    if mode == "imm": return f"#${raw[1]:02X}"
    if mode == "zp": return f"${raw[1]:02X}"
    if mode == "zpx": return f"${raw[1]:02X},X"
    if mode == "zpy": return f"${raw[1]:02X},Y"
    if mode == "inx": return f"(${raw[1]:02X},X)"
    if mode == "iny": return f"(${raw[1]:02X}),Y"
    if mode == "rel":
        displacement = raw[1] - 256 if raw[1] >= 128 else raw[1]
        return f"${(pc + 2 + displacement) & 0xFFFF:04X}"
    address = raw[1] | (raw[2] << 8)
    if mode == "abs": return f"${address:04X}"
    if mode == "abx": return f"${address:04X},X"
    if mode == "aby": return f"${address:04X},Y"
    return f"(${address:04X})"


def main() -> None:
    """Disassemble a runtime-address range from one raw 6502 binary.

    Inputs:
        Accepts a file path, inclusive start address, exclusive end address, and
        optional runtime load address.  Integers accept decimal or base prefixes.

    Outputs:
        Prints address, raw bytes, mnemonic, and formatted operand for each
        decoded official opcode.  Unknown bytes are emitted as ``.byte``.

    Raises:
        OSError: If the binary cannot be read.
        IndexError: If the requested start offset lies outside the file.
        ValueError: If a numeric command-line argument cannot be parsed.

    Side Effects:
        Reads the input file and writes only to standard output.

    Design:
        This intentionally small analysis aid recognizes the official opcodes
        required by the project.  It does not infer code flow or decode unofficial
        opcodes, and it stops before printing a truncated final instruction.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("start", type=lambda value: int(value, 0))
    parser.add_argument("end", type=lambda value: int(value, 0))
    parser.add_argument("--load", type=lambda value: int(value, 0), default=0)
    args = parser.parse_args()
    data = args.path.read_bytes()
    offset = args.start - args.load
    limit = args.end - args.load
    while offset < limit:
        pc = args.load + offset
        opcode = data[offset]
        decoded = OPS.get(opcode)
        if decoded is None:
            print(f"{pc:04X}: {opcode:02X}       .byte ${opcode:02X}")
            offset += 1
            continue
        mnemonic, mode = decoded
        size = SIZES[mode]
        raw = data[offset:offset + size]
        if len(raw) != size:
            break
        print(f"{pc:04X}: {raw.hex(' ').upper():<8}  {mnemonic} {operand(mode, raw, pc)}".rstrip())
        offset += size


if __name__ == "__main__":
    main()
