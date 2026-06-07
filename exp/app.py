import streamlit as st
import pandas as pd
import pycountry
import random
import time
from fake_useragent import UserAgent
from google_play_scraper import app as gp_app

# Инициализируем генератор случайных браузеров для маскировки
try:
    ua = UserAgent()
except Exception:
    ua = None

# --- БАЗА ДАННЫХ СТРАН МИРА ---
# Автоматически загружаем все страны мира по международному стандарту ISO
ALL_COUNTRIES = {c.alpha_2.lower(): c.name for c in pycountry.countries}

# Готовые группы стран для быстрого выбора в один клик
GEO_GROUPS = {
    "Tier-1 (Запад)": ["us", "ca", "gb", "de", "fr", "it", "es", "au"],
    "Tier-1 (Азия)": ["jp", "kr", "cn", "tw", "sg"],
    "Евросоюз (EU)": ["at", "be", "bg", "hr", "cy", "cz", "dk", "ee", "fi", "fr", "de", "gr", "hu", "ie", "it", "lv", "lt", "lu", "mt", "nl", "pl", "pt", "ro", "sk", "si", "es", "se"],
    "ЛАТАМ (LATAM)": ["br", "mx", "ar", "co", "cl", "pe"],
    "Ближний Восток / MENA": ["sa", "ae", "eg", "tr", "il", "qa"],
    "СНГ и Смежные": ["ru", "kz", "by", "uz", "am", "ge", "ua"]
}

# Карта мультиязычных стран (где скрипт сам соберет дополнительные локали)
MULTILINGUAL_COUNTRIES = {
    "ca": ["en", "fr"],       # Канада: Английский + Французский
    "us": ["en", "es-419"],   # США: Английский + Испанский
    "ch": ["de", "fr", "it"], # Швейцария: Немецкий + Французский + Итальянский
    "be": ["nl", "fr"],       # Бельгия: Голландский + Французский
    "kz": ["ru", "kk"],       # Казахстан: Русский + Казахский
    "ae": ["ar", "en"]        # ОАЭ: Арабский + Английский
}

# --- ИНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="Бесплатный ASO Парсер", layout="wide")

st.title("🌍 Глобальный ASO Парсер метаданных")
st.caption("Работает бесплатно с вашего IP. Оптимизирован для безопасной выгрузки до 30-40 стран за один раз.")

# Блок настроек
st.subheader("🛠 1. Настройки запроса")
col_plat, col_link = st.columns([1, 3])

with col_plat:
    platform = st.radio("Платформа", ["Google Play", "App Store (В разработке)"])
with col_link:
    app_id = st.text_input("Вставьте ID приложения или ссылку", placeholder="например: com.instagram.android или com.spotify.music")

st.markdown("---")

# Блок выбора ГЕО
st.subheader("⚙️ 2. Выбор стран и регионов")

selected_groups = st.multiselect(
    "Быстрый выбор по группам стран (опционально):",
    options=list(GEO_GROUPS.keys())
)

# Вычисляем страны, которые входят в выбранные пресеты
preselected_codes = set()
for group in selected_groups:
    preselected_codes.update(GEO_GROUPS[group])

# Формируем списки для красивого отображения "Название (КОД)"
all_countries_options = [f"{name} ({code.upper()})" for code, name in ALL_COUNTRIES.items()]
default_countries_options = [f"{ALL_COUNTRIES[code]} ({code.upper()})" for code in preselected_codes if code in ALL_COUNTRIES]

# Финальный интерактивный список
final_selected_countries = st.multiselect(
    "Итоговый список стран (можно свободно добавлять новые или удалять кликом):",
    options=all_countries_options,
    default=default_countries_options,
    help="Просто введите название любой страны мира, чтобы добавить её."
)

st.markdown("---")

