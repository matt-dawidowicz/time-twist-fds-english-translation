Time Twist English translation v80 — clarity candidate

Based on v79, including all previous fixes. Three approved changes: home comparison, explicit numerical coyote rule, and separation of Mary's speech from narration. See Clarity-changes-v80.txt. Further review and the full-section skip are recorded in Further-clarity-review.txt.

Includes the combined four-side FDS plus separate Zenpen and Kouhen two-side images.

Checks: 1,304 records; 721 menu labels; 73 native renders; 301 native text lookups; 25 action sites; 17 empty Use paths; 32 normal Use choices; 312 main-menu choices; 39 scored quiz routes. No repacking, dictionary changes, or file-size growth. Full emulator/PPU playtesting remains; waits are simulated by the native 6502 harness.

Boot cleanly; old save states can restore earlier banks.

Rebuild: python3 source/build_v80.py /path/to/v79-combined.fds .
Validate: python3 source/verify_v80.py /path/to/v79-combined.fds Time-Twist-v80-clarity-candidate.fds reports
Capacity: python3 source/check_capacity.py /path/to/v79-combined.fds
