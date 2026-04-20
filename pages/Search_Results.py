import streamlit as st
import sqlite3
import json
import os

# Page configuration
st.set_page_config(
    page_title="dot.ai | Deep Search Results",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load Global Styles
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Path to style.css in the parent directory
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "style.css")
local_css(css_path)

# Custom Background for Standalone Page
st.markdown("""
    <style>
        .stApp {
            background: radial-gradient(circle at top right, #1e1b4b, #020617) !important;
        }
        .results-container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 60px 20px;
        }
        .dossier-header {
            text-align: center;
            margin-bottom: 60px;
            animation: messageEntrance 0.8s ease-out;
        }
        .dossier-tag {
            background: linear-gradient(90deg, #8B5CF6, #06B6D4);
            color: white;
            padding: 5px 15px;
            border-radius: 50px;
            font-size: 0.75rem;
            font-weight: 800;
            letter-spacing: 2px;
            text-transform: uppercase;
            display: inline-block;
            margin-bottom: 15px;
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.4);
        }
    </style>
""", unsafe_allow_html=True)

# Fetch latest results from DB
def get_latest_results():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_history.db")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT query, results_json FROM latest_search WHERE id = 1")
        row = c.fetchone()
        conn.close()
        if row:
            return row[0], json.loads(row[1])
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
    return None, None

query, results = get_latest_results()

# Render UI
st.markdown("<div class='results-container'>", unsafe_allow_html=True)

# Cinematic Header
st.markdown(f"""
    <div class="dossier-header">
        <div class="dossier-tag">Neural Extraction Successful</div>
        <h1 style='color: white; font-family: "Space Grotesk", sans-serif; font-size: 3.5rem; letter-spacing: -2px; margin-bottom: 10px;'>INTELLIGENCE DOSSIER</h1>
        <p style='color: var(--text-muted); font-size: 1.1rem; max-width: 600px; margin: 0 auto;'>Validated neural data report generated for research query: <span style='color: var(--accent-cyan); font-weight: 600;'>"{query.upper() if query else 'N/A'}"</span></p>
    </div>
""", unsafe_allow_html=True)

col_nav = st.columns([1, 1, 1])
with col_nav[1]:
    st.link_button("🔙 BACK TO COMMAND CENTER", "/", use_container_width=True)

st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

if not results:
    st.info("No active search results found. Please perform a search in the main Nexus hub.")
else:
    for i, r in enumerate(results):
        st.markdown(f"""
            <div class="neural-dossier-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 25px;">
                    <span style="border: 1px solid rgba(139, 92, 246, 0.4); color: #8B5CF6; padding: 4px 12px; border-radius: 8px; font-size: 0.7rem; font-weight: 800; letter-spacing: 1px;">ENTRY {i+1}</span>
                    <a href="{r['href']}" target="_blank" style="text-decoration: none;">
                        <span style="background: rgba(6, 182, 212, 0.1); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); padding: 8px 20px; border-radius: 12px; font-weight: 700; font-size: 0.85rem; font-family: 'Space Grotesk', sans-serif; transition: 0.3s; cursor: pointer;">
                            EXPLORE SOURCE 📑
                        </span>
                    </a>
                </div>
                <h2 style="color: #fff; margin-bottom: 20px; font-size: 1.8rem; line-height: 1.2; font-family: 'Space Grotesk', sans-serif; letter-spacing: -0.5px;">{r['title']}</h2>
                <p style="color: #cbd5e1; font-size: 1.05rem; line-height: 1.8; opacity: 0.85; font-family: 'Outfit', sans-serif;">{r['body']}</p>
                
                <div style="margin-top: 30px; display: flex; align-items: center; gap: 20px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 20px;">
                    <div style="display: flex; flex-direction: column;">
                        <span style="font-size: 0.65rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">Data Origin</span>
                        <span style="color: #06B6D4; font-size: 0.85rem; font-weight: 600; font-family: 'Space Grotesk', sans-serif;">{r['href'][:50]}...</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
