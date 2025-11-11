from pymongo import MongoClient
import pandas as pd
from datetime import datetime

client = MongoClient('mongodb://localhost:27017/')
db = client['stock_forecast_db']

def get_instruments():
    # Use real MongoDB data instead of mock data
    instruments_coll = db['instruments']
    instruments = list(instruments_coll.find({}, {'_id': 0}))  # Exclude MongoDB _id
    return instruments

def store_historical_data(symbol, df):
    historical_coll = db['historical_prices']
    for _, row in df.iterrows():
        doc = {
            'instrument_id': symbol,
            'timestamp': row.name.isoformat(),
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': int(row['Volume']),
            'created_at': datetime.now().isoformat()
        }
        historical_coll.update_one(
            {'instrument_id': symbol, 'timestamp': doc['timestamp']},
            {'$set': doc},
            upsert=True
        )

def get_historical_data(symbol, start_date, end_date):
    historical_coll = db['historical_prices']
    query = {
        'instrument_id': symbol,
        'timestamp': {'$gte': start_date.isoformat(), '$lte': end_date.isoformat()}
    }
    data = list(historical_coll.find(query).sort('timestamp', 1))
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.drop('_id', axis=1, inplace=True)
    return df[['open', 'high', 'low', 'close', 'volume']]

def store_forecasts(symbol, horizon, model_id, forecasts):
    try:
        forecasts_coll = db['forecasts']
        
        # Make a COPY to avoid mutating original
        docs_to_insert = []
        for f in forecasts:
            doc = f.copy()  # Don't modify original
            doc.update({
                'symbol': symbol,
                'horizon': horizon,
                'model_id': model_id
            })
            docs_to_insert.append(doc)
        
        # Insert without returning _id into original list
        result = forecasts_coll.insert_many(docs_to_insert)
        
        # Optional: log IDs, but NEVER modify `forecasts`
        logger.info(f"Stored {len(result.inserted_ids)} forecasts")
        
        return True
    except Exception as e:
        logger.error(f"Failed to store forecasts: {e}")
        raise
    
# Add these portfolio functions to your db.py

def create_initial_portfolio(user_id='default', initial_capital=10000):
    """Create a starting portfolio for a user"""
    portfolio_coll = db['portfolios']
    
    portfolio = {
        'user_id': user_id,
        'cash_balance': float(initial_capital),
        'holdings': {},  # {symbol: quantity}
        'total_value': float(initial_capital),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    portfolio_coll.update_one(
        {'user_id': user_id},
        {'$set': portfolio},
        upsert=True
    )
    return portfolio

def execute_trade(user_id, symbol, action, quantity, price):
    """Execute a buy/sell trade"""
    portfolio_coll = db['portfolios']
    transactions_coll = db['portfolio_transactions']
    
    # Get current portfolio
    portfolio = portfolio_coll.find_one({'user_id': user_id})
    if not portfolio:
        raise Exception("Portfolio not found")
    
    total_cost = quantity * price
    
    if action == 'buy':
        if portfolio['cash_balance'] < total_cost:
            raise Exception("Insufficient funds")
        
        # Update portfolio
        new_cash = portfolio['cash_balance'] - total_cost
        holdings = portfolio.get('holdings', {})
        current_quantity = holdings.get(symbol, 0)
        holdings[symbol] = current_quantity + quantity
        
    elif action == 'sell':
        holdings = portfolio.get('holdings', {})
        current_quantity = holdings.get(symbol, 0)
        
        if current_quantity < quantity:
            raise Exception("Insufficient shares")
        
        # Update portfolio
        new_cash = portfolio['cash_balance'] + total_cost
        holdings[symbol] = current_quantity - quantity
        
        # Remove symbol if quantity becomes zero
        if holdings[symbol] == 0:
            del holdings[symbol]
    else:
        raise Exception("Invalid action")
    
    # Calculate new total value (simplified - we'll enhance this later)
    new_total_value = new_cash
    
    # Update portfolio in database
    portfolio_coll.update_one(
        {'user_id': user_id},
        {
            '$set': {
                'cash_balance': new_cash,
                'holdings': holdings,
                'total_value': new_total_value,
                'updated_at': datetime.now().isoformat()
            }
        }
    )
    
    # Record transaction
    transaction = {
        'portfolio_id': user_id,
        'symbol': symbol,
        'action': action,
        'quantity': quantity,
        'price': price,
        'total_amount': total_cost,
        'timestamp': datetime.now().isoformat(),
        'created_at': datetime.now().isoformat()
    }
    
    transactions_coll.insert_one(transaction)
    
    return {
        'success': True,
        'new_cash_balance': new_cash,
        'new_holdings': holdings,
        'total_value': new_total_value
    }

def calculate_portfolio_performance(user_id):
    """Calculate portfolio performance metrics"""
    portfolio_coll = db['portfolios']
    transactions_coll = db['portfolio_transactions']
    
    portfolio = portfolio_coll.find_one({'user_id': user_id})
    if not portfolio:
        raise Exception("Portfolio not found")
    
    initial_capital = 10000  # Assuming fixed initial capital
    current_value = portfolio['total_value']
    total_return = ((current_value - initial_capital) / initial_capital) * 100
    
    metrics = {
        'initial_capital': initial_capital,
        'current_value': current_value,
        'total_return_percent': round(total_return, 2),
        'total_return_dollar': round(current_value - initial_capital, 2),
        'cash_balance': portfolio['cash_balance'],
        'number_of_holdings': len(portfolio.get('holdings', {})),
        'number_of_trades': transactions_coll.count_documents({'portfolio_id': user_id})
    }
    
    return metrics