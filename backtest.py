import pandas as pd
from binance.client import Client
import talib
import backtrader as bt

# Binance API anahtarlarınızı buraya ekleyin
api_key = 'API KEY'
api_secret = 'SECRET KEY'

# Binance Client objesini oluşturun
client = Client(api_key, api_secret)

# İstenen sembolü ve zaman aralığını belirleyin
symbol = 'AVAXTRY'
interval = '1h'

# Kripto verilerini çekin
klines = client.get_klines(symbol=symbol, interval=interval)
df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])

# Gereksiz sütunları kaldırın
df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

# Zaman sütununu düzenleyin
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# Sütun türlerini uygun şekilde dönüştürün
df = df.apply(pd.to_numeric, errors='coerce')

# NaN değerleri sıfırlarla doldurun
df.fillna(0, inplace=True)

# RSI hesapla
df['rsi'] = talib.RSI(df['close'], timeperiod=14)

# CCI hesapla
df['cci'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=14)

# Bollinger Bantları hesapla
df['upper_band'], df['middle_band'], df['lower_band'] = talib.BBANDS(df['close'], timeperiod=20)

# Basit Hareketli Ortalama hesapla
df['sma'] = talib.SMA(df['close'], timeperiod=20)

# Al/Sat sinyallerini üret
df['rsi'] = (df['rsi'] < 30) & (df['close'] < df['lower_band']) & (df['close'] < df['sma']) & (df['volume'] > df['volume'].rolling(window=20).mean())
df['cci'] = (df['cci'] < -100) & (df['close'] < df['lower_band']) & (df['close'] < df['sma']) & (df['volume'] > df['volume'].rolling(window=20).mean())
df['bollinger'] = (df['close'] < df['lower_band']) & (df['close'] < df['sma']) & (df['volume'] > df['volume'].rolling(window=20).mean())
df['sma'] = (df['close'] < df['lower_band']) & (df['close'] < df['sma']) & (df['volume'] > df['volume'].rolling(window=20).mean())
df['volume'] = (df['volume'] > df['volume'].rolling(window=20).mean())

# Al/Sat sinyallerini göster
signals = df[['rsi', 'cci', 'bollinger', 'sma', 'volume']]

# Çıktıyı bir dosyaya kaydet
signals.to_csv('signals_output.csv')

# Backtrader ile backtesting
class MyStrategy(bt.Strategy):
    params = (
        ("rsi_period", 14),
        ("sma_period", 20),
        ("bollinger_period", 20),
        ("bollinger_dev", 2),
        # Diğer parametreleri ekleyebilirsiniz
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=self.params.rsi_period)
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.sma_period)
        self.bollinger = bt.indicators.BollingerBands(self.data.close, period=self.params.bollinger_period, devfactor=self.params.bollinger_dev)
        self.volume = self.data.volume

    def next(self):
        if self.rsi < 30 and self.data.close[0] < self.bollinger.lines.bot.bot[0] and not self.position:
            # RSI < 30, fiyat bollinger alt bandının altında ve pozisyon yoksa alım yap
            self.buy()

        elif self.rsi > 70 and self.data.close[0] > self.bollinger.lines.bot.bot[0] and self.position:
            # RSI > 70, fiyat bollinger üst bandının üstünde ve pozisyon varsa satış yap
            self.sell()

    def stop(self):
        self.plot()

cerebro = bt.Cerebro()

# Veri çerçevesini tanımlayın
data = bt.feeds.PandasData(dataname=signals)

# Cerebro'ya veriyi ekleyin
cerebro.adddata(data)

# Stratejiyi Cerebro'ya ekleyin
cerebro.addstrategy(MyStrategy)

# Başlangıç sermayesini ve işlem komisyonlarını ayarlayın
cerebro.broker.set_cash(100000)
cerebro.broker.setcommission(commission=0.001)

# Backtesting işlemini başlatın
cerebro.run()

# Backtesting sonuçlarını görüntüleyin
cerebro.plot(style='candlestick')
