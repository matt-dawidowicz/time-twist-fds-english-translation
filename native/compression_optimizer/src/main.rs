use std::cmp::Ordering;
use std::collections::HashMap;
use std::collections::hash_map::Entry;
use std::io::{self, Read};
use std::process;

const PROTOCOL: &str = "TIME_TWIST_COMPRESSION_V1";
const RESULT_PROTOCOL: &str = "TIME_TWIST_COMPRESSION_RESULT_V1";
const MAX_CANDIDATE_TOKENS: usize = 32;
const MAX_CANDIDATES_TO_EVALUATE: usize = 200;
const DEFAULT_BEAM_WIDTH: usize = 4;
const DEFAULT_BEAM_BRANCH_FACTOR: usize = 4;
const EXTENDED_BEAM_WIDTH: usize = 12;
const EXTENDED_BEAM_BRANCH_FACTOR: usize = 8;
const EXTENDED_BEAM_HEADROOM_BYTES: isize = 16;

type Token = u16;
type Record = Vec<Token>;
type Group = Vec<Record>;
type Groups = Vec<Group>;
type Dictionary = Vec<Record>;

#[derive(Clone, Debug, PartialEq, Eq)]
struct ResultState {
    groups: Groups,
    dictionary: Dictionary,
}

#[derive(Clone)]
struct BeamState {
    size: usize,
    groups: Groups,
    dictionary: Dictionary,
}

#[derive(Clone)]
struct CandidateCount {
    count: usize,
    order: usize,
}

#[derive(Clone)]
struct RankedCandidate {
    saving: isize,
    order: usize,
    candidate: Record,
}

struct Problem {
    groups: Groups,
    required_entries: Dictionary,
    max_entries: usize,
    max_bytes: Option<usize>,
    requires_full_dictionary: bool,
}

struct Lines<'a> {
    lines: std::str::Lines<'a>,
}

impl<'a> Lines<'a> {
    fn new(input: &'a str) -> Self {
        Self {
            lines: input.lines(),
        }
    }

    fn next(&mut self) -> Result<&'a str, String> {
        self.lines
            .next()
            .ok_or_else(|| "unexpected end of optimizer protocol".to_string())
    }

    fn value(&mut self, prefix: &str) -> Result<&'a str, String> {
        let line = self.next()?;
        line.strip_prefix(prefix)
            .map(str::trim)
            .ok_or_else(|| format!("expected {prefix:?}, got {line:?}"))
    }
}

fn token_kind(token: Token) -> u8 {
    (token >> 8) as u8
}

fn token_value(token: Token) -> u8 {
    (token & 0x00ff) as u8
}

fn is_literal(token: Token) -> bool {
    matches!(token_kind(token), 0 | 1)
}

fn dictionary_token(value: usize) -> Result<Token, String> {
    if !(1..=255).contains(&value) {
        return Err(format!("dictionary token {value} is out of range"));
    }
    Ok(0x0200 | value as Token)
}

fn symbol_bit_length(token: Token) -> Result<usize, String> {
    match token_kind(token) {
        0 => {
            if token_value(token) > 47 {
                Err(format!("common token {token:04X} is out of range"))
            } else {
                Ok(6)
            }
        }
        1 => {
            if token_value(token) > 63 {
                Err(format!("extended token {token:04X} is out of range"))
            } else {
                Ok(9)
            }
        }
        2 => {
            if token_value(token) == 0 || token_value(token) > 68 {
                Err(format!("dictionary token {token:04X} is out of range"))
            } else {
                Ok(9)
            }
        }
        3 => {
            if token_value(token) > 7 || token_value(token) == 5 {
                Err(format!("control token {token:04X} is out of range"))
            } else {
                Ok(7)
            }
        }
        _ => Err(format!("unsupported token {token:04X}")),
    }
}

