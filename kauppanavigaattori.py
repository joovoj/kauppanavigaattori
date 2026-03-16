import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime, date
import os

st.set_page_config(
    page_title="🌿 Kauppanavigaattori",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── TEEMA: valkoinen pohja, vihreät tekstit ──────────────────────────────────
st.markdown("""
<style>
  /* Pohjaväri */
  .stApp { background-color: #ffffff; }
  section[data-testid="stSidebar"] { background-color: #f4faf4; }

  /* Kaikki teksti vihreäksi */
  body, p, span, div, label, li, td, th, h1, h2, h3, h4 {
      color: #1a5c2a !important;
  }
  .stMarkdown, .stText { color: #1a5c2a !important; }
  h1 { color: #0d3b18 !important; font-size: 2rem !important; }
  h2 { color: #145a26 !important; }
  h3 { color: #1a5c2a !important; }

  /* Napit */
  .stButton > button {
      background-color: #1a5c2a !important;
      color: #ffffff !important;
      border: none !important;
      border-radius: 8px !important;
      font-weight: 700 !important;
      font-size: 14px !important;
      padding: 0.4rem 1rem !important;
  }
  .stButton > button * { color: #ffffff !important; }
  .stButton > button:hover {
      background-color: #0d3b18 !important;
      color: #ffffff !important;
  }
  .stButton > button p { color: #ffffff !important; }

  /* Input-kentät – valkoinen tausta, tumma teksti, vihreä reuna */
  .stTextInput > div > div > input {
      border: 2px solid #1a5c2a !important;
      border-radius: 6px !important;
      background-color: #ffffff !important;
      color: #1a5c2a !important;
  }
  .stTextInput > div > div > input::placeholder { color: #aaa !important; }
  .stNumberInput > div > div > input {
      border: 2px solid #1a5c2a !important;
      border-radius: 6px !important;
      background-color: #ffffff !important;
      color: #1a5c2a !important;
  }
  .stSelectbox > div > div {
      background-color: #ffffff !important;
      color: #1a5c2a !important;
      border: 2px solid #1a5c2a !important;
      border-radius: 6px !important;
  }
  .stSelectbox > div > div > div { color: #1a5c2a !important; }
  .stTextArea > div > div > textarea {
      background-color: #ffffff !important;
      color: #1a5c2a !important;
      border: 2px solid #1a5c2a !important;
      border-radius: 6px !important;
  }

  /* Metriikkaboxes */
  [data-testid="metric-container"] {
      background: #f4faf4;
      border: 1px solid #b7dfbc;
      border-radius: 10px;
      padding: 12px;
  }

  /* Info/warning-boxies */
  .stAlert { border-radius: 8px !important; }

  /* Kortti */
  .product-card {
      background: #f9fdf9;
      border: 1px solid #c3e6c8;
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 12px;
  }

  /* Arvosana-badget */
  .grade-a { background:#1e8449;color:white;padding:3px 10px;border-radius:5px;font-weight:bold; }
  .grade-b { background:#58d68d;color:#0d3b18;padding:3px 10px;border-radius:5px;font-weight:bold; }
  .grade-c { background:#f4d03f;color:#333;padding:3px 10px;border-radius:5px;font-weight:bold; }
  .grade-d { background:#e67e22;color:white;padding:3px 10px;border-radius:5px;font-weight:bold; }
  .grade-e { background:#c0392b;color:white;padding:3px 10px;border-radius:5px;font-weight:bold; }

  /* Divider */
  hr { border-color: #c3e6c8 !important; }

  /* Tabs */
  .stTabs [data-baseweb="tab"] { color: #1a5c2a !important; font-weight: 600; }
  .stTabs [aria-selected="true"] { border-bottom: 3px solid #1a5c2a !important; }

  /* Dataframe header */
  .stDataFrame thead tr th { background: #e8f5ea !important; color: #0d3b18 !important; }
</style>
""", unsafe_allow_html=True)

# ── APUDATA ──────────────────────────────────────────────────────────────────
HISTORY_FILE = "ostohistoria.json"
SHOPPING_FILE = "ostoslista.json"
WASTE_FILE = "kaappitavarat.json"

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

for key, file in [("history", HISTORY_FILE), ("shopping", SHOPPING_FILE), ("waste", WASTE_FILE)]:
    if key not in st.session_state:
        st.session_state[key] = load_json(file)

# ── OPEN FOOD FACTS API ───────────────────────────────────────────────────────
import time

OFF   = "https://world.openfoodfacts.org"
# Käytetään vain välttämättömät kentät – vähemmän dataa = nopeampi vastaus
FIELDS_SEARCH = "code,product_name,brands,nutrition_grades,ecoscore_grade,ecoscore_score,nova_group,image_front_small_url,categories_tags"
FIELDS_FULL   = "code,product_name,brands,nutrition_grades,ecoscore_grade,ecoscore_score,nova_group,image_front_url,categories_tags,carbon_footprint_from_known_ingredients_100g,packagings,labels_tags,ecoscore_data,nutriments,ingredients_text"
HEADERS = {"User-Agent": "KauppaNavigaattori/2.0"}

def _fetch(url: str, params: dict, timeout: int = 15) -> dict | None:
    """Yksinkertainen fetch ilman raskasta retry-logiikkaa."""
    try:
        r = requests.get(url, params=params, timeout=timeout, headers=HEADERS)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

@st.cache_data(ttl=600, show_spinner=False)
def search_products(query: str) -> list:
    """
    Haku kolmella eri strategialla peräkkäin.
    Palauttaa ensimmäisen joka antaa tuloksia.
    """
    # Strategia 1: Yksinkertainen haku (nopein, toimii 90% ajasta)
    data = _fetch(f"{OFF}/cgi/search.pl", {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 16,
        "fields": FIELDS_SEARCH,
        "sort_by": "unique_scans_n",
    })
    results = (data or {}).get("products", [])

    # Strategia 2: v2 search API – jos 1 ei toimi
    if len(results) < 1:
        data = _fetch(f"{OFF}/api/v2/search", {
            "search_terms": query,
            "page_size": 16,
            "fields": FIELDS_SEARCH,
            "sort_by": "unique_scans_n",
        })
        results = (data or {}).get("products", [])

    # Strategia 3: Kielikohtainen haku englanniksi – viimeinen vaihtoehto
    if len(results) < 1:
        data = _fetch(f"https://world.openfoodfacts.org/cgi/search.pl", {
            "search_terms": query,
            "action": "process",
            "json": 1,
            "page_size": 16,
            "fields": FIELDS_SEARCH,
        })
        results = (data or {}).get("products", [])

    return [p for p in results if p.get("product_name")]

@st.cache_data(ttl=1800, show_spinner=False)
def get_by_barcode(barcode: str) -> dict | None:
    """Viivakoodihaku – välimuistissa 30 min."""
    data = _fetch(f"{OFF}/api/v2/product/{barcode}.json", {"fields": FIELDS_FULL})
    if data and data.get("status") == 1:
        return data["product"]
    return None

@st.cache_data(ttl=600, show_spinner=False)
def find_alternatives(categories_str: str, own_code: str) -> list:
    """Etsii parempia Eco-Score A vaihtoehtoja samasta kategoriasta."""
    if not categories_str:
        return []
    cat = categories_str.split(",")[-1].strip().replace("en:", "").replace("fi:", "")
    data = _fetch(f"{OFF}/cgi/search.pl", {
        "action": "process",
        "tagtype_0": "categories", "tag_contains_0": "contains", "tag_0": cat,
        "tagtype_1": "ecoscore_grade", "tag_contains_1": "contains", "tag_1": "a",
        "json": 1, "page_size": 8, "fields": FIELDS_SEARCH
    })
    results = (data or {}).get("products", [])
    return [p for p in results if p.get("code") != own_code and p.get("product_name")][:4]

def get_recipe_links(product_name: str, categories: list) -> list:
    name = product_name.lower()
    cats = " ".join(categories).lower()
    term = requests.utils.quote(product_name.split(" ")[0])
    links = [
        {"site": "🍽️ Kotikokki.net",    "url": f"https://www.kotikokki.net/reseptit/haku/?search={term}",  "desc": f"Reseptejä: {product_name.split()[0]}"},
        {"site": "🛒 K-Ruoka reseptit",  "url": f"https://www.k-ruoka.fi/reseptit?search={term}",           "desc": f"K-Ruoka: {product_name.split()[0]}"},
        {"site": "🥣 Soppa365",          "url": f"https://www.soppa365.fi/?s={term}",                        "desc": f"Soppa365: {product_name.split()[0]}"},
        {"site": "👨‍🍳 Ruokaisa.fi",    "url": f"https://www.ruokaisa.fi/?s={term}",                        "desc": f"Ruokaisa: {product_name.split()[0]}"},
    ]
    if any(k in cats+name for k in ["kasvis","vegan","oat","kaura","soija","tofu","papu","linssi"]):
        links.append({"site": "🌱 Vegaaniliitto", "url": f"https://www.vegaaniliitto.fi/?s={term}", "desc": "Kasvis- ja vegaanireseptit"})
    if any(k in cats+name for k in ["kala","lohi","ahven","siika","fish","salmon"]):
        links.append({"site": "🐟 Kalareseptit", "url": f"https://www.kotikokki.net/reseptit/haku/?search={term}+kala", "desc": "Kalareseptit"})
    return links


# ── TUOTEOSASTO-TUNNISTUS ─────────────────────────────────────────────────────
DEPARTMENT_KEYWORDS = {
    "🥛 Maitotuotteet & munat": ["milk","dairy","maito","jogurt","yogurt","juusto","cheese","kerma","cream","voi","butter","kananmuna","egg","quark","viili","piimä"],
    "🥩 Liha & kala":           ["meat","liha","beef","pork","chicken","kana","sika","nauta","lohi","salmon","fish","kala","silli","tonnikala","tuna","makkara","sausage","broiler"],
    "🥦 Kasvikset & hedelmät":  ["vegetable","fruit","kasvis","hedelmä","vihannes","tomaatti","tomato","kurkku","salaatti","salad","omena","apple","banaani","banana","porkkana","carrot","peruna","potato","paprika","sipuli","onion","mango","appelsiini"],
    "🍞 Leipä & leivonnaiset":  ["bread","leipä","ruisleipä","pulla","bun","cake","kakku","keksi","cookie","cracker","muffin","bagel","wrap","tortilla","rye"],
    "🥫 Säilykkeet & kuivatuotteet": ["pasta","rice","riisi","noodle","can","säilyke","legume","papu","linssi","lentil","chickpea","herne","oat","kaura","müsli","cereal","jauhot","flour","sugar","sokeri","suola","salt"],
    "🧴 Juomat":                ["drink","juice","mehu","vesi","water","kalja","beer","viini","wine","kahvi","coffee","tee","tea","smoothie","limonadi","soda","kaura","oat milk","soijajuoma","soy milk"],
    "🍫 Makeiset & snacksit":   ["chocolate","suklaa","candy","makeinen","snack","sipsit","chips","karkki","jäätelö","ice cream","popcorn","bar","patukat"],
    "🧊 Pakasteet":             ["frozen","pakaste","pakastettu"],
    "🧹 Muut":                  []
}

def guess_department(product: dict) -> str:
    """Arvaa tuotteen kauppaosasto kategoriatägien ja nimen perusteella."""
    name = (product.get("product_name","") + " " + " ".join(product.get("categories_tags",[])) + " " + product.get("brands","")).lower()
    for dept, keywords in DEPARTMENT_KEYWORDS.items():
        if any(k in name for k in keywords):
            return dept
    return "🧹 Muut"

# ── SESONKITUOTTEET ───────────────────────────────────────────────────────────
def get_season_products() -> dict:
    """Palauttaa kuukauden mukaan suomalaiset sesonkituotteet."""
    month = datetime.now().month
    seasons = {
        (12,1,2): {
            "name": "🌨️ Talvi",
            "tip": "Kausi kotimaiselle juureksille, punajuurelle ja talvisäilyköille.",
            "products": [
                {"name":"Lanttu","reason":"Suomalainen talviklassikko – Eco A, kasvaa Suomessa","search":"lanttu"},
                {"name":"Punajuuri","reason":"Edullinen, kasvaa Suomessa ympäri vuoden","search":"punajuuri"},
                {"name":"Kaali","reason":"Kotimainen, hyvä Eco-Score, paljon C-vitamiinia","search":"kaali"},
                {"name":"Juuripersilja","reason":"Talven supervihannes, kotimaisena kevyt hiilijalanjälki","search":"juuripersilja"},
                {"name":"Hapankaali","reason":"Fermentoitu – pitkä säilyvyys, vähän hävikkiä","search":"hapankaali"},
                {"name":"Silakoita","reason":"Kotimainen kala, pienin hiilijalanjälki kalalajeista","search":"silakka"},
            ]
        },
        (3,4,5): {
            "name": "🌱 Kevät",
            "tip": "Kevään ensimmäiset vihannekset ja kotimaiset yrtit kasvavat.",
            "products": [
                {"name":"Pinaatti","reason":"Ensimmäinen kotimainen lehtivihannes keväällä","search":"pinaatti"},
                {"name":"Nokkonen","reason":"Ilmainen ja erittäin ravinteikasta – Eco A","search":"nokkonen"},
                {"name":"Raparperi","reason":"Kotimainen kevätklassikko, C-vitamiinia","search":"raparperi"},
                {"name":"Retiisi","reason":"Nopein kotimainen kesävihannes","search":"retiisi"},
                {"name":"Vihreä sipuli","reason":"Kasvaa Suomessa, pienin jalanjälki","search":"vihreä sipuli"},
                {"name":"Silakka","reason":"Parhaassa iskussa keväällä, kotimainen kala","search":"silakka"},
            ]
        },
        (6,7,8): {
            "name": "☀️ Kesä",
            "tip": "Suomalaisten sesonki! Mansikat, mustaherukat ja uudet perunat huipussaan.",
            "products": [
                {"name":"Mansikka","reason":"Suomen mansikka – lyhyt matka, pieni jalanjälki","search":"mansikka"},
                {"name":"Mustikka","reason":"Luonnonmarjana erittäin pieni Eco-Score","search":"mustikka"},
                {"name":"Uusi peruna","reason":"Kotimainen kesäperuna – parempi kuin tuontiperuna","search":"uusi peruna"},
                {"name":"Kurkku","reason":"Kasvihuonekurkku Suomesta kesällä parhaimmillaan","search":"kurkku"},
                {"name":"Tomaatti","reason":"Kotimainen parempi kuin tuotu talvella","search":"tomaatti"},
                {"name":"Kesäkurpitsa","reason":"Nopeakasvuinen, erittäin pieni jalanjälki","search":"kesäkurpitsa"},
            ]
        },
        (9,10,11): {
            "name": "🍂 Syksy",
            "tip": "Sadonkorjuuaika – juurekset, sienet ja omenat parhaimmillaan.",
            "products": [
                {"name":"Omena","reason":"Kotimainen omena parhaimmillaan syksyllä","search":"omena"},
                {"name":"Sienet","reason":"Metsäsienet ilmaiseksi tai pienellä jalanjäljellä","search":"sieni"},
                {"name":"Kurpitsa","reason":"Sadonkorjuuajan klassikko, monipuolinen","search":"kurpitsa"},
                {"name":"Porkkana","reason":"Kotimainen, edullinen, Eco A","search":"porkkana"},
                {"name":"Puolukka","reason":"Suomalainen metsämarja – Eco A, pitkä säilyvyys","search":"puolukka"},
                {"name":"Kaalikeitto","reason":"Syksyn perinteisin suomalainen ruoka","search":"kaali"},
            ]
        },
    }
    for months, data in seasons.items():
        if month in months:
            return data
    return seasons[(6,7,8)]

# ── OSTOHISTORIA ─────────────────────────────────────────────────────────────
HISTORY_FILE = "ostohistoria.json"

def load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_to_history(product: dict, price: float = 0.0):
    history = load_history()
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "name": product.get("product_name","Tuntematon"),
        "brand": product.get("brands",""),
        "eco": str(product.get("ecoscore_grade","?")).upper(),
        "nutri": str(product.get("nutrition_grades","?")).upper(),
        "nova": product.get("nova_group"),
        "carbon": product.get("carbon_footprint_from_known_ingredients_100g"),
        "price": price,
    }
    history.append(entry)
    with open(HISTORY_FILE,"w",encoding="utf-8") as f:
        json.dump(history[-200:], f, ensure_ascii=False)  # max 200 merkintää

