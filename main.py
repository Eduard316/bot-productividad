
import os
import pandas as pd
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# ===================== Flask App =====================
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot de productividad con Flask y Telegram está activo'

# ===================== Variables de Conversación =====================
CAJAS, UNIDADES, TURNO = range(3)
user_data = {}

# ===================== Funciones de cálculo =====================
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
        return "🟡 Ocupación ligeramente baja – {:.0f} cajas/unidad útil.".format(ocupacion_ajustad...
    else:
        return "🟢 Ocupación óptima – {:.0f} cajas/unidad útil.".format(ocupacion_ajustada)

# ===================== Flujo de Telegram =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 ¿Cuántas cajas hay en shipping?")
    return CAJAS

async def cajas_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['cajas'] = int(update.message.text)
    await update.message.reply_text("🚛 ¿Cuántas unidades se han formado?")
    return UNIDADES

async def unidades_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['unidades'] = int(update.message.text)
    reply_markup = ReplyKeyboardMarkup([['mañana', 'noche']], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("🌙 ¿Qué turno es?", reply_markup=reply_markup)
    return TURNO

async def turno_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data['turno'] = update.message.text
    caida = cargar_historico(turno_actual=user_data['turno'])
    cajas_aj, ocupacion_aj, unidades_utiles = proyectar(user_data['cajas'], user_data['unidades'], caida)
    recomendacion = generar_recomendacion(ocupacion_aj)

    respuesta = (
        f"📊 Proyección para turno *{user_data['turno']}*:
"
        f"- Cajas actuales: {user_data['cajas']}
"
        f"- Unidades útiles: {unidades_utiles}
"
        f"- Caída histórica: {caida}%
"
        f"- Cajas ajustadas: {cajas_aj}
"
        f"- Ocupación proyectada: {ocupacion_aj} cajas/unidad

"
        f"{recomendacion}"
    )
    await update.message.reply_text(respuesta, parse_mode="Markdown")
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Proceso cancelado.")
    return ConversationHandler.END

# ===================== Iniciar Bot =====================
def iniciar_bot():
    token = os.environ.get("TELEGRAM_TOKEN")
    app_bot = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CAJAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, cajas_input)],
            UNIDADES: [MessageHandler(filters.TEXT & ~filters.COMMAND, unidades_input)],
            TURNO: [MessageHandler(filters.TEXT & ~filters.COMMAND, turno_input)],
        },
        fallbacks=[CommandHandler('cancelar', cancelar)]
    )

    app_bot.add_handler(conv_handler)
    app_bot.run_polling()

# ===================== Ejecutar Flask y Bot =====================
if __name__ == '__main__':
    import threading
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))).start()
    iniciar_bot()
