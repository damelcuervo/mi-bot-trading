import pandas as pd
import ccxt
import analisis as al
import config
import os
import csv
from datetime import datetime
import time


def obtener_datos_historicos(simbolo, temporalidad, limite):
    exchange = ccxt.binance()
    ahora = int(time.time() * 1000)
    
    # Calculamos cuánto tiempo atrás ir basándonos en el límite de velas
    # 15m son 15 * 60 * 1000 milisegundos
    ms_por_vela = 15 * 60 * 1000 # Ajustar si cambias la temporalidad
    desde_ms = ahora - (limite * ms_por_vela)
    
    ohlcv_total = []
    
    print(f"--- Descargando {limite} velas de {simbolo} ({temporalidad}) ---")
    
    while len(ohlcv_total) < limite:
        # Calculamos cuántas faltan para no bajar de más
        faltan = limite - len(ohlcv_total)
        current_limit = min(faltan, 1000) # Máximo 1000 por pedido
        
        try:
            # Pedimos el bloque de velas
            bloque = exchange.fetch_ohlcv(simbolo, timeframe=temporalidad, since=desde_ms, limit=current_limit)
            
            if not bloque:
                break
                
            ohlcv_total.extend(bloque)
            
            # Actualizamos el puntero: la siguiente tanda empieza 1ms después de la última vela recibida
            desde_ms = bloque[-1][0] + 1
            
            # Imprimimos progreso para no aburrirnos
            print(f"Progreso: {len(ohlcv_total)} / {limite} velas", end="\r")
            
            # Un pequeño delay para que Binance no nos bloquee
            time.sleep(0.1)
            
        except Exception as e:
            print(f"\nError en la descarga: {e}")
            break

    print(f"\n--- Descarga completada: {len(ohlcv_total)} velas ---")
    
    df = pd.DataFrame(ohlcv_total, columns=['Fecha', 'Apertura', 'Máximo', 'Mínimo', 'Cierre', 'Volumen'])
    df['Fecha'] = pd.to_datetime(df['Fecha'], unit='ms')
    return df

def registrar_operacion_csv(tipo, precio, rsi, adx, resultado, saldo):
    nombre_archivo = 'historial_backtest.csv'
    existe = os.path.isfile(nombre_archivo)
    with open(nombre_archivo, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Fecha', 'Tipo', 'Precio', 'RSI', 'ADX', 'Ganancia', 'Saldo'])
        writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tipo, precio, rsi, adx, resultado, saldo])

def correr_backtest():
    # 1. Preparación - Usa el límite definido en config
    df = obtener_datos_historicos(config.SIMBOLO, config.TEMPORALIDAD, config.LIMITE_VELAS)
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
    for i in range(205, len(df)): 
        ventana = df.iloc[:i+1]
        fila_actual = df.iloc[i]
        precio = fila_actual['Cierre']
        
        # --- LÓGICA DE APERTURA ---
        if posicion is None:
            señal = al.obtener_señal(ventana, posicion)
            if señal in ["COMPRA", "SHORT"]:
                posicion = "LONG" if señal == "COMPRA" else "SHORT"
                precio_entrada = precio
                trades_totales += 1
                
                # Cálculo de capital según interés compuesto[cite: 1, 2]
                if config.USAR_INTERES_COMPUESTO:
                    capital_arriesgado = saldo * (config.PORCENTAJE_POR_TRADE / 100)
                else:
                    capital_arriesgado = config.SALDO_INICIAL_USD * (config.PORCENTAJE_POR_TRADE / 100)

        # --- LÓGICA DE CIERRE ---
        else:
            # Pasa el precio_entrada para que funcione la lógica de salida dinámica en analisis.py[cite: 3]
            señal = al.obtener_señal(ventana, posicion, precio_entrada)
            
            if señal == "CERRAR":
                if posicion == "LONG":
                    retorno = (precio - precio_entrada) / precio_entrada
                else: # SHORT
                    retorno = (precio_entrada - precio) / precio_entrada
                
                # Descuento de comisiones (opcional, según tu config)[cite: 2]
                ganancia_neta = capital_arriesgado * retorno
                saldo += ganancia_neta
                
                if ganancia_neta > 0:
                    ganados += 1
                
                # Registro en CSV
                registrar_operacion_csv(
                    posicion, 
                    precio, 
                    round(fila_actual['RSI'], 2), 
                    round(fila_actual['ADX'], 2), 
                    round(ganancia_neta, 2), 
                    round(saldo, 2)
                )
                
                print(f"Trade {trades_totales}: {posicion} | Neto: ${ganancia_neta:.2f} | Saldo: ${saldo:.2f}")
                
                posicion = None
                precio_entrada = None

    # 3. Resultados Finales (RESTAURADOS)
    print("-" * 50)
    print(f"RESULTADOS FINALES:")
    print(f"Saldo Final: ${saldo:.2f}")
    print(f"Rendimiento: {((saldo/config.SALDO_INICIAL_USD)-1)*100:.2f}%")
    print(f"Total Trades: {trades_totales}")
    if trades_totales > 0:
        win_rate = (ganados / trades_totales) * 100
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Trades Ganados: {ganados}")
        print(f"Trades Perdidos: {trades_totales - ganados}")
    print("-" * 50)

if __name__ == "__main__":
    correr_backtest()