fn record_payload_bits(record: &[Token]) -> Result<usize, String> {
    record.iter().try_fold(
        0usize,
        |total, &token| Ok(total + symbol_bit_length(token)?),
    )
}

fn record_packed_size(record: &[Token]) -> Result<usize, String> {
    Ok((record_payload_bits(record)? + 14) / 8)
}

fn packed_size(groups: &Groups, dictionary: &Dictionary) -> Result<usize, String> {
    let group_bytes = groups.iter().try_fold(0usize, |total, group| {
        group.iter().try_fold(total, |subtotal, record| {
            Ok::<usize, String>(subtotal + record_packed_size(record)?)
        })
    })?;
    dictionary.iter().try_fold(group_bytes, |total, entry| {
        Ok(total + record_packed_size(entry)?)
    })
}

fn literal_token_key(token: Token) -> Result<u8, String> {
    match token_kind(token) {
        0 if token_value(token) <= 47 => Ok(token_value(token)),
        1 if token_value(token) <= 63 => Ok(0x40 + token_value(token)),
        _ => Err(format!("non-literal token {token:04X} in dictionary entry")),
    }
}

fn candidate_key(candidate: &[Token]) -> Result<Vec<u8>, String> {
    candidate
        .iter()
        .map(|&token| literal_token_key(token))
        .collect()
}

fn dictionary_key(dictionary: &Dictionary) -> Result<Vec<Vec<u8>>, String> {
    dictionary
        .iter()
        .map(|entry| candidate_key(entry))
        .collect()
}

fn result_key(state: &ResultState) -> Result<(usize, usize, Vec<Vec<u8>>), String> {
    Ok((
        packed_size(&state.groups, &state.dictionary)?,
        state.dictionary.len(),
        dictionary_key(&state.dictionary)?,
    ))
}

fn beam_key(state: &BeamState) -> Result<(usize, Vec<Vec<u8>>), String> {
    Ok((state.size, dictionary_key(&state.dictionary)?))
}

fn validate_required_entries(entries: &Dictionary, maximum_entries: usize) -> Result<(), String> {
    if entries.len() > maximum_entries {
        return Err("too many required dictionary entries".to_string());
    }
    let mut seen: HashMap<Record, ()> = HashMap::new();
    for entry in entries {
        if entry.is_empty() {
            return Err("required dictionary entries must be nonempty".to_string());
        }
        if entry.iter().any(|&token| !is_literal(token)) {
            return Err("required dictionary entries must contain literal glyphs".to_string());
        }
        if seen.insert(entry.clone(), ()).is_some() {
            return Err("required dictionary entries must be unique".to_string());
        }
    }
    Ok(())
}

fn replace_candidate(groups: &Groups, candidate: &[Token], reference: Token) -> Groups {
    let mut rebuilt_groups = Vec::with_capacity(groups.len());
    for group in groups {
        let mut rebuilt_records = Vec::with_capacity(group.len());
        for record in group {
            let mut rebuilt = Vec::with_capacity(record.len());
            let mut position = 0usize;
            while position < record.len() {
                if position + candidate.len() <= record.len()
                    && &record[position..position + candidate.len()] == candidate
                {
                    rebuilt.push(reference);
                    position += candidate.len();
                } else {
                    rebuilt.push(record[position]);
                    position += 1;
                }
            }
            rebuilt_records.push(rebuilt);
        }
        rebuilt_groups.push(rebuilt_records);
    }
    rebuilt_groups
}

fn install_required_entries(
    groups: &Groups,
    required_entries: &Dictionary,
    maximum_entries: usize,
) -> Result<ResultState, String> {
    validate_required_entries(required_entries, maximum_entries)?;
    let mut compressed = groups.clone();
    let mut dictionary = Vec::with_capacity(maximum_entries);
    for candidate in required_entries {
        let reference = dictionary_token(dictionary.len() + 1)?;
        compressed = replace_candidate(&compressed, candidate, reference);
        dictionary.push(candidate.clone());
    }
    Ok(ResultState {
        groups: compressed,
        dictionary,
    })
}

