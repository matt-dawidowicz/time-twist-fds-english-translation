# Translation intent-gap audit

This is a triage report, not an automatic translation grade. Records are
ranked from the project's existing Japanese/linguistic/voice/workbook evidence.
Runtime-blocked records are retained but sorted after immediately actionable
records so staging ambiguity is not guessed away.

| Score | Record | Runtime evidence | Reasons | Natural | Playable |
| ---: | --- | --- | --- | --- | --- |
| 142 | `TT6A/g0/r13` | no | natural/playable wording diverges (0.218 similarity); workbook explicitly records lost nuance; source has marked register/dialect/voice evidence | Joseph: The truth is… my betrothed, Mary, seems to be with child. But I swear to God, I've never so much as held her hand! Mary says she has no idea how it happened… but can that possibly be true? / Protagonist: Hee-haw… / Joseph: I can't believe in anything anymore! The engagement is off! | Joseph: My fiancee Mary{CTRL:0}seems to be pregnant.{CTRL:2}I swear before God,{CTRL:0}I've never even touched{CTRL:4}her hand!{CTRL:3}Says she has no idea...{CTRL:4}Can that be true?{CTRL:3}Me: Hee-haw...{CTRL:3}Joseph: Nothing's true!{CTRL:4}The engagement is off! |
| 90 | `TT3A/g2/r30` | yes | natural/playable wording diverges (0.863 similarity); workbook explicitly records lost nuance; runtime/staging evidence required before rewriting | One fragment of the note. / In blue ink: “…4 km southwest…” / “…Rebecca.” | A fragment of the note.{CTRL:0}Blue ink:{CTRL:0}'... 4 km southwest...'{CTRL:0}'... Rebecca' |
| 15 | `TT3A/g2/r7` | yes | runtime/staging evidence required before rewriting; source has marked register/dialect/voice evidence | Voice: Wait, Cougar… | Voice: Wait, Cougar... |
| 15 | `TT3B/g0/r24` | yes | runtime/staging evidence required before rewriting; source has marked register/dialect/voice evidence | Voice: Fool. You think you can escape from me? | Voice: Fool. You think{CTRL:0}you can escape from me? |
| 15 | `TT4/g4/r14` | yes | runtime/staging evidence required before rewriting; source has marked register/dialect/voice evidence | Okay… we did it… … wait. I've got a bad feeling! | Okay... we did it...{CTRL:0}{CTRL:2}... wait.{CTRL:6}I've got a bad feeling! |
