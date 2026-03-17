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

# Suomi-hakusanojen käännökset englanniksi (OFF-data on pääosin englanniksi)
FI_TO_EN = {
    "maito": "milk", "kevytmaito": "semi skimmed milk", "täysmaito": "whole milk",
    "kauramaito": "oat milk", "soijamaito": "soy milk", "kaurajuoma": "oat drink",
    "jogurtti": "yogurt", "kermaviili": "sour cream", "raejuusto": "cottage cheese",
    "juusto": "cheese", "emmental": "emmental", "kananmuna": "egg",
    "voi": "butter", "margariini": "margarine", "kerma": "cream",
    "jauheliha": "minced meat", "naudan jauheliha": "beef mince",
    "broileri": "chicken", "kana": "chicken", "kalkkuna": "turkey",
    "lohi": "salmon", "silakka": "baltic herring", "muikku": "vendace",
    "tonnikala": "tuna", "silli": "herring", "sei": "saithe",
    "peruna": "potato", "porkkana": "carrot", "tomaatti": "tomato",
    "kurkku": "cucumber", "paprika": "bell pepper", "sipuli": "onion",
    "valkosipuli": "garlic", "pinaatti": "spinach", "parsakaali": "broccoli",
    "kaali": "cabbage", "salaatti": "lettuce", "punajuuri": "beetroot",
    "lanttu": "swede", "nauris": "turnip", "palsternakka": "parsnip",
    "kesäkurpitsa": "zucchini", "kurpitsa": "pumpkin",
    "omena": "apple", "banaani": "banana", "appelsiini": "orange",
    "mansikka": "strawberry", "mustikka": "blueberry", "puolukka": "lingonberry",
    "vadelma": "raspberry", "päärynä": "pear", "viinimarja": "currant",
    "pasta": "pasta", "riisi": "rice", "kaura": "oat", "vehnä": "wheat",
    "ruisleipä": "rye bread", "hapanleipä": "sourdough", "pulla": "bun",
    "linssit": "lentils", "kikherneet": "chickpeas", "härkäpapu": "fava bean",
    "papu": "bean", "soija": "soy", "tofu": "tofu",
    "nyhtökaura": "pulled oats", "härkis": "faba bean mince",
    "suklaa": "chocolate", "keksi": "cookie", "mysli": "muesli",
    "pähkinä": "nuts", "manteli": "almond", "cashew": "cashew",
    "oliiviöljy": "olive oil", "rypsiöljy": "rapeseed oil",
    "kahvi": "coffee", "tee": "tea", "mehu": "juice",
    "kivennäisvesi": "sparkling water", "limonadi": "lemonade",
}

def _translate_query(query: str) -> str:
    """Kääntää suomenkielisen hakusanan englanniksi OFF-hakua varten."""
    q = query.lower().strip()
    if q in FI_TO_EN:
        return FI_TO_EN[q]
    # Osittainen täsmäys
    for fi, en in FI_TO_EN.items():
        if fi in q:
            return q.replace(fi, en)
    return query

def _is_relevant(product: dict, query: str) -> bool:
    """Tarkistaa onko tuote relevantti haulle – suodattaa epäolennaiset pois."""
    name = (product.get("product_name") or "").lower()
    brand = (product.get("brands") or "").lower()
    cats = " ".join(product.get("categories_tags") or []).lower()
    combined = f"{name} {brand} {cats}"
    q_words = query.lower().split()
    # Vähintään yksi hakusana löytyy tuotetiedoista
    return any(w in combined for w in q_words if len(w) > 2)

