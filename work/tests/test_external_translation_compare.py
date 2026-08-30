from work.tools.external_translation_compare import overlay_sparse_payload, patch_spans


def test_patch_spans_merge_five_byte_gap():
    payload = bytearray(20)
    payload[2] = 1
    payload[8] = 2  # five zeros between changed bytes
    payload[15] = 3  # six zeros: new span
    assert patch_spans(bytes(payload)) == [(2, 9), (15, 16)]


def test_overlay_preserves_zero_writes_inside_hunk():
    base = b"abcdefghij"
    payload = bytes([0, 0, ord("X"), 0, 0, 0, 0, 0, ord("Y"), 0])
    rebuilt = overlay_sparse_payload(base, payload)
    assert rebuilt == b"abX\0\0\0\0\0Yj"
