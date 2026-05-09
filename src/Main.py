import asyncio
from crawl4ai import AsyncWebCrawler
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import pandas as pd

import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

async def extract_lineup(url):
    # 1. Scrape the website into Markdown
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        markdown_content = result.markdown[:15000]

    # 2. Setup the LLM (Using GPT-4o or Gemini 1.5 Pro)
    #llm = ChatOpenAI(model="gpt-4o", temperature=0)
    llm = ChatGoogleGenerativeAI(
        model="models/gemini-2.5-flash"
    )

    # 3. Define the Extraction Prompt
    prompt = ChatPromptTemplate.from_template(
        "Extract the music festival lineup from this text. "
        "Include Artist Name, Date, and Stage. "
        "Return ONLY a JSON list. Do not include any markdown "
        "formatting or extra text. \n\nText: {text}"
    )

    # 4. Chain and Run
    chain = prompt | llm
    response = chain.invoke({"text": markdown_content})

    # 5. Convert JSON response to CSV
    # (Assuming the LLM returned a clean JSON string)
    import json
    data = json.loads(response.content)
    df = pd.DataFrame(data)
    df.to_csv("festival_lineup.csv", index=False)
    print("CSV Generated!")

# Run it
asyncio.run(extract_lineup("https://www.hinterlandiowa.com/lineup"))