"""
Polymarket Top Holders Analysis - Streamlit Web App
Analyze top YES/NO holders and their all-time P&L
"""

import streamlit as st
import requests
import json
import re
import time
from typing import List, Dict, Optional
import pandas as pd

# Page config
st.set_page_config(
    page_title="Polymarket Whale Tracker",
    page_icon="🐋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    /* Main header */
    .main-header {
        text-align: center;
        padding: 3rem 1rem;
        background: #1a1a2e;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 3.5rem;
        margin: 0;
        font-weight: 800;
        letter-spacing: -1px;
    }
    .main-header p {
        color: #ffffff;
        font-size: 1.3rem;
        margin-top: 1rem;
        font-weight: 600;
        opacity: 0.95;
    }
    
    /* Metric cards */
    .metric-card {
        background: #ffffff;
        padding: 2rem;
        border-radius: 12px;
        border: 3px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .metric-card p:first-child {
        color: #424242;
        font-size: 1rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    .metric-card p:last-child {
        color: #000000;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
    }
    
    /* Success (green) */
    .success-metric {
        background: #e8f5e9;
        border: 3px solid #4caf50;
    }
    .success-metric p:first-child {
        color: #1b5e20;
    }
    .success-metric p:last-child {
        color: #2e7d32;
    }
    
    /* Danger (yellow/red) */
    .danger-metric {
        background: #fff3e0;
        border: 3px solid #ff9800;
    }
    .danger-metric p:first-child {
        color: #e65100;
    }
    .danger-metric p:last-child {
        color: #f57c00;
    }
    
    /* Info boxes */
    .info-box {
        background: #e3f2fd;
        padding: 1.5rem;
        border-radius: 10px;
        border: 3px solid #1976d2;
        margin: 1.5rem 0;
    }
    .info-box h3 {
        color: #0d47a1;
        font-weight: 700;
        font-size: 1.4rem;
    }
    
    /* Selected market box */
    .selected-market {
        background: #f3e5f5;
        padding: 1.5rem;
        border-radius: 10px;
        border: 3px solid #9c27b0;
        margin: 1.5rem 0;
    }
    .selected-market h4 {
        color: #4a148c;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        font-size: 1.1rem;
    }
    .selected-market p {
        color: #000000;
        font-size: 1.2rem;
        font-weight: 600;
        margin: 0;
    }
    
    /* Buttons */
    .stButton > button {
        font-size: 1.2rem;
        font-weight: 700;
        padding: 1rem 3rem;
        background: #1976d2;
        color: white;
        border: none;
        border-radius: 8px;
    }
    .stButton > button:hover {
        background: #1565c0;
        border: none;
    }
    
    /* Section headers */
    h3 {
        color: #000000;
        font-weight: 800;
        font-size: 1.8rem;
        margin-top: 2rem;
    }
    
    /* Make all text darker and bolder */
    p, span, div {
        color: #212121;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🐋 Polymarket Whale Tracker</h1>
    <p>Analyze top holders and their all-time P&L across all markets</p>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# CORE FUNCTIONS (from your script)
# =============================================================================

def extract_slug(url: str) -> Optional[str]:
    """Extract the event slug from a Polymarket URL"""
    match = re.search(r'polymarket\.com/event/([^?#/]+)', url)
    return match.group(1) if match else None


def fetch_market_data(slug: str) -> Dict:
    """Fetch market data from Polymarket Gamma API"""
    url = f"https://gamma-api.polymarket.com/events?slug={slug}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    if not data or len(data) == 0:
        raise Exception("No market data found for this slug")
    
    return data[0]


def fetch_holders(condition_id: str, limit: int = 20) -> List[Dict]:
    """Fetch top holders for a given condition ID"""
    url = f"https://data-api.polymarket.com/holders?market={condition_id}&limit={limit}&sort=shares&order=desc"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def fetch_user_positions(wallet_address: str, condition_id: str) -> List[Dict]:
    """Fetch user's positions for a specific market"""
    url = f"https://data-api.polymarket.com/positions?user={wallet_address}&market={condition_id}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except:
        return []


def fetch_user_activity(wallet_address: str, condition_id: str, limit: int = 100) -> List[Dict]:
    """Fetch user's trading activity"""
    url = f"https://data-api.polymarket.com/activity?user={wallet_address}&market={condition_id}&limit={limit}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except:
        return []


def fetch_profit_from_leaderboard(wallet_address: str) -> Optional[float]:
    """Get P&L from leaderboard API (only works for top 50 profitable traders)"""
    url = f"https://lb-api.polymarket.com/profit?user={wallet_address}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and 'profit' in data:
                return float(data['profit'])
    except:
        pass
    return None


def scrape_user_profit_from_profile(wallet_address: str) -> Optional[float]:
    """Scrape all-time P&L from user's profile page"""
    profile_url = f"https://polymarket.com/profile/{wallet_address}"
    
    try:
        response = requests.get(profile_url, timeout=10)
        if response.status_code != 200:
            return None
        
        html = response.text
        
        # Strategy 1: Look for "Profit/Loss" with explicit sign detection
        patterns = [
            r'Profit/Loss[^$]*?([\u2212\-])?\s*\$\s*([\d,]+\.[\d]{2})',
            r'data-pnl\s*=\s*["\']+([\u2212\-]?[\d,]+\.?\d*)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                groups = match.groups()
                
                if len(groups) == 2:
                    sign, number = groups
                    value = float(number.replace(',', ''))
                    if sign and sign in ['\u2212', '-']:
                        return -value
                    else:
                        return value
        
        # Strategy 2: Context-based detection
        sections = html.split('Profit/Loss')
        if len(sections) > 1:
            pnl_section = sections[1][:600]
            is_negative = False
            
            negative_classes = ['text-red', 'text-danger', 'negative', 'loss']
            if any(cls in pnl_section.lower() for cls in negative_classes):
                is_negative = True
            
            if '\u2212' in pnl_section[:100] or re.search(r'-\s*\$', pnl_section[:100]):
                is_negative = True
            
            amount_match = re.search(r'\$\s*([\d,]+\.[\d]{2})', pnl_section)
            if amount_match:
                value = float(amount_match.group(1).replace(',', ''))
                return -value if is_negative else value
        
        return None
        
    except Exception as e:
        return None


def get_total_pnl(wallet_address: str) -> Optional[float]:
    """Get all-time P&L (API first, then scraping)"""
    # Try API first
    pnl = fetch_profit_from_leaderboard(wallet_address)
    if pnl is not None:
        return pnl
    
    # Fall back to scraping
    return scrape_user_profit_from_profile(wallet_address)


def calculate_position_details(wallet_address: str, condition_id: str, outcome_index: int) -> Dict:
    """Calculate detailed position information"""
    positions = fetch_user_positions(wallet_address, condition_id)
    
    position = None
    for pos in positions:
        if pos.get('outcomeIndex') == outcome_index:
            position = pos
            break
    
    if not position:
        return {
            'shares': 0,
            'avg_price': 0,
            'current_price': 0,
            'current_value': 0,
            'pnl_cash': 0,
        }
    
    shares = float(position.get('size', 0))
    avg_price = float(position.get('avgPrice', 0))
    current_price = float(position.get('curPrice', 0))
    current_value = float(position.get('currentValue', 0))
    initial_value = float(position.get('initialValue', 0))
    
    return {
        'shares': shares,
        'avg_price': avg_price,
        'current_price': current_price,
        'current_value': current_value,
        'pnl_cash': current_value - initial_value,
    }


def enrich_holder_with_position(holder: Dict, condition_id: str) -> Dict:
    """Enrich holder data with position info"""
    wallet = holder.get('proxyWallet')
    outcome_index = holder.get('outcomeIndex', 0)
    
    if not wallet:
        return holder
    
    position_details = calculate_position_details(wallet, condition_id, outcome_index)
    
    # Get activity
    activities = fetch_user_activity(wallet, condition_id)
    buys = sum(1 for a in activities if a.get('side') == 'BUY')
    sells = sum(1 for a in activities if a.get('side') == 'SELL')
    volume = sum(float(a.get('size', 0)) for a in activities)
    
    # Get all-time P&L
    total_pnl = get_total_pnl(wallet)
    
    return {
        'wallet': wallet,
        'name': holder.get('name') or wallet[:8],
        'shares': position_details['shares'],
        'avg_price': position_details['avg_price'],
        'current_price': position_details['current_price'],
        'current_value': position_details['current_value'],
        'market_pnl': position_details['pnl_cash'],
        'total_pnl': total_pnl,
        'buys': buys,
        'sells': sells,
        'volume': volume,
    }


# =============================================================================
# STREAMLIT APP
# =============================================================================

# Input section
st.markdown("### 🔗 Enter Market URL")
col1, col2 = st.columns([4, 1])
with col1:
    url = st.text_input(
        "Polymarket URL", 
        placeholder="https://polymarket.com/event/your-market-here",
        label_visibility="collapsed"
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    
st.markdown("---")

if url:
    try:
        # Extract slug
        slug = extract_slug(url)
        if not slug:
            st.error("Invalid Polymarket URL")
            st.stop()
        
        with st.spinner("Fetching market data..."):
            market_data = fetch_market_data(slug)
        
        market_title = market_data.get('title', 'Unknown')
        st.markdown(f"""
        <div class="info-box">
            <h3 style="margin:0; color:#1976d2;">📊 {market_title}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        markets = market_data.get('markets', [])
        
        # Filter for yes/no markets
        yes_no_markets = [m for m in markets if m.get('enableOrderBook', False)]
        
        if not yes_no_markets:
            st.error("No yes/no markets found")
            st.stop()
        
        # Handle multiple markets - show selection FIRST
        selected_index = 0
        if len(yes_no_markets) > 1:
            st.markdown("#### 🎯 Multiple Markets Found")
            st.info(f"This event has {len(yes_no_markets)} different markets. Select the one you want to analyze:")
            options = [m.get('question', f'Market {i}') for i, m in enumerate(yes_no_markets, 1)]
            selected_index = st.selectbox("Choose market:", range(len(options)), format_func=lambda x: options[x], key="market_selector")
        
        selected_market = yes_no_markets[selected_index]
        condition_id = selected_market.get('conditionId')
        question = selected_market.get('question', 'Unknown')
        
        st.markdown(f"""
        <div class="selected-market">
            <h4>🎲 SELECTED MARKET</h4>
            <p>{question}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # NOW show the analyze button
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_clicked = st.button("🔍 Analyze This Market", type="primary", use_container_width=True, key="analyze_btn")
        
        if analyze_clicked:
            
            # Fetch holders
            with st.spinner("Fetching holders..."):
                holders_data = fetch_holders(condition_id)
            
            # Process YES and NO holders
            yes_holders_raw = []
            no_holders_raw = []
            
            if isinstance(holders_data, list):
                for outcome_data in holders_data:
                    holders = outcome_data.get('holders', [])
                    if holders:
                        outcome_index = holders[0].get('outcomeIndex', 0)
                        if outcome_index == 0:
                            yes_holders_raw = holders[:15]
                        else:
                            no_holders_raw = holders[1:16]  # Skip first (bug)
            
            # Process YES holders
            st.markdown("---")
            st.markdown("### 📈 Top 15 YES Holders")
            yes_progress = st.progress(0, text="Fetching YES holders...")
            yes_holders = []
            
            for i, holder in enumerate(yes_holders_raw):
                enriched = enrich_holder_with_position(holder, condition_id)
                yes_holders.append(enriched)
                yes_progress.progress((i + 1) / len(yes_holders_raw), text=f"Processing {i+1}/{len(yes_holders_raw)} YES holders...")
                time.sleep(0.15)
            
            yes_progress.empty()
            
            # Display YES holders table
            if yes_holders:
                yes_df = pd.DataFrame(yes_holders)
                
                # Format columns
                display_df = pd.DataFrame({
                    'Trader': yes_df['name'],
                    'Shares': yes_df['shares'].apply(lambda x: f"{x:,.0f}"),
                    'Entry Price': yes_df['avg_price'].apply(lambda x: f"${x:.3f}"),
                    'Current Price': yes_df['current_price'].apply(lambda x: f"${x:.3f}"),
                    'Position Value': yes_df['current_value'].apply(lambda x: f"${x:,.0f}"),
                    'Market P&L': yes_df['market_pnl'].apply(lambda x: f"${x:,.0f}"),
                    'All-Time P&L': yes_df['total_pnl'].apply(
                        lambda x: f"${x:,.0f}" if x is not None else "N/A"
                    )
                })
                
                st.dataframe(
                    display_df, 
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
                
                # Summary metrics in columns
                col1, col2, col3 = st.columns(3)
                
                avg_total_pnl = yes_df[yes_df['total_pnl'].notna()]['total_pnl'].mean()
                total_volume = yes_df['current_value'].sum()
                avg_entry = (yes_df['shares'] * yes_df['avg_price']).sum() / yes_df['shares'].sum()
                
                with col1:
                    pnl_class = "success-metric" if avg_total_pnl >= 0 else "danger-metric"
                    st.markdown(f"""
                    <div class="metric-card {pnl_class}">
                        <p style="margin:0; font-size:0.9rem; opacity:0.8;">Avg All-Time P&L</p>
                        <p style="margin:0; font-size:2rem; font-weight:bold;">
                            {"+" if avg_total_pnl >= 0 else ""}${avg_total_pnl:,.0f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <p style="margin:0; font-size:0.9rem; opacity:0.8;">Total Position Value</p>
                        <p style="margin:0; font-size:2rem; font-weight:bold;">${total_volume:,.0f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <p style="margin:0; font-size:0.9rem; opacity:0.8;">Weighted Avg Entry</p>
                        <p style="margin:0; font-size:2rem; font-weight:bold;">${avg_entry:.3f}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Process NO holders
            st.markdown("---")
            st.markdown("### 📉 Top 15 NO Holders")
            no_progress = st.progress(0, text="Fetching NO holders...")
            no_holders = []
            
            for i, holder in enumerate(no_holders_raw):
                enriched = enrich_holder_with_position(holder, condition_id)
                no_holders.append(enriched)
                no_progress.progress((i + 1) / len(no_holders_raw), text=f"Processing {i+1}/{len(no_holders_raw)} NO holders...")
                time.sleep(0.15)
            
            no_progress.empty()
            
            # Display NO holders table
            if no_holders:
                no_df = pd.DataFrame(no_holders)
                
                # Format columns
                display_df = pd.DataFrame({
                    'Trader': no_df['name'],
                    'Shares': no_df['shares'].apply(lambda x: f"{x:,.0f}"),
                    'Entry Price': no_df['avg_price'].apply(lambda x: f"${x:.3f}"),
                    'Current Price': no_df['current_price'].apply(lambda x: f"${x:.3f}"),
                    'Position Value': no_df['current_value'].apply(lambda x: f"${x:,.0f}"),
                    'Market P&L': no_df['market_pnl'].apply(lambda x: f"${x:,.0f}"),
                    'All-Time P&L': no_df['total_pnl'].apply(
                        lambda x: f"${x:,.0f}" if x is not None else "N/A"
                    )
                })
                
                st.dataframe(
                    display_df, 
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
                
                # Summary metrics in columns
                col1, col2, col3 = st.columns(3)
                
                avg_total_pnl = no_df[no_df['total_pnl'].notna()]['total_pnl'].mean()
                total_volume = no_df['current_value'].sum()
                avg_entry = (no_df['shares'] * no_df['avg_price']).sum() / no_df['shares'].sum()
                
                with col1:
                    pnl_class = "success-metric" if avg_total_pnl >= 0 else "danger-metric"
                    st.markdown(f"""
                    <div class="metric-card {pnl_class}">
                        <p style="margin:0; font-size:0.9rem; opacity:0.8;">Avg All-Time P&L</p>
                        <p style="margin:0; font-size:2rem; font-weight:bold;">
                            {"+" if avg_total_pnl >= 0 else ""}${avg_total_pnl:,.0f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <p style="margin:0; font-size:0.9rem; opacity:0.8;">Total Position Value</p>
                        <p style="margin:0; font-size:2rem; font-weight:bold;">${total_volume:,.0f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <p style="margin:0; font-size:0.9rem; opacity:0.8;">Weighted Avg Entry</p>
                        <p style="margin:0; font-size:2rem; font-weight:bold;">${avg_entry:.3f}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.success("✅ Analysis complete!")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem 0; color: #666;">
    <p style="font-size: 1rem; margin-bottom: 0.5rem;">
        <strong>Polymarket Whale Tracker</strong> - Track smart money, fade the losers
    </p>
    <p style="font-size: 0.9rem; margin: 0;">
        Analyzes top holders + all-time P&L across ALL markets
    </p>
    <p style="margin-top: 1rem;">
        <a href="https://github.com/geomanks/polymarket-holders" target="_blank" style="text-decoration: none;">
            ⭐ Star on GitHub
        </a>
    </p>
</div>
""", unsafe_allow_html=True)
