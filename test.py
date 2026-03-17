import json
import random
import os
import time
from utils import *
from vignettes import *


# === Configuration ===
_NAME = ["R"] # "F", "L", "R", "X"
_AGE = ["32"] # "25", "26", "27", "28", "29", "30", "31", "32", "44", "45", "46", "47"
_RACE = ["Black"] # "Black", "White", "Asian", "Hispanic"
_GENDER = ["Woman"] # 'Man', 'Woman'
_SO = ["homo"] # "hetro", "homo"
_LANGUAGE = ["Stigmatizing_Doubt", "Stigmatizing_Blame", "Stigmatizing_Stereotyping"] # "Neutral", "Stigmatizing", "Stigmatizing_Doubt", "Stigmatizing_Blame", "Stigmatizing_Stereotyping"
_NUM_STIG = [1, 4, 7, 14, 21]
_NUM_PER_CAT = 7
_DISEASE = ["SCD"] # "SCD", "Obesity"
_TEST = ["pass"] # "pain", "pass", "knee"
_COT = False
_DEBIAS = False
RETRY_NUM = 10

MODEL = 'MiniMaxAI/MiniMax-M2.5'
CLIENT = build_model(MODEL)

NAME_IN_PATH = MODEL.split("/")[-1]
COT_STRING = "cot" if _COT else "direct"
if _DEBIAS:
    COT_STRING += "_debias"


def construct_scenario(disease, scenario_type, stig_num=100000):
    if "_" in scenario_type:
        stig_lang_type = [scenario_type.split("_")[-1]]
    elif scenario_type == "Stigmatizing":
        stig_lang_type = ["Doubt", "Blame", "Stereotyping"]
    elif scenario_type == "Neutral":
        stig_lang_type = []

    sentence_versions, configurable_scenario = select_scenario(disease)
    stig_target = [s for s in sentence_versions if sentence_versions[s]["Type"] in stig_lang_type]
    stig_num = min(stig_num, len(stig_target))
    stig_lang = random.sample(stig_target, stig_num)
    scenario_sentences = {s: sentence_versions[s]["Stigmatizing"] if s in stig_lang else sentence_versions[s]["Neutral"] for s in sentence_versions}

    scenario = f"{configurable_scenario}"
    for s in scenario_sentences:
        scenario = scenario.replace(s, scenario_sentences[s])

    return scenario


def construct_prompt(scenario, test_name, name, age, race, gender, so):
    parts = []
    if MODEL.startswith("gemini"):
        parts.append({"text": "You are a clinician. Here is a note of a patient:"})
    else:
        messages = [{"role": "user", "content": "You are a clinician. Here is a note of a patient:"}]
    if gender.lower() == "man":
        name = "Mr. " + name
        pronoun = ["he", "him", "himself", "his"]
        if so.lower() == "homo":
            partner = "boyfriend"
        elif so.lower() == "hetro":
            partner = "girlfriend"
    elif gender.lower() == "woman":
        name = "Miss " + name
        pronoun = ["she", "her", "herself", "her"]
        if so.lower() == "homo":
            partner = "girlfriend"
        elif so.lower() == "hetro":
            partner = "boyfriend"
    time1, time2 = random_time(12, 14)
    scenario = scenario.replace("<NAME>", name).replace("<AGE>", age).replace("<RACE>", race).replace("<GENDER>", gender).replace("<PRONOUN_1>", pronoun[0]).replace("<PRONOUN_2>", pronoun[1]).replace("<PRONOUN_3>", pronoun[2]).replace("<PRONOUN_4>", pronoun[3]).replace("<PARTNER>", partner).replace("<TIME_1>", time1).replace("<TIME_2>", time2)
    if _DEBIAS:
        scenario = debias(scenario)
    if MODEL.startswith("gemini"):
        parts.append({"text": scenario})
    else:
        messages.append({"role": "user", "content": scenario})

    if test_name == "pain":
        order = random.sample([i for i in range(len(test_pain[1]))], len(test_pain[1]))
        order_back = None
        instruction = test_pain[0]
        choices = "\n".join([f"{a+1}. {test_pain[1][b]}" for a, b in enumerate(order)])
        thinking_string = test_pain[2]
        if MODEL.startswith("gemini"):
            parts.append({"text": f"{instruction}\n{choices}\n{thinking_string}"})
        else:
            messages.append({"role": "user", "content": f"{instruction}\n{choices}\n{thinking_string}"})

    elif test_name == "knee":
        order = random.sample([i for i in range(len(test_knee[1]))], len(test_knee[1]))
        order_back = None
        instruction = test_knee[0]
        choices = "\n".join([f"{a+1}. {test_knee[1][b]}" for a, b in enumerate(order)])
        thinking_string = test_knee[2]
        if MODEL.startswith("gemini"):
            parts.append({"text": f"{instruction}\n{choices}\n{thinking_string}"})
        else:
            messages.append({"role": "user", "content": f"{instruction}\n{choices}\n{thinking_string}"})

    elif test_name == "pass":
        pass_string = ""
        order = None
        order_back = []
        offset = 0
        for subscale_id in range(len(test_pass[0])):
            order_s = random.sample([i for i in range(len(test_pass[1][subscale_id]))], len(test_pass[1][subscale_id]))
            order_back_s = [i for i in range(len(test_pass[1][subscale_id]))]
            for i in range(len(order_s)):
                order_back_s[order_s[i]] = i
            pass_string += test_pass[0][subscale_id] + "\n" + "\n".join([f"{a+1+offset}. {test_pass[1][subscale_id][b]}" for a, b in enumerate(order_s)]) + "\n\n"
            order_back += [i + offset for i in order_back_s]
            offset += len(test_pass[1][subscale_id])
        
        thinking_string = test_pass[2]
        if MODEL.startswith("gemini"):
            parts.append({"text": pass_string + thinking_string})
        else:
            messages.append({"role": "user", "content": pass_string + thinking_string})
    if MODEL.startswith("gemini"):
        messages = {"role": "user", "parts": parts}
    return messages, order, order_back


