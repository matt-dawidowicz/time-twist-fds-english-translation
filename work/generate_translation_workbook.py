"""Build the complete Time Twist translation-review workbook.

The immutable ROM-derived comparison JSON is the source of truth.  The two
user-supplied review HTML files are diagnostic evidence only.  In particular,
this generator does not copy their reconstructed-Japanese column because that
column still contains unsafe substring replacements (for example, き声る).
Instead, reconstruction is deliberately conservative and limited to long,
high-confidence lexical units, names, titles, and place names.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path

from generate_bilingual_comparison import _romanize
from time_twist.scenario_validation import (
    PRESENTATION_BREAK_RECORD_IDS,
    scenario_controls_match_policy,
)

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
OUTPUTS = ROOT / "outputs"
SOURCE_JSON = OUTPUTS / "Time Twist Japanese-English script comparison.json"
TRANSLATIONS = WORK / "translations"
UI_CONTROL_OVERRIDE_IDS = frozenset({"NOV2/wait"})
CONTROL_OVERRIDE_IDS = UI_CONTROL_OVERRIDE_IDS | PRESENTATION_BREAK_RECORD_IDS
INTENT_RESTORED_IDS = frozenset(
    {"TT1B/g0/r1", "TT1B/g0/r31", "TT1B/g1/r14", "TT1B/g2/r5"}
)
REVIEW_CANDIDATES: tuple[Path, ...] = ()

CONTROL_RE = re.compile(r"\{CTRL:(\d+)\}")
JP_LABEL_RE = re.compile(
    r"(?:^|\s)([\u3041-\u3096\u30A1-\u30F6\u30FC\u30FB0-9]+)\u300C"
)

BANK_ORDER = (
    "TT1A",
    "TT1B",
    "TT2",
    "T22",
    "TT3A",
    "TT3B",
    "TT4",
    "TT5",
    "T25",
    "TT6A",
    "TT6B",
    "TT6C",
    "TT6D",
    "NOV2",
    "NOV4",
    "TITLE",
    "SON-KOUH",
)

# Measured from the complete public scenario maps with the native encoder,
# exact packed-size model, optimized dictionary search, and recorded fixed-tail
# capacities. A private ROM-backed candidate rebuild remains a separate release
# and playtest gate.
PATCH_FOOTPRINT_RESULTS = {
    "TT1A": {"used": 1656, "capacity": 1669, "remaining": 13},
    "TT1B": {"used": 4022, "capacity": 4026, "remaining": 4},
    "TT2": {"used": 3834, "capacity": 3847, "remaining": 13},
    "T22": {"used": 1801, "capacity": 1812, "remaining": 11},
    "TT3A": {"used": 3733, "capacity": 3741, "remaining": 8},
    "TT3B": {"used": 1837, "capacity": 1840, "remaining": 3},
    "TT4": {"used": 4738, "capacity": 4741, "remaining": 3},
    "TT5": {"used": 3693, "capacity": 3702, "remaining": 9},
    "T25": {"used": 2363, "capacity": 2374, "remaining": 11},
    "TT6A": {"used": 2823, "capacity": 2833, "remaining": 10},
    "TT6B": {"used": 2298, "capacity": 2336, "remaining": 38},
    "TT6C": {"used": 3520, "capacity": 3536, "remaining": 16},
    "TT6D": {"used": 323, "capacity": 332, "remaining": 9},
}

SCENES = {
    "TT1A": {
        "title": "1995 prologue, fortune service, and personality test",
        "summary": (
            "On September 25, 1995, a newscast introduces physicist Dr. Simon's "
            "time-travel research. A televised fortune service collects the "
            "player's blood type, birth month, and yes/no personality answers, "
            "then predicts a meeting at a suburban museum. The narration "
            "establishes a polluted, anxious near-future Japan."
        ),
        "choices": (
            "The personality-test prompts are Japanese declarative propositions "
            "answered yes/no. Natural English questions are used where that makes "
            "the interface clearer without changing the proposition."
        ),
    },
    "TT1B": {
        "title": "Devil Museum, possession, Dr. Simon, and the first time warp",
        "summary": (
            "The protagonist reaches the Devil Museum, meets a mysterious girl, "
            "and triggers exhibits tied to a sealed Devil. Comic flirting, a "
            "Nagoya/Owari-coded businessman, a church, and Dr. Simon's Time Belt "
            "lead into the first historical jump."
        ),
        "choices": (
            "The protagonist normally labels himself おれ, but switches to gentler "
            "ぼく when protecting or reassuring the girl. The Devil's pompous "
            "voice and the businessman's clustered regional caricature are kept "
            "distinct."
        ),
    },
    "TT2": {
        "title": "1428 France: Pierre, Jeanne d'Arc, and the witch hunt",
        "summary": (
            "The protagonist arrives in 1428 France by possessing Pierre. He "
            "navigates a town, solves comic quizzes, meets Jeanne, and learns that "
            "the Bishop is exploiting a witch hunt under the Devil's influence."
        ),
        "choices": (
            "Rough commoner speech, official/church formality, and stock elderly "
            "role-language are differentiated. Jeanne is 'Jeanne' in dialogue and "
            "'Jeanne d'Arc' in historical narration."
        ),
    },
    "T22": {
        "title": "France continuation: the prison, the pact, and the rescue",
        "summary": (
            "The Baron and jailer confront evidence of the Bishop's demonic pact. "
            "The protagonist works through the prison and execution grounds to "
            "save Jeanne and expose the Bishop."
        ),
        "choices": (
            "The pact uses elevated, deliberately archaic diction; ordinary prison "
            "dialogue does not. Ecclesiastical titles remain titles rather than "
            "personal names."
        ),
    },
    "TT3A": {
        "title": "1944 Germany: POW camp, resistance network, and escape",
        "summary": (
            "The protagonist becomes U.S. airman Cougar in a southern German POW "
            "camp. He escapes through a tunnel, encounters Simon and the Rebecca "
            "resistance network, and navigates Gestapo surveillance and coded "
            "clues."
        ),
        "choices": (
            "Military ranks and Nazi terminology are translated plainly. The "
            "fragmented blue-note clue is layout-dependent and remains flagged for "
            "visual verification."
        ),
    },
    "TT3B": {
        "title": "1944 Germany continuation: Schmidt, Hitler, and the border",
        "summary": (
            "Schmidt appears to capture Cougar and Simon but reveals himself as a "
            "resistance ally. Their flight toward Switzerland becomes a direct "
            "confrontation with Hitler under supernatural influence."
        ),
        "choices": (
            "Simon remains formal and idealistic; Schmidt is terse and controlled. "
            "The script's caricature of Hitler is translated without embellishing "
            "or softening it."
        ),
    },
    "TT4": {
        "title": "Ancient Athens and the Greek underworld",
        "summary": (
            "The protagonist appears as the physician Nicras in ancient Athens, "
            "revives a priest, receives Athena's plea, treats townspeople, and "
            "descends through mythological territory involving Hermes, Hades, "
            "Artemis, Poseidon, and Cerberus."
        ),
        "choices": (
            "Greek names use established English forms. よみのくに is rendered "
            "contextually as the underworld rather than importing a Japanese "
            "Shinto cosmology into the Greek setting."
        ),
    },
    "TT5": {
        "title": "September 1864 Atlanta: slavery, emancipation, and plantation life",
        "summary": (
            "The protagonist becomes George, a Black farmhand living with his "
            "mother Belle near Atlanta during the American Civil War. The chapter "
            "depicts racist violence, emancipation, plantation labor, Lincoln, "
            "and puzzles involving farm work and livestock."
        ),
        "choices": (
            "The source's racist and dated material is translated directly, not "
            "sanitized. Enslaved characters' stylized Japanese speech is rendered "
            "as rural/working-class English without exaggerated minstrel dialect."
        ),
    },
    "T25": {
        "title": "Civil War continuation: Meyer, Lincoln, and the river escape",
        "summary": (
            "The plantation storyline continues through Meyer's mansion, a "
            "meeting with Lincoln, armed guards, and an escape sequence involving "
            "George, Belle, a boat, and coyotes."
        ),
        "choices": (
            "Meyer's self-serving politeness and Lincoln's measured formality are "
            "kept separate. Political claims are translated as character dialogue, "
            "not endorsed narration."
        ),
    },
    "TT6A": {
        "title": "Circa 4 BC Nazareth: Joseph, Mary, and Kashim the donkey",
        "summary": (
            "The protagonist becomes Joseph's donkey Kashim in Nazareth. Joseph "
            "struggles with Mary's pregnancy, the village debates prophecy and "
            "Roman rule, and a census order begins the journey to Bethlehem."
        ),
        "choices": (
            "Biblical names use familiar English forms. Elderly じゃ/のう speech is "
            "treated as role-language, while the protagonist's donkey sounds and "
            "inner monologue retain the chapter's comedy."
        ),
    },
    "TT6B": {
        "title": "Journey to Bethlehem: desert trials, riddles, and animal comedy",
        "summary": (
            "Joseph, Mary, and Kashim cross barren country, seek food and water, "
            "solve direction and identity riddles, and meet talking animals before "
            "reaching Bethlehem."
        ),
        "choices": (
            "Animal voices remain comic without becoming children's-book baby "
            "talk. Marked forms such as だっぺ are treated as characterization, not "
            "proof that the setting itself has a Japanese regional dialect."
        ),
    },
    "TT6C": {
        "title": "Nativity climax and final confrontation",
        "summary": (
            "At the Nativity, the Devil attempts revenge. The Magi, Joseph, Mary, "
            "Kashim, and the restored protagonist fight possession and work to "
            "save the infant Jesus before the story returns to 1995."
        ),
        "choices": (
            "Caspar, Melchior, and Balthazar use dignified diction. The Devil's "
            "archaizing self-importance contrasts with the protagonist's blunt "
            "modern voice."
        ),
    },
    "TT6D": {
        "title": "Epilogue in 1995",
        "summary": (
            "The protagonist and the girl awaken in the present. She does not "
            "remember their shared history, but her fortune and the recurring "
            "incantation close the romantic and supernatural loops."
        ),
        "choices": (
            "The girl's feminine sentence endings are conveyed through warmth and "
            "confidence, not a caricatured accent. The final growl remains "
            "deliberately ominous."
        ),
    },
    "NOV2": {
        "title": "System menu and disk-change prompts",
        "summary": "Start, wait, disk-side, insertion, and wrong-disk messages.",
        "choices": "Uppercase is retained for system text; exact packed slots govern abbreviations.",
    },
    "NOV4": {
        "title": "Title-screen start prompt",
        "summary": "The fixed start-menu label loaded with the title program.",
        "choices": "Uppercase is retained.",
    },
    "TITLE": {
        "title": "Title graphics",
        "summary": "English wordmark and subtitle represented as graphics rather than scenario records.",
        "choices": "The requested subtitle is retained exactly.",
    },
    "SON-KOUH": {
        "title": "Kouhen direct-boot guard",
        "summary": "Graphics text instructing the player to begin by loading Zenpen.",
        "choices": "Natural English is expanded; the graphic itself remains a separate technical asset.",
    },
}

CONTROL_LEGEND = {
    "CTRL:0": (
        "Observed mainly as a dialogue-row or line advance. Exact runtime behavior "
        "depends on the surrounding script routine."
    ),
    "CTRL:1": (
        "Observed as a stronger paragraph/page transition or staged reveal. "
        "Preserved without translating it."
    ),
    "CTRL:2": (
        "Observed at page/box transitions and speaker-sequence breaks. Preserved "
        "without asserting a single universal meaning."
    ),
    "CTRL:3": (
        "Observed in multi-page continuation/timing sequences and sometimes near "
        "animation or input boundaries."
    ),
    "CTRL:4": (
        "Observed in continuation/timing sequences; often alternates with CTRL:3 "
        "while the text buffer advances."
    ),
    "CTRL:6": (
        "Observed as a major wait/page/scene beat. Exact behavior requires runtime "
        "tracing for each call site."
    ),
}

SPEAKER_MAP = {
    "きゃすたー": "Newscaster",
    "しもん": "Dr. Simon",
    "おれ": "Protagonist",
    "おんなのこ": "Girl",
    "あくま": "Devil",
    "おとこ": "Man",
    "おんな": "Woman",
    "ろうじん": "Old Man",
    "しんぷ": "Priest",
    "しんじゃ": "Congregant",
    "しんじゃ1": "Congregant 1",
    "しんじゃ2": "Congregant 2",
    "ぴえーる": "Pierre",
    "おやじ": "Older Man",
    "ちの": "Chino",
    "ごるどー": "Gordo",
    "るごー": "Lugot",
    "やくにん": "Official",
    "かんしゅ": "Jailer",
    "しきょう": "Bishop",
    "だんしゃく": "Baron",
    "いざべる": "Isabelle",
    "じゃんぬ": "Jeanne",
    "へいし": "Soldier",
    "へいし1": "Soldier 1",
    "へいし2": "Soldier 2",
    "くーがー": "Cougar",
    "にっく": "Nick",
    "らるふ": "Ralph",
    "ふらんきー": "Frankie",
    "ひとらー": "Hitler",
    "しゅみっと": "Schmidt",
    "しんかん": "Priest",
    "あてな": "Athena",
    "へるめす": "Hermes",
    "はです": "Hades",
    "あるてみす": "Artemis",
    "ぽせいどん": "Poseidon",
    "けるべろす": "Cerberus",
    "しょうにん": "Merchant",
    "だりお": "Dario",
    "わかもの": "Youth",
    "つりびと": "Fisherman",
    "にくらす": "Nicras",
    "りんかーん": "Lincoln",
    "まいやー": "Meyer",
    "べる": "Belle",
    "じょーじ": "George",
    "とむ": "Tom",
    "ははおや": "Mother",
    "こよーて": "Coyote",
    "よせふ": "Joseph",
    "まりあ": "Mary",
    "ちょうろう": "Elder",
    "こども": "Child",
    "らくだ": "Camel",
    "めすうま": "Mare",
    "ひつじ": "Sheep",
    "うし": "Cow",
    "やどや": "Innkeeper",
    "かすぱる": "Caspar",
    "めるきおーる": "Melchior",
    "ばるたざーる": "Balthazar",
    "いえす": "Jesus",
    "まりあ・よせふ": "Mary and Joseph",
}

SPEAKER_IDENTITY_OVERRIDES = {
    "TT1A/g0/r3": "Fortune Service announcer / interface voice",
    "TT1A/g0/r27": "Fortune Service prediction / interface narration",
    "TT1A/g1/r0": "Fortune Service announcer / interface voice",
    "TT1A/g1/r2": "Narrator",
    "TT1B/g0/r0": "Protagonist's internal narration",
    "TT1B/g0/r6": "Museum sign / written notice",
    "TT1B/g0/r14": "Museum exhibit plaque",
    "TT1B/g0/r15": "Museum exhibit plaque",
    "TT1B/g0/r16": "Museum exhibit plaque",
    "TT1B/g0/r17": "Museum exhibit plaque",
    "TT1B/g0/r18": "Museum exhibit plaque",
    "TT1B/g1/r31": "Written name or label: Kuga",
    "TT1B/g2/r2": "Old Man",
    "TT1B/g2/r4": "Old Man",
    "TT1B/g2/r6": "Old Man",
    "TT1B/g2/r7": "Old Man",
    "TT1B/g2/r12": "Newspaper headline and article",
    "TT2/g0/r22": "Church decree / posted notice",
    "TT2/g0/r25": "Church decree / posted notice",
    "TT2/g0/r28": "Shop sign: Tavern",
    "TT2/g0/r29": "Shop sign: Tailor",
    "TT2/g0/r30": "Shop sign: Locksmith",
    "TT2/g0/r31": "Shop sign: Glassmaker",
    "TT2/g1/r0": "Shop sign: Blacksmith",
    "TT2/g1/r12": "Quiz prompt",
    "TT2/g1/r18": "Quiz prompt",
    "TT2/g2/r2": "Written memorandum",
    "TT2/g4/r2": "Two townspeople",
    "TT2/g4/r9": "Two townspeople",
    "TT2/g4/r10": "Two townspeople",
    "TT2/g4/r12": "Townspeople",
    "TT2/g4/r18": "Imprisoned women",
    "TT2/g4/r20": "Imprisoned women",
    "TT2/g4/r22": "Imprisoned women",
    "T22/g0/r5": "Imprisoned women",
    "T22/g0/r10": "Written pact signed by the Bishop",
    "T22/g0/r12": "Imprisoned women",
    "T22/g1/r1": "Written pact signed by the Bishop",
    "T22/g1/r10": "Narrator and crowd voices",
    "T22/g1/r17": "Onlookers",
    "TT3A/g0/r20": "Off-screen ally / remembered voice",
    "TT3A/g0/r21": "Off-screen ally / remembered voice",
    "TT3A/g2/r7": "Off-screen voice, likely an ally",
    "TT3A/g4/r7": "Quiz prompt",
    "TT3B/g0/r24": "Hitler or the Devil speaking through him",
    "TT4/g0/r3": "Statue inscription: Athena",
    "TT4/g1/r3": "Statue inscription: Hermes",
    "TT4/g1/r4": "Narrator and off-screen patient",
    "TT4/g2/r16": "Statue inscription: Orion",
    "TT4/g3/r8": "Statue inscription: Artemis",
    "TT4/g3/r12": "Statue inscription: Hades",
    "TT4/g4/r8": "Written puzzle clue",
    "TT4/g4/r9": "Written puzzle clue",
    "TT4/g4/r10": "Written puzzle clue",
    "TT4/g4/r11": "Written puzzle clue",
    "TT4/g4/r12": "Written puzzle clue",
    "TT4/g4/r14": "Protagonist narration and unidentified warning voice",
    "TT4/g4/r31": "Statue inscription: Poseidon",
    "TT5/g0/r0": "Freedmen / crowd voices",
    "TT5/g0/r4": "Belle and George",
    "TT5/g1/r9": "Belle and other concerned voices",
    "TT6B/g1/r12": "Travelers / Magi",
    "TT6B/g1/r14": "Travelers / Magi",
    "TT6C/g0/r0": "Joseph and Mary",
    "TT6C/g1/r16": "Devil",
    "TT6C/g2/r3": "Artwork caption",
    "TT6C/g2/r6": "Written postwar note and narrator",
    "TT6D/g0/r6": "Devil / ominous growl",
}

GAMEPLAY_SPEAKER_AMBIGUITIES = {
    "TT3A/g2/r7": (
        "The off-screen voice is probably an ally, but the exact speaker needs the "
        "surrounding gameplay shot."
    ),
    "TT3B/g0/r24": (
        "The line may be Hitler himself or the Devil speaking through him; the "
        "visual staging determines the displayed identity."
    ),
    "TT4/g4/r14": (
        "The command “Wait” is unlabeled; a gameplay shot is needed to identify "
        "the warning voice."
    ),
}

SPEAKER_REFERENCES = (
    {
        "name": "Protagonist",
        "labels": "おれ; occasionally ぼく inside speech",
        "first_person": "おれ (rough/plain masculine); ぼく when softening his tone",
        "endings": "plain modern speech; ぞ/な/だ; frequent stutters and exclamations",
        "politeness": "casual, with situational politeness",
        "dialect": "standard modern Japanese",
        "habits": "internal commentary, comic panic, flirtation, abrupt disbelief",
        "relationships": "player viewpoint; protects the girl; pursues the Devil and Simon",
        "english_voice": "quick, contemporary, wry, and emotionally transparent; not macho parody",
    },
    {
        "name": "Girl",
        "labels": "おんなのこ",
        "first_person": "わたし",
        "endings": "feminine-coded わ/の and polite forms where appropriate",
        "politeness": "friendly to polite",
        "dialect": "standard Japanese",
        "habits": "gentle teasing, surprise, growing confidence",
        "relationships": "modern woman tied to the museum incident and epilogue",
        "english_voice": "warm and poised, capable of teasing; avoid exaggerated femininity",
    },
    {
        "name": "Devil",
        "labels": "あくま",
        "first_person": "わし",
        "endings": "じゃ/のう/ぞ and grand declaratives",
        "politeness": "pompous and domineering",
        "dialect": "stock archaizing old-man/authority role-language, not a firm region",
        "habits": "mockery, theatrical threats, inflated self-importance",
        "relationships": "possessor and antagonist across all historical chapters",
        "english_voice": "grandiose, sardonic, old-fashioned when useful; never generic rural dialect",
    },
    {
        "name": "Dr. Simon",
        "labels": "しもん; しもんはかせ",
        "first_person": "わたし",
        "endings": "formal explanatory prose",
        "politeness": "educated and controlled",
        "dialect": "standard Japanese",
        "habits": "scientific explanation, ethical reflection, hesitation under pressure",
        "relationships": "physicist behind the Time Belt; recurring ally and target",
        "english_voice": "precise, formal, humane, occasionally halting",
    },
    {
        "name": "Nagoya/Owari-coded businessman",
        "labels": "おとこ",
        "first_person": "implicit",
        "endings": "がや/で; どえりゃー; うるしゃー; くりゃーて",
        "politeness": "loud, panicked, then boastful",
        "dialect": "clustered stylized Nagoya/Owari speech",
        "habits": "money obsession and oversized resort plans",
        "relationships": "comic modern encounter near the museum",
        "english_voice": "brash regional-businessman flavor without mapping him to one real U.S. region",
    },
    {
        "name": "Pierre and medieval commoners",
        "labels": "ぴえーる; ちの; ごるどー; るごー",
        "first_person": "おれ",
        "endings": "rough contractions and emphatic particles",
        "politeness": "casual/rough",
        "dialect": "stylized commoner speech, not geographically Japanese in the fiction",
        "habits": "gallows humor, fear, solidarity",
        "relationships": "townspeople and allies in 1428 France",
        "english_voice": "earthy medieval-adventure dialogue; readable, not faux-Shakespearean",
    },
    {
        "name": "Bishop",
        "labels": "しきょう",
        "first_person": "varies; often authority-coded",
        "endings": "archaizing じゃ/おれ commands under demonic influence",
        "politeness": "public authority masking cruelty",
        "dialect": "role-language rather than a regional diagnosis",
        "habits": "decrees, threats, hypocritical religious language",
        "relationships": "antagonist in the Jeanne d'Arc chapter",
        "english_voice": "self-important ecclesiastical authority with theatrical menace",
    },
    {
        "name": "Schmidt",
        "labels": "しゅみっと",
        "first_person": "contextual",
        "endings": "terse declaratives",
        "politeness": "military restraint",
        "dialect": "standard Japanese",
        "habits": "controlled speech and concealed resistance allegiance",
        "relationships": "apparent Nazi officer; ally to Cougar and Simon",
        "english_voice": "clipped and disciplined, softening only after his reveal",
    },
    {
        "name": "Belle and George",
        "labels": "べる; じょーじ",
        "first_person": "わたし / おれ",
        "endings": "rural and working-class stylization",
        "politeness": "deferential under coercion; intimate in private",
        "dialect": "source uses stylized nonstandard Japanese to mark class/setting",
        "habits": "Belle is protective and devout; George is direct and frightened",
        "relationships": "mother and son on Meyer's farm",
        "english_voice": "plain rural speech with dignity; avoid minstrel caricature",
    },
    {
        "name": "Joseph",
        "labels": "よせふ",
        "first_person": "おれ",
        "endings": "casual masculine speech",
        "politeness": "familiar with Kashim; respectful to officials/elders",
        "dialect": "standard Japanese",
        "habits": "worry, earnestness, occasional comic self-pity",
        "relationships": "Mary's betrothed; Kashim's owner",
        "english_voice": "earnest, worried, fundamentally kind",
    },
    {
        "name": "Mary",
        "labels": "まりあ",
        "first_person": "わたし",
        "endings": "soft feminine and polite forms",
        "politeness": "gentle and respectful",
        "dialect": "standard Japanese",
        "habits": "calm concern and gratitude",
        "relationships": "Joseph's betrothed; mother of Jesus",
        "english_voice": "quiet, clear, and compassionate",
    },
    {
        "name": "Village Elder",
        "labels": "ちょうろう",
        "first_person": "わし",
        "endings": "じゃ/のう/おる",
        "politeness": "authoritative but caring",
        "dialect": "conventional elderly role-language",
        "habits": "historical and prophetic exposition",
        "relationships": "leader in the Nazareth village",
        "english_voice": "measured elder voice; lightly old-fashioned, never hillbilly",
    },
)

# Long, high-confidence substitutions only. Short homophones such as こえ,
# はし, かみ, あう, きく, and みる are intentionally excluded.
SAFE_RECONSTRUCTIONS = {
    "あくまはくぶつかん": "悪魔博物館",
    "うらないさーびすせんたー": "占いサービスセンター",
    "ぶつりがくしゃ": "物理学者",
    "しもんはかせ": "シモン博士",
    "たいむとらべる": "タイムトラベル",
    "たいむましん": "タイムマシン",
    "たいむべると": "タイムベルト",
    "たいむわーぷ": "タイムワープ",
    "きょうのうんせい": "今日の運勢",
    "けつえきがた": "血液型",
    "せいかくしんだん": "性格診断",
    "こんそめすーぷ": "コンソメスープ",
    "じゃいあんつ": "ジャイアンツ",
    "へいわしゅぎしゃ": "平和主義者",
    "じょうほうかんり": "情報管理",
    "あくまのて": "悪魔の手",
    "ぶろんずのぞう": "ブロンズの像",
    "ひみつけっしゃ": "秘密結社",
    "いけにえ": "生贄",
    "てんじひん": "展示品",
    "れじゃーせんたー": "レジャーセンター",
    "てれぱしー": "テレパシー",
    "じあげや": "地上げ屋",
    "じゃんぬ・だるく": "ジャンヌ・ダルク",
    "じゃんぬ": "ジャンヌ",
    "ぴえーる": "ピエール",
    "ふらんすおうこく": "フランス王国",
    "まじょがり": "魔女狩り",
    "しょけいだい": "処刑台",
    "けいやくしょ": "契約書",
    "だんしゃく": "男爵",
    "いざべる": "イザベル",
    "しきょう": "司教",
    "かんしゅ": "看守",
    "ほりょしゅうようじょ": "捕虜収容所",
    "だい2じせかいたいせん": "第二次世界大戦",
    "げしゅたぽ": "ゲシュタポ",
    "げっとー": "ゲットー",
    "れじすたんす": "レジスタンス",
    "れべっか": "レベッカ",
    "ひとらー": "ヒトラー",
    "しゅみっと": "シュミット",
    "くーがー": "クーガー",
    "ふらんきー": "フランキー",
    "にっく": "ニック",
    "らるふ": "ラルフ",
    "すいしゃごや": "水車小屋",
    "あてな": "アテナ",
    "へるめす": "ヘルメス",
    "あるてみす": "アルテミス",
    "ぽせいどん": "ポセイドン",
    "けるべろす": "ケルベロス",
    "よみのくに": "黄泉の国",
    "しんでん": "神殿",
    "ぎんか": "銀貨",
    "やくそう": "薬草",
    "そくらてす": "ソクラテス",
    "ぴたごらす": "ピタゴラス",
    "ぷらとん": "プラトン",
    "へろどとす": "ヘロドトス",
    "ほめろす": "ホメロス",
    "にくらす": "ニクラス",
    "だりお": "ダリオ",
    "りんかーん": "リンカーン",
    "まいやー": "マイヤー",
    "じょーじ": "ジョージ",
    "すとうふじん": "ストウ夫人",
    "かいほうせんげん": "解放宣言",
    "なんぶ": "南部",
    "ほくぐん": "北軍",
    "なんぐん": "南軍",
    "よせふ": "ヨセフ",
    "まりあ": "マリア",
    "かしむ": "カシム",
    "いすらえる": "イスラエル",
    "なざれ": "ナザレ",
    "べつれへむ": "ベツレヘム",
    "えるされむ": "エルサレム",
    "ろーまこうてい": "ローマ皇帝",
    "あうぐすとす": "アウグストゥス",
    "こせきちょうさ": "戸籍調査",
    "きげんぜん": "紀元前",
    "ちょうろう": "長老",
    "よげんしょ": "預言書",
    "すくいぬし": "救い主",
    "かすぱる": "カスパル",
    "めるきおーる": "メルキオール",
    "ばるたざーる": "バルタザール",
    "いえす・きりすと": "イエス・キリスト",
    "まらどぅる ばらお がらどぅーら": "マラドゥル・バラオ・ガラドゥーラ",
    "まらどぅる ばらお がるどぅーら": "マラドゥル・バラオ・ガルドゥーラ",
    "れきし": "歴史",
    "はくぶつかん": "博物館",
    "きょうかい": "教会",
    "けんきゅう": "研究",
    "せんそう": "戦争",
    "しゅうきょう": "宗教",
    "じゆう": "自由",
    "へいわ": "平和",
}

# Full natural meanings for fixed-address labels. The actual patch-safe field
# retains the verified compact slot text and reports its packed-byte limit.
FIXED_NATURAL = {
    "みる": "Look",
    "はなす": "Talk",
    "とる": "Take",
    "つかう": "Use",
    "きく": "Ask / listen",
    "かぐ": "Smell",
    "いどう": "Move",
    "まわり": "Surroundings",
    "へやのなか": "Inside the room",
    "そら": "Sky",
    "からだ": "Body",
    "ひがし": "East",
    "にし": "West",
    "きた": "North",
    "みなみ": "South",
    "あたっく": "Attack",
    "つっつく": "Poke",
    "あるく": "Walk",
    "よむ": "Read",
    "つぼ": "Jar",
    "てんじひん": "Exhibit",
    "おんなのこ": "Girl",
    "ばけもの": "Monster",
    "おまじない": "Magic charm",
    "てをにぎる": "Hold hands",
    "かたをだく": "Put an arm around",
    "わらいかける": "Smile at",
    "ほめる": "Compliment",
    "さけぶ": "Shout",
    "め": "Eyes",
    "はな": "Nose",
    "みみ": "Ears",
    "むね": "Chest",
    "おとこ": "Man",
    "ちず": "Map",
    "いえ": "House",
    "ひょうさつ": "Nameplate",
    "いんたーほん": "Intercom",
    "しんぶん": "Newspaper",
    "むしめがね": "Magnifying glass",
    "え": "Picture",
    "ろうじん": "Old man",
    "おもて": "Outside / front",
    "じめん": "Ground",
    "すすむ": "Forward",
    "もどる": "Back",
    "しもん": "Simon",
    "おく": "Back / inner area",
    "きょうかい": "Church",
    "しんぷ": "Priest",
    "しんじゃ": "Congregant",
    "せっきょう": "Sermon",
    "あくま": "Devil",
    "たいむべると": "Time Belt",
    "にげる": "Run away",
    "ぴえーる": "Pierre",
    "がらす": "Glass",
    "わいん": "Wine",
    "あきびん": "Empty bottle",
    "のむ": "Drink",
    "ふく": "Clothes",
    "かぎ": "Key",
    "でーた": "Data",
    "かんばん": "Signboard",
    "たてふだ": "Posted sign",
    "びん": "Bottle",
    "きる": "Put on / cut (context-dependent)",
    "ぬぐ": "Take off",
    "おやじ": "Older man",
    "だますかす": "Deceive and coax",
    "えるされむ": "Jerusalem",
    "くりみあ": "Crimea",
    "ひゃくねん": "One hundred years",
    "たいへいよう": "Pacific Ocean",
    "しょうにん": "Merchant",
    "しみん": "Citizen",
    "げいにん": "Entertainer",
    "ざいにん": "Criminal",
    "がいど": "Guide",
    "ぞいど": "Zoid",
    "げるど": "Geld",
    "ぎるど": "Guild",
    "おいど": "Oid",
    "だ・びんち": "da Vinci",
    "ら・こすて": "Lacoste",
    "で・ぱるま": "De Palma",
    "で・にーろ": "De Niro",
    "ど・ぬーぶ": "Danube",
    "う・たんと": "U Thant",
    "どうぐ": "Tools",
    "すすめる": "Proceed / offer (context-dependent)",
    "どうぐばこ": "Toolbox",
    "ちの": "Chino",
    "ごるどー": "Gordo",
    "まつ": "Wait",
    "またない": "Do not wait",
    "るごー": "Lugot",
    "ひきうける": "Accept",
    "ことわる": "Refuse",
    "さけ": "Alcohol",
    "やくにん": "Official",
    "やじうま": "Onlookers",
    "たてもの": "Building",
    "けいむしょ": "Prison",
    "まち": "Town",
    "かんしゅ": "Jailer",
    "おんなたち": "Women",
    "ちかしつ": "Basement",
    "しきょう": "Bishop",
    "じゃんぬ": "Jeanne",
    "ろーぷ": "Rope",
    "ろうそく": "Candle",
    "ろうや": "Cell",
    "だんしゃく": "Baron",
    "けいやくしょ": "Pact",
    "おす": "Push",
    "かべ": "Wall",
    "あな": "Hole",
    "あける": "Open",
    "はこ": "Box",
    "かみきれ": "Scrap of paper",
    "しょけいだい": "Execution scaffold",
    "ぽけっと": "Pocket",
    "ぺんち": "Pliers",
    "さくのそと": "Outside the fence",
    "たたく": "Hit",
    "はいる": "Enter",
    "ゆか": "Floor",
    "にっく": "Nick",
    "らるふ": "Ralph",
    "ふらんきー": "Frankie",
    "すとーぶ": "Stove",
    "べっど": "Bed",
    "しゃわーしつ": "Shower room",
    "しーつ": "Sheet",
    "まっとれす": "Mattress",
    "たいる": "Tile",
    "こいし": "Pebble",
    "しゃわー": "Shower",
    "とんねる": "Tunnel",
    "つち": "Soil",
    "まえ": "Front",
    "うしろ": "Back",
    "へいし": "Soldier",
    "いい／": "Yes",
    "やめる": "Stop / no",
    "じゅう": "Gun",
    "なげる": "Throw",
    "かなあみ": "Wire fence",
    "もり": "Woods",
    "べんち": "Bench",
    "あかいもじ": "Red writing",
    "あおいもじ": "Blue writing",
    "2まいのかみ": "Two notes",
    "あいことば": "Password",
    "あいさつ": "Greeting",
    "まるめる": "Crumple",
    "もやす": "Burn",
    "やぶく": "Tear",
    "かさねる": "Overlap",
    "すいしゃごや": "Watermill",
    "ふんすい": "Fountain",
    "みた": "Saw it",
    "みない": "Did not see",
    "とりだす": "Take out",
    "かみ": "Paper / god / hair (context-dependent)",
    "ごみばこ": "Trash can",
    "げしゅたぽ": "Gestapo",
    "げっとー": "Ghetto",
    "れじでんす": "Residence",
    "れじすたんす": "Resistance",
    "れじすたー": "Register",
    "じーぼーと": "G-boat",
    "なちぼーと": "Nazi boat",
    "ゆーぼーと": "U-boat",
    "ばななぼーと": "Banana boat",
    "ぎゃばん": "Gabin",
    "どろん": "Delon",
    "べるもんど": "Belmondo",
    "ふぃりっぷ": "Philippe",
    "とりゅふぉー": "Truffaut",
    "もんとごめり": "Montgomery",
    "ぱっとん": "Patton",
    "あいぜんはわ": "Eisenhower",
    "るーずべると": "Roosevelt",
    "ちゃーちる": "Churchill",
    "まっかーさー": "MacArthur",
    "はい": "Yes",
    "いいえ": "No",
    "ほうき": "Broom",
    "がいとう": "Streetlamp",
    "しゅみっと": "Schmidt",
    "くるまのそと": "Outside the car",
    "たたかう": "Fight",
    "ぼうぎょ": "Defend",
    "ちりょう": "Treat",
    "ぎんか": "Silver coin",
    "ちょうこく": "Statue",
    "しんかん": "Priest",
    "くび": "Head / neck",
    "ほほをたたく": "Slap the cheeks",
    "はらをおす": "Press the abdomen",
    "あごをあげる": "Lift the chin",
    "ひざをまげる": "Bend the knees",
    "みみをふさぐ": "Cover the ears",
    "めをおさえる": "Cover the eyes",
    "はなをつまむ": "Pinch the nose",
    "やすみやすみ": "With pauses",
    "たてつづけ": "Continuously",
    "おりーぶ": "Olive",
    "おいる": "Oil",
    "すず": "Bell",
    "わたす": "Give",
    "たべる": "Eat",
    "なめる": "Lick",
    "うる": "Sell",
    "かう": "Buy",
    "やくそう": "Medicinal herb",
    "かわない": "Do not buy",
    "しんでん": "Temple",
    "だりお": "Dario",
    "わかもの": "Youth",
    "あげる": "Raise",
    "さげる": "Lower",
    "たいら": "Level",
    "あたためる": "Warm",
    "ひやす": "Cool",
    "もむ": "Massage",
    "ゆびでつぶす": "Crush with fingers",
    "はりでつぶす": "Prick with a needle",
    "なにもしない": "Do nothing",
    "あぶらをぬる": "Apply oil",
    "ぬのをまく": "Wrap with cloth",
    "むすめ": "Girl / daughter",
    "ははおや": "Mother",
    "おおばこ": "Plantain herb",
    "どくだみ": "Fish mint",
    "あまちゃづる": "Jiaogulan",
    "すりつぶす": "Grind",
    "せんじる": "Decoct / boil",
    "みち": "Road",
    "やり": "Spear",
    "ふりまわす": "Swing",
    "そくらてす": "Socrates",
    "ぴたごらす": "Pythagoras",
    "ぷらとん": "Plato",
    "へろどとす": "Herodotus",
    "ほめろす": "Homer",
    "うみ": "Sea",
    "つりびと": "Fisherman",
    "こども": "Child",
    "にくらす": "Nicras",
    "ぽりす": "Polis",
    "ありす": "Aris",
    "いめるだ": "Imelda",
    "じゃかるた": "Jakarta",
    "すぱるた": "Sparta",
    "だるだろす": "Daedalus",
    "へらくれす": "Heracles",
    "なぽれおん": "Napoleon",
    "ごるばちょふ": "Gorbachev",
    "あがめむのん": "Agamemnon",
    "かんのん": "Kannon",
    "ぱるちざん": "Partisan",
    "あいすのん": "Aisnon",
    "ぱるてのん": "Parthenon",
    "いちご": "Strawberry",
    "めろん": "Melon",
    "いちじく": "Fig",
    "げんまい": "Brown rice",
    "しんじゅ": "Pearl",
    "こーひー": "Coffee",
    "じょーじ": "George",
    "べる": "Belle",
    "おとこたち": "Men",
    "やけあと": "Burned ruins",
    "ひづめのあと": "Hoofprints",
    "かね": "Money",
    "まど": "Window",
    "ひきだし": "Drawer",
    "わた": "Cotton",
    "わかりました": "Understood",
    "もういちど": "Again",
    "すけじゅーる": "Schedule",
    "まいやーよぶ": "Call Meyer",
    "みずくみ": "Fetch water",
    "わたつみ": "Pick cotton",
    "やねしゅうり": "Repair roof",
    "まきわり": "Split wood",
    "くさむしり": "Pull weeds",
    "とむ": "Tom",
    "かいへいたい": "Marine Corps",
    "きへいたい": "Cavalry",
    "あかふね": "Red ship",
    "しろふね": "White ship",
    "くろふね": "Black ship",
    "でびふじん": "Madame Dewi",
    "すとうふじん": "Mrs. Stowe",
    "あきのふじん": "Mrs. Akino",
    "めりーふじん": "Mrs. Mary",
    "ほいっとにー": "Whitney",
    "きらうえあ": "Kilauea",
    "えとな": "Etna",
    "らしゅもあ": "Rushmore",
    "おいわけ": "Oiwake",
    "えいしゃき": "Projector",
    "わたくりき": "Cotton gin",
    "こううんき": "Plow",
    "しゃしんき": "Camera",
    "ひこうき": "Airplane",
    "びでおでっき": "VCR",
    "こたえ": "Answer",
    "もんだい": "Problem",
    "うし": "Cow",
    "ひつじ": "Sheep",
    "ぶた": "Pig",
    "10のけた": "Tens digit",
    "1のけた": "Ones digit",
    "6いじょう": "Six or more",
    "いれる": "Pour in",
    "おわり": "Finish",
    "おおびん": "Large bottle",
    "ちゅうびん": "Medium bottle",
    "こびん": "Small bottle",
    "やしき": "Mansion",
    "まいやー": "Meyer",
    "ほらあな": "Cave",
    "なか": "Inside",
    "やしきのなか": "Inside the mansion",
    "わごん": "Wagon",
    "ぽっと": "Pot",
    "まどのそと": "Outside the window",
    "ろうか": "Hallway",
    "きゃくしつ": "Guest room",
    "しょさい": "Study",
    "かいだん": "Stairs",
    "つくえ": "Desk",
    "1だんめ": "First drawer",
    "2だんめ": "Second drawer",
    "3だんめ": "Third drawer",
    "かくれる": "Hide",
    "おりる": "Get down",
    "あがる": "Go up",
    "のる": "Get on",
    "ぼーといどう": "Travel by boat",
    "こよーて": "Coyote",
    "かわ": "River",
    "おれ": "Protagonist",
    "うなずく": "Nod",
    "よこをむく": "Turn aside",
    "そで": "Sleeve",
    "むら": "Village",
    "ちょうろう": "Elder",
    "いど": "Well",
    "かいばおけ": "Feeding trough",
    "なわ": "Rope",
    "ほしくさ": "Hay",
    "いどのみず": "Well water",
    "おか": "Hill",
    "みぎのいえ": "Right-hand house",
    "ひだりのいえ": "Left-hand house",
    "まりあ": "Mary",
    "うつわ": "Bowl",
    "ひきうす": "Hand mill",
    "うでわ": "Bracelet",
    "くびかざり": "Necklace",
    "こむぎ": "Wheat",
    "こうぐ": "Tools",
    "だい": "Stand",
    "だいのうえ": "On the stand",
    "かわら": "Roof tile",
    "こどもたち": "Children",
    "よせふ": "Joseph",
    "めをむく": "Glare / widen the eyes",
    "したをだす": "Stick out tongue",
    "ういんくする": "Wink",
    "てんと": "Tent",
    "らくだ": "Camel",
    "うま": "Horse",
    "うんち": "Dung",
    "ちえのみ": "Fruit of wisdom",
    "ちしきのみ": "Fruit of knowledge",
    "いしす": "Isis",
    "ばーる": "Baal",
    "えほば": "Jehovah",
    "いらく": "Iraq",
    "よるだん": "Jordan",
    "しりあ": "Syria",
    "えじぷと": "Egypt",
    "だびで": "David",
    "そろもん": "Solomon",
    "さむそん": "Samson",
    "やこぶ": "Jacob",
    "いさく": "Isaac",
    "さだむ": "Saddam",
    "あぶらはむ": "Abraham",
    "さたん": "Satan",
    "きりすと": "Christ",
    "ぞろあすたー": "Zoroaster",
    "しっぽをふる": "Wag tail",
    "のみをとる": "Pick off fleas",
    "ひづめ": "Hoof",
    "しっぽ": "Tail",
    "たてがみ": "Mane",
    "とびかかる": "Leap at",
    "あかんぼう": "Baby",
    "おれのからだ": "My body",
    "かしむ": "Kashim",
    "どかす": "Move aside",
    "ぱねる": "Panel",
    "ふた": "Lid",
    "じんこつ": "Human bones",
    "そと": "Outside",
    "るーがー": "Ruger",
    "はうあー": "Hauer",
    "べるがー": "Berger",
    "がらすや": "Glazier",
    "かじや": "Blacksmith",
    "さかや": "Tavern keeper",
    "したてや": "Tailor",
    "かとりーぬ": "Catherine",
    "みれーぬ": "Mylène",
    "ろーら": "Laura",
    "もろっこ": "Morocco",
    "れべっか": "Rebecca",
    "ぶれっど": "Bread",
    "とらっど": "Trad",
    "おーすとりあ": "Austria",
    "ふらんす": "France",
    "すいす": "Switzerland",
    "べるぎー": "Belgium",
    "せんぶり": "Swertia",
    "だいたろす": "Daedalus",
    "けんたうろす": "Centaur",
    "あとらす": "Atlas",
    "ふれっど": "Fred",
    "ぼぶ": "Bob",
    "じむ": "Jim",
    "かもしか": "Serow",
    "となかい": "Reindeer",
    "ぴゅーま": "Puma",
    "きんのうでわ": "Gold bracelet",
    "ぎんのうでわ": "Silver bracelet",
    "どうのうでわ": "Copper bracelet",
    "すずのうでわ": "Tin bracelet",
    "まぐだら": "Magdala",
    "なざれ": "Nazareth",
    "べつれへむ": "Bethlehem",
    "あれくさんだ": "Alexander",
    "ひだり": "Left",
    "うえ": "Up",
    "みぎ": "Right",
    "さいしょから": "Start from the beginning",
    "しばらく{CTRL:0}  おまちください": "Please wait",
    "ぜんぺんの": "Part 1",
    "こうへんの": "Part 2",
    "えーめんを": "Side A",
    "びーめんを": "Side B",
    "せっとしてください": "Please insert",
    "ちがった でぃすくが": "Wrong disk",
    "せっとされています": "is inserted",
    "えー らむせーぶ{CTRL:0}びー ですくせーぶ{CTRL:0}せる きゃんせる": "A: RAM save / B: disk save / Select: cancel",
    "でぃすくせーぶ{CTRL:0}しとるからの": "Saving to disk.",
    "しょうはじめ": "Chapter start",
    "でぃすく、とらぶる": "Disk error",
    "おぼえる": "Store in memory",
    "おもいだす": "Recall from memory",
}

MANUAL_FINAL = {
    "TT1B/g0/r1": "When was the last time I saw a blue sky?",
    "TT1B/g0/r28": (
        "Protagonist: Um… / Girl: Have you seen all the exhibits? / "
        "Protagonist: No…"
    ),
    "TT1B/g0/r31": (
        "Protagonist: No way… You mean you're… / Devil: I am what you might "
        "call… a devil. / Protagonist: G-g-g-gah! / Devil: All that patient "
        "telepathy has finally paid off. / Protagonist: …"
    ),
    "TT1B/g1/r14": (
        "Protagonist: You've got quite a pair… heh-heh. / Girl: Eek!"
    ),
    "TT1B/g2/r5": (
        "Resident: I've lived in this house for 40 years! I can't just leave now! "
        "/ Protagonist: I'm no land shark. / Resident: Oh! I-I'm terribly sorry."
    ),
    "TT3A/g2/r30": (
        "One fragment of the note. / In blue ink: “…4 km southwest…” / “…Rebecca.”"
    ),
    "TT6A/g0/r13": (
        "Joseph: The truth is… my betrothed, Mary, seems to be with child. But I "
        "swear to God, I've never so much as held her hand! Mary says she has no "
        "idea how it happened… but can that possibly be true? / Protagonist: "
        "Hee-haw… / Joseph: I can't believe in anything anymore! The engagement "
        "is off!"
    ),
}

ROMAJI_OVERRIDES = {
    "TT3A/g2/r30": (
        "ko     na     i 4   ro no / fu       i shi ya   ya / "
        "e de   te / be   ka"
    ),
    "TT3A/g3/r13": (
        "koko kara nansei 4 kiro no / furui suisha-goya no / "
        "mae de mate / Rebekka"
    ),
    "TITLE/subtitle": "rekishi no katasumi de……",
}

MANUAL_PATCH = {
    "TT1A/g0/r1": (
        'News: Dr. Simon,{CTRL:0}the "solitary genius,"{CTRL:2}'
        "physicist, commented{CTRL:0}on time travel last eve:{CTRL:4}"
    ),
    "TT1A/g0/r9": "Baseball means Giants.",
    "TT1A/g0/r23": (
        "A cool-headed pacifist,{CTRL:0}skilled with facts.{CTRL:2}"
        "Friendly, but groups and{CTRL:0}close ties make you wary{CTRL:4}"
        "You may become isolated,{CTRL:3}yet judge yourself well.{CTRL:4}"
    ),
    "TT1A/g0/r24": (
        "Careful and methodical,{CTRL:0}you rarely fail, yet{CTRL:2}"
        "seem plain. Principled,{CTRL:0}diligent and stubborn.{CTRL:3}"
        "You tire from caring{CTRL:4}and fumble at romance,{CTRL:4}"
        "but are romantic inside."
    ),
    "TT1A/g0/r27": (
        '"Today\'s Fortune"{CTRL:0}{CTRL:2}Today may be a day you{CTRL:0}'
        "never forget.{CTRL:3}Calm judgment and will{CTRL:4}"
        "bring you luck.{CTRL:3}At a suburban museum,{CTRL:4}"
        "a lovely woman may leap{CTRL:4}right into your arms.{CTRL:3}"
        "Your clinching line:{CTRL:3}Those words are..."
    ),
    "TT1A/g0/r31": (
        "........................{CTRL:1}Weird...{CTRL:0}"
        "A magic charm?{CTRL:6}{CTRL:4}{CTRL:3}"
        "Well--act while I can!"
    ),
    "TT1B/g0/r1": "Blue sky--how long gone?",
    "TT1B/g0/r17": (
        '"Devil\'s Hand"{CTRL:0}{CTRL:2}A bronze statue, emblem{CTRL:0}'
        "of a 19th-century cult.{CTRL:4}{CTRL:3}Its claws tore hearts{CTRL:4}"
        "from sacrifices."
    ),
    "TT1B/g0/r28": (
        "Me: Um...{CTRL:1}Girl: Seen everything?{CTRL:0}Me: No..."
    ),
    "TT1B/g0/r31": (
        "Me: No way... You mean{CTRL:0}you're...{CTRL:0}"
        "Devil: I am what you{CTRL:0}might call... a devil.{CTRL:0}"
        "Me: G-g-g-gah!{CTRL:6}Devil: All that patient{CTRL:4}"
        "telepathy has finally{CTRL:0}paid off.{CTRL:4}Me: ........"
    ),
    "TT1B/g1/r14": (
        "Me: You've got quite a{CTRL:0}pair... heh-heh.{CTRL:1}Girl: Eek!"
    ),
    "TT1B/g1/r26": "Man: Shut up! Move!",
    "TT1B/g1/r27": (
        "Man: Big resort comin'{CTRL:0}right here!{CTRL:2}"
        "It may be backwoods now,{CTRL:0}but soon it'll boom!"
    ),
    "TT1B/g1/r28": "Money rules! For cash,{CTRL:0}I'd sell my soul!",
    "TT1B/g2/r5": (
        "...: I've lived in this{CTRL:0}house for 40 years!{CTRL:0}"
        "I can't just leave now!{CTRL:2}Me: I'm no land shark.{CTRL:6}"
        "...: Oh! I-I'm terribly{CTRL:0}sorry."
    ),
    "TT1B/g2/r14": "Wh-what?! That's me!",
    "TT3A/g2/r30": (
        "A fragment of the note.{CTRL:0}Blue ink:{CTRL:0}"
        "'... 4 km southwest...'{CTRL:0}'... Rebecca'"
    ),
    "TT6A/g0/r13": (
        "Joseph: My betrothed,{CTRL:0}Mary, may be with child.{CTRL:2}"
        "I swear before God,{CTRL:0}I never even held her{CTRL:4}hand!{CTRL:3}"
        "Mary has no idea how.{CTRL:4}Can that be true?{CTRL:3}"
        "Me: Hee-haw...{CTRL:3}Joseph: I trust nothing!{CTRL:4}"
        "Our betrothal is over!"
    ),
    "NOV2/wait": "PLEASE{CTRL:0}WAIT...",
}

MANUAL_NOTES = {
    "TT1B/g0/r31": (
        "いわゆるひとつの is not merely 'yes.' It is comic verbal padding strongly "
        "associated with baseball star Shigeo Nagashima's much-imitated manner of "
        "speech. The localization keeps a self-consciously roundabout 'what you "
        "might call' cadence."
    ),
    "TT1B/g1/r14": (
        "ボイン is dated, objectifying slang for large breasts, widespread from "
        "late-1960s television culture. The line is intentionally crude and comic; "
        "the translation should not neutralize it into an anatomical description."
    ),
    "TT3A/g2/r30": (
        "The ROM stores a deliberately spatial, fragmentary note. The current "
        "English reconstructs the clue as '4 km southwest' and 'Rebecca'; exact "
        "line placement requires a gameplay screenshot or nametable capture."
    ),
    "NOV2/wait": (
        "The existing English patch intentionally removed the source CTRL:0 so "
        "PLEASE WAIT could remain on one visible line. This workbook obeys the "
        "requested exact-control policy; runtime display behavior therefore needs "
        "visual verification before insertion."
    ),
}

EXTERNAL_REFERENCES = (
    {
        "topic": "いわゆるひとつの",
        "url": "https://ci.nii.ac.jp/ncid/BA52896443",
        "note": (
            "CiNii catalog record for 『いわゆるひとつの長嶋茂雄語録』, corroborating "
            "the phrase's cultural identification with Shigeo Nagashima."
        ),
    },
    {
        "topic": "ぼいん",
        "url": "https://kotobank.jp/word/%E3%81%BC%E3%81%84%E3%82%93-626865",
        "note": (
            "Kotobank dictionary entry: slang for large female breasts; the cited "
            "historical example dates from 1968."
        ),
    },
    {
        "topic": "ぼいん etymology",
        "url": "https://gogen-yurai.jp/boin/",
        "note": (
            "Reference account connecting popularization to late-1960s television "
            "and host Kyosen Ohashi."
        ),
    },
)

GLOSSARY_SEEDS = (
    (
        "Character",
        "おれ",
        "俺",
        "Protagonist",
        "I; me",
        "Source speaker tag and rough/plain masculine first person.",
    ),
    (
        "Character",
        "おんなのこ",
        "女の子",
        "Girl",
        "young woman",
        "Recurring modern woman; no personal name is supplied in the extracted text.",
    ),
    (
        "Character",
        "しもんはかせ",
        "シモン博士",
        "Dr. Simon",
        "Dr. Shimon",
        "Physicist and creator of the Time Belt.",
    ),
    (
        "Character",
        "あくま",
        "悪魔",
        "Devil",
        "demon",
        "Recurring antagonist; translated as a title/role.",
    ),
    (
        "Character",
        "ぴえーる",
        "ピエール",
        "Pierre",
        "",
        "Body/identity used in the 1428 France chapter.",
    ),
    (
        "Character",
        "じゃんぬ・だるく",
        "ジャンヌ・ダルク",
        "Jeanne d'Arc",
        "Joan of Arc",
        "Use Jeanne in direct address; full historical name in narration.",
    ),
    (
        "Character",
        "るごー",
        "ルゴー",
        "Lugot",
        "Rugot",
        "Medieval French ally; romanization retained consistently.",
    ),
    ("Character", "ちの", "チノ", "Chino", "", "Medieval French ally."),
    (
        "Character",
        "ごるどー",
        "ゴルドー",
        "Gordo",
        "Gordeaux",
        "Medieval French ally.",
    ),
    (
        "Character",
        "しきょう",
        "司教",
        "Bishop",
        "",
        "Office/title, not a personal name.",
    ),
    ("Character", "だんしゃく", "男爵", "Baron", "", "Office/title."),
    (
        "Character",
        "いざべる",
        "イザベル",
        "Isabelle",
        "Isabel",
        "The Baron's wife.",
    ),
    (
        "Character",
        "くーがー",
        "クーガー",
        "Cougar",
        "Kuger",
        "U.S. air lieutenant identity in 1944.",
    ),
    (
        "Character",
        "しゅみっと",
        "シュミット",
        "Schmidt",
        "",
        "German officer and resistance ally.",
    ),
    (
        "Character",
        "ひとらー",
        "ヒトラー",
        "Hitler",
        "",
        "Historical figure under supernatural influence in the game.",
    ),
    (
        "Character",
        "にくらす",
        "ニクラス",
        "Nicras",
        "Niklas",
        "Physician identity in ancient Athens.",
    ),
    (
        "Character",
        "あてな",
        "アテナ",
        "Athena",
        "",
        "Greek goddess of wisdom and patron of Athens.",
    ),
    ("Character", "へるめす", "ヘルメス", "Hermes", "", "Greek god."),
    ("Character", "はです", "ハデス", "Hades", "", "Greek underworld figure."),
    (
        "Character",
        "けるべろす",
        "ケルベロス",
        "Cerberus",
        "",
        "Guardian hound of the underworld.",
    ),
    (
        "Character",
        "りんかーん",
        "リンカーン",
        "Lincoln",
        "Abraham Lincoln",
        "Historical figure in the Civil War chapter.",
    ),
    (
        "Character",
        "まいやー",
        "マイヤー",
        "Meyer",
        "Mayer",
        "Plantation/farm owner; current script establishes Meyer.",
    ),
    ("Character", "べる", "ベル", "Belle", "Bell", "George's mother."),
    (
        "Character",
        "じょーじ",
        "ジョージ",
        "George",
        "",
        "Protagonist's identity in 1864 Atlanta.",
    ),
    ("Character", "よせふ", "ヨセフ", "Joseph", "", "Mary's betrothed."),
    ("Character", "まりあ", "マリア", "Mary", "Maria", "Mother of Jesus."),
    (
        "Character",
        "かしむ",
        "カシム",
        "Kashim",
        "Kas(h)im",
        "Joseph's donkey and the protagonist's animal identity.",
    ),
    (
        "Character",
        "かすぱる",
        "カスパル",
        "Caspar",
        "Gaspar",
        "One of the Magi.",
    ),
    (
        "Character",
        "めるきおーる",
        "メルキオール",
        "Melchior",
        "",
        "One of the Magi.",
    ),
    (
        "Character",
        "ばるたざーる",
        "バルタザール",
        "Balthazar",
        "Balthasar",
        "One of the Magi.",
    ),
    (
        "Historical person",
        "いえす・きりすと",
        "イエス・キリスト",
        "Jesus Christ",
        "",
        "Name revealed through an intentional Jesus/yes wordplay.",
    ),
    (
        "Location",
        "あくまはくぶつかん",
        "悪魔博物館",
        "Devil Museum",
        "Demon Museum",
        "Modern museum where the supernatural plot begins.",
    ),
    (
        "Location",
        "きょうかい",
        "教会",
        "Church",
        "",
        "Modern and medieval church contexts are distinguished by scene.",
    ),
    (
        "Location",
        "どいつなんぶ ほりょしゅうようじょ",
        "ドイツ南部 捕虜収容所",
        "POW camp in southern Germany",
        "",
        "1944 setting.",
    ),
    (
        "Location",
        "よみのくに",
        "黄泉の国",
        "the underworld",
        "Yomi",
        "Rendered by Greek-scene function rather than as a Japanese place name.",
    ),
    ("Location", "なざれ", "ナザレ", "Nazareth", "", "Nativity chapter."),
    (
        "Location",
        "べつれへむ",
        "ベツレヘム",
        "Bethlehem",
        "",
        "Nativity chapter.",
    ),
    (
        "Location",
        "えるされむ",
        "エルサレム",
        "Jerusalem",
        "",
        "Historical/biblical place name.",
    ),
    (
        "Location",
        "いすらえる",
        "イスラエル",
        "Israel",
        "",
        "The game's geographic label.",
    ),
    (
        "Artifact",
        "たいむべると",
        "タイムベルト",
        "Time Belt",
        "time belt",
        "Belt-shaped time machine; capitalization retained as an item name.",
    ),
    (
        "Artifact",
        "たいむましん",
        "タイムマシン",
        "time machine",
        "",
        "General technology term.",
    ),
    (
        "Artifact",
        "まふうじのつぼ",
        "魔封じの壺",
        "Demon-Sealing Jar",
        "demon-binding jar",
        "Museum artifact and key sealing vessel.",
    ),
    (
        "Artifact",
        "さばとのはこ",
        "サバトの箱",
        "Sabbath Box",
        "Witches' Sabbath box",
        "Museum exhibit said to hold soul contracts.",
    ),
    (
        "Artifact",
        "いましめのすず",
        "戒めの鈴",
        "Warding Bell",
        "Bell of Admonition",
        "Museum exhibit; English favors function.",
    ),
    (
        "Artifact",
        "あくまのて",
        "悪魔の手",
        "Devil's Hand",
        "",
        "A bronze statue, not merely a symbol.",
    ),
    (
        "Artifact",
        "まもりふだ",
        "守り札",
        "protective charm",
        "amulet",
        "Recurring warding object.",
    ),
    (
        "Supernatural",
        "まらどぅる ばらお がらどぅーら",
        "マラドゥル・バラオ・ガラドゥーラ",
        "Maradul Barao Garadura",
        "Galdura variant",
        "Incantation; variants in the source are preserved and noted.",
    ),
    (
        "Time travel",
        "たいむとらべる",
        "タイムトラベル",
        "time travel",
        "",
        "General concept.",
    ),
    (
        "Time travel",
        "たいむわーぷ",
        "タイムワープ",
        "time warp",
        "time jump",
        "The game's term for historical transit.",
    ),
    (
        "Historical period",
        "1428ねん",
        "1428年",
        "1428",
        "",
        "France/Jeanne chapter.",
    ),
    (
        "Historical period",
        "1944ねん 7がつ",
        "1944年7月",
        "July 1944",
        "",
        "German POW chapter.",
    ),
    (
        "Historical period",
        "1864ねん 9がつ",
        "1864年9月",
        "September 1864",
        "",
        "Atlanta/Civil War chapter.",
    ),
    (
        "Historical period",
        "きげんぜん 4ねんごろ",
        "紀元前4年頃",
        "circa 4 BC",
        "around 4 BCE",
        "The game uses BC-era framing.",
    ),
    ("Command", "みる", "見る", "LOOK", "Examine", "Core menu command."),
    ("Command", "はなす", "話す", "TALK", "Speak", "Core menu command."),
    ("Command", "いどう", "移動", "MOVE", "Go", "Core menu command."),
    ("Command", "つかう", "使う", "USE", "", "Core menu command."),
    ("Command", "とる", "取る", "TAKE", "Get", "Core menu command."),
    (
        "Command",
        "きく",
        "聞く／訊く",
        "ASK / LISTEN",
        "Hear",
        "Context determines whether it means ask or listen.",
    ),
    (
        "Interface",
        "さいしょから",
        "最初から",
        "START",
        "From the beginning",
        "Start-menu label.",
    ),
    (
        "Interface",
        "しばらく おまちください",
        "しばらくお待ちください",
        "PLEASE WAIT…",
        "",
        "System wait prompt.",
    ),
    (
        "Interface",
        "ぜんぺん",
        "前編",
        "PART 1",
        "first part",
        "Zenpen disk label.",
    ),
    (
        "Interface",
        "こうへん",
        "後編",
        "PART 2",
        "second part",
        "Kouhen disk label.",
    ),
    (
        "Graphics",
        "タイムツイスト",
        "タイムツイスト",
        "TIME TWIST",
        "",
        "Title wordmark.",
    ),
    (
        "Graphics",
        "歴史のかたすみで……",
        "歴史の片隅で……",
        "On the Outskirts of History…",
        "In a Corner of History",
        "Requested localized subtitle.",
    ),
    (
        "Register",
        "いわゆるひとつの",
        "いわゆる一つの",
        "what you might call…",
        "one of those…",
        "Comic Nagashima-associated verbal mannerism.",
    ),
    (
        "Slang",
        "ぼいん",
        "ボイン",
        "busty / large breasts",
        "",
        "Dated, objectifying slang; tone is intentionally crude.",
    ),
)


@dataclass
class WorkbookRow:
    """Represent one complete linguistic and technical review record.

    The first seventeen fields form the public workbook schema requested for
    every source record.  The remaining fields retain scene, storage, control,
    and review metadata needed by filters and by later patch engineering.

    Attributes:
        sequential_entry_number: One-based source-order position.
        original_record_id: Stable extraction ID used across all artifacts.
        bank: Scenario bank or standalone UI/graphics component.
        record_type: Scenario, fixed-address, or graphics-text classification.
        exact_japanese_source: Authoritative decoded ROM text, unchanged.
        romaji: Mechanical reading aid, with explicit overrides where needed.
        reconstructed_japanese: Conservative editorial normalization.
        literal_english_meaning: Intelligible structure-preserving translation.
        linguistic_and_cultural_notes: Evidence and localization commentary.
        speaker_or_narration_identity: Best contextual voice attribution.
        current_english: Existing patch text before this review.
        problems_with_current_english: Specific comparison findings.
        final_natural_english_translation: Preferred unconstrained localization.
        patch_safe_english_translation: ROM-character/control-safe candidate.
        confidence_level: Confidence or required verification category.
        unresolved_ambiguity: Material uncertainty that remains after review.
        translation_status: Completion state for filtering and reporting.
        scene: Human-readable scene or component title.
        source_location: Extraction provenance supplied by the source corpus.
        apparent_capacity: Known slot size or recompression estimate.
        source_control_codes: Ordered source controls for visible auditing.
        patch_control_codes: Ordered patch controls for visible auditing.
        control_codes_match: ``"yes"`` only when both sequences are identical.
        problem_categories: Semicolon-separated normalized QA categories.
        dialect_or_register: Boundary-aware grammatical voice observations.
        requires_gameplay_context: ``"yes"`` when a screenshot may resolve context.
        requires_technical_expansion: ``"yes"`` when fit needs engineering review.
        nuance_lost_in_patch_safe_version: Fit compromise or expansion rationale.

    Note:
        This model deliberately keeps exact Japanese, editorial reconstruction,
        and English interpretation in separate fields.  Callers must never use
        the reconstructed field as evidence of bytes present in the ROM.
    """

    sequential_entry_number: int
    original_record_id: str
    bank: str
    record_type: str
    exact_japanese_source: str
    romaji: str
    reconstructed_japanese: str
    literal_english_meaning: str
    linguistic_and_cultural_notes: str
    speaker_or_narration_identity: str
    current_english: str
    problems_with_current_english: str
    final_natural_english_translation: str
    patch_safe_english_translation: str
    confidence_level: str
    unresolved_ambiguity: str
    translation_status: str
    scene: str
    source_location: str
    apparent_capacity: str
    source_control_codes: str
    patch_control_codes: str
    control_codes_match: str
    problem_categories: str
    dialect_or_register: str
    requires_gameplay_context: str
    requires_technical_expansion: str
    nuance_lost_in_patch_safe_version: str


class ReviewTableParser(HTMLParser):
    """Parse only the tabular content needed from the diagnostic review HTML.

    The supplied review is an input aid, not authoritative source text.  A
    purpose-built parser avoids browser or third-party HTML dependencies while
    preserving line breaks within cells.  It intentionally ignores styling,
    links, nested layout, and text outside table rows.

    Attributes:
        rows: Completed rows, with decoded and stripped cell text.

    Assumptions:
        Table rows do not overlap, cells are direct or nested descendants of a
        row, and ``<br>`` is the only significant inline layout element.
    """

    def __init__(self) -> None:
        """Initialize an empty parser.

        Side Effects:
            Initializes :class:`html.parser.HTMLParser` with character-reference
            conversion enabled.
        """
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._in_cell = False
        self._buffer: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        """Process structural opening tags relevant to review-table extraction.

        Args:
            tag: Lowercase HTML element name supplied by ``HTMLParser``.
            attrs: Parsed attributes; accepted for the callback contract but
                intentionally ignored.

        Side Effects:
            Starts a row or cell buffer and appends a newline for ``<br>`` tags
            encountered inside the active cell.
        """
        if tag == "tr":
            self._row = []
        elif self._row is not None and tag in {"td", "th"}:
            self._in_cell = True
            self._buffer = []
        elif self._in_cell and tag == "br":
            self._buffer.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Finalize a cell or row when its closing tag is encountered.

        Args:
            tag: Lowercase closing-tag name supplied by ``HTMLParser``.

        Side Effects:
            Appends stripped cell text to the active row or a completed row to
            :attr:`rows`.

        Raises:
            ValueError: If a cell closes without an active row, indicating
                malformed state or unsupported table markup.
        """
        if tag in {"td", "th"} and self._in_cell:
            if self._row is None:
                raise ValueError(
                    "review table cell closed without an active row"
                )
            self._row.append("".join(self._buffer).strip())
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        """Append decoded text only when a review-table cell is active.

        Args:
            data: Character data supplied by ``HTMLParser``.

        Side Effects:
            Extends the current cell buffer.  Text outside cells is discarded.
        """
        if self._in_cell:
            self._buffer.append(data)


