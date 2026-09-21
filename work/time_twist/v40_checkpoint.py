"""Reviewed v40 layout fingerprints and continuation contracts; no alternate prose."""

from __future__ import annotations

import hashlib
import json
import re
import runpy
from pathlib import Path

RECORD_SHA256 = {
    "T22/g1/r20": "a9a29c7e7fef947b64eff847c4922a138841c404b9375d10d53f2dc0f8ec03de",
    "T22/g1/r21": "47b9387dcbf1e09ca70bc9869dce5bf46b3f86f831c9633fc64f96b879e33e6a",
    "T25/g1/r5": "fba0130481180f88c4e9973a27d2cbd81d9af8e96156d5def292cca944882843",
    "T25/g2/r8": "06f868a95a5dfe35a6e2c39bb6f391d3bec457ec2d4fd41003cc036b3bd9cab4",
    "TT1A/g0/r3": "fbdd6e38398c075297b3072bacf271e7a1ac3dfc32847ae5cf99cd6ac9a1f5a4",
    "TT1B/g0/r2": "71ac7be32cd368709307b91940387351f3a8074d77a754b61aa32bea3eb84e3f",
    "TT1B/g1/r30": "788264f498900a58ecec5a173e60386d3014b5ff4cc228b12bffe6ac51a3ac90",
    "TT1B/g2/r4": "4d49aba65015c61ee2c1ce7bc99939a6284330198a7590404e4ba1f690416659",
    "TT1B/g2/r6": "06b9348243baaa8e092c7eec56785287a705d568bcdba708be27ead9e91fab07",
    "TT1B/g2/r7": "a61f9f07578dfc9e77f650a07e0640722dc78de1331e9f2ea54bbad86d404165",
    "TT1B/g3/r26": "2e7affc46fbaa2e10797215c201823736934a1d9c2667a059f6029f366b17f73",
    "TT2/g0/r19": "089350d5cdb937a2340aa42643c67ed00bfa18544814ec3c6dc83b88f75e61f7",
    "TT2/g0/r22": "143267523f1f31abb8c549e2b97b1433b13f61c078f4d3db8ae868787ea6aad0",
    "TT2/g1/r12": "f8dad6439838aa6acf03b96edb2422b69d3861ae086c7f5e80cf672c48b59410",
    "TT2/g1/r15": "5bc4879754235f3ba6b47a004209c7d5ac6a5dc4efb72964e2f1757a29d44e90",
    "TT2/g1/r17": "b9377115339d242e4269c549fae77e2dbde5e455f6158c5b0b54cea192074261",
    "TT2/g1/r18": "28a5ef871d436b7ed4ab8d098748a3c6af22258dadb800d447050877bb9593dc",
    "TT2/g1/r29": "a758db5c7baa9048f35b90ceb72268f79524f51b28406023f3a898cb2bd539ab",
    "TT2/g1/r5": "45d92b7f6e882886e6a927604b54781f6772e71fd5ad86071aec8fb7ce9b59b1",
    "TT2/g1/r6": "e1ecf2006272bb39042eebbfb40e1cc09e5302ca2df36c92a841356c0c172dcc",
    "TT2/g2/r10": "2d74e7b90d2c02d61cff88708fb46d5d2f08470ff311d8032ad457109df2d64f",
    "TT2/g2/r15": "c20b5cb27468a5c6ba8ec1373e09285a257928d9aa12cdc46d00299f28a7712e",
    "TT2/g2/r16": "82316ed8a0e51ec658d220a6fcb5c2958ac3c607cde12ee60c3b67b04b379900",
    "TT2/g2/r28": "b5ff96835ec626cf5d1b5aa1fe7ebe0abc63bf54e0dc9f78ab31db275a29e5f1",
    "TT2/g2/r5": "76d6895bb4f1fd55a60354c5ffd43ff62e2d1478f73cca781f34e91453d26bee",
    "TT2/g3/r11": "9fd64312d3ee19f0dc7d16508850135c15ce7bbf84931638ccf35800a443999b",
    "TT2/g3/r12": "f827fa794cab8a6d73559bdbab4952845761c69e1d1d073fb2610cc41c931204",
    "TT2/g3/r21": "772ba347198d1ea4948e5ef003ef2166018059cff6603f53f58c10f422a7b451",
    "TT2/g4/r27": "9413ab3ac570b5e3c949e1028ba2c05d2d1b2db776cbfb854f39170746badbc4",
    "TT2/g4/r5": "3f8cd9e76f06b8791f08e7874626e9dce2599a80f73b134ff7a4df87b59b2d86",
    "TT2/g4/r6": "609051d894af4b939cf067de406f63e0c86bffd03578a8f8c71fdf924f182aff",
    "TT2/g5/r2": "73c6996f01129bd2523084af76a6a25a2db0fffb91626aad42d9a6ae0070bbd0",
    "TT2/g5/r3": "ee32b92059e471b1d0ca85e39f9cb2c9c12f8e6f51c3837dde627c8d46a648ad",
    "TT2/g5/r5": "ace22330933f9c01b8b52eea3661754601b18ba5b4b4156cf8aaf284cfcdc1c8",
    "TT2/g5/r6": "09aef067a118d9fb6dd5055e512736fd8a76aabc5f2c76ffc2d59ef86e95d3e6",
    "TT3A/g0/r14": "2734ab9ae0ce59184a7b280bdd5409cda7df95fa22c3b3230070ecccd98cf2f6",
    "TT3A/g0/r26": "17ca429acac3cbb04af5693e9009f61dd6bd12a1ea804f160dc30e7525e961df",
    "TT3A/g0/r3": "097ad6f827748eee81d0a3bd06dde071468016b754d490a3bac1489343f32852",
    "TT3A/g2/r11": "fe15d242145fafb72b5a26ba60385a23d9a3dc5913323dda916f2ee015999b56",
    "TT3A/g2/r5": "e2cf77378382d5b9b8cb7bb1df13751d0628d6691beb1ff7bd39652375b7cb13",
    "TT3A/g2/r6": "a23c8c441af84e61cbdc79e2ee3e0d3839e3dfb7534d9a6d60a0907043081c05",
    "TT3A/g4/r2": "882324c7e652c423f71d5448d1606d304ffe7c5daed8d2d9a2eff8cfad654cf7",
    "TT3A/g4/r4": "ec670883b753687911b7c5a6c664af914af101a2e4883d5f3976d76c3675dcc2",
    "TT3A/g4/r5": "0e50627d15d6bc6ef9ab74344b6b3c1fcfddebb80144eb644b586545da10e05d",
    "TT3A/g4/r6": "a20a614d51a8b35ce12d859087b160cb2f2052a127456312b30c0cf12ee18ae3",
    "TT3A/g4/r7": "9ffab733c0aed46e95e2d614df47a580fcac494715e059f74c94188be5dcad29",
    "TT3B/g0/r2": "bbb193dabbe98d1258a8d1dcda8c18503f63d3f1ac33d60ede3848872c3dc0ac",
    "TT3B/g0/r29": "4842db939c947954164c279aafbdab109ca41d875a289706a74cc00c1ad30e41",
    "TT4/g1/r22": "30b9035ebfe45c4614b7fd678de19f19807fe7b397b1ea4ad7b537db66e106ac",
    "TT4/g1/r27": "086bbe332d493a2ab491300bda356a9fa48d914af332983bb7adc6a0a287797d",
    "TT4/g2/r1": "6c67ec44392761cbcf24a025f0cb8d32a2e1178e5b5e26a4dad344829d97efb1",
    "TT4/g4/r18": "7c4a9d1c66e5e0422996e708b7d8218e9108511dc1f301dc99b632bb69addbf4",
    "TT4/g4/r22": "2ea8da850c09bf578940c373a86530c64b163994d90ddf1956c210abc26b84bb",
    "TT4/g5/r12": "30e3c4ef60de4e3d12dd64e359e6cc611927cd738b13e661c8bc5ea531a8dfe5",
    "TT4/g5/r13": "a980fe0a13a3f805e80d55bcb9e5473ccd80d9fc568b0bd13c8a270f977c8776",
    "TT4/g5/r7": "9111ed5fa33029a04156a87bed0f3d2f4f6d1885f9692246bf13ff54e02e5f79",
    "TT5/g1/r19": "9722b488f56e2f54dc2f783b45e50749bb46a19877a6de6af9325d21fcb0c73e",
    "TT5/g1/r6": "92f8bd7db5ee1ade093ce992723a07b5275170e918367153d5cfa0b895db19fc",
    "TT5/g2/r15": "f5d0ef2dfd02f349954d8db261169fb6de521b5c97ddae4f35e57c1d2cf58aee",
    "TT6A/g1/r10": "876fc42789ed6ace859cb12212b5cc7a9afd42199bca473b1b06426de3e6e3ce",
    "TT6A/g2/r19": "68ec30a5d7f3aed06f4698f14421c00f1a0c471ebd27936abd93a444104c3b4a",
    "TT6A/g2/r4": "d9946b1b8a787b06b7e6824b28e61c3afa577c1443977a122431e432a8e0e126",
    "TT6A/g2/r6": "311868ff22cb52f19ac1c64e9d22d2ae61e24db83dbd7f0ba5aeed840db5e64e",
    "TT6B/g1/r30": "9f2b496483e317a51adcfb3d0112c2041a6f73f1b48d4dcea4d4b417469113a0",
    "TT6B/g2/r0": "de3ab941d08661485b4f1438aa1bd62a52a2f77a7c0c7b8ab5b77d81250a9df9",
    "TT6B/g2/r15": "401467034b685c71b3a553f6baf88375d36d42d634bf64baeb3caac4dcf8a1bf",
    "TT6B/g2/r17": "61db5fdc7c6753d75ac47be2163dcfe747000bba0097deaf23b132b9996a09a8",
    "TT6B/g2/r2": "344c34761b58d878b6d11d1af1c3ab2bf493cabb240d919071f0e5cf95ef892a",
    "TT6B/g2/r23": "be363d4eeab9b4e39521578ff79d37a59c5f982c60176200911a386c39cb71e8",
    "TT6C/g0/r11": "cf815c910d2efa6e60f9ad6a915d450749b99d6cf0661491a8e2ee10c35165ce",
    "TT6C/g0/r16": "d483ae04892c3477acdcb8b777a5f2887b070a72825771852ce0157f34ef2016",
    "TT6C/g0/r4": "dd82bce35625483b27fc0829e4dd190cfc8f7660c3cc6d892860bf3e94d0ee05",
    "TT6C/g0/r8": "948648042b926137e6601d14b0fcd93c05dbd5ef3ae2d48e70754e321d1c81cb",
    "TT6C/g1/r21": "a432ab2e1d9b9ab8fbfa11cc10d3d975bf8e32cfba0ad07f1a63fd1473a90ad0",
    "TT6C/g1/r28": "8068cad5788882baea636f3ac00b180b010b6473b120cd18a94d9e15fd45f560",
    "TT6C/g2/r4": "212b207f87200b3008afc71fb4c8dcd7c1613e24f24a93bc7879eea969904e90",
    "TT6C/g3/r1": "d7eae64b72bc3050fc4cb2599b66582791b7994be8c5cdb579817f135a62f2e3",
}

