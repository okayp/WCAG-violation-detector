import streamlit as st

# Streamlit config must be first
st.set_page_config(page_title="Accessibility Auditor", layout="wide")

# ── Imports ─────────────────────────────────────────────────────────────
import subprocess
import json
import tempfile
import os
import sys
from urllib.parse import urlparse

#from app import extract_full_html_css
from get_sites import get_all_website_links
import openai
openai.api_key = "your_openai_api_key"

# ── OpenAI Function ─────────────────────────────────────────────────────
def get_fixed_html_from_openai(code, message, html_snippet):
    prompt = f"""
You are an expert in web accessibility and HTML. The following HTML element violates a WCAG guideline.

Rule Violated: {code}
Description: {message}
HTML to Fix:
{html_snippet}

Please provide a corrected version of this HTML that resolves the violation, with no extra explanation — only the corrected HTML.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that fixes WCAG accessibility violations in HTML."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error with OpenAI: {e}")
        return None

# ── Session State ──────────────────────────────────────────────────────
if "site_urls" not in st.session_state:
    st.session_state.site_urls = []
if "audit_url" not in st.session_state:
    st.session_state.audit_url = None

# ── UI: Input & URL Discovery ───────────────────────────────────────────
st.title("🔍 Web Accessibility Auditor")
homepage_url = st.text_input("Enter homepage URL")

if homepage_url and st.button("Scan Website for Internal Pages"):
    with st.spinner("🔄 Scanning for internal URLs..."):
        result = get_all_website_links(homepage_url)
        urls = result.get("urls", [])
        if homepage_url not in urls:
            urls.insert(0, homepage_url)
        st.session_state.site_urls = urls
        st.session_state.audit_url = None
        st.success(f"✅ Found {len(urls)} URLs.")

# ── UI: Page Selection ──────────────────────────────────────────────────
if st.session_state.site_urls and not st.session_state.audit_url:
    st.markdown("### 🧭 Select a page to audit:")
    for url in st.session_state.site_urls:
        if st.button(f"🔍 Audit: {url}"):
            st.session_state.audit_url = url
            st.rerun()

# ── Audit Execution ─────────────────────────────────────────────────────
if st.session_state.audit_url:
    url = st.session_state.audit_url
    st.markdown(f"## 🚀 Auditing: `{url}`")

    with st.spinner("Running Axe & Pa11y..."):
        # Inject target URL into JS runners
        for fname in ["axe_runner.js", "pa11y_runner.js"]:
            with open(fname, "r") as f:
                lines = f.readlines()
            with open(fname, "w") as f:
                for line in lines:
                    if line.strip().startswith("const url ="):
                        f.write(f'const url = "{url}";\n')
                    else:
                        f.write(line)

        # Run audits
        try:
            subprocess.run(["node", "axe_runner.js"], check=True)
        except Exception as e:
            st.warning(f"Axe failed: {e}")

        try:
            subprocess.run(["node", "pa11y_runner.js"], check=True)
        except Exception as e:
            st.warning(f"Pa11y failed: {e}")

        with open("pa11y_output.json", "r", encoding="utf-8") as f:
            pa11y_data = json.load(f)
        try:
            with open("axe_report.json", "r", encoding="utf-8") as f:
                axe_data = json.load(f)
        except:
            axe_data = None

    # ── Normalization ────────────────────────────────────────────────────
    impact_map_pa11y = {1: "critical", 2: "serious", 3: "moderate"}
    pa11y_issues = pa11y_data.get("issues", [])
    axe_issues = axe_data.get("violations", []) if axe_data else []

    standardized_pa11y = [{
        "source": "pa11y",
        "rule": i.get("code"),
        "impact": impact_map_pa11y.get(i.get("typeCode", 0), "minor"),
        "selector": i.get("selector"),
        "message": i.get("message", ""),
        "failure_summary": None,
        "matched_html": None
    } for i in pa11y_issues]

    standardized_axe = [{
        "source": "axe",
        "rule": v.get("id"),
        "impact": v.get("impact", "minor"),
        "selector": v.get("nodes", [{}])[0].get("target", [None])[0],
        "message": v.get("help", ""),
        "failure_summary": v.get("nodes", [{}])[0].get("failureSummary", ""),
        "matched_html": None
    } for v in axe_issues if v.get("nodes")]

    combined_issues = [i for i in (standardized_pa11y + standardized_axe) if i["selector"]]

    # ── Fetch Original HTML Snippets ─────────────────────────────────────
    selectors = [i["selector"] for i in combined_issues]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json", encoding="utf-8") as tmp:
        json.dump(selectors, tmp)
        selector_file = tmp.name
    try:
        result = subprocess.run(
            [sys.executable, "scraper.py", url, selector_file],
            capture_output=True, text=True, check=True
        )
        html_map = json.loads(result.stdout)
    except Exception as e:
        st.error(f"Scraper error: {e}")
        html_map = {}
    os.unlink(selector_file)

    for i in combined_issues:
        i["matched_html"] = html_map.get(i["selector"], "(not found)")

    st.success(f"✅ Audit completed – {len(combined_issues)} issues found.")


    # ── Display Issues ───────────────────────────────────────────────────
    for idx, issue in enumerate(combined_issues):
        with st.expander(f"[{issue['source'].upper()}] {issue['impact']} – {issue['rule']}"):
            st.markdown(f"**Selector:** `{issue['selector']}`")
            st.markdown(f"**Message:** {issue['message']}")
            if issue["failure_summary"]:
                st.markdown(f"**Failure Summary:** {issue['failure_summary']}")
            st.markdown("**❌ original_html**")
            st.code(issue["matched_html"], language="html")


            #if idx < 20:
            fixed = get_fixed_html_from_openai(issue["rule"], issue["message"], issue["matched_html"])
            st.markdown("**✅ fixed_html**")
            st.code(fixed, language="html")
            issue["fixed_html"] = fixed
            """
            else:
                st.warning("Skipped fix (limit 20)")
                issue["fixed_html"] = None
            """



    # ── Download JSON Button ─────────────────────────────────────────────
    st.markdown("---")
    st.download_button(
        label="📥 Download JSON Report",
        data=json.dumps(combined_issues, indent=2),
        file_name=f"accessibility_issues_{urlparse(url).netloc}.json",
        mime="application/json"
    )
