import streamlit as st
import pandas as pd
import pycountry
import requests
import re
import json

st.set_page_config(page_title="ASO Global Pro Clean", layout="wide")

st.title("📱 Официальный Глобальный ASO Парсер")
st.caption("Прямые запросы к Google и Apple без сторонних API и воркеров")

platform = st.selectbox("1. Выберите платформу", ["Google Play", "App Store"])
app_id = st.text_input("2. Введите ID приложения (бандл)", placeholder="com.instagram.android / id389801252")

st.markdown("---")
st.subheader("🌍 3. Выбор стран и регионов")

ALL_COUNTRIES = {c.alpha_2.upper(): c.name for c in pycountry.countries}

GEO_GROUPS = {
    "Tier-1 (Запад)": ["US", "CA", "GB", "DE", "FR", "IT", "ES", "AU"],
    "Tier-1 (Азия)": ["JP", "KR", "CN", "TW", "SG"],
    "Евросоюз (EU)": ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"],
    "ЛАТАМ (LATAM)": ["BR", "MX", "AR", "CO", "CL", "PE"],
    "Ближний Восток / MENA": ["SA", "AE", "EG", "TR", "IL", "QA", "KW", "BH", "OM", "JO", "LB"],
    "СНГ и Смежные": ["RU", "KZ", "BY", "UZ", "AM", "GE", "UA", "KG", "MD", "AZ"]
}

selected_groups = st.multiselect("Быстрый выбор регионов группами:", options=list(GEO_GROUPS.keys()))

preselected_codes = set()
for group in selected_groups:
    preselected_codes.update(GEO_GROUPS[group])

all_countries_options = [f"{code} - {name}" for code, name in ALL_COUNTRIES.items()]
default_countries_options = [f"{code} - {ALL_COUNTRIES[code]}" for code in preselected_codes if code in ALL_COUNTRIES]

final_selected_countries = st.multiselect(
    "Итоговый список стран для выгрузки:",
    options=all_countries_options,
    default=default_countries_options
)

st.markdown("---")

# Карта мультиязычности
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

# --- ПРЯМОЙ ПАРСИНГ GOOGLE PLAY БЕЗ ПОСРЕДНИКОВ ---
def parse_google_play_direct(bundle, country, lang):
    # Официальный URL Google Play с параметрами локали и региона
    url = f"https://play.google.com/store/apps/details?id={bundle}&hl={lang}&gl={country}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": f"{lang}-{country.upper()},{lang};q=0.9"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            html = res.text
            
            # Извлекаем Тайтл
            title_match = re.search(r'<h1[^>]*itemprop="name"[^>]*><span[^>]*>([^<]+)</span>', html)
            if not title_match:
                title_match = re.search(r'<title[^>]*>([^<]+) - Apps on Google Play</title>', html)
            title = title_match.group(1).strip() if title_match else "Unknown Title"
            
            # Извлекаем Иконку
            icon_match = re.search(r'<img[^>]*itemprop="image"[^>]*src="([^"]+)"', html)
            if not icon_match:
                icon_match = re.search(r'srcset="([^ ]+)[^"]*"[^>]*itemprop="image"', html)
            icon = icon_match.group(1) if icon_match else ""
            if icon and icon.startswith("//"): icon = "https:" + icon

            # Извлекаем Скриншоты
            screenshot_urls = re.findall(r'<img[^>]*srcset="([^ ]+)' , html)
            # Фильтруем только уникальные ссылки на скриншоты (гугловские s3/ggpht)
            screenshots = list(set([src for src in screenshot_urls if "ggpht.com" in src or "googleusercontent.com" in src]))[:8]
            
            # Короткое и полное описание (базовый сбор)
            desc_match = re.search(r'<div[^>]*itemprop="description"[^>]*>.*?<div[^>]*>(.*?)</div>', html, re.DOTALL)
            description = desc_match.group(1).replace("<br>", "\n").strip() if desc_match else "Открыть стор для просмотра описания"
            
            return {
                "Platform": "Google Play", "Country": ALL_COUNTRIES.get(country.upper(), country), "GL": country.upper(), "HL": lang.upper(),
                "Title": title, "Subtitle / Short": "Прямой сбор текста", "Description": description[:500] + "...", 
                "Icon": icon, "Screenshots": screenshots
            }
        else:
            st.warning(f"Google Play вернул статус {res.status_code} для {country.upper()}-{lang.upper()}")
    except Exception as e:
        st.error(f"Ошибка запроса к Google для {country.upper()}: {e}")
    return None

# --- ПРЯМОЙ ПАРСИНГ APP STORE БЕЗ ПОСРЕДНИКОВ ---
def parse_app_store_direct(app_id, country):
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
                    "Title": item.get("trackName"), "Subtitle / Short": item.get("subtitle", ""), "Description": item.get("description", "")[:500] + "...",
                    "Icon": item.get("artworkUrl100"), "Screenshots": item.get("screenshotUrls", [])[:8]
                }
        else:
            st.warning(f"App Store вернул статус {res.status_code} для {country.upper()}")
    except Exception as e: 
        st.error(f"Ошибка запроса к Apple для {country.upper()}: {e}")
    return None

# --- Сбор ---
if st.button("🚀 Начать сбор метаданных", type="primary"):
    if not app_id:
        st.error("Введите ID приложения!")
    elif not final_selected_countries:
        st.error("Выберите страны!")
    else:
        chosen_country_codes = [text.split(" - ")[0].strip().upper() for text in final_selected_countries]
        raw_results = []
        
        with st.spinner("Связываемся напрямую со сторами..."):
            for country in chosen_country_codes:
                if platform == "Google Play":
                    langs = get_official_languages(country)
                    for lang in langs:
                        data = parse_google_play_direct(app_id, country, lang)
                        if data: raw_results.append(data)
                else:
                    data = parse_app_store_direct(app_id, country)
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
                
                screenshots = item["Screenshots"]
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
            
            st.success(f"Готово! Собрано официальных версий: {len(df)}")
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
            st.error("Данные не найдены. Проверьте правильность ID приложения.")
