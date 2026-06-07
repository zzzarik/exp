import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

st.set_page_config(layout="wide")
st.title("📱 ASO Парсер (стабильный режим)")

app_id = st.text_input("ID приложения", "com.miranna.app")
# Для примера оставил только две страны, чтобы проверить связь
countries = ["US", "RU"] 
selected = st.multiselect("Страны:", countries, default=["US"])

if st.button("🚀 Собрать"):
    data_list = []
    # Используем GET запрос, он почти никогда не блокируется
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    for country in selected:
        try:
            url = f"https://play.google.com/store/apps/details?id={app_id}&hl=en&gl={country}"
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Парсим через BeautifulSoup (это надежнее, чем индексы JSON)
                title = soup.find('h1').text if soup.find('h1') else "N/A"
                data_list.append({"Страна": country, "Тайтл": title})
            else:
                st.warning(f"Ошибка {response.status_code} для {country}")
        except Exception as e:
            st.error(f"Сбой сети: {e}")

    if data_list:
        st.table(pd.DataFrame(data_list))
