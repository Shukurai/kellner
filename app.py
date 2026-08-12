import difflib
import os
import sqlite3
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

DB_PATH = "orders.db"
IMAGES_DIR = "menu_images"

_UMLAUT_MAP = str.maketrans(
    {"ü": "u", "ä": "a", "ö": "o", "ß": "ss", "é": "e", "è": "e"}
)


def _normalize(text: str) -> str:
    return text.lower().translate(_UMLAUT_MAP)


def search_menu(query: str, menu_df: pd.DataFrame) -> pd.DataFrame:
    """Ищет блюда по подстроке (без учёта умлаутов/регистра), а если ничего
    не нашлось — пробует нечёткий поиск на случай опечатки в одну букву."""
    if not query:
        return menu_df

    q_norm = _normalize(query)
    names_norm = menu_df["name"].map(_normalize)

    exact_mask = names_norm.str.contains(q_norm, regex=False)
    if exact_mask.any():
        return menu_df[exact_mask]

    def best_ratio(name_norm: str) -> float:
        tokens = name_norm.replace("/", " ").replace(",", " ").replace("-", " ").split()
        tokens.append(name_norm)
        return max(difflib.SequenceMatcher(None, q_norm, t).ratio() for t in tokens)

    ratios = names_norm.map(best_ratio)
    fuzzy_mask = ratios >= 0.72
    if fuzzy_mask.any():
        return menu_df[fuzzy_mask].loc[ratios[fuzzy_mask].sort_values(ascending=False).index]

    return menu_df.iloc[0:0]


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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
            image_path TEXT,
            custom_price INTEGER NOT NULL DEFAULT 0
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
            quantity INTEGER NOT NULL,
            note TEXT
        );
        """
    )
    conn.commit()

    # лёгкая миграция: добираем колонки, которых не было в старой БД
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(order_items)")}
    if "note" not in existing_cols:
        conn.execute("ALTER TABLE order_items ADD COLUMN note TEXT")
        conn.commit()

    menu_cols = {row[1] for row in conn.execute("PRAGMA table_info(menu)")}
    if "custom_price" not in menu_cols:
        conn.execute(
            "ALTER TABLE menu ADD COLUMN custom_price INTEGER NOT NULL DEFAULT 0"
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

    if conn.execute("SELECT COUNT(*) FROM menu WHERE name = 'Eis'").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO menu (name, price, category, custom_price) "
            "VALUES ('Eis', 0.0, 'Nachspeisen', 1)"
        )
        conn.commit()

    if conn.execute(
        "SELECT COUNT(*) FROM menu WHERE name = 'Getränk'"
    ).fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO menu (name, price, category, custom_price) "
            "VALUES ('Getränk', 0.0, 'Alkoholfreie Getränke', 1)"
        )
        conn.commit()
    conn.close()


init_db()
os.makedirs(IMAGES_DIR, exist_ok=True)
st.set_page_config(page_title="Официант", layout="wide")

tab_new, tab_open, tab_stats, tab_menu = st.tabs(
    ["🆕 Новый заказ", "📋 Заказы", "📊 Аналитика", "🍽 Меню"]
)

# ---------- Новый заказ ----------
with tab_new:
    conn = get_conn()
    menu_df = pd.read_sql("SELECT * FROM menu ORDER BY category, name", conn)
    tables_df = pd.read_sql("SELECT name FROM tables ORDER BY name", conn)

    with st.expander("➕ Добавить новый столик", expanded=tables_df.empty):
        new_table_name = st.text_input("Название столика", key="new_table_input")
        if st.button("Добавить столик"):
            clean_name = new_table_name.strip()
            if clean_name:
                conn.execute(
                    "INSERT OR IGNORE INTO tables (name) VALUES (?)", (clean_name,)
                )
                conn.commit()
                st.session_state["table_select"] = clean_name
                st.rerun()
            else:
                st.warning("Введи название столика")

    if tables_df.empty:
        st.info("Сначала добавь хотя бы один столик выше")
    else:
        table_name = st.selectbox("Столик", tables_df["name"], key="table_select")

        existing_total = conn.execute(
            "SELECT COALESCE(SUM(oi.price * oi.quantity), 0) "
            "FROM orders o JOIN order_items oi ON oi.order_id = o.id "
            "WHERE o.table_name = ? AND o.status = 'открыт'",
            (table_name,),
        ).fetchone()[0]
        if existing_total > 0:
            st.info(f"На «{table_name}» уже открыто на {existing_total:.2f} €")

        if "cart" not in st.session_state:
            st.session_state.cart = []

        st.subheader("Добавить блюдо")

        top_items = pd.read_sql(
            "SELECT oi.item_name, m.price, m.category, m.custom_price, "
            "SUM(oi.quantity) AS cnt "
            "FROM order_items oi "
            "JOIN menu m ON m.name = oi.item_name "
            "WHERE m.custom_price = 0 "
            "GROUP BY oi.item_name "
            "ORDER BY cnt DESC LIMIT 6",
            conn,
        )
        if not top_items.empty:
            # группируем рядом по категории (внутри — по популярности)
            top_items = top_items.sort_values(
                ["category", "cnt"], ascending=[True, False]
            ).reset_index(drop=True)

            palette = [
                "#e76f51", "#2a9d8f", "#e9c46a", "#457b9d",
                "#8ab17d", "#c9184a", "#577590", "#f4a261",
            ]
            categories_here = top_items["category"].unique().tolist()
            cat_color = {
                cat: palette[i % len(palette)]
                for i, cat in enumerate(categories_here)
            }

            css_rules = []
            for i in range(len(top_items)):
                color = cat_color[top_items.loc[i, "category"]]
                css_rules.append(
                    f".st-key-quick_{i} button {{"
                    f"border:2px solid {color} !important;"
                    f"padding:0.1rem 0.5rem !important;"
                    f"font-size:0.75rem !important;"
                    f"min-height:1.7rem !important;"
                    f"line-height:1.1 !important;"
                    f"}}"
                )
            st.markdown(f"<style>{''.join(css_rules)}</style>", unsafe_allow_html=True)

            st.caption("⚡ Часто заказывают")
            quick_row = st.container(horizontal=True, gap="small")
            with quick_row:
                for i, ti in top_items.iterrows():
                    if st.button(ti["item_name"], key=f"quick_{i}"):
                        quick_note = (
                            "Melange" if ti["category"] == "Frühstück" else ""
                        )
                        st.session_state.cart.append(
                            {
                                "item_name": ti["item_name"],
                                "price": float(ti["price"]),
                                "quantity": 1,
                                "note": quick_note,
                            }
                        )
                        st.rerun()

        search_query = st.text_input(
            "🔍 Поиск", placeholder="начни печатать название...", key="item_search"
        )
        matches = menu_df
        if search_query:
            matches = search_menu(search_query, menu_df)
            if matches.empty:
                st.warning("Ничего не найдено")
                matches = menu_df

        row_add = st.container(horizontal=True, vertical_alignment="bottom", gap="small")
        with row_add:
            item = st.selectbox("Блюдо", matches["name"].sort_values(), width=280)
            item_row = menu_df[menu_df["name"] == item].iloc[0]
            if item_row["custom_price"]:
                price = st.number_input(
                    "Цена, €", min_value=0.0, step=0.5,
                    value=float(item_row["price"]), key="manual_price",
                )
            else:
                price = float(item_row["price"])
                st.write(f"**{price:.2f} €**")
            add_clicked = st.button("➕ Добавить")

        note = ""
        if item_row["category"] == "Frühstück":
            note = st.selectbox(
                "Кофе/чай к завтраку",
                ["Melange", "Verlängerter", "Espresso", "Tee", "Heiße Schokolade"],
                key="breakfast_drink",
            )
        extra_note = st.text_input(
            "Уточнение (необязательно) — напр. без сахара, отдельно", key="extra_note"
        )
        if extra_note:
            note = f"{note}, {extra_note}" if note else extra_note

        if add_clicked:
            st.session_state.cart.append(
                {"item_name": item, "price": price, "quantity": 1, "note": note}
            )

        if item_row["image_path"] and os.path.exists(item_row["image_path"]):
            st.image(item_row["image_path"], width=200, caption=item)

        if st.session_state.cart:
            st.subheader("Текущий заказ")
            total = 0.0
            for idx, row in enumerate(st.session_state.cart):
                label = row["item_name"]
                if row.get("note"):
                    label += f" — :gray[_{row['note']}_]"
                st.markdown(label)

                line = st.container(
                    horizontal=True, vertical_alignment="center", gap="small"
                )
                with line:
                    minus_clicked = st.button("−", key=f"cart_minus_{idx}")
                    st.write(f"**{row['quantity']}**")
                    plus_clicked = st.button("+", key=f"cart_plus_{idx}")
                    st.write(f"{row['price'] * row['quantity']:.2f} €")
                    del_clicked = st.button("✖", key=f"cart_del_{idx}")

                if minus_clicked:
                    if row["quantity"] > 1:
                        st.session_state.cart[idx]["quantity"] -= 1
                    else:
                        st.session_state.cart.pop(idx)
                    st.rerun()
                if plus_clicked:
                    st.session_state.cart[idx]["quantity"] += 1
                    st.rerun()
                if del_clicked:
                    st.session_state.cart.pop(idx)
                    st.rerun()
                total += row["price"] * row["quantity"]
            st.write(f"**Итого нового: {total:.2f} €**")
            if existing_total > 0:
                st.write(
                    f"Всего по столику: **{total + existing_total:.2f} €** "
                    f"(уже было {existing_total:.2f} €)"
                )

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
                            "INSERT INTO order_items "
                            "(order_id, item_name, price, quantity, note) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (
                                order_id,
                                row["item_name"],
                                row["price"],
                                row["quantity"],
                                row.get("note") or None,
                            ),
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

# ---------- Заказы ----------
with tab_open:
    conn = get_conn()
    menu_df = pd.read_sql("SELECT * FROM menu ORDER BY category, name", conn)

    status_choice = st.radio("Статус", ["Открытые", "Оплаченные"], horizontal=True)
    status_value = "открыт" if status_choice == "Открытые" else "оплачен"

    orders_df = pd.read_sql(
        "SELECT id, table_name, created_at FROM orders WHERE status = ? "
        "ORDER BY created_at DESC",
        conn,
        params=(status_value,),
    )
    if orders_df.empty:
        st.info("Заказов нет")

    for _, order in orders_df.iterrows():
        oid = int(order["id"])
        with st.expander(order["table_name"]):
            details_key = f"show_details_{oid}"
            if details_key not in st.session_state:
                st.session_state[details_key] = False
            if st.button("ℹ️ Детали", key=f"details_btn_{oid}"):
                st.session_state[details_key] = not st.session_state[details_key]
            if st.session_state[details_key]:
                st.caption(f"Заказ №{oid} · {order['created_at']}")

            items = pd.read_sql(
                "SELECT id, item_name, price, quantity, note FROM order_items "
                "WHERE order_id = ?",
                conn,
                params=(oid,),
            )
            total = 0.0

            if status_value == "открыт":
                for _, it in items.iterrows():
                    label = it["item_name"]
                    if it["note"]:
                        label += f" — :gray[_{it['note']}_]"
                    st.markdown(label)

                    line = st.container(
                        horizontal=True, vertical_alignment="center", gap="small"
                    )
                    with line:
                        minus_clicked = st.button("−", key=f"open_minus_{it['id']}")
                        st.write(f"**{it['quantity']}**")
                        plus_clicked = st.button("+", key=f"open_plus_{it['id']}")
                        st.write(f"{it['price'] * it['quantity']:.2f} €")
                        del_clicked = st.button("✖", key=f"open_del_{it['id']}")

                    if minus_clicked:
                        if it["quantity"] > 1:
                            conn.execute(
                                "UPDATE order_items SET quantity = quantity - 1 "
                                "WHERE id = ?",
                                (int(it["id"]),),
                            )
                        else:
                            conn.execute(
                                "DELETE FROM order_items WHERE id = ?",
                                (int(it["id"]),),
                            )
                        conn.commit()
                        st.rerun()
                    if plus_clicked:
                        conn.execute(
                            "UPDATE order_items SET quantity = quantity + 1 "
                            "WHERE id = ?",
                            (int(it["id"]),),
                        )
                        conn.commit()
                        st.rerun()
                    if del_clicked:
                        conn.execute(
                            "DELETE FROM order_items WHERE id = ?", (int(it["id"]),)
                        )
                        conn.commit()
                        st.rerun()
                    total += it["price"] * it["quantity"]
                st.write(f"**Итого: {total:.2f} €**")

                with st.expander("➕ Добавить позицию в этот заказ"):
                    add_q = st.text_input("Поиск", key=f"add_search_{oid}")
                    add_matches = menu_df
                    if add_q:
                        add_matches = search_menu(add_q, menu_df)
                        if add_matches.empty:
                            add_matches = menu_df
                    add_item = st.selectbox(
                        "Блюдо", add_matches["name"].sort_values(), key=f"add_item_{oid}"
                    )
                    add_row = menu_df[menu_df["name"] == add_item].iloc[0]
                    if add_row["custom_price"]:
                        add_price = st.number_input(
                            "Цена, €", min_value=0.0, step=0.5,
                            value=float(add_row["price"]), key=f"add_price_{oid}",
                        )
                    else:
                        add_price = float(add_row["price"])
                        st.write(f"{add_price:.2f} €")
                    add_qty = st.number_input(
                        "Кол-во", min_value=1, step=1, value=1, key=f"add_qty_{oid}"
                    )
                    add_note = st.text_input("Уточнение", key=f"add_note_{oid}")
                    if st.button("Добавить в заказ", key=f"add_btn_{oid}"):
                        conn.execute(
                            "INSERT INTO order_items "
                            "(order_id, item_name, price, quantity, note) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (
                                oid,
                                add_item,
                                add_price,
                                add_qty,
                                add_note or None,
                            ),
                        )
                        conn.commit()
                        st.rerun()

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💰 Закрыть и оплатить", key=f"close_{oid}"):
                        conn.execute(
                            "UPDATE orders SET status = 'оплачен', closed_at = ? "
                            "WHERE id = ?",
                            (datetime.now().isoformat(), oid),
                        )
                        still_open = conn.execute(
                            "SELECT COUNT(*) FROM orders "
                            "WHERE table_name = ? AND status = 'открыт'",
                            (order["table_name"],),
                        ).fetchone()[0]
                        if still_open == 0:
                            conn.execute(
                                "DELETE FROM tables WHERE name = ?",
                                (order["table_name"],),
                            )
                        conn.commit()
                        st.rerun()
                with col_b:
                    if st.button("🗑 Удалить заказ", key=f"delorder_{oid}"):
                        conn.execute(
                            "DELETE FROM order_items WHERE order_id = ?", (oid,)
                        )
                        conn.execute("DELETE FROM orders WHERE id = ?", (oid,))
                        conn.commit()
                        st.rerun()

            else:
                for _, it in items.iterrows():
                    label = f"{it['item_name']} × {it['quantity']}"
                    if it["note"]:
                        label += f"  \n:gray[_{it['note']}_]"
                    st.markdown(label)
                    total += it["price"] * it["quantity"]
                st.write(f"**Итого: {total:.2f} €**")
                if st.button("🗑 Удалить заказ", key=f"delpaid_{oid}"):
                    conn.execute(
                        "DELETE FROM order_items WHERE order_id = ?", (oid,)
                    )
                    conn.execute("DELETE FROM orders WHERE id = ?", (oid,))
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
                    price_label = (
                        "цена уточняется у официанта"
                        if row["custom_price"]
                        else f"{row['price']:.2f} €"
                    )
                    st.write(f"**{row['name']}** — {price_label}")

    st.divider()
    with st.form("add_menu_item"):
        st.subheader("Добавить блюдо в меню")
        name = st.text_input("Название")
        custom = st.checkbox(
            "Цену каждый раз вводит официант (например, мороженое на развес)"
        )
        price = st.number_input(
            "Цена, €" if not custom else "Цена по умолчанию, €",
            min_value=0.0, step=0.5,
        )
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
                "INSERT INTO menu (name, price, category, image_path, custom_price) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, price, category, image_path, int(custom)),
            )
            conn.commit()
            st.rerun()
    conn.close()
