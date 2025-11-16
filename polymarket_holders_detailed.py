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
    """Fetch top holders for a given condition ID"""
    url = f"https://data-api.polymarket.com/holders?market={condition_id}&limit={limit}"
    
    print(f"Fetching top {limit} holders...")
    
    response = requests.get(url)
    response.raise_for_status()
    
    return response.json()


def fetch_user_positions(wallet_address: str, condition_id: str) -> List[Dict]:
    """Fetch user's positions, optionally filtered by condition ID"""
    url = f"https://data-api.polymarket.com/positions?user={wallet_address}&market={condition_id}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return []


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
    
    return {
        'shares': float(position.get('size', 0)),
        'avg_price': float(position.get('avgPrice', 0)),
        'initial_value': float(position.get('initialValue', 0)),
        'current_value': float(position.get('currentValue', 0)),
        'current_price': float(position.get('curPrice', 0)),
        'pnl_cash': float(position.get('cashPnl', 0)),
        'pnl_percent': float(position.get('percentPnl', 0)),
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
    
    # Get detailed position info
    position_details = calculate_position_details(wallet, condition_id, outcome_index)
    enriched.update(position_details)
    
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
        
        pnl_symbol = "📈" if pnl_cash >= 0 else "📉"
        pnl_sign = "+" if pnl_cash >= 0 else ""
        
        print(f"\n   {pnl_symbol} PROFIT/LOSS:")
        print(f"      Cash P&L:           {pnl_sign}${pnl_cash:>10,.2f}")
        print(f"      Percent P&L:        {pnl_sign}{pnl_percent:>10,.2f}%")
        
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
                # Fetch holders
                print(f"\nFetching holders for condition ID: {condition_id}\n")
                holders_data = fetch_holders(condition_id, limit=num_holders)
                
                if holders_data and isinstance(holders_data, list):
                    for outcome_data in holders_data:
                        holders = outcome_data.get('holders', [])
                        
                        if holders:
                            outcome_index = holders[0].get('outcomeIndex', 0)
                            outcome_name = 'YES' if outcome_index == 0 else 'NO'
                            
                            # Enrich each holder with detailed position data
                            print(f"Fetching detailed position data for {len(holders[:num_holders])} {outcome_name} holders...")
                            print("This may take a moment...\n")
                            
                            enriched_holders = []
                            for holder in holders[:num_holders]:
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
                                
                                all_summaries.append({
                                    'outcome': outcome_name,
                                    'num_holders': len(enriched_holders),
                                    'avg_shares': avg_shares,
                                    'weighted_avg_price': weighted_avg_price,
                                    'simple_avg_price': simple_avg_price,
                                    'avg_value_at_purchase': avg_value_at_purchase,
                                    'total_shares': total_shares,
                                    'total_value_at_purchase': total_value_at_purchase
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
                print(f"  {summary['outcome']} OUTCOME:")
                print(f"  {'─'*116}")
                print(f"     Total Holders Analyzed:       {summary['num_holders']}")
                print(f"     Average Shares per Holder:    {summary['avg_shares']:,.2f}")
                print(f"     Weighted Avg Price Paid:      ${summary['weighted_avg_price']:.4f}")
                print(f"     Simple Avg Price Paid:        ${summary['simple_avg_price']:.4f}")
                print(f"     Avg Value at Purchase:        ${summary['avg_value_at_purchase']:,.2f}")
                print(f"     Total Shares (Top {summary['num_holders']}):        {summary['total_shares']:,.2f}")
                print(f"     Total Value at Purchase:      ${summary['total_value_at_purchase']:,.2f}")
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
    
    # Get market URL
    print("\nEnter Polymarket market URL:")
    market_url = input("> ").strip()
    
    if not market_url:
        print("Error: No URL provided")
        sys.exit(1)
    
    # Get number of top holders
    print("\nEnter number of top holders to analyze (5-100, default 20):")
    num_input = input("> ").strip()
    
    if num_input:
        try:
            num_holders = int(num_input)
            if num_holders < 5 or num_holders > 100:
                print("Error: Number must be between 5 and 100")
                sys.exit(1)
        except ValueError:
            print("Invalid number, using default of 20")
            num_holders = 20
    else:
        num_holders = 20
    
    print(f"\nAnalyzing top {num_holders} holders...\n")
    process_market(market_url, num_holders=num_holders)