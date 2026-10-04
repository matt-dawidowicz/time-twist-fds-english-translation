"""Canonical visible answers for Time Twist's 39 scored quiz questions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuizAnswer:
    """One menu selector and the visible label that must reach success."""

    bank: str
    selector: int
    answer: str


QUIZ_ANSWERS = (
    QuizAnswer("TT2", 0x0E, "Jerusalem"),
    QuizAnswer("TT2", 0x0F, "Hundred Years"),
    QuizAnswer("TT2", 0x10, "Commoners"),
    QuizAnswer("TT2", 0x11, "Guild"),
    QuizAnswer("TT2", 0x12, "da Vinci"),
    QuizAnswer("TT3A", 0x2A, "Gestapo"),
    QuizAnswer("TT3A", 0x2B, "Résistance"),
    QuizAnswer("TT3A", 0x2C, "U-boat"),
    QuizAnswer("TT3A", 0x2D, "Gabin"),
    QuizAnswer("TT3A", 0x2E, "Eisenhower"),
    QuizAnswer("TT4", 0x30, "Polis"),
    QuizAnswer("TT4", 0x31, "Sparta"),
    QuizAnswer("TT4", 0x32, "Heracles"),
    QuizAnswer("TT4", 0x33, "Parthenon"),
    QuizAnswer("TT4", 0x34, "Fig"),
    QuizAnswer("TT5", 0x1A, "Cavalry"),
    QuizAnswer("TT5", 0x1B, "Black ship"),
    QuizAnswer("TT5", 0x1C, "Mrs. Stowe"),
    QuizAnswer("TT5", 0x1D, "Rushmore"),
    QuizAnswer("TT5", 0x1E, "Projector"),
    QuizAnswer("TT6B", 0x0F, "Fruit of wisdom"),
    QuizAnswer("TT6B", 0x10, "Jehovah"),
    QuizAnswer("TT6B", 0x11, "Egypt"),
    QuizAnswer("TT6B", 0x12, "Solomon"),
    QuizAnswer("TT6B", 0x13, "Christ"),
    QuizAnswer("TT6C", 0x14, "Five"),
    QuizAnswer("TT6C", 0x15, "Cougar"),
    QuizAnswer("TT6C", 0x16, "Glazier"),
    QuizAnswer("TT6C", 0x17, "Isabel"),
    QuizAnswer("TT6C", 0x18, "Rebecca"),
    QuizAnswer("TT6C", 0x19, "Switzerland"),
    QuizAnswer("TT6C", 0x1A, "Plantain herb"),
    QuizAnswer("TT6C", 0x1B, "Cerberus"),
    QuizAnswer("TT6C", 0x1C, "Tom"),
    QuizAnswer("TT6C", 0x1D, "Coyote"),
    QuizAnswer("TT6C", 0x1E, "Silver bracelet"),
    QuizAnswer("TT6C", 0x1F, "Bethlehem"),
    QuizAnswer("TT6C", 0x20, "Nicras"),
    QuizAnswer("TT6C", 0x21, "Joseph"),
)