fn candidate_counts(groups: &Groups) -> HashMap<Record, CandidateCount> {
    let mut counts: HashMap<Record, CandidateCount> = HashMap::new();
    let mut next_order = 0usize;
    for group in groups {
        for record in group {
            let mut segment_start = 0usize;
            for position in 0..=record.len() {
                let boundary = position == record.len() || !is_literal(record[position]);
                if !boundary {
                    continue;
                }
                let segment = &record[segment_start..position];
                for start in 0..segment.len() {
                    let maximum = MAX_CANDIDATE_TOKENS.min(segment.len() - start);
                    for length in 2..=maximum {
                        let candidate = segment[start..start + length].to_vec();
                        match counts.entry(candidate) {
                            Entry::Occupied(mut occupied) => occupied.get_mut().count += 1,
                            Entry::Vacant(vacant) => {
                                vacant.insert(CandidateCount {
                                    count: 1,
                                    order: next_order,
                                });
                                next_order += 1;
                            }
                        }
                    }
                }
                segment_start = position + 1;
            }
        }
    }
    counts
}

fn rank_candidates(groups: &Groups) -> Result<Vec<RankedCandidate>, String> {
    let mut ranked = Vec::new();
    for (candidate, info) in candidate_counts(groups) {
        if info.count < 2 {
            continue;
        }
        let literal_bits = record_payload_bits(&candidate)? as isize;
        let entry_bits = (record_packed_size(&candidate)? * 8) as isize;
        let estimated_saving = info.count as isize * (literal_bits - 9) - entry_bits;
        if estimated_saving > 0 {
            ranked.push(RankedCandidate {
                saving: estimated_saving,
                order: info.order,
                candidate,
            });
        }
    }
    ranked.sort_by(|left, right| {
        right
            .saving
            .cmp(&left.saving)
            .then_with(|| left.order.cmp(&right.order))
    });
    Ok(ranked)
}

fn non_overlapping_occurrences(haystack: &[Token], needle: &[Token]) -> usize {
    if needle.is_empty() || needle.len() > haystack.len() {
        return 0;
    }
    let mut count = 0usize;
    let mut position = 0usize;
    while position + needle.len() <= haystack.len() {
        if &haystack[position..position + needle.len()] == needle {
            count += 1;
            position += needle.len();
        } else {
            position += 1;
        }
    }
    count
}

fn prepared_records(groups: &Groups) -> Result<Vec<(Record, usize)>, String> {
    let mut prepared = Vec::new();
    for group in groups {
        for record in group {
            prepared.push((record.clone(), record_payload_bits(record)?));
        }
    }
    Ok(prepared)
}

fn candidate_packed_size(
    prepared: &[(Record, usize)],
    dictionary_size: usize,
    candidate: &[Token],
) -> Result<usize, String> {
    let literal_bits = record_payload_bits(candidate)?;
    let delta_bits = literal_bits
        .checked_sub(9)
        .ok_or_else(|| "candidate cannot save bits".to_string())?;
    let mut group_size = 0usize;
    for (record, old_bits) in prepared {
        let replacements = non_overlapping_occurrences(record, candidate);
        let saved = replacements * delta_bits;
        let new_bits = old_bits
            .checked_sub(saved)
            .ok_or_else(|| "candidate size underflow".to_string())?;
        group_size += (new_bits + 14) / 8;
    }
    Ok(group_size + dictionary_size + record_packed_size(candidate)?)
}

