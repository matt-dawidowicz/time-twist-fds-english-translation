"""Generate an analysis-ready Japanese/English corpus for Time Twist.

The Japanese column is always the text decoded from the immutable source
banks.  Linguistic annotations are deliberately kept in separate columns:
they are editorial aids, not claims that kanji or dialect labels appeared in
the original FDS text.
"""

from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from time_twist import ui
from time_twist.scenario import render_symbols
from time_twist.textcodec import split_records


ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
OUTPUTS = ROOT / "outputs"
BANK_ORDER = (
    "TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B",
    "TT4", "TT5", "T25", "TT6A", "TT6B", "TT6C", "TT6D",
)
CONTROL_RE = re.compile(r"\{CTRL:(\d+)\}")


@dataclass(frozen=True)
class ComparisonRow:
    """One stable source record plus machine-generated review annotations."""

    sequence: int
    bank: str
    text_id: str
    kind: str
    source_location: str
    packed_bytes: str
    japanese_exact: str
    japanese_readable: str
    mechanical_romaji: str
    normalized_japanese_aid: str
    current_english_exact: str
    current_english_readable: str
    source_controls: str
    english_controls: str
    control_match: str
    script_profile: str
    voice_dialect_register: str
    orthography_kanji_katakana: str
    comparison_flags: str
    review_priority: str
    proposed_retranslation: str = ""
    reviewer_notes: str = ""


# Strong signals only.  Some forms (especially じゃ and のう) are commonly
# used as fictional old-person speech and must not automatically be assigned
# to a real geographic dialect.
VOICE_MARKERS = (
    ("わたくし", "formal/humble first person; more ceremonious than 'I'"),
    ("わし", "elderly or authoritative masculine first person; character voice, not necessarily regional"),
    ("ぼく", "soft/juvenile masculine first person"),
    ("おれ", "plain-to-rough masculine first person"),
    ("おぬし", "archaic/status-marked second person"),
    ("そなた", "archaic or elevated second person"),
    ("きさま", "hostile/contemptuous second person in modern usage"),
    ("おまえ", "familiar or rough second person; relationship and tone matter"),
    ("でございます", "very polite/formal copula"),
    ("ござる", "archaic/stylized polite speech"),
    ("くだされ", "archaic request form"),
    ("なされ", "archaic or authoritative request/imperative"),
    ("せぬ", "literary/archaic negative"),
    ("とらん", "colloquial/dialectal negative; inspect the verb and speaker"),
    ("ぞい", "stereotyped elderly emphatic ending"),
    ("じゃろ", "old-person/western-style copula; usually fictional voice here"),
    ("じゃ", "old-person/western-style copula; context decides voice versus region"),
    ("のう", "elderly/reflective sentence ending; often fictional voice"),
    ("やで", "strong Kansai-style copula/emphasis"),
    ("やねん", "Kansai explanatory copula"),
    ("だべ", "Tohoku/rural-coded conjectural ending"),
    ("かしら", "traditionally feminine-coded uncertainty/question"),
    ("だわ", "traditionally feminine-coded sentence ending"),
    ("だぜ", "rough masculine emphasis"),
)

HONORIFICS = (
    ("さま", "-sama: high respect, worship, status, or irony"),
    ("どの", "-dono: historical/formal status title"),
    ("ちゃん", "-chan: affection, familiarity, or diminutive tone"),
    ("くん", "-kun: familiar/status-marked address, often toward a boy or junior"),
    ("さん", "-san: ordinary respectful address"),
)

ENDING_MARKERS = (
    (re.compile(r"ぜ(?:[。！？!?…」』]|$)"), "ぜ: rough masculine sentence-final emphasis"),
    (re.compile(r"ぞ(?:[。！？!?…」』]|$)"), "ぞ: forceful assertion or command emphasis"),
    (re.compile(r"まい(?:[。！？!?…」』]|$)"), "まい: literary negative intention or conjecture"),
    (re.compile(r"ぬ(?:[。！？!?…」』]|$)"), "ぬ: literary/archaic negative"),
    (re.compile(r"ばい(?:[。！？!?…」』]|$)"), "ばい: possible Kyushu/Hakata-style assertive ending; verify speaker context"),
)