@st.cache_data(ttl=600, show_spinner=False)
def search_products(query: str) -> list:
    """
    Haku kolmella strategialla. Käyttää suomi→englanti -käännöstä
    jos hakusana on suomeksi, jotta OFF:n englanninkielinen data löytyy.
    Suodattaa epäolennaiset tulokset pois.
    """
    en_query = _translate_query(query)
    use_en = en_query.lower() != query.lower()

    base_params = {
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 24,
        "fields": FIELDS_SEARCH,
        "sort_by": "unique_scans_n",
    }

    results = []

    # Strategia 1a: hae englanninkäännöksellä (jos suomenkielinen haku)
    if use_en:
        data = _fetch(f"{OFF}/cgi/search.pl", {**base_params, "search_terms": en_query})
        results = (data or {}).get("products", [])

    # Strategia 1b: hae alkuperäisellä hakusanalla
    if len(results) < 2:
        data = _fetch(f"{OFF}/cgi/search.pl", {**base_params, "search_terms": query})
        r2 = (data or {}).get("products", [])
        # Yhdistä tulokset, älä lisää duplikaatteja
        existing_codes = {p.get("code") for p in results}
        results += [p for p in r2 if p.get("code") not in existing_codes]

    # Strategia 2: v2 API viimeisenä
    if len(results) < 2:
        data = _fetch(f"{OFF}/api/v2/search", {
            "search_terms": en_query if use_en else query,
            "page_size": 24,
            "fields": FIELDS_SEARCH,
            "sort_by": "unique_scans_n",
        })
        r3 = (data or {}).get("products", [])
        existing_codes = {p.get("code") for p in results}
        results += [p for p in r3 if p.get("code") not in existing_codes]

    # Suodata: poista tuotteet joilla ei ole nimeä
    results = [p for p in results if p.get("product_name")]

    # Suodata: priorisoi relevantit tulokset ensin, mutta pidä kaikki
    relevant = [p for p in results if _is_relevant(p, en_query if use_en else query)]
    others = [p for p in results if not _is_relevant(p, en_query if use_en else query)]

    # Palauta relevantit ensin, sitten muut (max 20 yhteensä)
    return (relevant + others)[:20]

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

# ── FINELI – SUOMALAINEN ELINTARVIKETIETOKANTA (THL) ─────────────────────────
# Lähde: Fineli®, THL (thl.fi/fineli), CC BY 4.0
# Sisältää yleisimmät suomalaiset elintarvikkeet ravintosisältöineen per 100 g.
# Täydentää Open Food Facts -dataa tarkemmilla suomalaisilla arvoilla.

