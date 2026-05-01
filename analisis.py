import pandas as pd
import numpy as np

def calcular_indicadores(velas):
    columnas = ['Fecha', 'Apertura', 'Máximo', 'Mínimo', 'Cierre', 'Volumen']
    df = pd.DataFrame(velas, columns=columnas)
    
    # --- MEDIAS MÓVILES ---
    df['SMA_LENTA'] = df['Cierre'].rolling(window=21).mean()
    df['EMA_RAPIDA'] = df['Cierre'].ewm(span=9, adjust=False).mean()
    
    # --- RSI (Relative Strength Index) ---
    delta = df['Cierre'].diff()
    ganancia = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    perdida = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = ganancia / perdida
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # --- ESTOCÁSTICO RÁPIDO (%K y %D) ---
    bajo_min = df['Mínimo'].rolling(window=14).min()
    alto_max = df['Máximo'].rolling(window=14).max()
    df['STOCH_K'] = 100 * ((df['Cierre'] - bajo_min) / (alto_max - bajo_min))
    df['STOCH_D'] = df['STOCH_K'].rolling(window=3).mean()
    
    # --- DMI / ADX ---
    n = 14
    df['up'] = df['Máximo'].diff()
    df['down'] = -df['Mínimo'].diff()
    df['plus_dm'] = np.where((df['up'] > df['down']) & (df['up'] > 0), df['up'], 0)
    df['minus_dm'] = np.where((df['down'] > df['up']) & (df['down'] > 0), df['down'], 0)
    df['tr'] = np.maximum(df['Máximo'] - df['Mínimo'], 
               np.maximum(abs(df['Máximo'] - df['Cierre'].shift(1)), 
                          abs(df['Mínimo'] - df['Cierre'].shift(1))))
    tr_smooth = df['tr'].rolling(n).sum()
    df['plus_di'] = 100 * (df['plus_dm'].rolling(n).sum() / tr_smooth)
    df['minus_di'] = 100 * (df['minus_dm'].rolling(n).sum() / tr_smooth)
    dx = 100 * (abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']))
    df['ADX'] = dx.rolling(n).mean()
    
    return df

def obtener_señal(df):
    if len(df) < 30: return "ESPERAR"
    ultimo = df.iloc[-1]
    
    # Variables
    ema, sma = ultimo['EMA_RAPIDA'], ultimo['SMA_LENTA']
    plus_di, minus_di, adx = ultimo['plus_di'], ultimo['minus_di'], ultimo['ADX']
    rsi = ultimo['RSI']
    stoch_k, stoch_d = ultimo['STOCH_K'], ultimo['STOCH_D']
    
    if pd.isna(adx) or pd.isna(rsi): return "ESPERAR"

    # --- NUEVA LÓGICA DE SUPER CONFIRMACIÓN ---
    # COMPRA si:
    # 1. Tendencia: EMA > SMA
    # 2. Fuerza: +DI > -DI y ADX > 20
    # 3. Impulso: RSI < 70 (no está sobrecomprado)
    # 4. Gatillo: Estocástico K cruza sobre D
    compra = (ema > sma) and (plus_di > minus_di) and (adx > 20) and (rsi < 70) and (stoch_k > stoch_d)

    # VENTA si:
    # 1. EMA cruza abajo de SMA
    # 2. O si el RSI > 80 (extrema sobrecompra, mejor asegurar)
    # 3. O si -DI > +DI
    venta = (ema < sma) or (rsi > 80) or (minus_di > plus_di)

    if compra: return "COMPRA"
    if venta: return "VENTA"
    return "ESPERAR"