# These are aids for reconstructing normal modern orthography.  They are not
# substitutions for the source.  Ambiguous readings deliberately show more
# than one candidate.
ORTHOGRAPHY_TERMS = (
    ("れきし", "歴史"), ("じかん", "時間"), ("じだい", "時代"),
    ("みらい", "未来"), ("かこ", "過去"), ("げんざい", "現在"),
    ("せかい", "世界"), ("にほん", "日本"), ("とうきょう", "東京"),
    ("はくぶつかん", "博物館"), ("きょうかい", "教会"),
    ("びょういん", "病院"), ("がっこう", "学校"), ("けんきゅう", "研究"),
    ("はかせ", "博士"), ("せんせい", "先生"), ("しんぶん", "新聞"),
    ("せんそう", "戦争"), ("へいし", "兵士"), ("しけい", "死刑"),
    ("どれい", "奴隷"), ("じゆう", "自由"), ("へいわ", "平和"),
    ("しゅうきょう", "宗教"), ("しんこう", "信仰"), ("せいしょ", "聖書"),
    ("きせき", "奇跡"), ("よげん", "予言"), ("うらない", "占い"),
    ("あくま", "悪魔"), ("かみさま", "神様"), ("たましい", "魂"),
    ("いのち", "命"), ("こころ", "心"), ("からだ", "体"),
    ("おとこ", "男"), ("おんな", "女"), ("おんなのこ", "女の子"),
    ("おとこのこ", "男の子"), ("こども", "子供"), ("ひと", "人"),
    ("おとな", "大人"), ("おや", "親"), ("ちち", "父"), ("はは", "母"),
    ("むすこ", "息子"), ("むすめ", "娘"), ("なまえ", "名前"),
    ("ことば", "言葉"), ("こえ", "声"), ("はなし", "話"),
    ("ほんとう", "本当"), ("だいじ", "大事"), ("だいじょうぶ", "大丈夫"),
    ("しぬ", "死ぬ"), ("ころす", "殺す"), ("たすける", "助ける"),
    ("いきる", "生きる"), ("うまれる", "生まれる"), ("あう", "会う/遭う/合う"),
    ("みる", "見る/診る"), ("きく", "聞く/聴く/訊く"),
    ("いう", "言う"), ("おもう", "思う"), ("しる", "知る"),
    ("わかる", "分かる"), ("かえる", "帰る/変える/替える"),
    ("とる", "取る/撮る/採る"), ("なおす", "直す/治す"),
    ("かみ", "神/紙/髪"), ("はし", "橋/端/箸"),
)

KATAKANA_CANDIDATES = (
    ("しもん", "シモン (Simon)"), ("ひとらー", "ヒトラー (Hitler)"),
    ("りんかーん", "リンカーン (Lincoln)"), ("じゃんぬ", "ジャンヌ (Jeanne)"),
    ("ありすとてれす", "アリストテレス (Aristotle)"),
    ("いえす", "イエス (Jesus or 'yes'; context is essential)"),
    ("きりすと", "キリスト (Christ)"), ("えるされむ", "エルサレム (Jerusalem)"),
    ("べつれへむ", "ベツレヘム (Bethlehem)"), ("ろーま", "ローマ (Rome)"),
    ("どいつ", "ドイツ (Germany)"), ("あめりか", "アメリカ (America)"),
    ("てれび", "テレビ"), ("こんぴゅーた", "コンピュータ"),
    ("たいむ", "タイム"), ("べると", "ベルト"), ("でびる", "デビル"),
    ("こんそめ", "コンソメ"), ("みゅーじあむ", "ミュージアム"),
)


def _read_source_document(bank: str) -> dict:
    """Load the decoded scenario document for a named bank."""

    return json.loads((WORK / "translated_scripts" / f"{bank}.json").read_text(encoding="utf-8"))


def _source_path(document: dict) -> Path:
    """Resolve a decoded document's source bank, including relocated extracts."""

    path = Path(document["source"])
    if path.exists():
        return path
    candidates = list(WORK.glob(f"extracted_*/*_{path.name.split('_', 2)[-1]}"))
    if len(candidates) != 1:
        raise FileNotFoundError(f"cannot resolve source bank {path}")
    return candidates[0]


def _readable(text: str) -> str:
    """Expose embedded controls as visible, non-linguistic review markers."""

    return CONTROL_RE.sub(lambda match: f" ⟦CTRL:{match.group(1)}⟧ ", text).strip()


def _controls(text: str) -> tuple[str, ...]:
    """Return control-code values in their exact source order."""

    return tuple(CONTROL_RE.findall(text))


def _script_profile(text: str) -> str:
    """Summarize the visible text's hiragana, katakana, kanji, and Latin use."""

    clean = CONTROL_RE.sub("", text)
    counts = Counter()
    for character in clean:
        codepoint = ord(character)
        if 0x3040 <= codepoint <= 0x309F:
            counts["hiragana"] += 1
        elif 0x30A0 <= codepoint <= 0x30FF:
            counts["katakana"] += 1
        elif 0x4E00 <= codepoint <= 0x9FFF:
            counts["kanji"] += 1
        elif character.isascii() and character.isalpha():
            counts["Latin"] += 1
        elif character.isdigit():
            counts["digits"] += 1
    parts = [f"{name}:{counts[name]}" for name in ("hiragana", "katakana", "kanji", "Latin", "digits")]
    if counts["hiragana"] and not counts["katakana"] and not counts["kanji"]:
        parts.append("phonetic hiragana orthography")
    return "; ".join(parts)


