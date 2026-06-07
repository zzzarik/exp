import streamlit as st
import pandas as pd
import pycountry
import requests
import re

st.set_page_config(page_title="ASO Global Pro", layout="wide")

st.title("📱 Глобальный ASO Парсер метаданных")
st.caption("Удобный выбор ГЕО по группам, поиск по всему миру и автозагрузка картинок через =IMAGE()")

platform = st.selectbox("1. Выберите платформу", ["Google Play", "App Store"])
app_id = st.text_input("2. Введите ID приложения (бандл)", placeholder="com.instagram.android / id389801252")

st.markdown("---")
st.subheader("🌍 3. Выбор стран и регионов")

# Полная база всех стран мира из ISO
ALL_COUNTRIES = {c.alpha_2.lower(): c.name for c in pycountry.countries}

# Твои удобные ГЕО-группы для быстрого клика
GEO_GROUPS = {
    "Tier-1 (Запад)": ["us", "ca", "gb", "de", "fr", "it", "es", "au"],
    "Tier-1 (Азия)": ["jp", "kr", "cn", "tw", "sg"],
    "Евросоюз (EU)": ["at", "be", "bg", "hr", "cy", "cz", "dk", "ee", "fi", "fr", "de", "gr", "hu", "ie", "it", "lv", "lt", "lu", "mt", "nl", "pl", "pt", "ro", "sk", "si", "es", "se"],
    "ЛАТАМ (LATAM)": ["br", "mx", "ar", "co", "cl", "pe"],
    "Ближний Восток / MENA": ["sa", "ae", "eg", "tr", "il", "qa", "kw", "bh", "om", "jo", "lb"],
    "СНГ и Смежные": ["ru", "kz", "by", "uz", "am", "ge", "ua", "kg", "md", "az"]
}

# 1. Сначала выбираем группы
selected_groups = st.multiselect("Быстрый выбор регионов группами:", options=list(GEO_GROUPS.keys()))

# Собираем коды стран из выбранных групп
preselected_codes = set()
for group in selected_groups:
    preselected_codes.update(GEO_GROUPS[group])

# Формируем списки для красивого отображения в поиске
all_countries_options = [f"{name} ({code.upper()})" for code, name in ALL_COUNTRIES.items()]
default_countries_options = [f"{ALL_COUNTRIES[code]} ({code.upper()})" for code in preselected_codes if code in ALL_COUNTRIES]

# 2. Финальный поиск-мультиселект (сюда автоматически залетают страны из групп, и можно дописать любые руками)
final_selected_countries = st.multiselect(
    "Итоговый список стран для выгрузки (можно искать и добавлять штучно):",
    options=all_countries_options,
    default=default_countries_options
)

st.markdown("---")

# Официальная карта мультиязычности для Google Play
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

def get_official_languages(country_code):
    if country_code in MULTI_LANG_EXCEPTIONS:
        return MULTI_LANG_EXCEPTIONS[country_code]
    return [country_code, "en"]

# --- Функции парсинга ---
def parse_google_play(bundle, country, lang):
    url = f"https://play-store-api.asotools.workers.dev/api/apps/{bundle}?lang={lang}&country={country}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            item = res.json()
            if "title" in item:
                return {
                    "Platform": "Google Play", "Country": ALL_COUNTRIES[country], "GL": country.upper(), "HL": lang.upper(),
                    "Title": item.get("title"), "Subtitle / Short": item.get("summary"), "Description": item.get("description"),
                    "Icon": item.get("icon"), "Screenshots": item.get("screenshots", [])
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

# --- Сбор ---
if st.button("🚀 Начать сбор метаданных", type="primary"):
    if not app_id:
        st.error("Введите ID приложения!")
    elif not final_selected_countries:
        st.error("Выберите страны!")
    else:
        # Извлекаем чистые двухбуквенные коды стран из выбранных строк (например, "Qatar (QA)" -> "qa")
        chosen_country_codes = [text.split("(")[1].replace(")", "").lower() for text in final_selected_countries]
        raw_results = []
        
        with st.spinner("Выгружаем данные..."):
            for country in chosen_country_codes:
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
                row = {
                    "Платформа": item["Platform"],
                    "Страна": item["Country"],
                    "ГЕО (gl)": item["GL"],
                    "Язык (hl)": item["HL"],
                    "Тайтл": item["Title"],
                    "Субтитл": item["Subtitle / Short"],
                    "Описание": item["Description"],
                    "Иконка": f'=IMAGE("{item["Icon"]}")' if item["Icon"] else ""
                }
                
                # Раскладываем до 8 скриншотов по отдельным колонкам через формулу
                screenshots = item["Screenshots"][:8]
                for i in range(1, 9):
                    if i <= len(screenshots):
                        row[f"Скриншот {i}"] = f'=IMAGE("{screenshots[i-1]}")'
                    else:
                        row[f"Скриншот {i}"] = ""
                        
                processed_rows.append(row)
                
            df = pd.DataFrame(processed_rows)
            base_cols = ["Платформа", "Страна", "ГЕО (gl)", "Язык (hl)", "Иконка", "Тайтл", "Субтитл", "Описание"]
            scr_cols = [f"Скриншот {i}" for i in range(1, 9)]
            df = df[base_cols + scr_cols]
            
            st.success(f"Успешно собрано! Всего версий в таблице: {len(df)}")
            st.dataframe(df)
            
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="ASO Meta")
            buffer.seek(0)
            
            st.download_button(
                label="📥 Скачать Excel (.xlsx) с иконками и скриншотами",
                data=buffer,
                file_name=f"aso_report_{app_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Данные не найдены.")
