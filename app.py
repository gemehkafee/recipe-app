import streamlit as st
import json
import requests
from recipe_scrapers import scrape_html
from google.cloud import firestore
from google.oauth2 import service_account

# Connect to Firestore using Streamlit Secrets
if "gcp_service_account" in st.secrets:
    key_dict = json.loads(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
else:
    db = firestore.Client()

st.set_page_config(page_title="Recipe Catalog", page_icon="🍳")
st.title("🍳 Recipe Stripper & Searchable Catalog")

st.subheader("1. Convert & Save a Web Recipe")
url_input = st.text_input("Paste a recipe URL:", placeholder="https://www.simplyrecipes.com/...")

if st.button("Clean & Save Recipe"):
    if url_input:
        with st.spinner("Downloading webpage and stripping fluff..."):
            try:
                # 1. Full browser impersonation headers
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                
                # 2. Fetch the page HTML
                # response = requests.get(url_input, headers=headers, timeout=10)
                # response.raise_for_status()
                SCRAPER_API_KEY = "0a3aa80dd6e383f7da31594734e54b7a"
                proxy_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url_input}"

                response = requests.get(proxy_url, timeout=20)
                response.raise_for_status()
                
                # 3. Parse using recipe-scrapers' dedicated scrape_html function
                scraper = scrape_html(response.text, org_url=url_input, wild_mode=True)
                
                recipe_data = {
                    "title": scraper.title(),
                    "source_url": url_input,
                    "prep_time": f"{scraper.prep_time()} mins" if scraper.prep_time() else "N/A",
                    "cook_time": f"{scraper.cook_time()} mins" if scraper.cook_time() else "N/A",
                    "ingredients": scraper.ingredients(),
                    "instructions": scraper.instructions_list()
                }
                
                # 4. Save to GCP Firestore
                doc_ref = db.collection("recipes").document()
                doc_ref.set(recipe_data)
                st.success(f"Successfully scraped & saved: '{scraper.title()}'!")
                
            except Exception as e:
                st.error(f"Could not scrape that URL. Details: {e}")
    else:
        st.warning("Please paste a URL first!")

st.divider()

st.subheader("2. Your Searchable Recipe Catalog")
recipes_ref = db.collection("recipes").stream()
recipes_list = list(recipes_ref)

if not recipes_list:
    st.info("No recipes in your catalog yet. Add one above!")
else:
    for doc in recipes_list:
        data = doc.to_dict()
        with st.expander(f"📖 {data.get('title', 'Untitled Recipe')}"):
            st.write(f"**Prep Time:** {data.get('prep_time')} | **Cook Time:** {data.get('cook_time')}")
            if data.get("source_url"):
                st.caption(f"Source: {data.get('source_url')}")
            col1, col2 = st.columns(2)
            with col1:
                st.write("### Ingredients")
                for item in data.get("ingredients", []):
                    st.write(f"- {item}")
            with col2:
                st.write("### Instructions")
                for idx, step in enumerate(data.get("instructions", []), 1):
                    st.write(f"{idx}. {step}")
