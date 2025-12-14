from dotenv import load_dotenv
from openai import OpenAI
from together import Together
from google import genai
from google.genai import types
import anthropic
import os
import re



# === Determine backend ===
openai_models = [
    "gpt-5.1-2025-11-13", "gpt-4.1-2025-04-14"
]

together_models = [
    "Qwen/Qwen3-235B-A22B-Instruct-2507-tput", "deepseek-ai/DeepSeek-V3.1", "zai-org/GLM-4.6", "moonshotai/Kimi-K2-Instruct-0905",
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
]

google_models = [
    "gemini-3-pro-preview", "gemini-2.5-flash"
]

anthropic_models = [
    "claude-sonnet-4-5"
]


# === Load API keys from .env ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def build_model(model_name):
    if model_name in openai_models:
        client = OpenAI(api_key=OPENAI_API_KEY)
    elif model_name in together_models:
        os.environ["TOGETHER_API_KEY"] = TOGETHER_API_KEY
        client = Together()
    elif model_name in google_models:
        os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
        client = genai.Client()
    elif model_name in anthropic_models:
        os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
        client = anthropic.Anthropic()
    else:
        raise ValueError("❌ WRONG MODEL NAME!")
    return client


def ask_llm(client, model, msgs, temperature=0.0, top_p=1.0, reasoning="none", max_tokens=4096):
    try:
        if model.startswith("gpt-5") or model.startswith("o"):
            response = client.responses.create(
                model=model,
                input=msgs,
                max_output_tokens=max_tokens,
                reasoning={"effort": reasoning}
            )
            return response.output[-1].content[0].text, ""
        elif model in openai_models:
            response = client.responses.create(
                model=model,
                input=msgs,
                max_output_tokens=max_tokens,
                temperature=temperature,
                topP=top_p
            )
            return response.output[-1].content[0].text, ""
        elif model in google_models:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=msgs,
                    config=types.GenerateContentConfig(
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        response_mime_type="application/json",
                        response_json_schema={
                            "type": "object",
                            "properties": {
                                "choice": {
                                    "type": "integer",
                                    "description": "The chosen number (1, 2, 3, or 4) for pain medication dosing."
                                }
                            },
                            "required": ["choice"], 
                            "additionalProperties": False 
                        }
                    )
                )
            except Exception as e:
                print(f"[ERROR calling model]: {e}")
            return response.text, ""
        elif model in together_models:
            response = client.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content, response.choices[0].message.reasoning
        elif model in anthropic_models:
            try:
                response = client.messages.create(
                    model=model,
                    messages=msgs,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except Exception as e:
                print(f"[ERROR calling model]: {e}")
            return response.content[0].text, ""
    except Exception as e:
        return f"[ERROR calling model]: {e}"


def extract_last_json(s):
    pattern = r'\{[^{}]*\}'
    matches = re.findall(pattern, s)
    if matches:
        return matches[-1]
    return s