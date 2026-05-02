import pandas as pd
import ccxt
import analisis as al
import config
from datetime import datetime

def obtener_datos_historicos(simbolo, temporalidad, limite):
    exchange = ccxt.binance()
    print(f"--- Descargando {limite} velas de {simbolo} ({temporalidad}) ---")
    ohlcv = exchange.fetch_ohlcv(simbolo, timeframe=temporalidad, limit=limite)
    df = pd.DataFrame(ohlcv, columns=['Fecha', 'Apertura', 'Máximo', 'Mínimo', 'Cierre', 'Volumen'])
    df['Fecha'] = pd.to_datetime(df['Fecha'], unit='ms')
    return df

def correr_backtest():
    # 1. Preparación
    df = obtener_datos_historicos(config.SIMBOLO, config.TEMPORALIDAD, 1000)
    df = al.calcular_indicadores(df.values.tolist()) # Reusamos tu lógica de cálculo
    
    saldo = config.SALDO_INICIAL_USD
    posicion = None
    precio_entrada = 0
    trades_totales = 0
    ganados = 0

    print(f"\nIniciando simulación con ${saldo} USD...")
    print("-" * 50)

    # 2. Simulación fila por fila (como si pasara el tiempo)
    for i in range(25, len(df)): # Empezamos en 25 para tener datos de SMA21
        ventana = df.iloc[:i+1]
        fila_actual = df.iloc[i]
        precio = fila_actual['Cierre']
        
        # Pedimos señal al cerebro que ya armamos
        señal = al.obtener_señal(ventana, posicion)

        # Lógica de Apertura
        if posicion is None:
            if señal == "COMPRA":
                posicion = "LONG"
                precio_entrada = precio
                trades_totales += 1
            elif señal == "SHORT":
                posicion = "SHORT"
                precio_entrada = precio
                trades_totales += 1

        # Lógica de Cierre
        elif señal == "CERRAR":
            if posicion == "LONG":
                resultado = (precio - precio_entrada) * (saldo / precio_entrada)
            else:
                resultado = (precio_entrada - precio) * (saldo / precio_entrada)
            
            # Restamos comisión
            comision = saldo * config.COMISION_EXCHANGE
            neto = resultado - comision
            saldo += neto
            
            if neto > 0: ganados += 1
            
            print(f"Trade {trades_totales}: {posicion} | Salida: ${precio:.2f} | Neto: ${neto:.2f} | Saldo: ${saldo:.2f}")
            posicion = None

    # 3. Resultados Finales
    print("-" * 50)
    print(f"RESULTADOS FINALES:")
    print(f"Saldo Final: ${saldo:.2f}")
    print(f"Rendimiento: {((saldo/config.SALDO_INICIAL_USD)-1)*100:.2f}%")
    print(f"Total Trades: {trades_totales}")
    if trades_totales > 0:
        print(f"Win Rate: {(ganados/trades_totales)*100:.2f}%")

if __name__ == "__main__":
    correr_backtest()