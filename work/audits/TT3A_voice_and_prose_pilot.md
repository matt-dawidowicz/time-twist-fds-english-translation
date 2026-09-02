# TT3A voice and prose pilot

This pass extends the source-first voice/prose revision into TT3A: July 1944, the POW camp, escape network, Hitler/Devil pact scene, Dr. Simon's flight from the Nazi weapons program, and Gestapo contact checks.

## Editorial rules

- Exact Japanese meaning remains authoritative.
- External fan-translation wording is never copied.
- Source control-code order is preserved exactly.
- Every control-delimited English segment remains at or below 24 visible columns.
- The protagonist keeps his contemporary 1995 internal voice while inhabiting Cougar's body.
- POWs, resistance contacts, German soldiers, Gestapo agents, Simon, Hitler, and the Devil retain distinct registers.
- German characters do not receive phonetic German accents.
- Historically ugly or violent source material is not euphemized. The pass also does not invent additional content absent from the Japanese.

## Character direction

### Protagonist

Quick contemporary contractions, fragments, panic, and dry observations. He does not acquire a generic 1940s GI voice merely because he occupies Cougar's body.

### German soldiers

Short military commands and institutional threats. No ornamental villain language and no fake accent.

### Nick

Laconic, rough American POW voice. Existing blunt profanity remains where supported by the source.

### Frankie

Talkative, casual POW/expository voice. His pendant exchange is now spoken dialogue rather than item-description prose. His wartime exposition remains direct and concrete.

### Ralph

Operational resistance/escape-network briefing voice: compact instructions, code names, passwords, and warnings.

### Dr. Simon

The same educated, precise scientist established in 1995, now under severe ethical pressure. His formal baseline remains distinct from the POWs even when urgency shortens his syntax.

### Hitler

Grandiose ritual diction followed by fear and pleading. Grotesque details present in the Japanese are retained rather than generalized away.

### Devil

Same sardonic theatrical voice established earlier. The bargain is stated more clearly, his intended revenge has its missing referent restored, and his contempt for Hitler is more explicit where the Japanese supports it.

### Gestapo agents

Crisp field-command speech, not theatrical villainy. The female agent's English-loan command is naturalized to idiomatic English while retaining the same threat and reveal.

### Older quizmaster

Lightly folksy elderly cadence from the marked role-language, without a caricature regional accent. His recognition gesture also restores the source's reference to the tip of the nose.

## Source-grounded restorations

- `TT3A/g0/r24`: restores the uncertainty in `ki no sei ka`; the protagonist only feels as though the object is giving him courage.
- `TT3A/g0/r30`: restores `yatsu ni`, specifying the target of the Devil's revenge.
- `TT3A/g0/r31`: restores the stronger verb in Hitler's request and the Devil's explicit instruction that Hitler handle the matter himself.
- `TT3A/g1/r25`: makes the destination in `gasushitsu ni okurikonderu` concrete rather than euphemistic.
- `TT3A/g2/r29`: restores that a stranger asked the child to deliver Simon's note.
- `TT3A/g3/r4`: restores the moral force of `hitogoroshi` rather than using a weaker generic verb.
- `TT3A/g3/r13`: restores both omitted location details: the destination is four kilometers southwest **of here**, and the recipient should wait **out front** of the old watermill.

## Prose direction

- Contemporary internal narration uses contractions where appropriate.
- Military commands are shorter and sharper.
- Frankie sounds conversational rather than like an encyclopedia entry.
- Ralph's `Rebecca` explanation is clarified as a network codename.
- Simon remains precise even when emotionally forceful.
- Hitler and the Devil receive more contrast: grandiosity and desperation versus contempt and theatrical authority.
- Sensitive historical language that is explicitly present in the Japanese is retained in character dialogue rather than silently modernized.

## Validation

The final TT3A candidate contains 152 scenario records and changes 53 of them.

Local structural validation found:

- exact control-event sequence preserved for every changed record;
- no control-delimited English segment longer than 24 visible characters;
- maximum changed-segment width: 24 characters;
- no unsupported English-font characters introduced;
- revised TT3A visible text is 8 characters shorter overall than the prior branch version.

The raw-character reduction is useful headroom but is not proof of packed fit. TT3A uses dictionary compression and has tight bank capacity, so the canonical compression/release-build fit gate remains required before release approval.
