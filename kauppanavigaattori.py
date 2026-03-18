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
HISTORY_FILE   = "ostohistoria.json"
SHOPPING_FILE  = "ostoslista.json"
WASTE_FILE     = "kaappitavarat.json"
MEALPLAN_FILE  = "ateriasuunnitelma.json"
POINTS_FILE    = "kestävyyspisteet.json"
EXPIRY_FILE    = "kaappitavarat_pvm.json"

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

for key, file in [
    ("history",  HISTORY_FILE),
    ("shopping", SHOPPING_FILE),
    ("waste",    WASTE_FILE),
    ("mealplan", MEALPLAN_FILE),
    ("points",   POINTS_FILE),
    ("expiry",   EXPIRY_FILE),
]:
    if key not in st.session_state:
        st.session_state[key] = load_json(file)

# Pisteet: varmista perusrakenne
if not isinstance(st.session_state.points, dict):
    st.session_state.points = {}
st.session_state.points.setdefault("total", 0)
st.session_state.points.setdefault("streak", 0)
st.session_state.points.setdefault("log", [])
st.session_state.points.setdefault("badges", [])

# ── OPEN FOOD FACTS API ───────────────────────────────────────────────────────
import time

OFF   = "https://world.openfoodfacts.org"
# Käytetään vain välttämättömät kentät – vähemmän dataa = nopeampi vastaus
FIELDS_SEARCH = "code,product_name,brands,nutrition_grades,ecoscore_grade,ecoscore_score,nova_group,image_front_small_url,categories_tags,countries_tags,labels_tags"
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

NORDIC_COUNTRIES = {"en:finland","en:sweden","en:norway","en:denmark","en:estonia",
                    "fi:suomi","fi:finland","se:sverige","sv:sweden"}

def _score_product(product: dict, query: str) -> int:
    """Pisteytysfunktio tulosten järjestämiseen – pohjoismaiset ja relevantit ensin."""
    score = 0
    name  = (product.get("product_name") or "").lower()
    brand = (product.get("brands") or "").lower()
    cats  = " ".join(product.get("categories_tags") or []).lower()
    ctags = set(product.get("countries_tags") or [])
    ltags = set(product.get("labels_tags") or [])

    q_words = [w for w in query.lower().split() if len(w) > 2]
    for w in q_words:
        if w in name:  score += 10
        elif w in brand: score += 5
        elif w in cats:  score += 2

    if ctags & NORDIC_COUNTRIES:
        score += 15
    finnish_labels = {"en:organic","fi:luomu","fi:hyvaa-suomesta","fi:avainlippu","en:finnish-heart-symbol"}
    if ltags & finnish_labels:
        score += 8
    if name and not any(c.isascii() for c in name[:10]):
        score -= 5
    return score

def _is_relevant(product: dict, query: str) -> bool:
    return _score_product(product, query) > 0

