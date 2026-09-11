# English dialogue pagination policy

Production English uses the full four-row NOV2 dialogue buffer before requiring a continuation whenever the source control is only Japanese page geometry.

`CTRL:2` has mixed behavior in the recovered script: it can represent an ordinary page/box transition or a meaningful speaker/timing boundary. Production layout therefore demotes a `CTRL:2` only when the first English layout proves that it interrupts a continuous phrase and the following chunk does not begin a new speaker. Strong sentence/section breaks and speaker transitions remain preserved.

Controls `1`, `3`, and `6` remain mandatory semantic controls and must stay in source order. The production validator permits only source `CTRL:2` values to be omitted; it rejects invented or reordered semantic controls.

Regression coverage includes the TT1A personality-result case that previously stopped after two visible rows and the Maradul Barao Garadura chant, whose strong `CTRL:2` pause remains intact.
