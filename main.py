import streamlit as st
import time
import os
import sqlite3
import base64
import google.generativeai as genai
import urllib.parse
from dotenv import load_dotenv
from datetime import datetime
from duckduckgo_search import DDGS
import urllib.request
import urllib.parse
from PIL import Image

# Load environment variables
load_dotenv(override=True)

# Initialize session state early
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7
if "chat_search" not in st.session_state:
    st.session_state.chat_search = ""
if "web_search_enabled" not in st.session_state:
    st.session_state.web_search_enabled = True
if "vision_enabled" not in st.session_state:
    st.session_state.vision_enabled = True
if "selected_model_name" not in st.session_state:
    st.session_state.selected_model_name = "models/gemini-2.5-flash"
if "last_search_results" not in st.session_state:
    st.session_state.last_search_results = []
if "deep_search_results" not in st.session_state:
    st.session_state.deep_search_results = []
if "deep_search_query" not in st.session_state:
    st.session_state.deep_search_query = ""
if "active_view" not in st.session_state:
    st.session_state.active_view = "Nexus Chat"
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
if "external_trigger" not in st.session_state:
    st.session_state.external_trigger = None
    st.session_state.external_trigger = None

# --- EXTERNAL PROMPT HANDLER (DASHBOARD SYNC) [V49] ---
if "p" in st.query_params:
    external_prompt = st.query_params["p"]
    # Clear to prevent loops (Streamlit 1.30+ API)
    st.query_params.clear()
    
    if external_prompt:
        if st.session_state.current_chat_id is None:
            # We need to define create_conversation first or use it here
            # Since create_conversation is defined later, we might need to be careful
            # But in Streamlit, functions are defined before they are used if top-down
            pass 
        
        # We'll handle the actual message appending AFTER function definitions
        st.session_state.external_trigger = external_prompt

# Initialize DOT.ai (Gemini) Client
api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "your_gemini_api_key_here":
    genai.configure(api_key=api_key)
    # Ultra-Simple Vision Instruction
    sys_instr = "Your name is DOT.ai. You are a highly intelligent and professional AI assistant. Provide complete, detailed, and comprehensive information for whatever the user asks. Explain concepts clearly and thoroughly, but ensure all information is strictly relevant to the user's query."
    if st.session_state.vision_enabled:
        sys_instr += " If the user wants a picture or image, just include this exact tag in your response: [GENERATE_IMAGE: {description}] where {description} is a short English prompt for the image. Do not use markdown for the image yourself; only provide this tag."
    
    model = genai.GenerativeModel(
        model_name=st.session_state.selected_model_name,
        system_instruction=sys_instr,
        generation_config={"temperature": st.session_state.temperature}
    )
else:
    model = None