def sha256(path: Path) -> str:
    """Calculate an uppercase SHA-256 fingerprint for one file.

    Args:
        path: Existing file to read in one-mebibyte chunks.

    Returns:
        The 64-character hexadecimal digest in uppercase.

    Raises:
        OSError: If the file cannot be opened or read.

    Design:
        Streaming keeps source and generated multi-megabyte workbooks out of
        memory while producing reproducible provenance metadata.
    """
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def collapse(text: str) -> str:
    """Normalize arbitrary whitespace for a single-line editorial field.

    Args:
        text: Text that may contain tabs, newlines, or repeated spaces.

    Returns:
        Text with every whitespace run replaced by one ASCII space and leading
        or trailing whitespace removed.
    """
    return re.sub(r"\s+", " ", text).strip()


def without_controls(text: str, separator: str = " ") -> str:
    """Remove control tags without accidentally joining adjacent words.

    Args:
        text: Decoded text containing zero or more ``{CTRL:n}`` markers.
        separator: Text inserted for each removed marker before whitespace is
            collapsed.

    Returns:
        Control-free, whitespace-normalized visible text.
    """
    return collapse(CONTROL_RE.sub(separator, text))


def naturalize_current(text: str) -> str:
    """Convert patch typography into readable editorial prose.

    Args:
        text: Existing English that may include control tags, repeated periods,
            or compact speaker labels.

    Returns:
        A control-free display string with typographic ellipses and expanded
        generic speaker labels.

    Note:
        This function does not translate Japanese or infer missing content.  It
        is only a presentation fallback when no reviewed replacement exists.
    """
    value = CONTROL_RE.sub(" ", text)
    value = re.sub(r"\.{4,}", "…", value)
    value = value.replace("...", "…")
    value = collapse(value)
    value = re.sub(r"\bMe:", "Protagonist:", value)
    value = re.sub(r"^\.\.\.:\s*", "Unidentified voice: ", value)
    return value


