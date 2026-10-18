"""Structured answers the AI helpers return."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WordHelp(BaseModel):
    syllables: str = Field(description="Word split into syllables with hyphens.")
    say_it: str = Field(description="Simple sound-it-out guide.")
    part_of_speech: str
    meaning_here: str = Field(description="Meaning in this sentence, at the reader's level.")
    synonyms: list[str] = Field(description="Up to 5 simpler replacement words for this sentence.")
    example: str = Field(description="One new short sentence using the word the same way.")


class TrickyWord(BaseModel):
    word: str
    meaning: str


class Explanation(BaseModel):
    heading: str
    points: list[str]
    tricky_words: list[TrickyWord]


class CheckQuestion(BaseModel):
    question: str
    answer: str


class Summary(BaseModel):
    big_idea: str
    key_points: list[str]
    words_to_know: list[TrickyWord]
    check_questions: list[CheckQuestion]


class RewrittenParagraph(BaseModel):
    n: int = Field(description="The paragraph number you were given.")
    text: str


class Rewrite(BaseModel):
    paragraphs: list[RewrittenParagraph]


class SettingSuggestion(BaseModel):
    setting: str = Field(description="One of the setting keys listed in the instructions.")
    value: str = Field(description="One of the allowed values for that setting.")
    reason: str = Field(description="One short, friendly sentence on why this might help.")


class TutorReply(BaseModel):
    reply: str = Field(description="Your chat message to the student (simple markdown).")
    suggestions: list[SettingSuggestion] = Field(description="0 to 3 reading-setting changes to try. Usually empty.")
