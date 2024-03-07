import pandas as pd
from binance.client import Client
import talib
import requests

response = requests.get('https://checkip.amazonaws.com/')
print(response.text)

# Binance API anahtarlarınızı buraya ekleyin
api_key = 'API KEY'
api_secret = 'SECRET KEY'

# Binance Client objesini oluşturun
client = Client(api_key, api_secret)

# İstenen sembolü ve zaman aralığını belirleyin
symbol = 'AVAXTRY'
interval = '1h'

# Sembol bilgilerini al
symbol_info = client.get_symbol_info(symbol)

# LOT_SIZE filtresini bul
lot_size_filter = next((filter_item for filter_item in symbol_info['filters'] if filter_item['filterType'] == 'LOT_SIZE'), None)

# LOT_SIZE filtresini kontrol et
if lot_size_filter is not None:
    min_qty = float(lot_size_filter['minQty'])
    step_size = float(lot_size_filter['stepSize'])
    target_quantity = 0.01
    # Eğer LOT_SIZE filtresi bulunduysa, target_quantity değerini uygun hale getir
    if lot_size_filter is not None:
        target_quantity = max(min_qty, target_quantity)
        target_quantity = round(target_quantity / step_size) * step_size

    # Eğer LOT_SIZE filtresi bulunamadıysa, hata mesajı yazdır
    else:
        print("LOT_SIZE filtresi bulunamadı.")

    # Eğer istediğiniz miktarı belirlenen filtre ile uygun hale getirdiyseniz, işlemi gerçekleştirin.
    print(f"{target_quantity} miktarı uygun hale getirildi: {target_quantity}")
    # execute_trade('BUY', rounded_quantity)  # Gerçek emir verme fonksiyonunu ekleyin

else:
    print("LOT_SIZE filtresi bulunamadı.")

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
df['rsi'] = talib.RSI(df['close'], timeperiod=7)

# CCI hesapla
df['cci'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=7)

# Bollinger Bantları hesapla
df['upper_band'], df['middle_band'], df['lower_band'] = talib.BBANDS(df['close'], timeperiod=20)

# Basit Hareketli Ortalama hesapla
df['sma'] = talib.SMA(df['close'], timeperiod=20)

# Al/Sat sinyallerini üret
# RSI sinyali
df['rsi_signal'] = (df['rsi'] < 30) & (df['close'] < df['lower_band']) & (df['close'] < df['sma']) & (df['volume'] > df['volume'].rolling(window=20).mean())
# RSI'nın 70'in üstünde olması durumunda satış sinyali
df['rsi_signal'] |= (df['rsi'] > 70)

df['cci_signal'] = (df['cci'] < -100) & (df['close'] < df['lower_band']) & (df['close'] < df['sma']) & (
            df['volume'] > df['volume'].rolling(window=20).mean())
df['bollinger_signal'] = (df['close'] < df['lower_band']) & (df['close'] < df['sma']) & (
            df['volume'] > df['volume'].rolling(window=20).mean())
df['sma_signal'] = (df['close'] < df['lower_band']) & (df['close'] < df['sma']) & (
            df['volume'] > df['volume'].rolling(window=20).mean())
df['volume_signal'] = (df['volume'] > df['volume'].rolling(window=20).mean())

# Satış sinyali için örnek bir sütun ekle
df['sell_signal'] = df['rsi_signal'] | df['cci_signal'] | df['bollinger_signal'] | df['sma_signal'] | df[
    'volume_signal']

# Alım sinyali için örnek bir sütun ekle
df['buy_signal'] = (df['rsi_signal'] | df['cci_signal'] | df['bollinger_signal'] | df['sma_signal'] | df[
    'volume_signal']) & ~df['sell_signal']  # Satış sinyali olmayan yerlerde alım sinyali

# Çıktıyı bir dosyaya kaydet
signals = df[['rsi_signal', 'cci_signal', 'bollinger_signal', 'sma_signal', 'volume_signal', 'sell_signal', 'buy_signal']]
signals.to_csv('signals_output.csv')

# Alım satım işlemlerini gerçekleştirmek için fonksiyon
# Alım satım işlemlerini gerçekleştirmek için fonksiyon
def execute_trade(row):
    try:
        order = None  # order değişkenini tanımlayın
        if row['buy_signal']:
            # Alım sinyali
            order = client.create_order(
                symbol='AVAXTRY',
                side='BUY',
                type='MARKET',
                quantity=balance# Alım miktarını isteğinize göre güncelleyin
            )
            print(f'Alım emri verildi - {symbol}')
        elif row['sell_signal']:
            # Satış sinyali
            # Satış emri için mevcut varlık miktarını al
            balance = client.get_asset_balance(asset='AVAX')['free']
            order = client.create_order(
                symbol='AVAXTRY',
                side='SELL',
                type='MARKET',
                quantity='0.01'
            )
            print(f'Satış emri verildi - {symbol}')

        if order is not None:
            print('Detaylar:', order)
        return True
    except Exception as e:
        print('Emir verme hatası:', e)
        return False

# Alım satım sinyallerine göre işlem gerçekleştir
for index, row in signals.iterrows():
    if row['buy_signal'] or row['sell_signal']:
        execute_trade(row)

# Eklenen çıktıyı görüntüle
print(signals)
