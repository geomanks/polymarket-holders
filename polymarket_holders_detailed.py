#!/usr/bin/env python3
"""
Polymarket Top Holders with Detailed Position Analysis
Shows each holder's position: shares, average price, current value, P&L

Usage: python polymarket_holders_detailed.py <market_url>
Example: python polymarket_holders_detailed.py "https://polymarket.com/event/new-york-city-mayoral-election"
"""

import requests
import sys
import json
from typing import List, Dict, Optional
import re
import time


def extract_slug(url: str) -> Optional[str]:
    """Extract the event slug from a Polymarket URL"""
    match = re.search(r'polymarket\.com/event/([^?#/]+)', url)
    return match.group(1) if match else None


def fetch_market_data(slug: str) -> Dict:
    """Fetch market data from Polymarket Gamma API"""
    url = f"https://gamma-api.polymarket.com/events?slug={slug}"
    
    print(f"Fetching market data for: {slug}\n")
    
    response = requests.get(url)
    response.raise_for_status()
    
    data = response.json()
    
    if not data or len(data) == 0:
        raise Exception("No market data found for this slug")
    
    return data[0]


def fetch_holders(condition_id: str, limit: int = 50) -> List[Dict]:
    """Fetch top holders for a given condition ID, sorted by shares held"""
    # Add sort parameter to get holders with most shares first
    url = f"https://data-api.polymarket.com/holders?market={condition_id}&limit={limit}&sort=shares&order=desc"
    
    response = requests.get(url)
    response.raise_for_status()
    
    return response.json()


def fetch_user_positions(wallet_address: str, condition_id: str = None) -> List[Dict]:
    """Fetch user's positions, optionally filtered by condition ID"""
    if condition_id:
        url = f"https://data-api.polymarket.com/positions?user={wallet_address}&market={condition_id}"
    else:
        url = f"https://data-api.polymarket.com/positions?user={wallet_address}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return []


def fetch_all_user_positions(wallet_address: str) -> List[Dict]:
    """Fetch all user's positions across all markets"""
    url = f"https://data-api.polymarket.com/positions?user={wallet_address}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return []


def fetch_user_profile(wallet_address: str) -> Dict:
    """Fetch user profile with total statistics"""
    # Try multiple possible endpoints
    endpoints = [
        f"https://data-api.polymarket.com/users/{wallet_address}",
        f"https://data-api.polymarket.com/user/{wallet_address}",
        f"https://gamma-api.polymarket.com/users/{wallet_address}",
        f"https://strapi-matic.poly.market/users/{wallet_address}",
    ]
    
    for url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data:
                    print(f"[DEBUG] Found profile data at: {url}")
                    return data
        except Exception as e:
            continue
    
    return {}


def fetch_user_stats(wallet_address: str) -> Dict:
    """Fetch individual user's all-time P&L"""
    # Try individual user profit endpoints
    endpoints = [
        f"https://lb-api.polymarket.com/profit/{wallet_address}",
        f"https://lb-api.polymarket.com/users/{wallet_address}/profit",
        f"https://data-api.polymarket.com/profit?user={wallet_address}",
        f"https://data-api.polymarket.com/users/{wallet_address}/profit",
    ]
    
    for url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data
        except Exception as e:
            continue
    
    # Fallback: try the leaderboard endpoint
    try:
        url = f"https://lb-api.polymarket.com/profit?user={wallet_address}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list):
                # Check if user is in the leaderboard
                for user_stat in data:
                    if user_stat.get('proxyWallet', '').lower() == wallet_address.lower():
                        return user_stat
    except:
        pass
    
    return {}