fn greedy(
    groups: &Groups,
    required_entries: &Dictionary,
    candidate_limit: Option<usize>,
    maximum_entries: usize,
) -> Result<ResultState, String> {
    let installed = install_required_entries(groups, required_entries, maximum_entries)?;
    let mut compressed = installed.groups;
    let mut dictionary = installed.dictionary;
    let mut current_size = packed_size(&compressed, &dictionary)?;

    while dictionary.len() < maximum_entries {
        let ranked = rank_candidates(&compressed)?;
        let prepared = prepared_records(&compressed)?;
        let dictionary_size = dictionary.iter().try_fold(0usize, |total, entry| {
            Ok::<usize, String>(total + record_packed_size(entry)?)
        })?;
        let mut best_candidate: Option<Record> = None;
        let mut best_size = current_size;
        let take = candidate_limit.unwrap_or(usize::MAX);
        for ranked_candidate in ranked.iter().take(take) {
            let size =
                candidate_packed_size(&prepared, dictionary_size, &ranked_candidate.candidate)?;
            if size < best_size {
                best_size = size;
                best_candidate = Some(ranked_candidate.candidate.clone());
            }
        }
        let Some(candidate) = best_candidate else {
            break;
        };
        let reference = dictionary_token(dictionary.len() + 1)?;
        compressed = replace_candidate(&compressed, &candidate, reference);
        dictionary.push(candidate);
        current_size = best_size;
    }

    Ok(ResultState {
        groups: compressed,
        dictionary,
    })
}

fn compress_without_optimization(problem: &Problem) -> Result<ResultState, String> {
    let primary = greedy(
        &problem.groups,
        &problem.required_entries,
        Some(MAX_CANDIDATES_TO_EVALUATE),
        problem.max_entries,
    )?;
    let primary_size = packed_size(&primary.groups, &primary.dictionary)?;
    let primary_complete =
        !problem.requires_full_dictionary || primary.dictionary.len() == problem.max_entries;
    if problem
        .max_bytes
        .map_or(true, |limit| primary_size <= limit)
        && primary_complete
    {
        return Ok(primary);
    }

    let fallback = greedy(
        &problem.groups,
        &problem.required_entries,
        None,
        problem.max_entries,
    )?;
    let fallback_size = packed_size(&fallback.groups, &fallback.dictionary)?;
    if problem.requires_full_dictionary {
        if fallback.dictionary.len() != problem.max_entries {
            return Err(format!(
                "fixed-address UI requires exactly {} dictionary entries; compressor produced {}",
                problem.max_entries,
                fallback.dictionary.len()
            ));
        }
        return Ok(fallback);
    }
    if fallback_size < primary_size {
        Ok(fallback)
    } else {
        Ok(primary)
    }
}

