import streamlit as st
import pandas as pd
import requests
import json
import re
import time

st.title("ASO Инструмент аудита")

# --- Поля ввода ---
store = st.selectbox("Выберите стор", ["App Store", "Google Play"])
app_id = st.text_input("Введите ID приложения (Bundle ID или Package Name):")
countries = st.multiselect("Выберите страны:", ['us', 'ru', 'kz', 'de', 'fr', 'gb', 'it'])

# --- Логика запросов ---
def fetch_as_data(app_id, country):
    url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200: return f"Ошибка сервера: {resp.status_code}"
    
    data = resp.json()
    if data['resultCount'] == 0: return "Данных не найдено"
    
    item = data['results'][0]
    return {
        "Title": item.get('trackName'),
        "Subtitle": item.get('subtitle', ''),
        "Icon": f'=IMAGE("{item.get("artworkUrl512")}")',
        "Screenshots": ", ".join([f'=IMAGE("{u}")' for u in item.get('screenshotUrls', [])[:3]])
    }

# --- Интерфейс ---
if st.button("Запустить сбор"):
    results = []
    for country in countries:
        st.write(f"Запрос к {country}...")
        
        if store == "App Store":
            data = fetch_as_data(app_id, country)
            if isinstance(data, dict):
                data['Country'] = country
                results.append(data)
            else:
                st.error(f"{country}: {data}")
        
        time.sleep(2) # Задержка чтобы не банили
    
    if results:
        df = pd.DataFrame(results)
        st.dataframe(df)
        st.download_button("Скачать CSV", df.to_csv(index=False).encode('utf-8'), "audit.csv")