CONTINUATION_PREDECESSORS = {
    "T22/g1/r20": ("T22/g1/r19",),
    "T25/g1/r5": ("T25/g1/r4",),
    "T25/g2/r8": ("T25/g2/r3",),
    "TT1B/g0/r2": ("TT1B/g0/r1",),
    "TT1B/g1/r30": ("TT1B/g1/r29",),
    "TT1B/g2/r4": ("TT1B/g2/r3",),
    "TT1B/g2/r6": ("TT1B/g2/r3",),
    "TT1B/g2/r7": ("TT1B/g2/r3",),
    "TT2/g0/r19": ("TT2/g0/r18",),
    "TT2/g1/r12": ("TT2/g1/r11",),
    "TT2/g1/r15": ("TT2/g1/r14",),
    "TT2/g1/r16": ("TT2/g1/r14",),
    "TT2/g1/r17": ("TT2/g1/r14",),
    "TT2/g1/r18": ("TT2/g1/r14",),
    "TT2/g1/r29": ("TT2/g1/r28",),
    "TT2/g1/r5": ("TT2/g1/r4",),
    "TT2/g1/r6": ("TT2/g1/r4",),
    "TT2/g2/r10": ("TT2/g1/r28",),
    "TT2/g2/r16": ("TT2/g1/r21",),
    "TT2/g2/r5": ("TT2/g1/r21",),
    "TT2/g3/r11": ("TT2/g1/r21",),
    "TT2/g3/r21": ("TT2/g1/r28",),
    "TT2/g4/r5": ("TT2/g1/r28",),
    "TT2/g4/r6": ("TT2/g1/r28",),
    "TT3A/g0/r26": ("TT3A/g0/r14",),
    "TT3A/g0/r3": ("TT3A/g0/r2",),
    "TT3A/g2/r11": ("TT3A/g2/r10",),
    "TT3A/g2/r5": ("TT3A/g2/r4",),
    "TT3A/g2/r6": ("TT3A/g2/r4",),
    "TT3A/g4/r2": ("TT3A/g4/r1",),
    "TT3A/g4/r4": ("TT3A/g4/r3",),
    "TT3A/g4/r5": ("TT3A/g4/r3",),
    "TT3A/g4/r6": ("TT3A/g4/r3",),
    "TT3A/g4/r7": ("TT3A/g4/r3",),
    "TT3B/g0/r29": ("TT3B/g0/r28",),
    "TT4/g1/r27": ("TT4/g1/r26",),
    "TT4/g2/r1": ("TT4/g2/r0",),
    "TT4/g4/r18": ("TT4/g4/r17",),
    "TT4/g4/r22": ("TT4/g4/r21",),
    "TT4/g5/r10": ("TT4/g5/r9",),
    "TT4/g5/r11": ("TT4/g5/r9",),
    "TT4/g5/r12": ("TT4/g5/r9",),
    "TT4/g5/r13": ("TT4/g5/r9",),
    "TT4/g5/r7": ("TT4/g5/r6",),
    "TT6A/g2/r19": ("TT6A/g2/r18",),
    "TT6A/g2/r4": ("TT6A/g2/r3",),
    "TT6A/g2/r6": ("TT6A/g2/r5",),
    "TT6B/g1/r30": ("TT6B/g1/r29",),
    "TT6B/g2/r0": ("TT6B/g1/r31",),
    "TT6B/g2/r1": ("TT6B/g1/r31",),
    "TT6B/g2/r15": ("TT6B/g2/r14",),
    "TT6B/g2/r17": ("TT6B/g2/r16",),
    "TT6B/g2/r2": ("TT6B/g1/r31",),
    "TT6B/g2/r23": ("TT6B/g2/r22",),
    "TT6B/g2/r3": ("TT6B/g1/r31",),
    "TT6C/g0/r11": ("TT6C/g0/r10",),
    "TT6C/g0/r16": ("TT6C/g0/r15",),
    "TT6C/g0/r4": ("TT6C/g0/r3",),
    "TT6C/g0/r8": ("TT6C/g0/r7",),
    "TT6C/g1/r21": ("TT6C/g0/r14",),
    "TT6C/g1/r28": ("TT6C/g1/r27",),
    "TT6C/g2/r4": ("TT6C/g0/r14",),
    "TT6C/g3/r1": ("TT6C/g3/r0",),
}

