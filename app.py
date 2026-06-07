import streamlit as st
import pandas as pd
import pycountry
import requests
import re

st.set_page_config(page_title="ASO Global Pro Fixed", layout="wide")

st.title("📱 Глобальный ASO Парсер метаданных")
st.caption("Исправленная версия: выбор по группам, поиск и автоподгрузка картинок через =IMAGE()")

platform = st.selectbox("1. Выберите платформу", ["Google Play", "App Store"])
app_id = st.text_input("2. Введите ID приложения (бандл)", placeholder="com.instagram.android / id389801252")

st.markdown("---")
st.subheader("🌍 3. Выбор стран и регионов")

# Полная база всех стран мира из ISO (переводим ключи в верхний регистр для стабильности поиска)
ALL_COUNTRIES = {c.alpha_2.upper(): c.name for c in pycountry.countries}

# Твои ГЕО-группы (коды строго в верхнем регистре)
GEO_GROUPS = {
    "Tier-1 (Запад)": ["US", "CA", "GB", "DE", "FR", "IT", "ES", "AU"],
    "Tier-1 (Азия)": ["JP", "KR", "CN", "TW", "SG"],
    "Евросоюз (EU)": ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"],
    "ЛАТАМ (LATAM)": ["BR", "MX", "AR", "CO", "CL", "PE"],
    "Ближний Восток / MENA": ["SA", "AE", "EG", "TR", "IL", "QA", "KW", "BH", "OM", "JO", "LB"],
    "СНГ и Смежные": ["RU", "KZ", "BY", "UZ", "AM", "GE", "UA", "KG", "MD", "AZ"]
}

# 1. Выбираем группы
selected_groups = st.multiselect("Быстрый выбор регионов группами:", options=list(GEO_GROUPS.keys()))

# Собираем коды стран из выбранных групп
preselected_codes = set()
for group in selected_groups:
    preselected_codes.update(GEO_GROUPS[group])

# Формируем списки для отображения в поиске
all_countries_options = [f"{code} - {name}" for code, name in ALL_COUNTRIES.items()]
default_countries_options = [f"{code} - {ALL_COUNTRIES[code]}" for code in preselected_codes if code in ALL_COUNTRIES]

# 2. Итоговый поиск-мультиселект
final_selected_countries = st.multiselect(
    "Итоговый список стран для выгрузки (можно искать и добавлять вручную):",
    options=all_countries_options,
    default=default_countries_options
)

st.markdown("---")

# Официальная карта мультиязычности для Google Play (ключи в верхнем регистре)
MULTI_LANG_EXCEPTIONS = {
    "SA": ["ar", "en"], "QA": ["ar", "en"], "AE": ["ar", "en"], "KW": ["ar", "en"], 
    "BH": ["ar", "en"], "OM": ["ar", "en"], "EG": ["ar", "en"], "JO": ["ar", "en"], "LB": ["ar", "en"],
    "DZ": ["ar", "fr", "en"], "MA": ["ar", "fr", "en"], "TN": ["ar", "fr", "en"],
    "US": ["en", "es"], "CA": ["en", "fr"], "CH": ["de", "fr", "it"], "BE": ["nl", "fr", "de"],
    "CY": ["el", "tr", "en"], "HK": ["zh-HK", "en"], "TW": ["zh-TW", "en"], "SG": ["en", "zh-CN", "ms"],
    "MY": ["ms", "en", "zh-CN"], "PH": ["tl", "en"], "FI": ["fi", "sv"], "ZA": ["en", "af"],
    "KZ": ["kk", "ru"], "UA": ["uk", "ru"], "BY": ["be", "ru"], "UZ": ["uz", "ru"], 
    "KG": ["ky", "ru"], "MD": ["ro", "ru"], "AM": ["hy", "ru"], "GE": ["ka", "ru"], "AZ": ["az", "ru"],
}

def get_official_languages(country_code):
    up_code = country_code.upper()
    if up_code in MULTI_LANG_EXCEPTIONS:
        return MULTI_LANG_EXCEPTIONS[up_code]
    return [country_code.lower(), "en"]

# --- Функции парсинга ---
def parse_google_play(bundle, country, lang):
    # API требует нижний регистр для параметров URL
    c_low = country.lower()
    l_low = lang.lower()
    url = f"https://play-store-api.asotools.workers.dev/api/apps/{bundle}?lang={l_low}&country={c_low}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            item = res.json()
            if "title" in item:
                return {
                    "Platform": "Google Play", "Country": ALL_COUNTRIES.get(country.upper(), country), "GL": country.upper(), "HL": lang.upper(),
                    "Title": item.get("title"), "Subtitle / Short": item.get("summary"), "Description": item.get("description"),
                    "Icon": item.get("icon"), "Screenshots": item.get("screenshots", [])
                }
        else:
            st.warning(f"Google Play API вернул статус {res.status_code} для {country}-{lang}")
    except Exception as e: 
        st.error(f"Системная ошибка запроса GP для {country}: {e}")
    return None

def parse_app_store(app_id, country):
    if "id" in app_id:
        match = re.search(r'id(\d+)', app_id)
        if match: app_id = match.group(1)
            
    url = f"https://itunes.apple.com/lookup?id={app_id}&country={country.lower()}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            json_data = res.json()
            if json_data.get("resultCount", 0) > 0:
                item = json_data["results"][0]
                return {
                    "Platform": "App Store", "Country": ALL_COUNTRIES.get(country.upper(), country), "GL": country.upper(), "HL": "DEFAULT",
                    "Title": item.get("trackName"), "Subtitle / Short": item.get("subtitle", ""), "Description": item.get("description"),
                    "Icon": item.get("artworkUrl100"), "Screenshots": item.get("screenshotUrls", [])
                }
        else:
            st.warning(f"App Store API вернул статус {res.status_code} для {country}")
    except Exception as e: 
        st.error(f"Системная ошибка запроса Apple для {country}: {e}")
    return None

# --- Сбор ---
if st.button("🚀 Начать сбор метаданных", type="primary"):
    if not app_id:
        st.error("Введите ID приложения!")
    elif not final_selected_countries:
        st.error("Выберите страны!")
    else:
        # Теперь парсим код страны железно по первым двум буквам строки (например, "QA - Qatar" -> "QA")
        chosen_country_codes = [text.split(" - ")[0].strip().upper() for text in final_selected_countries]
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
            st.error("Данные не найдены. Проверьте правильность ID приложения / Бандла.")
