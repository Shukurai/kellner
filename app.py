import os
import sqlite3
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

DB_PATH = "orders.db"
IMAGES_DIR = "menu_images"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT DEFAULT 'Прочее',
            image_path TEXT
        );
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL REFERENCES tables(name),
            status TEXT DEFAULT 'открыт',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id),
            item_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL
        );
        """
    )
    conn.commit()

    if conn.execute("SELECT COUNT(*) FROM menu").fetchone()[0] == 0:
        seed = [
            # Frühstück
            ("Schnelles Frühstück", 5.90, "Frühstück"),
            ("Kleines Wiener Frühstück", 7.80, "Frühstück"),
            ("Grosses Wiener Frühstück", 9.10, "Frühstück"),
            ("Süßes Frühstück", 9.80, "Frühstück"),
            ("Spezial Frühstück", 11.90, "Frühstück"),
            ("Kaiser Frühstück", 12.90, "Frühstück"),
            ("Mediterranes Frühstück", 14.90, "Frühstück"),
            ("Semmel", 1.00, "Frühstück"),
            ("Kornspitz", 1.40, "Frühstück"),
            ("Butter, Marmelade, Honig", 1.00, "Frühstück"),
            # Fisch
            ("Lachs mit Reis", 19.90, "Fisch"),
            ("Zanderfilet mit Reis", 14.90, "Fisch"),
            ("Pangasius mit Reis", 10.90, "Fisch"),
            # Pasta
            ("Lasagne", 9.90, "Pasta"),
            ("Pasta Bolognese", 9.90, "Pasta"),
            ("Pasta Carbonara", 9.90, "Pasta"),
            ("Pasta Pomodoro", 8.20, "Pasta"),
            ("Parmesan (Zugabe)", 1.20, "Pasta"),
            # Kleine Speisen
            ("Ham&Eggs", 4.90, "Kleine Speisen"),
            ("Spiegelei / Eierspeise", 4.50, "Kleine Speisen"),
            ("Ei im Glas", 4.30, "Kleine Speisen"),
            ("Debreziner / Frankfurter", 5.20, "Kleine Speisen"),
            ("Schinken-Käsesemmel", 2.90, "Kleine Speisen"),
            ("Buttersemmel", 1.90, "Kleine Speisen"),
            ('Spezialtoast "Am Park"', 7.40, "Kleine Speisen"),
            ("Bauerntoast", 7.90, "Kleine Speisen"),
            ("Schinken-Käsetoast / Käsetoast", 3.90, "Kleine Speisen"),
            # Nachspeisen
            ("Wareniki mit Weichsel (süß)", 10.90, "Nachspeisen"),
            ("Sirniki", 6.50, "Nachspeisen"),
            ("Kaiserschmarren", 5.90, "Nachspeisen"),
            ("Nutellapalatschinken", 4.90, "Nachspeisen"),
            ("Schoko-Nusspalatschinken", 4.60, "Nachspeisen"),
            ("Marmeladepalatschinken", 4.30, "Nachspeisen"),
            ("Apfelstrudel mit Eis/Schlagobers", 5.40, "Nachspeisen"),
            ("Apfelstrudel", 3.60, "Nachspeisen"),
            ("Tort Napoleon", 4.90, "Nachspeisen"),
            ("Div. Torten (Vitrine)", 4.30, "Nachspeisen"),
            ("Linzeraugen", 2.90, "Nachspeisen"),
            ("Ischler", 2.90, "Nachspeisen"),
            ("Eismarillenknödel", 5.90, "Nachspeisen"),
            ("Schlagobers / Sauerrahm (Portion)", 0.80, "Nachspeisen"),
            # Salate
            ("Thunfisch Salat", 8.50, "Salate"),
            ("Salat Schlüssel", 8.50, "Salate"),
            ("Griechischer Salat", 8.50, "Salate"),
            ("Gemischter Salat", 5.90, "Salate"),
            ("Grüner Salat", 4.90, "Salate"),
            ("Olewie Salat", 7.50, "Salate"),
            # Suppen
            ("Soljanka Suppe", 8.50, "Suppen"),
            ("Fisch Suppe", 7.10, "Suppen"),
            ("Borsch mit Fleisch", 6.90, "Suppen"),
            ("Borsch vegetarisch", 5.90, "Suppen"),
            ("Hühner Suppe", 5.90, "Suppen"),
            ("Gulaschsuppe", 5.90, "Suppen"),
            ("Bohnensuppe", 5.90, "Suppen"),
            ("Leberknödelsuppe", 4.90, "Suppen"),
            # Hauptspeise Fleisch
            ("Rinder-Gulasch mit Buchweizen", 13.90, "Hauptspeise Fleisch"),
            ("Kotleti", 11.50, "Hauptspeise Fleisch"),
            ("Jarkoe", 10.90, "Hauptspeise Fleisch"),
            ("Wiener Schnitzel (Huhn)", 10.90, "Hauptspeise Fleisch"),
            ("Plow", 10.90, "Hauptspeise Fleisch"),
            ("Golubzi", 10.20, "Hauptspeise Fleisch"),
            ("Cevapcici", 10.20, "Hauptspeise Fleisch"),
            ("Chicken Wings", 10.20, "Hauptspeise Fleisch"),
            ("Chicken Nuggets", 10.20, "Hauptspeise Fleisch"),
            ("Pelmeni (12 Stk)", 10.90, "Hauptspeise Fleisch"),
            ("Wareniki mit Kartoffeln (12 Stk)", 10.90, "Hauptspeise Fleisch"),
            ("Wareniki mit Schafskäse (10 Stk)", 10.90, "Hauptspeise Fleisch"),
            ("Fleischpalatschinken", 9.50, "Hauptspeise Fleisch"),
            ("Palatschinken mit Spinat und Käse", 9.50, "Hauptspeise Fleisch"),
            # Beilagen
            ("Pommes", 4.50, "Beilagen"),
            ("Reis", 4.50, "Beilagen"),
            ("Penne", 4.50, "Beilagen"),
            ("Spagetti", 4.50, "Beilagen"),
            ("Buchweizen", 4.50, "Beilagen"),
            # Heiße Getränke
            ("Kleiner Mokka/Brauner", 2.60, "Heiße Getränke"),
            ("Espresso Macchiato", 2.90, "Heiße Getränke"),
            ("Grosser Mokka/Brauner", 3.80, "Heiße Getränke"),
            ("Wiener Melange", 3.40, "Heiße Getränke"),
            ("Wiener Melange mit Schlagobers", 3.90, "Heiße Getränke"),
            ("Verlängerter Schwarz/Brauner", 3.40, "Heiße Getränke"),
            ("Kanne Kaffee mit Milch", 4.10, "Heiße Getränke"),
            ("Cappuccino", 3.60, "Heiße Getränke"),
            ("Cappuccino mit Schlagobers", 4.30, "Heiße Getränke"),
            ("Café Latte / Haferlkaffee", 4.00, "Heiße Getränke"),
            ("Irisch Kaffee", 5.90, "Heiße Getränke"),
            ('Spezial Kaffee "Am Park"', 5.90, "Heiße Getränke"),
            ("Heiße Schokolade", 3.40, "Heiße Getränke"),
            ("Heiße Schokolade mit Schlagobers", 3.90, "Heiße Getränke"),
            ('Heiße Schokolade "Am Park"', 5.90, "Heiße Getränke"),
            ("Div. Tee (Kanne)", 3.00, "Heiße Getränke"),
            ("Div. Tee mit Zitrone (Kanne)", 3.50, "Heiße Getränke"),
            ("Zitrone (Zugabe)", 0.50, "Heiße Getränke"),
            # Kalte Getränke
            ("Eiskaffee", 5.50, "Kalte Getränke"),
            ("Eisschokolade", 5.50, "Kalte Getränke"),
            ("Espresso-Tonik", 5.50, "Kalte Getränke"),
            # Alkoholfreie Getränke
            ("Apfelsaft gespritzt 0,3l", 2.30, "Alkoholfreie Getränke"),
            ("Apfelsaft gespritzt 0,5l", 3.50, "Alkoholfreie Getränke"),
            ("Orangensaft gespritzt 0,3l", 2.30, "Alkoholfreie Getränke"),
            ("Orangensaft gespritzt 0,5l", 3.50, "Alkoholfreie Getränke"),
            ("Apfelsaft 0,3l", 2.70, "Alkoholfreie Getränke"),
            ("Apfelsaft 0,5l", 4.10, "Alkoholfreie Getränke"),
            ("Orangensaft 0,3l", 2.70, "Alkoholfreie Getränke"),
            ("Orangensaft 0,5l", 4.10, "Alkoholfreie Getränke"),
            ("Pago gespritzt 0,5l", 4.50, "Alkoholfreie Getränke"),
            ("Pago div. 0,2l", 3.50, "Alkoholfreie Getränke"),
            ("Sodazitron / Himbeersoda 0,3l", 2.30, "Alkoholfreie Getränke"),
            ("Sodazitron / Himbeersoda 0,5l", 3.50, "Alkoholfreie Getränke"),
            ("Sodawasser 0,33l", 1.80, "Alkoholfreie Getränke"),
            ("Sodawasser 0,5l", 2.80, "Alkoholfreie Getränke"),
            ("Römerquelle 0,33l", 2.80, "Alkoholfreie Getränke"),
            ("Eistee Pfirsich/Zitrone 0,3l", 3.80, "Alkoholfreie Getränke"),
            ("Coca Cola/Light/Zero 0,33l", 3.80, "Alkoholfreie Getränke"),
            ("Fanta/Almdudler/Sprite 0,33l", 3.80, "Alkoholfreie Getränke"),
            ("Tonic/Bitter Lemon 0,2l", 3.30, "Alkoholfreie Getränke"),
            ("Red Bull 0,25l", 3.80, "Alkoholfreie Getränke"),
            # Alkohol
            ("Sekt Glas", 3.90, "Alkohol"),
            ("Sekt Flasche", 24.90, "Alkohol"),
            ("Piccolo 0,2l", 7.80, "Alkohol"),
            ("Campari Soda/Orange", 5.90, "Alkohol"),
            ("Prosecco Glas", 3.90, "Alkohol"),
            ("Aperol gespritzt", 5.30, "Alkohol"),
            ("Aperol mit Prosecco", 6.50, "Alkohol"),
            ("Wein rot 1/8l", 2.40, "Alkohol"),
            ("Wein rot 1/4l", 3.50, "Alkohol"),
            ("Wein weiß 1/8l", 2.40, "Alkohol"),
            ("Wein weiß 1/4l", 3.50, "Alkohol"),
            ("Gespritzter Wein 1/4l", 3.20, "Alkohol"),
            ("Sommer gespritzt", 4.70, "Alkohol"),
            ("Cognac/Whiskey 2cl", 2.90, "Alkohol"),
            ("Inländer Rum/Schnaps/Gin/Baileys 2cl", 2.60, "Alkohol"),
            ("Martini", 4.00, "Alkohol"),
            ("Jägermeister/Vodka 2cl", 2.90, "Alkohol"),
            ("Zwettler Original 0,3l", 3.90, "Alkohol"),
            ("Zwettler Original 0,5l", 4.90, "Alkohol"),
            ("Gösser/Wieselburger 0,5l", 3.60, "Alkohol"),
            ("Heineken/Radler 0,5l", 4.10, "Alkohol"),
            ("Corona Extra 0,3l", 4.30, "Alkohol"),
            ("Edelweiss Weizenbier 0,5l", 4.10, "Alkohol"),
            ("Alkoholfreies Bier 0,5l", 3.70, "Alkohol"),
        ]
        conn.executemany(
            "INSERT INTO menu (name, price, category) VALUES (?, ?, ?)", seed
        )
        conn.commit()
    conn.close()


init_db()
os.makedirs(IMAGES_DIR, exist_ok=True)
st.set_page_config(page_title="Официант", layout="wide")

tab_new, tab_open, tab_stats, tab_menu = st.tabs(
    ["🆕 Новый заказ", "📋 Открытые заказы", "📊 Аналитика", "🍽 Меню"]
)

# ---------- Новый заказ ----------
with tab_new:
    conn = get_conn()
    menu_df = pd.read_sql("SELECT * FROM menu ORDER BY category, name", conn)
    tables_df = pd.read_sql("SELECT name FROM tables ORDER BY name", conn)

    with st.expander("➕ Добавить новый столик", expanded=tables_df.empty):
        new_table_name = st.text_input("Название столика", key="new_table_input")
        if st.button("Добавить столик"):
            if new_table_name.strip():
                conn.execute(
                    "INSERT OR IGNORE INTO tables (name) VALUES (?)",
                    (new_table_name.strip(),),
                )
                conn.commit()
                st.rerun()
            else:
                st.warning("Введи название столика")

    if tables_df.empty:
        st.info("Сначала добавь хотя бы один столик выше")
    else:
        table_name = st.selectbox("Столик", tables_df["name"])

        if "cart" not in st.session_state:
            st.session_state.cart = []

        st.subheader("Добавить блюдо")
        cols = st.columns([3, 2, 1, 1])
        with cols[0]:
            item = st.selectbox("Блюдо (можно начать печатать)", menu_df["name"].sort_values())
        item_row = menu_df[menu_df["name"] == item].iloc[0]
        with cols[1]:
            price = float(item_row["price"])
            st.metric("Цена", f"{price:.2f} €")
        with cols[2]:
            qty = st.number_input("Кол-во", min_value=1, step=1, value=1)
        with cols[3]:
            st.write("")
            st.write("")
            if st.button("➕ Добавить"):
                st.session_state.cart.append(
                    {"item_name": item, "price": price, "quantity": qty}
                )

        if item_row["image_path"] and os.path.exists(item_row["image_path"]):
            st.image(item_row["image_path"], width=200, caption=item)

        if st.session_state.cart:
            st.subheader("Текущий заказ")
            cart_df = pd.DataFrame(st.session_state.cart)
            cart_df["Сумма"] = cart_df["price"] * cart_df["quantity"]
            st.dataframe(cart_df, width="stretch", hide_index=True)
            st.write(f"**Итого: {cart_df['Сумма'].sum():.2f} €**")

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Оформить заказ", type="primary"):
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO orders (table_name) VALUES (?)", (table_name,)
                    )
                    order_id = cur.lastrowid
                    for row in st.session_state.cart:
                        cur.execute(
                            "INSERT INTO order_items (order_id, item_name, price, quantity) "
                            "VALUES (?, ?, ?, ?)",
                            (order_id, row["item_name"], row["price"], row["quantity"]),
                        )
                    conn.commit()
                    st.session_state.cart = []
                    st.success(f"Заказ №{order_id} для столика «{table_name}» создан")
                    st.rerun()
            with col_b:
                if st.button("🗑 Очистить"):
                    st.session_state.cart = []
                    st.rerun()
    conn.close()

# ---------- Открытые заказы ----------
with tab_open:
    conn = get_conn()
    open_orders = pd.read_sql(
        "SELECT id, table_name, created_at FROM orders "
        "WHERE status = 'открыт' ORDER BY created_at",
        conn,
    )
    if open_orders.empty:
        st.info("Нет открытых заказов")
    for _, order in open_orders.iterrows():
        with st.expander(
            f"Столик «{order['table_name']}» — заказ №{order['id']} ({order['created_at']})"
        ):
            items = pd.read_sql(
                "SELECT item_name, price, quantity FROM order_items WHERE order_id = ?",
                conn,
                params=(int(order["id"]),),
            )
            items["Сумма"] = items["price"] * items["quantity"]
            st.dataframe(items, width="stretch", hide_index=True)
            st.write(f"**Итого: {items['Сумма'].sum():.2f} €**")
            if st.button("💰 Закрыть и оплатить", key=f"close_{order['id']}"):
                conn.execute(
                    "UPDATE orders SET status = 'оплачен', closed_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), int(order["id"])),
                )
                conn.commit()
                st.rerun()
    conn.close()

# ---------- Аналитика ----------
with tab_stats:
    conn = get_conn()
    df = pd.read_sql(
        """
        SELECT o.id, o.table_name, o.status, o.created_at,
               oi.item_name, oi.price, oi.quantity
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status = 'оплачен'
        """,
        conn,
    )
    conn.close()

    if df.empty:
        st.info("Пока нет оплаченных заказов для аналитики")
    else:
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["Сумма"] = df["price"] * df["quantity"]
        df["Дата"] = df["created_at"].dt.date

        c1, c2, c3 = st.columns(3)
        c1.metric("Выручка всего", f"{df['Сумма'].sum():.2f} €")
        c2.metric("Заказов", df["id"].nunique())
        c3.metric(
            "Средний чек", f"{df.groupby('id')['Сумма'].sum().mean():.2f} €"
        )

        st.subheader("Выручка по дням")
        daily = df.groupby("Дата")["Сумма"].sum()
        st.bar_chart(daily)

        st.subheader("Топ блюд по количеству")
        top_items = df.groupby("item_name")["quantity"].sum().sort_values(
            ascending=False
        )
        st.bar_chart(top_items)

# ---------- Меню ----------
with tab_menu:
    conn = get_conn()
    menu_df = pd.read_sql("SELECT * FROM menu ORDER BY category, name", conn)

    for cat in menu_df["category"].unique():
        with st.expander(cat):
            for _, row in menu_df[menu_df["category"] == cat].iterrows():
                c1, c2 = st.columns([1, 4])
                with c1:
                    if row["image_path"] and os.path.exists(row["image_path"]):
                        st.image(row["image_path"], width=80)
                with c2:
                    st.write(f"**{row['name']}** — {row['price']:.2f} €")

    st.divider()
    with st.form("add_menu_item"):
        st.subheader("Добавить блюдо в меню")
        name = st.text_input("Название")
        price = st.number_input("Цена, €", min_value=0.0, step=0.5)
        category = st.text_input("Категория", value="Прочее")
        uploaded = st.file_uploader(
            "Фото блюда (необязательно)", type=["png", "jpg", "jpeg"]
        )
        if st.form_submit_button("Добавить") and name:
            image_path = None
            if uploaded is not None:
                ext = uploaded.name.rsplit(".", 1)[-1]
                image_path = os.path.join(IMAGES_DIR, f"{uuid.uuid4().hex}.{ext}")
                with open(image_path, "wb") as f:
                    f.write(uploaded.getbuffer())
            conn.execute(
                "INSERT INTO menu (name, price, category, image_path) VALUES (?, ?, ?, ?)",
                (name, price, category, image_path),
            )
            conn.commit()
            st.rerun()
    conn.close()
