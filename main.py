import pandas as pd
from binance.client import Client
import talib

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

# Eklenen çıktıyı görüntüle
print(signals)