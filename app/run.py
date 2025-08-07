from bs4 import BeautifulSoup
import requests
import pandas as pd
from langchain_core.prompts import PromptTemplate
#from langchain_community.llms import Ollama
from langchain_ollama import ChatOllama
from langchain.chains import LLMChain
#from langchain.chat_models import ChatOpenAI  # для GPT-3.5/4
from langchain_openai import ChatOpenAI
import json
import os
from dotenv import load_dotenv

import gspread
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

api_key = os.getenv("OPEN_API_KEY", "")
#print(api_key)
#exit()



# 1. Авторизація
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# 2. Відкриваємо Google Таблицю
spreadsheet = client.open_by_key('1spG9Orhh6xEsfFjaGzR5Dm0bJDE9mwgZlwkmUXNyrWY')  # або по ID: client.open_by_key("ID")


# 3. Вибираємо лист (sheet)
worksheet = spreadsheet.worksheet("Sheet1")


#print(worksheet)
#exit()



headers = {
    'User-Agent': 'Mozilla/5.0',
    'Accept-Language': 'en-US,en;q=0.5'
}

link = 'https://www.artificialintelligence-news.com/feed/'

### load page
res = requests.get(link, headers=headers)


bs = BeautifulSoup(res.content, "xml")
items = bs.find_all('item')

path_to_cache  = 'data.json'
path_to_result = 'parsed_data.xlsx'

### загружаем кеш

def load_cache(filename):

    data_cache = {}

    # Проверка на существование файла
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            data_cache = json.load(f)

    return data_cache




data_loaded = load_cache(path_to_cache)


####



data = []

if os.path.exists(path_to_result):
    df = pd.read_excel(path_to_result)
    data = df.to_dict(orient="records")



llm = ChatOpenAI(
    model_name="gpt-4.1-nano",      # або "gpt-3.5-turbo"
    temperature=0,         # бажано зменшити для парсингу
    openai_api_key=api_key  # або використовуй через os.environ
)

prompt = PromptTemplate(
    input_variables=["context"],
    template="""
        Ты переводчик текстов с английского на русский. 
        Ниже — текст на английском:

        {context}

        Нужно на русском языке и в раза 3 компактней описать то что сказано в статье
    
    """
)

prompt2 = PromptTemplate(
    input_variables=["context"],
    template="""
        Ты переводчик заголовков статей с английского на русский . 
        Ниже — заголовков на английском:

        {context}

    """
)

chain = LLMChain(llm=llm, prompt=prompt)
chain_title = LLMChain(llm=llm, prompt=prompt2)

for item in items:

  title = item.title.string if item.title else ""

  post = {
        'title': item.title.string,
        'summary' : '',
        'link': item.link.string ,
        'cta': "Попробовать аналог у нас → ResearchBot Pro",
        'tags': [],
        'source': "ArtificialIntelligence-News",
        'publishedAt' : item.pubDate.string,
        #'image' : ''
  }


  ## проверяем что мы такое уже добавляли все это
  if item.link.string in data_loaded:
      continue


  cats = item.find_all('category')
  categories = []
  for cat in cats:
    categories.append(cat.string)

  post['tags'] = categories


  content = item.find('content:encoded')
  if content:
      # парсим HTML внутри <content:encoded>
    soup = BeautifulSoup(content.text, "html.parser")
    clean_content = soup.get_text(" ", strip=True)  # все теги -> текст
    post['summary'] = clean_content

  title_ru = chain_title.run({"context": title})
  text_ru = chain.run({"context": clean_content})

  post['title'] = title_ru
  post['summary'] = text_ru

  data.append(post)
  data_loaded[item.link.string] = item.link.string
  #break

#print(data)

# превращаем в DataFrame
df = pd.DataFrame(data)
df.to_excel(path_to_result, index=False)


# 5. Запис Pandas DataFrame в Google Sheet
worksheet.clear()  # Очистити перед оновленням (можна не викликати, якщо хочеш оновлювати вручну)
set_with_dataframe(worksheet, df)

### save cache
with open(path_to_cache, "w", encoding="utf-8") as f:
    json.dump(data_loaded, f, ensure_ascii=False, indent=4)



