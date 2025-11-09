# New file: portfolio_manager.py
from datetime import datetime, timedelta
import numpy as np
from db import db

class PortfolioManager:
    def __init__(self, user_id='default'):
        self.user_id = user_id
        self.portfolios_coll = db['portfolios']
        self.transactions_coll = db['portfolio_transactions']
    
    def execute_trade(self, symbol, action, quantity, price):
        """Execute a buy or sell trade with validation"""
        portfolio = self.portfolios_coll.find_one({'user_id': self.user_id})
        
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
        
        # Calculate new total value (simplified - in reality, you'd fetch current prices)
        new_total_value = new_cash + self.calculate_holdings_value(holdings)
        
        # Update portfolio in database
        update_result = self.portfolios_coll.update_one(
            {'user_id': self.user_id},
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
        self.record_transaction(symbol, action, quantity, price)
        
        return {
            'success': True,
            'new_cash_balance': new_cash,
            'new_holdings': holdings,
            'total_value': new_total_value
        }
    
    def calculate_holdings_value(self, holdings):
        """Calculate current value of all holdings"""
        total_value = 0
        for symbol, quantity in holdings.items():
            try:
                ticker = yf.Ticker(symbol)
                current_data = ticker.history(period='1d')
                if not current_data.empty:
                    current_price = current_data['Close'].iloc[-1]
                    total_value += quantity * current_price
            except:
                # If we can't get current price, use last transaction price
                continue
        return total_value
    
    def record_transaction(self, symbol, action, quantity, price):
        """Record a transaction"""
        transaction = {
            'portfolio_id': self.user_id,
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': price,
            'total_amount': quantity * price,
            'timestamp': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        self.transactions_coll.insert_one(transaction)
    
    def get_performance_metrics(self):
        """Calculate portfolio performance metrics"""
        portfolio = self.portfolios_coll.find_one({'user_id': self.user_id})
        transactions = list(self.transactions_coll.find(
            {'portfolio_id': self.user_id}
        ).sort('timestamp', 1))
        
        if not portfolio or not transactions:
            return {}
        
        initial_capital = 10000  # Assuming fixed initial capital
        current_value = portfolio['total_value']
        total_return = ((current_value - initial_capital) / initial_capital) * 100
        
        # Calculate daily returns for volatility and Sharpe ratio
        daily_returns = self.calculate_daily_returns(transactions)
        
        metrics = {
            'initial_capital': initial_capital,
            'current_value': current_value,
            'total_return_percent': round(total_return, 2),
            'total_return_dollar': round(current_value - initial_capital, 2),
            'cash_balance': portfolio['cash_balance'],
            'number_of_holdings': len(portfolio.get('holdings', {})),
            'number_of_trades': len(transactions)
        }
        
        if daily_returns:
            volatility = np.std(daily_returns) * np.sqrt(252)  # Annualized
            sharpe_ratio = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
            
            metrics.update({
                'volatility': round(volatility, 4),
                'sharpe_ratio': round(sharpe_ratio, 2)
            })
        
        return metrics
    
    def calculate_daily_returns(self, transactions):
        """Calculate daily portfolio returns from transactions"""
        # This is a simplified version - in reality, you'd track portfolio value daily
        returns = []
        for i in range(1, len(transactions)):
            prev_value = transactions[i-1]['total_amount']
            curr_value = transactions[i]['total_amount']
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)
        return returns

# Helper functions for the API routes
def execute_trade(user_id, symbol, action, quantity, price):
    pm = PortfolioManager(user_id)
    return pm.execute_trade(symbol, action, quantity, price)

def calculate_portfolio_performance(user_id):
    pm = PortfolioManager(user_id)
    return pm.get_performance_metrics()