FINELI_DB = {
    "maito kevyt":          {"kcal":37, "proteiini":3.4,"rasva":0.5,"hh":4.7,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":21},
    "maito täysmaito":      {"kcal":61, "proteiini":3.2,"rasva":3.5,"hh":4.7,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":22},
    "maito rasvaton":       {"kcal":32, "proteiini":3.3,"rasva":0.1,"hh":4.8,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":23},
    "kauramaito":           {"kcal":44, "proteiini":1.0,"rasva":1.5,"hh":6.5,"kuitu":0.8,"suola":0.1,"ryhmä":"Kasvipohjaiset","fineli_id":5602},
    "soijamaito":           {"kcal":39, "proteiini":3.3,"rasva":1.8,"hh":2.5,"kuitu":0.4,"suola":0.1,"ryhmä":"Kasvipohjaiset","fineli_id":5601},
    "jogurtti maustamaton": {"kcal":59, "proteiini":3.9,"rasva":3.1,"hh":4.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":130},
    "kaurajogurtti":        {"kcal":57, "proteiini":2.5,"rasva":1.2,"hh":9.5,"kuitu":1.0,"suola":0.1,"ryhmä":"Kasvipohjaiset","fineli_id":5612},
    "kermaviili":           {"kcal":118,"proteiini":3.0,"rasva":10.0,"hh":3.5,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":143},
    "raejuusto":            {"kcal":72, "proteiini":12.4,"rasva":2.0,"hh":2.2,"kuitu":0.0,"suola":0.4,"ryhmä":"Maitotalous","fineli_id":177},
    "emmental":             {"kcal":370,"proteiini":28.0,"rasva":29.0,"hh":0.5,"kuitu":0.0,"suola":1.0,"ryhmä":"Juustot","fineli_id":160},
    "edam":                 {"kcal":326,"proteiini":25.0,"rasva":24.0,"hh":0.5,"kuitu":0.0,"suola":1.5,"ryhmä":"Juustot","fineli_id":161},
    "kananmuna":            {"kcal":143,"proteiini":12.6,"rasva":10.0,"hh":0.8,"kuitu":0.0,"suola":0.4,"ryhmä":"Munat","fineli_id":9},
    "voi":                  {"kcal":717,"proteiini":0.8,"rasva":80.0,"hh":0.0,"kuitu":0.0,"suola":1.2,"ryhmä":"Rasvat","fineli_id":63},
    "margariini":           {"kcal":517,"proteiini":0.2,"rasva":58.0,"hh":0.5,"kuitu":0.0,"suola":0.6,"ryhmä":"Rasvat","fineli_id":68},
    "naudan jauheliha":     {"kcal":243,"proteiini":17.0,"rasva":19.5,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Liha","fineli_id":397},
    "sian jauheliha":       {"kcal":214,"proteiini":17.0,"rasva":16.0,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Liha","fineli_id":398},
    "broilerin rintafilee": {"kcal":110,"proteiini":23.5,"rasva":1.5,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Siipikarja","fineli_id":427},
    "kalkkunan rintafilee": {"kcal":104,"proteiini":22.0,"rasva":1.2,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Siipikarja","fineli_id":437},
    "lohi":                 {"kcal":208,"proteiini":19.0,"rasva":14.0,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Kala","fineli_id":508},
    "silakka":              {"kcal":126,"proteiini":18.0,"rasva":6.0, "hh":0.0,"kuitu":0.0,"suola":0.2,"ryhmä":"Kala","fineli_id":503},
    "muikku":               {"kcal":88, "proteiini":18.0,"rasva":1.5,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Kala","fineli_id":507},
    "tonnikala säilyke":    {"kcal":116,"proteiini":25.5,"rasva":1.0,"hh":0.0,"kuitu":0.0,"suola":0.5,"ryhmä":"Kala","fineli_id":517},
    "nakkimakkara":         {"kcal":290,"proteiini":12.0,"rasva":26.0,"hh":3.0,"kuitu":0.0,"suola":1.8,"ryhmä":"Lihavalmisteet","fineli_id":461},
    "porkkana":             {"kcal":35, "proteiini":0.9,"rasva":0.2,"hh":7.5,"kuitu":2.4,"suola":0.1,"ryhmä":"Juurekset","fineli_id":234},
    "peruna":               {"kcal":72, "proteiini":1.9,"rasva":0.1,"hh":16.0,"kuitu":1.3,"suola":0.0,"ryhmä":"Juurekset","fineli_id":223},
    "lanttu":               {"kcal":26, "proteiini":1.2,"rasva":0.1,"hh":4.8,"kuitu":2.3,"suola":0.0,"ryhmä":"Juurekset","fineli_id":248},
    "punajuuri":            {"kcal":38, "proteiini":1.8,"rasva":0.1,"hh":7.0,"kuitu":2.4,"suola":0.1,"ryhmä":"Juurekset","fineli_id":246},
    "tomaatti":             {"kcal":18, "proteiini":0.9,"rasva":0.2,"hh":2.8,"kuitu":1.2,"suola":0.0,"ryhmä":"Hedelmävihannekset","fineli_id":280},
    "kurkku":               {"kcal":14, "proteiini":0.6,"rasva":0.1,"hh":2.2,"kuitu":0.6,"suola":0.0,"ryhmä":"Hedelmävihannekset","fineli_id":278},
    "paprika":              {"kcal":28, "proteiini":0.9,"rasva":0.2,"hh":5.0,"kuitu":1.7,"suola":0.0,"ryhmä":"Hedelmävihannekset","fineli_id":285},
    "pinaatti":             {"kcal":20, "proteiini":2.2,"rasva":0.4,"hh":1.5,"kuitu":2.2,"suola":0.1,"ryhmä":"Lehtivihannekset","fineli_id":296},
    "parsakaali":           {"kcal":25, "proteiini":3.0,"rasva":0.3,"hh":2.3,"kuitu":3.0,"suola":0.0,"ryhmä":"Kasvikset","fineli_id":256},
    "kaali":                {"kcal":24, "proteiini":1.3,"rasva":0.2,"hh":4.0,"kuitu":2.0,"suola":0.0,"ryhmä":"Kasvikset","fineli_id":255},
    "sipuli":               {"kcal":36, "proteiini":1.1,"rasva":0.1,"hh":7.5,"kuitu":1.5,"suola":0.0,"ryhmä":"Juurekset","fineli_id":241},
    "valkosipuli":          {"kcal":111,"proteiini":5.0,"rasva":0.2,"hh":22.0,"kuitu":2.1,"suola":0.0,"ryhmä":"Maustekasvit","fineli_id":242},
    "mansikka":             {"kcal":29, "proteiini":0.8,"rasva":0.3,"hh":5.3,"kuitu":2.0,"suola":0.0,"ryhmä":"Marjat","fineli_id":323},
    "mustikka":             {"kcal":37, "proteiini":0.5,"rasva":0.5,"hh":7.2,"kuitu":2.7,"suola":0.0,"ryhmä":"Marjat","fineli_id":328},
    "puolukka":             {"kcal":37, "proteiini":0.5,"rasva":0.5,"hh":7.1,"kuitu":3.8,"suola":0.0,"ryhmä":"Marjat","fineli_id":331},
    "omena":                {"kcal":50, "proteiini":0.3,"rasva":0.2,"hh":11.5,"kuitu":2.0,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":309},
    "banaani":              {"kcal":89, "proteiini":1.1,"rasva":0.3,"hh":20.5,"kuitu":2.6,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":305},
    "appelsiini":           {"kcal":43, "proteiini":0.9,"rasva":0.2,"hh":8.8,"kuitu":2.0,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":312},
    "avokado":              {"kcal":160,"proteiini":2.0,"rasva":15.0,"hh":2.0,"kuitu":6.7,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":304},
    "ruisleipä":            {"kcal":216,"proteiini":6.8,"rasva":1.8,"hh":43.0,"kuitu":9.3,"suola":1.1,"ryhmä":"Leivät","fineli_id":707},
    "vehnäleipä":           {"kcal":240,"proteiini":8.0,"rasva":2.0,"hh":47.0,"kuitu":2.8,"suola":1.2,"ryhmä":"Leivät","fineli_id":700},
    "kaura hiutale":        {"kcal":368,"proteiini":12.5,"rasva":7.0,"hh":61.0,"kuitu":9.0,"suola":0.0,"ryhmä":"Viljatuotteet","fineli_id":742},
    "pasta":                {"kcal":356,"proteiini":13.0,"rasva":1.5,"hh":71.0,"kuitu":3.5,"suola":0.0,"ryhmä":"Viljatuotteet","fineli_id":770},
    "riisi valkoinen":      {"kcal":356,"proteiini":7.0,"rasva":0.5,"hh":79.0,"kuitu":0.6,"suola":0.0,"ryhmä":"Viljatuotteet","fineli_id":762},
    "riisi täysjyvä":       {"kcal":349,"proteiini":7.5,"rasva":2.5,"hh":73.0,"kuitu":3.5,"suola":0.0,"ryhmä":"Viljatuotteet","fineli_id":763},
    "linssit kuiva":        {"kcal":299,"proteiini":23.0,"rasva":1.4,"hh":48.0,"kuitu":12.0,"suola":0.0,"ryhmä":"Palkokasvit","fineli_id":659},
    "kikherneet":           {"kcal":364,"proteiini":19.0,"rasva":6.0,"hh":61.0,"kuitu":17.0,"suola":0.0,"ryhmä":"Palkokasvit","fineli_id":657},
    "härkäpapu kuiva":      {"kcal":308,"proteiini":25.0,"rasva":1.5,"hh":48.0,"kuitu":8.5,"suola":0.0,"ryhmä":"Palkokasvit","fineli_id":653},
    "sokeriherne":          {"kcal":81, "proteiini":5.4,"rasva":0.4,"hh":14.0,"kuitu":5.0,"suola":0.0,"ryhmä":"Palkokasvit","fineli_id":663},
    "rypsiöljy":            {"kcal":828,"proteiini":0.0,"rasva":92.0,"hh":0.0,"kuitu":0.0,"suola":0.0,"ryhmä":"Rasvat","fineli_id":71},
    "oliiviöljy":           {"kcal":824,"proteiini":0.0,"rasva":91.0,"hh":0.0,"kuitu":0.0,"suola":0.0,"ryhmä":"Rasvat","fineli_id":74},
    "auringonkukansiemen":  {"kcal":584,"proteiini":20.0,"rasva":52.0,"hh":11.0,"kuitu":9.0,"suola":0.0,"ryhmä":"Siemenet","fineli_id":840},
    "pellavasiemen":        {"kcal":534,"proteiini":18.0,"rasva":42.0,"hh":18.0,"kuitu":28.0,"suola":0.0,"ryhmä":"Siemenet","fineli_id":842},
    "manteli":              {"kcal":575,"proteiini":21.0,"rasva":50.0,"hh":13.0,"kuitu":12.0,"suola":0.0,"ryhmä":"Pähkinät","fineli_id":826},
    "cashewpähkinä":        {"kcal":574,"proteiini":15.0,"rasva":46.0,"hh":30.0,"kuitu":3.3,"suola":0.0,"ryhmä":"Pähkinät","fineli_id":822},
    "tofu":                 {"kcal":76, "proteiini":8.0,"rasva":4.5,"hh":0.5,"kuitu":0.3,"suola":0.0,"ryhmä":"Kasviproteiinit","fineli_id":675},
    "nyhtökaura":           {"kcal":155,"proteiini":20.0,"rasva":4.5,"hh":8.5,"kuitu":5.0,"suola":0.3,"ryhmä":"Kasviproteiinit","fineli_id":5620},
    "härkis":               {"kcal":138,"proteiini":19.0,"rasva":3.5,"hh":7.5,"kuitu":5.5,"suola":0.4,"ryhmä":"Kasviproteiinit","fineli_id":5621},
}

def fineli_search(query: str) -> list:
    q = query.lower().strip()
    results = []
    for name, data in FINELI_DB.items():
        if q == name:
            results.insert(0, {"name": name, **data, "_score": 3})
        elif name.startswith(q):
            results.append({"name": name, **data, "_score": 2})
        elif q in name or any(q in word for word in name.split()):
            results.append({"name": name, **data, "_score": 1})
    results.sort(key=lambda x: -x["_score"])
    return results[:5]

def fineli_enrich(product: dict) -> dict | None:
    name = (product.get("product_name") or "").lower()
    best = None
    best_score = 0
    for fin_name, fin_data in FINELI_DB.items():
        score = sum(1 for w in fin_name.split() if w in name)
        if score > best_score:
            best_score = score
            best = {"name": fin_name, **fin_data}
    return best if best_score > 0 else None

def show_fineli_card(fin_data: dict):
    ryhmä = fin_data.get("ryhmä","")
    fin_name = fin_data.get("name","").title()
    fineli_id = fin_data.get("fineli_id","")
    st.markdown(f"""
<div style='background:#f0fff4;border:1.5px solid #1a5c2a;border-radius:10px;padding:16px 20px;margin:8px 0'>
<div style='display:flex;align-items:center;gap:8px;margin-bottom:12px'>
  <span style='font-size:1.3em'>🇫🇮</span>
  <b style='color:#0d3b18;font-size:1.05em'>Fineli-ravintotieto (THL)</b>
  <span style='background:#d4edda;color:#1a5c2a;border-radius:4px;padding:2px 8px;font-size:0.8em;margin-left:4px'>{ryhmä}</span>
</div>
""", unsafe_allow_html=True)
    cols = st.columns(6)
    nutrients = [
        ("🔥 Energia", f"{fin_data.get('kcal',0):.0f} kcal"),
        ("💪 Proteiini", f"{fin_data.get('proteiini',0):.1f} g"),
        ("🫙 Rasva", f"{fin_data.get('rasva',0):.1f} g"),
        ("🍞 Hiilihydr.", f"{fin_data.get('hh',0):.1f} g"),
        ("🌾 Kuitu", f"{fin_data.get('kuitu',0):.1f} g"),
        ("🧂 Suola", f"{fin_data.get('suola',0):.2f} g"),
    ]
    for col, (label, value) in zip(cols, nutrients):
        with col:
            st.markdown(f"""
<div style='text-align:center;background:white;border-radius:8px;padding:8px 4px;border:1px solid #d4edda'>
<div style='font-size:0.72em;color:#4a8c5c;margin-bottom:2px'>{label}</div>
<div style='font-size:1.05em;font-weight:700;color:#0d3b18'>{value}</div>
</div>""", unsafe_allow_html=True)
    url = f"https://fineli.fi/fineli/fi/elintarvikkeet/{fineli_id}"
    st.markdown(f"""<div style='margin-top:10px;font-size:0.8em;color:#555'>
Lähde: <a href='{url}' target='_blank' style='color:#1a5c2a;font-weight:600'>Fineli® THL – {fin_name}</a>
<span style='color:#888'> · Arvot per 100 g</span></div></div>""", unsafe_allow_html=True)


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

    # Fineli-täydennys
    fin = fineli_enrich(product)
    if fin:
        st.markdown("---")
        st.markdown("### 🍽️ Ravintosisältö (Fineli)")
        show_fineli_card(fin)

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
        "📈 Tilastot",
        "🇫🇮 Fineli-ravintohaku",
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
        en_hint = _translate_query(q)
        if en_hint.lower() != q.lower():
            st.caption(f"🔎 Haetaan suomenkielisellä sanalla + englanninkäännöksellä: **{en_hint}**")
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

# ── 7. FINELI-RAVINTOHAKU ─────────────────────────────────────────────────────
elif "Fineli" in page:
    st.title("🇫🇮 Fineli-ravintohaku")
    st.markdown("Hae suomalaisia elintarvikkeita **THL:n Fineli-tietokannasta** – tarkat ravintosisältötiedot välittömästi.")

    st.info("💡 Fineli-data täydentää automaattisesti myös tuotteiden tietosivut – kun haet esim. lohta Open Food Factsista, Fineli-ravintotiedot ilmestyvät tuotesivulle automaattisesti.")

    fin_q = st.text_input("🔍 Hae elintarviketta", placeholder="esim. lohi, kauramaito, ruisleipä, härkis, peruna...")

    if fin_q:
        hits = fineli_search(fin_q)
        if hits:
            st.success(f"Löytyi {len(hits)} osumaa")
            for hit in hits:
                with st.expander(f"🥦 **{hit['name'].title()}** – {hit['kcal']} kcal / 100 g · {hit.get('ryhmä','')}"):
                    show_fineli_card(hit)
        else:
            st.warning("Ei osumia. Kokeile lyhyempää hakusanaa – esim. 'lohi', 'maito', 'pasta', 'peruna'")

    st.markdown("---")
    st.markdown("### 📋 Kaikki tuotteet tietokannassa")

    ryhmät = sorted(set(v["ryhmä"] for v in FINELI_DB.values()))
    selected = st.selectbox("Suodata elintarvikeryhmän mukaan", ["Kaikki ryhmät"] + ryhmät)

    rows = []
    for name, d in FINELI_DB.items():
        if selected == "Kaikki ryhmät" or d["ryhmä"] == selected:
            rows.append({
                "Tuote": name.title(),
                "Ryhmä": d["ryhmä"],
                "Energia (kcal)": d["kcal"],
                "Proteiini (g)": d["proteiini"],
                "Rasva (g)": d["rasva"],
                "Hiilihydr. (g)": d["hh"],
                "Kuitu (g)": d["kuitu"],
                "Suola (g)": d["suola"],
            })

    if rows:
        df_fin = pd.DataFrame(rows).sort_values("Tuote").reset_index(drop=True)
        st.dataframe(df_fin, use_container_width=True, hide_index=True)
        st.caption(f"Yhteensä {len(rows)} elintarviketta · Lähde: Fineli® THL · Kaikki arvot per 100 g")

    st.markdown("---")
    st.markdown("### 🔗 Fineli-tietokanta verkossa")
    st.markdown("Haluatko nähdä täydellisen Fineli-tietokannan? THL ylläpitää yli 4000 elintarvikkeen tietokantaa:")
    st.link_button("🌐 Avaa Fineli.fi (THL)", "https://fineli.fi/fineli/fi/index")

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