fn beam_search(
    groups: &Groups,
    required_entries: &Dictionary,
    beam_width: usize,
    branch_factor: usize,
    candidate_limit: Option<usize>,
    maximum_entries: usize,
) -> Result<ResultState, String> {
    if beam_width == 0 || branch_factor == 0 {
        return Err("beam width and branch factor must be positive".to_string());
    }
    let installed = install_required_entries(groups, required_entries, maximum_entries)?;
    let initial_size = packed_size(&installed.groups, &installed.dictionary)?;
    let mut beam = vec![BeamState {
        size: initial_size,
        groups: installed.groups,
        dictionary: installed.dictionary,
    }];
    let mut best = beam[0].clone();

    while !beam.is_empty() && beam[0].dictionary.len() < maximum_entries {
        let mut successors = Vec::new();
        for state in &beam {
            let ranked = rank_candidates(&state.groups)?;
            let prepared = prepared_records(&state.groups)?;
            let dictionary_size = state.dictionary.iter().try_fold(0usize, |total, entry| {
                Ok::<usize, String>(total + record_packed_size(entry)?)
            })?;
            let mut evaluated: Vec<(usize, Vec<u8>, Record)> = Vec::new();
            let take = candidate_limit.unwrap_or(usize::MAX);
            for ranked_candidate in ranked.iter().take(take) {
                let candidate_size =
                    candidate_packed_size(&prepared, dictionary_size, &ranked_candidate.candidate)?;
                if candidate_size < state.size {
                    evaluated.push((
                        candidate_size,
                        candidate_key(&ranked_candidate.candidate)?,
                        ranked_candidate.candidate.clone(),
                    ));
                }
            }
            evaluated
                .sort_by(|left, right| left.0.cmp(&right.0).then_with(|| left.1.cmp(&right.1)));
            let reference = dictionary_token(state.dictionary.len() + 1)?;
            for (candidate_size, _, candidate) in evaluated.into_iter().take(branch_factor) {
                let mut dictionary = state.dictionary.clone();
                dictionary.push(candidate.clone());
                successors.push(BeamState {
                    size: candidate_size,
                    groups: replace_candidate(&state.groups, &candidate, reference),
                    dictionary,
                });
            }
        }
        if successors.is_empty() {
            break;
        }

        let mut unique: HashMap<Vec<Vec<u8>>, BeamState> = HashMap::new();
        for state in successors {
            let key = dictionary_key(&state.dictionary)?;
            match unique.entry(key) {
                Entry::Occupied(mut occupied) => {
                    if state.size < occupied.get().size {
                        occupied.insert(state);
                    }
                }
                Entry::Vacant(vacant) => {
                    vacant.insert(state);
                }
            }
        }
        beam = unique.into_values().collect();
        beam.sort_by(|left, right| {
            beam_key(left)
                .and_then(|left_key| beam_key(right).map(|right_key| left_key.cmp(&right_key)))
                .unwrap_or(Ordering::Equal)
        });
        beam.truncate(beam_width);
        if beam_key(&beam[0])? < beam_key(&best)? {
            best = beam[0].clone();
        }
    }

    Ok(ResultState {
        groups: best.groups,
        dictionary: best.dictionary,
    })
}

fn reapply_dictionary(groups: &Groups, dictionary: &Dictionary) -> Result<ResultState, String> {
    let mut compressed = groups.clone();
    let mut rebuilt_dictionary = Vec::with_capacity(dictionary.len());
    for candidate in dictionary {
        let reference = dictionary_token(rebuilt_dictionary.len() + 1)?;
        compressed = replace_candidate(&compressed, candidate, reference);
        rebuilt_dictionary.push(candidate.clone());
    }
    Ok(ResultState {
        groups: compressed,
        dictionary: rebuilt_dictionary,
    })
}

fn improve_dictionary_order(
    groups: &Groups,
    dictionary: &Dictionary,
    required_entry_count: usize,
    max_passes: usize,
    maximum_entries: usize,
) -> Result<ResultState, String> {
    if required_entry_count > dictionary.len() || max_passes == 0 {
        return Err("invalid dictionary-order optimizer arguments".to_string());
    }
    validate_required_entries(dictionary, maximum_entries)?;
    let mut order = dictionary.clone();
    let mut best = reapply_dictionary(groups, &order)?;
    let mut best_size = packed_size(&best.groups, &best.dictionary)?;

    for _ in 0..max_passes {
        let mut improved = false;
        for left in required_entry_count..order.len() {
            for right in left + 1..order.len() {
                let mut trial_order = order.clone();
                trial_order.swap(left, right);
                let trial = reapply_dictionary(groups, &trial_order)?;
                let trial_size = packed_size(&trial.groups, &trial.dictionary)?;
                if trial_size < best_size {
                    order = trial_order;
                    best = trial;
                    best_size = trial_size;
                    improved = true;
                }
            }
        }
        if !improved {
            break;
        }
    }
    Ok(best)
}

