from flask import Flask, request
import pandas as pd
import os
import telegram
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater, ConversationHandler

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telegram.Bot(token=TOKEN)

# Etapas del flujo
CAJAS, UNIDADES, TURNO = range(3)

# Carga y análisis del histórico
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
        return f"🔴 Ocupación baja – {ocupacion_ajustada:.0f} cajas/unidad útil. Refuerza la planificación con tu equipo."
    elif ocupacion_ajustada < 2100:
        return f"🟡 Ocupación ligeramente baja – {ocupacion_ajustada:.0f} cajas/unidad útil. Aumenta la eficiencia en cierres."
    else:
        return f"🟢 Ocupación óptima – {ocupacion_ajustada:.0f} cajas/unidad útil. Refuerza los cierres para mantener el nivel."

def start(update, context):
    update.message.reply_text("👋 ¡Hola! ¿Cuántas cajas tienes en Shipping?")
    return CAJAS

def recibir_cajas(update, context):
    context.user_data['cajas'] = int(update.message.text)
    update.message.reply_text("¿Cuántas unidades formaste?")
    return UNIDADES

def recibir_unidades(update, context):
    context.user_data['unidades'] = int(update.message.text)
    update.message.reply_text("¿Qué turno estás? (mañana o noche)")
    return TURNO

def recibir_turno(update, context):
    turno = update.message.text.lower()
    cajas = context.user_data['cajas']
    unidades = context.user_data['unidades']

    caida = cargar_historico(turno_actual=turno)
    cajas_aj, ocupacion_aj, unidades_utiles = proyectar(cajas, unidades, caida)
    recomendacion = generar_recomendacion(ocupacion_aj)

    mensaje = (
        f"📦 Cajas actuales: {cajas}\n"
        f"🚚 Unidades formadas: {unidades}\n"
        f"📉 Caída proyectada: {caida}%\n"
        f"✅ Cajas ajustadas: {cajas_aj}\n"
        f"📊 Ocupación estimada: {ocupacion_aj} cajas/unidad útil\n"
        f"{recomendacion}"
    )
    update.message.reply_text(mensaje)
    return ConversationHandler.END

def cancelar(update, context):
    update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Bot de productividad operativo"

def main():
    global dp
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CAJAS: [MessageHandler(Filters.text & ~Filters.command, recibir_cajas)],
            UNIDADES: [MessageHandler(Filters.text & ~Filters.command, recibir_unidades)],
            TURNO: [MessageHandler(Filters.text & ~Filters.command, recibir_turno)],
        },
        fallbacks=[CommandHandler('cancelar', cancelar)]
    )
    dp.add_handler(conv_handler)

if __name__ == "__main__":
    main()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
