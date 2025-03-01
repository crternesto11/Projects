import pandas as pd
import re
import os
from pdfminer.high_level import extract_text
from openai import OpenAI
from functions import get_inner_text, get_synonyms, get_terms, get_req_tags, rebuild_prompts

def Job_query(init_prompt, check_prompt, count_prompt, synonyms_prompt):
    
    ##initialize connection
    client = OpenAI(
        # defaults to os.environ.get("OPENAI_API_KEY")
        api_key = "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",
    )
    conversation_history = []

    ##1. prompt for initial results
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": init_prompt, "tempreture": 0.6}
            ]
    )
    conversation_history.append({"role": "user", "content": init_prompt})
    conversation_history.append({"role": "assistant", "content": response.choices[0].message.content.strip()})

    ##2. check if there are mistakes
    response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "system", "content": "You are a helpful assistant."},
            *conversation_history,
            {"role": "user", "content": check_prompt, "temperature": 0.6}]
    )
    #conversation_history.append({"role": "user", "content": check_prompt})
    conversation_history.append({"role": "assistant", "content": response.choices[0].message.content.strip()})

    ##3. calculate the correct number for skills set
    response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "system", "content": "You are a helpful assistant."},
            *conversation_history,
            {"role": "user", "content": count_prompt, "temperature": 0.6}]
    )
    #conversation_history.append({"role": "user", "content": count_prompt})
    conversation_history.append({"role": "assistant", "content": response.choices[0].message.content.strip()})

    ##4. make synonyms
    response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "system", "content": "You are a helpful assistant."},
            *conversation_history,
            {"role": "user", "content": synonyms_prompt, "temperature": 0.4}]
    )

    return response.choices[0].message.content.strip()

### main function ###
def generate_query(file_path):
    ##Get the prompts
    with open('./prompts/init_prompt.txt') as f:
        init_prompt = f.read()

    with open('./prompts/check_prompt.txt') as f:
        check_prompt = f.read()
        
    with open('./prompts/count_prompt.txt') as f:
        count_prompt = f.read()

    with open('./prompts/synonyms_prompt.txt') as f:
        synonyms_prompt = f.read()

    ## get the libraries
    synonyms = get_synonyms()
    terms = get_terms()
    R_tags, N_tags = get_req_tags()

    ##Adding the requirements prompts
    sentences = ['rather than nice to have:','rather than required:']
    new_prompt = rebuild_prompts(sentences[0], R_tags, init_prompt)
    new_prompt = rebuild_prompts(sentences[1], N_tags, new_prompt)

    #check if file exists
    if os.path.isfile(file_path):
        print(f"Found file: {filename}")
        job_description = get_inner_text(file_path)
        prompt_1 = new_prompt + job_description
        prompt_2 = check_prompt + terms
        prompt_3 = count_prompt + terms
        prompt_4 = synonyms_prompt + synonyms + "\n \n ### job description ###\n" + job_description
        result = Job_query(prompt_1, prompt_2, prompt_3, prompt_4)

        with open('./query/'+filename+'.txt', 'w', encoding='utf-8') as f:
            f.write('REQUIREMENTS\n\n')
            f.write(result)
    else:
        print(f"Not Found file: {filename}")

if __name__ == "__main__":
    folder_path = "./LI_tech_jobdescriptions"
    files = os.listdir(folder_path)
    
    for filename in files[::5]:
        file_path = os.path.join(folder_path, filename)
        generate_query(file_path)
