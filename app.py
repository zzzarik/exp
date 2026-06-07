import streamlit as st
import pandas as pd
import pycountry
import requests
import re
import json
from bs4 import BeautifulSoup

st.set_page_config(page_title="ASO Global Pro Max", layout="wide")

st.title("📱 Официальный Глобальный ASO Парсер")
st.caption("Полный сбор метаданных: включая Short Description для Google Play и Subtitle для App Store")

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

# --- ИСПРАВЛЕННЫЙ ПАРСИНГ GOOGLE PLAY С СБОРОМ SHORT DESCRIPTION ---
def parse_google_play_direct(bundle, country, lang):
    url = f"https://play.google.com/store/apps/details?id={bundle}&hl={lang}&gl={country}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": f"{lang}-{country.upper()},{lang};q=0.9"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            html = res.text
            soup = BeautifulSoup(html, "html.parser")
            
            # Ищем скрипт с внутренним JSON стора
            script_data = ""
            for script in soup.find_all("script"):
                if script.string and "AF_initDataCallback" in script.string and "ds:5" in script.string:
                    script_data = script.string
                    break
            
            if not script_data:
                for script in soup.find_all("script"):
                    if script.string and "AF_initDataCallback" in script.string and "key: 'ds:" in script.string:
                        script_data = script.string
                        break
            
            title, short_description, description, icon, screenshots = "Unknown Title", "", "", "", []
            
            if script_data:
                try:
                    json_match = re.search(r'data:\s*(\[.+?\])\s*,\s*sideChannel:', script_data, re.DOTALL)
                    if json_match:
                        data_array = json.loads(json_match.group(1))
                        
                        try: app_info = data_array[0][1][2]
                        except: app_info = data_array
                        
                        # 1. Точный Тайтл
                        try: title = app_info[0][0]
                        except: pass
                        
                        # 2. Настоящий Short Description (Короткое описание приложения)
                        try: short_description = app_info[73][0][1]
                        except:
                            try: short_description = app_info[63][1][1]  # Альтернативная ветка структуры
                            except: pass
                        
                        # 3. Полное Описание
                        try: description = app_info[72][0][1]
                        except:
                            try: description = app_info[10][0][1]
                            except: pass
                            
                        # 4. Иконка
                        try: icon = app_info[95][0][3][2]
                        except: pass
                            
                        # 5. Скриншоты
                        try:
                            scr_data = app_info[78][0]
                            for img_wrapper in scr_data:
                                url_img = img_wrapper[3][2]
                                if url_img and url_img not in screenshots:
                                    screenshots.append(url_img)
                        except: pass
                except:
                    pass
            
            # --- Резервный сбор, если Google перетасовал JSON-массив ---
            if title == "Unknown Title" or not title:
                title_tag = soup.find("h1") or soup.find("title")
                title = title_tag.get_text().replace(" - Apps on Google Play", "").strip() if title_tag else "Unknown Title"
            
            # Если короткое описание не вытянулось из JSON, ищем его в мета-тегах
            if not short_description:
                meta_og_desc = soup.find("meta", {"property": "og:description"})
                if meta_og_desc and meta_og_desc.get("content"):
                    short_description = meta_og_desc["content"].strip()
            
            if not description:
                desc_meta = soup.find("meta", {"name": "description"})
                description = desc_meta["content"].strip() if desc_meta else "Смотрите описание в сторе"
                
            if not icon:
                try: icon = soup.find("meta", {"property": "og:image"})["content"]
                except: pass
                
            if icon and icon.startswith("//"): icon = "https:" + icon

            if not screenshots:
                for img in soup.find_all("img"):
                    src = img.get("src") or img.get("srcset", "").split(" ")[0]
                    if src and ("ggpht.com" in src or "googleusercontent.com" in src) and "rw" in src:
                        if src.startswith("//"): src = "https:" + src
                        if src not in screenshots: screenshots.append(src)
            
            return {
                "Platform": "Google Play", "Country": ALL_COUNTRIES.get(country.upper(), country), "GL": country.upper(), "HL": lang.upper(),
                "Title": title, "Subtitle / Short": short_description if short_description else "Не задан разработчиком", 
                "Description": description[:1000] + "...", "Icon": icon, "Screenshots": screenshots[:8]
            }
    except Exception as e:
        st.error(f"Ошибка запроса для {country.upper()}: {e}")
    return None

# --- ПРЯМОЙ ПАРСИНГ APP STORE ---
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
                    "Title": item.get("trackName"), 
                    "Subtitle / Short": item.get("subtitle", "Не задан разработчиком"), # Официальный Subtitle в iOS
                    "Description": item.get("description", "")[:1000] + "...",
                    "Icon": item.get("artworkUrl100"), "Screenshots": item.get("screenshotUrls", [])[:8]
                }
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
        
        with st.spinner("Вытаскиваем метаданные, тайтлы и короткие описания..."):
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
                    "Субтитл / Шорт": item["Subtitle / Short"],
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
            base_cols = ["Платформа", "Страна", "ГЕО (gl)", "Язык (hl)", "Иконка", "Тайтл", "Субтитл / Шорт", "Описание"]
            scr_cols = [f"Скриншот {i}" for i in range(1, 9)]
            df = df[base_cols + scr_cols]
            
            st.success(f"Успешно собрано официальных версий: {len(df)}")
            st.dataframe(df)
            
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="ASO Meta")
            buffer.seek(0)
            
            st.download_button(
                label="📥 Скачать чистый Excel (.xlsx)",
                data=buffer,
                file_name=f"aso_final_report_{app_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Данные не найдены.")