ROMAJI_BASIC = {
    "あ":"a","い":"i","う":"u","え":"e","お":"o",
    "か":"ka","き":"ki","く":"ku","け":"ke","こ":"ko",
    "が":"ga","ぎ":"gi","ぐ":"gu","げ":"ge","ご":"go",
    "さ":"sa","し":"shi","す":"su","せ":"se","そ":"so",
    "ざ":"za","じ":"ji","ず":"zu","ぜ":"ze","ぞ":"zo",
    "た":"ta","ち":"chi","つ":"tsu","て":"te","と":"to",
    "だ":"da","ぢ":"ji","づ":"zu","で":"de","ど":"do",
    "な":"na","に":"ni","ぬ":"nu","ね":"ne","の":"no",
    "は":"ha","ひ":"hi","ふ":"fu","へ":"he","ほ":"ho",
    "ば":"ba","び":"bi","ぶ":"bu","べ":"be","ぼ":"bo",
    "ぱ":"pa","ぴ":"pi","ぷ":"pu","ぺ":"pe","ぽ":"po",
    "ま":"ma","み":"mi","む":"mu","め":"me","も":"mo",
    "や":"ya","ゆ":"yu","よ":"yo",
    "ら":"ra","り":"ri","る":"ru","れ":"re","ろ":"ro",
    "わ":"wa","を":"o","ん":"n","ゔ":"vu",
    "ぁ":"a","ぃ":"i","ぅ":"u","ぇ":"e","ぉ":"o",
}
ROMAJI_DIGRAPHS = {
    "きゃ":"kya","きゅ":"kyu","きょ":"kyo","ぎゃ":"gya","ぎゅ":"gyu","ぎょ":"gyo",
    "しゃ":"sha","しゅ":"shu","しょ":"sho","じゃ":"ja","じゅ":"ju","じょ":"jo",
    "ちゃ":"cha","ちゅ":"chu","ちょ":"cho","にゃ":"nya","にゅ":"nyu","にょ":"nyo",
    "ひゃ":"hya","ひゅ":"hyu","ひょ":"hyo","びゃ":"bya","びゅ":"byu","びょ":"byo",
    "ぴゃ":"pya","ぴゅ":"pyu","ぴょ":"pyo","みゃ":"mya","みゅ":"myu","みょ":"myo",
    "りゃ":"rya","りゅ":"ryu","りょ":"ryo","ふぁ":"fa","ふぃ":"fi","ふぇ":"fe","ふぉ":"fo",
    "てぃ":"ti","でぃ":"di","とぅ":"tu","どぅ":"du","うぃ":"wi","うぇ":"we","うぉ":"wo",
}


def _to_hiragana(character: str) -> str:
    """Map a katakana code point to hiragana for mechanical romanization."""

    codepoint = ord(character)
    if 0x30A1 <= codepoint <= 0x30F6:
        return chr(codepoint - 0x60)
    return character


def _romanize(text: str) -> str:
    """Produce deterministic review-aid romaji without claiming full parsing."""

    clean = CONTROL_RE.sub(" / ", text)
    kana = "".join(_to_hiragana(character) for character in clean)
    output: list[str] = []
    geminate = False
    index = 0
    while index < len(kana):
        character = kana[index]
        if character == "っ":
            geminate = True
            index += 1
            continue
        pair = kana[index:index + 2]
        syllable = ROMAJI_DIGRAPHS.get(pair)
        if syllable is not None:
            index += 2
        else:
            syllable = ROMAJI_BASIC.get(character, character)
            index += 1
        if character == "ー" and output:
            previous = output[-1]
            vowel = next((value for value in reversed(previous) if value in "aeiou"), "")
            output.append(vowel)
            continue
        if geminate and syllable and syllable[0].isalpha():
            if syllable.startswith("ch"):
                syllable = "t" + syllable
            else:
                syllable = syllable[0] + syllable
            geminate = False
        output.append(syllable)
    return "".join(output)