TT3A_DICTIONARY_ADDITIONS = [
    [["ctrl", 0], ["ctrl", 0], ["com", 42], ["com", 8]],
    [["ctrl", 0], ["dict", 4], ["dict", 1]],
    [
        ["com", 0],
        ["com", 9],
        ["com", 12],
        ["com", 20],
        ["com", 0],
        ["com", 14],
        ["dict", 19],
    ],
    [
        ["com", 20],
        ["com", 11],
        ["com", 12],
        ["dict", 1],
        ["dict", 8],
        ["com", 22],
    ],
    [["ext", 60], ["com", 7], ["ctrl", 0]],
]


def v40_checkpoint_records(
    archived: dict[str, str], actual: dict[str, str]
) -> dict[str, str]:
    """Allow only reviewed layout hashes while keeping archived wording exact."""
    from .release_metadata import ReleaseBuildError

    approved = dict(archived)
    for record, digest in RECORD_SHA256.items():
        value = actual.get(record, "")
        if hashlib.sha256(value.encode("utf-8")).hexdigest() != digest:
            raise ReleaseBuildError(
                f"active text differs from v40 checkpoint in 1 records: {record}"
            )
        plain = lambda text: " ".join(  # noqa: E731
            re.sub(r"\{CTRL:[0-7]\}", " ", text).split()
        )
        if plain(value) != plain(archived[record]):
            raise ReleaseBuildError(f"v40 changed visible wording: {record}")
        approved[record] = value
    return approved


