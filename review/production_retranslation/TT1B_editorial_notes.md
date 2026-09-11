# TT1B production retranslation — editorial review

**Status:** Review-only. Nothing in this directory is consumed by the ROM build.

TT1B is the first major voice test for the production localization: the protagonist, the Girl, the Devil, the Nagoya/Owari-coded businessman, Dr. Simon, the museum elder, the priest, and church members all appear in a short span. The Japanese-source findings in `audit/AUTHENTICITY_SECOND_PASS.md` and the terminology/voice guide are binding.

## Editorial principles demonstrated here

- The protagonist sounds young, contemporary, quick, and occasionally awkward rather than like compressed subtitles.
- The Devil sounds theatrical, sardonic, entitled, and selectively old-fashioned without faux-medieval excess or a rural accent.
- The Girl is warm and poised. Feminine Japanese endings influence tone, not spelling or caricature.
- The businessman gets loud, swaggering regional flavor without being mapped to a real American dialect.
- Simon sounds precise and technical even while injured.
- The elder is courteous and measured, not generically "old-timey."
- Museum placards read like actual exhibit copy rather than telegrams.
- Sexual, religious, sacrificial, and demonic material is translated directly where the Japanese contains it.

## Representative changes

| ID | Current | Review proposal | Why it is better |
| --- | --- | --- | --- |
| TT1B/g0/r0 | `Made it... Devil Museum / I've wanted to visit.` | `Made it… Devil Museum. I've been meaning to come here.` | `一度こようと思ってたんだ` is an existing intention, not simply a generic desire. The revision sounds like spontaneous internal narration. |
| TT1B/g0/r1 | `Last saw blue sky when?` | `When was the last time I saw a blue sky?` | Restores a complete natural thought. The Japanese explicitly says `青空`, and the old line is pure byte-budget English. |
| TT1B/g0/r6 | `"Closed today. Inquire at the church."` | `"CLOSED TODAY. If you need assistance, please go to the church."` | Reads as a posted notice while retaining the functional instruction `ご用のある方は教会まで`. |
| TT1B/g0/r14 | `Used at witches' rites... Said to hold soul pacts made with devils.` | `A box used at witches' gatherings in medieval Europe. Said to have held soul contracts made with devils.` | Restores exhibit-register prose and the explicit `契約書` sense of written soul contracts. |
| TT1B/g0/r15 | `Long ago, God's child fought a fierce battle and sealed him within.` | `A legendary jar in which, thousands of years ago, the child of God is said to have imprisoned and sealed the Devil after a terrible battle.` | Restores `数千年`, the jar's legendary status, the explicit Devil referent, and both imprisonment and sealing. |
| TT1B/g0/r16 | `Ancient pharaohs used it as a charm.` | `A legendary bell said to have been used by the pharaohs of ancient Egypt to ward off evil.` | `魔除け` is specifically warding off evil, not an unspecified charm; the placard now sounds like museum copy. |
| TT1B/g0/r17 | `19th-century U.S. a devil cult's symbol... Its claws gouged hearts from sacrifices.` | `A bronze statue that became the symbol of a 19th-century American secret society devoted to Devil worship. Its razor-sharp claws tore the hearts from sacrificial victims.` | Restores `秘密結社`, the bronze-statue identity, and the explicit sacrificial-victim detail in fluent English. |
| TT1B/g0/r18 | `Late-1600s nomads wore this star medal for safe travel.` | `A star-shaped medal worn by nomadic Romani in the late 17th century to protect themselves from dangers on the road. A warding spell is engraved on it.` | Preserves the historical referent without reproducing an English slur; restores the travel-danger and engraved-spell details. |
| TT1B/g0/r31 | `Devil: Call me a devil.` | `Devil: I am what you might call… a devil.` | Better captures `いわゆるひとつの悪魔だ`, whose comic pomp is part of the Devil's characterization. |
| TT1B/g1/r0 | `Devil: No arguing.` | `Devil: There will be no debate.` | `問答無用` is categorical dismissal. The proposal is forceful while fitting the Devil's elevated self-importance. |
| TT1B/g1/r10 | `You have nice eyes.` | `You've got beautiful eyes.` | Sounds like the protagonist actually trying to flirt; still simple and youthful. |
| TT1B/g1/r14 | `You're busty... heh` | `You've got pretty big boobs… heh.` | Deliberately uncensored because `ぼいん` is a comic colloquial reference to large breasts. The directness belongs to the protagonist's awkward flirtation; it is not added vulgarity. |
| TT1B/g1/r26 | `Shut it! Move it!` | `Pipe down! You're in the way!` | Preserves the two actual ideas in `うるしゃー / じゃまだがや` rather than making the second command sound like "move faster." |
| TT1B/g1/r27 | `I'll build a giant leisure center here! It's the sticks now, but soon it'll boom!` | `I'm building a gigantic resort complex right here! It's the middle of nowhere now, but you just wait—this place'll be booming!` | Keeps the exaggerated Nagoya/Owari businessman energy through cadence and boastfulness rather than a fake American accent. |
| TT1B/g1/r28 | `Money's all! I'd sell my soul for it` | `Money is everything! For enough of it, I'd sell my soul to the Devil!` | Restores the explicit Devil and turns a broken compression fragment into the character-defining joke. |
| TT1B/g2/r5 | `I'm no land shark.` | `I'm not some real-estate shark.` | `地上げ屋` is a land-speculation/property-pressure operator; the extra context prevents modern players from reading "land shark" as random slang. |
| TT1B/g2/r9 | `I roamed the world, copying traits from old legends.` | `I traveled the world, faithfully reconstructing the features I'd heard described in old accounts.` | `忠実に再現` is explicitly faithful reconstruction. This also suits the elder's careful, educated register. |
| TT1B/g2/r12 | compressed newspaper fragments | full newspaper paragraph | The Japanese is a news report: Simon, age 84, announces a startling time-warp theory, disappears to escape media attention, and is rumored to have used his completed machine. The proposal restores journalistic flow and causal relationships. |
| TT1B/g2/r22 | `Between us... he's here now. His villa is in town. I talk too much...` | `Now, just between us… he's here. He has a secret villa in this town. Ah… I really do talk too much. There I go again…` | Preserves the elder's accidental oversharing as a character beat rather than a sequence of clipped facts. |
| TT1B/g2/r23 | `Sorry to bother you / My apologies.` | `Thanks for having me. / Sorry I couldn't be a better host.` | Localizes the paired Japanese hospitality formulas `おじゃましました / おかまいもしませんで` by function rather than literal apology-for-apology. |
| TT1B/g3/r8 | `A time-machine belt. Finally complete.` | `A belt-shaped time machine. I only just completed it.` | Makes the Time Belt concept explicit and gives Simon natural scientific exposition. |
| TT1B/g3/r23 | `Pardon our sins and forebears' sins!` | `Lord, forgive our sins and the sins of our forefathers!` | Sounds like an actual prayer while retaining the explicit ancestral-sins content recovered by the authenticity audit. |
| TT1B/g3/r29 | compressed sermon | `A brave young man stood against the Devil and gave his life to save the child of God...` | Restores the sermon as a coherent anecdote, preserves the youth's sacrifice and gentle smile, and allows the quoted final words to land emotionally. |
| TT1B/g3/r30 | compressed clauses | coherent sermon paragraph | The source develops a repeated historical pattern—chaos, Devil, fear, darkness, courageous resistance, justice. The proposal preserves that rhetoric instead of presenting sentence fragments. |
| TT1B/g3/r31 | `Devil: Oh? Still intact... I'm off on a long trip.` | `Devil: Well, well… my body's still unharmed... I am about to embark on a long journey.` | Maintains the Devil's smug elevated register and the protagonist's strong stutter. |
| TT1B/g4/r0 | `Was I always this scary?` | `Did I always look this mean?!` | `きつい顔` is a harsh/severe-looking face, not supernatural scariness. |
| TT1B/g4/r2 | `Clearly, soul contracts.` | `Why ask what you already know? Soul contracts, naturally.` | Restores the Devil's condescension (`わかりきったことを聞くな`) and makes the punch line sound like his idea of obvious routine business. |

## Deliberate restraint

The pass does **not** convert the Devil into Shakespeare, the businessman into a Southern/New York caricature, the Girl into exaggerated feminine speech, or the protagonist into a profanity machine. Those would all be "colorful" but less accurate. Characterization comes from register, cadence, word choice, and the source's actual marked features.
