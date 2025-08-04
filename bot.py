import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import requests

# Etapas del flujo
CAJAS, UNIDADES, TURNO = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 ¿Cuántas cajas hay en shipping?")
    return CAJAS

async def cajas_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cajas'] = int(update.message.text)
    await update.message.reply_text("🚛 ¿Cuántas unidades se han formado?")
    return UNIDADES

async def unidades_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['unidades'] = int(update.message.text)
    reply_markup = ReplyKeyboardMarkup([['mañana'], ['noche']], one_time_keyboard=True)
    await update.message.reply_text("🌙 ¿Cuál es el turno actual?", reply_markup=reply_markup)
    return TURNO

async def turno_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    turno = update.message.text
    cajas = context.user_data['cajas']
    unidades = context.user_data['unidades']
    url = f"https://bot-productividad.onrender.com/proyeccion?cajas={cajas}&unidades={unidades}&turno={turno}"
    data = requests.get(url).json()
    mensaje = (
        f"📊 Proyección para turno {data['turno']}:
"
        f"Cajas actuales: {data['cajas']}
"
        f"Unidades formadas: {data['unidades']}
"
        f"Unidades útiles: {data['unidades'] - 10}
"
        f"Caída estimada: {data['caida']}%
"
        f"Cajas ajustadas: {data['cajas_ajustadas']}
"
        f"Ocupación ajustada: {data['ocupacion_ajustada']} cajas/unidad
"
        f"{data['recomendacion']}"
    )
    await update.message.reply_text(mensaje)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado.")
    return ConversationHandler.END

def main():
    import os
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CAJAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, cajas_input)],
            UNIDADES: [MessageHandler(filters.TEXT & ~filters.COMMAND, unidades_input)],
            TURNO: [MessageHandler(filters.TEXT & ~filters.COMMAND, turno_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