# ── KASVISVAIHTOEHTO-TUNNISTUS ────────────────────────────────────────────────
MEAT_TO_PLANT = {
    "jauheliha":  {"alt":"Härkäpapu- tai soijarouhe","tip":"Sama rakenne, 80% pienempi hiilijalanjälki","search":"härkäpapu rouhe"},
    "nauta":      {"alt":"Linssit tai herneet","tip":"Proteiinia yhtä paljon, murto-osa päästöistä","search":"linssit"},
    "sianliha":   {"alt":"Tofu tai seitan","tip":"Hyvä proteiinilähde, huomattavasti ekologisempi","search":"tofu"},
    "kana":       {"alt":"Kananpapu tai kikherne","tip":"Sama proteiini, kasviproteiini on ekologisempaa","search":"kikherne"},
    "broiler":    {"alt":"Nyhtökaura tai härkäpapu","tip":"Kotimaiset kasvivaihtoehdot kanalle","search":"nyhtökaura"},
    "makkara":    {"alt":"Kasvisgrillimakkara","tip":"Kasvismakkara maistuu samalta, vähemmän prosessoitu","search":"kasvisgrillimakkara"},
    "lohi":       {"alt":"Silakka tai muikku","tip":"Kotimainen kala – pienempi jalanjälki kuin lohi","search":"silakka"},
    "maito":      {"alt":"Kauramaito","tip":"Kotimainen kauramaito – 80% pienempi jalanjälki","search":"kauramaito"},
    "jogurtti":   {"alt":"Kaurajogurtti","tip":"Kasvipohjainen jogurtti, sama rakenne","search":"kaurajogurtti"},
    "juusto":     {"alt":"Kasvisjuusto tai nutritional yeast","tip":"Juustoa käytetään pieninä määrinä – harkitse vaihtoehtoa","search":"kasvisjuusto"},
}

