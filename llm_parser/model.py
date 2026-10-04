from openai import OpenAI
from pydantic import BaseModel


class ModelEvaluator:
    def __init__(
            self,
            model_name: str,
            base_url: str,
            api_key: str,
            max_tokens: int
        ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model_name = model_name
        self.max_tokens = max_tokens

    def evaluate(self, prompt: str, schema: type[BaseModel], image: str | None, text: str | None):
        content = []
        if image is not None:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image}"},
            })
        if text is not None:
            content.append({
                "type": "text",
                "text": text,
            })
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": content,
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "ExtractedData",
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
            max_tokens=self.max_tokens,
            temperature=0,
            extra_body={"repeat_penalty": 1.15},
        )
        try:
            choice = response.choices[0]
            if choice.finish_reason == "length":
                raise Exception("Truncated output")
            return schema.model_validate_json(choice.message.content)
        except Exception as e:
            print(e)
            return None

