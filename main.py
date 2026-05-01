import ccxt
import time
import config
import analisis
import pandas as pd

def ejecutar_paper_trading():
    exchange = ccxt.binance()
    
    # Estado inicial del simulador
    usd_disponible = config.SALDO_INICIAL_USD
    btc_poseido = 0
    en_posicion = False
    precio_compra = 0  # Necesario para calcular Stop Loss y Take Profit
    
    print(f"--- MODO PAPER TRADING INICIADO ---")
    print(f"Saldo Inicial: ${usd_disponible} USD")
    print(f"Estrategia: EMA {config.EMA_RAPIDA} / SMA {config.SMA_LENTA} + DMI/ADX\n")

    while True:
        try:
            # 1. Obtener datos y calcular indicadores
            velas = exchange.fetch_ohlcv(config.SIMBOLO, timeframe=config.TEMPORALIDAD, limit=config.LIMITE_VELAS)
            df = analisis.calcular_indicadores(velas)
            señal = analisis.obtener_señal(df)
            
            # Extraer valores actuales
            precio_actual = df['Cierre'].iloc[-1]
            ema = df['EMA_RAPIDA'].iloc[-1]
            sma = df['SMA_LENTA'].iloc[-1]
            adx = df['ADX'].iloc[-1]
            rsi_act = df['RSI'].iloc[-1]        # <--- Agregamos esta
            stoch_k = df['STOCH_K'].iloc[-1]    # <--- Agregamos esta

            # 2. Mostrar Monitor en Consola (Solo si hay datos suficientes)
            if not pd.isna(ema) and not pd.isna(adx):
                print(f"P: {precio_actual:.2f} | RSI: {rsi_act:.1f} | STOCH_K: {stoch_k:.1f} | ADX: {adx:.1f} | {señal}")
            else:
                print("⏳ Esperando datos para completar indicadores...")
                time.sleep(5)
                continue

            # 3. Lógica de GESTIÓN DE RIESGO (Stop Loss y Take Profit)
            if en_posicion:
                variacion = (precio_actual - precio_compra) / precio_compra
                
                # Caso A: Stop Loss (2% por defecto)
                if variacion <= -config.STOP_LOSS_PCT:
                    usd_disponible = (btc_poseido * precio_actual) * (1 - config.COMISION_EXCHANGE)
                    btc_poseido = 0
                    en_posicion = False
                    print(f"🛑 STOP LOSS ACTIVADO: Salimos con pérdida del {variacion*100:.2f}%")

                # Caso B: Take Profit (6% según tu cambio)
                elif variacion >= config.TAKE_PROFIT_PCT:
                    usd_disponible = (btc_poseido * precio_actual) * (1 - config.COMISION_EXCHANGE)
                    btc_poseido = 0
                    en_posicion = False
                    print(f"🎯 TAKE PROFIT ALCANZADO: Ganancia del {variacion*100:.2f}%")

            # 4. Lógica de ENTRADA (LONG o SHORT)
            if señal == "COMPRA" and not en_posicion:
                tipo_posicion = "LONG"
                precio_compra = precio_actual
                btc_poseido = (usd_disponible / precio_actual) * (1 - config.COMISION_EXCHANGE)
                usd_disponible = 0
                en_posicion = True
                print(f"🚀 POSICIÓN LONG: Entramos comprando a ${precio_actual}")

            elif señal == "SHORT" and not en_posicion:
                tipo_posicion = "SHORT"
                precio_compra = precio_actual
                # En un Short simulado, "poseemos" el valor en USD que bajará
                btc_poseido = (usd_disponible / precio_actual) 
                usd_disponible = 0
                en_posicion = True
                print(f"📉 POSICIÓN SHORT: Entramos vendiendo a ${precio_actual}")

            # 5. Lógica de SALIDA
            elif señal == "VENTA" and en_posicion:
                # Aquí cerramos cualquier posición abierta
                if tipo_posicion == "LONG":
                    usd_disponible = (btc_poseido * precio_actual) * (1 - config.COMISION_EXCHANGE)
                else: # Si era SHORT, ganamos si el precio bajó
                    beneficio = (precio_compra - precio_actual) * btc_poseido
                    usd_disponible = (precio_compra * btc_poseido) + beneficio
                
                btc_poseido = 0
                en_posicion = False
                print(f"💰 POSICIÓN CERRADA a ${precio_actual}. Volvemos a USD.")

            # 5. Estado de la Cartera
            valor_cartera = usd_disponible + (btc_poseido * precio_actual)
            ganancia_total = valor_cartera - config.SALDO_INICIAL_USD
            print(f"CARTERA: ${valor_cartera:.2f} | GANANCIA TOTAL: ${ganancia_total:.2f}")
            print("-" * 50)

            time.sleep(30) # Esperamos 30 segundos para la próxima revisión
            
        except Exception as e:
            print(f"Error en el bucle: {e}")
            time.sleep(10)

if __name__ == "__main__":
    ejecutar_paper_trading()