"""
Polymarket Whale Tracker - SIMPLE & CLEAN VERSION (Visuals Improved)
"""

import streamlit as st
import requests
import re
import time
import pandas as pd
from typing import Optional, List, Dict
import urllib.parse

# ===== PAGE SETUP =====
# Use a dark theme for a sleek, modern look, and a wider layout.
st.set_page_config(
    page_title="Polymarket Top Holders Tracker", 
    page_icon="💰", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ===== ENHANCED STYLING (Dark Theme & Typography) =====
st.markdown("""
<style>
    /* Global Background and Typography */
    .main { 
        background-color: #0d1117; /* Dark GitHub-like background */
        color: #c9d1d9; /* Light grey text */
        font-family: 'Inter', sans-serif;
    }
    
    /* Headers */
    h1, h2, h3 { 
        color: #58a6ff !important; /* Polymarket Blue */
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    h1 {
        border-bottom: 2px solid #21262d; /* Subtle divider for the title */
        padding-bottom: 10px;
    }

    /* Streamlit Components */
    .stTextInput > label, .stSelectbox > label {
        font-size: 1.1rem;
        font-weight: 500;
        color: #c9d1d9;
    }
    .stButton > button {
        background-color: #238636; /* Success green for main action */
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #2ea043;
    }
    
    /* Info/Success/Error Blocks */
    .stAlert { 
        font-size: 1.1rem; 
        border-radius: 8px;
    }
    .stAlert.info { 
        background-color: #1a1f28; 
        border-left: 5px solid #58a6ff;
        color: #c9d1d9;
    }
    .stAlert.success {
        background-color: #1a1f28; 
        border-left: 5px solid #238636;
        color: #c9d1d9;
    }

    /* Divider */
    .st-dg { /* Target the Streamlit divider */
        background-color: #21262d;
    }
    
    /* Metrics Highlighting */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #58a6ff; /* Blue for the value */
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #8b949e; /* Light grey for the label */
    }

    /* DataFrame Styling - to blend with dark theme */
    .stDataFrame {
        border: 1px solid #21262d;
        border-radius: 8px;
    }

    /* P&L Color Coding */
    .positive { color: #38b449; font-weight: bold; } /* Green for positive */
    .negative { color: #f85149; font-weight: bold; } /* Red for negative */
    .neutral { color: #c9d1d9; } /* Default */

</style>
""", unsafe_allow_html=True)

st.title("Polymarket Top Holders Tracker")
st.write("### **See the top traders in any market**")
st.divider()

# ===== CORE FUNCTIONS (No Change needed here for visuals) =====

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

# ===== CUSTOM FORMATTING FUNCTIONS for DataFrame Styling =====

def format_pnl_style(val):
    """Applies CSS class for P&L based on value."""
    if pd.isna(val):
        return 'color: #8b949e' # Gray for N/A
    if val > 0:
        return 'color: #38b449; font-weight: bold' # Green
    elif val < 0:
        return 'color: #f85149; font-weight: bold' # Red
    else:
        return 'color: #c9d1d9' # White/Neutral

def format_currency_with_pnl_style(s):
    """Applies formatting and P&L color to a Pandas Series."""
    formatted_series = s.apply(lambda x: f'${x:,}' if pd.notna(x) else 'N/A')
    styled_series = [format_pnl_style(val) for val in s]
    return [f'{style}; {formatted}' for style, formatted in zip(styled_series, formatted_series)]

# --- Helper function for displaying results ---
def display_results(df: pd.DataFrame, title: str, color_code: str):
    """Reusable function to display a holder section."""
    st.header(f"{color_code} {title}")
    
    # Apply custom styling to the DataFrame
    # Calculate height to show all rows without scrolling (approximately 35px per row + 38px for header)
    table_height = len(df) * 35 + 38
    
    st.dataframe(
        df.style.format({
            'Shares': '{:,}',
            'Entry': '${:.3f}',
            'Current': '${:.3f}',
            'Value': '${:,}',
            'Market P&L': lambda x: f'${x:,}',
            'All-Time P&L': lambda x: f'${x:,.0f}' if pd.notna(x) else 'N/A'
        })
        .applymap(format_pnl_style, subset=['Market P&L', 'All-Time P&L'])
        .set_properties(**{'background-color': '#161b22', 'color': '#c9d1d9'}), # Dark theme background/text for table cells
        use_container_width=True,
        hide_index=True,
        height=table_height
    )
    
    # Metrics
    st.markdown("### Key Metrics")
    col1, col2, col3 = st.columns(3)
    avg_pnl = df['All-Time P&L'].mean()
    
    col1.metric("**Average All-Time P&L**", 
                f"${avg_pnl:,.0f}" if pd.notna(avg_pnl) else "N/A", 
                delta_color="off") # Use off to prevent the delta icon from appearing
    col2.metric("**Total Position Value**", f"${df['Value'].sum():,}")
    
    # Calculate Volume-Weighted Average Price (VWAP) for Entry
    total_shares = df['Shares'].sum()
    if total_shares > 0:
        avg_entry = (df['Shares'] * df['Entry']).sum() / total_shares
        col3.metric("**Volume-Weighted Avg Entry**", f"${avg_entry:.3f}")
    else:
        col3.metric("**Volume-Weighted Avg Entry**", "N/A")


# ===== IMAGE GENERATION FOR TWITTER SHARING =====

# ===== MAIN APP (Updated to use new styling and functions) =====

# Initialize session state for URL
if 'current_url' not in st.session_state:
    st.session_state['current_url'] = ""

url = st.text_input("**🔗 Paste Polymarket Market URL:**", 
                    value=st.session_state['current_url'],
                    placeholder="e.g., https://polymarket.com/event/will-tory-retain-power...")

# Update session state when URL changes
if url != st.session_state['current_url']:
    st.session_state['current_url'] = url
    # Clear old analysis data when URL changes
    for key in ['analysis_yes_data', 'analysis_no_data', 'analysis_slug', 'analysis_market_title', 'share_image', 'image_generated']:
        if key in st.session_state:
            del st.session_state[key]

if url:
    slug = extract_slug(url)
    if not slug:
        st.error("❌ Invalid URL. Please ensure it starts with `https://polymarket.com/event/`")
        st.stop()
    
    try:
        with st.spinner("🚀 Loading market details..."):
            market_data = fetch_market_data(slug)
    except Exception as e:
        st.error(f"Failed to fetch market data: {e}")
        st.stop()
        
    st.success(f"**Market Title:** {market_data.get('title')}")
    
    markets = [m for m in market_data.get('markets', []) if m.get('enableOrderBook')]
    if not markets:
        st.error("No yes/no markets found in this event.")
        st.stop()
    
    if len(markets) > 1:
        options = [m.get('question', f'Market {i}') for i, m in enumerate(markets, 1)]
        selected_question = st.selectbox(
            "**Select specific market to analyze:**", 
            options,
            key="market_select"
        )
        idx = options.index(selected_question)
        selected = markets[idx]
    else:
        selected = markets[0]
        st.info(f"**Market Question:** {selected.get('question')}")
    
    st.markdown("---") # Use custom styled divider
    
    if st.button("🔍 **ANALYZE WHALES**", type="primary", use_container_width=True):
        condition_id = selected.get('conditionId')
        
        with st.spinner("🎣 Fetching top holders for YES and NO outcomes..."):
            try:
                holders_data = fetch_holders(condition_id)
            except Exception as e:
                st.error(f"Failed to fetch holder data: {e}")
                st.stop()
        
        yes_raw, no_raw = [], []
        for outcome in holders_data:
            holders = outcome.get('holders', [])
            if holders:
                if holders[0].get('outcomeIndex') == 0:
                    yes_raw = holders[:15]
                else:
                    # Skip first NO holder (index 0) due to API bug, take next 15
                    no_raw = holders[1:16]  # Skip index 0, take indices 1-15
        
        # YES HOLDERS
        st.markdown("##") # Add vertical space
        st.markdown("---")
        st.subheader("🟢 Analyzing YES Holders...")
        
        yes_data = []
        total_yes = len(yes_raw)
        
        # Create container for progress
        progress_container = st.empty()
        status_container = st.empty()
        
        for i, h in enumerate(yes_raw):
            # Update status message
            holder_name = h.get('name') or h.get('proxyWallet', 'Unknown')[:10]
            status_container.info(f"📊 Analyzing: **{holder_name}** ({i+1}/{total_yes})")
            
            # Update progress bar with percentage
            percentage = int(((i + 1) / total_yes) * 100)
            progress_container.progress((i+1)/total_yes, text=f"Progress: {percentage}% - Fetching position data & all-time P&L...")
            
            enriched = enrich_holder(h, condition_id)
            if enriched:
                yes_data.append(enriched)
            time.sleep(0.15)
        
        # Clear progress indicators
        progress_container.empty()
        status_container.empty()
        
        if yes_data:
            df_yes = pd.DataFrame(yes_data)
            display_results(df_yes, "YES Holders (Top 15)", "🟢")
            
            # Add download button
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
        st.markdown("##") # Add vertical space
        st.markdown("---")
        st.subheader("🔴 Analyzing NO Holders...")
        
        no_data = []
        total_no = len(no_raw)
        
        # Create container for progress
        progress_container = st.empty()
        status_container = st.empty()
        
        for i, h in enumerate(no_raw):
            # Update status message
            holder_name = h.get('name') or h.get('proxyWallet', 'Unknown')[:10]
            status_container.info(f"📊 Analyzing: **{holder_name}** ({i+1}/{total_no})")
            
            # Update progress bar with percentage
            percentage = int(((i + 1) / total_no) * 100)
            progress_container.progress((i+1)/total_no, text=f"Progress: {percentage}% - Fetching position data & all-time P&L...")
            
            enriched = enrich_holder(h, condition_id)
            if enriched:
                no_data.append(enriched)
            time.sleep(0.15)
        
        # Clear progress indicators
        progress_container.empty()
        status_container.empty()
        
        if no_data:
            df_no = pd.DataFrame(no_data)
            display_results(df_no, "NO Holders (Top 15)", "🔴")
            
            # Add download button
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
        st.balloons()
        st.success("✅ Analysis Complete!")
        
        # Store data in session state for Twitter share functionality
        st.session_state['analysis_yes_data'] = yes_data
        st.session_state['analysis_no_data'] = no_data
        st.session_state['analysis_slug'] = slug
        st.session_state['analysis_market_title'] = market_data.get('title')
        
        # ===== COMPARISON SECTION =====
        if yes_data and no_data:
            st.markdown("##")
            st.markdown("---")
            st.header("⚖️ YES vs NO Comparison")
            
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
                
                # Smart money indicator
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
                
                # Smart money indicator
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
            st.header("🐦 Share on Twitter")
            
            # Create a nicely formatted text table for Twitter
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
            
            # Format values before putting them in the tweet
            yes_pnl_str = f"${yes_avg_pnl:,.0f}" if pd.notna(yes_avg_pnl) else "N/A"
            no_pnl_str = f"${no_avg_pnl:,.0f}" if pd.notna(no_avg_pnl) else "N/A"
            yes_winners_str = f"{profitable_yes}/{total_yes} ({(profitable_yes/total_yes*100):.0f}%)" if total_yes > 0 else "N/A"
            no_winners_str = f"{profitable_no}/{total_no} ({(profitable_no/total_no*100):.0f}%)" if total_no > 0 else "N/A"
            
            # Shorten the URL
            full_url = f"https://polymarket-holders-exp.streamlit.app/"
            try:
                response = requests.get(f"https://tinyurl.com/api-create.php?url={full_url}", timeout=3)
                short_url = response.text if response.status_code == 200 else full_url
            except:
                short_url = full_url
            
            # Create the tweet text
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
            
            # Display the tweet preview
            st.markdown("### 📝 Your Tweet (Ready to Post!)")
            st.code(tweet_text, language=None)
            
            # Create the Twitter URL with encoded text
            twitter_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(tweet_text)}"
            
            st.link_button("🐦 Post to Twitter", twitter_url, use_container_width=True, type="primary")
            
            st.success("✅ Click the button above - your tweet is ready! Twitter will open with this text pre-filled.")

st.markdown("---")
st.caption("A tool for tracking large positions on Polymarket. Data fetched via Polymarket APIs. [GitHub Repository](https://github.com/geomanks/polymarket-holders)")

# Add share section
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("[![Star on GitHub](https://img.shields.io/github/stars/geomanks/polymarket-holders?style=social)](https://github.com/geomanks/polymarket-holders)")
with col2:
    st.markdown("[![Twitter](https://img.shields.io/twitter/url?style=social&url=https%3A%2F%2Fgithub.com%2Fgeomanks%2Fpolymarket-holders)](https://twitter.com/intent/tweet?text=Check%20out%20this%20Polymarket%20Whale%20Tracker!&url=https://polymarket-whale-tracker.streamlit.app)")
with col3:
    st.markdown("**Made with ❤️ for the Polymarket community**")
