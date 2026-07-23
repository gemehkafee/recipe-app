import streamlit as st
import json
from recipe_scrapers import scrape_me
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
url_input = st.text_input("Paste a recipe URL:", placeholder="https://www.allrecipes.com/...")

if st.button("Clean & Save Recipe"):
    if url_input:
        with st.spinner("Downloading webpage and stripping fluff..."):
            try:
                scraper = scrape_me(url_input)
                recipe_data = {
                    "title": scraper.title(),
                    "source_url": url_input,
                    "prep_time": f"{scraper.prep_time()} mins",
                    "cook_time": f"{scraper.cook_time()} mins",
                    "ingredients": scraper.ingredients(),
                    "instructions": scraper.instructions_list()
                }
                
                doc_ref = db.collection("recipes").document()
                doc_ref.set(recipe_data)
                st.success(f"Successfully scraped & saved: '{scraper.title()}'!")
            except Exception as e:
                st.error(f"Could not scrape that URL. Error: {e}")
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
            col1, col2 = st.columns(2)
            with col1:
                st.write("### Ingredients")
                for item in data.get("ingredients", []):
                    st.write(f"- {item}")
            with col2:
                st.write("### Instructions")
                for idx, step in enumerate(data.get("instructions", []), 1):
                    st.write(f"{idx}. {step}")
