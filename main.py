
from flask import Flask, request
import pandas as pd

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

if __name__ == '__main__':
    app.run()