# --- ЛОГИКА СБОРА ДАННЫХ ---
if st.button("🔥 Запустить выгрузку данных", type="primary"):
    if not app_id:
        st.error("Ошибка: Вы не указали ID приложения!")
    elif not final_selected_countries:
        st.error("Ошибка: Выберите хотя бы одну страну для выгрузки!")
    else:
        # Чистим коды стран, превращая обратно "Канада (CA)" -> "ca"
        chosen_country_codes = [text.split("(")[1].replace(")", "").lower() for text in final_selected_countries]
        
        # Строим карту задач с учетом умных локалей
        tasks = []
        for code in chosen_country_codes:
            langs = MULTILINGUAL_COUNTRIES.get(code, [code])
            for lang in langs:
                tasks.append({
                    "country": code,
                    "lang": lang,
                    "country_name": ALL_COUNTRIES[code]
                })
        
        total_tasks = len(tasks)
        
        # Предупреждение о лимитах бесплатного режима
        if total_tasks > 45:
            st.warning(f"⚠️ Вы выбрали слишком много локалей ({total_tasks}). Без прокси Google может прервать загрузку на середине. Рекомендуется разбить выгрузку на 2-3 части (до 40 запросов за раз).")
        
        # Элементы прогресса в интерфейсе
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        parsed_results = []
        
        # Запуск парсинга в цикле
        for idx, task in enumerate(tasks):
            c_code = task["country"]
            l_code = task["lang"]
            c_name = task["country_name"]
            
            status_text.text(f"⏳ Обработка [{idx+1}/{total_tasks}]: {c_name} — Локаль: {l_code.upper()}...")
            
            if platform == "Google Play":
                try:
                    # Защита 1: Меняем отпечаток браузера на каждом шаге
                    current_ua = ua.random if ua else "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    
                    # Запрос к стору
                    data = gp_app(app_id, lang=l_code, country=c_code)
                    
                    # Сохраняем ровно то, что нужно для ASO
                    parsed_results.append({
                        "Платформа": "Google Play",
                        "Страна": c_name,
                        "ГЕО код": c_code.upper(),
                        "Локаль": l_code.upper(),
                        "Тайтл (Title)": data.get("title"),
                        "Короткое описание (Short)": data.get("summary"),
                        "Полное описание (Full Description)": data.get("description"),
                        "Иконка (URL)": data.get("icon"),
                        "Скриншоты (Ссылки через запятую)": ", ".join(data.get("screenshots", []))
                    })
                    
                except Exception as e:
                    if "429" in str(e):
                        st.error("🚨 Превышен лимит запросов (Error 429). Google временно ограничил ваш IP. Подождите 15-20 минут перед следующим запуском.")
                        break
                    else:
                        st.warning(f"Ошибка выгрузки для {c_name} ({l_code.upper()}): {e}")
            
            elif platform == "App Store (В разработке)":
                # Заглушка структуры для App Store
                parsed_results.append({
                    "Платформа": "App Store",
                    "Страна": c_name,
                    "ГЕО код": c_code.upper(),
                    "Локаль": l_code.upper(),
                    "Тайтл (Title)": f"App Store Title {c_code.upper()}",
                    "Короткое описание (Short)": "Subtitle iOS",
                    "Полное описание (Full Description)": "Full iOS Description...",
                    "Иконка (URL)": "https://apple.com/image.png",
                    "Скриншоты (Ссылки через запятую)": "https://apple.com/screen1.png"
                })
            
            # Защита 2: Рандомная пауза (имитируем человека, чтобы не получить бан)
            time.sleep(random.uniform(1.5, 3.5))
            progress_bar.progress((idx + 1) / total_tasks)
            
        status_text.text("✅ Готово!")
        
        # --- ВЫВОД РЕЗУЛЬТАТОВ И СКАЧИВАНИЕ ФАЙЛА ---
        if parsed_results:
            df = pd.DataFrame(parsed_results)
            
            st.subheader("📊 Таблица результатов")
            st.dataframe(df)
            
            # Переводим в CSV формат, который без проблем открывается в Excel
            csv_data = df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Скачать готовый Excel (CSV) файл",
                data=csv_data,
                file_name=f"aso_metadata_{app_id}.csv",
                mime="text/csv"
            )