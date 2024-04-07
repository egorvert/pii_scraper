# PII Scraper

## Description
Example Python script that uses llama2-uncensored LLM to find personal information on a webpage.

## Prerequisites
For this to work, you must have Ollama installed on your local machine. You can install Ollama here: https://ollama.com

You must also have Python3 and pip installed.

## Setup
Clone the repository using `git clone`.

To use the virtual environment, open a terminal in the working directory and run `env/bin/activate`.

Once you have activated the virtual environment, run `pip install -r requirements.txt` to install all the necessary dependencies.

## Usage
Run `python3 main.py -h` to see all available parameters

Run `python3 main.py` without any flags to see a demo how it works.

Use the `-u` flag to specify a custom URL.

You may need to run the script multiple times to see optimal results as the LLM output can be finnicky at times.
