import pandas as pd
import numpy as np
import os
import csv
import config
from datetime import datetime

def calcular_indicadores(velas):
    columnas = ['Fecha', 'Apertura', 'Máximo', 'Mínimo', 'Cierre', 'Volumen']
    df = pd.DataFrame(velas, columns=columnas)
    
    # 1. Volatilidad (ATR)
    df['ATR'] = calcular_atr(df, config.PERIODO_ATR)

    # 2. Medias Móviles (Rápida, Lenta y Filtro Macro)
    df['EMA_RAPIDA'] = df['Cierre'].ewm(span=config.EMA_RAPIDA, adjust=False).mean()
    df['SMA_LENTA'] = df['Cierre'].rolling(window=config.SMA_LENTA).mean()
    df['EMA_200'] = df['Cierre'].ewm(span=config.EMA_MACRO, adjust=False).mean()
    
    # 3. RSI
    delta = df['Cierre'].diff()
    ganancia = (delta.where(delta > 0, 0)).rolling(window=config.RSI_PERIODO).mean()
    perdida = (-delta.where(delta < 0, 0)).rolling(window=config.RSI_PERIODO).mean()
    rs = ganancia / perdida
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 4. STOCH_K
    bajo_min = df['Mínimo'].rolling(window=14).min()
    alto_max = df['Máximo'].rolling(window=14).max()
    df['STOCH_K'] = 100 * ((df['Cierre'] - bajo_min) / (alto_max - bajo_min))
    
    # 5. ADX (Cálculo optimizado)
    n = config.ADX_PERIODO
    df['tr'] = np.maximum(df['Máximo'] - df['Mínimo'], 
               np.maximum(abs(df['Máximo'] - df['Cierre'].shift(1)), 
                          abs(df['Mínimo'] - df['Cierre'].shift(1))))
    df['up'] = df['Máximo'].diff()
    df['down'] = -df['Mínimo'].diff()
    df['plus_dm'] = np.where((df['up'] > df['down']) & (df['up'] > 0), df['up'], 0)
    df['minus_dm'] = np.where((df['down'] > df['up']) & (df['down'] > 0), df['down'], 0)
    
    tr_s = df['tr'].rolling(n).sum()
    df['plus_di'] = 100 * (df['plus_dm'].rolling(n).sum() / tr_s)
    df['minus_di'] = 100 * (df['minus_dm'].rolling(n).sum() / tr_s)
    dx = 100 * (abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']))
    df['ADX'] = dx.rolling(n).mean()
    
    return df

def calcular_atr(df, window=14):
    """Calcula el Average True Range."""
    high_low = df['Máximo'] - df['Mínimo']
    high_close = abs(df['Máximo'] - df['Cierre'].shift())
    low_close = abs(df['Mínimo'] - df['Cierre'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(window=window).mean()

def obtener_señal(df, posicion_actual):
    if len(df) < config.EMA_MACRO: return "ESPERAR" 

    ult = df.iloc[-1]
    ant = df.iloc[-2]

    # Filtros de Seguridad
    tendencia_fuerte = ult['ADX'] >= config.ADX_MINIMO
    precio_sobre_ema200 = ult['Cierre'] > ult['EMA_200']
    
    # Cruces de Medias
    cruce_alcista = (ant['EMA_RAPIDA'] <= ant['SMA_LENTA']) and (ult['EMA_RAPIDA'] > ult['SMA_LENTA'])
    cruce_bajista = (ant['EMA_RAPIDA'] >= ant['SMA_LENTA']) and (ult['EMA_RAPIDA'] < ult['SMA_LENTA'])

    # --- LÓGICA DE APERTURA ---
    if posicion_actual is None:
        # COMPRA (LONG): Cruce + Tendencia + Arriba de EMA 200 + RSI no saturado
        if cruce_alcista and tendencia_fuerte and precio_sobre_ema200 and ult['RSI'] < config.RSI_LIMITE_LONG:
            return "COMPRA"
        
        # VENTA (SHORT): Cruce + Tendencia + Abajo de EMA 200 + RSI no saturado
        if cruce_bajista and tendencia_fuerte and not precio_sobre_ema200 and ult['RSI'] > config.RSI_LIMITE_SHORT:
            return "SHORT"
    
    # --- LÓGICA DE CIERRE ---
    if posicion_actual == "LONG":
        if cruce_bajista or ult['RSI'] > 75: return "CERRAR"
        
    if posicion_actual == "SHORT":
        if cruce_alcista or ult['RSI'] < 25: return "CERRAR"

    return "ESPERAR"

def gestionar_salida_dinamica(precio_actual, precio_entrada, posicion):
    """Protección de Capital: Break Even."""
    if precio_entrada == 0: return False

    if posicion == "LONG":
        ganancia_pct = ((precio_actual - precio_entrada) / precio_entrada) * 100
    else:
        ganancia_pct = ((precio_entrada - precio_actual) / precio_entrada) * 100

    if ganancia_pct >= config.ACTIVACION_BREAK_EVEN:
        if posicion == "LONG" and precio_actual <= precio_entrada:
            return True
        if posicion == "SHORT" and precio_actual >= precio_entrada:
            return True

    return False

def registrar_operacion(tipo, precio, rsi, adx, resultado, saldo):
    nombre_archivo = 'historial_operaciones.csv'
    existe = os.path.isfile(nombre_archivo)
    with open(nombre_archivo, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Fecha', 'Tipo', 'Precio', 'RSI', 'ADX', 'Ganancia', 'Saldo'])
        writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tipo, precio, rsi, adx, resultado, saldo])