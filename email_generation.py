import pandas as pd
from openai import APIConnectionError, OpenAI
import requests
from requests.exceptions import ChunkedEncodingError
import json
import copy
import time
import sys

# functions from other files
from functions.Profile_WeatherAPI import get_weather
from functions.data_collection import get_highest_tech, get_best_email_address, get_names, get_valuable_aspects
from functions.first_sentence_prompts import expertises_prompt, check_school_US, check_jokes, weather_prompt, generic_prompt


def read_data_from_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()

            # 1. Find original job query
            start = content.find('OpenAI Query:')
            if start == -1:
                print("Error: Could not find 'OpenAI Query:' in the file")
                return None
            
            # Move start to the beginning of the query
            start = content.find('{')
            if start == -1:
                print("Error: Could not find valid JSON object in the file")
                return None
            
            end = content.find('Query:', start)
            if end == -1:
                print("Error: Could not find valid Elasticsearch result in the file")
                return None
            
            # get the job query
            jd_query_str = content[start:end].strip()

            # Parse the JSON object
            jd_data = json.loads(jd_query_str)
            

            # 2. Find the start of the JSON object after 'Output:'
            start = content.find('Output:')
            if start == -1:
                print("Error: Could not find 'Output:' in the file")
                return None

            # Move start to the beginning of the JSON object
            start = content.find('{', start)
            if start == -1:
                print("Error: Could not find valid JSON object after 'Output:' in the file")
                return None

            # Extract the JSON string from the start position to the end of the file
            json_str = content[start:].strip()

            # Parse the JSON object
            data = json.loads(json_str)

            # Extract profiles and their information
            profiles = []
            hits = data.get('hits', {})
            for hit in hits.get('hits', []):
                profile_id = hit.get('_id', 'unknown ID')
                profile = hit.get('_source', {})
                locations = [loc['location'] for loc in profile.get('locations', []) if 'location' in loc]
                social_urls =  profile.get('soc_urls', [])
                expertises = profile.get('expertises', [])
                profiles.append({'id': profile_id, 
                                 'social_urls': get_best_email_address(social_urls), 
                                 'expertises': get_highest_tech(expertises),
                                 'hireable': profile.get('hireable', 'unknown status'),
                                 'yoe_list': [{**item, 'years': round(item['years'])} for item in profile.get('yoe_list', [])],
                                 'prev_titles': [title['title'] for title in profile.get('prev_titles', [])],
                                 'techs': profile.get('techs', []),
                                 'name': get_names(profile.get('person_profile', "empty profile")),
                                 'schools': profile.get('schools', []),
                                 'industries': profile.get('industries', []),
                                 'full_info': profile.get('full_info', 'unknown info'),
                                 'locations': locations,
                                 'weather': get_weather(locations[0].split(',')[0].strip())})

            return jd_data, profiles

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file {file_path}")
        print(f"JSON error message: {str(e)}")
        return None
    

def email_generator(email_generation_prompt: str, ending_checking_prompt: str,spam_checking_prompt: str):

    ##initialize connection
    client = OpenAI(
        # defaults to os.environ.get("OPENAI_API_KEY")
        api_key = "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",
    )
    conversation_history = []

    ##1. Generate the email
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": email_generation_prompt, "tempreture": 0.6}
            ]
    )
    conversation_history.append({"role": "user", "content": email_generation_prompt})
    conversation_history.append({"role": "assistant", "content": response.choices[0].message.content.strip()})

    ##2. Writing the ending
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            *conversation_history,
            {"role": "user", "content": ending_checking_prompt, "tempreture": 0.5}
            ]
    )
    conversation_history.append({"role": "user", "content": email_generation_prompt})
    conversation_history.append({"role": "assistant", "content": response.choices[0].message.content.strip()})

    ##3. checking spam words
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            *conversation_history,
            {"role": "user", "content": spam_checking_prompt, "tempreture": 0.6}
            ]
    )

    return response.choices[0].message.content.strip()