def get_plant_alternative(product: dict) -> dict | None:
    """Tarkistaa onko tuotteelle kasvispohjainen vaihtoehto."""
    name = product.get("product_name","").lower()
    cats = " ".join(product.get("categories_tags",[])).lower()
    combined = name + " " + cats
    for keyword, alt_data in MEAT_TO_PLANT.items():
        if keyword in combined:
            return alt_data
    return None


# ── PISTEYTYS-APUFUNKTIOT ─────────────────────────────────────────────────────
def grade_badge(grade: str) -> str:
    g = str(grade).lower()
    if g in ["a","b","c","d","e"]:
        return f"<span class='grade-{g}'>{g.upper()}</span>"
    return "<span style='background:#aaa;color:white;padding:3px 10px;border-radius:5px;'>?</span>"

def eco_text(grade: str) -> str:
    return {
        "a": "🌱 Erinomainen ympäristövalinta – minimaalinen ympäristövaikutus.",
        "b": "👍 Hyvä valinta – pieni ympäristövaikutus verrattuna samaan kategoriaan.",
        "c": "🟡 Kohtalainen – ympäristövaikutus on keskitasoa.",
        "d": "⚠️ Melko korkea ympäristövaikutus – jos kiinnostaa, vaihtoehtoja löytyy!",
        "e": "🔴 Korkea ympäristövaikutus – haluatko tutustua kestävämpiin vaihtoehtoihin?",
    }.get(str(grade).lower(), "ℹ️ Eco-Score ei ole saatavilla tälle tuotteelle.")

