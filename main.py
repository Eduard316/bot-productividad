
import os
from flask import Flask, request
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from dotenv import load_dotenv

# ------------------ FLASK SERVER --------------------
app = Flask(__name__)

def cargar_historico(path='historico_turnos_plantilla.csv', turno_actual='noche'):
    df = pd.read_csv(path, parse_dates=['fecha'])
    df = df[df['turno'] == turno_actual]
    df['mes'] = df['fecha'].dt.to_period('M')
    df['unidades_utiles'] = df['unidades_formadas'] - 10
    df['ocupacion'] = df['cajas'] / df['unidades_utiles']
    resumen = df.groupby('mes').agg({'ocupacion': 'mean'}).reset_index()
    if len(resumen) >= 2:
        caida_total = ((resumen['ocupacion'].iloc[-1] - resumen['ocupacion'].iloc[0]) / resumen['ocupacion'].iloc[0]) * 100
    else:
        caida_total = 0
    return round(caida_total, 2)

def proyectar(cajas_actuales, unidades_formadas, caida_pct):
    unidades_utiles = unidades_formadas - 10
    cajas_ajustadas = cajas_actuales * (1 - (caida_pct / 100))
    ocupacion_ajustada = cajas_ajustadas / unidades_utiles
    return round(cajas_ajustadas), round(ocupacion_ajustada), unidades_utiles

def generar_recomendacion(ocupacion_ajustada):
    if ocupacion_ajustada < 1900:
        return "🔴 Ocupación baja – {:.0f} cajas/unidad útil.".format(ocupacion_ajustada)
    elif ocupacion_ajustada < 2100:
        return "🟡 Ocupación ligeramente baja – {:.0f} cajas/unidad útil.".format(ocupacion_ajustada)
    else:
        return "🟢 Ocupación óptima – {:.0f} cajas/unidad útil.".format(ocupacion_ajustada)

@app.route('/')
def home():
    return "Bot de productividad activo"

@app.route('/proyeccion', methods=['GET'])
def calcular():
    cajas = int(request.args.get('cajas'))
    unidades = int(request.args.get('unidades'))
    turno = request.args.get('turno', 'noche')
    caida = cargar_historico(turno_actual=turno)
    cajas_aj, ocupacion_aj, unidades_utiles = proyectar(cajas, unidades, caida)
    recomendacion = generar_recomendacion(ocupacion_aj)
    return {
        "turno": turno,
        "cajas": cajas,
        "unidades": unidades,
        "caida": caida,
        "cajas_ajustadas": cajas_aj,
        "ocupacion_ajustada": ocupacion_aj,
        "recomendacion": recomendacion
    }

# ------------------ TELEGRAM BOT --------------------
CAJAS, UNIDADES, TURNO = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 ¿Cuántas cajas hay en shipping?")
    return CAJAS

async def cajas_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cajas"] = int(update.message.text)
    await update.message.reply_text("🚛 ¿Cuántas unidades formadas?")
    return UNIDADES

async def unidades_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["unidades"] = int(update.message.text)
    reply_keyboard = [["mañana", "noche"]]
    await update.message.reply_text(
        "🌙 ¿Qué turno es?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return TURNO

async def turno_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["turno"] = update.message.text
    datos = context.user_data

    caida = cargar_historico(turno_actual=datos["turno"])
    cajas_aj, ocupacion_aj, unidades_utiles = proyectar(datos["cajas"], datos["unidades"], caida)
    recomendacion = generar_recomendacion(ocupacion_aj)

    texto = (
        f"📊 Proyección para turno {datos['turno']}:
"
        f"📦 Cajas actuales: {datos['cajas']}
"
        f"🚛 Unidades formadas: {datos['unidades']}
"
        f"📉 Caída histórica estimada: {caida}%
"
        f"📦 Cajas ajustadas: {cajas_aj}
"
        f"📈 Ocupación proyectada: {ocupacion_aj} cajas/unidad útil
"
        f"{recomendacion}"
    )
    await update.message.reply_text(texto)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

def lanzar_bot():
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")
    app_telegram = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CAJAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, cajas_input)],
            UNIDADES: [MessageHandler(filters.TEXT & ~filters.COMMAND, unidades_input)],
            TURNO: [MessageHandler(filters.TEXT & ~filters.COMMAND, turno_input)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app_telegram.add_handler(conv_handler)
    app_telegram.run_polling()

# ------------------ MAIN --------------------
if __name__ == "__main__":
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()
    lanzar_bot()
