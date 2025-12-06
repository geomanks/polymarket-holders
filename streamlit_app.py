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
    page_icon="🔮",
    layout="wide"
)

# Title
st.title("🔮 Polymarket Whale Tracker")
st.markdown("Analyze top 15 YES/NO holders for any market + their all-time P&L")

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

# Input
url = st.text_input("Enter Polymarket Market URL:", placeholder="https://polymarket.com/event/...")

if st.button("🔍 Analyze", type="primary"):
    if not url:
        st.error("Please enter a Polymarket URL")
    else:
        try:
            # Extract slug
            slug = extract_slug(url)
            if not slug:
                st.error("Invalid Polymarket URL")
                st.stop()
            
            with st.spinner("Fetching market data..."):
                market_data = fetch_market_data(slug)
            
            market_title = market_data.get('title', 'Unknown')
            st.success(f"**Market:** {market_title}")
            
            markets = market_data.get('markets', [])
            
            # Filter for yes/no markets
            yes_no_markets = [m for m in markets if m.get('enableOrderBook', False)]
            
            if not yes_no_markets:
                st.error("No yes/no markets found")
                st.stop()
            
            # Handle multiple markets
            selected_market = None
            if len(yes_no_markets) > 1:
                options = [m.get('question', f'Market {i}') for i, m in enumerate(yes_no_markets, 1)]
                choice = st.selectbox("Select market:", options)
                selected_market = yes_no_markets[options.index(choice)]
            else:
                selected_market = yes_no_markets[0]
            
            condition_id = selected_market.get('conditionId')
            question = selected_market.get('question', 'Unknown')
            
            st.info(f"**Question:** {question}")
            
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
            st.subheader("📈 Top 15 YES Holders")
            yes_progress = st.progress(0)
            yes_holders = []
            
            for i, holder in enumerate(yes_holders_raw):
                enriched = enrich_holder_with_position(holder, condition_id)
                yes_holders.append(enriched)
                yes_progress.progress((i + 1) / len(yes_holders_raw))
                time.sleep(0.15)
            
            # Display YES holders table
            if yes_holders:
                yes_df = pd.DataFrame(yes_holders)
                yes_df['All-Time P&L'] = yes_df['total_pnl'].apply(
                    lambda x: f"${x:,.2f}" if x is not None else "N/A"
                )
                yes_df['Market P&L'] = yes_df['market_pnl'].apply(lambda x: f"${x:,.2f}")
                yes_df['Shares'] = yes_df['shares'].apply(lambda x: f"{x:,.2f}")
                yes_df['Avg Entry'] = yes_df['avg_price'].apply(lambda x: f"${x:.4f}")
                yes_df['Current Price'] = yes_df['current_price'].apply(lambda x: f"${x:.4f}")
                
                display_df = yes_df[['name', 'Shares', 'Avg Entry', 'Current Price', 'Market P&L', 'All-Time P&L']]
                st.dataframe(display_df, use_container_width=True)
                
                # Summary
                avg_total_pnl = yes_df[yes_df['total_pnl'].notna()]['total_pnl'].mean()
                st.metric("Average All-Time P&L (YES)", f"${avg_total_pnl:,.2f}" if pd.notna(avg_total_pnl) else "N/A")
            
            st.divider()
            
            # Process NO holders
            st.subheader("📉 Top 15 NO Holders")
            no_progress = st.progress(0)
            no_holders = []
            
            for i, holder in enumerate(no_holders_raw):
                enriched = enrich_holder_with_position(holder, condition_id)
                no_holders.append(enriched)
                no_progress.progress((i + 1) / len(no_holders_raw))
                time.sleep(0.15)
            
            # Display NO holders table
            if no_holders:
                no_df = pd.DataFrame(no_holders)
                no_df['All-Time P&L'] = no_df['total_pnl'].apply(
                    lambda x: f"${x:,.2f}" if x is not None else "N/A"
                )
                no_df['Market P&L'] = no_df['market_pnl'].apply(lambda x: f"${x:,.2f}")
                no_df['Shares'] = no_df['shares'].apply(lambda x: f"{x:,.2f}")
                no_df['Avg Entry'] = no_df['avg_price'].apply(lambda x: f"${x:.4f}")
                no_df['Current Price'] = no_df['current_price'].apply(lambda x: f"${x:.4f}")
                
                display_df = no_df[['name', 'Shares', 'Avg Entry', 'Current Price', 'Market P&L', 'All-Time P&L']]
                st.dataframe(display_df, use_container_width=True)
                
                # Summary
                avg_total_pnl = no_df[no_df['total_pnl'].notna()]['total_pnl'].mean()
                st.metric("Average All-Time P&L (NO)", f"${avg_total_pnl:,.2f}" if pd.notna(avg_total_pnl) else "N/A")
            
            st.success("✅ Analysis complete!")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


# Footer
st.divider()
st.markdown("""
**About:** This tool analyzes the top holders in Polymarket yes/no markets and shows their all-time profit/loss across ALL markets.

**Source:** [GitHub](https://github.com/geomanks/polymarket-holders)
""")