def prepare_v40_dictionaries(source: Path) -> None:
    """Repack equivalent dictionary entries and append reviewed phrases.

    Existing IDs retain their literal expansions and fixed-menu meanings.
    References are restricted to earlier IDs, forming an acyclic graph.
    The unchanged recovered codec performs all encoding. Wait/scroll controls
    must not occur inside dictionary entries: a renderer return would leave
    dictionary frames on the CPU stack.
    """
    codec = runpy.run_path(str(source / "codec.py"))
    expand = codec["expand_dictionary"]
    compress = codec["compress_record"]
    for bank in ("TT1B", "TT3A"):
        path = source / "data" / f"{bank}_dictionary_v34.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = [tuple(map(tuple, entry)) for entry in payload["entries"]]
        literals = expand(entries)
        rebuilt = [
            compress(
                literal,
                {
                    other: text
                    for other, text in literals.items()
                    if other < index
                },
            )
            for index, literal in literals.items()
        ]
        if bank == "TT1B":
            rebuilt = entries
        if expand(rebuilt) != literals:
            raise ValueError(f"{bank}: dictionary meanings changed")
        if bank == "TT1B":
            rebuilt.extend(
                tuple(map(tuple, entry)) for entry in TT1B_DICTIONARY_ADDITIONS
            )
        if bank == "TT3A":
            rebuilt.extend(
                tuple(map(tuple, entry)) for entry in TT3A_DICTIONARY_ADDITIONS
            )
        for literal in expand(rebuilt).values():
            if any(kind == "ctrl" and value != 0 for kind, value in literal):
                raise ValueError(f"{bank}: dictionary contains a wait/scroll")
        payload["entries"] = rebuilt
        path.write_text(json.dumps(payload), encoding="utf-8")


TT1B_DICTIONARY_ADDITIONS = [
    [["dict", 72], ["com", 4], ["ctrl", 0], ["dict", 73], ["dict", 5]]
]