def _voice_notes(text: str) -> tuple[str, ...]:
    """Detect boundary-aware pronoun, register, and role-language signals."""

    clean = CONTROL_RE.sub("", text)
    notes: list[str] = []
    for marker, explanation in VOICE_MARKERS:
        found = marker in clean
        if marker == "じゃ":
            # Do not mistake the opening of じゃんぬ (Jeanne) for a copula.
            found = bool(re.search(r"じゃ(?!んぬ)", clean))
        elif marker == "のう":
            # Avoid ordinary words such as きのう and のうりょく.
            found = bool(re.search(r"のう(?=[\s。！？!?…／」』]|$)", clean))
        if found:
            notes.append(f"{marker}: {explanation}")
    for marker, explanation in HONORIFICS:
        honorific_source = clean
        if marker == "さま":
            honorific_source = honorific_source.replace("きさま", "").replace("さまざま", "")
        elif marker == "さん":
            honorific_source = honorific_source.replace("たくさん", "")
            honorific_source = re.sub(r"さんにん", "", honorific_source)
        if re.search(re.escape(marker) + r"(?=[\s、。！？!?…／」』はがをにとのへも]|$)", honorific_source):
            notes.append(f"{marker}: {explanation}")
    for pattern, explanation in ENDING_MARKERS:
        if explanation.startswith("ぜ:") and "だぜ" in clean:
            continue
        if pattern.search(clean):
            notes.append(explanation)
    if re.search(r"(?:です|ます)(?:[。！？!?…」』]|$)", clean):
        notes.append("です/ます: polite register")
    return tuple(dict.fromkeys(notes))


def _orthography_notes(text: str) -> tuple[str, str]:
    """Return exact kana plus conservative kanji/katakana review suggestions."""

    clean = CONTROL_RE.sub("", text)
    candidates: list[str] = []
    searchable = clean
    # First mask foreign names/loans, then ordinary lexemes.  Masking and
    # longest-first matching prevent false restorations such as 人らー for
    # ひとらー (Hitler) or 女の子のこ for おんなのこ.
    for reading, spelling in sorted(KATAKANA_CANDIDATES, key=lambda item: len(item[0]), reverse=True):
        if reading in searchable:
            candidates.append(f"{reading} → {spelling}")
            searchable = searchable.replace(reading, " " * len(reading))
    for reading, spelling in sorted(ORTHOGRAPHY_TERMS, key=lambda item: len(item[0]), reverse=True):
        if len(reading) <= 2:
            pattern = re.compile(
                r"(?<![ぁ-ん])" + re.escape(reading)
                + r"(?=[はがをにとのへもでよか、。！？!?…／」』\s]|$)"
            )
            match = pattern.search(searchable)
        else:
            match = re.search(re.escape(reading), searchable)
        if match:
            candidates.append(f"{reading} → {spelling}")
            searchable = searchable[:match.start()] + " " * (match.end() - match.start()) + searchable[match.end():]
    if not candidates and any(0x3040 <= ord(character) <= 0x309F for character in clean):
        candidates.append("Source suppresses normal kanji/katakana distinctions; restore only with context")
    # Do not synthesize a kanji sentence: replacing substrings without a full
    # morphological parse can silently invent the wrong word.  The adjacent
    # candidate column carries the safe, reviewable suggestions.
    return clean, tuple(dict.fromkeys(candidates))


def _comparison_flags(japanese: str, english: str, kind: str, packed_bytes: str) -> tuple[str, ...]:
    """Identify control, layout, numeral, and punctuation checks for a row."""

    flags: list[str] = []
    source_controls = _controls(japanese)
    english_controls = _controls(english)
    if source_controls != english_controls:
        flags.append("control sequence differs")
    source_numbers = re.findall(r"\d+", CONTROL_RE.sub("", japanese))
    if source_numbers:
        flags.append(f"source numerals {source_numbers}; verify dates/counts and Japanese ordering")
    if kind == "fixed-address":
        flags.append(f"fixed-address label; {packed_bytes} packed bytes")
    if re.search(r"\b[A-Z]{1,5}\b", english) and kind == "fixed-address":
        flags.append("compact uppercase label may be an abbreviation")
    if "  " in english:
        flags.append("English contains padding used for layout or packed size")
    if "……" in japanese or "…" in japanese:
        flags.append("ellipsis carries timing/hesitation tone")
    return tuple(flags)


def _priority(kind: str, voice: tuple[str, ...], orthography: tuple[str, ...], flags: tuple[str, ...]) -> str:
    """Assign a review priority from explicit, explainable warning signals."""

    score = 0
    score += min(4, len(voice) * 2)
    score += 2 if any("/" in note or "context" in note for note in orthography) else 0
    score += 3 if any("control sequence" in flag for flag in flags) else 0
    score += 2 if kind == "fixed-address" else 0
    score += 1 if any("abbreviation" in flag or "padding" in flag for flag in flags) else 0
    return "high" if score >= 5 else "medium" if score >= 2 else "low"


