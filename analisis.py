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

import pandas as pd

def obtener_señal(df):
    # Paso 1: Verificamos que tengamos suficientes datos para los indicadores
    # El ADX y la SMA lenta necesitan al menos 21-25 velas
    if len(df) < 30: 
        return "ESPERAR"
    
    ultimo = df.iloc[-1]
    
    # --- Extracción de Indicadores ---
    ema = ultimo['EMA_RAPIDA']
    sma = ultimo['SMA_LENTA']
    plus_di = ultimo['plus_di']
    minus_di = ultimo['minus_di']
    adx = ultimo['ADX']
    rsi = ultimo['RSI']
    stoch_k = ultimo['STOCH_K']
    stoch_d = ultimo['STOCH_D']

    # Paso 2: Verificamos que no haya valores nulos (NaN)
    if pd.isna(adx) or pd.isna(rsi) or pd.isna(stoch_k):
        return "ESPERAR"

    # --- LÓGICA PARA COMPRA (LONG / ALCISTA) ---
    # 1. Tendencia: EMA por encima de SMA
    # 2. Fuerza: +DI por encima de -DI y ADX fuerte (> 20)
    # 3. Filtro RSI: Que no esté ya muy caro (< 65)
    # 4. Gatillo Estocástico: Cruce alcista (K > D)
    condicion_long = (
        (ema > sma) and 
        (plus_di > minus_di) and 
        (adx > 20) and 
        (rsi < 65) and 
        (stoch_k > stoch_d)
    )

    # --- LÓGICA PARA VENTA (SHORT / BAJISTA) ---
    # 1. Tendencia: EMA por debajo de SMA
    # 2. Fuerza: -DI por encima de +DI y ADX fuerte (> 20)
    # 3. Filtro RSI: Que no esté ya muy barato (> 35) para evitar vender en el piso
    # 4. Gatillo Estocástico: Cruce bajista (K < D)
    condicion_short = (
        (ema < sma) and 
        (minus_di > plus_di) and 
        (adx > 20) and 
        (rsi > 35) and 
        (stoch_k < stoch_d)
    )

    # --- RETORNO DE SEÑAL ---
    if condicion_long:
        return "COMPRA"
    elif condicion_short:
        return "SHORT"
    else:
        return "ESPERAR"