# ---- UTILLITY HELPERS ----
def load_neural_engine(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None

def perform_web_search(query):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if results:
                st.session_state.last_search_results = results
                context = "\n\n--- WEB SEARCH RESULTS ---\n"
                for r in results:
                    url = r.get('href', '')
                    title = r['title']
                    context += f"Source: {title}\nURL: {url}\nContent: {r['body']}\n\n"
                return context
    except Exception as e:
        print(f"Search error: {e}")
    return ""

def get_neural_fallback(user_input):
    import re
    user_input_clean = user_input.lower().strip()
    
    # --- LEVEL 1: Instant Local Layer (Zero Latency) ---
    greetings = {
        r"^(hi|hello|hey|hii|helo|hy|hola|salam)$": "Hello! Main DOT.ai hoon. Kaise madad kar sakta hoon aapki? 🌌",
        r"^(kaise ho|how are you|kya haal)$": "Main ekdum badhiya hoon! Aap bataiye, aapka din kaisa ja raha hai? 😊",
        r"^(kya kar rahe ho|what are you doing)$": "Main abhi aapke sawalon ka intezar kar raha hoon taaki aapki life asaan bana sakoon! 🦾",
        r"^(shukriya|thanks|thank you)$": "Aapka swagat hai! Agar kuch aur poochna ho toh main yahin hoon. ✨"
    }
    for pattern, reply in greetings.items():
        if re.search(pattern, user_input_clean):
            return reply

    # --- LEVEL 2: Image Generation Trigger ---
    if re.search(r'\b(image|picture|drawing|draw|banao|dikhao)\b', user_input_clean):
        prompt_words = [w for w in user_input.split() if w not in ["image", "dikhao", "banao", "ek", "ki", "draw"]]
        img_prompt = "_".join(prompt_words) if prompt_words else "futuristic_neural_ai"
        return f"Bilkul! Neural Vision se aapke liye ye image generate ho rahi hai:\n\n![Vision](https://image.pollinations.ai/prompt/{img_prompt}?width=1024&height=1024&nologo=true)"

    # --- LEVEL 3: Robust Neural Relay ---
    try:
        import urllib.request
        prompt = urllib.parse.quote(user_input)
        sys_prompt = urllib.parse.quote("Your name is dot.ai. Provide full, detailed, and complete information for whatever the user asks. Explain clearly.")
        url = f"https://text.pollinations.ai/{prompt}?model=openai&system={sys_prompt}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=12) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        return f"Neural Relay error: Mujhe thodi dikkat aa rahi hai internet connect karne mein."


def display_copy_button(text):
    import json
    json_text = json.dumps(text)
    html_code = f"""
    <div id="copy-status" style="color: #06B6D4; font-size: 0.8rem; margin-top: 5px; font-family: 'Space Grotesk', sans-serif;"></div>
    <button id="copy-btn" onclick="copyToClipboard()" style="
        background: rgba(139, 92, 246, 0.1);
        border: 1px solid rgba(139, 92, 246, 0.3);
        color: #8B5CF6;
        padding: 8px 16px;
        border-radius: 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    ">
        <span id="btn-icon">📋</span> <span id="btn-text">Copy Response</span>
    </button>

    <script>
        function updateUI(status) {{
            const statusDiv = document.getElementById('copy-status');
            const btn = document.getElementById('copy-btn');
            const btnText = document.getElementById('btn-text');
            statusDiv.innerText = status;
            btn.style.borderColor = '#06B6D4';
            btn.style.background = 'rgba(6, 182, 212, 0.1)';
            btnText.style.color = '#06B6D4';
            setTimeout(() => {{
                statusDiv.innerText = '';
                btn.style.borderColor = 'rgba(139, 92, 246, 0.3)';
                btn.style.background = 'rgba(139, 92, 246, 0.1)';
                btnText.style.color = '#8B5CF6';
            }}, 2000);
        }}

        function copyToClipboard() {{
            const text = {json_text};
            if (navigator.clipboard) {{
                navigator.clipboard.writeText(text).then(() => updateUI('Copied to clipboard! ⚡'))
                    .catch(err => console.error('Failed to copy', err));
            }} else {{
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-9999px';
                textArea.style.top = '0';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {{
                    const successful = document.execCommand('copy');
                    if (successful) updateUI('Copied! ✨');
                    else throw new Error('execCommand failed');
                }} catch (err) {{
                    console.error('Copy failed completely', err);
                }}
                document.body.removeChild(textArea);
            }}
        }}
    </script>
    """
    from streamlit.components.v1 import html
    html(html_code, height=60)

def extract_text_from_pdf(pdf_file):
    try:
        reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"


# ---- DATABASE LOGIC ----
def init_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS latest_search
                 (id INTEGER PRIMARY KEY, query TEXT, results_json TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_search_result(query, results):
    import json
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    # Always overwrite ID 1 to maintain only the latest search for the results page
    c.execute("INSERT OR REPLACE INTO latest_search (id, query, results_json) VALUES (1, ?, ?)", 
              (query, json.dumps(results)))
    conn.commit()
    conn.close()

def save_message(conv_id, role, content):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)", (conv_id, role, content))
    conn.commit()
    conn.close()

def create_conversation(title):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("INSERT INTO conversations (title) VALUES (?)", (title,))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_recent_conversations(limit=15):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    # Fetch timestamp for grouping
    c.execute("SELECT id, title, timestamp FROM conversations ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def delete_conversation(conv_id):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    c.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()

def load_messages(conv_id):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC", (conv_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

init_db()

# --- EXTERNAL TRIGGER PROCESSING (DASHBOARD SYNC) ---
if st.session_state.external_trigger:
    ext_prompt = st.session_state.external_trigger
    st.session_state.external_trigger = None # Clear it
    
    if st.session_state.current_chat_id is None:
        st.session_state.current_chat_id = create_conversation(ext_prompt)
    
    st.session_state.messages.append({"role": "user", "content": ext_prompt})
    save_message(st.session_state.current_chat_id, "user", ext_prompt)
    
    # Check if search is needed
    search_keywords = ["search", "find", "who is", "what is", "latest", "news", "current", "weather", "price", "visualize", "analyze", "generate"]
    needs_search = st.session_state.web_search_enabled or any(k in ext_prompt.lower() for k in search_keywords)
    
    if needs_search:
        st.session_state.deep_search_query = ext_prompt
        # Perform search and switch view
        with st.status("🧠 Neural extraction in progress...", expanded=True):
            context = perform_web_search(ext_prompt)
            if st.session_state.last_search_results:
                st.session_state.deep_search_results = st.session_state.last_search_results
                save_search_result(ext_prompt, st.session_state.last_search_results)
                st.session_state.active_view = "Deep Search"
    
    st.rerun()

# Page configuration
st.set_page_config(
    page_title="dot.ai | Premium AI",
    page_icon="🌌",
    layout="wide"
)

def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
            
load_css("style.css")

# ---- LIVE UI ENGINE ----
def inject_particle_engine():
    st.components.v1.html("""
    <canvas id="neuralCanvas"></canvas>
    <style>
        body { margin: 0; overflow: hidden; background: transparent; }
        #neuralCanvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: -1;
            background: radial-gradient(circle at center, #0f172a 0%, #020617 100%);
        }
    </style>
    <script>
        const canvas = document.getElementById('neuralCanvas');
        const ctx = canvas.getContext('2d');
        let particles = [];
        const particleCount = 60;

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }

        window.addEventListener('resize', resize);
        resize();

        class Particle {
            constructor() { this.reset(); }
            reset() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.vx = (Math.random() - 0.5) * 0.4;
                this.vy = (Math.random() - 0.5) * 0.4;
                this.radius = Math.random() * 2 + 1;
            }
            update() {
                this.x += this.vx; this.y += this.vy;
                if (this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) this.reset();
            }
            draw() {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(139, 92, 246, 0.4)';
                ctx.fill();
            }
        }

        for (let i = 0; i < particleCount; i++) particles.push(new Particle());

        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => {
                p.update(); p.draw();
                particles.forEach(p2 => {
                    const dx = p.x - p2.x;
                    const dy = p.y - p2.y;
                    const dist = Math.sqrt(dx*dx + dy*dy);
                    if (dist < 150) {
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(6, 182, 212, ${0.15 * (1 - dist/150)})`;
                        ctx.lineWidth = 0.5;
                        ctx.moveTo(p.x, p.y); ctx.lineTo(p2.x, p2.y);
                        ctx.stroke();
                    }
                });
            });
            requestAnimationFrame(animate);
        }
        animate();
    </script>
    """, height=0)

inject_particle_engine()

# Force all external links to open in a separate tab globally via JavaScript injection
from streamlit.components.v1 import html
html("""
<script>
    const forceNewTab = () => {
        const links = window.parent.document.querySelectorAll('a');
        links.forEach(link => {
            if (link.href && !link.href.includes(window.location.host)) {
                link.setAttribute('target', '_blank');
                link.setAttribute('rel', 'noopener noreferrer');
            }
        });
    };
    
    // Initial run
    setTimeout(forceNewTab, 1000);
    
    // Interval run to catch dynamically added links (like in chat)
    setInterval(forceNewTab, 2000);
</script>
""", height=0)

st.markdown('<base target="_blank">', unsafe_allow_html=True)

# --- Sky Menu (Single Floating Menu Bar on the Left) ---
with st.popover("☰", use_container_width=False):
    # 🔘 Top Branding (Stylized dot.ai Logo)
    st.markdown("""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px 0; border-bottom: 1px solid rgba(139, 92, 246, 0.1); margin-bottom: 15px;">
            <div style="
                font-family: 'Space Grotesk', sans-serif;
                font-weight: 900; 
                font-size: 2.6rem; 
                background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                letter-spacing: -3px;
                filter: drop-shadow(0 0 10px rgba(139, 92, 246, 0.3));
                line-height: 1;
            ">dot.ai</div>
            <div style="
                font-size: 0.6rem; 
                color: #94A3B8; 
                letter-spacing: 4px; 
                text-transform: uppercase; 
                margin-top: 5px; 
                opacity: 0.7;
                font-weight: 700;
            ">NEURAL INTERFACE</div>
        </div>
    """, unsafe_allow_html=True)

    # 📱 Mobile Sync QR
    st.markdown("<div style='text-align: center; font-size: 0.73rem; color: #40C9FF; font-weight: 700; letter-spacing: 2px; margin-bottom: 12px;'>DEVICE SYNC</div>", unsafe_allow_html=True)
    
    import socket
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
        except Exception:
            return '127.0.0.1'
        finally:
            try:
                s.close()
            except Exception:
                pass
            
    local_url = f"http://{get_local_ip()}:8501"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={local_url}&bgcolor=15-23-42&color=FFFFFF"
    
    st.image(qr_url, use_container_width=True, caption="Scan to view on your phone")

    st.markdown("---")
    
    # ➕ Main Action
    if st.button("➕ New Session", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.current_chat_id = None
        st.rerun()

        st.rerun()

    st.markdown("---")
    st.markdown("##### 🕒 Recent Sessions")
    recent_chats = get_recent_conversations(limit=5)
    if not recent_chats:
        st.markdown("<div style='text-align: center; opacity: 0.3; font-size: 1.2rem; margin: 10px 0;'>∅</div>", unsafe_allow_html=True)
    else:
        for chat_id, title, ts_str in recent_chats:
            is_active = (st.session_state.current_chat_id == chat_id)
            button_label = f"💬 {title[:22]}..." if len(title) > 22 else f"💬 {title}"
            if st.button(button_label, key=f"top_chat_{chat_id}", use_container_width=True, type="secondary" if not is_active else "primary"):
                st.session_state.messages = load_messages(chat_id)
                st.session_state.current_chat_id = chat_id
                st.rerun()
    
    st.markdown("---")
    
    if st.button("🗑️ Clear All History", use_container_width=True):
        conn = sqlite3.connect('chat_history.db')
        c = conn.cursor()
        c.execute("DELETE FROM messages")
        c.execute("DELETE FROM conversations")
        conn.commit()
        conn.close()
        st.session_state.messages = []
        st.session_state.current_chat_id = None
        st.rerun()

    st.markdown("---")
    
    # --- Neural Configuration (Settings) Section ---
    if st.button("⚙️ Settings", use_container_width=True):
        st.session_state.show_settings = not st.session_state.show_settings

    if st.session_state.show_settings:
        st.markdown("<div style='background: rgba(139, 92, 246, 0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(139, 92, 246, 0.1); margin-bottom: 20px;'>", unsafe_allow_html=True)
        st.session_state.temperature = st.slider("Creativity", 0.0, 1.0, 0.7, key="temp_slider_top")
        
        model_options = {
            "DOT.ai Flash (Fast)": "models/gemini-2.5-flash",
            "DOT.ai Pro (Smart)": "models/gemini-pro-latest",
            "DOT.ai Preview (Ultra)": "models/gemini-3.1-flash-lite-preview"
        }
        selected_display = st.selectbox("Intelligence Core", list(model_options.keys()), 
                                       index=list(model_options.values()).index(st.session_state.selected_model_name) if st.session_state.selected_model_name in model_options.values() else 0,
                                       key="model_sel_top")
        
        if model_options[selected_display] != st.session_state.selected_model_name:
            st.session_state.selected_model_name = model_options[selected_display]
            st.rerun()

        st.session_state.web_search_enabled = st.toggle("🌐 Web Grounding", value=st.session_state.web_search_enabled, key="web_top")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.button("💎 Premium Active", use_container_width=True)

# Navigation logic removed as per user request

# --- Conditional View Rendering ---
if st.session_state.active_view == "Nexus Chat":
    # Header (Dynamic visibility)
    if st.session_state.messages:
        st.markdown('''
            <div class="main-title-container">
                <div class="main-title">dot.ai</div>
            </div>
            ''', unsafe_allow_html=True)
        st.markdown('<div class="tagline">The Future of Intelligence</div>', unsafe_allow_html=True)

    # Main Frame Logging
    if not st.session_state.messages:
        # Nexus Prime: Cinema UI Layout [V37]
        st.markdown("""
            <style>
                .main .block-container { 
                    padding: 0 !important; 
                    max-width: 100% !important; 
                    margin: 0 !important;
                }
                [data-testid="stAppViewBlockContainer"], [data-testid="block-container"], .main .block-container { 
                    padding: 0 !important; 
                    margin: 0 !important;
                    max-width: 100% !important;
                }
                header[data-testid="stHeader"] { display: none !important; }
                [data-testid="stDecoration"] { display: none !important; }
                [data-testid="stStatusWidget"] { display: none !important; }
                footer { display: none !important; }
                .stApp { 
                    background: #020617 !important; 
                }
                
                /* Hide the default spacing given by Streamlit */
                div[data-testid="stVerticalBlock"] { 
                    gap: 0 !important; 
                    padding: 0 !important; 
                    margin: 0 !important;
                }
                
                /* Force iframe to sit exactly at the top without any empty space */
                iframe[title="streamlit.components.v1.html"] {
                    position: absolute !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 100vw !important;
                    height: 850px !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    border: none !important;
                }
                .main .block-container { 
                    padding-top: 0 !important; 
                }
            </style>
        """, unsafe_allow_html=True)
        
        scene_path = os.path.join(os.path.dirname(__file__), "three_scene.html")
        html_code = load_neural_engine(scene_path)
        
        if html_code:
            import streamlit.components.v1 as components
            # Reverted back to the original comfortable height
            components.html(html_code, height=850, scrolling=False)
        else:
            st.error("Neural Scene Engine Missing.")
    else:
        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            avatar = "🧑‍🚀" if message["role"] == "user" else "🌌"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])
                if message["role"] == "assistant":
                    display_copy_button(message["content"])

    # --- CHAT INPUT & RESPONSE HANDLER (Isolated to Main View) ---
    if raw_prompt := st.chat_input("Ask anything...", accept_file="multiple", accept_audio=True):
        
        # Extract text correctly based on returned dictionary/attribute structure
        prompt_text = ""
        attachment_names = []
        uploaded_files_data = []
        
        if hasattr(raw_prompt, 'text') and raw_prompt.text:
            prompt_text = raw_prompt.text
        elif isinstance(raw_prompt, dict) and raw_prompt.get("text"):
            prompt_text = raw_prompt["text"]
        elif isinstance(raw_prompt, str):
            prompt_text = raw_prompt
            
        if hasattr(raw_prompt, 'files') and raw_prompt.files:
            attachment_names = [f.name for f in raw_prompt.files]
            uploaded_files_data = raw_prompt.files
        elif isinstance(raw_prompt, dict) and raw_prompt.get("files"):
            attachment_names = [f.name for f in raw_prompt["files"]]
            uploaded_files_data = raw_prompt["files"]
            
        if hasattr(raw_prompt, 'audio') and raw_prompt.audio:
            attachment_names.append("🎤 voice_memo.wav")
        elif isinstance(raw_prompt, dict) and raw_prompt.get("audio"):
            attachment_names.append("🎤 voice_memo.wav")
            
        # Process images directly for Gemini
        pil_images = []
        for file in uploaded_files_data:
            if file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    img = Image.open(file)
                    pil_images.append(img)
                except Exception as e:
                    st.toast(f"Could not load image {file.name}")
            
        if not prompt_text and attachment_names:
            prompt_text = f"Attached: {', '.join(attachment_names)}"
            
        prompt = prompt_text
        
        search_keywords = ["search", "find", "who is", "what is", "latest", "news", "current", "weather", "price"]
        needs_search = st.session_state.web_search_enabled or any(k in prompt.lower() for k in search_keywords)
        
        prompt_with_context = prompt
        
        if needs_search:
            with st.status("🧠 Neural extraction in progress...", expanded=True):
                context = perform_web_search(prompt)
                if context:
                    prompt_with_context = f"{prompt}\n{context}"
                    save_search_result(prompt, st.session_state.last_search_results)

        # Normal chat logic
        if st.session_state.current_chat_id is None:
            st.session_state.current_chat_id = create_conversation(prompt)
            
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt, 
            "internal_prompt": prompt_with_context,
            "images": pil_images  # Added to session state
        })
        save_message(st.session_state.current_chat_id, "user", prompt)
        st.rerun()

    # Handle AI Response if last message is from user
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant", avatar="🌌"):
            message_placeholder = st.empty()
            full_response = ""
            
            last_msg = st.session_state.messages[-1]
            user_msg = last_msg.get("internal_prompt", last_msg["content"])
            attached_images = last_msg.get("images", [])
            
            if not model:
                with st.status("🧠 Processing Neural Request...", expanded=False):
                    try:
                        full_response = get_neural_fallback(user_msg)
                    except:
                        full_response = "Neural Relay is sleepy. Main abhi jawab nahi de paa raha hoon."
                
                # Simulate streaming
                words = full_response.split()
                temp_response = ""
                for word in words:
                    temp_response += word + " "
                    message_placeholder.markdown(f'<div class="assistant-message">{temp_response}▌</div>', unsafe_allow_html=True)
                    time.sleep(0.015)
                message_placeholder.markdown(f'<div class="assistant-message">{full_response}</div>', unsafe_allow_html=True)
            else:
                try:
                    with st.status("🌌 Neural Extraction...", expanded=False):
                        chat = model.start_chat()
                        
                        # Support Multimodal Payload
                        payload = [user_msg] + attached_images if attached_images else user_msg
                        
                        response = chat.send_message(payload, stream=True)
                        for chunk in response:
                            if chunk.text:
                                full_response += chunk.text
                                message_placeholder.markdown(f'<div class="assistant-message">{full_response}▌</div>', unsafe_allow_html=True)
                        message_placeholder.markdown(f'<div class="assistant-message">{full_response}</div>', unsafe_allow_html=True)
                except Exception as e:
                    # AUTO-FALLBACK on Gemini Errors (Quota/Keys)
                    with st.status("🔄 Core Link Unstable. Rerouting via Neural Relay...", expanded=False):
                        full_response = get_neural_fallback(user_msg)
                        message_placeholder.markdown(f'<div class="neural-relay-box">⚡ [DIAGNOSTIC] {full_response}</div>', unsafe_allow_html=True)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            save_message(st.session_state.current_chat_id, "assistant", full_response)
            st.rerun()

