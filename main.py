import argparse
import os
import json
from time import sleep
from selenium import webdriver
from bs4 import BeautifulSoup
from requests import post, delete
from requests import get as get_req


class CheckerModel:
    modelfilePath = "Modelfile.txt"
    name = "checker"

    def modelExists(self):
        res = get_req("http://localhost:11434/api/tags")
        names = [model['name'] for model in res.json().get('models', [])]
        return "checker:latest" in names

    def create(self):
        with open(self.modelfilePath, "r") as file:
            modelfile = file.read()

        res = post("http://localhost:11434/api/create", json={
            "name": self.name,
            "modelfile": modelfile,
            "stream": False
        })
        if "success" in res.json().get("status"):
            return True
        else:
            print("\n!!! ERROR !!!\n", res.json())
            return False
        
    def delete(self):
        query = delete("http://localhost:11434/api/delete", json={
            "name": self.name
        })
        return query.status_code

    def useModel(self, data):
        query = post("http://localhost:11434/api/generate", json={
            "model": self.name,
            "prompt": data,
            "format": "json",
            "stream": False
        })
        print("\n\u001b[34;1mCHECKER RESPONSE:\u001b[0m")
        print(query.json().get("response"))
    

# Setup
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

def getText(url: str) -> str:
    driver.get(url)
    driver.implicitly_wait(2) # Let the page load
    soup = BeautifulSoup(driver.page_source, "lxml")
    webBody = soup.find('body')
    driver.quit()
    return webBody.getText()


def getPII(bodyText: str):
    query = post("http://localhost:11434/api/generate", json={  
        "model": "llama2-uncensored",
        "prompt": f"""Act as a Cybersecurity AI helping people find what information is exposed about them online so they can better protect themselves. It is crucial to the user that the data you return is real, accurate, and valid.
                    
                    You must find all data in the text provided at the end of the prompt that relates to a person and can be classified using the labels below:
                    'email',
                    'name' (first name, last name, middle name, author name, contributor name, nickname),
                    'phone',
                    'date of birth',
                    'age',
                    'passport_number',
                    'drivers_license',
                    'credit_card_number',
                    'IBAN',
                    'home_address',
                    'work address',
                    'education_information',
                    'employment_information',

                    Return raw data as a collection of JSON objects where the key is the individual and the value is the JSON object containing data associated with the person.
                    If some data is missing, skip the label entirely in your response.
                    Return only the data you find in the provided text. 
                    Do not make up data if you don't know it. 
                    Do not return template data such as "John Doe", "John Smith", or "Jane Smith".
                    Do not write messages, emails or paragraphs.
                    Here is the text you must process and scan for personal data: {bodyText}
                    Respond using only JSON""",
        "stream": False,
        "format": "json",
        "options" : {"temperature": 0.5}})
    return query.json().get("response")

def verifyData(data, text) -> list[str]:
    cleanData = []
    
    def check_and_append(item):
        if isinstance(item, str) and item in text:
            cleanData.append(item)
        elif isinstance(item, list):
            if not item:
                return
            for sub_item in item:
                check_and_append(sub_item)
        elif isinstance(item, dict):
            for key, value in item.items():
                check_and_append(value)
    
    for key, value in data.items():
        check_and_append(value)

    return cleanData

def parse_webpage(url: str, args: dict) -> list[str]:
    print("\u001b[33mFetching URL...\u001b[0m")
    bodyText = getText(url)
    bodyText = " ".join(bodyText.split()) # Remove excessive whitespaces to make it easier for LLM to process data
    
    print("\u001b[33mGenerating response...\u001b[0m")
    res = getPII(bodyText)
    
    if args["verbose"]:
        os.system('clear')
        print("\u001b[34;1mRAW DATA:\u001b[0m")
        print(res.rstrip("\n"))

    if args["check"]:
        checker = CheckerModel()
        if checker.modelExists() and args["remake"]:
            print("\n\u001b[33;1m>> Model found, re-making model\n\u001b[0m")
            checker.delete()
            print("\u001b[31m>> Model deleted...\u001b[0m")
            status = checker.create()
            print("\u001b[32m>> Model created with status", status, "\u001b[0m")
        elif checker.modelExists:
            print("\n\u001b[33;1m>> Model found, using existing model\n\u001b[0m")
        else:
            print("\n\u001b[33;1m>> No existing model has been found\n\u001b[0m")
            print("creating...")
            status = checker.create()
            print("\u001b[32m>>Model created with status", status, "\u001b[0m")
        checker.useModel(res)

    try:
        responseList = json.loads(res)
        d = verifyData(responseList, bodyText)
        return d
    except json.decoder.JSONDecodeError:
        print("\n\u001b[31mEncountered an error with the output. Trying again...\u001b[0m")
        res = res + '}'
        responseList = json.loads(res)
        d = verifyData(responseList, bodyText)
        return d


if __name__ == "__main__":
    cli = argparse.ArgumentParser(prog="PIIWebScraper", description="Script to collect all PII from a webpage url")
    cli.add_argument("-u", "--url", help="Website URL to scrape", required=False, default="")
    cli.add_argument("-v", "--verbose", help="Show AI output", required=False, action="store_true")
    cli.add_argument("-c", "--check", help="Use checker model", required=False, action="store_true")
    cli.add_argument("-r", "--remake", help="Remake checker model", required=False, action="store_true")
    args = vars(cli.parse_args())
    if args["url"] != "":
        out = parse_webpage(args["url"], args)
    else:
        out = parse_webpage("https://contactout.com/elon-musk-email-44227#:~:text=To%20contact%20Elon%20Musk%20send,%2D888%2D518%2D3752", args)
        # parse_webpage("https://en.wikipedia.org/wiki/Bill_Gates")
        # parse_webpage("https://www.forbes.com/profile/jeff-bezos")
        # parse_webpage("https://github.com/google/leveldb/blob/main/AUTHORS")
        # parse_webpage("https://www.cs.helsinki.fi/u/torvalds/", args)
    
    print("\n\u001b[34;1mOUTPUT\u001b[0m", out)
