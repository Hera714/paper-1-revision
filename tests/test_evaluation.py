import pytest

from kar3d.evaluation import extract_answer, parse_first_json_object, split_thinking_and_answer


def test_extract_answer_accepts_observed_ovis_final_formats():
    assert extract_answer("<think>Depths: 5.96, 13.16.</think>\n\n1") == "1"
    assert extract_answer("<think>Object 3 is tallest.</think>\n\n1. Diagonal") == "1"
    assert extract_answer("<think>Compare 1, 2, and 3.</think>\n\n4") == "4"
    assert extract_answer("<think>Reasoning.</think><answer>2</answer>") == "2"
    assert extract_answer("<think>Reasoning.</think>Answer: 3") == "3"
    assert extract_answer("<think>Reasoning.</think>Answer (1-4): 2") == "2"
    assert extract_answer("<think>Reasoning.</think>Final answer (1 - 4): option 4") == "4"


def test_extract_answer_does_not_guess_from_reasoning():
    assert extract_answer("<think>Option 1 seems likely.</think>") == "Unknown"
    assert extract_answer("<think>Option 1 seems likely.</think>Unclear") == "Unknown"


def test_split_thinking_and_answer_preserves_both_texts():
    assert split_thinking_and_answer("<think>Compare the objects.</think>\n2. Left") == (
        "Compare the objects.", "2. Left"
    )
    assert split_thinking_and_answer("4") == ("", "4")


def test_parse_first_json_object_ignores_a_second_object():
    parsed, trailing = parse_first_json_object(
        'prefix {"objects": [{"name": "chair"}]} {"objects": []}'
    )
    assert parsed["objects"][0]["name"] == "chair"
    assert trailing == '{"objects": []}'


def test_parse_first_json_object_reports_truncation():
    with pytest.raises(ValueError):
        parse_first_json_object('{"objects": [{"name": "chair"}')