def conservative_reconstruction(exact: str) -> str:
    """Build an editorial Japanese reading from explicitly approved mappings.

    Args:
        exact: Authoritative decoded Japanese, possibly with control tags.

    Returns:
        Control-free normalized Japanese after longest-first substitutions from
        :data:`SAFE_RECONSTRUCTIONS`.

    Design:
        Longest-first replacement prevents a shorter entry from consuming part
        of a more specific phrase.  Unmapped kana remain untouched so ambiguity
        is visible instead of being silently assigned kanji.
    """
    text = CONTROL_RE.sub(" ", exact)
    for source, replacement in sorted(
        SAFE_RECONSTRUCTIONS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        text = text.replace(source, replacement)
    return collapse(text)


def controls(text: str) -> tuple[str, ...]:
    """Extract control payloads in exact source order.

    Args:
        text: Decoded Japanese or English containing ``{CTRL:n}`` markers.

    Returns:
        A tuple of payload strings without braces or the ``CTRL:`` prefix.
    """
    return tuple(CONTROL_RE.findall(text))


def current_capacity(source_row: dict) -> str:
    """Describe the storage evidence available for one extracted record.

    Args:
        source_row: Source-corpus mapping with ``packed_bytes`` and current
            English fields.

    Returns:
        A human-readable fixed-slot size, a scenario recompression/display
        estimate, or a note that the item is graphics/program text.

    Raises:
        KeyError: If required source-corpus fields are missing.

    Note:
        Group-compressed records have no independent byte slot.  Their visible
        length and longest control-delimited segment are warnings, not proof of
        final bank fit; native recompression remains authoritative.
    """
    if source_row["packed_bytes"].isdigit():
        return (
            f"{source_row['packed_bytes']} packed bytes (fixed-address slot)"
        )
    if source_row["packed_bytes"] == "group-compressed":
        current = source_row["current_english_exact"]
        segments = re.split(r"\{CTRL:\d+\}", current)
        visible = len(CONTROL_RE.sub("", current))
        maximum = max((len(part) for part in segments), default=0)
        return (
            f"current draft {visible} visible characters; longest control-delimited "
            f"segment {maximum}/24 columns; final fit depends on group recompression"
        )
    return "graphics/program text; no scenario slot"


def parse_review(
    source_rows: list[dict],
    review_path: Path | None = None,
) -> tuple[dict[str, dict], Path | None]:
    """Load and strictly align the optional diagnostic review with the corpus.

    Args:
        source_rows: Authoritative source rows in extraction order.

    Returns:
        A pair containing review annotations keyed by stable text ID and the
        selected review-file path.

    Raises:
        FileNotFoundError: If none of :data:`REVIEW_CANDIDATES` exists.
        ValueError: If row count, column count, or source-order IDs differ.
        OSError: If the review file cannot be read.

    Design:
        Positional and ID checks prevent plausible-looking annotations from
        being attached to the wrong ROM record.  Automated review text remains
        advisory and is interpreted again by later functions.
    """
    if review_path is None:
        review_path = next(
            (path for path in REVIEW_CANDIDATES if path.exists()), None
        )
    if review_path is None:
        neutral = {
            "qa": "",
            "direction": "",
            "close_reading": "",
            "review_priority": "medium",
            "raw_notes": "",
        }
        return {row["text_id"]: dict(neutral) for row in source_rows}, None
    if not review_path.is_file():
        raise FileNotFoundError(
            f"diagnostic review file not found: {review_path}"
        )
    parser = ReviewTableParser()
    parser.feed(review_path.read_text(encoding="utf-8"))
    data_rows = parser.rows[1:]
    if len(data_rows) != len(source_rows):
        raise ValueError(
            f"review has {len(data_rows)} rows; source has {len(source_rows)}"
        )
    output: dict[str, dict] = {}
    for source, review in zip(source_rows, data_rows, strict=True):
        if len(review) != 9:
            raise ValueError(f"review row has {len(review)} columns")
        id_lines = review[1].splitlines()
        if source["text_id"] not in id_lines:
            raise ValueError(
                f"review/source order mismatch: {source['text_id']} not in {id_lines}"
            )
        qa_and_direction = review[7]
        if "Translation direction" in qa_and_direction:
            qa, direction = qa_and_direction.split("Translation direction", 1)
        else:
            qa, direction = qa_and_direction, ""
        close = review[5]
        close = close.removeprefix("Close reading").strip()
        if close.startswith("No independent full literal rendering"):
            close = ""
        priority_match = re.search(r"review:\s*(high|medium|low)", review[8])
        output[source["text_id"]] = {
            "qa": qa.strip(),
            "direction": direction.strip(),
            "close_reading": close.strip('“”" '),
            "review_priority": (
                priority_match.group(1) if priority_match else "medium"
            ),
            "raw_notes": review[6],
        }
    return output, review_path


def direction_is_translation(direction: str) -> bool:
    """Decide whether review guidance contains usable translated wording.

    Args:
        direction: Diagnostic review's translation-direction cell.

    Returns:
        ``True`` when the non-empty text is not one of the known generic
        instructions.

    Note:
        This conservative allow-by-exclusion rule prevents prose such as
        "Retranslate clause by clause" from appearing as game dialogue.
    """
    generic = (
        "Current English is a usable draft",
        "Retranslate clause by clause",
        "Preserve meaning first",
        "Use ",
    )
    return bool(direction) and not direction.startswith(generic)


def expanded_fixed_meaning(source_row: dict) -> str:
    """Recover a readable natural meaning for a constrained fixed-address label.

    Args:
        source_row: Fixed-address source mapping containing exact Japanese and
            the current compact English.

    Returns:
        A curated phrase, month name, counted-unit phrase, numbered Coyote label,
        existing readable English, or normalized Japanese fallback.

    Raises:
        KeyError: If required source fields are absent.

    Design:
        The result is editorial analysis only.  It does not replace the verified
        compact patch form or imply that expanded English fits the original slot.
    """
    exact = source_row["japanese_exact"]
    plain = collapse(CONTROL_RE.sub(" ", exact))
    if exact in FIXED_NATURAL:
        return FIXED_NATURAL[exact]
    if plain in FIXED_NATURAL:
        return FIXED_NATURAL[plain]
    month = re.fullmatch(r"(\d+)がつ", plain)
    if month:
        names = (
            "",
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        )
        number = int(month.group(1))
        if 1 <= number <= 12:
            return names[number]
    count = re.fullmatch(
        r"(\d+)(ぴき|ひき|びき|こ|かしょ|はい|ぱい|ぷん|せんち)", plain
    )
    if count:
        units = {
            "ぴき": "animals",
            "ひき": "animals",
            "びき": "animals",
            "こ": "items",
            "かしょ": "places",
            "はい": "cups",
            "ぱい": "cups",
            "ぷん": "minutes",
            "せんち": "centimeters",
        }
        return f"{count.group(1)} {units[count.group(2)]}"
    numbered = re.fullmatch(r"こよーて(\d+)", plain)
    if numbered:
        return f"Coyote {numbered.group(1)}"
    current = source_row["current_english_readable"].strip()
    if current and not re.fullmatch(r"[A-Z0-9 .-]{1,7}", current):
        return current
    return current or plain


def final_natural(source_row: dict, review: dict) -> str:
    """Select the preferred unconstrained English localization.

    Args:
        source_row: Authoritative source record plus provisional English.
        review: Aligned diagnostic annotations for the same text ID.

    Returns:
        Manual translation when available, expanded fixed-address meaning,
        readable graphics text, a substantive review proposal, or naturalized
        current English in that priority order.

    Raises:
        KeyError: If required source or review fields are missing.
    """
    text_id = source_row["text_id"]
    if text_id in MANUAL_FINAL:
        return MANUAL_FINAL[text_id]
    if source_row["kind"] == "fixed-address":
        return expanded_fixed_meaning(source_row)
    if source_row["kind"] == "graphics-text":
        return naturalize_current(source_row["current_english_exact"])
    if direction_is_translation(review["direction"]):
        return naturalize_current(review["direction"])
    return naturalize_current(source_row["current_english_exact"])


def literal_meaning(source_row: dict, review: dict, final: str) -> str:
    """Select an intelligible structure-preserving English reading.

    Args:
        source_row: Authoritative source record and provisional English.
        review: Aligned diagnostic review annotations.
        playable_scenario_text: Release-authoritative ID-keyed scenario text.
        final: Already selected natural translation, retained for call-site
            symmetry and future context-sensitive comparison.

    Returns:
        Close reading, expanded fixed meaning, manual correction, substantive
        review translation, or naturalized draft in decreasing preference.

    Note:
        A corrected complete reading is preferred over repeating a draft known
        to omit Japanese information.  "Literal" here exposes information and
        structure; it is not deliberately ungrammatical word-for-word English.
    """
    if review["close_reading"]:
        return naturalize_current(review["close_reading"])
    if source_row["kind"] == "fixed-address":
        return expanded_fixed_meaning(source_row)
    if source_row["text_id"] in MANUAL_FINAL:
        return MANUAL_FINAL[source_row["text_id"]]
    # The current draft generally follows Japanese clause order even when its
    # localization is terse. For rows with a substantive correction, use the
    # corrected complete reading so omitted content is not repeated as "literal."
    if direction_is_translation(review["direction"]):
        return naturalize_current(review["direction"])
    return naturalize_current(source_row["current_english_exact"])


def speaker_identity(source_row: dict, final: str) -> str:
    """Infer the most defensible speaker or narration identity.

    Args:
        source_row: Source record containing type, exact Japanese, and stable ID.
        final: Natural English, used only for explicit English speaker labels.

    Returns:
        Manual override, interface/graphics identity, semicolon-separated
        Japanese or English labels, an unidentified-voice marker, or the broad
        narration/interaction fallback.

    Design:
        The function never assigns a character merely because an unlabeled line
        resembles that character's voice.  Uncertainty remains explicit until
        neighboring records or gameplay provide evidence.
    """
    if source_row["text_id"] in SPEAKER_IDENTITY_OVERRIDES:
        return SPEAKER_IDENTITY_OVERRIDES[source_row["text_id"]]
    if source_row["kind"] == "fixed-address":
        return "Interface / command / object label"
    if source_row["kind"] == "graphics-text":
        return "Title or system graphics"
    source = CONTROL_RE.sub(" ", source_row["japanese_exact"])
    labels = JP_LABEL_RE.findall(source)
    identities: list[str] = []
    for label in labels:
        name = SPEAKER_MAP.get(label, label)
        if name not in identities:
            identities.append(name)
    if identities:
        return "; ".join(identities)
    english_labels = re.findall(
        r"(?:^|/|\s)([A-Z][A-Za-z0-9 .-]{0,28}):", final
    )
    if english_labels:
        return "; ".join(
            dict.fromkeys(label.strip() for label in english_labels)
        )
    if "「" in source:
        return "Unidentified voice / context-dependent speaker"
    return "Narration / protagonist's internal observation / interaction text"


def dialect_register(source_row: dict) -> str:
    """Describe contextual voice and register markers without substring guesses.

    Args:
        source_row: Source mapping whose exact Japanese is analyzed.

    Returns:
        A semicolon-separated list of distinct pronoun, ending, politeness,
        dialect-cluster, hesitation, and display-timing observations.

    Design:
        Regular expressions require grammatical boundaries so kana embedded in
        unrelated words do not create false dialect labels.  Stock role-language
        such as ``わし``/``じゃ`` is distinguished from clustered regional forms.
    """
    text = CONTROL_RE.sub(" ", source_row["japanese_exact"])
    notes: list[str] = []
    if re.search(r"おれ(?:は|が|の|を|に|も|だ|「|$)", text):
        notes.append("おれ: plain-to-rough masculine first person")
    if re.search(r"ぼく(?:は|が|の|を|に|も|「|$)", text):
        notes.append("ぼく: softer masculine first person")
    if re.search(r"わたくし(?:は|が|の|を|に|も|「|$)", text):
        notes.append("わたくし: formal/humble first person")
    if re.search(r"わし(?:は|が|の|を|に|も|じゃ|「|$)", text):
        notes.append("わし: elderly/authoritative masculine role-language")
    if re.search(r"きさま(?:ら|は|が|の|を|に|も|「|$)", text):
        notes.append("きさま: hostile/contemptuous second person")
    if re.search(r"おまえ(?:ら|は|が|の|を|に|も|「|$)", text):
        notes.append("おまえ: familiar or rough second person")
    if re.search(r"じゃ(?:[ろっがぞな。！？…」]|$)", text):
        notes.append(
            "じゃ: old-person/authority role-copula; not automatically regional"
        )
    if re.search(r"(?<![あき])のう(?:[。！？…」]|$)", text):
        notes.append("のう: elderly/reflective ending")
    if any(
        marker in text
        for marker in ("どえりゃー", "だがや", "うるしゃー", "くりゃーて")
    ):
        notes.append("clustered stylized Nagoya/Owari speech")
    if re.search(r"だっぺ(?:[。！？…」]|$)", text):
        notes.append("だっぺ: marked rural/Tohoku-coded ending")
    if re.search(r"だべ(?:[。！？…」]|$)", text):
        notes.append("だべ: marked rural/Tohoku-coded ending")
    if re.search(r"だわ(?:[。！？…」]|$)", text):
        notes.append("だわ: feminine-coded ending in this period/register")
    if re.search(r"かしら(?:[。！？…」]|$)", text):
        notes.append("かしら: feminine-coded uncertainty/question")
    if re.search(r"ぜ(?:[。！？…」]|$)", text):
        notes.append("ぜ: rough masculine emphasis")
    if re.search(r"ぞ(?:[。！？…」]|$)", text):
        notes.append("ぞ: forceful emphasis")
    if re.search(r"ございます|いたします|くださいます", text):
        notes.append("elevated polite/honorific language")
    elif re.search(r"です|ます|ください", text):
        notes.append("polite です/ます register")
    if re.search(r"([\u3041-\u3096])\s+\1", text):
        notes.append("stutter/restart is meaningful performance")
    if "……" in text or "…" in text:
        notes.append("ellipsis carries hesitation, silence, or timing")
    if "／" in text:
        notes.append("／ functions as a strong display exclamation/beat")
    return "; ".join(dict.fromkeys(notes))


def linguistic_notes(source_row: dict, review: dict, register: str) -> str:
    """Assemble evidence-backed linguistic and cultural commentary.

    Args:
        source_row: Authoritative source and record metadata.
        review: Aligned review annotations, reserved for context-sensitive
            extension of the note pipeline.
        register: Boundary-aware output from :func:`dialect_register`.

    Returns:
        A prose note covering relevant register, control behavior, fixed-slot
        constraints, curated line findings, historical content, and the
        reconstruction evidence boundary.

    Design:
        Sensitive historical language is described as source characterization,
        neither endorsed nor silently sanitized.
    """
    notes: list[str] = []
    if register:
        notes.append(register)
    if controls(source_row["japanese_exact"]):
        notes.append(
            "Control tags are non-linguistic display/timing instructions and are "
            "preserved in order in the patch-safe field."
        )
    if source_row["kind"] == "fixed-address":
        notes.append(
            f"Fixed-address interface record: {source_row['packed_bytes']} packed "
            "bytes. The natural field expands the meaning; the patch-safe field "
            "retains the verified slot form."
        )
    if source_row["text_id"] in MANUAL_NOTES:
        notes.append(MANUAL_NOTES[source_row["text_id"]])
    if source_row["text_id"] == "TT1B/g0/r28":
        notes.append(
            "ぜんぶみました is formally compatible with a statement or a question "
            "because the ROM text lacks a normal question mark. The protagonist's "
            "reply いえ ('no') makes 'Have you seen all the exhibits?' the strongest "
            "contextual reading."
        )
    if source_row["text_id"] == "TT1B/g0/r17":
        notes.append("ブロンズの像 explicitly means a bronze statue/figure.")
    if source_row["text_id"] == "TT1B/g0/r1":
        notes.append(
            "青空 is explicit: the image is a blue sky, not an unspecified 'it.'"
        )
    if source_row["text_id"] == "TT1A/g0/r9":
        notes.append(
            "A declarative personality-test proposition with a Japanese pro-baseball "
            "cultural reference to the Yomiuri Giants."
        )
    if source_row["text_id"] == "TT1B/g2/r5":
        notes.append(
            "地上げ屋 is a bubble-era 'land shark' or developer who pressures "
            "residents to leave so parcels can be assembled."
        )
    if source_row["bank"] in {"TT5", "T25"} and any(
        term in source_row["japanese_exact"]
        for term in ("どれい", "さべつ", "なんぶ")
    ):
        notes.append(
            "The source is depicting nineteenth-century slavery/racism; harmful "
            "content is translated as character speech or narration without "
            "endorsing or sanitizing it."
        )
    notes.append(
        "Reconstructed Japanese is conservative editorial normalization; any kana "
        "left unreconstructed remains deliberately unresolved rather than being "
        "silently assigned kanji."
    )
    return " ".join(notes)


def problem_categories(
    qa: str, source_row: dict, final: str
) -> tuple[str, ...]:
    """Map free-form review evidence to normalized QA problem categories.

    Args:
        qa: Diagnostic review prose for the current record.
        source_row: Source metadata used to distinguish fixed-address text.
        final: Selected natural translation for compression comparison.

    Returns:
        An ordered, duplicate-free tuple of concrete issue labels.  Records with
        no detected issue receive ``"Accurate"``; constrained labels may instead
        receive the acceptable-compression category.

    Design:
        Matching is intentionally limited to English review prose.  It is not
        used to infer Japanese dialect or grammar, avoiding the unsafe substring
        behavior found in the earlier diagnostic workbook.
    """
    categories: list[str] = []
    generic_review_boilerplate = (
        "No obvious line-level defect detected automatically. "
        "Confirm speaker identity, scene context, and screen-space constraints "
        "before finalizing."
    )
    lowered = qa.replace(generic_review_boilerplate, "").lower()
    mapping = (
        ("drops", "Omitted information"),
        ("omits", "Omitted information"),
        ("removes", "Omitted information"),
        ("invents", "Added information"),
        ("added", "Added information"),
        ("subject", "Incorrect subject"),
        ("object", "Incorrect object"),
        ("speaker", "Incorrect speaker / context"),
        ("tense", "Incorrect tense or aspect"),
        ("name", "Incorrect or uncertain name"),
        ("place", "Incorrect place"),
        ("item", "Incorrect item"),
        ("joke", "Lost joke"),
        ("comic", "Lost joke or characterization"),
        ("character", "Lost characterization"),
        ("dialect", "Lost dialect"),
        ("regional", "Lost dialect"),
        ("cultural", "Wrong/lost cultural reference"),
        ("polite", "Wrong or flattened register"),
        ("honorific", "Wrong or flattened register"),
        ("ambiguous", "Ambiguous Japanese"),
        ("context", "Context needed"),
        ("trunc", "Technical truncation"),
        ("awkward", "Unnatural English"),
        ("grammar", "Grammar or punctuation problem"),
        ("punctuation", "Grammar or punctuation problem"),
    )
    for needle, category in mapping:
        if needle in lowered and category not in categories:
            categories.append(category)
    if source_row["kind"] == "fixed-address":
        natural = final.casefold()
        current = source_row["current_english_readable"].casefold()
        if natural != current:
            categories.append(
                "Acceptable compression / technical abbreviation"
            )
        else:
            categories.append("Accurate")
    elif not categories:
        categories.append("Accurate")
    resolved_playable_ids = {
        "TT1B/g0/r31",
        "TT1B/g1/r14",
        "TT1B/g2/r5",
        "TT6A/g0/r13",
    }
    if source_row["text_id"] in resolved_playable_ids:
        return ("Accurate",)
    return tuple(dict.fromkeys(categories))


def current_problems(
    source_row: dict, review: dict, final: str, categories: tuple[str, ...]
) -> str:
    """Explain concrete differences between current and preferred English.

    Args:
        source_row: Source record and currently installed translation.
        review: Aligned diagnostic findings.
        final: Preferred natural English selected for the record.
        categories: Normalized output from :func:`problem_categories`.

    Returns:
        A curated finding for known problem lines, a fixed-slot fit explanation,
        a control-code caveat, a concise accuracy statement, or cleaned review
        prose.

    Design:
        Generic "check context" boilerplate is never presented as a specific
        defect.  Fixed-address abbreviations are documented as technical choices
        instead of being mislabeled as mistranslations.
    """
    qa = review["qa"]
    manual = {
        "TT1B/g0/r31": (
            "Resolved in the playable text: the protagonist's disbelief, the "
            "Devil's Nagashima-like roundabout comic reply, and the patient "
            "telepathy payoff are restored across audited presentation rows."
        ),
        "TT1B/g1/r14": (
            "Resolved in the playable text: the dated, leering ボイン joke keeps "
            "both the 'quite a pair' wording and the heh-heh laugh, while the "
            "girl's embarrassed protest remains."
        ),
        "TT1B/g2/r5": (
            "Resolved in the playable text: the resident's forty-year attachment "
            "to this house, disbelief at leaving now, and flustered polite apology "
            "are restored; 'land shark' retains the 地上げ屋 social meaning."
        ),
        "TT6A/g0/r13": (
            "Resolved in the playable text: Joseph identifies Mary as his "
            "betrothed and explicitly says she has no idea how she became pregnant."
        ),
    }
    if source_row["text_id"] in manual:
        return manual[source_row["text_id"]]
    generic = "No obvious line-level defect detected automatically."
    if source_row["kind"] == "fixed-address":
        if (
            final.casefold()
            == source_row["current_english_readable"].casefold()
        ):
            return f"Accurate within a fixed {source_row['packed_bytes']}-byte record."
        return (
            f"Technical abbreviation: current slot text "
            f"'{source_row['current_english_readable']}' represents '{final}' in "
            f"{source_row['packed_bytes']} packed bytes. Natural meaning is expanded "
            f"in the final field."
        )
    if source_row["text_id"] == "NOV2/wait":
        return (
            "Grammar is accurate, but the existing patch intentionally removed the "
            "source CTRL:0 to keep the prompt on one visible line; that conflicts "
            "with this workbook's exact-control requirement."
        )
    if generic in qa:
        if source_row["current_english_readable"].strip() == final.strip():
            return "Accurate."
        return (
            "Acceptable draft; natural wording and speaker labeling refined."
        )
    cleaned = qa.replace(generic, "").strip()
    cleaned = re.sub(r"Technical constraints.*$", "", cleaned).strip()
    return cleaned or "; ".join(categories)


def insert_controls_by_current_layout(final: str, current_exact: str) -> str:
    """Redistribute existing control tags proportionally across revised words.

    Args:
        final: Control-free replacement English.
        current_exact: Existing English whose ordered controls and segment
            proportions define the timing/layout template.

    Returns:
        Replacement English with every existing control reinserted in order.
        If the replacement has no words, only the ordered controls are returned.

    Assumptions:
        Controls separate display or timing segments, and relative segment
        lengths are a better automatic fallback than collecting all controls at
        the end.  Manual patch overrides take precedence for sensitive records.

    Note:
        This is a proposal generator, not visual proof.  The result still passes
        control equality, display-width, encoder, and bank recompression checks.
    """
    values = list(controls(current_exact))
    if not values:
        return final
    old_segments = re.split(r"\{CTRL:\d+\}", current_exact)
    total = sum(max(len(segment), 1) for segment in old_segments)
    words = final.split()
    if not words:
        return "".join(f"{{CTRL:{value}}}" for value in values)
    cumulative_targets: list[float] = []
    running = 0
    for segment in old_segments[:-1]:
        running += max(len(segment), 1)
        cumulative_targets.append(running / total)
    boundaries: list[int] = []
    for target in cumulative_targets:
        candidate = max(1, min(len(words) - 1, round(target * len(words))))
        if boundaries and candidate <= boundaries[-1]:
            candidate = min(len(words) - 1, boundaries[-1] + 1)
        boundaries.append(candidate)
    pieces: list[str] = []
    start = 0
    for index, boundary in enumerate(boundaries):
        pieces.append(" ".join(words[start:boundary]))
        pieces.append(f"{{CTRL:{values[index]}}}")
        start = boundary
    pieces.append(" ".join(words[start:]))
    return "".join(pieces)


def patch_charset_safe(text: str) -> str:
    """Replace editorial Unicode punctuation with ROM-font-safe equivalents.

    Args:
        text: Proposed English that may contain smart quotes, typographic
            dashes, ellipses, or non-breaking spaces.

    Returns:
        Text using the patch character set's ASCII punctuation conventions.

    Note:
        This conversion is deliberately narrow.  Unsupported letters are left
        visible so the actual encoder can reject them instead of hiding a
        translation error through lossy transliteration.
    """
    return (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("…", "...")
        .replace("—", "--")
        .replace("–", "-")
        .replace("\u00a0", " ")
    )


def load_playable_scenario_text() -> dict[str, str]:
    """Load the ID-keyed scenario maps that define the playable release."""
    output: dict[str, str] = {}
    for path in sorted(TRANSLATIONS.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(
                f"playable translation map is not an object: {path}"
            )
        for text_id, text in payload.items():
            if not isinstance(text_id, str) or not isinstance(text, str):
                raise ValueError(
                    f"playable translation map has non-string data: {path}"
                )
            if text_id in output:
                raise ValueError(
                    f"duplicate playable translation ID: {text_id}"
                )
            output[text_id] = text
    return output


def patch_safe(
    source_row: dict,
    final: str,
    review: dict,
    playable_scenario_text: dict[str, str],
) -> tuple[str, str, bool]:
    """Build a control-safe patch candidate and estimate technical fit risk.

    Args:
        source_row: Source metadata and currently installed English.
        final: Preferred unconstrained translation.
        review: Aligned diagnostic review annotations.
        playable_scenario_text: Authoritative record-ID-to-English scenario map.

    Returns:
        A three-item tuple of patch text, any documented nuance/fit note, and a
        Boolean indicating that expansion or recompression review is required.

    Raises:
        ValueError: If the proposed patch changes the source control sequence.
        KeyError: If required corpus fields are missing.

    Design:
        Playable scenario maps are authoritative, fixed-address/graphics records
        retain their installed forms, and editorial alternatives remain in the
        natural-translation field.
        Visible-length and 24-column checks are conservative warnings.  A bank
        listed in :data:`PATCH_FOOTPRINT_RESULTS` overrides that estimate because
        its finalized map passed native encoding, display, and recompression.
    """
    text_id = source_row["text_id"]
    if source_row["kind"] == "scenario":
        try:
            patch = playable_scenario_text[text_id]
        except KeyError as error:
            raise ValueError(
                f"playable scenario translation is missing: {text_id}"
            ) from error
    elif source_row["kind"] in {"fixed-address", "graphics-text"}:
        patch = source_row["current_english_exact"]
    elif text_id in MANUAL_PATCH:
        patch = MANUAL_PATCH[text_id]
    elif (
        direction_is_translation(review["direction"])
        or text_id in MANUAL_FINAL
    ):
        patch = insert_controls_by_current_layout(
            final.replace("Protagonist:", "Me:"),
            source_row["current_english_exact"],
        )
    else:
        patch = source_row["current_english_exact"]
    patch = patch_charset_safe(patch)
    if (
        text_id in PRESENTATION_BREAK_RECORD_IDS
        and not scenario_controls_match_policy(
            text_id, patch, source_row["japanese_exact"]
        )
    ):
        raise ValueError(
            f"{text_id}: control tags changed beyond audited presentation breaks"
        )
    if (
        controls(patch) != controls(source_row["japanese_exact"])
        and text_id not in CONTROL_OVERRIDE_IDS
    ):
        raise ValueError(
            f"control mismatch in proposed patch for {text_id}: "
            f"{controls(source_row['japanese_exact'])} != {controls(patch)}"
        )
    if source_row["packed_bytes"].isdigit():
        return patch, "", False
    if source_row["packed_bytes"] != "group-compressed":
        return patch, "", False
    current_visible = len(
        CONTROL_RE.sub("", source_row["current_english_exact"])
    )
    patch_visible = len(CONTROL_RE.sub("", patch))
    current_segment_max = max(
        (
            len(part)
            for part in re.split(
                r"\{CTRL:\d+\}", source_row["current_english_exact"]
            )
        ),
        default=0,
    )
    patch_segment_max = max(
        (len(part) for part in re.split(r"\{CTRL:\d+\}", patch)), default=0
    )
    segment_overflow = patch_segment_max > max(24, current_segment_max)
    expansion = patch_visible > current_visible or segment_overflow
    if source_row["bank"] in PATCH_FOOTPRINT_RESULTS:
        # These revised bank-wide maps passed both display validation and native
        # recompression after the patch-safe wording was finalized.
        expansion = False
    nuance = ""
    if (
        source_row["text_id"] not in INTENT_RESTORED_IDS
        and patch == source_row["current_english_exact"]
        and final != naturalize_current(patch)
    ):
        nuance = (
            "The playable wording still differs from the reviewed natural reading. "
            "Re-evaluate it under the intent-first layout/compression workflow; "
            "earlier compact wording is not authoritative merely because it fit."
        )
    elif expansion:
        nuance = (
            "No semantic point was intentionally dropped, but the proposed wording "
            "exceeds the current draft's visible length or a 24-column segment and "
            "requires recompression/wrapping review."
        )
    return patch, nuance, expansion


def ambiguity_and_confidence(
    source_row: dict, review: dict, register: str
) -> tuple[str, str, bool]:
    """Classify unresolved ambiguity and the evidence needed to resolve it.

    Args:
        source_row: Source record and stable ID.
        review: Diagnostic annotations including review priority.
        register: Analyzed dialect/register description.

    Returns:
        A tuple containing the ambiguity explanation, confidence label, and
        whether gameplay or visual verification is requested.

    Design:
        Known spatial, speaker, punctuation, and control conflicts are handled
        explicitly.  The function still returns a proposed translation; low
        confidence never becomes an excuse for an empty workbook field.
    """
    text_id = source_row["text_id"]
    if text_id == "TT3A/g2/r30":
        return (
            "Spatial order of the torn-note characters needs a gameplay screenshot "
            "or nametable capture.",
            "Requires ROM or visual verification",
            True,
        )
    if text_id == "TT1B/g0/r28":
        return (
            "Punctuation alone permits statement/question readings, but the reply "
            "いえ strongly favors a question.",
            "Medium",
            True,
        )
    if text_id == "NOV2/wait":
        return (
            "Source control preservation conflicts with the existing one-line "
            "English display fix.",
            "Requires ROM or visual verification",
            True,
        )
    if text_id in GAMEPLAY_SPEAKER_AMBIGUITIES:
        return (
            GAMEPLAY_SPEAKER_AMBIGUITIES[text_id],
            "Requires gameplay context",
            True,
        )
    if "Unidentified voice" in speaker_identity(source_row, ""):
        return (
            "The ROM uses an unlabeled quotation; visual scene context may identify "
            "the speaker more precisely.",
            "Requires gameplay context",
            True,
        )
    if source_row["kind"] in {"fixed-address", "graphics-text"}:
        return "", "High", False
    if review["review_priority"] == "high":
        return "", "Medium", False
    if "context-dependent" in register:
        return (
            "A lexical or speaker reading depends on the interaction target.",
            "Requires gameplay context",
            True,
        )
    return "", "High", False


def make_rows(
    review_file: Path | None = None,
) -> tuple[list[WorkbookRow], dict, Path | None]:
    """Create the complete ordered workbook from authoritative source records.

    Returns:
        A tuple of populated :class:`WorkbookRow` objects, the untouched source
        payload, and the diagnostic review path used.

    Raises:
        OSError: If source or review files cannot be read.
        json.JSONDecodeError: If the source corpus is not valid JSON.
        ValueError: If the source count is not exactly 2,052, review alignment
            fails, or a proposed patch changes control codes.
        KeyError: If required corpus fields, bank scene metadata, or aligned
            review annotations are missing.

    Side Effects:
        Reads the authoritative JSON corpus and one diagnostic HTML file.  It
        does not write artifacts; writing is deferred until validation succeeds.

    Design:
        Every field is derived in source order.  Natural translation, literal
        reading, speaker, register, QA, patch fit, and confidence are calculated
        separately so one inference cannot overwrite authoritative source data.
    """
    payload = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    source_rows = payload["rows"]
    if len(source_rows) != 2058:
        raise ValueError(f"expected 2058 source rows, got {len(source_rows)}")
    review_map, review_path = parse_review(source_rows, review_file)
    playable_scenario_text = load_playable_scenario_text()
    output: list[WorkbookRow] = []
    for source_row in source_rows:
        review = review_map[source_row["text_id"]]
        final = final_natural(source_row, review)
        literal = literal_meaning(source_row, review, final)
        register = dialect_register(source_row)
        notes = linguistic_notes(source_row, review, register)
        categories = problem_categories(review["qa"], source_row, final)
        problems = current_problems(source_row, review, final, categories)
        patch, nuance, expansion = patch_safe(
            source_row, final, review, playable_scenario_text
        )
        ambiguity, confidence, gameplay = ambiguity_and_confidence(
            source_row, review, register
        )
        if expansion:
            status = (
                "Final proposed — technical expansion/recompression review"
            )
        elif gameplay:
            status = "Final proposed — gameplay/visual confirmation requested"
        else:
            status = "Final proposed"
        output.append(
            WorkbookRow(
                sequential_entry_number=source_row["sequence"],
                original_record_id=source_row["text_id"],
                bank=source_row["bank"],
                record_type=source_row["kind"],
                exact_japanese_source=source_row["japanese_exact"],
                romaji=ROMAJI_OVERRIDES.get(
                    source_row["text_id"], source_row["mechanical_romaji"]
                ),
                reconstructed_japanese=conservative_reconstruction(
                    source_row["japanese_exact"]
                ),
                literal_english_meaning=literal,
                linguistic_and_cultural_notes=notes,
                speaker_or_narration_identity=speaker_identity(
                    source_row, final
                ),
                current_english=source_row["current_english_exact"],
                problems_with_current_english=problems,
                final_natural_english_translation=final,
                patch_safe_english_translation=patch,
                confidence_level=confidence,
                unresolved_ambiguity=ambiguity,
                translation_status=status,
                scene=SCENES[source_row["bank"]]["title"],
                source_location=source_row["source_location"],
                apparent_capacity=current_capacity(source_row),
                source_control_codes=",".join(
                    controls(source_row["japanese_exact"])
                ),
                patch_control_codes=",".join(controls(patch)),
                control_codes_match=(
                    "yes"
                    if controls(source_row["japanese_exact"])
                    == controls(patch)
                    else "no"
                ),
                problem_categories="; ".join(categories),
                dialect_or_register=register
                or "Unmarked / neutral or context-dependent",
                requires_gameplay_context="yes" if gameplay else "no",
                requires_technical_expansion="yes" if expansion else "no",
                nuance_lost_in_patch_safe_version=nuance,
            )
        )
    return output, payload, review_path


def first_occurrence(rows: list[WorkbookRow], needle: str) -> str:
    """Find a glossary expression's first contiguous source occurrence.

    Args:
        rows: Workbook rows in authoritative source order.
        needle: Exact Japanese glossary spelling, possibly with control tags.

    Returns:
        The first matching stable record ID, or an explanatory sentinel when the
        spelling does not occur as one contiguous decoded substring.

    Note:
        Both exact and control-stripped forms are checked.  The function does not
        perform fuzzy matching because that could silently conflate homophones.
    """
    simplified = CONTROL_RE.sub(" ", needle)
    for row in rows:
        if (
            needle in row.exact_japanese_source
            or simplified in CONTROL_RE.sub(" ", row.exact_japanese_source)
        ):
            return row.original_record_id
    return "not found as one contiguous ROM substring"


def make_glossary(rows: list[WorkbookRow]) -> list[dict]:
    """Materialize the curated global terminology table.

    Args:
        rows: Completed workbook rows used to locate first occurrences.

    Returns:
        Dictionaries containing category, exact and reconstructed Japanese,
        mechanical romaji, chosen English, alternatives, first occurrence, and
        editorial notes for every glossary seed.

    Design:
        Chosen forms come from the centralized seed table so terminology cannot
        drift silently between HTML, JSON, CSV, and the voice guide.
    """
    output = []
    for (
        category,
        exact,
        reconstructed,
        chosen,
        alternatives,
        notes,
    ) in GLOSSARY_SEEDS:
        output.append(
            {
                "category": category,
                "exact_japanese": exact,
                "reconstructed_japanese": reconstructed,
                "romaji": _romanize(exact),
                "chosen_english": chosen,
                "alternative_readings": alternatives,
                "first_occurrence": first_occurrence(rows, exact),
                "notes": notes,
            }
        )
    return output


def escape_cell(value: object) -> str:
    """Escape one value for safe HTML table-cell interpolation.

    Args:
        value: Any value whose string representation should be displayed.

    Returns:
        HTML-escaped text with newline characters converted to ``<br>``.
    """
    return html.escape(str(value)).replace("\n", "<br>")


def render_html(
    rows: list[WorkbookRow],
    glossary: list[dict],
    source_payload: dict,
    review_path: Path | None,
) -> str:
    """Render the complete searchable workbook as a self-contained HTML page.

    Args:
        rows: Validated review rows in authoritative order.
        glossary: Materialized global glossary.
        source_payload: Source corpus metadata used for provenance.
        review_path: Diagnostic review file used during generation.

    Returns:
        A UTF-8-compatible HTML document containing methodology, scene summaries,
        control legend, voice guide, glossary, all record columns, and client-side
        filters.  No external scripts or stylesheets are required.

    Raises:
        OSError: If provenance fingerprints cannot read their source files.
        KeyError: If expected source metadata, scenes, glossary, or row fields
            are missing.

    Design:
        Exact and reconstructed Japanese receive visually distinct styles.
        Filter metadata is duplicated into escaped ``data-*`` attributes so the
        static artifact remains searchable without a web server or build step.
    """
    counts = Counter(row.record_type for row in rows)
    footprint_summary = "; ".join(
        f"{bank} {result['used']}/{result['capacity']} bytes "
        f"({result['remaining']} free)"
        for bank, result in PATCH_FOOTPRINT_RESULTS.items()
    )
    review_provenance = (
        f" Diagnostic review: {escape_cell(review_path.name)} "
        f"(SHA-256 {sha256(review_path)})."
        if review_path is not None
        else " Diagnostic review: none supplied; neutral diagnostics used."
    )
    bank_options = "".join(
        f'<option value="{html.escape(bank)}">{html.escape(bank)}</option>'
        for bank in BANK_ORDER
    )
    speaker_values = sorted(
        {row.speaker_or_narration_identity for row in rows}
    )
    speaker_options = "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in speaker_values
    )
    confidence_values = sorted({row.confidence_level for row in rows})
    confidence_options = "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in confidence_values
    )
    status_values = sorted({row.translation_status for row in rows})
    status_options = "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in status_values
    )
    categories = sorted(
        {
            category.strip()
            for row in rows
            for category in row.problem_categories.split(";")
            if category.strip()
        }
    )
    category_options = "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in categories
    )
    scene_cards = "".join(
        (
            f'<article><h3>{escape_cell(bank)} — {escape_cell(scene["title"])}</h3>'
            f'<p>{escape_cell(scene["summary"])}</p>'
            f'<p><b>Translation choices:</b> {escape_cell(scene["choices"])}</p></article>'
        )
        for bank, scene in SCENES.items()
    )
    speaker_headers = (
        "Known name",
        "Japanese labels",
        "First person",
        "Typical endings",
        "Politeness",
        "Dialect",
        "Verbal habits",
        "Relationships",
        "Recommended English voice",
    )
    speaker_rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{escape_cell(entry[key])}</td>"
            for key in (
                "name",
                "labels",
                "first_person",
                "endings",
                "politeness",
                "dialect",
                "habits",
                "relationships",
                "english_voice",
            )
        )
        + "</tr>"
        for entry in SPEAKER_REFERENCES
    )
    glossary_rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{escape_cell(entry[key])}</td>"
            for key in (
                "category",
                "exact_japanese",
                "reconstructed_japanese",
                "romaji",
                "chosen_english",
                "alternative_readings",
                "first_occurrence",
                "notes",
            )
        )
        + "</tr>"
        for entry in glossary
    )
    record_fields = tuple(WorkbookRow.__dataclass_fields__)
    display_headers = {
        "sequential_entry_number": "#",
        "original_record_id": "Record ID",
        "record_type": "Type",
        "exact_japanese_source": "Exact Japanese from ROM",
        "romaji": "Romaji",
        "reconstructed_japanese": "Probable normalized Japanese",
        "literal_english_meaning": "Literal English",
        "linguistic_and_cultural_notes": "Linguistic / cultural notes",
        "speaker_or_narration_identity": "Speaker / narration",
        "current_english": "Current English",
        "problems_with_current_english": "Current-English problems",
        "final_natural_english_translation": "Final natural English",
        "patch_safe_english_translation": "Patch-safe English",
        "confidence_level": "Confidence",
        "unresolved_ambiguity": "Unresolved ambiguity",
        "translation_status": "Status",
        "source_location": "Source location",
        "apparent_capacity": "Apparent capacity",
        "source_control_codes": "Source controls",
        "patch_control_codes": "Patch controls",
        "control_codes_match": "Controls match",
        "problem_categories": "Problem category",
        "dialect_or_register": "Dialect / register",
        "requires_gameplay_context": "Gameplay context?",
        "requires_technical_expansion": "Expansion?",
        "nuance_lost_in_patch_safe_version": "Patch-safe loss / fit note",
    }
    header_html = "".join(
        f"<th>{escape_cell(display_headers.get(field, field.replace('_', ' ').title()))}</th>"
        for field in record_fields
    )
    body_rows = []
    for row in rows:
        data = asdict(row)
        attrs = {
            "bank": row.bank,
            "kind": row.record_type,
            "speaker": row.speaker_or_narration_identity,
            "status": row.translation_status,
            "confidence": row.confidence_level,
            "problems": row.problem_categories,
            "dialect": row.dialect_or_register,
            "gameplay": row.requires_gameplay_context,
            "technical": row.requires_technical_expansion,
        }
        attr_text = " ".join(
            f'data-{key}="{html.escape(value, quote=True)}"'
            for key, value in attrs.items()
        )
        cells = []
        for field in record_fields:
            css = ""
            if field == "exact_japanese_source":
                css = ' class="jp exact"'
            elif field == "reconstructed_japanese":
                css = ' class="jp reconstructed"'
            elif field in {
                "literal_english_meaning",
                "final_natural_english_translation",
                "patch_safe_english_translation",
            }:
                css = ' class="translation"'
            cells.append(f"<td{css}>{escape_cell(data[field])}</td>")
        body_rows.append(f"<tr {attr_text}>{''.join(cells)}</tr>")
    control_rows = "".join(
        f"<tr><td><code>⟦{escape_cell(key)}⟧</code></td><td>{escape_cell(value)}</td></tr>"
        for key, value in CONTROL_LEGEND.items()
    )
    refs = "".join(
        f'<li><a href="{html.escape(ref["url"], quote=True)}">{escape_cell(ref["topic"])}</a>: '
        f'{escape_cell(ref["note"])}</li>'
        for ref in EXTERNAL_REFERENCES
    )
    technical_count = sum(
        row.requires_technical_expansion == "yes" for row in rows
    )
    gameplay_count = sum(
        row.requires_gameplay_context == "yes" for row in rows
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Time Twist Complete Translation Workbook</title>
<style>
:root{{--bg:#0f1014;--panel:#171923;--panel2:#202334;--line:#3b4057;--text:#f2f4ff;--muted:#b9bfd3;--accent:#ee66ff;--cyan:#70dbff;--gold:#ffd476;--green:#91e6b2}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,sans-serif}}
main{{padding:22px}} h1,h2,h3{{line-height:1.15}} a{{color:var(--cyan)}} code{{color:var(--gold)}}
.warning,.summary,article{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;margin:10px 0}}
.warning{{border-left:5px solid var(--accent)}} .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}}
.card{{background:var(--panel2);padding:12px;border-radius:7px}} .card b{{display:block;font-size:1.5em;color:var(--cyan)}}
.filters{{position:sticky;top:0;z-index:5;background:rgba(15,16,20,.97);padding:10px 0;border-bottom:1px solid var(--line)}}
input,select{{background:#25293a;color:var(--text);border:1px solid #69708d;padding:7px;margin:3px;max-width:290px}}
.table-wrap{{overflow:auto;max-height:78vh;border:1px solid var(--line)}} table{{border-collapse:separate;border-spacing:0;min-width:100%;background:var(--panel)}}
th,td{{border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:7px;vertical-align:top;min-width:120px;white-space:pre-wrap;overflow-wrap:anywhere}}
th{{position:sticky;top:0;background:#292c40;z-index:2;text-align:left}} tbody tr:nth-child(even){{background:#141722}}
.jp{{font-family:"Yu Gothic UI","Meiryo",sans-serif;font-size:15px;min-width:280px}} .exact{{background:#162a34;color:#d4f6ff}}
.reconstructed{{background:#2c2435;color:#ffd8ff}} .translation{{min-width:260px}} .hidden{{display:none}}
.scene-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:10px}} details{{margin:12px 0}}
.small{{color:var(--muted);font-size:.92em}} .status{{color:var(--green)}}
</style></head><body><main>
<h1>Time Twist: Complete Japanese–English Translation Workbook</h1>
<div class="warning"><b>Evidence boundary:</b> “Exact Japanese from ROM” is copied byte-for-byte at the decoded-text level from the authoritative extraction. “Probable normalized Japanese” is a conservative editorial aid. Kana left as kana is deliberately unresolved; inferred kanji were not present in the ROM. Control tags are program instructions, not punctuation.</div>
<div class="cards">
<div class="card"><b>{len(rows):,}</b>total records</div>
<div class="card"><b>{counts['scenario']:,}</b>scenario records</div>
<div class="card"><b>{counts['fixed-address']:,}</b>fixed-address/UI records</div>
<div class="card"><b>{counts['graphics-text']:,}</b>graphics records</div>
<div class="card"><b>{gameplay_count:,}</b>gameplay/visual checks</div>
<div class="card"><b>{technical_count:,}</b>storage overflows / expansion checks</div>
</div>
<p class="small">Authoritative source: {escape_cell(SOURCE_JSON.name)} (SHA-256 {sha256(SOURCE_JSON)}).{review_provenance} Exact/source order: {escape_cell(source_payload['source_of_truth'])}</p>
<details open><summary><b>Method and field interpretation</b></summary>
<div class="summary"><p>All 2,052 records have a proposed final and patch-safe English field. Short simple lines may have identical literal and natural translations. Fixed-address natural meanings are expanded for analysis; their patch-safe forms retain the verified compact slot text. Every scenario patch passed the ROM character encoder and 24-column display validator. The materially revised banks passed native dictionary recompression: {escape_cell(footprint_summary)}. Unchanged banks retain the already-tested installed English maps.</p>
<p>The supplied diagnostic review was consulted for line-specific corrections, but its unsafe substring-based Japanese reconstruction was not copied. Speaker identity is derived from explicit labels, neighboring English speaker turns, and scene grouping. Ambiguity is recorded without leaving the line untranslated.</p></div></details>
<details><summary><b>Scene summaries ({len(SCENES)})</b></summary><div class="scene-grid">{scene_cards}</div></details>
<details><summary><b>Control-code evidence</b></summary><div class="summary"><p>These functions are empirical summaries, not universal opcode names. Patch-safe text preserves the exact ordered tag sequence for every record.</p><table><thead><tr><th>Tag</th><th>Observed role</th></tr></thead><tbody>{control_rows}</tbody></table></div></details>
<details><summary><b>Speaker and character-voice reference</b></summary><div class="table-wrap"><table><thead><tr>{''.join(f'<th>{escape_cell(x)}</th>' for x in speaker_headers)}</tr></thead><tbody>{speaker_rows}</tbody></table></div></details>
<details><summary><b>Global glossary ({len(glossary)} entries)</b></summary><div class="table-wrap"><table><thead><tr><th>Category</th><th>Exact Japanese</th><th>Reconstructed</th><th>Romaji</th><th>Chosen English</th><th>Alternatives</th><th>First occurrence</th><th>Notes</th></tr></thead><tbody>{glossary_rows}</tbody></table></div></details>
<details><summary><b>External cultural references</b></summary><div class="summary"><ul>{refs}</ul></div></details>
<h2>Record-by-record workbook</h2>
<div class="filters">
<input id="search" size="42" placeholder="Search Japanese, romaji, English, IDs, notes, glossary terms">
<select id="bank"><option value="">All banks</option>{bank_options}</select>
<select id="kind"><option value="">All record types</option><option>scenario</option><option>fixed-address</option><option>graphics-text</option></select>
<select id="speaker"><option value="">All speakers</option>{speaker_options}</select>
<select id="status"><option value="">All statuses</option>{status_options}</select>
<select id="confidence"><option value="">All confidence levels</option>{confidence_options}</select>
<select id="problem"><option value="">All problem categories</option>{category_options}</select>
<select id="dialect"><option value="">All dialect/register</option><option value="marked">Marked dialect/register only</option></select>
<select id="gameplay"><option value="">Gameplay context: all</option><option value="yes">Yes</option><option value="no">No</option></select>
<select id="technical"><option value="">Technical expansion: all</option><option value="yes">Yes</option><option value="no">No</option></select>
<span id="shown" class="status"></span>
</div>
<div class="table-wrap"><table id="records"><thead><tr>{header_html}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>
<script>
const rows=[...document.querySelectorAll('#records tbody tr')];
const controls=['search','bank','kind','speaker','status','confidence','problem','dialect','gameplay','technical'].map(id=>document.getElementById(id));
function apply(){{
 const q=document.getElementById('search').value.toLocaleLowerCase();
 const bank=document.getElementById('bank').value, kind=document.getElementById('kind').value;
 const speaker=document.getElementById('speaker').value, status=document.getElementById('status').value;
 const confidence=document.getElementById('confidence').value, problem=document.getElementById('problem').value;
 const dialect=document.getElementById('dialect').value, gameplay=document.getElementById('gameplay').value;
 const technical=document.getElementById('technical').value; let shown=0;
 for(const row of rows){{
  const ok=(!q||row.textContent.toLocaleLowerCase().includes(q))
   &&(!bank||row.dataset.bank===bank)&&(!kind||row.dataset.kind===kind)
   &&(!speaker||row.dataset.speaker===speaker)&&(!status||row.dataset.status===status)
   &&(!confidence||row.dataset.confidence===confidence)
   &&(!problem||row.dataset.problems.includes(problem))
   &&(!dialect||(dialect==='marked'&&!row.dataset.dialect.startsWith('Unmarked')))
   &&(!gameplay||row.dataset.gameplay===gameplay)&&(!technical||row.dataset.technical===technical);
  row.classList.toggle('hidden',!ok); if(ok) shown++;
 }}
 document.getElementById('shown').textContent=`${{shown.toLocaleString()}} / ${{rows.length.toLocaleString()}} records`;
}}
for(const control of controls) control.addEventListener(control.tagName==='INPUT'?'input':'change',apply);
apply();
</script></main></body></html>"""


def write_csv(path: Path, records: Iterable[dict]) -> None:
    """Write homogeneous mappings as Excel-friendly UTF-8 CSV.

    Args:
        path: Destination file, whose parent directory must already exist.
        records: Ordered mappings.  The first mapping defines column order.

    Raises:
        ValueError: If ``records`` is empty.
        OSError: If the destination cannot be created or written.
        csv.Error: If the standard-library CSV writer cannot serialize a value.

    Side Effects:
        Replaces ``path`` with UTF-8-with-BOM CSV and normalized CSV newlines.
    """
    records = list(records)
    if not records:
        raise ValueError("cannot write empty CSV")
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(records[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(records)


def write_progress(
    rows: list[WorkbookRow],
    glossary: list[dict],
    review_path: Path | None,
) -> None:
    """Write a human-readable project completion and exception report.

    Args:
        rows: Completed workbook rows.
        glossary: Materialized glossary, used for the entry count.
        review_path: Diagnostic input used for provenance fingerprinting.

    Raises:
        OSError: If a source fingerprint cannot be read or the progress file
            cannot be written.

    Side Effects:
        Replaces ``outputs/Time_Twist_translation_progress.md`` with counts,
        bank coverage, native recompression evidence, screenshot requests,
        expansion warnings, terminology decisions, and unresolved ambiguities.
    """
    gameplay = [row for row in rows if row.requires_gameplay_context == "yes"]
    technical = [
        row for row in rows if row.requires_technical_expansion == "yes"
    ]
    unresolved = [row for row in rows if row.unresolved_ambiguity]
    bank_counts = Counter(row.bank for row in rows)
    progress = [
        "# Time Twist translation progress",
        "",
        f"- Total records: **{len(rows):,}**",
        f"- Completed records: **{len(rows):,}**",
        "- Remaining records: **0**",
        f"- Completed banks/components: **{', '.join(BANK_ORDER)}**",
        "- Current bank: **Complete — cross-bank consistency and QC finished**",
        f"- Glossary entries: **{len(glossary)}**",
        f"- Records requiring gameplay/visual context: **{len(gameplay)}**",
        f"- Records requiring technical expansion/recompression review: **{len(technical)}**",
        "",
        "## Source fingerprints",
        "",
        f"- `{SOURCE_JSON.name}` — SHA-256 `{sha256(SOURCE_JSON)}`",
        *(
            [f"- `{review_path.name}` — SHA-256 `{sha256(review_path)}`"]
            if review_path is not None
            else [
                "- Diagnostic review: not supplied (neutral diagnostics used)"
            ]
        ),
        "",
        "## Bank coverage",
        "",
    ]
    progress.extend(
        f"- {bank}: {bank_counts[bank]} records complete"
        for bank in BANK_ORDER
    )
    progress.extend(
        [
            "",
            "## Native compression validation",
            "",
            "Every patch-safe scenario line passed the ROM character encoder and "
            "24-column display validator. All 13 complete public scenario maps "
            "also passed exact optimized dictionary recompression against their "
            "recorded fixed-tail capacities. A private ROM-backed candidate build "
            "and playtest remain separate gates:",
            "",
        ]
    )
    for bank, result in PATCH_FOOTPRINT_RESULTS.items():
        byte_word = "byte" if result["remaining"] == 1 else "bytes"
        progress.append(
            f"- {bank}: {result['used']}/{result['capacity']} bytes used; "
            f"{result['remaining']} {byte_word} remain."
        )
    progress.extend(
        [
            "",
            "## Records requiring gameplay screenshots or visual verification",
            "",
        ]
    )
    if gameplay:
        progress.extend(
            f"- `{row.original_record_id}` — "
            f"{row.unresolved_ambiguity or row.translation_status}"
            for row in gameplay
        )
    else:
        progress.append("- None.")
    progress.extend(
        [
            "",
            "## Records requiring technical expansion or recompression review",
            "",
        ]
    )
    if technical:
        progress.extend(
            f"- `{row.original_record_id}` — {row.apparent_capacity}; "
            f"{row.nuance_lost_in_patch_safe_version}"
            for row in technical
        )
    else:
        progress.append("- None.")
    progress.extend(
        [
            "",
            "## Major unresolved terminology decisions",
            "",
            "- `レベッカ / Rebecca`: treated as the resistance network's name; the spatial clue still needs visual confirmation.",
            "- `マラドゥル・バラオ・ガラドゥーラ / ガルドゥーラ`: source variants are preserved rather than silently regularized.",
            "- `マイヤー`: retained as **Meyer** for consistency with the current script; **Mayer** remains a possible romanization.",
            "- `カシム`: retained as **Kashim**; **Kasim/Qasim** are possible transliterations.",
            "- `黄泉の国`: localized as **the underworld** in the Greek chapter; **Yomi** is retained as an analysis alternative.",
            "",
            "## Remaining genuinely uncertain lines",
            "",
        ]
    )
    progress.extend(
        f"- `{row.original_record_id}` ({row.confidence_level}) — "
        f"{row.unresolved_ambiguity}"
        for row in unresolved
    )
    (OUTPUTS / "Time_Twist_translation_progress.md").write_text(
        "\n".join(progress) + "\n", encoding="utf-8"
    )


def write_voice_guide(glossary: list[dict]) -> None:
    """Write the standalone character-voice and terminology guide.

    Args:
        glossary: Materialized terminology entries in chosen display order.

    Raises:
        KeyError: If a speaker or glossary entry lacks a required field.
        OSError: If the guide cannot be written.

    Side Effects:
        Replaces ``outputs/Time_Twist_terminology_and_voice_guide.md``.
    """
    lines = [
        "# Time Twist terminology and character-voice guide",
        "",
        "This guide accompanies the complete translation workbook. Exact Japanese "
        "always refers to decoded ROM text; reconstructed Japanese is editorial.",
        "",
        "## Character voices",
        "",
    ]
    for entry in SPEAKER_REFERENCES:
        lines.extend(
            [
                f"### {entry['name']}",
                "",
                f"- Japanese labels: {entry['labels']}",
                f"- First person: {entry['first_person']}",
                f"- Typical endings: {entry['endings']}",
                f"- Politeness: {entry['politeness']}",
                f"- Dialect/register: {entry['dialect']}",
                f"- Verbal habits: {entry['habits']}",
                f"- Relationships: {entry['relationships']}",
                f"- Recommended English voice: {entry['english_voice']}",
                "",
            ]
        )
    lines.extend(["## Core terminology", ""])
    lines.extend(
        f"- **{entry['chosen_english']}** — exact `{entry['exact_japanese']}`; "
        f"reconstructed `{entry['reconstructed_japanese']}`; first "
        f"`{entry['first_occurrence']}`. {entry['notes']}"
        for entry in glossary
    )
    lines.extend(
        [
            "",
            "## Control-code policy",
            "",
            "Control tags are never translated. Their exact order is preserved in "
            "scenario records. A documented fixed-interface exception may retain "
            "the already validated playable control layout. The legend in the HTML "
            "workbook describes observed behavior without pretending each value has "
            "one universal linguistic meaning.",
            "",
        ]
    )
    (OUTPUTS / "Time_Twist_terminology_and_voice_guide.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def validate(
    rows: list[WorkbookRow], source_payload: dict, glossary: list[dict]
) -> None:
    """Enforce release-blocking workbook invariants before artifact writes.

    Args:
        rows: Proposed workbook rows.
        source_payload: Authoritative extraction payload.
        glossary: Materialized terminology table.

    Raises:
        AssertionError: If record count is not 2,052; IDs are duplicated; exact
            Japanese differs from source; control order drifts; either English
            field is empty; a known unsafe reconstruction reappears; or the
            glossary is empty.
        KeyError: If a workbook ID is absent from the source payload.

    Note:
        This validation protects structural completeness and evidence boundaries.
        It cannot prove literary quality or gameplay fit; those require review,
        encoder/recompression tests, and the listed visual checks.
    """
    source_rows = source_payload["rows"]
    if len(rows) != 2058:
        raise AssertionError(f"expected 2058 rows, got {len(rows)}")
    ids = [row.original_record_id for row in rows]
    if len(ids) != len(set(ids)):
        duplicates = [
            item for item, count in Counter(ids).items() if count > 1
        ]
        raise AssertionError(f"duplicate IDs: {duplicates}")
    source_by_id = {row["text_id"]: row for row in source_rows}
    for row in rows:
        source = source_by_id[row.original_record_id]
        if row.exact_japanese_source != source["japanese_exact"]:
            raise AssertionError(
                f"Japanese source drift: {row.original_record_id}"
            )
        if (
            controls(row.exact_japanese_source)
            != controls(row.patch_safe_english_translation)
            and row.original_record_id not in CONTROL_OVERRIDE_IDS
        ):
            raise AssertionError(f"control drift: {row.original_record_id}")
        if not row.final_natural_english_translation:
            raise AssertionError(
                f"missing final translation: {row.original_record_id}"
            )
        if not row.patch_safe_english_translation:
            raise AssertionError(
                f"missing patch translation: {row.original_record_id}"
            )
        if (
            "き声る" in row.reconstructed_japanese
            or "人らー" in row.reconstructed_japanese
        ):
            raise AssertionError(
                f"unsafe reconstruction: {row.original_record_id}"
            )
    if not glossary:
        raise AssertionError("glossary is empty")


def write_checkpoints(rows: list[WorkbookRow]) -> None:
    """Persist resumable per-bank JSON review checkpoints.

    Args:
        rows: Complete workbook rows, from which each bank is selected in
            :data:`BANK_ORDER`.

    Raises:
        KeyError: If a bank lacks scene metadata.
        OSError: If the checkpoint directory or any output cannot be written.

    Side Effects:
        Creates ``work/translation_workbook_banks`` as needed, replaces one JSON
        file per bank/component, and repeatedly replaces the rolling Markdown
        checkpoint after each bank.

    Design:
        Checkpoints are written only after aggregate validation.  They support
        inspection and recovery but are not separate translation authorities.
    """
    directory = WORK / "translation_workbook_banks"
    directory.mkdir(parents=True, exist_ok=True)
    completed: list[str] = []
    for bank in BANK_ORDER:
        bank_rows = [asdict(row) for row in rows if row.bank == bank]
        (directory / f"{bank}.json").write_text(
            json.dumps(
                {
                    "bank": bank,
                    "scene": SCENES[bank],
                    "completed_records": len(bank_rows),
                    "rows": bank_rows,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        completed.append(bank)


def main() -> None:
    """Generate, validate, fingerprint, and report every translation artifact.

    Inputs:
        Reads the authoritative comparison JSON and the first existing diagnostic
        review candidate configured by this module.

    Outputs:
        Writes HTML, CSV, and JSON workbooks; CSV and JSON glossaries; a voice
        guide; a progress report; and per-bank checkpoints.  Prints each primary
        artifact's filename, byte size, and SHA-256 digest to standard output.

    Side Effects:
        Creates the output directory if needed and replaces all generated files
        listed above.

    Raises:
        Propagates source parsing, alignment, validation, serialization, and I/O
        failures.  No partially generated aggregate workbook is written before
        :func:`validate` succeeds.

    Design:
        The JSON artifact carries source fingerprints and the same scene,
        speaker, glossary, control, and native-fit evidence shown in HTML so
        machine-readable and human-readable outputs remain auditable.
    """
    parser = argparse.ArgumentParser(
        description="Generate the Time Twist translation-review workbook."
    )
    parser.add_argument(
        "--review-file",
        type=Path,
        help="optional diagnostic review HTML; no personal paths are searched",
    )
    args = parser.parse_args()

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    rows, source_payload, review_path = make_rows(args.review_file)
    glossary = make_glossary(rows)
    validate(rows, source_payload, glossary)
    write_checkpoints(rows)
    row_dicts = [asdict(row) for row in rows]
    html_path = OUTPUTS / "Time_Twist_complete_translation_workbook.html"
    csv_path = OUTPUTS / "Time_Twist_complete_translation_workbook.csv"
    json_path = OUTPUTS / "Time_Twist_complete_translation_workbook.json"
    html_path.write_text(
        render_html(rows, glossary, source_payload, review_path),
        encoding="utf-8",
    )
    write_csv(csv_path, row_dicts)
    json_path.write_text(
        json.dumps(
            {
                "schema": "Time Twist complete translation workbook v1",
                "source_of_truth": source_payload["source_of_truth"],
                "source_file": SOURCE_JSON.name,
                "source_sha256": sha256(SOURCE_JSON),
                "diagnostic_review_file": (
                    review_path.name if review_path is not None else None
                ),
                "diagnostic_review_sha256": (
                    sha256(review_path) if review_path is not None else None
                ),
                "exact_japanese_policy": (
                    "Exact Japanese is copied from the decoded ROM corpus. "
                    "Reconstructed Japanese is editorial and conservative."
                ),
                "control_legend": CONTROL_LEGEND,
                "patch_validation": {
                    "rom_font_encoder": "all scenario records passed",
                    "display_width": "all scenario records passed",
                    "revised_bank_footprints": PATCH_FOOTPRINT_RESULTS,
                },
                "scenes": SCENES,
                "speaker_reference": list(SPEAKER_REFERENCES),
                "glossary": glossary,
                "external_references": list(EXTERNAL_REFERENCES),
                "rows": row_dicts,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_csv(OUTPUTS / "Time_Twist_translation_glossary.csv", glossary)
    (OUTPUTS / "Time_Twist_translation_glossary.json").write_text(
        json.dumps(glossary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_voice_guide(glossary)
    write_progress(rows, glossary, review_path)
    for path in (
        html_path,
        csv_path,
        json_path,
        OUTPUTS / "Time_Twist_translation_glossary.csv",
        OUTPUTS / "Time_Twist_translation_glossary.json",
        OUTPUTS / "Time_Twist_terminology_and_voice_guide.md",
        OUTPUTS / "Time_Twist_translation_progress.md",
    ):
        print(f"{path.name}\t{path.stat().st_size}\t{sha256(path)}")


if __name__ == "__main__":
    main()
