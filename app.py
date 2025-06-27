import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import csv
import io

st.set_page_config(page_title="ChatGPT Citation Extractor", layout="centered")

st.title("📄 ChatGPT Citation Extractor with AI Overview Detection")
st.markdown("Paste a **ChatGPT share URL** to extract all citations — including AI-style `[1]` references and confidence scores.")

url_input = st.text_input("🔗 Enter ChatGPT shared link (e.g. https://chatgpt.com/c/...):")

def extract_citations(html):
    soup = BeautifulSoup(html, 'html.parser')
    citations = []
    seen = set()

    # Mapping like: href => citation ID (e.g. [1])
    ref_map = {}

    # Step 1: Detect references like [1] or Source [2] pointing to a link
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

    # Step 2: All other anchor tags
    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href.startswith('http'):
            continue
        text = a.get_text(strip=True) or "(no text)"
        domain = urlparse(href).netloc.replace('www.', '')
        citation_id = ref_map.get(href, "")

        # Confidence score nearby (✓ 92%, 87%, etc.)
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
    if not url_input.startswith("https://chatgpt.com/c/"):
        st.error("❌ Please enter a valid ChatGPT share URL.")
    else:
        with st.spinner("Fetching and analyzing chat..."):
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                res = requests.get(url_input, headers=headers, timeout=10)

                if res.status_code != 200:
                    st.error(f"❌ Failed to fetch content (status code: {res.status_code})")
                else:
                    citations = extract_citations(res.text)
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
