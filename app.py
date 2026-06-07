import streamlit as st
import pandas as pd
import pycountry
import requests
import re
import json

st.set_page_config(page_title="ASO Global Pro Max", layout="wide")

st.title("📱 Официальный Глобальный ASO Парсер")
st.caption("Стабильная версия: Прямые RPC-запросы к Google Play и iTunes Lookup")

platform = st.selectbox("1. Выберите платформу", ["Google Play", "App Store"])
app_id = st.text_input("2. Введите ID приложения (бандл)", placeholder="com.instagram.android / id389801252")

st.markdown("---")
st.subheader("🌍 3. Выбор стран и регионов")

# Полная база ВСЕХ стран мира из ISO
ALL_COUNTRIES = {c.alpha_2.upper(): c.name for c in pycountry.countries}
all_countries_options = sorted([f"{code} - {name}" for code, name in ALL_COUNTRIES.items()])

GEO_GROUPS = {
    "Tier-1 (Запад)": ["US", "CA", "GB", "DE", "FR", "IT", "ES", "AU"],
    "Tier-1 (Азия)": ["JP", "KR", "CN", "TW", "SG"],
    "Евросоюз (EU)": ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"],
    "ЛАТАМ (LATAM)": ["BR", "MX", "AR", "CO", "CL", "PE"],
    "Ближний Восток / MENA": ["SA", "AE", "EG", "TR", "IL", "QA", "KW", "BH", "OM", "JO", "LB"],
    "СНГ и Смежные": ["RU", "KZ", "BY", "UZ", "AM", "GE", "UA", "KG", "MD", "AZ"]
}

selected_groups = st.multiselect("Быстрый выбор региона группами (опционально):", options=list(GEO_GROUPS.keys()))

preselected_codes = set()
for group in selected_groups:
    preselected_codes.update(GEO_GROUPS[group])

default_countries_options = [f"{code} - {ALL_COUNTRIES[code]}" for code in preselected_codes if code in ALL_COUNTRIES]

# Итоговый выбор: здесь можно выбрать ЛЮБУЮ страну из списка всех стран мира вручную
final_selected_countries = st.multiselect(
    "Итоговый список стран для выгрузки (можно искать и добавлять вручную любую страну мира):",
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

# --- СТАБИЛЬНЫЙ ПАРСИНГ GOOGLE PLAY ЧЕРЕЗ BATCHEXECUTE API ---
def parse_google_play_rpc(bundle, country, lang):
    url = "https://play.google.com/_/PlayStoreUi/data/batchexecute"
    
    # Официальный внутренний RPC-запрос для получения деталей приложения (внутренний id: rpcId 'jQ136b')
    payload = f'f.req=[[["jQ136b","[[\\"{bundle}\\",1,null,1]]",null,"generic"]]]'
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    params = {
        "hl": lang.lower(),
        "gl": country.lower()
    }
    
    try:
        res = requests.post(url, params=params, data=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            text = res.text
            match = re.search(r'\[\["wrb.fr".*?\]\]', text, re.DOTALL)
            if not match:
                return None
                
            raw_json = json.loads(match.group(0))
            inner_data_str = raw_json[0][2]
            inner_data = json.loads(inner_data_str)
            
            # Внутри структуры batchexecute данные лежат по строгим индексам
            app_details = inner_data[1][2]
            
            title = app_details[0][0]  # Название
            short_desc = app_details[73][0][1]  # Короткое описание (Short Description)
            long_desc = app_details[72][0][1]  # Длинное описание (Long Description)
            icon = app_details[95][0][3][2]  # Иконка
            
            # Скриншоты достаются только из выделенного под них массива ассетов
            screenshots = []
            try:
                scr_list = app_details[78][0]
                for scr in scr_list:
                    img_url = scr[3][2]
                    if img_url and img_url not in screenshots:
                        screenshots.append(img_url)
            except:
                pass
                
            return {
                "Platform": "Google Play", "Country": ALL_COUNTRIES.get(country.upper(), country), "GL": country.upper(), "HL": lang.upper(),
                "Title": title, "Subtitle / Short": short_desc, "Description": long_desc, 
                "Icon": icon, "Screenshots": screenshots[:8]
            }
    except Exception as e:
        pass
    return None

# --- ОФИЦИАЛЬНЫЙ ПАРСИНГ APP STORE ---
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
                    "Subtitle / Short": item.get("subtitle", "Не задан разработчиком"), 
                    "Description": item.get("description", ""),
                    "Icon": item.get("artworkUrl100"), "Screenshots": item.get("screenshotUrls", [])[:8]
                }
    except Exception as e: 
        st.error(f"Ошибка запроса к Apple для {country.upper()}: {e}")
    return None

# --- Сбор данных ---
if st.button("🚀 Начать сбор метаданных", type="primary"):
    if not app_id:
        st.error("Введите ID приложения!")
    elif not final_selected_countries:
        st.error("Выберите страны!")
    else:
        chosen_country_codes = [text.split(" - ")[0].strip().upper() for text in final_selected_countries]
        raw_results = []
        
        with st.spinner("Загрузка официальных метаданных сторов..."):
            for country in chosen_country_codes:
                if platform == "Google Play":
                    langs = get_official_languages(country)
                    for lang in langs:
                        data = parse_google_play_rpc(app_id, country, lang)
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
                file_name=f"aso_report_{app_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Данные не найдены. Проверьте правильность ID приложения.")