def nutri_text(grade: str) -> str:
    return {
        "a": "🥗 Ravitsemuksellisesti erinomainen – loistava valinta terveyden kannalta!",
        "b": "👌 Hyvä ravintosisältö – sopii hyvin säännölliseen käyttöön.",
        "c": "🟡 Kohtuullinen ravintosisältö – ok silloin tällöin.",
        "d": "⚠️ Melko vähän ravinteita suhteessa kaloritiheyteen.",
        "e": "🍟 Herkuttelutuote – sopii satunnaiseen nauttimiseen.",
    }.get(str(grade).lower(), "ℹ️ Nutri-Score ei ole saatavilla.")

def nova_text(nova) -> str:
    return {
        1: "🥦 NOVA 1 – Käsittelemätön tai minimaalisesti käsitelty. Paras vaihtoehto!",
        2: "🧂 NOVA 2 – Keittiöaines (esim. öljy, sokeri, suola). Käytetään ruoanlaitossa.",
        3: "🍞 NOVA 3 – Prosessoitu elintarvike. Sisältää joitain lisäaineita.",
        4: "🍟 NOVA 4 – Ultraprosessoitu tuote. Sopii satunnaiseen herkutteluun.",
    }.get(nova, "ℹ️ NOVA-ryhmä ei saatavilla.")

def carbon_context(carbon_g) -> str:
    if carbon_g is None:
        return ""
    if carbon_g < 30:
        return "🌱 Hyvin pieni hiilijalanjälki"
    elif carbon_g < 80:
        return "👍 Kohtalaisen pieni hiilijalanjälki"
    elif carbon_g < 200:
        return "🟡 Keskitasoinen hiilijalanjälki"
    elif carbon_g < 400:
        return "⚠️ Melko suuri hiilijalanjälki"
    else:
        return "🔴 Suuri hiilijalanjälki"

def eco_stars(score) -> str:
    if score is None:
        return ""
    stars = int(score / 20)
    return "⭐" * stars + "☆" * (5 - stars)

