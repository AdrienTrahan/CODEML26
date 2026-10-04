import json
from types import SimpleNamespace
from unittest.mock import patch

from llm_parser.model import ModelEvaluator
from llm_parser.schema import ExtractedData


def test_evaluate_text_sends_text_only_and_returns_validated_json():
    payload = '{"empattements": [{"name": "E1", "data": ["9-25M"]}], "semelles": []}'
    response = SimpleNamespace(choices=[SimpleNamespace(
        finish_reason="stop",
        message=SimpleNamespace(content=payload),
    )])
    with patch("llm_parser.model.OpenAI") as openai:
        openai.return_value.chat.completions.create.return_value = response
        evaluator = ModelEvaluator("text-model", "http://localhost:1234/v1", "key", 8192)
        result = evaluator.evaluate_text("Extract the elements", ExtractedData, "E1: 9-25M")

    assert json.loads(result) == json.loads(payload)
    kwargs = openai.return_value.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "text-model"
    assert kwargs["messages"] == [
        {"role": "system", "content": "Extract the elements"},
        {"role": "user", "content": "E1: 9-25M"},
    ]
    assert kwargs["response_format"]["json_schema"]["schema"] == ExtractedData.model_json_schema()


def test_evaluate_text_rejects_invalid_schema_output():
    response = SimpleNamespace(choices=[SimpleNamespace(
        finish_reason="stop",
        message=SimpleNamespace(content='{"empattements": [], "semelles": "invalid"}'),
    )])
    with patch("llm_parser.model.OpenAI") as openai:
        openai.return_value.chat.completions.create.return_value = response
        evaluator = ModelEvaluator("text-model", "http://localhost:1234/v1", "key", 8192)
        result = evaluator.evaluate_text("Extract", ExtractedData, "Semelle S1")

    assert result is None