def scrape_user_profit_from_profile(wallet_address: str) -> float:
    """
    Scrape all-time P&L from user's Polymarket profile page.
    FIXED: Now correctly detects and preserves negative signs!
    """
    profile_url = f"https://polymarket.com/profile/{wallet_address}"
    
    try:
        response = requests.get(profile_url, timeout=10)
        if response.status_code != 200:
            return None
        
        html = response.text
        
        # Strategy 1: Look for "Profit/Loss" label specifically - MOST RELIABLE
        # Unicode minus: \u2212, Regular minus: -
        # Look for the value that comes AFTER any intermediate text (like "1D1W1MALL")
        patterns = [
            # Match Profit/Loss, skip any non-digit/non-$ chars, then capture sign and large amount
            r'Profit/Loss[^$]*?([\u2212\-])?\s*\$\s*([\d,]+\.[\d]{2})',
            r'data-pnl\s*=\s*["\']+([\u2212\-]?[\d,]+\.?\d*)["\']',
            r'data-profit[-_]?loss\s*=\s*["\']+([\u2212\-]?[\d,]+\.?\d*)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                groups = match.groups()
                
                if len(groups) == 2:
                    sign, number = groups
                    value = float(number.replace(',', ''))
                    # Check for unicode minus (\u2212) or regular minus
                    if sign and sign in ['\u2212', '-']:
                        print(f"[DEBUG] Found P&L with sign: {sign}${number} = -${value:,.2f}")
                        return -value
                    else:
                        print(f"[DEBUG] Found P&L (positive): ${number} = +${value:,.2f}")
                        return value
                elif len(groups) == 1:
                    value_str = groups[0]
                    if value_str.startswith('\u2212') or value_str.startswith('-'):
                        value = float(value_str.lstrip('\u2212-').replace(',', ''))
                        print(f"[DEBUG] Found P&L with prefix: -${value:,.2f}")
                        return -value
                    else:
                        value = float(value_str.replace(',', ''))
                        print(f"[DEBUG] Found P&L (positive): +${value:,.2f}")
                        return value
        
        # Strategy 2: Context-based detection - look SPECIFICALLY near "Profit/Loss" text
        sections = html.split('Profit/Loss')
        if len(sections) > 1:
            pnl_section = sections[1][:600]
            is_negative = False
            
            negative_classes = ['text-red', 'text-danger', 'negative', 'loss', 'text-destructive', 'minus', 'color-red', 'red']
            if any(cls in pnl_section.lower() for cls in negative_classes):
                is_negative = True
                print(f"[DEBUG] Found negative indicator in CSS")
            
            first_100 = pnl_section[:100]
            # Check for unicode minus (\u2212) or regular minus
            if '\u2212' in first_100 or re.search(r'-\s*\$', first_100):
                is_negative = True
                print(f"[DEBUG] Found minus sign")
            
            # Look for properly formatted dollar amounts with 2 decimal places
            amount_match = re.search(r'\$\s*([\d,]+\.[\d]{2})', pnl_section)
            if amount_match:
                value = float(amount_match.group(1).replace(',', ''))
                # Accept ANY value found near "Profit/Loss" label
                final_value = -value if is_negative else value
                print(f"[DEBUG] Context: ${value:,.2f} -> {'+' if final_value >= 0 else ''}${final_value:,.2f}")
                return final_value
        
        # Strategy 3: Parse __NEXT_DATA__
        next_data_match = re.search(r'__NEXT_DATA__[^<]*({.*?})</script>', html, re.DOTALL)
        if next_data_match:
            try:
                import json
                data = json.loads(next_data_match.group(1))
                
                def find_profit(obj, depth=0):
                    if depth > 10:
                        return None
                    if isinstance(obj, dict):
                        for key in ['profit', 'pnl', 'allTimePnl', 'totalPnl', 'amount']:
                            if key in obj and isinstance(obj[key], (int, float)):
                                return float(obj[key])
                        for value in obj.values():
                            result = find_profit(value, depth + 1)
                            if result is not None:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_profit(item, depth + 1)
                            if result is not None:
                                return result
                    return None
                
                profit = find_profit(data)
                if profit is not None:
                    print(f"[DEBUG] Found profit in __NEXT_DATA__: ${profit:,.2f}")
                    return profit
            except Exception as e:
                print(f"[DEBUG] Error parsing __NEXT_DATA__: {e}")
        
        # Strategy 4: DISABLED - Too many false positives
        # Don't use generic dollar amount scraping as fallback
        
        print(f"[DEBUG] Could not find Profit/Loss value")
        return None
        
    except Exception as e:
        print(f"[DEBUG] Error scraping: {e}")
        return None



def fetch_user_activity(wallet_address: str, condition_id: str = None, limit: int = 100) -> List[Dict]:
    """Fetch user's trading activity for a specific market"""
    if condition_id:
        url = f"https://data-api.polymarket.com/activity?user={wallet_address}&market={condition_id}&limit={limit}"
    else:
        url = f"https://data-api.polymarket.com/activity?user={wallet_address}&limit={limit}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except:
        return []


def calculate_position_details(wallet_address: str, condition_id: str, outcome_index: int) -> Dict:
    """Calculate detailed position information for a specific holder in a specific market"""
    
    # Fetch positions for this market
    positions = fetch_user_positions(wallet_address, condition_id)
    
    # Find the position for the specific outcome
    position = None
    for pos in positions:
        if pos.get('outcomeIndex') == outcome_index:
            position = pos
            break
    
    if not position:
        return {
            'shares': 0,
            'avg_price': 0,
            'initial_value': 0,
            'current_value': 0,
            'current_price': 0,
            'pnl_cash': 0,
            'pnl_percent': 0,
        }
    
    # Calculate P&L manually: current_value - initial_value
    shares = float(position.get('size', 0))
    avg_price = float(position.get('avgPrice', 0))
    current_price = float(position.get('curPrice', 0))
    initial_value = float(position.get('initialValue', 0))
    current_value = float(position.get('currentValue', 0))
    
    # Manual calculation: P&L = (current_price - avg_price) * shares
    calculated_pnl = (current_price - avg_price) * shares
    
    # Or use: current_value - initial_value
    calculated_pnl_alt = current_value - initial_value
    
    return {
        'shares': shares,
        'avg_price': avg_price,
        'initial_value': initial_value,
        'current_value': current_value,
        'current_price': current_price,
        'pnl_cash': calculated_pnl_alt,  # Use calculated P&L instead of API's
        'pnl_percent': (calculated_pnl_alt / initial_value * 100) if initial_value > 0 else 0,
        'total_bought': float(position.get('totalBought', 0)),
    }


def enrich_holder_with_position(holder: Dict, condition_id: str) -> Dict:
    """Enrich holder data with detailed position information"""
    wallet = holder.get('proxyWallet')
    outcome_index = holder.get('outcomeIndex', 0)
    
    if not wallet:
        return holder
    
    enriched = {
        'wallet': wallet,
        'name': holder.get('name'),
        'pseudonym': holder.get('pseudonym'),
        'bio': holder.get('bio'),
        'shares_from_holders_api': holder.get('amount', 0),
        'outcomeIndex': outcome_index,
        'outcome': 'YES' if outcome_index == 0 else 'NO',
    }
    
    # Get detailed position info for this market
    position_details = calculate_position_details(wallet, condition_id, outcome_index)
    enriched.update(position_details)
    
    # Get all-time P&L from API
    stats = fetch_user_stats(wallet)
    
    all_time_pnl = None
    
    # Handle different response types
    if stats:
        if isinstance(stats, dict):
            # Individual user profit response
            all_time_pnl = stats.get('amount') or stats.get('profit') or stats.get('pnl')
            if all_time_pnl is not None:
                all_time_pnl = float(all_time_pnl)
                print(f"[DEBUG] Found all-time P&L from API for {wallet[:10]}: ${all_time_pnl:,.2f}")
        elif isinstance(stats, list):
            # Leaderboard response - find this wallet
            for user_stat in stats:
                if user_stat.get('proxyWallet', '').lower() == wallet.lower():
                    all_time_pnl = float(user_stat.get('amount', 0))
                    print(f"[DEBUG] Found all-time P&L from leaderboard for {wallet[:10]}: ${all_time_pnl:,.2f}")
                    break
    
    # If not found in API, try scraping the profile page
    if all_time_pnl is None:
        print(f"[DEBUG] Trying to scrape profile for {wallet[:10]}")
        all_time_pnl = scrape_user_profit_from_profile(wallet)
    
    if all_time_pnl is not None:
        enriched['total_pnl_all_markets'] = all_time_pnl
    else:
        # Last resort: calculate from positions
        print(f"[DEBUG] No profit data available, calculating from positions for {wallet[:10]}")
        all_positions = fetch_all_user_positions(wallet)
        if all_positions:
            total_unrealized = sum(
                float(pos.get('currentValue', 0)) - float(pos.get('initialValue', 0))
                for pos in all_positions
            )
            total_realized = sum(float(pos.get('realizedPnl', 0)) for pos in all_positions)
            enriched['total_pnl_all_markets'] = total_unrealized + total_realized
        else:
            enriched['total_pnl_all_markets'] = 0
    
    # Get recent activity for this market
    activity = fetch_user_activity(wallet, condition_id, limit=50)
    
    if activity:
        # Calculate trading stats for this market
        buy_trades = [a for a in activity if a.get('side') == 'BUY' and a.get('outcomeIndex') == outcome_index]
        sell_trades = [a for a in activity if a.get('side') == 'SELL' and a.get('outcomeIndex') == outcome_index]
        
        enriched['num_buys'] = len(buy_trades)
        enriched['num_sells'] = len(sell_trades)
        enriched['total_trades'] = len(buy_trades) + len(sell_trades)
        
        if buy_trades:
            total_buy_volume = sum(float(t.get('usdcSize', 0)) for t in buy_trades)
            total_buy_shares = sum(float(t.get('size', 0)) for t in buy_trades)
            enriched['total_buy_volume'] = total_buy_volume
            enriched['total_buy_shares'] = total_buy_shares
            
        if sell_trades:
            total_sell_volume = sum(float(t.get('usdcSize', 0)) for t in sell_trades)
            total_sell_shares = sum(float(t.get('size', 0)) for t in sell_trades)
            enriched['total_sell_volume'] = total_sell_volume
            enriched['total_sell_shares'] = total_sell_shares
    
    return enriched


def display_detailed_holders(holders: List[Dict], outcome_name: str, market_title: str, show_average: bool = False):
    """Display holders with detailed position information"""
    if not holders or len(holders) == 0:
        print(f"\nNo holders found for {outcome_name}\n")
        return
    
    print(f"\n{'='*120}")
    print(f"DETAILED POSITIONS FOR: {market_title} - {outcome_name}")
    print(f"{'='*120}\n")
    
    for idx, holder in enumerate(holders, 1):
        name = holder.get('name') or holder.get('pseudonym') or 'Anonymous'
        wallet = holder.get('wallet', 'Unknown')
        
        print(f"{'#'}{idx} {name}")
        print(f"{'─'*120}")
        print(f"   Wallet: {wallet}")
        
        # Position Information
        shares = holder.get('shares', 0)
        avg_price = holder.get('avg_price', 0)
        current_price = holder.get('current_price', 0)
        
        print(f"\n   📊 POSITION DETAILS:")
        print(f"      Shares Held:        {shares:>12,.2f}")
        print(f"      Average Price:      ${avg_price:>11,.4f}")
        print(f"      Current Price:      ${current_price:>11,.4f}")
        
        # Value Information
        initial_value = holder.get('initial_value', 0)
        current_value = holder.get('current_value', 0)
        
        print(f"\n   💰 VALUE:")
        print(f"      Initial Investment: ${initial_value:>11,.2f}")
        print(f"      Current Value:      ${current_value:>11,.2f}")
        
        # P&L Information
        pnl_cash = holder.get('pnl_cash', 0)
        pnl_percent = holder.get('pnl_percent', 0)
        total_pnl_all = holder.get('total_pnl_all_markets', 0)
        
        pnl_symbol = "📈" if pnl_cash >= 0 else "📉"
        pnl_sign = "+" if pnl_cash >= 0 else ""
        
        total_pnl_symbol = "📈" if total_pnl_all >= 0 else "📉"
        total_pnl_sign = "+" if total_pnl_all >= 0 else ""
        
        print(f"\n   {pnl_symbol} PROFIT/LOSS (This Market):")
        print(f"      Cash P&L:           {pnl_sign}${pnl_cash:>10,.2f}")
        print(f"      Percent P&L:        {pnl_sign}{pnl_percent:>10,.2f}%")
        
        print(f"\n   {total_pnl_symbol} TOTAL P&L (All Markets):")
        print(f"      Total Cash P&L:     {total_pnl_sign}${total_pnl_all:>10,.2f}")
        
        # Trading Activity for this market
        num_buys = holder.get('num_buys', 0)
        num_sells = holder.get('num_sells', 0)
        total_trades = holder.get('total_trades', 0)
        
        if total_trades > 0:
            print(f"\n   📈 TRADING ACTIVITY (This Market):")
            print(f"      Total Trades:       {total_trades:>12}")
            print(f"      Buy Orders:         {num_buys:>12}")
            print(f"      Sell Orders:        {num_sells:>12}")
            
            if holder.get('total_buy_volume'):
                print(f"      Total Bought:       ${holder.get('total_buy_volume', 0):>11,.2f}")
            if holder.get('total_sell_volume'):
                print(f"      Total Sold:         ${holder.get('total_sell_volume', 0):>11,.2f}")
        
        # Bio if available
        bio = holder.get('bio')
        if bio:
            print(f"\n   💬 BIO: {bio[:100]}{'...' if len(bio) > 100 else ''}")
        
        print(f"\n")
    
    # Display summary at the end
    if show_average:
        total_shares = sum(h.get('shares', 0) for h in holders)
        avg_shares = total_shares / len(holders) if holders else 0
        
        # Calculate weighted average price paid by all top holders
        total_weighted_price = sum(h.get('shares', 0) * h.get('avg_price', 0) for h in holders)
        weighted_avg_price = total_weighted_price / total_shares if total_shares > 0 else 0
        
        # Calculate average of average prices (unweighted)
        total_avg_prices = sum(h.get('avg_price', 0) for h in holders)
        simple_avg_price = total_avg_prices / len(holders) if holders else 0
        
        avg_value_at_purchase = avg_shares * weighted_avg_price
        total_value_at_purchase = total_shares * weighted_avg_price
        
        print(f"{'='*120}")
        print(f"📊 TOP {len(holders)} HOLDERS SUMMARY:")
        print(f"{'='*120}")
        print(f"   Total Holders Analyzed:       {len(holders)}")
        print(f"   Average Shares per Holder:    {avg_shares:,.2f}")
        print(f"   Weighted Avg Price Paid:      ${weighted_avg_price:.4f}")
        print(f"   Simple Avg Price Paid:        ${simple_avg_price:.4f}")
        print(f"   Avg Value at Purchase:        ${avg_value_at_purchase:,.2f}")
        print(f"   Total Shares (Top {len(holders)}):        {total_shares:,.2f}")
        print(f"   Total Value at Purchase:      ${total_value_at_purchase:,.2f}")
    
    print(f"{'='*120}\n")


def process_market(market_url: str, num_holders: int = 20):
    """Main function to process a market URL and display detailed holder positions"""
    
    slug = extract_slug(market_url)
    if not slug:
        print("Error: Invalid Polymarket URL")
        sys.exit(1)
    
    try:
        # Fetch market data
        market_data = fetch_market_data(slug)
        
        market_title = market_data.get('title', 'Unknown')
        print(f"Event: {market_title}")
        print(f"Description: {market_data.get('description', 'N/A')[:100]}...\n")
        
        markets = market_data.get('markets', [])
        
        if not markets:
            print("Error: No markets found in this event")
            sys.exit(1)
        
        print(f"Found {len(markets)} market(s)\n")
        
        # For multi-outcome events, let user select
        if len(markets) > 2:
            print("This is a multi-outcome event. Markets:")
            for idx, market in enumerate(markets, 1):
                question = market.get('question', market.get('outcome', f'Market {idx}'))
                print(f"{idx}. {question}")
            
            print(f"\nEnter the number of the market you want to view:")
            choice = input("> ").strip()
            
            try:
                market_idx = int(choice) - 1
                if market_idx < 0 or market_idx >= len(markets):
                    print("Invalid market number")
                    sys.exit(1)
                selected_markets = [markets[market_idx]]
                market_title = markets[market_idx].get('question', market_title)
            except ValueError:
                print("Invalid input")
                sys.exit(1)
        else:
            selected_markets = markets
        
        # Process each market
        all_summaries = []  # Collect summaries for both YES and NO
        
        for market in selected_markets:
            condition_id = market.get('conditionId')
            if not condition_id:
                continue
            
            try:
                # Always fetch 20 holders per outcome (API max)
                fetch_limit = 20
                print(f"\nFetching top {fetch_limit} holders for condition ID: {condition_id}\n")
                holders_data = fetch_holders(condition_id, limit=fetch_limit)
                
                if holders_data and isinstance(holders_data, list):
                    for outcome_data in holders_data:
                        holders = outcome_data.get('holders', [])
                        
                        if holders:
                            outcome_index = holders[0].get('outcomeIndex', 0)
                            outcome_name = 'YES' if outcome_index == 0 else 'NO'
                            
                            # For NO holders, skip the first one (bugged) and get next 15
                            # For YES holders, get first 15
                            if outcome_name == 'NO':
                                holders_to_process = holders[1:16]  # Skip first, take next 15 (indices 1-15)
                            else:
                                holders_to_process = holders[:15]  # Take first 15 (indices 0-14)
                            
                            # Enrich each holder with detailed position data
                            print(f"Fetching detailed position data for {len(holders_to_process)} {outcome_name} holders...")
                            print("This may take a moment...\n")
                            
                            enriched_holders = []
                            for holder in holders_to_process:
                                print(f"  Processing: {holder.get('name') or holder.get('proxyWallet', '')[:20]}...")
                                enriched = enrich_holder_with_position(holder, condition_id)
                                enriched_holders.append(enriched)
                                time.sleep(0.15)  # Be nice to the API
                            
                            display_detailed_holders(enriched_holders, outcome_name, market_title, show_average=False)
                            
                            # Calculate summary for this outcome
                            if enriched_holders:
                                total_shares = sum(h.get('shares', 0) for h in enriched_holders)
                                avg_shares = total_shares / len(enriched_holders) if enriched_holders else 0
                                total_weighted_price = sum(h.get('shares', 0) * h.get('avg_price', 0) for h in enriched_holders)
                                weighted_avg_price = total_weighted_price / total_shares if total_shares > 0 else 0
                                total_avg_prices = sum(h.get('avg_price', 0) for h in enriched_holders)
                                simple_avg_price = total_avg_prices / len(enriched_holders) if enriched_holders else 0
                                avg_value_at_purchase = avg_shares * weighted_avg_price
                                total_value_at_purchase = total_shares * weighted_avg_price
                                
                                # Calculate average total PnL
                                total_pnl_sum = sum(h.get('total_pnl_all_markets', 0) for h in enriched_holders)
                                avg_total_pnl = total_pnl_sum / len(enriched_holders) if enriched_holders else 0
                                
                                all_summaries.append({
                                    'outcome': outcome_name,
                                    'num_holders': len(enriched_holders),
                                    'avg_shares': avg_shares,
                                    'weighted_avg_price': weighted_avg_price,
                                    'simple_avg_price': simple_avg_price,
                                    'avg_value_at_purchase': avg_value_at_purchase,
                                    'total_shares': total_shares,
                                    'total_value_at_purchase': total_value_at_purchase,
                                    'avg_total_pnl': avg_total_pnl
                                })
                            
            except Exception as e:
                print(f"Error processing market: {e}")
                import traceback
                traceback.print_exc()
        
        # Display all summaries at the end
        if all_summaries:
            print(f"\n{'='*120}")
            print(f"📊 FINAL SUMMARY - TOP HOLDERS ANALYSIS")
            print(f"{'='*120}\n")
            
            for summary in all_summaries:
                avg_pnl = summary['avg_total_pnl']
                pnl_symbol = "📈" if avg_pnl >= 0 else "📉"
                pnl_sign = "+" if avg_pnl >= 0 else ""
                
                print(f"  {summary['outcome']} OUTCOME:")
                print(f"  {'─'*116}")
                print(f"     Total Holders Analyzed:       {summary['num_holders']}")
                print(f"     Average Shares per Holder:    {summary['avg_shares']:,.2f}")
                print(f"     Weighted Avg Price Paid:      ${summary['weighted_avg_price']:.4f}")
                print(f"     Simple Avg Price Paid:        ${summary['simple_avg_price']:.4f}")
                print(f"     Avg Value at Purchase:        ${summary['avg_value_at_purchase']:,.2f}")
                print(f"     Total Shares (Top {summary['num_holders']}):        {summary['total_shares']:,.2f}")
                print(f"     Total Value at Purchase:      ${summary['total_value_at_purchase']:,.2f}")
                print(f"     {pnl_symbol} Avg Total P&L (All Markets):  {pnl_sign}${avg_pnl:,.2f}")
                print(f"\n")
            
            print(f"{'='*120}\n")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Interactive mode - prompt for inputs
    print("=" * 60)
    print("POLYMARKET TOP HOLDERS ANALYSIS")
    print("=" * 60)
    print("\nAnalyzing top 15 YES holders and top 15 NO holders")
    print("(skipping first NO holder due to data issue)\n")
    
    # Get market URL
    print("Enter Polymarket market URL:")
    market_url = input("> ").strip()
    
    if not market_url:
        print("Error: No URL provided")
        sys.exit(1)
    
    # Fixed at 15 holders
    num_holders = 15
    
    print(f"\nAnalyzing top {num_holders} holders...\n")
    process_market(market_url, num_holders=num_holders)
