# analisis.py
import pandas as pd
import numpy as np
import os
import csv
import config
from datetime import datetime

def calcular_indicadores(df):
    # 1. Bandas de Bollinger
    df['SMA_20'] = df['Cierre'].rolling(window=20).mean()
    df['STD'] = df['Cierre'].rolling(window=20).std()
    df['Banda_Sup'] = df['SMA_20'] + (df['STD'] * 2)
    df['Banda_Inf'] = df['SMA_20'] - (df['STD'] * 2)
    
    # 2. RSI
    delta = df['Cierre'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 3. ATR y ADX (Para evitar errores en backtest.py)
    high_low = df['Máximo'] - df['Mínimo']
    high_close = abs(df['Máximo'] - df['Cierre'].shift())
    low_close = abs(df['Mínimo'] - df['Cierre'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = ranges.max(axis=1).rolling(window=14).mean()
    
    plus_dm = df['Máximo'].diff()
    minus_dm = df['Mínimo'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    plus_di = 100 * (plus_dm.rolling(window=14).mean() / df['ATR'])
    minus_di = 100 * (abs(minus_dm.rolling(window=14).mean()) / df['ATR'])
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['ADX'] = dx.rolling(window=14).mean()

    # 4. Filtro de Tendencia EMA 100
    df['EMA_100'] = df['Cierre'].ewm(span=100, adjust=False).mean()
    
    return df

def obtener_señal(df, posicion_actual, precio_entrada_operacion=None, ultimo_resultado=None):
    if len(df) < 100: return "ESPERAR"
    
    ult = df.iloc[-1]
    precio = ult['Cierre']
    adx = ult['ADX'] # Usamos el ADX que ya calculamos
    
    if posicion_actual is None:
        distancia_ema = abs(precio - ult['EMA_100']) / ult['EMA_100'] * 100

        # --- FILTRO ADX: No entrar si la tendencia es DEMASIADO fuerte ---
        # Si el ADX > 35, el mercado está en un rally o desplome violento. 
        # Es mejor no jugar a la reversión ahí.
        if adx > 35:
            return "ESPERAR"

        # ENTRADA LONG: Solo si el ADX es moderado (evita cuchillos cayendo)
        if precio <= ult['Banda_Inf'] and ult['RSI'] < 32:
            if precio > ult['EMA_100'] or distancia_ema < 0.15:
                return "COMPRA"
        
        # ENTRADA SHORT: Solo si el ADX es moderado
        if precio >= ult['Banda_Sup'] and ult['RSI'] > 68:
            if precio < ult['EMA_100'] or distancia_ema < 0.15:
                return "SHORT"
            
    else:
        # Cálculo de ganancia
        if posicion_actual == "LONG":
            ganancia_pct = ((precio - precio_entrada_operacion) / precio_entrada_operacion) * 100
        else:
            ganancia_pct = ((precio_entrada_operacion - precio) / precio_entrada_operacion) * 100
        
        # 1. Stop Loss más ajustado ante volatilidad alta
        # Si el ADX es alto, acortamos el Stop Loss para salir rápido si falla
        stop_loss_dinamico = -0.75 if adx < 30 else -0.50
        if ganancia_pct <= stop_loss_dinamico: 
            return "CERRAR"
        
        # 2. Salidas optimizadas
        if posicion_actual == "LONG":
            if ganancia_pct > 1.2 and precio < precio_entrada_operacion * 1.008:
                return "CERRAR"
            if precio >= ult['SMA_20'] and ult['RSI'] > 74: 
                return "CERRAR"
        else:
            if ganancia_pct > 1.2 and precio > precio_entrada_operacion * 0.992:
                return "CERRAR"
            if precio <= ult['SMA_20'] and ult['RSI'] < 24: 
                return "CERRAR"
            
    return "ESPERAR"