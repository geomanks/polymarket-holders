"""
Polymarket Whale Tracker - SIMPLE & CLEAN VERSION
"""

import streamlit as st
import requests
import re
import time
import pandas as pd
from typing import Optional, List, Dict

# ===== PAGE SETUP =====
st.set_page_config(page_title="Polymarket Whale Tracker", page_icon="🐋", layout="wide")

# ===== SIMPLE STYLING =====
st.markdown("""
<style>
    .main { background: white; }
    h1, h2, h3 { color: #000 !important; }
    .stAlert { font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

st.title("🐋 Polymarket Whale Tracker")
st.write("**See who's winning and who's losing in any market**")
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

# ===== MAIN APP =====

url = st.text_input("**📋 Paste Polymarket URL:**", placeholder="https://polymarket.com/event/...")

if url:
    slug = extract_slug(url)
    if not slug:
        st.error("❌ Invalid URL")
        st.stop()
    
    with st.spinner("Loading market..."):
        market_data = fetch_market_data(slug)
    
    st.success(f"**Market:** {market_data.get('title')}")
    
    markets = [m for m in market_data.get('markets', []) if m.get('enableOrderBook')]
    if not markets:
        st.error("No yes/no markets found")
        st.stop()
    
    if len(markets) > 1:
        options = [m.get('question', f'Market {i}') for i, m in enumerate(markets, 1)]
        idx = st.selectbox("**Select market:**", range(len(options)), format_func=lambda x: options[x])
        selected = markets[idx]
    else:
        selected = markets[0]
    
    st.info(f"**📊 {selected.get('question')}**")
    
    if st.button("🔍 **ANALYZE**", type="primary", use_container_width=True):
        condition_id = selected.get('conditionId')
        holders_data = fetch_holders(condition_id)
        
        yes_raw, no_raw = [], []
        for outcome in holders_data:
            holders = outcome.get('holders', [])
            if holders:
                if holders[0].get('outcomeIndex') == 0:
                    yes_raw = holders[:15]
                else:
                    no_raw = holders[1:16]
        
        # YES HOLDERS
        st.header("📈 YES Holders")
        progress = st.progress(0)
        yes_data = []
        for i, h in enumerate(yes_raw):
            enriched = enrich_holder(h, condition_id)
            if enriched:
                yes_data.append(enriched)
            progress.progress((i+1)/len(yes_raw))
            time.sleep(0.15)
        progress.empty()
        
        if yes_data:
            df = pd.DataFrame(yes_data)
            
            # Show table
            st.dataframe(
                df.style.format({
                    'Shares': '{:,}',
                    'Entry': '${:.3f}',
                    'Current': '${:.3f}',
                    'Value': '${:,}',
                    'Market P&L': '${:,}',
                    'All-Time P&L': lambda x: f'${x:,}' if pd.notna(x) else 'N/A'
                }),
                use_container_width=True,
                hide_index=True
            )
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            avg_pnl = df['All-Time P&L'].mean()
            col1.metric("**Avg All-Time P&L**", f"${avg_pnl:,.0f}" if pd.notna(avg_pnl) else "N/A")
            col2.metric("**Total Value**", f"${df['Value'].sum():,}")
            col3.metric("**Avg Entry**", f"${(df['Shares']*df['Entry']).sum()/df['Shares'].sum():.3f}")
        
        st.divider()
        
        # NO HOLDERS
        st.header("📉 NO Holders")
        progress = st.progress(0)
        no_data = []
        for i, h in enumerate(no_raw):
            enriched = enrich_holder(h, condition_id)
            if enriched:
                no_data.append(enriched)
            progress.progress((i+1)/len(no_raw))
            time.sleep(0.15)
        progress.empty()
        
        if no_data:
            df = pd.DataFrame(no_data)
            
            # Show table
            st.dataframe(
                df.style.format({
                    'Shares': '{:,}',
                    'Entry': '${:.3f}',
                    'Current': '${:.3f}',
                    'Value': '${:,}',
                    'Market P&L': '${:,}',
                    'All-Time P&L': lambda x: f'${x:,}' if pd.notna(x) else 'N/A'
                }),
                use_container_width=True,
                hide_index=True
            )
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            avg_pnl = df['All-Time P&L'].mean()
            col1.metric("**Avg All-Time P&L**", f"${avg_pnl:,.0f}" if pd.notna(avg_pnl) else "N/A")
            col2.metric("**Total Value**", f"${df['Value'].sum():,}")
            col3.metric("**Avg Entry**", f"${(df['Shares']*df['Entry']).sum()/df['Shares'].sum():.3f}")
        
        st.success("✅ Done!")

st.divider()
st.caption("🐋 Track the whales • [GitHub](https://github.com/geomanks/polymarket-holders)")
