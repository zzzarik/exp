import streamlit as st
import pandas as pd
import pycountry
import requests
import re
import json
from bs4 import BeautifulSoup

st.set_page_config(page_title="ASO Global Pro Ultra Fix", layout="wide")

st.title("📱 Официальный Глобальный ASO Парсер")
st.caption("Исправлено: Настоящий Long Description и только РЕАЛЬНЫЕ скриншоты приложения")

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

# --- ЖЕЛЕЗОБЕТОННЫЙ РАЗБОР GOOGLE PLAY ---
def parse_google_play_direct(bundle, country, lang):
    url = f"https://play.google.com/store/apps/details?id={bundle}&hl={lang}&gl={country}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": f"{lang}-{country.upper()},{lang};q=0.9"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            html = res.text
            soup = BeautifulSoup(html, "html.parser")
            
            # Собираем ВСЕ текстовые блоки из AF_initDataCallback, чтобы вытащить описания без привязки к индексам
            all_strings = []
            for script in soup.find_all("script"):
                if script.string and "AF_initDataCallback" in script.string:
                    # Выдергиваем все текстовые фрагменты в кавычках
                    found_strs = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', script.string)
                    for s in found_strs:
                        s_clean = s.replace('\\n', '\n').replace('\\t', '').strip()
                        if len(s_clean) > 5 and s_clean not in all_strings:
                            all_strings.append(s_clean)
            
            # Вычисляем Шорт и Лонг по длине и вхождению
            short_description = ""
            long_description = ""
            
            # Сортируем собранные тексты по длине
            potential_descriptions = [s for s in all_strings if len(s) > 10 and not s.startswith("http") and not s.startswith("ds:")]
            potential_descriptions.sort(key=len, reverse=True)
            
            # Самый длинный текст на странице стора — это 100% полное описание (Long Description)
            if potential_descriptions:
                long_description = potential_descriptions[0]
                
                # Короткое описание обычно имеет длину до 120 символов и является подстрокой или идет отдельно
                for text in potential_descriptions[1:]:
                    if len(text) <= 120 and text not in long_description:
                        short_description = text
                        break
                # Если отдельный шорт не нашелся, берем первое предложение из лонга
                if not short_description:
                    short_description = long_description.split('.')[0] + "."

            # Находим чистый Тайтл
            title_tag = soup.find("h1")
            title = title_tag.get_text().strip() if title_tag else ""
            if not title:
                meta_title = soup.find("title")
                title = meta_title.get_text().replace(" - Apps on Google Play", "").strip() if meta_title else "Unknown Title"

            # Находим Иконку приложения
            icon = ""
            meta_og_image = soup.find("meta", {"property": "og:image"})
            if meta_og_image and meta_og_image.get("content"):
                icon = meta_og_image["content"]

            # --- ФИЛЬТРАЦИЯ ТОЛЬКО РЕАЛЬНЫХ СКРИНШОТОВ ПРИЛОЖЕНИЯ ---
            screenshots = []
            for script in soup.find_all("script"):
                if script.string and "AF_initDataCallback" in script.string and "ggpht.com" in script.string:
                    # Ищем полноценные ссылки на Google контент
                    urls = re.findall(r'(https://lh3\.googleusercontent\.com/[^\s"\']+|https://[^.\s"\']+\.ggpht\.com/[^\s"\']+)', script.string)
                    for u in urls:
                        u_clean = u.split("=")[0].split('"')[0].split("'")[0] # Чистим параметры обрезки гугла
                        # Скриншоты в новом Google Play содержат в URL спец-маркеры (fife, rw, или специфичные хэши)
                        # И исключаем иконки рейтингов (они обычно содержат фиксированные паттерны или очень мелкие)
                        if "ggpht.com" in u_clean or "googleusercontent.com" in u_clean:
                            if u_clean not in screenshots and u_clean != icon:
                                # Пропускаем заведомо известные мелкие служебные иконки стора
                                if any(x in u_clean.lower() for x in ["/me/", "/pc/", "shared-icon", "google-play-"]):
                                    continue
                                screenshots.append(u_clean)

            # Отбираем только те картинки, которые идут плотным массивом галереи (обычно они имеют схожую структуру URL)
            # Зачастую первые 2-3 ссылки — это аватарки или дубли иконки, реальные скрины идут следом
            final_screenshots = []
            for scr in screenshots:
                # Фильтр: настоящие скриншоты Google Play хранятся с длинными хэшами, отсекаем мусорные мелкие плашки рейтингов PEGI
                if len(scr) > 60: 
                    final_screenshots.append(scr)
            
            # Если наловилось слишком много мусора, берем срез галереи, где лежат реальные скрины
            if len(final_screenshots) > 8:
                # Убираем возможный дубликат иконки из начала массива
                final_screenshots = [img for img in final_screenshots if img != icon][:8]
            else:
                final_screenshots = final_screenshots[:8]

            return {
                "Platform": "Google Play", "Country": ALL_COUNTRIES.get(country.upper(), country), "GL": country.upper(), "HL": lang.upper(),
                "Title": title, "Subtitle / Short": short_description, "Description": long_description, 
                "Icon": icon, "Screenshots": final_screenshots
            }
    except Exception as e:
        st.error(f"Ошибка запроса для {country.upper()}: {e}")
    return None

# --- ПАРСИНГ APP STORE ---
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

# --- Сбор ---
if st.button("🚀 Начать сбор метаданных", type="primary"):
    if not app_id:
        st.error("Введите ID приложения!")
    elif not final_selected_countries:
        st.error("Выберите страны!")
    else:
        chosen_country_codes = [text.split(" - ")[0].strip().upper() for text in final_selected_countries]
        raw_results = []
        
        with st.spinner("Выгружаем чистые метаданные (Лонг, Шорт и Скриншоты)..."):
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