fn optimize(problem: &Problem) -> Result<ResultState, String> {
    if !(1..=68).contains(&problem.max_entries) {
        return Err("maximum dictionary entries is out of range".to_string());
    }
    validate_required_entries(&problem.required_entries, problem.max_entries)?;

    let baseline = compress_without_optimization(problem)?;
    let mut candidates = vec![
        baseline.clone(),
        beam_search(
            &problem.groups,
            &problem.required_entries,
            DEFAULT_BEAM_WIDTH,
            DEFAULT_BEAM_BRANCH_FACTOR,
            Some(MAX_CANDIDATES_TO_EVALUATE),
            problem.max_entries,
        )?,
        improve_dictionary_order(
            &problem.groups,
            &baseline.dictionary,
            problem.required_entries.len(),
            5,
            problem.max_entries,
        )?,
    ];

    let baseline_size = packed_size(&baseline.groups, &baseline.dictionary)?;
    if let Some(max_bytes) = problem.max_bytes {
        let headroom = max_bytes as isize - baseline_size as isize;
        if headroom <= EXTENDED_BEAM_HEADROOM_BYTES {
            candidates.push(beam_search(
                &problem.groups,
                &problem.required_entries,
                EXTENDED_BEAM_WIDTH,
                EXTENDED_BEAM_BRANCH_FACTOR,
                Some(MAX_CANDIDATES_TO_EVALUATE),
                problem.max_entries,
            )?);
        }
    }

    if problem.requires_full_dictionary {
        candidates.retain(|candidate| candidate.dictionary.len() == problem.max_entries);
    }
    if candidates.is_empty() {
        return Err("no compression candidate satisfies the release constraints".to_string());
    }

    let mut best = candidates.remove(0);
    let mut best_key = result_key(&best)?;
    for candidate in candidates {
        let key = result_key(&candidate)?;
        if key < best_key {
            best = candidate;
            best_key = key;
        }
    }
    Ok(best)
}

fn parse_usize(value: &str, label: &str) -> Result<usize, String> {
    value
        .parse::<usize>()
        .map_err(|error| format!("invalid {label}: {error}"))
}

fn parse_tokens(value: &str) -> Result<Record, String> {
    let value = value.trim();
    if value.is_empty() || value == "-" {
        return Ok(Vec::new());
    }
    value
        .split_whitespace()
        .map(|item| {
            u16::from_str_radix(item, 16)
                .map_err(|error| format!("invalid token {item:?}: {error}"))
        })
        .collect()
}

fn parse_problem(input: &str) -> Result<Problem, String> {
    let mut lines = Lines::new(input);
    if lines.next()?.trim() != PROTOCOL {
        return Err("unsupported compression optimizer protocol".to_string());
    }
    let max_entries = parse_usize(lines.value("MAX_ENTRIES")?, "MAX_ENTRIES")?;
    let max_bytes_text = lines.value("MAX_BYTES")?;
    let max_bytes = if max_bytes_text == "NONE" {
        None
    } else {
        Some(parse_usize(max_bytes_text, "MAX_BYTES")?)
    };
    let requires_full_dictionary = match lines.value("REQUIRES_FULL")? {
        "0" => false,
        "1" => true,
        other => return Err(format!("invalid REQUIRES_FULL value {other:?}")),
    };
    let required_count = parse_usize(lines.value("REQUIRED")?, "REQUIRED")?;
    let mut required_entries = Vec::with_capacity(required_count);
    for _ in 0..required_count {
        required_entries.push(parse_tokens(lines.value("ENTRY")?)?);
    }

    let group_count = parse_usize(lines.value("GROUPS")?, "GROUPS")?;
    let mut groups = Vec::with_capacity(group_count);
    for _ in 0..group_count {
        let record_count = parse_usize(lines.value("GROUP")?, "GROUP")?;
        let mut group = Vec::with_capacity(record_count);
        for _ in 0..record_count {
            group.push(parse_tokens(lines.value("RECORD")?)?);
        }
        groups.push(group);
    }
    if lines.next()?.trim() != "END" {
        return Err("optimizer protocol did not end with END".to_string());
    }
    Ok(Problem {
        groups,
        required_entries,
        max_entries,
        max_bytes,
        requires_full_dictionary,
    })
}

