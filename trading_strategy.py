import backtrader as bt
import backtrader.talib as btalib
import quantstats as qs
import pandas as pd
from data_fetcher import fetch_stock_data

class MultiIndicatorStrategy(bt.Strategy):
    params = (
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
        ('rsi_period', 14),
        ('rsi_upper', 70),
        ('rsi_lower', 30),
        ('kdj_period', 9),
        ('kdj_slow', 3),
        ('kdj_fast', 3),
        ('boll_period', 20),
        ('boll_dev', 2.0),
        ('risk_percent', 0.02),
    )

    def __init__(self):
        # Initialize indicators
        self.macd = btalib.MACD(
            self.data.close,
            fastperiod=self.p.macd1,
            slowperiod=self.p.macd2,
            signalperiod=self.p.macdsig
        )

        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.p.rsi_period
        )

        # KDJ implementation using STOCH from TA-Lib
        self.stoch = btalib.STOCH(
            self.data.high,
            self.data.low,
            self.data.close,
            fastk_period=self.p.kdj_period,
            slowk_period=self.p.kdj_slow,
            slowk_matype=0,
            slowd_period=self.p.kdj_fast,
            slowd_matype=0
        )
        self.k = self.stoch.lines.slowk
        self.d = self.stoch.lines.slowd
        self.j = 3 * self.k - 2 * self.d  # Standard J line calculation (J = 3K - 2D)

        # Bollinger Bands
        self.boll = bt.indicators.BollingerBands(
            self.data.close,
            period=self.p.boll_period,
            devfactor=self.p.boll_dev
        )

        # Track pending orders and position
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # Track portfolio values for performance analysis
        self.portfolio_values = []
        self.dates = []

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'TRADE PROFIT, Gross: {trade.pnl:.2f}, Net: {trade.pnlcomm:.2f}')

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def next(self):
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Buy conditions
            buy_conditions = [
                # MACD crossover above signal
                self.macd.macd[-1] < self.macd.macdsignal[-1] and self.macd.macd[0] > self.macd.macdsignal[0],
                # RSI below lower threshold
                self.rsi[0] < self.p.rsi_lower,
                # KDJ crossover (K line crosses above D line)
                self.k[-1] < self.d[-1] and self.k[0] > self.d[0],
                # Price below lower Bollinger Band
                self.data.close[0] < self.boll.lines.bot[0]
            ]

            if any(buy_conditions):
                self.log('BUY CREATE, %.2f' % self.data.close[0])
                # Calculate position size based on risk percentage
                risk_amount = self.broker.getvalue() * self.p.risk_percent
                # Calculate position size with safety checks
                if self.data.close[0] > 0:
                    size = int(risk_amount / (self.data.close[0] * 1.01))  # 1% buffer
                    size = max(1, size)  # Ensure minimum position size of 1
                else:
                    self.log("Invalid price data, cannot calculate position size")
                    return
                self.order = self.buy(size=size)
        else:
            # Sell conditions
            sell_conditions = [
                # MACD crossover below signal
                self.macd.macd[-1] > self.macd.macdsignal[-1] and self.macd.macd[0] < self.macd.macdsignal[0],
                # RSI above upper threshold
                self.rsi[0] > self.p.rsi_upper,
                # KDJ crossover (K line crosses below D line)
                self.k[-1] > self.d[-1] and self.k[0] < self.d[0],
                # Price above upper Bollinger Band
                self.data.close[0] > self.boll.lines.top[0]
            ]

            if any(sell_conditions):
                self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.order = self.sell(size=self.position.size)
        
        # Record portfolio value and date
        self.portfolio_values.append(self.broker.getvalue())
        self.dates.append(self.data.datetime.datetime(0))

def run_backtest():
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(MultiIndicatorStrategy)

    # Load data
    df = fetch_stock_data(symbol='BABA', period='1y')
    if df is None or df.empty:
        print("No data available for backtesting.")
        return

    # Create a Data Feed
    data = bt.feeds.PandasData(
            dataname=df,
            open='Open',
            high='High',
            low='Low',
            close='Close',
            volume='Volume',
            openinterest=None
        )

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(100000.0)

    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # Set the commission - 0.1% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.001)

    # Run over everything
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plot the result
    img = cerebro.plot(style='candlestick')
    # save the plot
    img[0][0].savefig('baba_strategy.png')

    # Extract strategy returns for QuantStats
    strategy = results[0]
    if len(strategy.portfolio_values) == 0:
        print("No portfolio values recorded. Cannot generate report.")
        return
    
    # Create returns series from portfolio values
    returns = pd.Series(strategy.portfolio_values, index=pd.DatetimeIndex(strategy.dates).tz_localize('UTC'))
    returns = returns.pct_change().fillna(0)

    # Generate QuantStats report
    qs.reports.html(returns, output='strategy_performance.html', title='BABA Trading Strategy Performance')
    print('QuantStats report generated: strategy_performance.html')


if __name__ == '__main__':
    run_backtest()