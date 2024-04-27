import argparse
import boto3
import profile_model
from time import sleep
from selenium import webdriver
from bs4 import BeautifulSoup
from langchain_community.chat_models import BedrockChat
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import Union
from fastapi import FastAPI

# Setup
CHUNK_SIZE = 400000 # Max number of characters per chunk (1 token ~4 characters)
client = boto3.client('bedrock-runtime')
llm = BedrockChat(model_id="anthropic.claude-3-sonnet-20240229-v1:0")
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)
app = FastAPI()

def setupArgs():
    cli = argparse.ArgumentParser(prog="PIIWebScraper", description="Script to collect all PII from a webpage url")
    cli.add_argument("-u", "--url", help="Website URL to scrape", required=False, default="")
    cli.add_argument("-v", "--verbose", help="Show AI output", required=False, action="store_true")
    return cli

def getText(url: str) -> str:
    driver.get(url)
    driver.implicitly_wait(2) # Let the page load
    soup = BeautifulSoup(driver.page_source, "lxml")
    webBody = soup.find('body')
    driver.quit()
    return webBody.getText()

def generate(query):
    parser = JsonOutputParser(pydantic_object=profile_model.Model)

    prompt = PromptTemplate(
        template="Answer the user query.\n{format_instructions}\n{query}\n",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser
    resp = chain.invoke({"query": query})

    print("\n\u001b[34;1mOUTPUT\u001b[0m")
    return resp

def makePrompt(bodyText: str):
    prompt = f"""Act as a Cybersecurity AI helping people find what information is exposed about them online so they can better protect themselves. It is crucial to the user that the data you return is real, accurate, and valid.
                
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
                Respond using only JSON"""
    return prompt

def parse_webpage_console(url: str, args: dict) -> list[str]:
    if len(bodyText) > CHUNK_SIZE:
        print("\n\u001b[33mFetching URL...\u001b[0m")
        bodyText = getText(url)
        bodyText = " ".join(bodyText.split()) # Remove excessive whitespaces to make it easier for LLM to process data
    
        # Split bodyText into halves if it is above the max chunk size
        print("\n\n\u001b[31mCONTEXT OVERFLOW!\u001b[0m")
        print("\u001b[33mSplitting prompts...\u001b[0m")
        promptLH = makePrompt(bodyText[len(bodyText)//2])
        promptRH = makePrompt(bodyText[len(bodyText)//2:])

        print("\u001b[33mGenerating response 1...\u001b[0m")
        print(generate((promptLH)))
        sleep(3)
        print("\u001b[33mGenerating response 2...\u001b[0m")
        print(generate((promptRH)))
    else:
        print("\n\u001b[32mCONTEXT SIZE OK\u001b[0m")
        print("\u001b[33mGenerating response...\u001b[0m")
        prompt = makePrompt(bodyText)
        print(generate((prompt)))

@app.get('/')
def read_root():
    return {"Usage": "Make a request to other endpoints to get user information"}

@app.put('/parse/{page_url}')
async def parse_webpage(url: str) -> dict:
    bodyText = getText(url)
    bodyText = " ".join(bodyText.split())
    prompt = makePrompt(bodyText)
    return generate(prompt)

if __name__ == "__main__":
    cli = setupArgs()
    args = vars(cli.parse_args())
    print(len("Hello world"))
    if args["url"] != "":
        parse_webpage_console(args["url"], args)
    else:
        print("\n\u001b[31mNO ARGUMENTS DETECTED!\u001b[0m")
        print(">> showing default example")
        parse_webpage_console("https://contactout.com/elon-musk-email-44227#:~:text=To%20contact%20Elon%20Musk%20send,%2D888%2D518%2D3752", args)
        # parse_webpage_console("https://en.wikipedia.org/wiki/Bill_Gates")
        # parse_webpage_console("https://www.forbes.com/profile/jeff-bezos")
        # parse_webpage_console("https://github.com/google/leveldb/blob/main/AUTHORS")
        # parse_webpage_console("https://www.cs.helsinki.fi/u/torvalds/", args)
        # parse_webpage_console("https://www.ukstudycentre.co.uk/stories/egor-vert/", args)
