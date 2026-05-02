from dotenv import load_dotenv
from openai import OpenAI
from together import Together
from google import genai
from google.genai import types
import anthropic
import os
import re
import random


# === Determine backend ===
openai_models = [
    "gpt-5.4-2026-03-05"
]

together_models = [
    "Qwen/Qwen3.5-397B-A17B", "deepseek-ai/DeepSeek-V3.1", "zai-org/GLM-5",
    "MiniMaxAI/MiniMax-M2.5", "moonshotai/Kimi-K2.5"
]

deepinfra_models = [
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
]

google_models = [
    "gemini-3-flash-preview"
]

anthropic_models = [
    "claude-sonnet-4-6"
]


# === Load API keys from .env ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def build_model(model_name):
    if model_name in openai_models:
        client = OpenAI(api_key=OPENAI_API_KEY)
    elif model_name in together_models:
        os.environ["TOGETHER_API_KEY"] = TOGETHER_API_KEY
        client = Together()
    elif model_name in deepinfra_models:
        client = OpenAI(api_key=DEEPINFRA_API_KEY, base_url="https://api.deepinfra.com/v1/openai")
    elif model_name in google_models:
        os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
        client = genai.Client()
    elif model_name in anthropic_models:
        os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
        client = anthropic.Anthropic()
    else:
        raise ValueError("❌ WRONG MODEL NAME!")
    return client


def ask_llm(client, model, msgs, cot=False, temperature=0.0, top_p=1.0, max_tokens=8192):
    try:
        if model.startswith("gpt-5") or model.startswith("o"):
            response = client.responses.create(
                model=model,
                input=msgs,
                max_output_tokens=max_tokens,
                reasoning={"effort": "high" if cot else "none"} # none, low, medium, high
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
                        thinking_config=types.ThinkingConfig(thinking_level="high" if cot else "minimal") # minimal, low, medium, high
                    )
                )
            except Exception as e:
                print(f"[ERROR calling model]: {e}")
            return response.text, ""
        elif model in together_models:
            response = client.chat.completions.create(
                model=model,
                messages=msgs,
                reasoning={"enabled": cot},
                reasoning_effort="high" if cot else "low", # low, medium, high
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content, None
        elif model in deepinfra_models:
            response = client.chat.completions.create(
                model=model,
                messages=msgs,
                reasoning_effort="high" if cot else "none", # none, low, medium, high
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content, None
        elif model in anthropic_models:
            try:
                response = client.messages.create(
                    model=model,
                    messages=msgs,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    output_config={"effort": "high" if cot else "low"},  # low, medium, high, max
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


def random_time(start_hour: int, end_hour: int) -> str:
    if not (0 <= start_hour < 24 and 0 < end_hour <= 24 and start_hour < end_hour):
        raise ValueError("(0 <= start_hour < end_hour <= 24)")

    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}", f"{hour+1:02d}:{minute:02d}"