fn format_tokens(tokens: &[Token]) -> String {
    if tokens.is_empty() {
        return "-".to_string();
    }
    tokens
        .iter()
        .map(|token| format!("{token:04X}"))
        .collect::<Vec<_>>()
        .join(" ")
}

fn format_result(result: &ResultState) -> Result<String, String> {
    let mut output = String::new();
    output.push_str(RESULT_PROTOCOL);
    output.push('\n');
    output.push_str(&format!(
        "PACKED_SIZE {}\n",
        packed_size(&result.groups, &result.dictionary)?
    ));
    output.push_str(&format!("DICTIONARY {}\n", result.dictionary.len()));
    for entry in &result.dictionary {
        output.push_str("ENTRY ");
        output.push_str(&format_tokens(entry));
        output.push('\n');
    }
    output.push_str(&format!("GROUPS {}\n", result.groups.len()));
    for group in &result.groups {
        output.push_str(&format!("GROUP {}\n", group.len()));
        for record in group {
            output.push_str("RECORD ");
            output.push_str(&format_tokens(record));
            output.push('\n');
        }
    }
    output.push_str("END\n");
    Ok(output)
}

fn run() -> Result<(), String> {
    let mut input = String::new();
    io::stdin()
        .read_to_string(&mut input)
        .map_err(|error| format!("failed to read optimizer input: {error}"))?;
    let problem = parse_problem(&input)?;
    let result = optimize(&problem)?;
    print!("{}", format_result(&result)?);
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("time-twist-compression-optimizer: {error}");
        process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn common(value: u8) -> Token {
        value as Token
    }

    #[test]
    fn protocol_round_trip_parses_empty_and_nonempty_records() {
        let input = concat!(
            "TIME_TWIST_COMPRESSION_V1\n",
            "MAX_ENTRIES 68\n",
            "MAX_BYTES 100\n",
            "REQUIRES_FULL 0\n",
            "REQUIRED 1\n",
            "ENTRY 0001 0002\n",
            "GROUPS 1\n",
            "GROUP 2\n",
            "RECORD 0001 0002 0001 0002\n",
            "RECORD -\n",
            "END\n",
        );
        let problem = parse_problem(input).expect("parse problem");
        assert_eq!(problem.max_entries, 68);
        assert_eq!(problem.required_entries, vec![vec![common(1), common(2)]]);
        assert_eq!(problem.groups[0][1], Vec::<Token>::new());
    }

    #[test]
    fn greedy_dictionary_reduces_repeated_literal_phrase() {
        let phrase = vec![common(1), common(2), common(3), common(4)];
        let groups = vec![vec![
            [phrase.clone(), phrase.clone(), phrase.clone()].concat(),
            [phrase.clone(), phrase.clone()].concat(),
        ]];
        let result = greedy(&groups, &Vec::new(), Some(200), 68).expect("greedy");
        assert!(!result.dictionary.is_empty());
        assert!(
            packed_size(&result.groups, &result.dictionary).expect("size")
                < packed_size(&groups, &Vec::new()).expect("literal size")
        );
    }

    #[test]
    fn optimized_result_never_exceeds_baseline() {
        let phrase = vec![common(1), common(2), common(3), common(4), common(5)];
        let groups = vec![vec![
            [phrase.clone(), phrase.clone(), vec![common(6), common(7)]].concat(),
            [phrase.clone(), phrase.clone(), phrase.clone()].concat(),
        ]];
        let problem = Problem {
            groups,
            required_entries: Vec::new(),
            max_entries: 68,
            max_bytes: Some(1024),
            requires_full_dictionary: false,
        };
        let baseline = compress_without_optimization(&problem).expect("baseline");
        let optimized = optimize(&problem).expect("optimized");
        assert!(
            packed_size(&optimized.groups, &optimized.dictionary).expect("optimized size")
                <= packed_size(&baseline.groups, &baseline.dictionary).expect("baseline size")
        );
    }
}
