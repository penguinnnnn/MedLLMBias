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
    "Qwen/Qwen3.5-397B-A17B", "deepseek-ai/DeepSeek-V3.1", "zai-org/GLM-5", "moonshotai/Kimi-K2.5",
    "MiniMaxAI/MiniMax-M2.5", "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
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


def ask_llm(client, model, msgs, temperature=0.0, top_p=1.0, max_tokens=4096):
    try:
        if model.startswith("gpt-5") or model.startswith("o"):
            response = client.responses.create(
                model=model,
                input=msgs,
                max_output_tokens=max_tokens,
                reasoning={"effort": "none"} # none, low, medium, high
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
                        thinking_config=types.ThinkingConfig(thinking_level="minimal") # minimal, low, medium, high
                    )
                )
            except Exception as e:
                print(f"[ERROR calling model]: {e}")
            return response.text, ""
        elif model in together_models:
            response = client.chat.completions.create(
                model=model,
                messages=msgs,
                reasoning={"enabled": False},
                # reasoning_effort="low", # low, medium, high
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
                    thinking={"type": "disabled"},
                    # output_config={"effort": "low"},  # low, medium, high, max
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


def debias(scenario):
    messages = [{"role": "user", "content": """### Role
You are a physician with expertise in clinical communication and a commitment to ensure all patients are treated with dignity. Your task is to rewrite medical notes to remove language that may stigmatize patients while maintaining clinical accuracy.

### Definitions of Stigmatizing Language
You must identify and debias the following three types of stigmatizing language:
1. **Blame**: Language that implies the patient is responsible for their condition or health outcomes, often using judgmental qualifiers that characterize the patient as irresponsible for not accepting, not following, or actively resisting medical recommendations.
2. **Doubt**: Language that undermines a patient’s credibility by implying skepticism regarding a patient’s reported symptoms, experiences, or behaviors, often portraying the patient as untruthful, exaggerating,  or providing unreliable information.
3. **Maligning character**: Descriptions that portray the patient as frustrating, difficult to interact with, or socially undesirable. This includes unnecessary social, economic, or demographic details that are not clinically relevant but may trigger generalized assumptions or negative biases about the patient.

### Instructions
1. **Debias through Paraphrasing**: Rewrite the provided medical note to remove stigmatizing language. Use neutral language that focuses on facts rather than negative characterizations of the patient.
2. **Clinical Information Retention**: Do not omit important clinical information. Every clinically relevant fact present in the original note should be preserved in the output. You may only remove language that is stigmatizing and clinically irrelevant. Information that is clinically important to include but that may be communicated in a stigmatizing way can be rephrased but not removed. 
3. **Zero Hallucination & No Additions**: Do not add any new descriptions, interpretations, or information that is not explicitly stated in the original note. Every word in your output must have a direct correspondence to the facts in the input.
4. **Output Format**: Provide only the debiased version of the note.

### Input Note
""" + scenario}]
    for attempt in range(RETRY_NUM):
        try:
            response_text, reasoning = ask_llm(CLIENT, MODEL, messages)
            if len(response_text) > 100:
                with open('results/gpt-4.1-2025-04-14/original.txt', 'a') as f:
                    f.write(f"{scenario}\n\n\n====================\n\n\n")
                with open('results/gpt-4.1-2025-04-14/debiased.txt', 'a') as f:
                    f.write(f"{response_text}\n\n\n====================\n\n\n")
                break
        except Exception as e:
            print(f"Failed: {e}; Attempt {attempt+1} failed; retrying...")
            time.sleep(1)
    return response_text