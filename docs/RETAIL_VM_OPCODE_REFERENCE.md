# Retail gameplay VM opcode reference

This document is the canonical semantic inventory for **source-reachable retail** Time Twist gameplay VM opcodes. It intentionally distinguishes the language used by shipped scenario programs from extra forms implemented by the native interpreter but not reached by the recovered retail source graph.

Evidence labels follow `REVERSE_ENGINEERING_GUIDE.md`. A mnemonic is deliberately mechanical when the native side effect is proven but the story-facing intent is not.

## Coverage contract

- **61** distinct opcodes occur in the source-reachable retail language.
- Route-seeded static execution reaches **7,283 command starts** covering **23,902 / 24,229 script bytes (98.6504%)**.
- The remaining **327 bytes** are non-reached source islands; they are not promoted to executable commands without a proven incoming VM state.
- No source-reachable class-C or class-F opcode occurs.
- `$A20E` indexed-predicate forms are native engine capability but have zero source-reachable uses and `$A20E=$0000` in all 13 composed gameplay scenes.

`work/time_twist/retail_vm.py` is the machine-readable registry. `work/tools/audit_retail_vm_semantics.py` source-guards the relevant NOV2 interpreter surfaces and real-scene header invariants against maintainer-supplied original disks.

## Canonical opcode table

