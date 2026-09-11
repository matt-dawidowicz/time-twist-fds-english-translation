# FDS load profiling

This diagnostic pass measures Time Twist's runtime use of the FDS BIOS
`LoadFiles` routine at `$E1F8`. It is analysis-only: the profiler does not
modify game memory, disk images, translation data, or release behavior.

## Static map

Run the canonical runtime diagnostic against the two original Japanese disks:

```text
time-twist-runtime load-profile \
  --zenpen path/to/time_twist_zenpen_japan.fds \
  --kouhen path/to/time_twist_kouhen_japan.fds
```

The original revision has two literal `JSR $E1F8` instructions, both in the
resident `NOV2` overlay:

- `$6008`: the dynamic scenario/graphics loader;
- `$606D`: the fixed NOV4/SAVE loader.

The scenario loader's inline DiskID pointer is patched between the TT1/TT2 and
side-A/side-B structures. Its file-list buffer at `$60DF` is populated from a
15-entry, four-byte selector table at `$7BA5`. `load-profile` source-guards the
call instructions and the selector-copy code before interpreting that table.

The static report also identifies the last physical file required by each
selector entry. This exposes how much declared file data lies after that file,
which is the maximum portion a bounded custom loader could avoid traversing.
It is not a timing estimate; actual elapsed time must come from the runtime
trace.

## Mesen 2 runtime trace

Open the game in Mesen 2, then open the scripting window and load:

```text
work/tools/mesen_fds_load_profile.lua
```

The script hooks the two known NOV2 wrapper calls and their return points. It
also hooks `$E1F8` itself as a coverage guard: an unexpected BIOS entry is
logged if some path bypasses both known wrappers.

For every load, the script records:

- sequential load number;
- wrapper type;
- start/end frame and CPU cycle count;
- runtime-patched TT1/TT2 DiskID and side number;
- exact file IDs requested;
- BIOS return error code in A;
- number of files loaded in Y.

Log records begin with `TTLOAD` and are tab-delimited. `START` and `END` rows
share the same `seq` value. A normal successful load ends with `error=$00`.

For the first benchmark, use the original Japanese images and play through a
representative set of scene transitions. Do not enable emulator fast-forward,
run-ahead, or disk-speed overrides. Keep those emulator settings identical for
all later comparisons.

## Current static opportunities

The static map already shows several loads whose requested files end well
before the declared end of the side. Two useful examples are:

- TT3 selector entries 5/6: required files end at archival byte 23,247 while
  the declared used area ends at byte 51,588, leaving 28,341 bytes afterward;
- TT6C selector entry 13: required files end at byte 38,389 while the declared
  used area ends at byte 50,843, leaving 12,454 bytes afterward.

These figures only establish an optimization ceiling. Step 1 is complete only
once the Mesen trace shows how often each selector is used and how many frames
and cycles each real load consumes.