def _make_row(
    *, sequence: int, bank: str, text_id: str, kind: str,
    source_location: str, packed_bytes: str, japanese: str, english: str,
) -> ComparisonRow:
    """Construct a fully annotated comparison row from one source record."""

    voice = _voice_notes(japanese)
    normalized, orthography = _orthography_notes(japanese)
    flags = _comparison_flags(japanese, english, kind, packed_bytes)
    source_controls = _controls(japanese)
    english_controls = _controls(english)
    return ComparisonRow(
        sequence=sequence,
        bank=bank,
        text_id=text_id,
        kind=kind,
        source_location=source_location,
        packed_bytes=packed_bytes,
        japanese_exact=japanese,
        japanese_readable=_readable(japanese),
        mechanical_romaji=_romanize(japanese),
        normalized_japanese_aid=normalized,
        current_english_exact=english,
        current_english_readable=_readable(english),
        source_controls=",".join(source_controls),
        english_controls=",".join(english_controls),
        control_match="yes" if source_controls == english_controls else "NO",
        script_profile=_script_profile(japanese),
        voice_dialect_register=" | ".join(voice),
        orthography_kanji_katakana=" | ".join(orthography),
        comparison_flags=" | ".join(flags),
        review_priority=_priority(kind, voice, orthography, flags),
    )


def _scenario_rows(start_sequence: int) -> list[ComparisonRow]:
    """Collect all scenario records and verify translation-map coverage."""

    rows: list[ComparisonRow] = []
    sequence = start_sequence
    for bank in BANK_ORDER:
        source = _read_source_document(bank)
        translations = json.loads((WORK / "translations" / f"{bank}.json").read_text(encoding="utf-8"))
        seen: set[str] = set()
        for group in source["groups"]:
            for record in group["records"]:
                text_id = record["id"]
                if text_id not in translations:
                    raise ValueError(f"missing English translation for {text_id}")
                seen.add(text_id)
                rows.append(_make_row(
                    sequence=sequence,
                    bank=bank,
                    text_id=text_id,
                    kind="scenario",
                    source_location=f"group {group['group']} @ {group['address']}; record {record['record']}",
                    packed_bytes="group-compressed",
                    japanese=record["japanese"],
                    english=translations[text_id],
                ))
                sequence += 1
        extra = set(translations) - seen
        if extra:
            raise ValueError(f"translation map has unknown IDs for {bank}: {sorted(extra)}")
    return rows


FIXED_SPECS = (
    ("TT1B", ui.TT1B_FIXED_TEXT_START_OFFSET, ui.TT1B_FIXED_TEXT_END_OFFSET, ui.TT1B_FIXED_TEXT_RECORDS),
    ("TT2", ui.TT2_FIXED_TEXT_START_OFFSET, ui.TT2_FIXED_TEXT_END_OFFSET, ui.TT2_FIXED_TEXT_RECORDS),
    ("T22", ui.T22_FIXED_TEXT_START_OFFSET, ui.T22_FIXED_TEXT_END_OFFSET, ui.T22_FIXED_TEXT_RECORDS),
    ("TT3A", ui.TT3A_FIXED_TEXT_START_OFFSET, ui.TT3A_FIXED_TEXT_END_OFFSET, ui.TT3A_FIXED_TEXT_RECORDS),
    ("TT3B", ui.TT3B_FIXED_TEXT_START_OFFSET, ui.TT3B_FIXED_TEXT_END_OFFSET, ui.TT3B_FIXED_TEXT_RECORDS),
    ("TT4", ui.TT4_FIXED_TEXT_START_OFFSET, ui.TT4_FIXED_TEXT_END_OFFSET, ui.TT4_FIXED_TEXT_RECORDS),
    ("TT5", ui.TT5_FIXED_TEXT_START_OFFSET, ui.TT5_FIXED_TEXT_END_OFFSET, ui.TT5_FIXED_TEXT_RECORDS),
    ("T25", ui.T25_FIXED_TEXT_START_OFFSET, ui.T25_FIXED_TEXT_END_OFFSET, ui.T25_FIXED_TEXT_RECORDS),
    ("TT6A", ui.TT6A_FIXED_TEXT_START_OFFSET, ui.TT6A_FIXED_TEXT_END_OFFSET, ui.TT6A_FIXED_TEXT_RECORDS),
    ("TT6B", ui.TT6B_FIXED_TEXT_START_OFFSET, ui.TT6B_FIXED_TEXT_END_OFFSET, ui.TT6B_FIXED_TEXT_RECORDS),
    ("TT6C", ui.TT6C_FIXED_TEXT_START_OFFSET, ui.TT6C_FIXED_TEXT_END_OFFSET, ui.TT6C_FIXED_TEXT_RECORDS),
)