| Opcode | Semantic name | Operand grammar | Length | Handler | Evidence |
| --- | --- | --- | --- | --- | --- |
| `$00` | `store_immediate` | `address:u16, value:u8` | 4 bytes | `$7C0E` | **VERIFIED** |
| `$01` | `add_immediate` | `address:u16, value:u8` | 4 bytes | `$7C0E` | **VERIFIED** |
| `$02` | `subtract_immediate` | `address:u16, value:u8` | 4 bytes | `$7C0E` | **VERIFIED** |
| `$04` | `compare_immediate` | `address:u16, value:u8` | 4 bytes | `$7C0E` | **VERIFIED** |
| `$06` | `copy_byte` | `destination_address:u16, source_address:u16` | 5 bytes | `$7C0E` | **VERIFIED** |
| `$09` | `write_counted_block` | `count:u8, destination_address:u16, values[count]:u8` | 4 + count bytes | `$7C0E` | **VERIFIED** |
| `$0E` | `write_address_value_pairs` | `count:u8, entries[count]:(address:u16, value:u8)` | 2 + 3*count bytes | `$7C0E` | **VERIFIED** |
| `$0F` | `invoke_system_sequence` | `sequence_id:u8` | 2 bytes | `$7C0E` | **VERIFIED** |
| `$10` | `text_then_continue` | `text_record:u8` | 2 bytes | `$6A04` | **VERIFIED** |
| `$11` | `text_alt_wait_then_continue` | `text_record:u8` | 2 bytes | `$6A04` | **DERIVED** |
| `$18` | `text_then_current_route` | `text_record:u8` | 2 bytes | `$6A04` | **VERIFIED** |
| `$19` | `text_alt_wait_then_current_route` | `text_record:u8` | 2 bytes | `$6A04` | **DERIVED** |
| `$20` | `menu_direct` | `menu_record:u8` | 2 bytes | `$6A82` | **VERIFIED** |
| `$21` | `menu_direct_secondary_prompt` | `menu_record:u8, secondary_prompt:u8` | 3 bytes | `$6A82` | **VERIFIED** |
| `$28` | `menu_resumable` | `menu_record:u8` | 2 bytes | `$6A82` | **VERIFIED** |
| `$29` | `menu_resumable_secondary_prompt` | `menu_record:u8, secondary_prompt:u8` | 3 bytes | `$6A82` | **VERIFIED** |
| `$30` | `branch_selection_absolute` | `targets[choice_count]:u16` | 1 + 2*choice_count bytes | `$6BFD` | **VERIFIED** |
| `$31` | `branch_selection_relative` | `targets[choice_count]:s8` | 1 + choice_count bytes | `$6BFD` | **VERIFIED** |
| `$40` | `branch_inline_predicate_absolute` | `inline_predicate, targets[result_count]:u16` | variable | `$6C5E` | **VERIFIED** |
| `$41` | `branch_flag_predicate_absolute` | `flag_id:u8, targets[result_count]:u16` | variable | `$6C5E` | **VERIFIED** |
| `$44` | `branch_inline_predicate_relative` | `inline_predicate, targets[result_count]:s8` | variable | `$6C5E` | **VERIFIED** |
| `$45` | `branch_flag_predicate_relative` | `flag_id:u8, targets[result_count]:s8` | variable | `$6C5E` | **VERIFIED** |
| `$49` | `branch_not_flag_predicate_absolute` | `flag_id:u8, targets[result_count]:u16` | variable | `$6C5E` | **VERIFIED** |
| `$4D` | `branch_not_flag_predicate_relative` | `flag_id:u8, targets[result_count]:s8` | variable | `$6C5E` | **VERIFIED** |
| `$50` | `jump_absolute` | `target:u16` | 3 bytes | `$6DA9` | **VERIFIED** |
| `$51` | `switch_route_and_jump` | `route_selector:u8` | 2 bytes | `$6DA9` | **VERIFIED** |
| `$52` | `jump_current_route` | `none` | 1 byte | `$6DA9` | **VERIFIED** |
| `$53` | `return_subroutine` | `none` | 1 byte | `$6DA9` | **VERIFIED** |
| `$54` | `call_absolute` | `target:u16` | 3 bytes | `$6DA9` | **VERIFIED** |
| `$58` | `jump_relative` | `delta:s8` | 2 bytes | `$6DA9` | **VERIFIED** |
| `$60` | `mutate_flags_extended` | `counts:u8, set_ids[set_count], clear_ids[clear_count]` | 2 + set_count + clear_count bytes | `$6F2C` | **VERIFIED** |
| `$61` | `set_1_flag` | `set_ids[1]:u8` | 2 bytes | `$6F2C` | **VERIFIED** |
| `$62` | `set_2_flags` | `set_ids[2]:u8` | 3 bytes | `$6F2C` | **VERIFIED** |
| `$63` | `set_3_flags` | `set_ids[3]:u8` | 4 bytes | `$6F2C` | **VERIFIED** |
| `$64` | `clear_1_flag` | `clear_ids[1]:u8` | 2 bytes | `$6F2C` | **VERIFIED** |
| `$65` | `set_1_clear_1_flag` | `set_ids[1]:u8, clear_ids[1]:u8` | 3 bytes | `$6F2C` | **VERIFIED** |
| `$66` | `set_2_clear_1_flag` | `set_ids[2]:u8, clear_ids[1]:u8` | 4 bytes | `$6F2C` | **VERIFIED** |
| `$67` | `set_3_clear_1_flag` | `set_ids[3]:u8, clear_ids[1]:u8` | 5 bytes | `$6F2C` | **VERIFIED** |
| `$68` | `clear_2_flags` | `clear_ids[2]:u8` | 3 bytes | `$6F2C` | **VERIFIED** |
| `$69` | `set_1_clear_2_flags` | `set_ids[1]:u8, clear_ids[2]:u8` | 4 bytes | `$6F2C` | **VERIFIED** |
| `$6C` | `clear_3_flags` | `clear_ids[3]:u8` | 4 bytes | `$6F2C` | **VERIFIED** |
| `$6D` | `set_1_clear_3_flags` | `set_ids[1]:u8, clear_ids[3]:u8` | 5 bytes | `$6F2C` | **VERIFIED** |
| `$70` | `configure_scene_components` | `mask:u8, selectors[popcount(mask)]:u8` | 2 + popcount(mask) bytes | `$6F49` | **VERIFIED** |
| `$83` | `write_audio_latch_3_mirrored` | `value:u8` | 2 bytes | `$717E` | **VERIFIED** |
| `$90` | `write_audio_latch_0` | `value:u8` | 2 bytes | `$7192` | **VERIFIED** |
| `$91` | `write_audio_latch_1` | `value:u8` | 2 bytes | `$7192` | **VERIFIED** |
| `$92` | `write_audio_latch_2` | `value:u8` | 2 bytes | `$7192` | **VERIFIED** |
| `$93` | `write_audio_latch_3` | `value:u8` | 2 bytes | `$7192` | **VERIFIED** |
| `$A1` | `delay_ticks` | `duration:u8` | 2 bytes | `$71A4` | **VERIFIED** |
| `$B0` | `begin_exploration` | `exploration_mode:u8` | 2 bytes | `$71F5` | **DERIVED** |
| `$B2` | `start_irq_raster_transition_mode_2` | `none` | 1 byte | `$71F5` | **VERIFIED** |
| `$B3` | `start_irq_raster_transition_mode_3` | `none` | 1 byte | `$71F5` | **VERIFIED** |
| `$B5` | `move_fixed_point_to_target` | `axis_mode:u8, step:u8, target:u16` | 5 bytes | `$71F5` | **DERIVED** |
| `$B6` | `enable_raster_scroll_wave` | `none` | 1 byte | `$71F5` | **DERIVED** |
| `$B7` | `configure_hotspot_boundaries` | `hotspot_set:u8, boundary_selector:u8` | 3 bytes | `$71F5` | **VERIFIED** |
| `$B9` | `save_exploration_continuation` | `slot_or_mode:u8` | 2 bytes | `$71F5` | **DERIVED** |
| `$BA` | `restore_saved_coordinate_slot` | `slot_id:u8` | 2 bytes | `$71F5` | **DERIVED** |
| `$BB` | `clear_saved_coordinate_slot` | `slot_id:u8` | 2 bytes | `$71F5` | **VERIFIED** |
| `$BC` | `resume_exploration` | `exploration_mode:u8` | 2 bytes | `$71F5` | **DERIVED** |
| `$D2` | `clone_flip_background_chr` | `count:u8, records[count]:(source_tile:u8, destination_tile:u8, flags:u8)` | 2 + 3*count bytes | `$78BA` | **VERIFIED** |
| `$E0` | `fds_scene_transition` | `transition_selector:u8` | 2 bytes | `$79A7` | **DERIVED** |

