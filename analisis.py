import pandas as pd
import numpy as np
import os
import csv
from datetime import datetime

def calcular_indicadores(velas):
    columnas = ['Fecha', 'Apertura', 'Máximo', 'Mínimo', 'Cierre', 'Volumen']
    df = pd.DataFrame(velas, columns=columnas)
    
    # Medias Móviles
    df['EMA_RAPIDA'] = df['Cierre'].ewm(span=9, adjust=False).mean()
    df['SMA_LENTA'] = df['Cierre'].rolling(window=21).mean()
    
    # RSI
    delta = df['Cierre'].diff()
    ganancia = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    perdida = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = ganancia / perdida
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # STOCH_K
    bajo_min = df['Mínimo'].rolling(window=14).min()
    alto_max = df['Máximo'].rolling(window=14).max()
    df['STOCH_K'] = 100 * ((df['Cierre'] - bajo_min) / (alto_max - bajo_min))
    
    # ADX
    n = 14
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

def obtener_señal(df, posicion_actual):
    if len(df) < 22: return "ESPERAR" # Evita errores si no hay suficientes velas

    ult = df.iloc[-1]
    ant = df.iloc[-2]

    # Condiciones de apertura
    tendencia_fuerte = ult['ADX'] > 30
    cruce_alcista = (ant['EMA_RAPIDA'] <= ant['SMA_LENTA']) and (ult['EMA_RAPIDA'] > ult['SMA_LENTA'])
    cruce_bajista = (ant['EMA_RAPIDA'] >= ant['SMA_LENTA']) and (ult['EMA_RAPIDA'] < ult['SMA_LENTA'])

    if posicion_actual is None:
        if cruce_alcista and tendencia_fuerte and ult['RSI'] < 60:
            return "COMPRA"
        if cruce_bajista and tendencia_fuerte and ult['RSI'] > 40:
            return "SHORT"
    
    # Lógica de Cierre
    if posicion_actual == "LONG" and (ult['EMA_RAPIDA'] < ult['SMA_LENTA'] or ult['RSI'] > 75):
        return "CERRAR"
    if posicion_actual == "SHORT" and (ult['EMA_RAPIDA'] > ult['SMA_LENTA'] or ult['RSI'] < 25):
        return "CERRAR"

    return "ESPERAR"

def registrar_operacion(tipo, precio, rsi, adx, resultado, saldo):
    nombre_archivo = 'historial_operaciones.csv'
    existe = os.path.isfile(nombre_archivo)
    with open(nombre_archivo, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Fecha', 'Tipo', 'Precio', 'RSI', 'ADX', 'Ganancia', 'Saldo'])
        writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tipo, precio, rsi, adx, resultado, saldo])