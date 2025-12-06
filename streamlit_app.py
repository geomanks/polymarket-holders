"""
Polymarket Top Holders Analysis - Professional Edition
"""

import streamlit as st
import requests
import re
import time
import pandas as pd
from typing import Optional, List, Dict
import urllib.parse

# ===== PAGE SETUP =====
st.set_page_config(
    page_title="Polymarket Holders Analysis", 
    page_icon="📊", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ===== PROFESSIONAL STYLING =====
st.markdown("""
<style>
    /* Import Professional Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styling */
    .main { 
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
        color: #e4e7eb;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Remove Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Typography Hierarchy */
    h1 { 
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 2.5rem !important;
        letter-spacing: -1px !important;
        margin-bottom: 0.5rem !important;
    }
    
    h2 { 
        color: #f0f2f5 !important;
        font-weight: 600 !important;
        font-size: 1.75rem !important;
        letter-spacing: -0.5px !important;
        margin-top: 2rem !important;
    }
    
    h3 { 
        color: #d1d5db !important;
        font-weight: 600 !important;
        font-size: 1.25rem !important;
        margin-top: 1.5rem !important;
    }
    
    /* Subtitle/Description */
    .subtitle {
        color: #9ca3af;
        font-size: 1.1rem;
        font-weight: 400;
        margin-bottom: 2rem;
        line-height: 1.6;
    }
    
    /* Card Containers */
    .card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* Input Fields */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        font-size: 0.95rem !important;
        padding: 0.75rem !important;
        transition: all 0.2s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
    }
    
    .stTextInput label, .stSelectbox label {
        color: #d1d5db !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    /* Primary Button */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.75rem 2rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4) !important;
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: #d1d5db !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        font-weight: 500 !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease !important;
    }
    
    .stDownloadButton > button:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
    }
    
    /* Alert Boxes */
    .stAlert {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        color: #e4e7eb !important;
    }
    
    div[data-baseweb="notification"] > div {
        background: rgba(99, 102, 241, 0.1) !important;
        border-left: 4px solid #6366f1 !important;
    }
    
    /* Success Messages */
    .element-container:has(> .stAlert[data-baseweb="notification"]) {
        background: rgba(16, 185, 129, 0.1) !important;
        border-left: 4px solid #10b981 !important;
    }
    
    /* Warning Messages */
    .stWarning {
        background: rgba(245, 158, 11, 0.1) !important;
        border-left: 4px solid #f59e0b !important;
    }
    
    /* Error Messages */
    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border-left: 4px solid #ef4444 !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #ffffff !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #9ca3af !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }
    
    /* DataFrames */
    .stDataFrame {
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    
    .stDataFrame [data-testid="stDataFrameResizable"] {
        background: rgba(255, 255, 255, 0.02) !important;
    }
    
    /* Table Headers */
    .stDataFrame thead tr th {
        background: rgba(99, 102, 241, 0.15) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.5px !important;
        padding: 1rem !important;
        border-bottom: 2px solid rgba(99, 102, 241, 0.3) !important;
    }
    
    /* Table Rows */
    .stDataFrame tbody tr {
        border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    .stDataFrame tbody tr:hover {
        background: rgba(255, 255, 255, 0.03) !important;
    }
    
    .stDataFrame tbody tr td {
        padding: 0.75rem 1rem !important;
        color: #e4e7eb !important;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%) !important;
    }
    
    /* Divider */
    hr {
        border-color: rgba(255, 255, 255, 0.1) !important;
        margin: 2rem 0 !important;
    }
    
    /* P&L Styling */
    .positive { 
        color: #10b981 !important; 
        font-weight: 600 !important; 
    }
    
    .negative { 
        color: #ef4444 !important; 
        font-weight: 600 !important; 
    }
    
    .neutral { 
        color: #9ca3af !important; 
    }
    
    /* Section Headers */
    .section-header {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
        border-left: 4px solid #6366f1;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 2rem 0 1rem 0;
    }
    
    /* Link Button (Twitter) */
    .stLinkButton > a {
        background: linear-gradient(135deg, #1da1f2 0%, #0c8bd9 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        text-decoration: none !important;
        display: inline-block !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(29, 161, 242, 0.3) !important;
    }
    
    .stLinkButton > a:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(29, 161, 242, 0.4) !important;
    }
    
    /* Code blocks (for tweet preview) */
    .stCodeBlock {
        background: rgba(0, 0, 0, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }
    
    /* Columns spacing */
    [data-testid="column"] {
        padding: 0 0.5rem !important;
    }
    
    /* Caption/Footer */
    .stCaption {
        color: #6b7280 !important;
        font-size: 0.85rem !important;
    }
    
</style>
""", unsafe_allow_html=True)

# ===== HEADER =====
st.markdown('<h1>📊 Polymarket Holdings Analysis</h1>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Track and analyze the top traders in any Polymarket prediction market. Identify smart money patterns and profitable positions.</div>', unsafe_allow_html=True)
st.divider()

# ===== CORE FUNCTIONS =====

def extract_slug(url: str) -> Optional[str]:
    match = re.search(r'polymarket\.com/event/([^?#/]+)', url)
    return match.group(1) if match else None

def fetch_market_data(slug: str):
    url = f"https://gamma-api.polymarket.com/events?slug={slug}"
    return requests.get(url).json()[0]

def fetch_holders(condition_id: str):
    url = f"https://data-api.polymarket.com/holders?market={condition_id}&limit=20&sort=shares&order=desc"
    return requests.get(url).json()

def fetch_user_positions(wallet: str, condition_id: str):
    url = f"https://data-api.polymarket.com/positions?user={wallet}&market={condition_id}"
    try:
        return requests.get(url, timeout=5).json()
    except:
        return []

def fetch_profit_leaderboard(wallet: str) -> Optional[float]:
    try:
        data = requests.get(f"https://lb-api.polymarket.com/profit?user={wallet}", timeout=5).json()
        return float(data.get('profit')) if data and 'profit' in data else None
    except:
        return None

def scrape_pnl(wallet: str) -> Optional[float]:
    try:
        html = requests.get(f"https://polymarket.com/profile/{wallet}", timeout=10).text
        
        # Strategy 1: Look for Profit/Loss
        match = re.search(r'Profit/Loss[^$]*?([\u2212\-])?\s*\$\s*([\d,]+\.[\d]{2})', html)
        if match:
            sign, number = match.groups()
            value = float(number.replace(',', ''))
            return -value if sign in ['\u2212', '-'] else value
        
        # Strategy 2: Context
        sections = html.split('Profit/Loss')
        if len(sections) > 1:
            section = sections[1][:600]
            is_neg = any(x in section.lower() for x in ['text-red', 'negative', 'loss'])
            is_neg = is_neg or '\u2212' in section[:100] or re.search(r'-\s*\$', section[:100])
            match = re.search(r'\$\s*([\d,]+\.[\d]{2})', section)
            if match:
                value = float(match.group(1).replace(',', ''))
                return -value if is_neg else value
        return None
    except:
        return None

def get_pnl(wallet: str) -> Optional[float]:
    pnl = fetch_profit_leaderboard(wallet)
    return pnl if pnl is not None else scrape_pnl(wallet)

def enrich_holder(holder: dict, condition_id: str) -> dict:
    wallet = holder.get('proxyWallet')
    if not wallet:
        return None
    
    positions = fetch_user_positions(wallet, condition_id)
    outcome_index = holder.get('outcomeIndex', 0)
    
    position = next((p for p in positions if p.get('outcomeIndex') == outcome_index), None)
    if not position:
        return None
    
    shares = float(position.get('size', 0))
    avg_price = float(position.get('avgPrice', 0))
    current_price = float(position.get('curPrice', 0))
    current_value = float(position.get('currentValue', 0))
    initial_value = float(position.get('initialValue', 0))
    
    return {
        'Name': holder.get('name') or wallet[:10],
        'Shares': int(shares),
        'Entry': avg_price,
        'Current': current_price,
        'Value': int(current_value),
        'Market P&L': int(current_value - initial_value),
        'All-Time P&L': get_pnl(wallet)
    }

# ===== FORMATTING FUNCTIONS =====

def format_pnl_style(val):
    """Applies CSS class for P&L based on value."""
    if pd.isna(val):
        return 'color: #6b7280'
    if val > 0:
        return 'color: #10b981; font-weight: 600'
    elif val < 0:
        return 'color: #ef4444; font-weight: 600'
    else:
        return 'color: #9ca3af'

def format_pnl(val):
    """Format P&L values with proper sign and color."""
    if pd.isna(val):
        return "N/A"
    return f"${val:,.0f}"

def format_currency(val):
    """Format currency values."""
    if pd.isna(val):
        return "N/A"
    return f"${val:,.0f}"

def format_price(val):
    """Format price values with 3 decimal places."""
    if pd.isna(val):
        return "N/A"
    return f"${val:.3f}"

def format_shares(val):
    """Format share counts."""
    if pd.isna(val):
        return "N/A"
    return f"{int(val):,}"

def display_results(df: pd.DataFrame, title: str, emoji: str):
    """Display analysis results with modern styling."""
    st.markdown(f'<div class="section-header"><h2>{emoji} {title}</h2></div>', unsafe_allow_html=True)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_capital = df['Value'].sum()
    total_shares = df['Shares'].sum()
    avg_pnl = df['All-Time P&L'].mean()
    weighted_entry = (df['Shares'] * df['Entry']).sum() / total_shares if total_shares > 0 else 0
    
    with col1:
        st.metric("Total Capital", f"${total_capital:,}")
    with col2:
        st.metric("Total Shares", f"{total_shares:,}")
    with col3:
        pnl_str = f"${avg_pnl:,.0f}" if pd.notna(avg_pnl) else "N/A"
        pnl_delta = f"{avg_pnl:+,.0f}" if pd.notna(avg_pnl) else None
        st.metric("Avg All-Time P&L", pnl_str, delta=pnl_delta)
    with col4:
        st.metric("Weighted Entry", f"${weighted_entry:.3f}")
    
    st.markdown("###")
    
    # Styled dataframe
    styled_df = df.style.format({
        'Shares': format_shares,
        'Entry': format_price,
        'Current': format_price,
        'Value': format_currency,
        'Market P&L': format_pnl,
        'All-Time P&L': format_pnl
    }).applymap(format_pnl_style, subset=['Market P&L', 'All-Time P&L'])
    
    st.dataframe(styled_df, use_container_width=True, height=600)

# ===== MAIN APPLICATION =====

# Market selection
col1, col2 = st.columns([3, 1])

with col1:
    url = st.text_input(
        "POLYMARKET EVENT URL",
        placeholder="https://polymarket.com/event/...",
        help="Paste the full URL of any Polymarket event"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🔍 ANALYZE", use_container_width=True)

# Analysis logic
if analyze_btn:
    if not url:
        st.error("⚠️ Please enter a Polymarket event URL")
    else:
        slug = extract_slug(url)
        if not slug:
            st.error("❌ Invalid URL format. Please use a valid Polymarket event URL.")
        else:
            with st.spinner("Loading market data..."):
                try:
                    market_data = fetch_market_data(slug)
                except Exception as e:
                    st.error(f"❌ Failed to fetch market data: {str(e)}")
                    st.stop()
            
            st.success(f"✅ Market loaded: **{market_data.get('title')}**")
            
            markets = market_data.get('markets', [])
            if len(markets) == 0:
                st.error("No markets found for this event.")
                st.stop()
            
            if len(markets) > 1:
                st.info(f"This event has {len(markets)} sub-markets. Select one below:")
                market_options = {m.get('question', f"Market {i}"): m for i, m in enumerate(markets)}
                selected_question = st.selectbox("Select Market", options=list(market_options.keys()))
                selected = market_options[selected_question]
            else:
                selected = markets[0]
            
            condition_id = selected.get('conditionId')
            st.info(f"**Question:** {selected.get('question', 'N/A')}")
            
            st.markdown("##")
            st.divider()
            
            # YES HOLDERS
            st.markdown('<div class="section-header"><h2>🟢 Analyzing YES Holders...</h2></div>', unsafe_allow_html=True)
            
            yes_raw = fetch_holders(condition_id)
            yes_data = []
            total_yes = len(yes_raw)
            
            progress_container = st.empty()
            status_container = st.empty()
            
            for i, h in enumerate(yes_raw):
                holder_name = h.get('name') or h.get('proxyWallet', 'Unknown')[:10]
                status_container.info(f"📊 Analyzing: **{holder_name}** ({i+1}/{total_yes})")
                
                percentage = int(((i + 1) / total_yes) * 100)
                progress_container.progress((i+1)/total_yes, text=f"Progress: {percentage}% - Fetching position data & all-time P&L...")
                
                enriched = enrich_holder(h, condition_id)
                if enriched:
                    yes_data.append(enriched)
                time.sleep(0.15)
            
            progress_container.empty()
            status_container.empty()
            
            if yes_data:
                df_yes = pd.DataFrame(yes_data)
                display_results(df_yes, "YES Holders (Top 15)", "🟢")
                
                csv_yes = df_yes.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download YES Holders CSV",
                    data=csv_yes,
                    file_name=f"polymarket_yes_holders_{slug}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("No significant YES holders found.")
            
            # NO HOLDERS
            st.markdown("##")
            st.markdown("---")
            st.markdown('<div class="section-header"><h2>🔴 Analyzing NO Holders...</h2></div>', unsafe_allow_html=True)
            
            no_raw = fetch_holders(condition_id)
            no_data = []
            total_no = len(no_raw)
            
            progress_container = st.empty()
            status_container = st.empty()
            
            for i, h in enumerate(no_raw):
                holder_name = h.get('name') or h.get('proxyWallet', 'Unknown')[:10]
                status_container.info(f"📊 Analyzing: **{holder_name}** ({i+1}/{total_no})")
                
                percentage = int(((i + 1) / total_no) * 100)
                progress_container.progress((i+1)/total_no, text=f"Progress: {percentage}% - Fetching position data & all-time P&L...")
                
                enriched = enrich_holder(h, condition_id)
                if enriched:
                    no_data.append(enriched)
                time.sleep(0.15)
            
            progress_container.empty()
            status_container.empty()
            
            if no_data:
                df_no = pd.DataFrame(no_data)
                display_results(df_no, "NO Holders (Top 15)", "🔴")
                
                csv_no = df_no.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download NO Holders CSV",
                    data=csv_no,
                    file_name=f"polymarket_no_holders_{slug}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("No significant NO holders found.")

            st.markdown("---")
            st.success("✅ Analysis Complete!")
            
            # Store data in session state
            st.session_state['analysis_yes_data'] = yes_data
            st.session_state['analysis_no_data'] = no_data
            st.session_state['analysis_slug'] = slug
            st.session_state['analysis_market_title'] = market_data.get('title')
            
            # ===== COMPARISON SECTION =====
            if yes_data and no_data:
                st.markdown("##")
                st.markdown("---")
                st.markdown('<div class="section-header"><h2>⚖️ YES vs NO Comparison</h2></div>', unsafe_allow_html=True)
                
                df_yes = pd.DataFrame(yes_data)
                df_no = pd.DataFrame(no_data)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 🟢 YES Side")
                    yes_avg_pnl = df_yes['All-Time P&L'].mean()
                    yes_total_value = df_yes['Value'].sum()
                    yes_total_shares = df_yes['Shares'].sum()
                    yes_avg_entry = (df_yes['Shares'] * df_yes['Entry']).sum() / yes_total_shares if yes_total_shares > 0 else 0
                    
                    st.metric("Avg All-Time P&L", f"${yes_avg_pnl:,.0f}" if pd.notna(yes_avg_pnl) else "N/A")
                    st.metric("Total Capital", f"${yes_total_value:,}")
                    st.metric("Total Shares", f"{yes_total_shares:,}")
                    st.metric("Avg Entry Price", f"${yes_avg_entry:.3f}")
                    
                    profitable_yes = len(df_yes[df_yes['All-Time P&L'] > 0])
                    total_yes = len(df_yes[df_yes['All-Time P&L'].notna()])
                    if total_yes > 0:
                        win_rate = (profitable_yes / total_yes) * 100
                        st.metric("Profitable Traders", f"{profitable_yes}/{total_yes} ({win_rate:.0f}%)")
                
                with col2:
                    st.markdown("### 🔴 NO Side")
                    no_avg_pnl = df_no['All-Time P&L'].mean()
                    no_total_value = df_no['Value'].sum()
                    no_total_shares = df_no['Shares'].sum()
                    no_avg_entry = (df_no['Shares'] * df_no['Entry']).sum() / no_total_shares if no_total_shares > 0 else 0
                    
                    st.metric("Avg All-Time P&L", f"${no_avg_pnl:,.0f}" if pd.notna(no_avg_pnl) else "N/A")
                    st.metric("Total Capital", f"${no_total_value:,}")
                    st.metric("Total Shares", f"{no_total_shares:,}")
                    st.metric("Avg Entry Price", f"${no_avg_entry:.3f}")
                    
                    profitable_no = len(df_no[df_no['All-Time P&L'] > 0])
                    total_no = len(df_no[df_no['All-Time P&L'].notna()])
                    if total_no > 0:
                        win_rate = (profitable_no / total_no) * 100
                        st.metric("Profitable Traders", f"{profitable_no}/{total_no} ({win_rate:.0f}%)")
                
                # Smart money verdict
                st.markdown("###")
                if pd.notna(yes_avg_pnl) and pd.notna(no_avg_pnl):
                    if yes_avg_pnl > no_avg_pnl:
                        diff = yes_avg_pnl - no_avg_pnl
                        st.info(f"💡 **Smart Money Indicator:** YES holders are more profitable on average (+${diff:,.0f} vs NO)")
                    elif no_avg_pnl > yes_avg_pnl:
                        diff = no_avg_pnl - yes_avg_pnl
                        st.info(f"💡 **Smart Money Indicator:** NO holders are more profitable on average (+${diff:,.0f} vs YES)")
                    else:
                        st.info("💡 **Smart Money Indicator:** Both sides have equally profitable traders")
                
                # ===== TWITTER SHARE SECTION =====
                st.markdown("##")
                st.markdown("---")
                st.markdown('<div class="section-header"><h2>🐦 Share on Twitter</h2></div>', unsafe_allow_html=True)
                
                market_title_short = market_data.get('title')[:60] + "..." if len(market_data.get('title')) > 60 else market_data.get('title')
                
                # Determine smart money verdict
                if pd.notna(yes_avg_pnl) and pd.notna(no_avg_pnl):
                    if yes_avg_pnl > no_avg_pnl:
                        diff = yes_avg_pnl - no_avg_pnl
                        verdict = f"YES holders +${diff:,.0f} more profitable"
                        winner_emoji = "🟢"
                    elif no_avg_pnl > yes_avg_pnl:
                        diff = no_avg_pnl - yes_avg_pnl
                        verdict = f"NO holders +${diff:,.0f} more profitable"
                        winner_emoji = "🔴"
                    else:
                        verdict = "Both sides equally profitable"
                        winner_emoji = "⚖️"
                else:
                    verdict = "Insufficient data"
                    winner_emoji = "❓"
                
                yes_pnl_str = f"${yes_avg_pnl:,.0f}" if pd.notna(yes_avg_pnl) else "N/A"
                no_pnl_str = f"${no_avg_pnl:,.0f}" if pd.notna(no_avg_pnl) else "N/A"
                yes_winners_str = f"{profitable_yes}/{total_yes} ({(profitable_yes/total_yes*100):.0f}%)" if total_yes > 0 else "N/A"
                no_winners_str = f"{profitable_no}/{total_no} ({(profitable_no/total_no*100):.0f}%)" if total_no > 0 else "N/A"
                
                # Shorten the URL
                full_url = f"https://polymarket-holders.streamlit.app/"
                try:
                    response = requests.get(f"https://tinyurl.com/api-create.php?url={full_url}", timeout=3)
                    short_url = response.text if response.status_code == 200 else full_url
                except:
                    short_url = full_url
                
                tweet_text = f"""
{market_title_short} @polymarket
{selected.get('question', '')}
TOP 15 HOLDERS
🟢YES Side:
├ Avg P&L: {yes_pnl_str}
├ Capital: ${yes_total_value:,}
🔴NO Side:
├ Avg P&L: {no_pnl_str}
├ Capital: ${no_total_value:,}
🔗 {short_url}
"""
                
                st.markdown("### 📝 Your Tweet (Ready to Post!)")
                st.code(tweet_text, language=None)
                
                twitter_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(tweet_text)}"
                
                st.link_button("🐦 Post to Twitter", twitter_url, use_container_width=True, type="primary")
                
                st.success("✅ Click the button above - your tweet is ready! Twitter will open with this text pre-filled.")

# ===== FOOTER =====
st.markdown("---")
st.caption("Professional analysis tool for Polymarket prediction markets. Data sourced via official Polymarket APIs.")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("[![Star on GitHub](https://img.shields.io/github/stars/geomanks/polymarket-holders?style=social)](https://github.com/geomanks/polymarket-holders)")
with col2:
    st.markdown("[![Twitter](https://img.shields.io/twitter/url?style=social&url=https%3A%2F%2Fgithub.com%2Fgeomanks%2Fpolymarket-holders)](https://twitter.com/intent/tweet?text=Check%20out%20this%20Polymarket%20Analysis%20Tool!&url=https://polymarket-holders.streamlit.app)")
with col3:
    st.markdown("**Built for the Polymarket community**")
