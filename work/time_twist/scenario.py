"""Hardened public facade for scenario parsing and rebuilding."""

from __future__ import annotations

from pathlib import Path

from . import _scenario_core as _core

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)
del _name

LOAD_ADDRESS = _core.LOAD_ADDRESS
MAX_DICTIONARY_ENTRY_COUNT = _core.MAX_DICTIONARY_ENTRY_COUNT
ScenarioRecord = _core.ScenarioRecord
ScenarioBank = _core.ScenarioBank
ScenarioError = _core.ScenarioError
rebuild_scenario_bank = _core.rebuild_scenario_bank
render_symbols = _core.render_symbols


def parse_scenario_bank(
    path: Path,
    *,
    load_address: int = LOAD_ADDRESS,
    minimum_dictionary_entries: int = 0,
) -> ScenarioBank:
    """Parse a bank and include dictionary slots required outside dialogue.

    ``minimum_dictionary_entries`` is a one-based source dictionary floor
    supplied by callers that have decoded fixed-address UI records. Ordinary
    parsing remains reachability-based when the default zero is used. Nested
    references in the newly included entries are followed transitively.
    """
    if not 0 <= minimum_dictionary_entries <= MAX_DICTIONARY_ENTRY_COUNT:
        raise ScenarioError(
            f"dictionary minimum {minimum_dictionary_entries} is out of range"
        )
    bank = _core.parse_scenario_bank(path, load_address=load_address)
    required_count = max(minimum_dictionary_entries, len(bank.dictionary))
    if required_count == len(bank.dictionary):
        return bank

    dictionary_offset = bank.dictionary_address - bank.load_address
    dictionary = bank.dictionary
    end_offset = bank.dictionary_end_offset
    while len(dictionary) < required_count:
        dictionary, end_offset = _core._decode_fixed_records(
            bank.data,
            dictionary_offset,
            required_count,
        )
        nested_count = _core._maximum_dictionary_reference(dictionary)
        if nested_count > MAX_DICTIONARY_ENTRY_COUNT:
            raise ScenarioError(
                f"dictionary reference {nested_count} is out of range"
            )
        required_count = max(required_count, nested_count)

    return ScenarioBank(
        path=bank.path,
        data=bank.data,
        load_address=bank.load_address,
        dictionary_address=bank.dictionary_address,
        group_table_address=bank.group_table_address,
        group_addresses=bank.group_addresses,
        dictionary=dictionary,
        dictionary_end_offset=end_offset,
        records=bank.records,
    )
