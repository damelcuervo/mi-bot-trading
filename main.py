import ccxt
import time
import config
import analisis as al

def ejecutar_bot():
    # Conexión pública
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
    
    print("--- MODO PAPER TRADING INICIADO ---")
    saldo_total = config.SALDO_INICIAL_USD
    posicion_actual = None
    precio_entrada = 0.0

    while True:
        try:
            # 1. Obtener Velas
            velas = exchange.fetch_ohlcv(config.SIMBOLO, timeframe=config.TEMPORALIDAD, limit=100)
            df = al.calcular_indicadores(velas)
            
            # 2. Extraer datos del último registro
            ult = df.iloc[-1]
            precio = ult['Cierre']
            rsi, adx, ema, sma = ult['RSI'], ult['ADX'], ult['EMA_RAPIDA'], ult['SMA_LENTA']

            # 3. Evaluar Señal
            señal = al.obtener_señal(df, posicion_actual)

            # 4. Lógica de Trading
            if posicion_actual is None:
                if señal in ["COMPRA", "SHORT"]:
                    posicion_actual = "LONG" if señal == "COMPRA" else "SHORT"
                    precio_entrada = precio
                    print(f"🚀 {posicion_actual} ABIERTO en ${precio:.2f}")

            elif señal == "CERRAR":
                ganancia = (precio - precio_entrada) * (saldo_total / precio_entrada) if posicion_actual == "LONG" else (precio_entrada - precio) * (saldo_total / precio_entrada)
                neto = ganancia - (saldo_total * config.COMISION_EXCHANGE)
                saldo_total += neto
                al.registrar_operacion(posicion_actual, precio, rsi, adx, neto, saldo_total)
                print(f"✅ CERRADO. Resultado: ${neto:.2f} | Saldo: ${saldo_total:.2f}")
                posicion_actual = None

            # 5. Monitor de Consola
            print(f"[ {time.strftime('%H:%M:%S')} ] P: {precio:.2f} | EMA9: {ema:.2f} | SMA21: {sma:.2f} | RSI: {rsi:.1f} | ADX: {adx:.1f} | {posicion_actual or 'BUSCANDO'}")
            
            time.sleep(30)

        except Exception as e:
            print(f"❌ Error en el bucle: {e}")
            time.sleep(10)

if __name__ == "__main__":
    ejecutar_bot()