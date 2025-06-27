import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import csv
import io
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

st.set_page_config(page_title="ChatGPT Citation Extractor", layout="centered")

st.title("📄 ChatGPT Citation Extractor (Supports `/share/` URLs)")
st.markdown("Paste a public **ChatGPT share URL** (e.g. `https://chatgpt.com/share/...`) and extract all citations — including AI Overview references and confidence scores.")

url_input = st.text_input("🔗 Enter ChatGPT shared link:")

@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(ChromeDriverManager().install(), options=options)

def fetch_rendered_html(url):
    driver = get_driver()
    driver.get(url)
    time.sleep(5)  # Let JS load
    html = driver.page_source
    driver.quit()
    return html

def extract_citations(html):
    soup = BeautifulSoup(html, 'html.parser')
    citations = []
    seen = set()
    ref_map = {}

    for sup in soup.find_all(['sup', 'span']):
        ref_match = re.match(r'\[?(\d{1,2})\]?', sup.get_text(strip=True))
        if ref_match:
            ref_id = ref_match.group(1)
            parent = sup.find_parent()
            if parent:
                link = parent.find('a', href=True)
                if link:
                    href = link['href']
                    domain = urlparse(href).netloc.replace('www.', '')
                    text = link.get_text(strip=True) or "(no text)"
                    ref_map[href] = ref_id
                    key = href
                    if key not in seen:
                        citations.append([text, href, domain, ref_id, ""])
                        seen.add(key)

    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href.startswith('http'):
            continue
        text = a.get_text(strip=True) or "(no text)"
        domain = urlparse(href).netloc.replace('www.', '')
        citation_id = ref_map.get(href, "")
        confidence = ""
        next_text = a.find_next(string=True)
        if next_text:
            match = re.search(r'(\d{2,3})\s*%', next_text)
            if match:
                confidence = match.group(1) + "%"
        key = href
        if key not in seen:
            citations.append([text, href, domain, citation_id, confidence])
            seen.add(key)
    return citations

def convert_to_csv(data):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Text", "URL", "Domain", "Citation ID", "Confidence"])
    writer.writerows(data)
    return output.getvalue().encode("utf-8")

if url_input:
    if not url_input.startswith("https://chatgpt.com/share/"):
        st.error("❌ Please enter a valid ChatGPT share URL.")
    else:
        with st.spinner("Loading shared conversation..."):
            try:
                html = fetch_rendered_html(url_input)
                citations = extract_citations(html)
                if citations:
                    st.success(f"✅ Found {len(citations)} unique citations.")
                    csv_data = convert_to_csv(citations)
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv_data,
                        file_name="chatgpt_citations.csv",
                        mime="text/csv"
                    )
                    st.markdown("### 📋 Preview")
                    st.dataframe(citations, use_container_width=True)
                else:
                    st.warning("⚠️ No citations found.")
            except Exception as e:
                st.error(f"❌ Error: {e}")