#main function
def email_generation(file_path):
    # Read data from JSON file
    jd_query, profiles = read_data_from_json(file_path)

    if jd_query is None or profiles is None:
        print("Error: Could not find job description or profiles data in the file")
        return None

    # get the valuable aspects from the job description
    valuable_aspects = get_valuable_aspects(jd_query['job_description'][0])
    if not valuable_aspects:
        valuable_aspects = 'use generic template'

    # get the prompts for email generation
    with open("./prompts/email_generation_prompt.txt") as f:
        email_generation_prompt = f.read()

    with open("./prompts/ending_checking_prompt.txt") as f:
        ending_checking_prompt = f.read()

    with open("./prompts/spam_checking_prompt.txt") as f:
        spam_checking_prompt = f.read()

    spam_words_library = pd.read_excel("./libraries/Negative Spam List.xlsx").iloc[:, 0].tolist()
    ending_library = pd.read_csv("./libraries/CTA.csv").iloc[:, 0].tolist()



    # generate the emails
    emails = []
    spam_total ={}


    check_list = ["b781e453-51bf-49ba-8af7-a634b84ba9b4",
        "59272f80-1c85-4488-b067-add848266f8b",
        "14c364d2-db2c-41b2-a906-31d3cee4b17a",
        "e73d4245-da91-4270-bd77-4692553aec18",
        "4119ab3c-c2f1-4820-981d-cabaef4e7694",
        "64e95565-0c09-43e8-b725-f54fbc3c73dc",
        "42478be0-8310-4ce1-94c3-495d39c9094e",
        "d56b16a7-fc46-4a76-ac3d-77b5b9fa53f7"
    ]

    profile_checking = []
    for profile in profiles:
        if profile['id'] in check_list:
            profile_checking.append(profile)





    for profile in profile_checking:

        ## Decide which first sentence to use and generate the first sentence
        while True:
            # if high expertises, use expertises prompt
            if profile['expertises']:     
                first_sentence = expertises_prompt(profile['expertises'], profile['name'].split(' ')[0])
                break

            # if have bachelor's degree in US, use school prompt
            result = check_school_US(profile['schools'], profile['name'].split(' ')[0])
            print(result)
            if result:
                first_sentence = result
                break
            
            # if joke correlated to job or skill, use joke prompt
            result = check_jokes(profile['techs'], jd_query['techs_req'], profile['name'].split(' ')[0])
            if result:
                first_sentence = result
                break
            
            # if location is not empty, use location prompt
            if len(profile['locations']) > 0:
                first_sentence = weather_prompt(profile['weather'], profile['name'].split(' ')[0])
                break

            # if none of the above satisfied, use generic prompt
            first_sentence = generic_prompt(profile['yoe_list'], profile['techs'], profile['name'].split(' ')[0])
            break
        
        # remove unnecessary keys from the jd before generating the email
        temp_jd = copy.deepcopy(jd_query)
        temp_jd.pop('job_description')

        # Generate the email_generation_prompt and spam_checking_prompt
        email_prompt = email_generation_prompt + first_sentence + '\n' + \
        '### valuable aspects of the job ###' + '\n' + valuable_aspects + '\n' + \
        '### candidate\'s information ###' + '\n' + str(profile) + '\n' + \
        '### job requirements ###' + '\n' + str(temp_jd)

        ending_prompt = ending_checking_prompt + '\n' + str(ending_library) + '\n'

        spam_prompt = spam_checking_prompt + '\n' + str(spam_words_library)

        content = email_generator(email_prompt, ending_prompt, spam_prompt)
        print(content)
        
        for word in spam_words_library:
            if word.lower() in content.lower():
                print(word)
                spam_total[word] = spam_total.get(word, 0) + 1


        emails.append({'email': profile['social_urls'][0], 'content':content})

    with open('email_generation.txt', 'w') as f:
        for email in emails:
            f.write(email['email'])
            f.write('\n')
            f.write(email['content'])
            f.write('\n------------------------------------------------\n')
    
    print(spam_total)



if __name__ == '__main__':

    while True:
        try:
            email_generation('./mlm_with_fuzzy.json')
            break

        except (APIConnectionError, ChunkedEncodingError) as e:
            time.sleep(10)

        finally:
            exc_type, exc_value, exc_traceback = sys.exc_info()

            if exc_value:
                raise exc_value
            break
