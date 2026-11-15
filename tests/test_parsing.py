"""Reading what a model wrote. Real models are messy, so these cover the mess."""
import pytest

from arena.engine.actions import parse_action
from arena.llm.backends import clean
from arena.llm.parsing import clean_speech, clip_words, extract_json, match_name, to_int

NAMES = ["Magister Vellum", "Glitchwick", "Aurelia Null"]


def test_extract_json_plain_fenced_and_chatty():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json('Sure! Here you go: {"a": 3} hope that helps') == {"a": 3}
    assert extract_json("no json at all") is None
    assert extract_json("") is None


def test_clean_strips_thinking_even_when_unterminated():
    assert clean("<think>hmm</think>Hello") == "Hello"
    assert clean("Hi <think>still thinking and ran out of tokens") == "Hi"


def test_match_name_is_forgiving_but_not_wild():
    assert match_name("glitchwick", NAMES) == "Glitchwick"
    assert match_name("Vellum", NAMES) == "Magister Vellum"
    assert match_name("Aurelia", NAMES) == "Aurelia Null"
    assert match_name("Nobody", NAMES) is None
    assert match_name("", NAMES) is None


def test_clean_speech_clips_and_removes_self_labels():
    out = clean_speech('Glitchwick: "I would like to speak. ' + "word " * 100 + '"', "Glitchwick", 20)
    assert not out.startswith("Glitchwick")
    assert len(out.split()) <= 21


def test_clip_words_and_to_int():
    assert clip_words("a b c d e", 3).startswith("a b c")
    assert to_int("7") == 7 and to_int("x", 4) == 4 and to_int(500, 0, 0, 9) == 9


def test_parse_action_json_and_targets():
    a = parse_action('{"action": "STRIKE", "target": "glitch", "amount": 99}', "Aurelia Null", NAMES)
    assert (a.kind, a.target) == ("STRIKE", "Glitchwick")
    assert a.amount <= 99 and a.amount >= 0


def test_parse_action_synonyms_and_bare_reply():
    assert parse_action('{"action": "attack", "target": "Glitchwick"}', "Aurelia Null", NAMES).kind == "STRIKE"
    assert parse_action("STRIKE Glitchwick", "Aurelia Null", NAMES).kind == "STRIKE"
    assert parse_action('{"action": "HOARD"}', "Aurelia Null", NAMES).kind == "HOARD"


def test_parse_action_garbage_is_a_stall_not_a_default_move():
    a = parse_action("I refuse to play this game, it is beneath me and I would like it noted at length " * 3, "Aurelia Null", NAMES)
    assert a.kind == "NONE" and a.reason


def test_parse_action_cannot_target_self():
    a = parse_action('{"action": "STRIKE", "target": "Aurelia Null"}', "Aurelia Null", NAMES)
    assert a.kind in ("NONE",) or a.target != "Aurelia Null"


def test_extract_json_repairs_what_small_models_write():
    assert extract_json('{"to":"Glitchwick",say":"Welcome, fellow Wick."}') == {"to": "Glitchwick", "say": "Welcome, fellow Wick."}
    assert extract_json('{"to":"ALL","say":"cut off mid sen') == {"to": "ALL", "say": "cut off mid sen"}
    assert extract_json("{'action': 'STRIKE', 'target': 'Bob', 'amount': 2") == {"action": "STRIKE", "target": "Bob", "amount": 2}
    assert extract_json("just a sentence, no braces: a: b") is None


def test_trim_sentences_ends_cleanly():
    from arena.llm.parsing import trim_sentences
    text = "First sentence here. Second sentence follows it. Third sentence is the one that runs far too long and never stops"
    out = trim_sentences(text, 8)
    assert out == "First sentence here. Second sentence follows it."
    assert trim_sentences("short one.", 50) == "short one."
    assert len(trim_sentences("word " * 200, 10).split()) <= 11   # no sentence break at all: falls back to a word clip
