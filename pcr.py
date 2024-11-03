"""
PCR Calculator Script

This script calculates the Put/Call Ratio (PCR) for a specified security symbol, 
option expiration date, and strike price or range of strikes. It uses open interest 
data from Yahoo Finance to provide insights into market sentiment.

Usage:
    python pcr.py --symbol SYMBOL --date-strike DATE_STRIKE [--lower LOWER] [--upper UPPER] [--G]

Options:
    --symbol, -s         : Security symbol (e.g., AAPL).
    --date-strike, -d    : Expiration date and optional strike in format "Month Day, Strike" 
                           (e.g., "Nov 29, 150"), "Month" (e.g., "Nov"), or "all".
    --lower              : Lower bound of strike price range (optional).
    --upper              : Upper bound of strike price range (optional).
    --G, -g              : Enable chart generation for PCR vs. Strike Prices.
    
Examples:
    Calculate PCR for all strikes in November for AAPL:
        python pcr.py --symbol AAPL --date-strike Nov --lower 100 --upper 200 --G
    
    Calculate PCR for a specific strike price on a given date:
        python pcr.py --symbol MSFT --date-strike "Nov 29, 150"
    
Version:
    1.0.2
"""

import yfinance as yf
import click
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Version release number
VERSION = "1.0.2"

def get_third_friday(year, month):
    """Helper function to find the third Friday of a given month and year."""
    first_day = datetime(year, month, 1)
    # Find the first Friday
    first_friday = first_day + timedelta(days=(4 - first_day.weekday() + 7) % 7)
    # Move to the third Friday
    third_friday = first_friday + timedelta(weeks=2)
    return third_friday.strftime("%Y-%m-%d")

@click.command()
@click.option('--symbol', '-s', required=True, type=str, help="Security symbol (e.g., AAPL)")
@click.option('--date-strike', '-d', required=True, type=str, help='Expiration date and strike in format "Month Day, Strike" (e.g., "Nov 29, 150"), "Month" (e.g., "Nov"), or "all".')
@click.option('--lower', type=float, help="Lower bound of strike price range (optional).")
@click.option('--upper', type=float, help="Upper bound of strike price range (optional).")
@click.option('--G', '-g', is_flag=True, help="Enable chart generation for PCR vs. Strike Prices.")
def calculate_put_call_ratio(symbol, date_strike, lower, upper, g):
    """
    Calculate Put/Call Ratio based on open interest for a given symbol, expiration date, 
    and strike range or single strike.
    """
    # Parse the date and strike price from the provided input
    match = re.match(r'(\w{3})(?: (\d{1,2}))?,? ?(\d+)?', date_strike)
    if not match:
        click.echo("Invalid format for date-strike. Use 'Month Day, Strike' (e.g., 'Nov 29, 150'), 'Month' (e.g., 'Nov'), or 'all'.")
        return

    # Extract month, optional day, and optional strike price
    month_str, day_str, strike_str = match.group(1), match.group(2), match.group(3)
    year = datetime.now().year  # assuming current year for simplicity

    # Determine expiration date
    if day_str:
        # If day is specified, use provided day and month
        try:
            expiration_date = datetime.strptime(f"{month_str} {day_str} {year}", "%b %d %Y").strftime("%Y-%m-%d")
        except ValueError:
            click.echo("Invalid date provided.")
            return
    else:
        # If only month is specified, get the third Friday of the month
        try:
            month = datetime.strptime(month_str, "%b").month
            expiration_date = get_third_friday(year, month)
        except ValueError:
            click.echo("Invalid month provided.")
            return

    # Download options data for the specified symbol
    ticker = yf.Ticker(symbol)
    
    # Check if the expiration date exists in available options dates
    if expiration_date not in ticker.options:
        click.echo(f"No options data available for the specified expiration date: {expiration_date}")
        return

    # Fetch option chain for the expiration date
    opt_chain = ticker.option_chain(expiration_date)
    
    # Determine if we're using a range or a single strike
    if lower is not None and upper is not None:
        click.echo(f"Displaying PCR for all strikes between {lower} and {upper}.")
        
        if g:
            click.echo("Generating PCR chart for the specified range of strikes.")

        total_put_oi = 0
        total_call_oi = 0
        strikes = []
        pcr_values = []
        
        click.echo(f"Put/Call Ratios for {symbol} on {expiration_date} for each strike price within range:")
        click.echo("Strike Price | Put OI | Call OI | PCR")
        click.echo("-----------------------------------------")
        
        for strike in opt_chain.calls['strike']:
            # Check if the strike is within the specified range
            if lower <= strike <= upper:
                # Check for open interest in both puts and calls
                call_oi = opt_chain.calls[opt_chain.calls['strike'] == strike]['openInterest']
                put_oi = opt_chain.puts[opt_chain.puts['strike'] == strike]['openInterest']
                
                call_oi_value = call_oi.values[0] if not call_oi.empty else 0
                put_oi_value = put_oi.values[0] if not put_oi.empty else 0
                
                # Calculate PCR
                pcr = put_oi_value / call_oi_value if call_oi_value > 0 else float('inf')
                click.echo(f"{strike:<12} | {put_oi_value:<6} | {call_oi_value:<6} | {pcr:.2f}")
                
                # Append values for charting
                strikes.append(strike)
                pcr_values.append(pcr)
                
                # Sum total open interest
                total_put_oi += put_oi_value
                total_call_oi += call_oi_value
        
        # Calculate and display total PCR
        if total_call_oi == 0:
            click.echo("Total Call Open Interest is 0, cannot calculate total PCR.")
        else:
            total_pcr = total_put_oi / total_call_oi
            click.echo("-----------------------------------------")
            click.echo(f"Total        | {total_put_oi:<6} | {total_call_oi:<6} | {total_pcr:.2f}")
        
        # Plot the chart if the --G or -g option is enabled
        if g:
            plt.figure(figsize=(10, 6))
            plt.plot(strikes, pcr_values, marker='o', linestyle='-', color='b')
            plt.xlabel("Strike Price")
            plt.ylabel("Put/Call Ratio (PCR)")
            plt.title(f"Put/Call Ratio (PCR) vs Strike Price for {symbol} on {expiration_date}")
            plt.grid(True)
            plt.show()

    else:
        # Calculate for specific strike or "all" strikes
        if lower is None and upper is None and date_strike.lower() != "all":
            # Calculate for single specific strike
            if strike_str is not None:
                strike_price = float(strike_str)
                call_oi = opt_chain.calls[opt_chain.calls['strike'] == strike_price]['openInterest']
                put_oi = opt_chain.puts[opt_chain.puts['strike'] == strike_price]['openInterest']
                
                # Check if the data is available for the specified strike
                if call_oi.empty or put_oi.empty:
                    click.echo(f"No options data found for strike price {strike_price} on {expiration_date}")
                    return
                
                # Calculate PCR based on open interest
                put_call_ratio = put_oi.values[0] / call_oi.values[0]
                click.echo(f"Put/Call Ratio for {symbol} at strike {strike_price} on {expiration_date}:")
                click.echo(f"Put OI: {put_oi.values[0]}, Call OI: {call_oi.values[0]}, PCR: {put_call_ratio:.2f}")
        else:
            click.echo("Invalid configuration: please specify a range with --lower and --upper or provide a single strike in --date-strike")

if __name__ == "__main__":
    print(f"Running PCR Calculator version {VERSION}")
    calculate_put_call_ratio()