## Semantic notes by family

### `$0x`: memory / ALU / built-in operations

The retail forms are `00/01/02/04/06/09/0E/0F`. The native `$0x/$Fx` handler is shared, but no `$Fx` form is source-reachable. `04` performs subtract/compare condition work without storing the arithmetic result. Retail `0F` uses built-in sequence ID 5 and enters engine state `$22`.

### `$1x`: text commands

`10/11` continue sequentially after the text state machine. `18/19` are route-terminating forms: completion performs the equivalent of `52` and transfers through the current `$A220` route. Bit 0 selects the alternate interaction/wait path, hence the deliberately mechanical `alt_wait` names.

### `$2x/$3x`: menu and selection

`20/21` open direct menu flows. `28/29` first snapshot the script PC and software-stack continuation. Bit 0 (`21/29`) adds the secondary `$A212` prompt/table selector. `30` dispatches a selection through absolute 16-bit targets; `31` uses signed relative targets. Choice count comes from the active menu record rather than the branch opcode itself.

### `$4x`: predicates

Bits 0-1 select predicate source and bit 2 selects absolute versus signed-relative targets. Retail source uses inline predicates plus compact flag predicates, including inverted flag forms. Indexed `$A20E` and actor-distance predicate forms exist in native code but are not source-reachable in the recovered retail graph.

### `$5x`: control flow and routes

`51` is stronger than a generic route branch: it records the previous route, updates current-route bookkeeping, and jumps through `$A220[new_route]`. `52` jumps through the current route without switching it. `54` uses the recovered software call stack; `53` returns from that stack. Retail `58` is the compact signed-relative jump form.

### `$6x`: persistent story/event flags

The 256 persistent flags occupy `$0480-$049F`. `60` carries explicit set/clear counts in its following byte. Nonzero low-nibble forms encode up to three set IDs and three clear IDs directly in the opcode bits; following bytes are IDs in set-then-clear order.

### `70`: scene component configuration

Retail class 7 uses only `70`. Its mask controls the packed selector list that populates scene component selectors, including static placements, palettes, actors, and palette animation.

### `83` and `90-93`: audio command latches

The generic “parameter write” description is obsolete. `83` writes `$07E3` and mirrors the value to `$D1`; `90-93` write `$07E0-$07E3`. Resident NOV3 and scene overlays consume these latches as audio commands. Individual values are not yet promoted to named songs/SFX until the audio-table correlation pass proves them.

### `A1`: delay

`A1` loads the following byte into the low byte of a countdown and zeroes the high byte; the scheduler decrements the 16-bit value until zero before advancing the script PC. `delay_ticks` avoids claiming a finer timing unit than the recovered scheduler contract requires.

### `$Bx`: exploration / raster primitives

- `B0` enters the fresh exploration initialization path; `BC` shares setup but restores saved exploration state, hence `begin_exploration` versus `resume_exploration` (**DERIVED** names).
- `B2/B3` install distinct fixed FDS IRQ timing sweeps. Their low-level raster-transition behavior is verified; narrative/directional names are intentionally withheld.
- `B5` configures a fixed-point coordinate move that stops exactly at the scripted target.
- `B6` enables the raster-time PPU-scroll waveform/distortion path via `$4A`.
- `B7` configures active hotspot/boundary selectors. `B9/BA/BB` manage exploration continuation and saved coordinate slots.

### `D2`: dynamic background CHR transform

`D2` reads a source tile from background pattern table 1, clones it into scratch CHR, optionally transforms it, and writes it to a destination tile. `$40` reverses bits within each row (horizontal flip); `$80` reverses row order in both bitplanes (vertical flip); `$C0` applies both. With no transform bits it is an ordinary runtime tile clone.

### `E0`: FDS / scene transition

Retail class E uses only `E0`. Its following selector enters the recovered FDS/scene/file transition state machine. The low-level role is stable even where individual selector values have not yet received story-facing names.

## Deliberately excluded native forms

The registry is **not** a list of everything the interpreter can theoretically decode. Examples intentionally excluded from the retail-language table include `$42/$46/$4A/$4E` indexed `$A20E` predicates, unused `$55-$57` indexed-call forms, all source-unreachable `$Cx` commands, and all source-unreachable `$Fx` forms. Engine capability and shipped source language must remain separate concepts.

## Remaining semantic-completion work

The first-pass registry gives every reachable opcode a stable low-level name and operand grammar. Follow-up work should now refine values *within* commands rather than invent new opcode families: correlate audio command values, determine human-facing direction names for raster/hotspot transitions, classify the 327 non-reached bytes only if a runtime entry is proven, and correlate FDS transition selectors with exact scene/file outcomes.