@st.cache_data(ttl=600, show_spinner=False)
def search_products(query: str) -> list:
    """
    Hakee VAIN suomalaisia ja pohjoismaisia tuotteita.
    1. Yrittää ensin hakea Suomi-filtterillä + englanninkäännöksellä
    2. Jos alle 2 tulosta, yrittää pohjoismaisella filtterillä
    3. Jos edelleen tyhjä, yrittää ilman filtteriä mutta suodattaa
       tiukasti vain pohjoismaiset tulokset
    """
    en_query = _translate_query(query)
    use_en = en_query.lower() != query.lower()
    search_term = en_query if use_en else query

    def fetch_with_country(term, country_tag, page_size=24):
        """Haku country-tagilla OFF:n tagihaku-API:lla."""
        data = _fetch(f"{OFF}/cgi/search.pl", {
            "search_terms": term,
            "tagtype_0": "countries",
            "tag_contains_0": "contains",
            "tag_0": country_tag,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": page_size,
            "fields": FIELDS_SEARCH,
            "sort_by": "unique_scans_n",
        })
        return (data or {}).get("products", [])

    results = []

    # Vaihe 1: Hae suomalaiset tuotteet englanninkäännöksellä
    results = fetch_with_country(search_term, "finland")

    # Vaihe 2: Jos ei tuloksia, kokeile alkuperäisellä hakusanalla
    if len(results) < 2 and use_en:
        r2 = fetch_with_country(query, "finland")
        codes = {p.get("code") for p in results}
        results += [p for p in r2 if p.get("code") not in codes]

    # Vaihe 3: Laajenna pohjoismaisiin (Ruotsi, Norja, Tanska, Viro)
    if len(results) < 2:
        for country in ["sweden", "norway", "denmark", "estonia"]:
            r_nordic = fetch_with_country(search_term, country)
            codes = {p.get("code") for p in results}
            results += [p for p in r_nordic if p.get("code") not in codes]
            if len(results) >= 4:
                break

    # Vaihe 4: Viimeinen vaihtoehto – hae ilman filtteriä mutta
    # suodata tiukasti: pidä VAIN pohjoismaiset tai nimetyt tuotteet
    if len(results) < 2:
        data = _fetch(f"{OFF}/cgi/search.pl", {
            "search_terms": search_term,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 50,
            "fields": FIELDS_SEARCH,
            "sort_by": "unique_scans_n",
        })
        all_results = (data or {}).get("products", [])
        codes = {p.get("code") for p in results}
        for p in all_results:
            if p.get("code") in codes:
                continue
            ctags = set(p.get("countries_tags") or [])
            if ctags & NORDIC_COUNTRIES:
                results.append(p)

    # Poista tuotteet ilman nimeä ja järjestä pistemäärän mukaan
    results = [p for p in results if p.get("product_name")]
    results.sort(key=lambda p: _score_product(p, search_term), reverse=True)
    return results[:20]

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
    # ── LISÄÄ TUOTTEET ──────────────────────────────────────────────────────────
    # Kalatuotteet
    "hauki":                {"kcal":83, "proteiini":18.0,"rasva":0.5,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Kala","fineli_id":505},
    "ahven":                {"kcal":82, "proteiini":18.5,"rasva":0.5,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Kala","fineli_id":501},
    "kirjolohi":            {"kcal":168,"proteiini":20.0,"rasva":9.5,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Kala","fineli_id":509},
    "sei":                  {"kcal":72, "proteiini":16.0,"rasva":0.5,"hh":0.0,"kuitu":0.0,"suola":0.2,"ryhmä":"Kala","fineli_id":512},
    "turska":               {"kcal":76, "proteiini":17.5,"rasva":0.5,"hh":0.0,"kuitu":0.0,"suola":0.2,"ryhmä":"Kala","fineli_id":513},
    "seitifile":            {"kcal":72, "proteiini":16.0,"rasva":0.5,"hh":0.0,"kuitu":0.0,"suola":0.2,"ryhmä":"Kala","fineli_id":512},
    "savulohi":             {"kcal":185,"proteiini":23.0,"rasva":10.0,"hh":0.0,"kuitu":0.0,"suola":2.5,"ryhmä":"Kala","fineli_id":520},
    "sardiini":             {"kcal":208,"proteiini":25.0,"rasva":11.0,"hh":0.0,"kuitu":0.0,"suola":1.5,"ryhmä":"Kala","fineli_id":518},
    "makrilli":             {"kcal":205,"proteiini":19.0,"rasva":14.0,"hh":0.0,"kuitu":0.0,"suola":0.2,"ryhmä":"Kala","fineli_id":515},
    "katkarapu":            {"kcal":71, "proteiini":15.5,"rasva":0.5,"hh":0.0,"kuitu":0.0,"suola":1.5,"ryhmä":"Kala","fineli_id":540},
    # Liha lisää
    "porsaan ulkofilee":    {"kcal":121,"proteiini":22.0,"rasva":3.5,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Liha","fineli_id":400},
    "naudan entrecote":     {"kcal":218,"proteiini":19.0,"rasva":15.5,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Liha","fineli_id":390},
    "lammas":               {"kcal":235,"proteiini":17.0,"rasva":18.0,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Liha","fineli_id":410},
    "poro":                 {"kcal":119,"proteiini":22.0,"rasva":3.0,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Riista","fineli_id":443},
    "hirvi":                {"kcal":115,"proteiini":22.0,"rasva":2.5,"hh":0.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Riista","fineli_id":442},
    "siipikarjan maksa":    {"kcal":119,"proteiini":19.0,"rasva":4.5,"hh":1.5,"kuitu":0.0,"suola":0.2,"ryhmä":"Siipikarja","fineli_id":430},
    "kinkku keitetty":      {"kcal":105,"proteiini":17.0,"rasva":3.5,"hh":1.0,"kuitu":0.0,"suola":1.5,"ryhmä":"Lihavalmisteet","fineli_id":460},
    "meetvursti":           {"kcal":415,"proteiini":18.0,"rasva":37.0,"hh":1.5,"kuitu":0.0,"suola":2.5,"ryhmä":"Lihavalmisteet","fineli_id":464},
    "makkara lenkki":       {"kcal":280,"proteiini":11.0,"rasva":25.0,"hh":3.5,"kuitu":0.0,"suola":1.8,"ryhmä":"Lihavalmisteet","fineli_id":462},
    # Maitotuotteet lisää
    "kreikkalainen jogurtti":{"kcal":97,"proteiini":9.0,"rasva":5.0,"hh":4.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":135},
    "kvark":                {"kcal":65, "proteiini":11.0,"rasva":0.2,"hh":4.5,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":178},
    "maitorahka":           {"kcal":72, "proteiini":12.0,"rasva":0.5,"hh":4.5,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":176},
    "piimä":                {"kcal":35, "proteiini":3.3,"rasva":0.5,"hh":3.8,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":146},
    "ruokakerma":           {"kcal":197,"proteiini":2.5,"rasva":20.0,"hh":3.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":156},
    "vispikerma":           {"kcal":345,"proteiini":2.2,"rasva":36.0,"hh":2.8,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":157},
    "kahvikerma":           {"kcal":197,"proteiini":2.5,"rasva":20.0,"hh":3.0,"kuitu":0.0,"suola":0.1,"ryhmä":"Maitotalous","fineli_id":156},
    "cheddar":              {"kcal":403,"proteiini":25.0,"rasva":33.0,"hh":0.5,"kuitu":0.0,"suola":1.8,"ryhmä":"Juustot","fineli_id":162},
    "mozzarella":           {"kcal":253,"proteiini":18.0,"rasva":20.0,"hh":0.5,"kuitu":0.0,"suola":0.6,"ryhmä":"Juustot","fineli_id":166},
    "feta":                 {"kcal":264,"proteiini":14.0,"rasva":22.0,"hh":1.0,"kuitu":0.0,"suola":2.7,"ryhmä":"Juustot","fineli_id":163},
    "kermajuusto":          {"kcal":342,"proteiini":7.0,"rasva":34.0,"hh":3.0,"kuitu":0.0,"suola":0.9,"ryhmä":"Juustot","fineli_id":170},
    "sinihomejuusto":       {"kcal":353,"proteiini":21.0,"rasva":29.0,"hh":1.0,"kuitu":0.0,"suola":2.5,"ryhmä":"Juustot","fineli_id":168},
    # Vilja lisää
    "ohraryynit":           {"kcal":354,"proteiini":10.0,"rasva":2.0,"hh":75.0,"kuitu":10.0,"suola":0.0,"ryhmä":"Viljatuotteet","fineli_id":750},
    "ruisrouhe":            {"kcal":318,"proteiini":9.5,"rasva":2.5,"hh":62.0,"kuitu":16.0,"suola":0.0,"ryhmä":"Viljatuotteet","fineli_id":745},
    "vehnäjauho":           {"kcal":348,"proteiini":10.0,"rasva":1.5,"hh":74.0,"kuitu":2.7,"suola":0.0,"ryhmä":"Viljatuotteet","fineli_id":780},
    "ruisjauho":            {"kcal":325,"proteiini":9.0,"rasva":1.5,"hh":68.0,"kuitu":13.0,"suola":0.0,"ryhmä":"Viljatuotteet","fineli_id":782},
    "täysjyvävehnä":        {"kcal":320,"proteiini":10.5,"rasva":2.0,"hh":64.0,"kuitu":10.0,"suola":0.0,"ryhmä":"Viljatuotteet","fineli_id":783},
    "spelttijauho":         {"kcal":338,"proteiini":12.0,"rasva":2.5,"hh":68.0,"kuitu":8.0,"suola":0.0,"ryhmä":"Viljatuotteet","fineli_id":784},
    "näkkileipä":           {"kcal":359,"proteiini":9.0,"rasva":2.0,"hh":76.0,"kuitu":10.0,"suola":1.3,"ryhmä":"Leivät","fineli_id":710},
    "hapankorppu":          {"kcal":350,"proteiini":9.0,"rasva":2.0,"hh":74.0,"kuitu":8.5,"suola":1.1,"ryhmä":"Leivät","fineli_id":712},
    "puuroseos":            {"kcal":350,"proteiini":10.0,"rasva":5.0,"hh":65.0,"kuitu":8.0,"suola":0.5,"ryhmä":"Viljatuotteet","fineli_id":748},
    "mysli":                {"kcal":390,"proteiini":9.0,"rasva":7.0,"hh":73.0,"kuitu":7.0,"suola":0.3,"ryhmä":"Viljatuotteet","fineli_id":749},
    "granola":              {"kcal":450,"proteiini":9.0,"rasva":17.0,"hh":65.0,"kuitu":5.0,"suola":0.3,"ryhmä":"Viljatuotteet","fineli_id":749},
    # Kasvikset lisää
    "fenkolit":             {"kcal":29, "proteiini":1.2,"rasva":0.2,"hh":5.0,"kuitu":2.7,"suola":0.1,"ryhmä":"Kasvikset","fineli_id":263},
    "parsa":                {"kcal":22, "proteiini":2.5,"rasva":0.2,"hh":2.0,"kuitu":2.1,"suola":0.0,"ryhmä":"Kasvikset","fineli_id":252},
    "artisokka":            {"kcal":40, "proteiini":2.5,"rasva":0.2,"hh":7.0,"kuitu":5.0,"suola":0.1,"ryhmä":"Kasvikset","fineli_id":251},
    "lehtikaali":           {"kcal":37, "proteiini":3.0,"rasva":0.5,"hh":5.0,"kuitu":3.6,"suola":0.1,"ryhmä":"Lehtivihannekset","fineli_id":297},
    "ruusukaali":           {"kcal":36, "proteiini":3.5,"rasva":0.3,"hh":4.5,"kuitu":4.1,"suola":0.0,"ryhmä":"Kasvikset","fineli_id":258},
    "maissi":               {"kcal":86, "proteiini":3.2,"rasva":1.2,"hh":17.0,"kuitu":2.4,"suola":0.0,"ryhmä":"Kasvikset","fineli_id":270},
    "herneet":              {"kcal":74, "proteiini":5.5,"rasva":0.4,"hh":12.5,"kuitu":5.0,"suola":0.0,"ryhmä":"Palkokasvit","fineli_id":663},
    "pavut valkoiset":      {"kcal":127,"proteiini":8.5,"rasva":0.5,"hh":23.0,"kuitu":7.5,"suola":0.0,"ryhmä":"Palkokasvit","fineli_id":654},
    "pavut mustat":         {"kcal":341,"proteiini":21.5,"rasva":1.4,"hh":62.0,"kuitu":15.0,"suola":0.0,"ryhmä":"Palkokasvit","fineli_id":655},
    "sokeriherne pakastettu":{"kcal":74,"proteiini":5.5,"rasva":0.4,"hh":12.5,"kuitu":5.0,"suola":0.0,"ryhmä":"Palkokasvit","fineli_id":663},
    # Hedelmät lisää
    "mango":                {"kcal":60, "proteiini":0.8,"rasva":0.4,"hh":13.5,"kuitu":1.6,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":318},
    "ananasa":              {"kcal":48, "proteiini":0.5,"rasva":0.1,"hh":11.5,"kuitu":1.4,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":301},
    "kivi":                 {"kcal":61, "proteiini":1.1,"rasva":0.5,"hh":13.0,"kuitu":3.0,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":310},
    "sitruuna":             {"kcal":29, "proteiini":1.1,"rasva":0.3,"hh":5.0,"kuitu":2.8,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":313},
    "lime":                 {"kcal":30, "proteiini":0.7,"rasva":0.2,"hh":6.5,"kuitu":2.8,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":314},
    "greiippi":             {"kcal":32, "proteiini":0.8,"rasva":0.1,"hh":7.0,"kuitu":1.6,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":315},
    "vesimeloni":           {"kcal":30, "proteiini":0.6,"rasva":0.2,"hh":6.4,"kuitu":0.4,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":326},
    "viinirypäleet":        {"kcal":67, "proteiini":0.6,"rasva":0.2,"hh":16.0,"kuitu":0.9,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":308},
    "luumu":                {"kcal":46, "proteiini":0.7,"rasva":0.1,"hh":10.5,"kuitu":1.4,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":320},
    "kirsikka":             {"kcal":50, "proteiini":1.0,"rasva":0.3,"hh":10.0,"kuitu":1.6,"suola":0.0,"ryhmä":"Hedelmät","fineli_id":306},
    "karpalo":              {"kcal":29, "proteiini":0.4,"rasva":0.1,"hh":6.3,"kuitu":4.6,"suola":0.0,"ryhmä":"Marjat","fineli_id":329},
    "tyrni":                {"kcal":82, "proteiini":1.2,"rasva":3.5,"hh":9.5,"kuitu":3.0,"suola":0.0,"ryhmä":"Marjat","fineli_id":334},
    "herukat punaiset":     {"kcal":36, "proteiini":1.0,"rasva":0.2,"hh":7.0,"kuitu":4.3,"suola":0.0,"ryhmä":"Marjat","fineli_id":332},
    "mustaherukat":         {"kcal":56, "proteiini":1.3,"rasva":0.4,"hh":11.0,"kuitu":6.8,"suola":0.0,"ryhmä":"Marjat","fineli_id":330},
    # Pähkinät ja siemenet lisää
    "saksanpähkinä":        {"kcal":654,"proteiini":15.0,"rasva":65.0,"hh":7.0,"kuitu":6.7,"suola":0.0,"ryhmä":"Pähkinät","fineli_id":824},
    "pistaasi":             {"kcal":562,"proteiini":20.0,"rasva":45.0,"hh":21.0,"kuitu":10.3,"suola":0.0,"ryhmä":"Pähkinät","fineli_id":827},
    "hasselpähkinä":        {"kcal":628,"proteiini":15.0,"rasva":61.0,"hh":7.0,"kuitu":9.7,"suola":0.0,"ryhmä":"Pähkinät","fineli_id":823},
    "maapähkinä":           {"kcal":567,"proteiini":26.0,"rasva":49.0,"hh":9.0,"kuitu":8.5,"suola":0.0,"ryhmä":"Pähkinät","fineli_id":825},
    "chiasiemen":           {"kcal":486,"proteiini":17.0,"rasva":31.0,"hh":42.0,"kuitu":34.0,"suola":0.0,"ryhmä":"Siemenet","fineli_id":843},
    "hampunsiemen":         {"kcal":553,"proteiini":32.0,"rasva":49.0,"hh":9.0,"kuitu":4.0,"suola":0.0,"ryhmä":"Siemenet","fineli_id":844},
    "seesaminsiemen":       {"kcal":573,"proteiini":18.0,"rasva":50.0,"hh":12.0,"kuitu":11.8,"suola":0.0,"ryhmä":"Siemenet","fineli_id":841},
    "kurpitsansiemen":      {"kcal":559,"proteiini":30.0,"rasva":49.0,"hh":6.0,"kuitu":6.0,"suola":0.0,"ryhmä":"Siemenet","fineli_id":845},
    # Muut
    "hunaja":               {"kcal":304,"proteiini":0.3,"rasva":0.0,"hh":83.0,"kuitu":0.0,"suola":0.0,"ryhmä":"Makeutusaineet","fineli_id":900},
    "vaahterasirappi":      {"kcal":260,"proteiini":0.1,"rasva":0.1,"hh":67.0,"kuitu":0.0,"suola":0.0,"ryhmä":"Makeutusaineet","fineli_id":901},
    "sokeri":               {"kcal":399,"proteiini":0.0,"rasva":0.0,"hh":99.7,"kuitu":0.0,"suola":0.0,"ryhmä":"Makeutusaineet","fineli_id":902},
    "kookossokeri":         {"kcal":375,"proteiini":0.5,"rasva":0.2,"hh":93.0,"kuitu":0.0,"suola":0.0,"ryhmä":"Makeutusaineet","fineli_id":903},
    "tummasuklaa":          {"kcal":546,"proteiini":5.0,"rasva":32.0,"hh":62.0,"kuitu":8.0,"suola":0.1,"ryhmä":"Makeiset","fineli_id":920},
    "maitosuklaa":          {"kcal":535,"proteiini":7.0,"rasva":30.0,"hh":60.0,"kuitu":2.0,"suola":0.2,"ryhmä":"Makeiset","fineli_id":921},
    "kahvi jauhettu":       {"kcal":2,  "proteiini":0.2,"rasva":0.1,"hh":0.2,"kuitu":0.0,"suola":0.0,"ryhmä":"Juomat","fineli_id":950},
    "musta tee":            {"kcal":1,  "proteiini":0.1,"rasva":0.0,"hh":0.2,"kuitu":0.0,"suola":0.0,"ryhmä":"Juomat","fineli_id":955},
    "appelsiinimehu":       {"kcal":44, "proteiini":0.7,"rasva":0.2,"hh":10.0,"kuitu":0.2,"suola":0.0,"ryhmä":"Juomat","fineli_id":960},
    "riisimaito":           {"kcal":48, "proteiini":0.3,"rasva":1.0,"hh":9.5,"kuitu":0.2,"suola":0.1,"ryhmä":"Kasvipohjaiset","fineli_id":5603},
    "kookosmaito":          {"kcal":197,"proteiini":2.0,"rasva":21.0,"hh":2.5,"kuitu":0.0,"suola":0.0,"ryhmä":"Kasvipohjaiset","fineli_id":5605},
    "mantelimaito":         {"kcal":24, "proteiini":0.5,"rasva":1.5,"hh":2.0,"kuitu":0.3,"suola":0.1,"ryhmä":"Kasvipohjaiset","fineli_id":5604},
    "tempeh":               {"kcal":193,"proteiini":19.0,"rasva":11.0,"hh":7.5,"kuitu":4.5,"suola":0.0,"ryhmä":"Kasviproteiinit","fineli_id":676},
    "seitan":               {"kcal":149,"proteiini":25.0,"rasva":2.0,"hh":7.0,"kuitu":0.6,"suola":0.5,"ryhmä":"Kasviproteiinit","fineli_id":677},
    "soijarouhee":          {"kcal":330,"proteiini":45.0,"rasva":1.0,"hh":30.0,"kuitu":15.0,"suola":0.0,"ryhmä":"Kasviproteiinit","fineli_id":678},
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



# ── KESTÄVYYSPISTEJÄRJESTELMÄ ─────────────────────────────────────────────────
BADGE_DEFS = [
    (10,  "🌱 Vihreä aloittaja",       "10 pistettä kerätty!"),
    (50,  "🌿 Kestävä ostaja",         "50 pistettä – hienoa!"),
    (100, "🏆 Ekosankari",             "100 pistettä – olet huipulla!"),
    (200, "🌍 Planeetan puolustaja",   "200 pistettä – legendaarinen!"),
    (5,   "🔥 5 putki",                "5 peräkkäistä eco A/B-valintaa!"),
    (10,  "💎 10 putki",               "10 peräkkäistä eco A/B-valintaa!"),
]

def add_points(reason: str, pts: int, eco_grade: str = ""):
    """Lisää pisteitä ja tarkistaa uudet saavutukset."""
    p = st.session_state.points
    p["total"] = p.get("total", 0) + pts
    # Putki: eco A tai B
    if eco_grade.lower() in ["a", "b"]:
        p["streak"] = p.get("streak", 0) + 1
    else:
        p["streak"] = 0
    # Logi
    from datetime import datetime
    p["log"].append({"reason": reason, "pts": pts, "date": datetime.now().strftime("%d.%m.%Y")})
    # Badget
    total = p["total"]
    streak = p["streak"]
    earned = p.get("badges", [])
    new_badges = []
    if total >= 200 and "🌍 Planeetan puolustaja" not in earned:
        new_badges.append("🌍 Planeetan puolustaja")
    elif total >= 100 and "🏆 Ekosankari" not in earned:
        new_badges.append("🏆 Ekosankari")
    elif total >= 50 and "🌿 Kestävä ostaja" not in earned:
        new_badges.append("🌿 Kestävä ostaja")
    elif total >= 10 and "🌱 Vihreä aloittaja" not in earned:
        new_badges.append("🌱 Vihreä aloittaja")
    if streak >= 10 and "💎 10 putki" not in earned:
        new_badges.append("💎 10 putki")
    elif streak >= 5 and "🔥 5 putki" not in earned:
        new_badges.append("🔥 5 putki")
    for b in new_badges:
        earned.append(b)
        st.toast(f"🎉 Uusi saavutus: {b}", icon="🏅")
    p["badges"] = earned
    save_json(POINTS_FILE, p)

# ── PAKKAUKSEN ARVIOINTI ──────────────────────────────────────────────────────
def score_packaging(packagings: list) -> tuple[str, str]:
    """Palauttaa (arvosana, selitys) pakkauksen perusteella."""
    if not packagings:
        return "?", "Pakkaustietoa ei saatavilla"
    materials = []
    for pkg in packagings:
        m = (pkg.get("material", {}).get("id") or "").lower()
        if m:
            materials.append(m)
    mat_str = " ".join(materials)
    if not mat_str:
        return "?", "Pakkaustietoa ei saatavilla"
    if "glass" in mat_str or "lasi" in mat_str:
        return "A", "🟢 Lasi – kierrätettävä ja uudelleenkäytettävä"
    if "cardboard" in mat_str or "paper" in mat_str or "kartonki" in mat_str:
        return "B", "🟡 Kartonki/paperi – hyvä valinta"
    if "metal" in mat_str or "aluminium" in mat_str or "steel" in mat_str:
        return "B", "🟡 Metalli/alumiini – kierrätettävä"
    if "plastic" in mat_str or "muovi" in mat_str:
        if "recycled" in mat_str or "kierrätetty" in mat_str:
            return "C", "🟠 Kierrätetty muovi – parempi kuin neitseellinen"
        return "D", "🔴 Muovi – harkitse lasivaihtoehtoa"
    return "C", "🟠 Sekamateriaali"

# ── ALKUPERÄMAA ───────────────────────────────────────────────────────────────
COUNTRY_FLAGS = {
    "en:finland": "🇫🇮 Suomi", "en:sweden": "🇸🇪 Ruotsi",
    "en:norway": "🇳🇴 Norja", "en:denmark": "🇩🇰 Tanska",
    "en:germany": "🇩🇪 Saksa", "en:france": "🇫🇷 Ranska",
    "en:italy": "🇮🇹 Italia", "en:spain": "🇪🇸 Espanja",
    "en:netherlands": "🇳🇱 Alankomaat", "en:united-kingdom": "🇬🇧 Britannia",
    "en:united-states": "🇺🇸 USA", "en:poland": "🇵🇱 Puola",
    "en:estonia": "🇪🇪 Viro", "en:latvia": "🇱🇻 Latvia",
    "en:lithuania": "🇱🇹 Liettua", "en:belgium": "🇧🇪 Belgia",
    "en:austria": "🇦🇹 Itävalta", "en:switzerland": "🇨🇭 Sveitsi",
}

def get_origin(countries_tags: list) -> str:
    if not countries_tags:
        return "🌐 Alkuperä tuntematon"
    for tag in countries_tags:
        if tag in COUNTRY_FLAGS:
            return COUNTRY_FLAGS[tag]
    return f"🌐 {countries_tags[0].replace('en:','').title()}"

def origin_color(countries_tags: list) -> str:
    tags = set(countries_tags or [])
    if "en:finland" in tags:
        return "#d4edda"
    if tags & {"en:sweden","en:norway","en:denmark","en:estonia"}:
        return "#e8f4fd"
    return "#fff8e1"

# ── CO₂-LASKIN OSTOSKORILLE ───────────────────────────────────────────────────
# kg CO₂ per kg tuotetta (arviot)
CO2_BY_CATEGORY = {
    "beef": 27.0, "lamb": 39.0, "pork": 12.0, "chicken": 6.9,
    "turkey": 10.9, "fish": 6.1, "salmon": 11.9,
    "milk": 3.2, "cheese": 13.5, "butter": 23.8, "yogurt": 2.2,
    "eggs": 4.8, "tofu": 3.0, "nuts": 2.3, "legumes": 0.9,
    "rice": 4.0, "pasta": 1.7, "bread": 1.1, "oats": 1.5,
    "vegetables": 0.4, "fruits": 0.5, "potatoes": 0.3,
    "oil": 6.0, "sugar": 1.5, "chocolate": 19.0, "coffee": 28.5,
}

def estimate_co2(product: dict, weight_g: float = 100) -> float:
    """Arvioi tuotteen CO₂ per annettu paino grammoissa."""
    # Käytä ensin OFF:n omaa dataa
    known = product.get("carbon_footprint_from_known_ingredients_100g")
    if known:
        return float(known) * weight_g / 100
    # Arvioi kategorian perusteella
    cats = " ".join(product.get("categories_tags") or []).lower()
    for cat, co2 in CO2_BY_CATEGORY.items():
        if cat in cats:
            return co2 * weight_g / 100 / 10  # kg→g, per 100g
    return 1.5 * weight_g / 100  # oletusarvo

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

    # Alkuperämaa
    ctags = product.get("countries_tags") or []
    if ctags:
        origin = get_origin(ctags)
        bg = origin_color(ctags)
        st.markdown(f"""<div style='background:{bg};border-radius:8px;padding:10px 16px;margin:8px 0;display:inline-block'>
<span style='font-size:1.05em'>🌐 <b>Alkuperämaa:</b> {origin}</span></div>""", unsafe_allow_html=True)

    # Pakkauksen arviointi
    packagings = product.get("packagings") or []
    if packagings:
        pkg_grade, pkg_text = score_packaging(packagings)
        pkg_colors = {"A":"#d4edda","B":"#fff3cd","C":"#ffe0b2","D":"#f8d7da","?":"#f0f0f0"}
        st.markdown(f"""<div style='background:{pkg_colors.get(pkg_grade,"#f0f0f0")};border-radius:8px;padding:10px 16px;margin:8px 0'>
<b>📦 Pakkauksen arvosana: {pkg_grade}</b> – {pkg_text}</div>""", unsafe_allow_html=True)

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
                "date": datetime.now().strftime("%Y-%m-%d"),
                "countries_tags": product.get("countries_tags", []),
            }
            st.session_state.shopping.append(item)
            save_json(SHOPPING_FILE, st.session_state.shopping)
            # ── Kestävyyspisteet ──────────────────────────────────────────────
            _eco = str(eco).lower()
            _nova = nova
            _cats = " ".join(product.get("categories_tags") or []).lower()
            _ctags = set(product.get("countries_tags") or [])
            pts = 0; reasons = []
            if _eco in ["a","b"]:
                pts += 3; reasons.append(f"Eco {_eco.upper()}")
            if any(k in _cats for k in ["plant","vegan","vegetable","legume","fruit","oat","soy","berry"]):
                pts += 2; reasons.append("kasvistuote")
            if _nova and str(_nova) in ["1","2"]:
                pts += 1; reasons.append(f"NOVA {_nova}")
            if "en:finland" in _ctags:
                pts += 2; reasons.append("kotimainen 🇫🇮")
            if pts > 0:
                add_points(", ".join(reasons), pts, _eco)
                st.toast(f"🌱 +{pts} pistettä! ({', '.join(reasons)})", icon="🏆")
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
    ctags = set(p.get("countries_tags") or [])
    country_flag = "🇫🇮 " if ctags & NORDIC_COUNTRIES else ""

    with st.container():
        st.markdown("<div class='product-card'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 4, 1])
        with c1:
            if img:
                st.image(img, width=65)
        with c2:
            origin_txt = get_origin(p.get("countries_tags") or [])
            st.markdown(f"{country_flag}**{name}**")
            if brand:
                st.caption(f"{brand} · {origin_txt}")
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
        "🗓️ Ateriasuunnittelija",
        "🏆 Kestävyyspisteet",
        "🔔 Parasta ennen",
        "📈 Tilastot",
        "🇫🇮 Fineli-ravintohaku",
        "ℹ️ Tietoa pisteytyksistä"
    ], label_visibility="collapsed")
    st.markdown("---")
    # Pistewidget sivupalkissa
    _pts = st.session_state.points.get("total", 0)
    _streak = st.session_state.points.get("streak", 0)
    _badges = st.session_state.points.get("badges", [])
    st.markdown(f"""<div style='background:#d4edda;border-radius:8px;padding:8px 12px;text-align:center'>
<div style='font-weight:700;color:#1a5c2a'>🏆 {_pts} pistettä</div>
{"<div style='font-size:0.8em;color:#4a8c5c'>🔥 " + str(_streak) + " putki</div>" if _streak > 1 else ""}
{"<div style='font-size:0.75em'>" + " ".join(_badges[-2:]) + "</div>" if _badges else ""}
</div>""", unsafe_allow_html=True)
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
            st.caption(f"🔎 Haetaan: **{en_hint}** · Näytetään vain suomalaiset ja pohjoismaiset tuotteet 🇫🇮")
        else:
            st.caption("🇫🇮 Näytetään vain suomalaiset ja pohjoismaiset tuotteet")
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
            st.warning("Ei suomalaisia/pohjoismaisia tuloksia. Tätä tuotetta ei löydy Open Food Facts -tietokannasta Suomesta. Kokeile viivakoodiskannausta tai englanninkielistä nimeä (esim. 'salmon', 'oat milk').")
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
        # CO₂-yhteenveto
        total_co2 = sum(float(item.get("carbon") or 0) * int(item.get("qty",1)) for item in st.session_state.shopping)
        total_price = sum(float(item.get("price") or 0) * int(item.get("qty",1)) for item in st.session_state.shopping)
        km_eq = round(total_co2 / 0.21, 1) if total_co2 > 0 else 0
        eco_good = sum(1 for i in st.session_state.shopping if str(i.get("eco","")).lower() in ["a","b"])
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            st.metric("🌍 CO₂ yhteensä", f"{total_co2:.0f} g")
            if km_eq > 0:
                st.caption(f"≈ {km_eq} km autolla")
        with mc2:
            st.metric("💶 Hinta yhteensä", f"{total_price:.2f} €")
        with mc3:
            st.metric("🌿 Eco A/B tuotteet", f"{eco_good}/{len(st.session_state.shopping)}")
        with mc4:
            st.metric("🏆 Pisteet", st.session_state.points.get("total",0))
        st.markdown("---")
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


# ── 8. ATERIASUUNNITTELIJA ────────────────────────────────────────────────────
elif "Ateriasuunnittelija" in page:
    st.title("🗓️ Ateriasuunnittelija")
    st.markdown("Suunnittele viikon ateriat etukäteen – sovellus laskee automaattisesti hiilijalanjäljen, ravitsemuksen ja budjetin.")

    DAYS = ["Maanantai","Tiistai","Keskiviikko","Torstai","Perjantai","Lauantai","Sunnuntai"]
    MEALS = ["Aamupala","Lounas","Päivällinen","Välipala"]

    if not isinstance(st.session_state.mealplan, dict):
        st.session_state.mealplan = {}

    # Päivän valinta
    sel_day = st.selectbox("Valitse päivä", DAYS)
    sel_meal = st.selectbox("Ateria", MEALS)

    # Hae tuote lisättäväksi
    st.markdown("#### ➕ Lisää tuote aterialle")
    mp_q = st.text_input("Hae tuotetta tai kirjoita nimi", placeholder="esim. kauramaito, ruisleipä...")
    if mp_q:
        fin_hits = fineli_search(mp_q)
        if fin_hits:
            st.caption(f"Fineli-tietokanta: {len(fin_hits)} osumaa")
            for hit in fin_hits:
                col1, col2 = st.columns([4,1])
                with col1:
                    st.markdown(f"**{hit['name'].title()}** – {hit['kcal']} kcal / 100 g · {hit.get('ryhmä','')}")
                with col2:
                    if st.button("➕", key=f"mp_{sel_day}_{sel_meal}_{hit['name']}"):
                        key = f"{sel_day}_{sel_meal}"
                        if key not in st.session_state.mealplan:
                            st.session_state.mealplan[key] = []
                        st.session_state.mealplan[key].append({
                            "name": hit["name"].title(),
                            "kcal": hit.get("kcal", 0),
                            "proteiini": hit.get("proteiini", 0),
                            "rasva": hit.get("rasva", 0),
                            "hh": hit.get("hh", 0),
                            "kuitu": hit.get("kuitu", 0),
                            "ryhmä": hit.get("ryhmä", ""),
                            "g": 100,
                        })
                        save_json(MEALPLAN_FILE, st.session_state.mealplan)
                        st.rerun()

    st.markdown("---")
    st.markdown("### 📅 Viikon suunnitelma")

    total_week_kcal = 0
    total_week_co2 = 0.0

    for day in DAYS:
        has_any = any(f"{day}_{m}" in st.session_state.mealplan for m in MEALS)
        with st.expander(f"**{day}**" + (" ✅" if has_any else ""), expanded=(day == sel_day)):
            day_kcal = 0
            for meal in MEALS:
                key = f"{day}_{meal}"
                items = st.session_state.mealplan.get(key, [])
                if items:
                    st.markdown(f"**{meal}:**")
                    for i, item in enumerate(items):
                        c1, c2, c3 = st.columns([3, 2, 1])
                        with c1:
                            g = st.number_input(f"{item['name']}", 10, 1000, item.get("g",100), step=10,
                                key=f"g_{day}_{meal}_{i}")
                            item["g"] = g
                        with c2:
                            kcal_portion = round(item.get("kcal",0) * g / 100)
                            st.caption(f"≈ {kcal_portion} kcal · {item.get('ryhmä','')}")
                            day_kcal += kcal_portion
                        with c3:
                            if st.button("🗑️", key=f"del_{day}_{meal}_{i}"):
                                st.session_state.mealplan[key].pop(i)
                                save_json(MEALPLAN_FILE, st.session_state.mealplan)
                                st.rerun()
                else:
                    st.caption(f"{meal}: –")
            if day_kcal > 0:
                st.markdown(f"**Päivän kalorit yhteensä: {day_kcal} kcal**")
            total_week_kcal += day_kcal

    st.markdown("---")
    st.markdown("### 📊 Viikon yhteenveto")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("🔥 Kalorit viikossa", f"{total_week_kcal} kcal")
        st.caption(f"≈ {round(total_week_kcal/7)} kcal/pv")
    with s2:
        items_count = sum(len(v) for v in st.session_state.mealplan.values())
        st.metric("🍽️ Aterioita suunniteltu", items_count)
    with s3:
        if st.button("🗑️ Tyhjennä koko viikko"):
            st.session_state.mealplan = {}
            save_json(MEALPLAN_FILE, {})
            st.rerun()

    if total_week_kcal > 0:
        st.info(f"💡 Suunnittelu vähentää ruokahävikkiä jopa 30 % – hienoa että suunnittelet etukäteen! 🌱")

# ── 9. KESTÄVYYSPISTEET ───────────────────────────────────────────────────────
elif "Kestävyyspisteet" in page:
    st.title("🏆 Kestävyyspisteet & saavutukset")
    st.markdown("Kerää pisteitä tekemällä kestäviä ruokavalintoja!")

    p = st.session_state.points
    total = p.get("total", 0)
    streak = p.get("streak", 0)
    badges = p.get("badges", [])
    log = p.get("log", [])

    # Pisteet isona
    st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a5c2a,#2d8a47);border-radius:16px;padding:24px;text-align:center;color:white;margin-bottom:16px'>
<div style='font-size:3em;font-weight:800'>{total}</div>
<div style='font-size:1.1em;opacity:0.9'>Kestävyyspistettä</div>
<div style='margin-top:8px;font-size:0.9em;opacity:0.8'>🔥 Putki: {streak} peräkkäistä Eco A/B-valintaa</div>
</div>""", unsafe_allow_html=True)

    # Seuraava taso
    levels = [(10,"🌱 Vihreä aloittaja"),(50,"🌿 Kestävä ostaja"),(100,"🏆 Ekosankari"),(200,"🌍 Planeetan puolustaja")]
    next_lvl = next((pts for pts, _ in levels if pts > total), None)
    if next_lvl:
        progress = min(total / next_lvl, 1.0)
        st.markdown(f"**Seuraava taso: {next_lvl} pistettä**")
        st.progress(progress)
        st.caption(f"{next_lvl - total} pistettä puuttuu")

    st.markdown("---")

    # Saavutukset
    st.markdown("### 🎖️ Saavutukset")
    ALL_BADGES = [
        ("🌱 Vihreä aloittaja", "10 pistettä"),
        ("🌿 Kestävä ostaja", "50 pistettä"),
        ("🏆 Ekosankari", "100 pistettä"),
        ("🌍 Planeetan puolustaja", "200 pistettä"),
        ("🔥 5 putki", "5 Eco A/B peräkkäin"),
        ("💎 10 putki", "10 Eco A/B peräkkäin"),
    ]
    badge_cols = st.columns(3)
    for i, (badge, desc) in enumerate(ALL_BADGES):
        earned = badge in badges
        with badge_cols[i % 3]:
            bg = "#d4edda" if earned else "#f0f0f0"
            opacity = "1" if earned else "0.4"
            st.markdown(f"""<div style='background:{bg};border-radius:10px;padding:12px;text-align:center;opacity:{opacity};margin-bottom:8px'>
<div style='font-size:1.8em'>{badge.split()[0]}</div>
<div style='font-weight:600;font-size:0.85em'>{' '.join(badge.split()[1:])}</div>
<div style='font-size:0.75em;color:#555'>{desc}</div>
{"<div style='color:#1a5c2a;font-weight:700;font-size:0.8em'>✅ Ansaittu!</div>" if earned else ""}
</div>""", unsafe_allow_html=True)

    # Pisteiden miten saa -ohje
    st.markdown("---")
    st.markdown("### 📋 Miten pisteitä kertyy?")
    st.markdown("""
| Teko | Pisteet |
|---|---|
| Eco A tai B -tuote ostoslistalle | +3 |
| Kasvis- tai vegaanituote | +2 |
| Kotimainen tuote 🇫🇮 | +2 |
| NOVA 1 tai 2 -tuote | +1 |
""")

    # Lokihistoria
    if log:
        st.markdown("---")
        st.markdown("### 📜 Pisteloki")
        for entry in reversed(log[-20:]):
            st.caption(f"🌱 +{entry.get('pts',0)} – {entry.get('reason','')} ({entry.get('date','')})")

    if st.button("🗑️ Nollaa pisteet"):
        st.session_state.points = {"total":0,"streak":0,"log":[],"badges":[]}
        save_json(POINTS_FILE, st.session_state.points)
        st.rerun()

# ── 10. PARASTA ENNEN -HÄLYTYKSET ─────────────────────────────────────────────
elif "Parasta ennen" in page:
    st.title("🔔 Parasta ennen -hälytykset")
    st.markdown("Lisää kotona olevat tuotteet listalle – sovellus varoittaa kun päiväys lähestyy ja ehdottaa reseptejä.")

    from datetime import date, timedelta

    # Lisää uusi tuote
    st.markdown("### ➕ Lisää tuote kaappilistaan")
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        exp_name = st.text_input("Tuotteen nimi", placeholder="esim. Jogurtti, Lohi, Pinaatti...")
    with c2:
        exp_date = st.date_input("Parasta ennen", value=date.today() + timedelta(days=7), min_value=date.today())
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Lisää") and exp_name:
            entry = {
                "name": exp_name,
                "expiry": exp_date.strftime("%Y-%m-%d"),
                "added": date.today().strftime("%Y-%m-%d"),
            }
            if not isinstance(st.session_state.expiry, list):
                st.session_state.expiry = []
            st.session_state.expiry.append(entry)
            save_json(EXPIRY_FILE, st.session_state.expiry)
            st.success(f"✅ {exp_name} lisätty!")
            st.rerun()

    st.markdown("---")

    if not st.session_state.expiry:
        st.info("Kaappilista on tyhjä. Lisää tuotteita yllä olevalla lomakkeella.")
    else:
        today = date.today()
        expired, urgent, ok = [], [], []
        for item in st.session_state.expiry:
            try:
                d = date.fromisoformat(item["expiry"])
                diff = (d - today).days
                item["_days"] = diff
                if diff < 0:      expired.append(item)
                elif diff <= 2:   urgent.append(item)
                else:             ok.append(item)
            except:
                ok.append(item)

        def show_expiry_items(items, bg, icon):
            for i, item in enumerate(items):
                d = item.get("_days", "?")
                label = "Vanhentunut!" if isinstance(d,int) and d < 0 else (f"Vanhenee tänään!" if d == 0 else f"Vanhenee {d} päivässä")
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                with c1: st.markdown(f"**{item['name']}**")
                with c2: st.caption(f"📅 {item['expiry']}")
                with c3:
                    st.markdown(f"<span style='background:{bg};padding:2px 8px;border-radius:4px;font-size:0.85em'>{icon} {label}</span>", unsafe_allow_html=True)
                with c4:
                    if st.button("🗑️", key=f"exp_del_{item['name']}_{i}"):
                        st.session_state.expiry.remove(item)
                        save_json(EXPIRY_FILE, st.session_state.expiry)
                        st.rerun()
                # Reseptiehdotus
                term = requests.utils.quote(item["name"].split()[0])
                st.caption(f"🍽️ Resepti-idea: [Kotikokki]( https://www.kotikokki.net/reseptit/haku/?search={term}) · [K-Ruoka](https://www.k-ruoka.fi/reseptit?search={term})")

        if expired:
            st.error(f"❌ Vanhentuneita tuotteita: {len(expired)}")
            show_expiry_items(expired, "#f8d7da", "❌")
            st.markdown("---")
        if urgent:
            st.warning(f"⚠️ Pian vanhentuvia (0–2 pv): {len(urgent)}")
            show_expiry_items(urgent, "#fff3cd", "⚠️")
            st.markdown("---")
        if ok:
            st.success(f"✅ Hyväkuntoisia tuotteita: {len(ok)}")
            show_expiry_items(ok, "#d4edda", "✅")

        st.markdown("---")
        if st.button("🗑️ Tyhjennä koko kaappilista"):
            st.session_state.expiry = []
            save_json(EXPIRY_FILE, [])
            st.rerun()

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
