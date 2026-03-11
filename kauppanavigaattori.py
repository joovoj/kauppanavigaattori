import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import os

st.set_page_config(
    page_title="🌿 Kauppanavigaattori",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .eco-a { background-color: #1e8449; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 1.2em; }
    .eco-b { background-color: #58d68d; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 1.2em; }
    .eco-c { background-color: #f4d03f; color: #333; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 1.2em; }
    .eco-d { background-color: #e67e22; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 1.2em; }
    .eco-e { background-color: #c0392b; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 1.2em; }
    .metric-box { background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 8px 0; border-left: 4px solid #2ecc71; }
    .product-title { font-size: 1.4em; font-weight: bold; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

# === HISTORY ===
HISTORY_FILE = "ostohistoria.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

if "history" not in st.session_state:
    st.session_state.history = load_history()

# === API FUNCTIONS ===
OFF_BASE = "https://world.openfoodfacts.org"

def get_product_by_barcode(barcode: str) -> dict | None:
    url = f"{OFF_BASE}/api/v2/product/{barcode}.json"
    fields = "product_name,brands,categories_tags_en,nutrition_grades,ecoscore_grade,ecoscore_score,ecoscore_data,nova_group,nutriments,packaging_tags,labels_tags,ingredients_text,image_front_url,carbon_footprint_from_known_ingredients_100g,packagings"
    try:
        r = requests.get(url, params={"fields": fields}, timeout=10,
                         headers={"User-Agent": "KauppaNavigaattori/1.0"})
        data = r.json()
        if data.get("status") == 1:
            return data["product"]
    except Exception:
        pass
    return None

def search_products(query: str, page: int = 1) -> list[dict]:
    url = f"{OFF_BASE}/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page": page,
        "page_size": 12,
        "fields": "code,product_name,brands,nutrition_grades,ecoscore_grade,ecoscore_score,nova_group,image_front_small_url,categories_tags_en"
    }
    try:
        r = requests.get(url, params=params, timeout=10,
                         headers={"User-Agent": "KauppaNavigaattori/1.0"})
        data = r.json()
        return data.get("products", [])
    except Exception:
        return []

# === DISPLAY HELPERS ===
GRADE_LABELS = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E"}
NOVA_DESC = {
    1: "🥦 Minimally processed",
    2: "🧂 Culinary ingredients",
    3: "🍞 Processed food",
    4: "🍟 Ultra-processed"
}

CARBON_BENCHMARKS = {
    # kg CO2e per 100g - rough estimates for context
    "beef": 2.7,
    "pork": 0.7,
    "chicken": 0.43,
    "dairy": 0.34,
    "eggs": 0.2,
    "vegetables": 0.05,
    "fruits": 0.07,
    "legumes": 0.08,
}

def grade_html(grade: str, kind: str = "eco") -> str:
    if not grade or grade == "unknown":
        return "<span style='background:#aaa;color:white;padding:3px 10px;border-radius:4px;'>?</span>"
    g = grade.lower()
    return f"<span class='{kind}-{g}'>{g.upper()}</span>"

def nova_badge(nova: int | None) -> str:
    if nova is None:
        return "Ei tietoa"
    colors = {1: "#1e8449", 2: "#58d68d", 3: "#e67e22", 4: "#c0392b"}
    c = colors.get(nova, "#aaa")
    return f"<span style='background:{c};color:white;padding:3px 10px;border-radius:4px;font-weight:bold;'>NOVA {nova}</span>"

def display_product_detail(product: dict):
    name = product.get("product_name", "Tuntematon tuote")
    brand = product.get("brands", "")
    eco_grade = product.get("ecoscore_grade", "unknown")
    eco_score = product.get("ecoscore_score", None)
    nutri_grade = product.get("nutrition_grades", "unknown")
    nova = product.get("nova_group", None)
    carbon = product.get("carbon_footprint_from_known_ingredients_100g", None)
    image_url = product.get("image_front_url", None)

    col1, col2 = st.columns([1, 2])
    with col1:
        if image_url:
            st.image(image_url, width=200)
        else:
            st.markdown("📦 *Ei kuvaa*")

    with col2:
        st.markdown(f"<div class='product-title'>{name}</div>", unsafe_allow_html=True)
        if brand:
            st.markdown(f"*{brand}*")

        st.markdown("---")
        # Scores row
        scores_col1, scores_col2, scores_col3 = st.columns(3)
        with scores_col1:
            st.markdown("**🌿 Eco-Score**")
            st.markdown(grade_html(eco_grade), unsafe_allow_html=True)
            if eco_score is not None:
                st.caption(f"Pisteet: {eco_score}/100")
        with scores_col2:
            st.markdown("**🥗 Nutri-Score**")
            st.markdown(grade_html(nutri_grade, kind="eco"), unsafe_allow_html=True)
        with scores_col3:
            st.markdown("**⚙️ NOVA-ryhmä**")
            st.markdown(nova_badge(nova), unsafe_allow_html=True)
            if nova:
                st.caption(NOVA_DESC.get(nova, ""))

    # Carbon footprint
    st.markdown("### 🌍 Hiilijalanjälki")
    if carbon:
        st.metric("CO₂e / 100g (tunnetuista ainesosista)", f"{carbon:.1f} g")
        # Visual bar
        max_carbon = 300
        pct = min(carbon / max_carbon * 100, 100)
        color = "#1e8449" if carbon < 50 else "#e67e22" if carbon < 150 else "#c0392b"
        st.markdown(
            f"""<div style="background:#eee;border-radius:6px;height:18px;width:100%;">
            <div style="background:{color};width:{pct:.0f}%;height:18px;border-radius:6px;"></div>
            </div><small>0 g &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 300 g CO₂e / 100g</small>""",
            unsafe_allow_html=True
        )
        st.markdown("")
    else:
        st.info("Hiilijalanjälkitietoa ei saatavilla tälle tuotteelle.")

    # Eco-Score details
    eco_data = product.get("ecoscore_data", {})
    if eco_data:
        st.markdown("### 📊 Ympäristövaikutukset")
        adjustments = eco_data.get("adjustments", {})

        detail_items = []
        packaging = adjustments.get("packaging", {})
        if packaging:
            pack_score = packaging.get("score", None)
            pack_value = packaging.get("value", None)
            if pack_score is not None:
                detail_items.append(("📦 Pakkaus (pisteet)", pack_score))
            if pack_value is not None:
                detail_items.append(("📦 Pakkausvaikutus", pack_value))

        origins = adjustments.get("origins_of_ingredients", {})
        if origins:
            tr_score = origins.get("transportation_score", None)
            epi = origins.get("epi_score", None)
            if tr_score is not None:
                detail_items.append(("🚚 Kuljetusvaikutus", tr_score))
            if epi is not None:
                detail_items.append(("🌱 Alkuperämaan ympäristöindeksi", epi))

        threatened = adjustments.get("threatened_species", {})
        if threatened:
            t_val = threatened.get("value", None)
            if t_val is not None:
                detail_items.append(("🦋 Uhanalaiset lajit (vaikutus)", t_val))

        labels = adjustments.get("labels", {})
        if labels:
            labels_val = labels.get("value", None)
            labels_list = labels.get("labels", [])
            if labels_val is not None:
                detail_items.append(("🏷️ Sertifikaattivaikutus", labels_val))
            if labels_list:
                st.markdown(f"**Sertifikaatit:** {', '.join(labels_list)}")

        if detail_items:
            for label, val in detail_items:
                st.markdown(f"- **{label}:** `{val}`")

    # Packaging info
    packagings = product.get("packagings", [])
    if packagings:
        st.markdown("### 📦 Pakkausmateriaalit")
        for p in packagings:
            material = p.get("material", {})
            mat_label = material.get("en", "") if isinstance(material, dict) else str(material)
            shape = p.get("shape", {})
            shape_label = shape.get("en", "") if isinstance(shape, dict) else str(shape)
            recycling = p.get("recycling", {})
            rec_label = recycling.get("en", "") if isinstance(recycling, dict) else str(recycling)
            if mat_label or shape_label:
                st.markdown(f"- **{shape_label}**: {mat_label} — ♻️ {rec_label or 'kierrätystieto puuttuu'}")

    # Labels/certifications
    labels_tags = product.get("labels_tags", [])
    eco_labels = [l for l in labels_tags if any(k in l for k in ["organic", "bio", "fair", "rainforest", "msc", "utz", "eco"])]
    if eco_labels:
        st.markdown("### 🏷️ Ympäristösertifikaatit")
        for label in eco_labels:
            st.markdown(f"✅ `{label.replace('en:', '').replace('-', ' ').title()}`")

    # Ingredients
    ingredients = product.get("ingredients_text", "")
    if ingredients:
        with st.expander("🔍 Ainesosat"):
            st.write(ingredients)

    # Add to history
    st.markdown("---")
    qty = st.number_input("Määrä (kpl)", min_value=1, max_value=50, value=1, key=f"qty_{name}")
    if st.button(f"➕ Lisää ostohistoriaan", key=f"add_{name}"):
        entry = {
            "name": name,
            "brand": brand,
            "eco_grade": eco_grade,
            "eco_score": eco_score,
            "nutri_grade": nutri_grade,
            "nova": nova,
            "carbon_100g": carbon,
            "quantity": qty,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        st.session_state.history.append(entry)
        save_history(st.session_state.history)
        st.success(f"✅ {name} lisätty ostoshistoriaan!")

def display_product_card(product: dict):
    name = product.get("product_name", "?")
    brand = product.get("brands", "")
    eco = product.get("ecoscore_grade", "?")
    nutri = product.get("nutrition_grades", "?")
    nova = product.get("nova_group", None)
    img = product.get("image_front_small_url", None)
    code = product.get("code", "")

    eco_color = {"a": "🟢", "b": "🟡", "c": "🟠", "d": "🔴", "e": "🔴"}.get(str(eco).lower(), "⚪")

    with st.container():
        c1, c2 = st.columns([1, 3])
        with c1:
            if img:
                st.image(img, width=80)
        with c2:
            st.markdown(f"**{name}**")
            if brand:
                st.caption(brand)
            st.markdown(
                f"{eco_color} Eco: **{str(eco).upper()}** &nbsp;|&nbsp; 🥗 Nutri: **{str(nutri).upper()}** &nbsp;|&nbsp; ⚙️ NOVA: **{nova or '?'}**",
                unsafe_allow_html=True
            )
            if st.button("Näytä tiedot", key=f"detail_{code}_{name[:10]}"):
                full = get_product_by_barcode(code)
                if full:
                    st.session_state.selected_product = full
                    st.session_state.view = "detail"
                    st.rerun()

# === SIDEBAR ===
with st.sidebar:
    st.markdown("## 🌿 Kauppanavigaattori")
    st.markdown("Kestävä ostaminen helpoksi")
    st.markdown("---")
    page = st.radio("Näkymä", ["🔍 Hae tuotteita", "📷 Viivakoodi", "🛒 Ostoshistoria", "📈 Tilastot"], index=0)
    st.markdown("---")
    st.markdown("**Tietolähteet:**")
    st.markdown("- [Open Food Facts](https://world.openfoodfacts.org)")
    st.markdown("- Eco-Score (A–E)")
    st.markdown("- NOVA-ryhmittely")
    st.markdown("- Nutri-Score")
    st.caption("Data: Open Food Facts CC-BY-SA")

# === MAIN CONTENT ===
if "view" not in st.session_state:
    st.session_state.view = "search"
if "selected_product" not in st.session_state:
    st.session_state.selected_product = None

# Back button
if st.session_state.view == "detail":
    if st.button("⬅️ Takaisin hakuun"):
        st.session_state.view = "search"
        st.session_state.selected_product = None
        st.rerun()
    if st.session_state.selected_product:
        display_product_detail(st.session_state.selected_product)

elif "Hae" in page:
    st.title("🔍 Hae tuotteita")
    st.markdown("Etsi tuotteita nimen tai brändin perusteella ja tarkista niiden ympäristövaikutus.")

    search_query = st.text_input("Hakusana (esim. 'maito', 'oatly', 'fazer')", placeholder="Kirjoita tuotteen nimi...")

    if search_query:
        with st.spinner("Haetaan tuotteita..."):
            products = search_products(search_query)

        if products:
            st.success(f"Löydettiin {len(products)} tuotetta")
            st.markdown("---")
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                show_eco_only = st.checkbox("Näytä vain Eco-Score-tuotteet")
            with col2:
                sort_by = st.selectbox("Järjestä", ["Oletuksena", "Paras Eco-Score", "Paras Nutri-Score"])

            if show_eco_only:
                products = [p for p in products if p.get("ecoscore_grade") and p.get("ecoscore_grade") not in ["unknown", "not-applicable"]]

            if sort_by == "Paras Eco-Score":
                order = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}
                products = sorted(products, key=lambda p: order.get(str(p.get("ecoscore_grade", "e")).lower(), 5))
            elif sort_by == "Paras Nutri-Score":
                order = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}
                products = sorted(products, key=lambda p: order.get(str(p.get("nutrition_grades", "e")).lower(), 5))

            for p in products:
                display_product_card(p)
                st.markdown("---")
        else:
            st.warning("Ei tuloksia. Kokeile eri hakusanaa.")
    else:
        st.info("💡 Kirjoita tuotteen nimi hakukenttään. Voit hakea suomeksi tai englanniksi.")
        st.markdown("""
        **Esimerkkihakuja:**
        - `oatly` – kauranjuoma
        - `fazer` – Fazerin tuotteet
        - `coca cola` – virvoitusjuomat
        - `luomu maito` – luomumaitotuotteet
        - `salmon` – lohi
        """)

elif "Viivakoodi" in page:
    st.title("📷 Viivakoodihaku")
    st.markdown("Syötä tuotteen viivakoodi (EAN-13) löytääksesi tarkat tiedot.")

    barcode = st.text_input("Viivakoodi", placeholder="Esim. 6416539002014")
    if st.button("🔍 Hae viivakoodilla") and barcode:
        with st.spinner("Haetaan tuotetta..."):
            product = get_product_by_barcode(barcode.strip())
        if product:
            display_product_detail(product)
        else:
            st.error("Tuotetta ei löydy tietokannasta. Tarkista viivakoodi tai hae nimellä.")

    st.markdown("---")
    st.markdown("""
    **💡 Vinkki:** Open Food Facts -sovelluksella voit skannata viivakoodin puhelimellasi. 
    Voit myös katsoa viivakoodin tuotteen pakkauksesta ja syöttää sen tähän.

    **Suomalaisia viivakoodeja testiin:**
    - `6410405082657` – Valio maito
    - `6416539002014` – Fazer
    """)

elif "Ostoshistoria" in page:
    st.title("🛒 Ostoshistoria")

    if not st.session_state.history:
        st.info("Et ole vielä lisännyt yhtään tuotetta ostoshistoriaan.")
    else:
        df = pd.DataFrame(st.session_state.history)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tuotteita yhteensä", len(df))
        with col2:
            eco_avg = df[df["eco_score"].notna()]["eco_score"].mean()
            st.metric("Keskimääräinen Eco-Score", f"{eco_avg:.0f}/100" if not pd.isna(eco_avg) else "N/A")
        with col3:
            carbon_sum = df[df["carbon_100g"].notna()]["carbon_100g"].sum()
            st.metric("CO₂e yhteensä (g/100g perusteella)", f"{carbon_sum:.1f} g" if carbon_sum else "N/A")

        st.markdown("---")
        st.dataframe(
            df[["date", "name", "brand", "eco_grade", "nutri_grade", "nova", "carbon_100g", "quantity"]].rename(columns={
                "date": "Päivä", "name": "Tuote", "brand": "Brändi",
                "eco_grade": "Eco", "nutri_grade": "Nutri", "nova": "NOVA",
                "carbon_100g": "CO₂e/100g (g)", "quantity": "Kpl"
            }),
            use_container_width=True
        )

        if st.button("🗑️ Tyhjennä historia"):
            st.session_state.history = []
            save_history([])
            st.success("Historia tyhjennetty.")
            st.rerun()

        # Download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Lataa CSV", csv, "ostoshistoria.csv", "text/csv")

elif "Tilastot" in page:
    st.title("📈 Ostostilastot")

    if not st.session_state.history or len(st.session_state.history) < 1:
        st.info("Lisää tuotteita ostoshistoriaan nähdäksesi tilastot.")
    else:
        df = pd.DataFrame(st.session_state.history)

        st.markdown("### 🌿 Eco-Score-jakauma")
        eco_counts = df["eco_grade"].value_counts()
        grade_order = ["a", "b", "c", "d", "e", "unknown", "not-applicable"]
        eco_counts = eco_counts.reindex([g for g in grade_order if g in eco_counts.index])
        st.bar_chart(eco_counts)

        st.markdown("### ⚙️ NOVA-ryhmäjakauma")
        nova_counts = df["nova"].value_counts().sort_index()
        st.bar_chart(nova_counts)

        st.markdown("### 📋 Yhteenveto")
        eco_good = df[df["eco_grade"].isin(["a", "b"])].shape[0]
        eco_bad = df[df["eco_grade"].isin(["d", "e"])].shape[0]
        nova4 = df[df["nova"] == 4].shape[0]

        st.markdown(f"""
        - ✅ **Hyvä Eco-Score (A/B):** {eco_good} tuotetta ({eco_good/len(df)*100:.0f}%)
        - ⚠️ **Huono Eco-Score (D/E):** {eco_bad} tuotetta ({eco_bad/len(df)*100:.0f}%)
        - 🍟 **Ultra-prosessoitua (NOVA 4):** {nova4} tuotetta ({nova4/len(df)*100:.0f}%)
        """)

        st.markdown("---")
        st.markdown("### 💡 Parannusehdotukset")
        if eco_bad > 0:
            bad_products = df[df["eco_grade"].isin(["d", "e"])]["name"].tolist()
            st.warning(f"Seuraavilla tuotteilla on korkea ympäristövaikutus: {', '.join(bad_products[:5])}")
        if nova4 > 0:
            ultra = df[df["nova"] == 4]["name"].tolist()
            st.info(f"Ultra-prosessoidut tuotteet: {', '.join(ultra[:5])}")
        if eco_good == len(df):
            st.success("🎉 Hienoa! Kaikki ostoksesi ovat ympäristöystävällisiä!")