def _fixed_rows(start_sequence: int) -> list[ComparisonRow]:
    """Decode fixed-address record tables through their native dictionaries."""

    rows: list[ComparisonRow] = []
    sequence = start_sequence
    for bank, start, end, english_records in FIXED_SPECS:
        source_document = _read_source_document(bank)
        data = _source_path(source_document).read_bytes()
        dictionary = ui._tt2_dictionary(data)
        packed = data[start:end]
        records, parsed_end = split_records(packed, limit=len(english_records))
        if parsed_end != len(packed):
            raise ValueError(f"{bank} fixed table did not consume its source range")
        starts = ui._record_starts(packed, len(records))
        ends = (*starts[1:], len(packed))
        for index, (record, english, record_start, record_end) in enumerate(zip(records, english_records, starts, ends)):
            japanese = render_symbols(record, dictionary)
            size = record_end - record_start
            rows.append(_make_row(
                sequence=sequence,
                bank=bank,
                text_id=f"{bank}/fixed/r{index}",
                kind="fixed-address",
                source_location=f"${0xA200 + start + record_start:04X}",
                packed_bytes=str(size),
                japanese=japanese,
                english=english.rstrip(),
            ))
            sequence += 1
    return rows


def _single_packed_japanese(packed: bytes) -> str:
    """Decode a byte string that must contain exactly one dictionary-free record."""

    records, end = split_records(packed, limit=1)
    if end != len(packed):
        raise ValueError("single UI record has trailing bytes")
    return render_symbols(records[0], ())


def _ui_rows(start_sequence: int) -> list[ComparisonRow]:
    """Collect quiz, prompt, disk, title, and direct-boot interface records."""

    rows: list[ComparisonRow] = []
    sequence = start_sequence
    tt1a_sections = (
        ("blood", ui.TT1A_BLOOD_TYPE_PATCHES),
        ("month", ui.TT1A_MONTH_PATCHES),
        ("confirmation", ui.TT1A_CONFIRMATION_PATCHES),
    )
    for section, records in tt1a_sections:
        for index, (offset, packed, english) in enumerate(records):
            rows.append(_make_row(
                sequence=sequence, bank="TT1A", text_id=f"TT1A/{section}/r{index}",
                kind="fixed-address", source_location=f"${0xA200 + offset:04X}",
                packed_bytes=str(len(packed)), japanese=_single_packed_japanese(packed),
                english=english.rstrip(),
            ))
            sequence += 1

    ui_specs = [
        ("NOV2", "NOV2/start", 0x6000 + ui.START_PROMPT_OFFSET, ui.ORIGINAL_START_PROMPT, "START"),
        ("NOV4", "NOV4/start", 0xA200 + ui.NOV4_START_PROMPT_OFFSET, ui.ORIGINAL_START_PROMPT, "START"),
        ("NOV2", "NOV2/wait", 0x6000 + ui.WAIT_PROMPT_OFFSET, ui.ORIGINAL_WAIT_PROMPT, "PLEASE WAIT..."),
    ]
    ui_specs.extend(
        ("NOV2", f"NOV2/disk/r{index}", 0x6000 + offset, packed, english)
        for index, (offset, packed, english) in enumerate((*ui.DISK_PROMPT_PATCHES, *ui.WRONG_DISK_PATCHES))
    )
    for bank, text_id, address, packed, english in ui_specs:
        rows.append(_make_row(
            sequence=sequence, bank=bank, text_id=text_id, kind="fixed-address",
            source_location=f"${address:04X}", packed_bytes=str(len(packed)),
            japanese=_single_packed_japanese(packed), english=english.rstrip(),
        ))
        sequence += 1

    graphic_rows = (
        ("TITLE", "TITLE/wordmark", "graphics-only", "タイムツイスト", "TIME TWIST"),
        ("TITLE", "TITLE/subtitle", "graphics-only", "歴史のかたすみで……", "On the Outskirts of History..."),
        ("SON-KOUH", "SON-KOUH/direct-boot", "graphics-only", "ぜんぺんディスクから ロードしてください。", "PLEASE START WITH PART 1"),
    )
    for bank, text_id, location, japanese, english in graphic_rows:
        rows.append(_make_row(
            sequence=sequence, bank=bank, text_id=text_id, kind="graphics-text",
            source_location=location, packed_bytes="n/a", japanese=japanese, english=english,
        ))
        sequence += 1
    return rows


def build_rows() -> list[ComparisonRow]:
    """Build the ordered corpus and reject duplicate stable record IDs."""

    scenario = _scenario_rows(1)
    fixed = _fixed_rows(len(scenario) + 1)
    interface = _ui_rows(len(scenario) + len(fixed) + 1)
    rows = scenario + fixed + interface
    if len({row.text_id for row in rows}) != len(rows):
        raise ValueError("comparison corpus contains duplicate text IDs")
    return rows