# ── TUOTTEEN TIEDOT ───────────────────────────────────────────────────────────
def show_product_detail(product: dict, show_alternatives: bool = True):
    name = product.get("product_name") or "Tuntematon tuote"
    brand = product.get("brands", "")
    eco = product.get("ecoscore_grade", "?")
    eco_score = product.get("ecoscore_score")
    nutri = product.get("nutrition_grades", "?")
    nova = product.get("nova_group")
    carbon = product.get("carbon_footprint_from_known_ingredients_100g")
    img = product.get("image_front_url")

    col_img, col_info = st.columns([1, 2])
    with col_img:
        if img:
            st.image(img, width=180)
    with col_info:
        st.markdown(f"## {name}")
        if brand:
            st.markdown(f"*{brand}*")
        if eco_score:
            st.markdown(f"**Ympäristöpisteet:** {eco_stars(eco_score)} ({eco_score}/100)")

    st.markdown("---")

    # Kolme pääpistytystä vierekkäin selityksineen
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🌿 Eco-Score")
        st.markdown(grade_badge(eco), unsafe_allow_html=True)
        st.markdown(f"<small>{eco_text(eco)}</small>", unsafe_allow_html=True)
    with c2:
        st.markdown("### 🥗 Nutri-Score")
        st.markdown(grade_badge(nutri), unsafe_allow_html=True)
        st.markdown(f"<small>{nutri_text(nutri)}</small>", unsafe_allow_html=True)
    with c3:
        st.markdown("### ⚙️ NOVA")
        nova_str = f"NOVA {nova}" if nova else "?"
        st.markdown(f"<span style='background:#1a5c2a;color:white;padding:3px 10px;border-radius:5px;font-weight:bold;'>{nova_str}</span>", unsafe_allow_html=True)
        st.markdown(f"<small>{nova_text(nova)}</small>", unsafe_allow_html=True)

    st.markdown("---")

    # Hiilijalanjälki
    st.markdown("### 🌍 Hiilijalanjälki")
    if carbon:
        context = carbon_context(carbon)
        st.markdown(f"**{carbon:.1f} g CO₂e / 100 g** &nbsp; {context}", unsafe_allow_html=True)
        pct = min(carbon / 400 * 100, 100)
        col = "#1e8449" if carbon < 80 else "#e67e22" if carbon < 200 else "#c0392b"
        st.markdown(f"""
        <div style="background:#e8f5ea;border-radius:8px;height:16px;">
          <div style="background:{col};width:{pct:.0f}%;height:16px;border-radius:8px;"></div>
        </div>
        <small style="color:#1a5c2a;">🌱 Pieni &nbsp;→&nbsp; 🔴 Suuri (max näyttää 400 g)</small>
        """, unsafe_allow_html=True)
    else:
        st.info("Hiilijalanjälkitieto ei saatavilla. Eco-Score antaa suuntaa ympäristövaikutuksesta.")

    # Pakkaus
    packagings = product.get("packagings", [])
    if packagings:
        st.markdown("### 📦 Pakkausmateriaalit")
        for p in packagings:
            m = p.get("material", {})
            mat = m.get("en", "") if isinstance(m, dict) else str(m)
            s = p.get("shape", {})
            shape = s.get("en", "") if isinstance(s, dict) else str(s)
            r = p.get("recycling", {})
            rec = r.get("en", "") if isinstance(r, dict) else str(r)
            if mat or shape:
                st.markdown(f"- **{shape}**: {mat} — ♻️ {rec or 'Kierrätystieto puuttuu'}")

    # Sertifikaatit
    labels = [l for l in product.get("labels_tags", [])
              if any(k in l for k in ["organic","bio","fair","rainforest","msc","utz","eco","luomu"])]
    if labels:
        st.markdown("### 🏷️ Ympäristösertifikaatit")
        for l in labels:
            st.markdown(f"✅ **{l.replace('en:','').replace('fi:','').replace('-',' ').title()}**")

    # Lisää ostoslistalle
    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        qty = st.number_input("Kappalemäärä", 1, 50, 1, key=f"qty_{name[:15]}")
    with col_b:
        price = st.number_input("Hinta (€)", 0.0, 200.0, 0.0, step=0.05, key=f"price_{name[:15]}")
    with col_c:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🛒 Lisää ostoslistalle", key=f"shop_{name[:15]}"):
            item = {
                "name": name, "brand": brand, "eco": eco, "nutri": nutri, "nova": nova,
                "carbon": carbon, "qty": qty, "price": price,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            st.session_state.shopping.append(item)
            save_json(SHOPPING_FILE, st.session_state.shopping)
            st.success(f"✅ {name} lisätty ostoslistalle!")

    if st.button("📦 Lisää kaappitavaroihin (hävikinseuranta)", key=f"waste_{name[:15]}"):
        item = {
            "name": name, "brand": brand,
            "added": datetime.now().strftime("%Y-%m-%d"),
            "expiry": "", "qty": 1
        }
        st.session_state.waste.append(item)
        save_json(WASTE_FILE, st.session_state.waste)
        st.success("✅ Lisätty kaappitavaroihin!")

    # Vaihtoehdot
    if show_alternatives:
        st.markdown("---")
        st.markdown("### 💡 Kestävämpiä vaihtoehtoja samasta kategoriasta")
        st.caption("Nämä tuotteet ovat samasta tuoteryhmästä ja niillä on parempi Eco-Score A:")
        with st.spinner("Etsitään vaihtoehtoja..."):
            cats_str = ",".join(product.get("categories_tags", []))
            alts = find_alternatives(cats_str, str(product.get("code", "")))
        if alts:
            alt_cols = st.columns(min(len(alts), 4))
            for i, alt in enumerate(alts[:4]):
                with alt_cols[i]:
                    alt_img = alt.get("image_front_small_url")
                    if alt_img:
                        st.image(alt_img, width=80)
                    st.markdown(f"**{alt.get('product_name','?')[:30]}**")
                    st.markdown(grade_badge(alt.get("ecoscore_grade","?")), unsafe_allow_html=True)
                    if st.button("Näytä", key=f"alt_{alt.get('code',i)}"):
                        full = get_by_barcode(alt.get("code",""))
                        if full:
                            st.session_state.sel = full
                            st.rerun()
        else:
            st.info("Vaihtoehtoja ei löydy tällä hetkellä – kokeile hakea itse eri tuotteita.")

def show_product_card(p: dict):
    name = p.get("product_name") or "?"
    brand = p.get("brands","")
    eco = p.get("ecoscore_grade","?")
    nutri = p.get("nutrition_grades","?")
    nova = p.get("nova_group")
    img = p.get("image_front_small_url")
    code = p.get("code","")
    eco_col = {"a":"🟢","b":"🟡","c":"🟠","d":"🔴","e":"🔴"}.get(str(eco).lower(),"⚪")

    with st.container():
        st.markdown("<div class='product-card'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 4, 1])
        with c1:
            if img:
                st.image(img, width=65)
        with c2:
            st.markdown(f"**{name}**")
            if brand:
                st.caption(brand)
            st.markdown(
                f"{eco_col} Eco: **{str(eco).upper()}** &nbsp;|&nbsp; 🥗 Nutri: **{str(nutri).upper()}** &nbsp;|&nbsp; ⚙️ NOVA: **{nova or '?'}**",
                unsafe_allow_html=True)
        with c3:
            if st.button("Avaa →", key=f"open_{code}_{name[:8]}"):
                full = get_by_barcode(code)
                if full:
                    st.session_state.sel = full
                    st.session_state.view = "detail"
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ── SIVUPALKKI ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌿 Kauppanavigaattori")
    st.caption("Kestävät valinnat helposti – ilman syyllistämistä")
    st.markdown("---")
    page = st.radio("", [
        "🔍 Hae tuotteita",
        "📷 Viivakoodihaku",
        "🛒 Ostoslista",
        "🗑️ Hävikinseuranta",
        "🌱 Sesonkituotteet",
        "📊 Ostohistoria",
        "📈 Tilastot",
        "ℹ️ Tietoa pisteytyksistä"
    ], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("**Tietolähteet:**")
    st.markdown("- [Open Food Facts](https://world.openfoodfacts.org) (CC-BY-SA)")
    st.markdown("- Eco-Score · Nutri-Score · NOVA")
    st.caption("Tuotedata voi olla puutteellista. Hinnat syötetään manuaalisesti.")

# ── STATE ─────────────────────────────────────────────────────────────────────
if "view" not in st.session_state:
    st.session_state.view = "list"
if "sel" not in st.session_state:
    st.session_state.sel = None

# Takaisin-nappi
if st.session_state.view == "detail":
    if st.button("⬅️ Takaisin"):
        st.session_state.view = "list"
        st.session_state.sel = None
        st.rerun()
    if st.session_state.sel:
        show_product_detail(st.session_state.sel)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# SIVUT
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. HAE TUOTTEITA ──────────────────────────────────────────────────────────
if "Hae" in page:
    st.title("🔍 Hae tuotteita")
    st.markdown("Löydä tuotteet ja tarkista niiden ympäristö- ja ravitsemustiedot ennen ostosta.")

    q = st.text_input("Hakusana", placeholder="esim. maito, oatly, fazer, lohi...")
    sort_by = st.selectbox("Järjestä tulokset", ["Oletuksena", "Paras Eco-Score ensin", "Paras Nutri-Score ensin"])

    if q:
        prog = st.progress(0, text="Haetaan tuotteita...")
        products = search_products(q)
        prog.progress(100, text="Valmis!")
        prog.empty()

        if products:
            order = {"a":0,"b":1,"c":2,"d":3,"e":4}
            if sort_by == "Paras Eco-Score ensin":
                products = sorted(products, key=lambda p: order.get(str(p.get("ecoscore_grade","e")).lower(),5))
            elif sort_by == "Paras Nutri-Score ensin":
                products = sorted(products, key=lambda p: order.get(str(p.get("nutrition_grades","e")).lower(),5))

            good_eco = sum(1 for p in products if str(p.get("ecoscore_grade","")).lower() in ["a","b"])
            st.success(f"Löydettiin {len(products)} tuotetta – {good_eco} hyvällä Eco-Scorella (A/B) 🌿")
            st.markdown("---")
            for p in products:
                show_product_card(p)
        else:
            st.warning("Ei tuloksia. Kokeile eri hakusanaa tai englanninkielistä nimeä (esim. 'oat milk', 'salmon').")
    else:
        st.markdown("""
        **Hakuvinkkejä 🌿**
        - `maito` tai `kaura maito` – maitovaihtoehdot
        - `lohi` – kalatuotteet
        - `fazer` tai `valio` – brändihaku
        - `luomu` – luomumerkityt tuotteet
        - `kasvispohjainen` – kasvistuotteet
        """)

# ── 2. VIIVAKOODIHAKU ─────────────────────────────────────────────────────────
elif "Viivakoodi" in page:
    st.title("📷 Viivakoodihaku")
    st.markdown("Löytyy tuotteen pakkauksesta (EAN-13). Syötä numerot tähän.")

    barcode = st.text_input("Viivakoodi", placeholder="esim. 6410405082657")
    if st.button("🔍 Hae") and barcode:
        with st.spinner("Haetaan..."):
            p = get_by_barcode(barcode.strip())
        if p:
            st.session_state.sel = p
            show_product_detail(p)
        else:
            st.error("Tuotetta ei löydy. Tarkista viivakoodi tai hae tuotteen nimellä.")

    st.markdown("---")
    st.markdown("""
    **Testaa näillä suomalaisilla viivakoodeilla:**
    - `6410405082657` – Valio tuote
    - `6416539002014` – Fazer
    """)

# ── 3. OSTOSLISTA ─────────────────────────────────────────────────────────────
elif "Ostoslista" in page:
    st.title("🛒 Ostoslista")
    st.markdown("Seuraa ostoksiasi, hintoja ja ympäristövaikutusta yhdessä paikassa.")

    if not st.session_state.shopping:
        st.info("Ostoslista on tyhjä. Lisää tuotteita hakemalla ja avaamalla tuotetiedot.")
    else:
        df = pd.DataFrame(st.session_state.shopping)

        # Yhteenvedot
        total_price = (df["price"] * df["qty"]).sum()
        total_items = df["qty"].sum()
        good_eco = df[df["eco"].isin(["a","b"])].shape[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💶 Yhteishinta", f"{total_price:.2f} €")
        c2.metric("📦 Tuotteita", int(total_items))
        c3.metric("🌿 Hyvä Eco (A/B)", f"{good_eco}/{len(df)}")
        eco_avg = df[df["eco"].isin(["a","b","c","d","e"])]["eco"].map({"a":5,"b":4,"c":3,"d":2,"e":1}).mean()
        c4.metric("📊 Eco-taso (ka)", f"{eco_avg:.1f}/5" if not pd.isna(eco_avg) else "N/A")

        st.markdown("---")

        # Nopea vinkki
        bad = df[df["eco"].isin(["d","e"])]["name"].tolist()
        if bad:
            st.warning(f"💡 Vinkki: Näillä tuotteilla on korkea ympäristövaikutus – voisit etsiä kestävämpää vaihtoehtoa: **{', '.join(bad[:3])}**")

        st.markdown("### Ostoslistan tuotteet")
        for i, row in df.iterrows():
            ec = row.get("eco","?")
            nt = row.get("nutri","?")
            nova = row.get("nova","?")
            price_total = row["price"] * row["qty"]
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.markdown(f"**{row['name']}** _{row.get('brand','')}_")
                st.markdown(
                    f"Eco: {grade_badge(ec)} &nbsp; Nutri: {grade_badge(nt)} &nbsp; NOVA: **{nova}**",
                    unsafe_allow_html=True)
            with col2:
                st.markdown(f"**{row['qty']} kpl** × {row['price']:.2f} € = **{price_total:.2f} €**")
            with col3:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.shopping.pop(i)
                    save_json(SHOPPING_FILE, st.session_state.shopping)
                    st.rerun()
            st.markdown("---")

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Lataa ostoslista CSV", csv, "ostoslista.csv", "text/csv")

        if st.button("🗑️ Tyhjennä koko lista"):
            st.session_state.shopping = []
            save_json(SHOPPING_FILE, [])
            st.rerun()

# ── 4. HÄVIKINSEURANTA ────────────────────────────────────────────────────────
elif "Hävikinseuranta" in page:
    st.title("🗑️ Hävikinseuranta")
    st.markdown("Seuraa mitä kaapissasi on, jotta vähennät ruokahävikkiä ja säästät rahaa.")

    # Lisää manuaalisesti
    with st.expander("➕ Lisää tuote kaappitavaroihin"):
        n1, n2, n3 = st.columns(3)
        with n1:
            w_name = st.text_input("Tuotteen nimi", key="w_name")
        with n2:
            w_expiry = st.date_input("Parasta ennen", key="w_exp", value=date.today())
        with n3:
            w_qty = st.number_input("Määrä (kpl)", 1, 20, 1, key="w_qty")
        if st.button("Lisää kaappiin") and w_name:
            st.session_state.waste.append({
                "name": w_name, "brand": "",
                "added": date.today().strftime("%Y-%m-%d"),
                "expiry": str(w_expiry),
                "qty": w_qty
            })
            save_json(WASTE_FILE, st.session_state.waste)
            st.success(f"✅ {w_name} lisätty!")
            st.rerun()

    st.markdown("---")

    if not st.session_state.waste:
        st.info("Kaappitavaralista on tyhjä. Lisää tuotteita seurataksesi viimeisiä käyttöpäiviä.")
    else:
        today = date.today()
        expiring_soon = []
        for item in st.session_state.waste:
            exp = item.get("expiry","")
            if exp:
                try:
                    d = date.fromisoformat(exp)
                    days = (d - today).days
                    item["_days"] = days
                    if days <= 3:
                        expiring_soon.append(item)
                except Exception:
                    item["_days"] = 999
            else:
                item["_days"] = 999

        if expiring_soon:
            st.error(f"⚠️ **{len(expiring_soon)} tuotetta** vanhenee pian – käytä ensin!")
            for item in expiring_soon:
                d = item.get("_days", 0)
                label = "**tänään!**" if d == 0 else f"**{d} päivässä**"
                st.markdown(f"🔴 **{item['name']}** vanhenee {label}")

        st.markdown("### 🗃️ Kaikki kaappitavarat")
        for i, item in enumerate(st.session_state.waste):
            days = item.get("_days", 999)
            color = "🔴" if days <= 1 else "🟠" if days <= 3 else "🟡" if days <= 7 else "🟢"
            exp_text = f"Vanhenee: {item['expiry']} ({days} pv)" if item.get("expiry") else "Ei päiväystä"
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"{color} **{item['name']}** — {exp_text} — {item['qty']} kpl")
            with c2:
                if st.button("✅ Käytetty", key=f"used_{i}"):
                    st.session_state.waste.pop(i)
                    save_json(WASTE_FILE, st.session_state.waste)
                    st.rerun()
            st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 💡 Hävikintorjuntavinkit")
        st.markdown("""
        - 🥶 **Pakasta** ennen viimeistä käyttöpäivää – leipä, liha ja monet muut säilyvät hyvin
        - 🥣 **FIFO-periaate** (First In, First Out): vanhimmat tuotteet edessä kaapissa
        - 📋 **Suunnittele ateriat** etukäteen ja osta vain tarvitsemasi
        - 🍲 **Ylijääneistä** voi tehdä uuden ruoan – esim. vihannekset keitoksi
        - 🛒 **Älä osta nälkäisenä** – impulssiostokset lisäävät hävikkiä
        - 🌡️ **Tarkista jääkaapin lämpötila** – +4°C on optimi
        """)

# ── 5. TILASTOT ───────────────────────────────────────────────────────────────
elif "Tilastot" in page:
    st.title("📈 Ostostilastot")

    if not st.session_state.shopping:
        st.info("Lisää tuotteita ostoslistalle nähdäksesi tilastosi.")
    else:
        df = pd.DataFrame(st.session_state.shopping)

        st.markdown("### 🌿 Eco-Score jakauma")
        eco_counts = df["eco"].value_counts()
        grade_order = [g for g in ["a","b","c","d","e"] if g in eco_counts.index]
        eco_ordered = eco_counts.reindex(grade_order)
        st.bar_chart(eco_ordered)

        st.markdown("### ⚙️ NOVA-ryhmäjakauma")
        nova_df = df["nova"].dropna().astype(str).value_counts().sort_index()
        st.bar_chart(nova_df)

        st.markdown("### 💶 Kulutus ekoluokittain")
        df["total_price"] = df["price"] * df["qty"]
        eco_spend = df.groupby("eco")["total_price"].sum().reindex(
            [g for g in ["a","b","c","d","e"] if g in df["eco"].values])
        st.bar_chart(eco_spend)

        st.markdown("---")
        st.markdown("### 📋 Yhteenveto")
        total = len(df)
        good_eco = df[df["eco"].isin(["a","b"])].shape[0]
        bad_eco = df[df["eco"].isin(["d","e"])].shape[0]
        nova4 = df[df["nova"]==4].shape[0] if "nova" in df else 0
        total_spend = (df["price"] * df["qty"]).sum()
        st.markdown(f"""
        - ✅ **Hyvä Eco (A/B):** {good_eco}/{total} tuotetta ({good_eco/total*100:.0f}%)
        - ⚠️ **Korkea ympäristövaikutus (D/E):** {bad_eco}/{total} tuotetta
        - 🍟 **Ultra-prosessoitu (NOVA 4):** {nova4} tuotetta
        - 💶 **Yhteiskulutus:** {total_spend:.2f} €
        """)

        if good_eco == total:
            st.success("🎉 Loistavaa! Kaikki ostoksesi ovat ympäristöystävällisiä valintoja!")
        elif good_eco / total >= 0.5:
            st.success("👍 Hyvää työtä! Yli puolet ostoksistasi on kestäviä valintoja.")
        else:
            st.info("💡 Pienilläkin muutoksilla voit parantaa ympäristövaikutustasi. Kokeile etsiä A/B-vaihtoehtoja!")

# ── 6. TIETOA PISTEYTYKSISTÄ ──────────────────────────────────────────────────
elif "Tietoa" in page:
    st.title("ℹ️ Mitä pisteet tarkoittavat?")
    st.markdown("Tässä on selkeä selitys kaikille pisteytyksille.")

    tab1, tab2, tab3, tab4 = st.tabs(["🌿 Eco-Score", "🥗 Nutri-Score", "⚙️ NOVA", "🌍 Hiilijalanjälki"])

    with tab1:
        st.markdown("""
        ## 🌿 Eco-Score – Miten ympäristöystävällinen tuote on?

        Eco-Score on yksinkertainen kirjain A–E joka kertoo, kuinka paljon ruoka rasittaa ympäristöä.
        **A on paras, E on heikoin.**

        | Kirjain | Mitä se käytännössä tarkoittaa | Tyypillisiä tuotteita |
        |---|---|---|
        | **A** 🟢 | Luonnolle erittäin ystävällinen | Luomuvihannekset, pavut, linssit |
        | **B** 🟡 | Hyvä valinta ympäristön kannalta | Luomumaito, kotimainen kala |
        | **C** 🟠 | Ihan ok, ei erityisen hyvä eikä huono | Pasta, kananmuna, juusto |
        | **D** 🔴 | Rasittaa ympäristöä enemmän | Leikkeleet, tavallinen juusto |
        | **E** 🔴 | Kuormittaa ympäristöä paljon | Naudanliha, lammas |

        **Mistä pisteet tulevat?** Katsotaan koko matka pellolta kauppaan: viljely, tehdas, kuljetus ja pakkaus.
        Luomumerkki, kierrätettävä pakkaus ja lähituotanto parantavat pisteitä.

        💚 **Pieni vinkki:** Vaihda naudanliha kanaan tai kalaan – se on yksi nopeimmista tavoista pienentää ruoan ympäristövaikutusta.
        """)

    with tab2:
        st.markdown("""
        ## 🥗 Nutri-Score – Kuinka terveellinen tuote on?

        Nutri-Score kertoo yhdellä kirjaimella (A–E) onko ruoka ravitsemuksellisesti hyvä valinta.
        **A on paras, E on heikoin.**

        | Kirjain | Mitä se tarkoittaa |
        |---|---|
        | **A** 🟢 | Todella ravitseva – loistava arkiruoka |
        | **B** 🟡 | Hyvä valinta – sopii säännölliseen käyttöön |
        | **C** 🟠 | Ihan ok – ei erityisen hyvä eikä huono |
        | **D** 🔴 | Paljon sokeria, suolaa tai rasvaa |
        | **E** 🔴 | Herkuttelutuote – sopii silloin tällöin |

        **Miten pisteet lasketaan?** Katsotaan 100 grammaa tuotetta:
        - Miinuspisteitä: sokeri, suola, kova rasva, kalorit
        - Pluspisteitä: kuitu, proteiini, hedelmät, vihannekset

        🍫 **Muista:** E-arvosana ei tarkoita kiellettyä! Suklaa voi olla E, mutta se on silti ok herkutteluun.
        Nutri-Score auttaa vain valitsemaan paremmin kun on useampi vaihtoehto.
        """)

    with tab3:
        st.markdown("""
        ## ⚙️ NOVA – Kuinka valmis ruoka on tehtaalla tehty?

        NOVA ei kerro onko ruoka terveellistä – se kertoo **kuinka paljon teollisuus on käsitellyt sitä**.
        Numerot 1–4, jossa 1 on lähes luonnontilaista ja 4 on hyvin pitkälle prosessoitua.

        | Numero | Mitä se tarkoittaa | Esimerkkejä |
        |---|---|---|
        | **1** 🥦 | Suoraan luonnosta, ei juurikaan käsitelty | Omenat, porkkanat, kananmuna, lohi, riisi |
        | **2** 🧂 | Keittiön perusaineet | Öljy, suola, sokeri, voi, jauhot |
        | **3** 🍞 | Valmistettu ruoka, muutama lisäaine | Juusto, säilykkeet, savustettu kinkku, leipä |
        | **4** 🍟 | Tehdassali täynnä lisäaineita | Sipsit, makeiset, pikanuudelit, valmisateriat, energiajuomat |

        **Miksi tällä on väliä?** Tutkimukset viittaavat siihen, että NOVA 4 -ruokien syöminen joka päivä
        voi olla yhteydessä terveyshaittoihin. Mutta se ei tarkoita, että pizzaa tai sipsejä ei saisi syödä! 🍕
        """)

    with tab4:
        st.markdown("""
        ## 🌍 Hiilijalanjälki – Kuinka paljon tuote päästää hiilidioksidia?

        Hiilijalanjälki kertoo kuinka paljon ilmastolle haitallisia kaasuja syntyy kun tuote valmistetaan.
        Se mitataan grammoina CO₂ per 100 grammaa ruokaa. **Mitä pienempi luku, sitä parempi.**

        | Luku | Mitä se tarkoittaa | Tyypillisiä tuotteita |
        |---|---|---|
        | alle 30 g | 🌱 Erittäin pieni | Kasvikset, hedelmät, pavut |
        | 30–80 g | 👍 Pieni | Kananmuna, kala, kauramaito |
        | 80–200 g | 🟡 Kohtalainen | Sianliha, juusto, pasta |
        | 200–400 g | ⚠️ Suuri | Naudanliha |
        | yli 400 g | 🔴 Erittäin suuri | Karitsa, jauheliha |

        **Helpot keinot pienentää ruoan hiilijalanjälkeä:**
        - 🥦 Syö enemmän kasviksia – ne ovat aina pieniä hiilijalanjäljeltään
        - 🐟 Valitse kala naudanlihan sijaan kun sopii
        - 🥛 Kokeile kauramaitoa – sen jalanjälki on noin 80% pienempi kuin tavallisella maidolla
        - 🇫🇮 Suosi kotimaista – lyhyempi matka = vähemmän päästöjä kuljetuksesta
        """)

    st.markdown("---")
    st.markdown("""
    ### 🌟 Muista
    Kaikkia näitä pisteitä kannattaa käyttää **apuvälineenä**, ei tiukkana sääntönä.
    Pienetkin muutokset arjen valinnoissa vaikuttavat positiivisesti – jokainen hyvä valinta lasketaan! 💚
    """)
