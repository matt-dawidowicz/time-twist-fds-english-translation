"""Evidence-backed metadata for source-reachable retail gameplay VM opcodes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetailVmOpcode:
    """Describe one opcode used by reachable retail gameplay script source."""

    opcode: int
    mnemonic: str
    operand_grammar: str
    length_rule: str
    handler: int
    evidence: str
    notes: str


HANDLERS = {
    0x0: 0x7C0E,
    0x1: 0x6A04,
    0x2: 0x6A82,
    0x3: 0x6BFD,
    0x4: 0x6C5E,
    0x5: 0x6DA9,
    0x6: 0x6F2C,
    0x7: 0x6F49,
    0x8: 0x717E,
    0x9: 0x7192,
    0xA: 0x71A4,
    0xB: 0x71F5,
    0xD: 0x78BA,
    0xE: 0x79A7,
}


def _op(
    opcode: int,
    mnemonic: str,
    operands: str,
    length: str,
    evidence: str = "VERIFIED",
    notes: str = "",
) -> RetailVmOpcode:
    """Build one registry entry with its family handler filled in."""
    return RetailVmOpcode(
        opcode=opcode,
        mnemonic=mnemonic,
        operand_grammar=operands,
        length_rule=length,
        handler=HANDLERS[opcode >> 4],
        evidence=evidence,
        notes=notes,
    )


def inline_predicate_span(data: bytes, offset: int = 0) -> int:
    """Return bytes from an inline predicate start to its target table.

    NOV2 `$977D-$97AF` uses the predicate's low nibble as the compact term
    count. A low nibble of `$0F` switches to the following full-byte count.
    The extended form has one additional packed-control byte relative to the
    compact formula because the native pointer advance includes the marker and
    extended-count header.

    Args:
        data: Byte stream containing the inline predicate.
        offset: Predicate start within `data`.

    Returns:
        Number of bytes occupied by the predicate encoding, stopping exactly at
        the first result-target byte.

    Raises:
        ValueError: If the extended-count header is truncated.
    """
    count = data[offset] & 0x0F
    if count == 0x0F:
        if offset + 1 >= len(data):
            raise ValueError("truncated extended inline predicate")
        count = data[offset + 1]
        return count + ((count + 6) // 2)
    return count + ((count + 2) // 2)


RETAIL_VM_OPCODES = (
    _op(0x00, "store_immediate", "address:u16, value:u8", "4 bytes"),
    _op(0x01, "add_immediate", "address:u16, value:u8", "4 bytes"),
    _op(0x02, "subtract_immediate", "address:u16, value:u8", "4 bytes"),
    _op(
        0x04,
        "compare_immediate",
        "address:u16, value:u8",
        "4 bytes",
        notes="Subtracts for condition state without storing the result.",
    ),
    _op(
        0x06,
        "copy_byte",
        "destination_address:u16, source_address:u16",
        "5 bytes",
    ),
    _op(
        0x09,
        "write_counted_block",
        "count:u8, destination_address:u16, values[count]:u8",
        "4 + count bytes",
    ),
    _op(
        0x0E,
        "write_address_value_pairs",
        "count:u8, entries[count]:(address:u16, value:u8)",
        "2 + 3*count bytes",
    ),
    _op(
        0x0F,
        "invoke_system_sequence",
        "sequence_id:u8",
        "2 bytes",
        notes="Retail source uses sequence 5, which enters engine state $22.",
    ),
    _op(
        0x10,
        "text_then_continue",
        "text_record:u8",
        "2 bytes",
    ),
    _op(
        0x11,
        "text_alt_wait_then_continue",
        "text_record:u8",
        "2 bytes",
        evidence="DERIVED",
        notes="Bit 0 selects the alternate interaction/wait path.",
    ),
    _op(
        0x18,
        "text_then_current_route",
        "text_record:u8",
        "2 bytes",
        notes="Completion transfers through the current $A220 route entry.",
    ),
    _op(
        0x19,
        "text_alt_wait_then_current_route",
        "text_record:u8",
        "2 bytes",
        evidence="DERIVED",
        notes="Combines the bit-0 text path with route-terminating bit 3.",
    ),
    _op(0x20, "menu_direct", "menu_record:u8", "2 bytes"),
    _op(
        0x21,
        "menu_direct_secondary_prompt",
        "menu_record:u8, secondary_prompt:u8",
        "3 bytes",
    ),
    _op(
        0x28,
        "menu_resumable",
        "menu_record:u8",
        "2 bytes",
        notes="Snapshots script PC and software-stack continuation state.",
    ),
    _op(
        0x29,
        "menu_resumable_secondary_prompt",
        "menu_record:u8, secondary_prompt:u8",
        "3 bytes",
        notes="Combines resumable context with an $A212 secondary selector.",
    ),
    _op(
        0x30,
        "branch_selection_absolute",
        "targets[choice_count]:u16",
        "1 + 2*choice_count bytes",
    ),
    _op(
        0x31,
        "branch_selection_relative",
        "targets[choice_count]:s8",
        "1 + choice_count bytes",
    ),
    _op(
        0x40,
        "branch_inline_predicate_absolute",
        "inline_predicate, targets[result_count]:u16",
        "variable",
    ),
    _op(
        0x41,
        "branch_flag_predicate_absolute",
        "flag_id:u8, targets[result_count]:u16",
        "variable",
    ),
    _op(
        0x44,
        "branch_inline_predicate_relative",
        "inline_predicate, targets[result_count]:s8",
        "variable",
    ),
    _op(
        0x45,
        "branch_flag_predicate_relative",
        "flag_id:u8, targets[result_count]:s8",
        "variable",
    ),
    _op(
        0x49,
        "branch_not_flag_predicate_absolute",
        "flag_id:u8, targets[result_count]:u16",
        "variable",
    ),
    _op(
        0x4D,
        "branch_not_flag_predicate_relative",
        "flag_id:u8, targets[result_count]:s8",
        "variable",
    ),
    _op(0x50, "jump_absolute", "target:u16", "3 bytes"),
    _op(
        0x51,
        "switch_route_and_jump",
        "route_selector:u8",
        "2 bytes",
        notes=(
            "Records the previous route, updates current-route bookkeeping, "
            "then jumps through $A220[new_route]."
        ),
    ),
    _op(0x52, "jump_current_route", "none", "1 byte"),
    _op(0x53, "return_subroutine", "none", "1 byte"),
    _op(0x54, "call_absolute", "target:u16", "3 bytes"),
    _op(0x58, "jump_relative", "delta:s8", "2 bytes"),
    _op(
        0x60,
        "mutate_flags_extended",
        "counts:u8, set_ids[set_count], clear_ids[clear_count]",
        "2 + set_count + clear_count bytes",
        notes="counts low nibble=set_count, high nibble=clear_count.",
    ),
    _op(0x61, "set_1_flag", "set_ids[1]:u8", "2 bytes"),
    _op(0x62, "set_2_flags", "set_ids[2]:u8", "3 bytes"),
    _op(0x63, "set_3_flags", "set_ids[3]:u8", "4 bytes"),
    _op(0x64, "clear_1_flag", "clear_ids[1]:u8", "2 bytes"),
    _op(
        0x65,
        "set_1_clear_1_flag",
        "set_ids[1]:u8, clear_ids[1]:u8",
        "3 bytes",
    ),
    _op(
        0x66,
        "set_2_clear_1_flag",
        "set_ids[2]:u8, clear_ids[1]:u8",
        "4 bytes",
    ),
    _op(
        0x67,
        "set_3_clear_1_flag",
        "set_ids[3]:u8, clear_ids[1]:u8",
        "5 bytes",
    ),
    _op(0x68, "clear_2_flags", "clear_ids[2]:u8", "3 bytes"),
    _op(
        0x69,
        "set_1_clear_2_flags",
        "set_ids[1]:u8, clear_ids[2]:u8",
        "4 bytes",
    ),
    _op(0x6C, "clear_3_flags", "clear_ids[3]:u8", "4 bytes"),
    _op(
        0x6D,
        "set_1_clear_3_flags",
        "set_ids[1]:u8, clear_ids[3]:u8",
        "5 bytes",
    ),
    _op(
        0x70,
        "configure_scene_components",
        "mask:u8, selectors[popcount(mask)]:u8",
        "2 + popcount(mask) bytes",
    ),
    _op(
        0x83,
        "write_audio_latch_3_mirrored",
        "value:u8",
        "2 bytes",
        notes="Writes $07E3 and mirrors the value into zero-page $D1.",
    ),
    _op(0x90, "write_audio_latch_0", "value:u8", "2 bytes"),
    _op(0x91, "write_audio_latch_1", "value:u8", "2 bytes"),
    _op(0x92, "write_audio_latch_2", "value:u8", "2 bytes"),
    _op(0x93, "write_audio_latch_3", "value:u8", "2 bytes"),
    _op(
        0xA1,
        "delay_ticks",
        "duration:u8",
        "2 bytes",
        notes="Loads a 16-bit countdown whose high byte starts at zero.",
    ),
    _op(
        0xB0,
        "begin_exploration",
        "exploration_mode:u8",
        "2 bytes",
        notes=(
            "Fresh setup saves $0796 in $07C0, initializes $0794/$0795/"
            "$07A8/$07A9, configures $4025, and takes the fresh coordinate/"
            "camera initialization path rather than BC's restore path."
        ),
    ),
    _op(
        0xB2,
        "start_irq_raster_transition_mode_2",
        "none",
        "1 byte",
        notes="Installs fixed FDS IRQ timing sweep parameters for mode 2.",
    ),
    _op(
        0xB3,
        "start_irq_raster_transition_mode_3",
        "none",
        "1 byte",
        notes="Installs fixed FDS IRQ timing sweep parameters for mode 3.",
    ),
    _op(
        0xB5,
        "move_coordinate_to_target",
        "coordinate_mode:u8, step:u8, target:u16",
        "5 bytes",
        notes=(
            "Modes 1/2 move coordinate pair $57/$58 positive/negative; "
            "mode 3 and higher select $18/$19, with 3 positive and 4+ "
            "negative. Native state uses 1/16 fixed point and stops exactly "
            "on the scripted target."
        ),
    ),
    _op(
        0xB6,
        "enable_raster_scroll_wave",
        "none",
        "1 byte",
        notes=(
            "Sets $4A=$FF and enters exploration substate 7, enabling the "
            "verified raster-time PPU-scroll waveform path."
        ),
    ),
    _op(
        0xB7,
        "configure_hotspot_boundaries",
        "hotspot_set:u8, boundary_selector:u8",
        "3 bytes",
    ),
    _op(
        0xB9,
        "save_exploration_checkpoint",
        "exploration_selector:u8",
        "2 bytes",
        notes=(
            "Saves script PC and software-stack continuation in "
            "$9B/$9C/$9F/$A0, copies the selector to $BA, clears any "
            "previous matching $07B3 slot, and enters exploration. $768F "
            "later uses the same $BA value as a one-based $A20C hotspot-group "
            "selector and exports group count/index through $91/$A7."
        ),
    ),
    _op(
        0xBA,
        "restore_exploration_coordinate_slot",
        "slot_id:u8",
        "2 bytes",
        notes=(
            "Finds the matching $07B3 slot record, copies its saved coordinate "
            "pair into the active actor records selected by $07AC, updates "
            "world/camera coordinates through $75F3, then consumes the slot."
        ),
    ),
    _op(
        0xBB,
        "clear_saved_coordinate_slot",
        "slot_id:u8",
        "2 bytes",
    ),
    _op(
        0xBC,
        "resume_exploration",
        "exploration_mode:u8",
        "2 bytes",
        notes=(
            "Shares B0's $72C6 setup, but the continuation restores $0796 "
            "from saved $07C0 instead of performing B0's fresh coordinate/"
            "camera initialization."
        ),
    ),
    _op(
        0xD2,
        "clone_flip_background_chr",
        (
            "count:u8, records[count]:(source_tile:u8, "
            "destination_tile:u8, flags:u8)"
        ),
        "2 + 3*count bytes",
        notes="$40=horizontal flip, $80=vertical flip, $C0=both.",
    ),
    _op(
        0xE0,
        "fds_scene_transition",
        "transition_selector:u8",
        "2 bytes",
        evidence="DERIVED",
        notes="Enters the FDS/scene/file transition state machine.",
    ),
)


RETAIL_VM_OPCODE_BY_VALUE = {
    entry.opcode: entry for entry in RETAIL_VM_OPCODES
}
RETAIL_VM_OPCODE_VALUES = tuple(entry.opcode for entry in RETAIL_VM_OPCODES)


def retail_vm_opcode(opcode: int) -> RetailVmOpcode:
    """Return metadata for one source-reachable retail opcode.

    Args:
        opcode: Full one-byte gameplay VM opcode.

    Returns:
        The matching registry entry.

    Raises:
        KeyError: If the opcode is not in the source-reachable retail language.
    """
    return RETAIL_VM_OPCODE_BY_VALUE[opcode]
