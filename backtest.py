import pandas as pd
import ccxt
import analisis as al
import config
import os
import csv
from datetime import datetime

def obtener_datos_historicos(simbolo, temporalidad, limite):
    exchange = ccxt.binance()
    print(f"--- Descargando {limite} velas de {simbolo} ({temporalidad}) ---")
    ohlcv = exchange.fetch_ohlcv(simbolo, timeframe=temporalidad, limit=limite)
    df = pd.DataFrame(ohlcv, columns=['Fecha', 'Apertura', 'Máximo', 'Mínimo', 'Cierre', 'Volumen'])
    df['Fecha'] = pd.to_datetime(df['Fecha'], unit='ms')
    return df

def registrar_operacion_csv(tipo, precio, rsi, adx, resultado, saldo):
    """Guarda el detalle de cada trade en un archivo CSV."""
    nombre_archivo = 'historial_backtest.csv'
    existe = os.path.isfile(nombre_archivo)
    with open(nombre_archivo, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Fecha', 'Tipo', 'Precio', 'RSI', 'ADX', 'Ganancia', 'Saldo'])
        writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tipo, precio, rsi, adx, resultado, saldo])

def correr_backtest():
    # 1. Preparación - Aumentamos a 30,000 para tener más datos
    df = obtener_datos_historicos(config.SIMBOLO, config.TEMPORALIDAD, 30000)
    df = al.calcular_indicadores(df) 
    
    saldo = config.SALDO_INICIAL_USD
    posicion = None
    precio_entrada = 0
    trades_totales = 0
    ganados = 0
    capital_arriesgado = 0

    print(f"\nIniciando simulación con ${saldo} USD...")
    print(f"Interés Compuesto: {'SÍ' if config.USAR_INTERES_COMPUESTO else 'NO'}")
    print("-" * 50)

    # 2. Simulación
    for i in range(250, len(df)): 
        ventana = df.iloc[:i+1]
        fila_actual = df.iloc[i]
        precio = fila_actual['Cierre']
        
        # Lógica de Apertura
        if posicion is None:
            señal = al.obtener_señal(ventana, posicion)
            if señal in ["COMPRA", "SHORT"]:
                posicion = "LONG" if señal == "COMPRA" else "SHORT"
                precio_entrada = precio
                trades_totales += 1
                
                if config.USAR_INTERES_COMPUESTO:
                    capital_arriesgado = saldo * (config.PORCENTAJE_POR_TRADE / 100)
                else:
                    capital_arriesgado = config.SALDO_INICIAL_USD

        # Lógica de Cierre
        elif posicion is not None:
            señal_cierre = al.obtener_señal(ventana, posicion) == "CERRAR"
            break_even = al.gestionar_salida_dinamica(precio, precio_entrada, posicion)

            if señal_cierre or break_even:
                motivo = "INDICADOR" if señal_cierre else "BREAK_EVEN"
                
                if posicion == "LONG":
                    resultado_pct = (precio - precio_entrada) / precio_entrada
                else:
                    resultado_pct = (precio_entrada - precio) / precio_entrada
                
                neto = (resultado_pct * capital_arriesgado) - (capital_arriesgado * config.COMISION_EXCHANGE)
                saldo += neto
                
                if neto > 0: ganados += 1
                
                # REGISTRO EN CSV Y CONSOLA
                registrar_operacion_csv(
                    posicion, 
                    precio, 
                    round(fila_actual['RSI'], 2), 
                    round(fila_actual['ADX'], 2), 
                    round(neto, 2), 
                    round(saldo, 2)
                )
                
                print(f"Trade {trades_totales}: {posicion} | Motivo: {motivo} | Neto: ${neto:.2f} | Saldo: ${saldo:.2f}")
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