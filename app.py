import streamlit as st
import pandas as pd
import pycountry
import requests
import re
import json

st.set_page_config(page_title="ASO Global Pro Max", layout="wide")

st.title("📱 Официальный Глобальный ASO Парсер")
st.caption("Гибридный выбор ГЕО: автоматические группы + ручной выбор отдельных стран")

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

# 1. Быстрый выбор группами (Пресет)
selected_groups = st.multiselect("Быстрый выбор региона группами (опционально):", options=list(GEO_GROUPS.keys()))

# Собираем коды из выбранных групп
preselected_codes = set()
for group in selected_groups:
    preselected_codes.update(GEO_GROUPS[group])

# Формируем список строк для отображения в дефолтных значениях ручного выбора
default_countries_options = [f"{code} - {ALL_COUNTRIES[code]}" for code in preselected_codes if code in ALL_COUNTRIES]

# 2. ГИБРИДНЫЙ ВЫБОР
final_selected_countries = st.multiselect(
    "Итоговый список стран для выгрузки (добавляй отдельные страны руками или удаляй крестиком):",
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

# --- УМНЫЙ ГИБКИЙ ПАРСИНГ GOOGLE PLAY ---
def parse_google_play_rpc(bundle, country, lang):
    url = "https://play.google.com/_/PlayStoreUi/data/batchexecute"
    payload = f'f.req=[[["jQ136b","[[\\"{bundle}\\",1,null,1]]",null,"generic"]]]'
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    params = {"hl": lang.lower(), "gl": country.lower()}
    
    try:
        res = requests.post(url, params=params, data=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            text = res.text
            match = re.search(r'\[\["wrb.fr".*?\]\]', text, re.DOTALL)
            if not match: return None
                
            raw_json = json.loads(match.group(0))
            inner_data_str = raw_json[0][2]
            if not inner_data_str: return None
            
            # Извлекаем вообще все текстовые строки из JSON, чтобы найти описания без привязки к индексам массива
            all_strings = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', inner_data_str)
            cleaned_strings = []
            for s in all_strings:
                s_clean = s.replace('\\n', '\n').replace('\\t', '').strip()
                if len(s_clean) > 2 and not s_clean.startswith('http') and s_clean not in cleaned_strings:
                    cleaned_strings.append(s_clean)
            
            # Фильтруем потенциальные тексты описания
            desc_candidates = [s for s in cleaned_strings if len(s) > 15 and not s.isnumeric()]
            desc_candidates.sort(key=len, reverse=True)
            
            if not desc_candidates: return None
            
            # Самая длинная строка — это 100% Long Description
            long_desc = desc_candidates[0]
            title = "Unknown Title"
            short_desc = ""
            
            # Тайтл обычно идет одной из первых строк и имеет длину до 50 символов
            for s in cleaned_strings[:15]:
                if 2 <= len(s) <= 50 and s != bundle:
                    title = s
                    break
                    
            # Ищем Short Description: строка короче 121 символа, не равная тайтлу
            for s in desc_candidates[1:]:
                if len(s) <= 120 and s != title:
                    short_desc = s
                    break
            
            if not short_desc:
                short_desc = long_desc.split('\n')[0][:120]

            # Собираем только реальные изображения
            img_urls = re.findall(r'(https://lh3\.googleusercontent\.com/[^\s"\'\\\]]+|https://[^.\s"\'\\\]]+\.ggpht\.com/[^\s"\'\\\]]+)', inner_data_str)
            
            icon = ""
            screenshots = []
            
            for url in img_urls:
                url_clean = url.split("=")[0].split('"')[0].split("'")[0]
                if url_clean.endswith('\\'): url_clean = url_clean[:-1]
                
                # Исключаем служебный мусор Google (кнопки, аватарки отзывов, иконки категорий и плашки рейтингов вроде PEGI)
                if any(x in url_clean.lower() for x in ["/me/", "/pc/", "shared-icon", "google-play", "menu-icon", "infopage"]):
                    continue
                    
                if not icon:
                    icon = url_clean
                    continue
                    
                if url_clean not in screenshots and url_clean != icon:
                    # Чистые скриншоты имеют длинные уникальные хэши в URL (обычно > 70 символов)
                    if len(url_clean) > 70:
                        screenshots.append(url_clean)
                        
            return {
                "Platform": "Google Play", "Country": ALL_COUNTRIES.get(country.upper(), country), "GL": country.upper(), "HL": lang.upper(),
                "Title": title, "Subtitle / Short": short_desc, "Description": long_desc, 
                "Icon": icon, "Screenshots": screenshots[:8]
            }
    except: pass
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
    except: pass
    return None

# --- Сбор данных ---
if st.button("🚀 Начать сбор метаданных", type="primary"):
    if not app_id:
        st.error("Введите ID приложения!")
    elif not final_selected_countries:
        st.error("Выберите хотя бы одну страну для выгрузки!")
    else:
        chosen_country_codes = [text.split(" - ")[0].strip().upper() for text in final_selected_countries]
        raw_results = []
        
        with st.spinner("Загрузка официальных метаданных..."):
            for country in sorted(chosen_country_codes):
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
            
            st.success(f"Успешно собрано локалей: {len(df)}")
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
