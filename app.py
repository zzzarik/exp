import streamlit as st
import pandas as pd
import pycountry
from google_play_scraper import app as gp_app

st.set_page_config(layout="wide")
st.title("📱 ASO Парсер (на скрапере)")

# 1. Списки стран и групп
ALL_COUNTRIES = {c.alpha_2.upper(): c.name for c in pycountry.countries}
GEO_GROUPS = {
    "Tier-1 (Запад)": ["US", "CA", "GB", "DE", "FR", "IT", "ES", "AU"],
    "СНГ": ["RU", "KZ", "BY", "UA", "AM", "GE"],
    "ЛАТАМ": ["BR", "MX", "AR", "CO", "CL", "PE"]
}

# 2. Интерфейс
app_id = st.text_input("ID приложения", "com.miranna.app")
selected_groups = st.multiselect("Выберите группы:", list(GEO_GROUPS.keys()))
all_country_keys = list(ALL_COUNTRIES.keys())
manual_countries = st.multiselect("Страны для сбора:", options=all_country_keys, 
                                 default=list(set([c for g in selected_groups for c in GEO_GROUPS[g]])))

# 3. Сбор данных
if st.button("🚀 Начать сбор"):
    results = []
    with st.spinner("Работаем через скрапер..."):
        for country in manual_countries:
            try:
                # Официальный метод скрапера
                data = gp_app(app_id, lang='en', country=country)
                results.append({
                    "Страна": country,
                    "Тайтл": data.get('title'),
                    "Шорт": data.get('summary'),
                    "Описание": data.get('description')[:150] + "...",
                    "Иконка": data.get('icon')
                })
            except Exception as e:
                st.error(f"Ошибка в {country}: {e}")
    
    if results:
        st.dataframe(pd.DataFrame(results))
