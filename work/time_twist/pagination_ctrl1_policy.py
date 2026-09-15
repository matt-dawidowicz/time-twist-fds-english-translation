"""Additional source-locked CTRL:1 demotions from the full pagination audit."""

ADDITIONAL_PRESENTATION_ONLY_CTRL1_TEMPLATES: dict[str, str] = {
    "TT1A/g0/r26": (
        "Earnest and passionate.{CTRL:1}You see what matters."
        "{CTRL:0}A born politician.{CTRL:6}Honor comes first."
        "{CTRL:4}Money is another story.{CTRL:4}Can be willful, selfish"
        "{CTRL:3}Crave dramatic romance."
    ),
    "TT1B/g1/r10": "Me: You have nice eyes.{CTRL:1}Girl: Thanks.",
    "TT1B/g1/r11": "Me: Nice nose.{CTRL:1}Girl: ........",
    "TT1B/g1/r12": (
        "Me: Lucky earlobes.{CTRL:1}Girl: Pfft... funny guy"
        "{CTRL:0}Me: Ha ha...{CTRL:0}Girl: Hee hee...{CTRL:4}"
        "{CTRL:3}She laughed!{CTRL:4}{CTRL:3}Me: What's your name?"
        "{CTRL:4}Girl: I'm..."
    ),
    "TT1B/g1/r14": "Me: You're busty... heh{CTRL:1}Girl: Eek!",
    "TT1B/g2/r2": (
        "...: Oh, I see!{CTRL:1}I have a special item"
        "{CTRL:0}not on museum display.{CTRL:0}Please come inside."
    ),
    "TT1B/g3/r31": (
        "Devil: Body's intact.{CTRL:1}Me: G-give my body back"
        "{CTRL:0}Devil: I think not.{CTRL:0}A long journey awaits."
    ),
    "TT2/g0/r9": "What's going on?!{CTRL:1}I'm in another body!",
    "TT2/g2/r15": (
        "Gordo: Pierre, listen!{CTRL:1}Chino fell for Jeanne"
        "{CTRL:0}at first sight, I hear."
    ),
    "T22/g0/r4": "Jailer: If only we had{CTRL:1}proof... just to myself",
    "T22/g1/r1": (
        "\"PACT{CTRL:1}O Devil, lord of night,{CTRL:0}I kneel. You are my god"
        "{CTRL:6}of justice. I vow all{CTRL:4}to vice, slander, evil."
        "{CTRL:3}Bishop\""
    ),
    "TT3A/g0/r29": (
        "Devil: Pact complete.{CTRL:1}Your soul for a share"
        "{CTRL:0}of my power.{CTRL:6}And I too..."
    ),
    "TT3A/g1/r21": (
        "Ralph: Head west from{CTRL:1}the woods to a park."
        "{CTRL:0}Ask Rebecca for orders.{CTRL:6}Me: Rebecca?!"
        "{CTRL:3}Ralph: Network codename{CTRL:4}Pass: Drop dead, Hitler"
    ),
    "TT3A/g1/r22": (
        "Drop dead, Hitler!{CTRL:1}Gestapo are everywhere."
        "{CTRL:0}Be very careful.{CTRL:0}Don't draw attention."
    ),
    "TT3A/g2/r29": (
        "He holds a paper.{CTRL:1}Simon: A child gave it"
        "{CTRL:0}to me. A stranger asked{CTRL:6}him to. I take it."
        "{CTRL:3}Blue writing."
    ),
    "TT3A/g3/r2": (
        "Man: One of Rebecca's?{CTRL:1}Me: No. I fled the camp"
        "{CTRL:0}last night."
    ),
    "TT3A/g3/r3": (
        "Man: Simon, physicist.{CTRL:1}I had contacts ask"
        "{CTRL:0}Rebecca for refuge..."
    ),
    "TT3A/g3/r24": "I reach down for it.{CTRL:1}There's paper inside.",
    "TT3A/g3/r25": "I smash it for the note{CTRL:1}Writing in red ink.",
    "TT3A/g4/r9": "Old man: By the way...{CTRL:1}know Gestapo greeting?",
    "TT3B/g1/r13": "Me: Read its words!{CTRL:1}Read it out loud!{CTRL:2}Cougar! Cougar!",
    "TT3B/g1/r22": (
        "Schmidt: Border ahead.{CTRL:1}Cougar: Mind's blank..."
        "{CTRL:0}Why am I here...?{CTRL:6}Simon: You must have"
        "{CTRL:4}hit your head badly.{CTRL:3}Schmidt: What a horror."
        "{CTRL:3}Cougar: Might change my{CTRL:4}whole view of life."
        "{CTRL:3}Simon: Indeed..."
    ),
    "TT4/g0/r10": (
        "Priest: The dead ascend{CTRL:1}to the underworld."
        "{CTRL:0}Almost passed through."
    ),
    "TT4/g0/r23": "I shake it lightly.{CTRL:1}It makes a sweet sound.",
    "TT4/g3/r21": (
        "Greece's age is over...{CTRL:1}Macedonia will rise"
        "{CTRL:0}to world supremacy."
    ),
    "TT5/g0/r3": (
        "Meyer: You worked hard.{CTRL:1}It is late today, so"
        "{CTRL:0}leave tomorrow instead.{CTRL:6}Belle: Understood."
    ),
    "TT5/g0/r27": "Dirty, wrinkled bills.{CTRL:1}Belle: Blood and sweat.",
    "TT5/g1/r9": "Be strong, George!{CTRL:1}Are you okay, George?!{CTRL:0}George!",
    "TT5/g1/r16": (
        "Meyer: Get to work now.{CTRL:1}To work efficiently,"
        "{CTRL:0}keep the proper order."
    ),
    "TT5/g2/r7": (
        "Dirty, wrinkled bills.{CTRL:1}Me: These bills..."
        "{CTRL:0}Tom: Paid this morning.{CTRL:0}Me: ..."
    ),
    "TT5/g2/r8": (
        "Tom: Trader comes soon.{CTRL:1}Thanks to George, we'll"
        "{CTRL:0}buy stock. Good news!"
    ),
    "TT5/g3/r13": (
        "Meyer: Awful people...{CTRL:1}Don't despair, Belle."
        "{CTRL:0}Work here, save again.{CTRL:6}Me: ..."
    ),
    "TT5/g3/r23": "A hand poised to grasp.{CTRL:1}I recall seeing it...",
    "T25/g0/r11": (
        "Soldier 1: Your master{CTRL:1}is quite the man. When"
        "{CTRL:0}the South faltered, he{CTRL:0}defected, gave intel"
        "{CTRL:3}Soldier 2: Cut it out!{CTRL:4}Soldier 1: I admire"
        "{CTRL:4}how well he gets by..."
    ),
    "T25/g0/r17": "Tall, but skinny.{CTRL:1}His set mouth shows{CTRL:0}a strong will.",
    "T25/g0/r18": (
        "Lincoln: America will{CTRL:1}be reborn. A time will"
        "{CTRL:0}come to use your gifts."
    ),
    "T25/g1/r6": (
        "Through the open gap...{CTRL:1}a black leather whip"
        "{CTRL:0}a cloth hood with holes"
    ),
    "T25/g1/r19": (
        "Lincoln: Your business?{CTRL:1}Meyer: I have a favor."
        "{CTRL:0}Please appoint me your{CTRL:0}special adviser."
        "{CTRL:3}Lincoln: ...{CTRL:3}Meyer: A Southerner"
        "{CTRL:4}would balance politics!"
    ),
    "TT6A/g0/r7": (
        "Joseph, Mary... a child{CTRL:1}that would mean..."
        "{CTRL:0}could it be...?"
    ),
    "TT6A/g1/r8": (
        "I can't eat this...{CTRL:1}Me: Brr! Brrrr!"
        "{CTRL:0}Weird... but it's good."
    ),
    "TT6A/g1/r23": (
        "Last night, an angel...{CTRL:1}\"You bear God's child."
        "{CTRL:0} Raise it with Joseph.\"{CTRL:6}Joseph won't believe me"
    ),
    "TT6A/g2/r3": "Mary: You'll carry it?{CTRL:1}She puts it in my mouth",
    "TT6B/g0/r29": (
        "Camel: What's up?{CTRL:1}Me: Can I eat the hay?"
        "{CTRL:0}Camel: Sure. Eat away"
    ),
    "TT6B/g1/r14": "Man: Seems this is it.{CTRL:1}Man: Finally here...",
    "TT6C/g0/r5": (
        "Devil: None rival me!{CTRL:1}Your precious savior"
        "{CTRL:0}is still only a baby..."
    ),
    "TT6C/g0/r7": "Me: Hee-haw!{CTRL:1}I bite his rear hard.",
    "TT6C/g0/r17": "Devil: Stay out, brat!{CTRL:1}Mary: !",
    "TT6C/g0/r18": (
        "Devil: This body's mine{CTRL:1}God's child and Devil"
        "{CTRL:0}now fused beautifully!"
    ),
    "TT6C/g0/r28": (
        "Baby sleeps peacefully.{CTRL:1}Joseph: The angel said"
        "{CTRL:0}we'll name him Demon."
    ),
    "TT6C/g1/r15": (
        "Me: I can finally go!{CTRL:1}My finger trembling,"
        "{CTRL:0}I press keys carefully.{CTRL:6}September 25, 1995."
        "{CTRL:3}Museum, before he came."
    ),
    "TT6C/g1/r18": (
        "Devil: Behold the view!{CTRL:1}Bow and swear loyalty,"
        "{CTRL:0}all the world is yours.{CTRL:6}A fair bargain, yes?"
    ),
    "TT6C/g1/r24": "Tokyo, Sept. 25, 1995{CTRL:1}No doubt about it...",
    "TT6C/g2/r12": (
        "Devil: So you know me.{CTRL:1}End this foolish fight"
        "{CTRL:0}Join forces with me!{CTRL:6}You feel like kin to me"
        "{CTRL:3}Me: Shut up!"
    ),
}