def _write_tsv(rows: list[ComparisonRow], path: Path) -> None:
    """Write spreadsheet-friendly UTF-8 TSV with a BOM."""

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ComparisonRow.__dataclass_fields__, dialect="excel-tab")
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def _write_json(rows: list[ComparisonRow], path: Path) -> None:
    """Write the lossless canonical comparison corpus as UTF-8 JSON."""

    payload = {
        "schema": "time-twist-bilingual-comparison-v1",
        "source_of_truth": "japanese_exact is decoded from immutable Japanese banks; annotations are editorial aids",
        "rows": [asdict(row) for row in rows],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _cell(value: object) -> str:
    """Escape a value for safe insertion into the generated HTML table."""

    return html.escape(str(value)).replace("\n", "<br>")


def _write_html(rows: list[ComparisonRow], path: Path) -> None:
    """Write the searchable human-review table."""

    counts = Counter(row.kind for row in rows)
    priorities = Counter(row.review_priority for row in rows)
    body_rows = []
    for row in rows:
        notes = "<br>".join(filter(None, (
            _cell(row.voice_dialect_register),
            _cell(row.orthography_kanji_katakana),
            _cell(row.comparison_flags),
        )))
        body_rows.append(
            f'<tr data-bank="{_cell(row.bank)}" data-kind="{_cell(row.kind)}" '
            f'data-priority="{_cell(row.review_priority)}">'
            f'<td>{row.sequence}</td><td><b>{_cell(row.bank)}</b><br><code>{_cell(row.text_id)}</code><br>'
            f'<small>{_cell(row.kind)}; {_cell(row.source_location)}; {_cell(row.packed_bytes)} bytes</small></td>'
            f'<td lang="ja">{_cell(row.japanese_readable)}<br><small>{_cell(row.mechanical_romaji)}</small></td>'
            f'<td lang="ja">{_cell(row.normalized_japanese_aid)}</td>'
            f'<td>{_cell(row.current_english_readable)}</td>'
            f'<td>{notes}</td><td class="priority {row.review_priority}">{_cell(row.review_priority)}</td></tr>'
        )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Time Twist Japanese-English Script Comparison</title>
<style>
body{{font:15px/1.45 system-ui,sans-serif;margin:24px;background:#111;color:#eee}} h1{{margin-bottom:.2em}}
.warning{{max-width:1100px;padding:12px 16px;background:#2b2137;border-left:5px solid #d85cff}}
.controls{{position:sticky;top:0;background:#111;padding:12px 0;z-index:2}} input,select{{padding:7px;margin-right:8px;background:#222;color:#fff;border:1px solid #666}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #444;padding:8px;vertical-align:top}} th{{position:sticky;top:62px;background:#252035;text-align:left}}
tr:nth-child(even){{background:#181818}} td:nth-child(3),td:nth-child(4),td:nth-child(5){{min-width:270px;white-space:pre-wrap}}
small{{color:#aaa}} code{{color:#f09cff}} .priority{{font-weight:bold}} .high{{color:#ff7e7e}} .medium{{color:#ffd36b}} .low{{color:#8de39b}}
</style></head><body>
<h1>Time Twist — complete Japanese/English comparison</h1>
<p>{len(rows):,} entries: {counts['scenario']:,} scenario records, {counts['fixed-address']:,} fixed-address/UI records, and {counts['graphics-text']:,} graphics-text entries. Review priorities: {priorities['high']:,} high, {priorities['medium']:,} medium, {priorities['low']:,} low.</p>
<div class="warning"><b>Evidence boundary:</b> “Japanese source” is exact decoded game text. “Normalized Japanese” and the linguistic notes are review aids inferred from phonetic kana; they are not hidden kanji recovered from the ROM. The game deliberately writes most dialogue in hiragana, so homophones, speaker identity, and scene context must decide many restorations. Mechanical romaji is navigational, not a translation. Fixed-address labels often had to fit slots as small as two to five packed bytes.</div>
<div class="controls"><input id="search" size="48" placeholder="Search Japanese, English, ID, or notes"><select id="bank"><option value="">All banks</option>{''.join(f'<option>{bank}</option>' for bank in (*BANK_ORDER, 'NOV2', 'NOV4', 'TITLE', 'SON-KOUH'))}</select><select id="priority"><option value="">All priorities</option><option>high</option><option>medium</option><option>low</option></select><span id="shown"></span></div>
<table><thead><tr><th>#</th><th>ID/source</th><th>Japanese source + romaji</th><th>Normalized-Japanese aid</th><th>Current English</th><th>Dialect/register/orthography/QA</th><th>Priority</th></tr></thead><tbody>{''.join(body_rows)}</tbody></table>
<script>
const rows=[...document.querySelectorAll('tbody tr')], q=document.querySelector('#search'), b=document.querySelector('#bank'), p=document.querySelector('#priority'), s=document.querySelector('#shown');
function filter(){{const needle=q.value.toLowerCase();let count=0;for(const row of rows){{const show=(!needle||row.innerText.toLowerCase().includes(needle))&&(!b.value||row.dataset.bank===b.value)&&(!p.value||row.dataset.priority===p.value);row.hidden=!show;if(show)count++}}s.textContent=`${{count.toLocaleString()}} shown`;}} [q,b,p].forEach(x=>x.addEventListener('input',filter));filter();
</script></body></html>"""
    path.write_text(document, encoding="utf-8")


def _write_guide(rows: list[ComparisonRow], path: Path) -> None:
    """Write corpus counts, caveats, and a prioritized review checklist."""

    banks = Counter(row.bank for row in rows if row.kind == "scenario")
    priority = Counter(row.review_priority for row in rows)
    voice_rows = sum(bool(row.voice_dialect_register) for row in rows)
    control_mismatches = [row.text_id for row in rows if row.control_match == "NO"]
    guide = f"""# Time Twist bilingual script comparison

This package is designed for a second-pass localization review, not merely a proof that English fits in the ROM.

## Files

- `Time Twist Japanese-English script comparison.html` — searchable human review interface.
- `Time Twist Japanese-English script comparison.tsv` — Excel/LibreOffice-ready UTF-8 worksheet with blank `proposed_retranslation` and `reviewer_notes` columns.
- `Time Twist Japanese-English script comparison.json` — structured corpus for scripts, LLM analysis, or version-controlled edits.

## Coverage

- {sum(banks.values()):,} scenario records across all 13 banks: {', '.join(f'{bank} {banks[bank]}' for bank in BANK_ORDER)}.
- {sum(row.kind == 'fixed-address' for row in rows):,} fixed-address command, object, quiz, personality-menu, and engine-interface records.
- {sum(row.kind == 'graphics-text' for row in rows):,} recovered graphics-text entries for the title and Kouhen direct-boot warning.
- {voice_rows:,} entries carry at least one detected voice, dialect, honorific, or register marker.
- Review queue: {priority['high']:,} high, {priority['medium']:,} medium, {priority['low']:,} low.
- Control-sequence mismatches: {len(control_mismatches)} ({', '.join(control_mismatches) if control_mismatches else 'none'}).

## How to interpret the Japanese

The game intentionally renders nearly all story text in hiragana. That erases distinctions normally carried by kanji and katakana. For example, `かみ` can mean 神 (god), 紙 (paper), or 髪 (hair), while foreign names such as `しもん` would normally be written シモン. The `normalized_japanese_aid` and `orthography_kanji_katakana` columns expose such candidates without rewriting the source.

Dialect tags are conservative. Forms such as `じゃ`, `のう`, and `わし` often create a fictional elderly voice rather than proving a geographic dialect. `やで` is a much stronger Kansai signal; sentence-final `ばい` may suggest Kyushu/Hakata speech. Pronouns and honorifics are called out because English frequently drops status, age, gender presentation, intimacy, or hostility that Japanese encodes directly.

## Recommended review order

1. Filter `review_priority` to `high` and review in scene order, with screenshots or a live playthrough for speaker identity.
2. Decide voice rules per recurring speaker before rewriting isolated lines.
3. Treat every slash-separated kanji candidate as unresolved until context selects it.
4. Keep `{{CTRL:n}}` sequences in the same order unless the renderer behavior is deliberately changed.
5. Draft natural English first, then fit it into the bank and fixed-record constraints. Do not allow a tiny menu slot to dictate the unconstrained literary translation.
6. Store the unconstrained preferred translation in `proposed_retranslation`; derive a separate ROM-safe rendering afterward.

## Known boundary

The staff roll is graphics/program data rather than part of the decoded packed-text corpus. Personal names in the credits have not been optically transcribed into this worksheet. The title and direct-boot warning are included because their source wording is already recovered and verified.
"""
    path.write_text(guide, encoding="utf-8")


def main() -> None:
    """Regenerate every bilingual comparison artifact from source documents."""

    rows = build_rows()
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    _write_tsv(rows, OUTPUTS / "Time Twist Japanese-English script comparison.tsv")
    _write_json(rows, OUTPUTS / "Time Twist Japanese-English script comparison.json")
    _write_html(rows, OUTPUTS / "Time Twist Japanese-English script comparison.html")
    _write_guide(rows, OUTPUTS / "Time Twist bilingual comparison guide.md")
    print(f"wrote {len(rows)} comparison rows")


if __name__ == "__main__":
    main()