elif st.session_state.active_view == "Deep Search":
    st.markdown("""
        <div class="search-hub-header">
            <h2 style='text-align: center; color: #8B5CF6; font-family: "Space Grotesk", sans-serif;'>NEURAL EXTRACTION ENGINE</h2>
            <p style='text-align: center; color: #94A3B8; font-size: 0.9rem;'>Access the infinite web through dot.ai's deep grounding layer.</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input("Enter your research query...", placeholder="Ex: Latest breakthroughs in quantum computing...", key="deep_tab_search")
    with col2:
        search_btn = st.button("🔍 Analyze Web", use_container_width=True)

    if search_btn and query:
        with st.status("🔍 Extracting neural data...", expanded=True):
            search_context = perform_web_search(query)
            if search_context:
                st.session_state.deep_search_results = st.session_state.last_search_results
                st.session_state.deep_search_query = query
                save_search_result(query, st.session_state.last_search_results)
                st.success("Extraction Complete.")
            else:
                st.error("No data found for this query.")
    
    if st.session_state.deep_search_results:
        st.markdown(f"""
            <div style='margin-bottom: 30px; border-left: 4px solid var(--accent-violet); padding-left: 20px;'>
                <h3 style='margin:0; font-family: "Space Grotesk", sans-serif; letter-spacing: 1px;'>📊 NEURAL DOSSIER</h3>
                <p style='color: var(--text-muted); font-size: 0.9rem;'>Intelligence report for: <i>{st.session_state.deep_search_query}</i></p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('''
            <a href="/Search_Results" target="_blank" style="text-decoration: none; width: 100%; display: block; margin-bottom: 30px;">
                <button style="width: 100%; height: 50px; background: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%); color: white; border: none; border-radius: 12px; font-family: 'Space Grotesk', sans-serif; font-size: 1rem; font-weight: 700; cursor: pointer; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); box-shadow: 0 10px 30px rgba(139, 92, 246, 0.3); letter-spacing: 1px;">
                    🚀 OPEN INTELLIGENCE DOSSIER (STANDALONE)
                </button>
            </a>
        ''', unsafe_allow_html=True)
        
        for r in st.session_state.deep_search_results:
            st.markdown(f"""
                <div class="neural-dossier-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px;">
                        <span style="font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #fff; font-size: 1.1rem;">{r['title']}</span>
                        <a href="{r['href']}" target="_blank" style="text-decoration: none; color: var(--accent-cyan); font-weight: 600; font-size: 0.8rem; border: 1px solid var(--accent-cyan); padding: 4px 10px; border-radius: 6px; transition: all 0.3s;">SOURCE ↗</a>
                    </div>
                    <p style="color: var(--text-muted); font-size: 1rem; line-height: 1.7; margin-bottom: 0;">{r['body']}</p>
                    <div style="margin-top: 15px; display: flex; gap: 10px;">
                        <span style="font-size: 0.7rem; background: rgba(139, 92, 246, 0.1); color: var(--accent-violet); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(139, 92, 246, 0.2);">VERIFIED DATA</span>
                        <span style="font-size: 0.7rem; background: rgba(6, 182, 212, 0.1); color: var(--accent-cyan); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(6, 182, 212, 0.2);">NEURAL EXTRACT</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

 

