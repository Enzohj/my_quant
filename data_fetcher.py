import akshare as ak
import pandas as pd
import os

CACHE_DIR = 'cache/us_daily'
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_stock_data(symbol='BABA', adjust="qfq", period=None, start_date:str=None, end_date:str=None):
    """
    Fetch stock data using AKShare
    
    Parameters:
    symbol (str): Stock symbol
    period (str): Data period (e.g., '1y', '6m', '1m')
    start_date (str): Start date for data fetching (YYYYMMDD)
    end_date (str): End date for data fetching (YYYYMMDD)
    adjust (str): Adjustment type (e.g., 'qfq', 'hfq')
    
    Returns:
    pd.DataFrame: Stock data with OHLCV columns
    """
    assert period is not None or (start_date is not None and end_date is not None), "Either period or start_date/end_date must be provided"
    try:
        # Fetch stock data
        if os.path.exists(f'{CACHE_DIR}/{symbol}_{adjust}.csv'):
            print('load from local cache')
            stock_data = pd.read_csv(f'{CACHE_DIR}/{symbol}_{adjust}.csv')
        else:
            print('load from remote')
            stock_data = ak.stock_us_daily(symbol=symbol, adjust=adjust)
            stock_data.to_csv(f'{CACHE_DIR}/{symbol}_{adjust}.csv', index=False)
        
        # Ensure the index is datetime
        stock_data['date'] = pd.to_datetime(stock_data['date'])
        stock_data.set_index('date', inplace=True)

        if period is not None:
            if period.endswith('y'):
                years = int(period[:-1])
                end_date = pd.Timestamp.now()
                start_date = end_date - pd.DateOffset(years=years)
            elif period.endswith('m'):
                months = int(period[:-1])
                end_date = pd.Timestamp.now()
                start_date = end_date - pd.DateOffset(months=months)
        else:
            start_date = pd.Timestamp(start_date)
            end_date = pd.Timestamp(end_date)
            if start_date > end_date:
                raise ValueError("start_date must be before end_date")
        
        # Filter data based on period
        stock_data = stock_data[(stock_data.index >= start_date) & (stock_data.index <= end_date)]

        # Rename columns to match backtrader requirements
        stock_data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        
        # Ensure data is sorted by date
        stock_data.sort_index(inplace=True)
        
        return stock_data
    
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return None



if __name__ == "__main__":
    STOCK_SYMBOL = 'BABA'
    DATA_PERIOD = '1y'
    # START_DATE and END_DATE are not needed when using period parameter
    # START_DATE = '20250101'
    # END_DATE = '20250701'
    
    print(f"Fetching data for {STOCK_SYMBOL}...")
    data = fetch_stock_data(symbol=STOCK_SYMBOL, period=DATA_PERIOD)
    # data = fetch_stock_data(symbol=STOCK_SYMBOL, start_date=START_DATE, end_date=END_DATE)
    if data is not None:
        print(f"Data shape: {data.shape}")
        print(data.head())
    else:
        print("Failed to fetch data")