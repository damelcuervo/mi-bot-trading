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
                # 1. Cálculo de resultados antes de cerrar
                if tipo_posicion == "LONG":
                    # Ganamos si el precio subió
                    usd_final = (btc_poseido * precio_actual) * (1 - config.COMISION_EXCHANGE)
                    ganancia_operacion = usd_final - (precio_compra * btc_poseido)
                else: 
                    # SHORT: Ganamos si el precio bajó (Precio_Entrada - Precio_Actual)
                    beneficio_puntos = (precio_compra - precio_actual) * btc_poseido
                    # Restamos una comisión estimada por la operación de short
                    ganancia_operacion = beneficio_puntos - (precio_compra * btc_poseido * config.COMISION_EXCHANGE)
                    usd_final = (precio_compra * btc_poseido) + ganancia_operacion

                # 2. Actualizamos el saldo real disponible
                usd_disponible = usd_final
                
                # 3. REGISTRO EN EL ARCHIVO CSV (Caja Negra)
                # Esto crea un archivo llamado 'historial_operaciones.csv' en tu escritorio
                analisis.registrar_operacion(
                    tipo_posicion, 
                    precio_actual, 
                    señal, 
                    rsi_act, 
                    adx, 
                    stoch_k, 
                    ganancia_operacion, 
                    usd_disponible
                )

                print(f"💰 POSICIÓN {tipo_posicion} CERRADA a ${precio_actual:.2f}")
                print(f"💵 Resultado de esta op: ${ganancia_operacion:.2f}")

                # 4. Resetear variables de posición
                btc_poseido = 0
                en_posicion = False
                tipo_posicion = None

            # 5. Estado de la Cartera (Visualización en consola)
            if en_posicion:
                if tipo_posicion == "LONG":
                    valor_cartera = btc_poseido * precio_actual
                else: # SHORT: valor inicial + (entrada - actual)
                    valor_cartera = (precio_compra * btc_poseido) + ((precio_compra - precio_actual) * btc_poseido)
            else:
                valor_cartera = usd_disponible

            ganancia_total = valor_cartera - config.SALDO_INICIAL_USD
            
            print(f"CARTERA: ${valor_cartera:.2f} | GANANCIA TOTAL: ${ganancia_total:.2f}")
            print("-" * 50)

            # Esperamos 30 segundos (o lo que configures) para la próxima vela/revisión
            time.sleep(30) 
            
        except Exception as e:
            print(f"⚠️ Error en el bucle: {e}")
            time.sleep(10) # Espera un poco antes de reintentar por si fue error de internet

if __name__ == "__main__":
    ejecutar_paper_trading()