from pdfminer.high_level import extract_text
from openai import OpenAI
import pandas as pd
import re

#get the job description part and remove unimportant links
def get_inner_text(filename):
    text = extract_text(filename) #get the job description for each pdf as prompt text by OCR

    start = text.index("Prem")
    end = text.index("See less")
    breakpoint_1 = text.index("employees")
    breakpoint_2 = text.index("About the job")

    new_text = text[start + 4:breakpoint_1] + text[breakpoint_2:end]
    try:
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        clean_text = re.sub(url_pattern, '', new_text)
        return clean_text
    except:
        return new_text

def get_synonyms():    
    synonyms = pd.read_excel('./libraries/Synonyms.xlsx')
    data = synonyms.iloc[:,2:].to_dict()
    cleaned_lists = [[v for v in v_dict.values() if pd.notnull(v)] for v_dict in data.values()]

    str_lists = [', '.join(sub_list) for sub_list in cleaned_lists]
    final_str = '[' + '], ['.join(str_lists) + ']'

    return final_str

def get_terms():
    term_1 = pd.read_csv('./libraries/Skills_tags_1.csv')
    term_2 = pd.read_csv('./libraries/Skills_tags_2.csv')

    new_term = term_1["javascript"].tolist()
    new_term.append("javascript")

    new_term = new_term + term_2["Keyword"].tolist()
    new_term = list(set(new_term))

    return ', '.join([f'"{item}"' for item in new_term])

def get_req_tags():
    tag_1 = pd.read_excel('./libraries/Requirements.xlsx').dropna()
    R_tags = tag_1.iloc[:,0].to_list()
    N_tags = tag_1.iloc[:,1].to_list()
    return ', '.join(R_tags), ', '.join(N_tags)

def rebuild_prompts(sentences, insert_words, prompt):
    return prompt[:prompt.index(sentences)+len(sentences)] + insert_words + prompt[prompt.index(sentences)+len(sentences):]
