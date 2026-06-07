import streamlit as st
import pandas as pd
import pycountry
import requests
import re

st.set_page_config(page_title="ASO IMAGE Formula Parser", layout="wide")

st.title("📱 Глобальный ASO Парсер с формулой =IMAGE()")
st.caption("Автоматически генерирует формулы для иконок и до 8 скриншотов в отдельных ячейках")

platform = st.selectbox("1. Выберите платформу", ["Google Play", "App Store"])
app_id = st.text_input("2. Введите ID приложения (бандл)", placeholder="com.instagram.android / id389801252")

ALL_COUNTRIES = {c.alpha_2.lower(): c.name for c in pycountry.countries}

MULTI_LANG_EXCEPTIONS = {
    "sa": ["ar", "en"], "qa": ["ar", "en"], "ae": ["ar", "en"], "kw": ["ar", "en"], 
    "bh": ["ar", "en"], "om": ["ar", "en"], "eg": ["ar", "en"], "jo": ["ar", "en"], "lb": ["ar", "en"],
    "dz": ["ar", "fr", "en"], "ma": ["ar", "fr", "en"], "tn": ["ar", "fr", "en"],
    "us": ["en", "es"], "ca": ["en", "fr"], "ch": ["de", "fr", "it"], "be": ["nl", "fr", "de"],
    "cy": ["el", "tr", "en"], "hk": ["zh-HK", "en"], "tw": ["zh-TW", "en"], "sg": ["en", "zh-CN", "ms"],
    "my": ["ms", "en", "zh-CN"], "ph": ["tl", "en"], "fi": ["fi", "sv"], "za": ["en", "af"],
    "kz": ["kk", "ru"], "ua": ["uk", "ru"], "by": ["be", "ru"], "uz": ["uz", "ru"], 
    "kg": ["ky", "ru"], "md": ["ro", "ru"], "am": ["hy", "ru"], "ge": ["ka", "ru"], "az": ["az", "ru"],
}

selected_countries = st.multiselect(
    "3. Выберите любые страны мира:",
    options=list(ALL_COUNTRIES.keys()),
    format_func=lambda x: f"{ALL_COUNTRIES[x]} ({x.upper()})"
)

def get_official_languages(country_code):
    if country_code in MULTI_LANG_EXCEPTIONS:
        return MULTI_LANG_EXCEPTIONS[country_code]
    return [country_code, "en"]

# --- Основные функции парсинга ---
def parse_google_play(bundle, country, lang):
    url = f"https://play-store-api.asotools.workers.dev/api/apps/{bundle}?lang={lang}&country={country}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            item = res.json()
            if "title" in item:
                # Получаем список скриншотов (если они есть)
                scr_list = item.get("screenshots", [])
                return {
                    "Platform": "Google Play", "Country": ALL_COUNTRIES[country], "GL": country.upper(), "HL": lang.upper(),
                    "Title": item.get("title"), "Subtitle / Short": item.get("summary"), "Description": item.get("description"),
                    "Icon": item.get("icon"), "Screenshots": scr_list
                }
    except Exception: pass
    return None

def parse_app_store(app_id, country):
    if "id" in app_id:
        match = re.search(r'id(\d+)', app_id)
        if match: app_id = match.group(1)
            
    url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            json_data = res.json()
            if json_data.get("resultCount", 0) > 0:
                item = json_data["results"][0]
                return {
                    "Platform": "App Store", "Country": ALL_COUNTRIES[country], "GL": country.upper(), "HL": "DEFAULT",
                    "Title": item.get("trackName"), "Subtitle / Short": item.get("subtitle", ""), "Description": item.get("description"),
                    "Icon": item.get("artworkUrl100"), "Screenshots": item.get("screenshotUrls", [])
                }
    except Exception: pass
    return None

# --- Обработка и генерация таблицы ---
if st.button("🚀 Сгенерировать ASO таблицу", type="primary"):
    if not app_id:
        st.error("Введите ID приложения!")
    elif not selected_countries:
        st.error("Выберите страны!")
    else:
        raw_results = []
        
        with st.spinner("Парсим метаданные..."):
            for country in selected_countries:
                if platform == "Google Play":
                    langs = get_official_languages(country)
                    for lang in langs:
                        data = parse_google_play(app_id, country, lang)
                        if data: raw_results.append(data)
                else:
                    data = parse_app_store(app_id, country)
                    if data: raw_results.append(data)
                        
        if raw_results:
            processed_rows = []
            
            for item in raw_results:
                # Базовые текстовые данные
                row = {
                    "Платформа": item["Platform"],
                    "Страна": item["Country"],
                    "ГЕО (gl)": item["GL"],
                    "Язык (hl)": item["HL"],
                    "Тайтл": item["Title"],
                    "Субтитл": item["Subtitle / Short"],
                    "Описание": item["Description"],
                    # Оборачиваем иконку в формулу
                    "Иконка": f'=IMAGE("{item["Icon"]}")' if item["Icon"] else ""
                }
                
                # Добавляем до 8 скриншотов в отдельные колонки, оборачивая каждый в =IMAGE()
                screenshots = item["Screenshots"][:8] # берем максимум 8 штук
                for i in range(1, 9):
                    if i <= len(screenshots):
                        row[f"Скриншот {i}"] = f'=IMAGE("{screenshots[i-1]}")'
                    else:
                        row[f"Скриншот {i}"] = "" # пустая ячейка, если скриншотов меньше 8
                        
                processed_rows.append(row)
                
            df = pd.DataFrame(processed_rows)
            # Пересобираем порядок колонок, чтобы картинки шли первыми или логично структурировались
            base_cols = ["Платформа", "Страна", "ГЕО (gl)", "Язык (hl)", "Иконка", "Тайтл", "Субтитл", "Описание"]
            scr_cols = [f"Скриншот {i}" for i in range(1, 9)]
            df = df[base_cols + scr_cols]
            
            st.success("Таблица с формулами готова!")
            st.dataframe(df) # Внутри Streamlit будут видны сами формулы, это нормально
            
            # Сохраняем в полноценный XLSX, чтобы формулы работали
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="ASO Meta")
            buffer.seek(0)
            
            st.download_button(
                label="📥 Скачать Excel (.xlsx) с автозагрузкой картинок",
                data=buffer,
                file_name=f"aso_formulas_export_{app_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Ничего не найдено.")
