import streamlit as st
import pandas as pd
import pycountry
import requests
import json

st.set_page_config(layout="wide")
st.title("📱 Глобальный ASO Парсер")

# 1. База стран и групп
ALL_COUNTRIES = {c.alpha_2.upper(): c.name for c in pycountry.countries}
GEO_GROUPS = {
    "Tier-1 (Запад)": ["US", "CA", "GB", "DE", "FR", "IT", "ES", "AU"],
    "Tier-1 (Азия)": ["JP", "KR", "CN", "TW", "SG"],
    "Евросоюз (EU)": ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"],
    "ЛАТАМ (LATAM)": ["BR", "MX", "AR", "CO", "CL", "PE"],
    "Ближний Восток / MENA": ["SA", "AE", "EG", "TR", "IL", "QA", "KW", "BH", "OM", "JO", "LB"],
    "СНГ и Смежные": ["RU", "KZ", "BY", "UZ", "AM", "GE", "UA", "KG", "MD", "AZ"]
}

# 2. Интерфейс
app_id = st.text_input("ID приложения", "com.miranna.app")
selected_groups = st.multiselect("Выберите группы регионов:", list(GEO_GROUPS.keys()))

# Формируем список стран: из групп + ручной выбор
group_countries = [c for g in selected_groups for c in GEO_GROUPS[g]]
manual_countries = st.multiselect("Добавить/удалить страны:", options=list(ALL_COUNTRIES.keys()), default=list(set(group_countries)))

if st.button("🚀 Собрать данные по всем странам"):
    results = []
    # Заголовки для обхода блокировок
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    with st.spinner("Загрузка..."):
        for country in manual_countries:
            url = "https://play.google.com/_/PlayStoreUi/data/batchexecute"
            # Параметры запроса
            params = {"f.req": f'[[["jQ136b","[[\\"{app_id}\\",7,null,1]]",null,"generic"]]]', "hl": "en", "gl": country}
            
            try:
                res = requests.post(url, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    raw_data = json.loads(res.text.split("\n")[2])[0][2]
                    data = json.loads(raw_data)
                    
                    # Извлечение данных из структуры массива (по индексу)
                    details = data[1][2]
                    results.append({
                        "Страна": country,
                        "Тайтл": details[0][0],
                        "Шорт": details[73][0][1],
                        "Лонг": details[72][0][1][:100]
                    })
            except Exception as e:
                st.error(f"Ошибка в {country}: {e}")
            
    if results:
        st.dataframe(pd.DataFrame(results))
        # Кнопка скачивания
        csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Скачать CSV", csv, "aso_data.csv", "text/csv")