def run_test():
    for d in _DISEASE:
        for t in _TEST:
            BASE_DIR = f'results/{d}/{COT_STRING}/{NAME_IN_PATH}/'
            os.makedirs(BASE_DIR, exist_ok=True)
            FILENAME = f'{BASE_DIR}/{t}.csv'
            with open(FILENAME, 'w') as f:
                f.write("Scenario,Name,Age,Race,Gender,SO,answer\n")
            for n in _NAME:
                for a in _AGE:
                    for r in _RACE:
                        for g in _GENDER:
                            for s in _SO:
                                for l in _LANGUAGE:
                                    for p in _NUM_STIG:
                                        if l == "Neutral" and p != 1:
                                            break
                                        if "_" in l and p > _NUM_PER_CAT:
                                            break
                                        print(f"{l}-{p},{n},{a},{r},{g},{s}")
                                        scenario = construct_scenario(d, l, p)
                                        messages, order, order_back = construct_prompt(scenario, t, n, a, r, g, s)
                                        print(messages)
                                        response, answer, reasoning = "", "", ""
                                        for attempt in range(RETRY_NUM):
                                            try:
                                                response_text, reasoning = ask_llm(CLIENT, MODEL, messages, _COT)
                                                response = json.loads(extract_last_json(response_text))
                                                if t == "pain":
                                                    answer = int(response.get("choice", -1))
                                                    if answer != -1:
                                                        answer = order[answer-1] + 1
                                                        break
                                                
                                                elif t == "knee":
                                                    answer = int(response.get("choice", -1))
                                                    if answer != -1:
                                                        answer = order[answer-1] + 1
                                                        break
                                                
                                                elif t == "pass":
                                                    answer = list(response.get("rating", []))
                                                    if len(answer) > 0:
                                                        answer = [answer[i] for i in order_back]
                                                        answer = answer[:4] + [6 - i for i in answer[4:]]
                                                        break
                                            except Exception as e:
                                                print(f"Failed: {e}; Attempt {attempt+1} failed; retrying...")
                                                time.sleep(1)
        
                                        print(answer)
                                        with open(FILENAME, 'a') as f:
                                            write_answer = f"{answer}".replace("[", "").replace("]", "").replace(" ", "")
                                            if t == 'pain':
                                                f.write(f"{l}-{p:02d},{n},{a},{r},{g},{s},{write_answer}\n")
                                            elif t == 'knee':
                                                f.write(f"{l}-{p:02d},{n},{a},{r},{g},{s},{write_answer}\n")
                                            elif t == 'pass':
                                                sum_score = sum(answer)
                                                f.write(f"{l}-{p:02d},{n},{a},{r},{g},{s},{sum_score},{write_answer}\n")
                                        with open(FILENAME.replace('.csv', '_reasoning.txt'), 'a') as f:
                                            if reasoning == "":
                                                reasoning = response_text
                                            f.write(f"{reasoning}\n\n\n====================\n\n\n")


if __name__ == "__main__":
    run_test()
