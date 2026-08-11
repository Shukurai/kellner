# Официант — заказы и аналитика

## Локальный запуск
```
pip install -r requirements.txt
streamlit run app.py
```
Открой `http://localhost:8501` — с телефона в той же Wi-Fi сети зайти можно по Network URL из терминала.

## Деплой на Streamlit Community Cloud
1. Создай репозиторий на GitHub, залей туда `app.py`, `requirements.txt`, `.gitignore`.
2. Зайди на share.streamlit.io → New app → выбери репозиторий и файл `app.py`.
3. Через минуту получишь публичный URL, открывается с телефона из любой сети.

⚠️ Важно: на Streamlit Cloud файловая система эфемерная — при перезапуске контейнера
(например, после долгого простоя) `orders.db` и загруженные фото блюд (`menu_images/`)
могут обнулиться. Для личного использования это некритично, но если нужна надёжность —
перенеси БД и хранение фото на Supabase (Postgres + Storage).
