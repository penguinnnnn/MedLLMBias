from dotenv import load_dotenv
from openai import OpenAI
from together import Together
import os
import re



# === Determine backend ===
openai_models = [
    "gpt-5-mini-2025-08-07", "gpt-4.1-2025-04-14"
]

together_models = [
    "Qwen/Qwen3-235B-A22B-Instruct-2507-tput", "deepseek-ai/DeepSeek-V3.1", "zai-org/GLM-4.6", "moonshotai/Kimi-K2-Instruct-0905",
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
]


# === Load API keys from .env ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")


def build_model(model_name):
    if model_name in openai_models:
        client = OpenAI(api_key=OPENAI_API_KEY)
    elif model_name in together_models:
        os.environ["TOGETHER_API_KEY"] = TOGETHER_API_KEY
        client = Together()
    else:
        raise ValueError("❌ WRONG MODEL NAME!")
    return client


def ask_llm(client, model, msgs, temperature=1.0, top_p=1.0, max_tokens=4096):
    try:
        if model.startswith("o"):
            response = client.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=temperature,
                top_p=top_p
            )
        else:
            response = client.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            )
        return response.choices[0].message.content, response.choices[0].message.reasoning
    except Exception as e:
        return f"[ERROR calling model]: {e}"


def extract_last_json(s):
    pattern = r'\{[^{}]*\}'
    matches = re.findall(pattern, s)
    if matches:
        return matches[-1]
    return s