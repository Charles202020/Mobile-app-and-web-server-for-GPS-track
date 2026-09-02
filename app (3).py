"""
Backend Flask que lee la base de datos que llena el sniffer y expone
la última coordenada (lat, lon, fecha, hora) para la página web.

La base de datos (coordenadas.db) queda como un archivo SQLite normal
y corriente en el disco: puedes abrirla con cualquier visor externo
(ej. "DB Browser for SQLite") al mismo tiempo que este servidor está
corriendo, sin que se bloqueen entre sí, porque cada consulta abre y
cierra su propia conexión de solo lectura o escritura puntual.

Este proceso corre en un puerto interno (5001 por defecto). Nginx es
el que queda expuesto al público y le reenvía las peticiones a este
backend (ver nginx.conf.completo).

Uso:
    python3 app.py
"""

import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify

NOMBRE_BD = "coordenadas.db"

app = Flask(__name__)


def obtener_ultima_coordenada(ruta_bd: str) -> dict | None:
    """
    Consulta la fila más reciente y devuelve solo lat, lon, fecha y
    hora (derivadas del timestamp GPS ts_fix, en milisegundos UTC).
    """
    conexion = sqlite3.connect(ruta_bd)
    conexion.row_factory = sqlite3.Row
    fila = conexion.execute(
        "SELECT lat, lon, ts_fix FROM coordenadas ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conexion.close()

    if fila is None:
        return None

    momento = datetime.fromtimestamp(fila["ts_fix"] / 1000, tz=timezone.utc)
    return {
        "lat": fila["lat"],
        "lon": fila["lon"],
        "fecha": momento.strftime("%Y-%m-%d"),
        "hora": momento.strftime("%H:%M:%S"),
    }


@app.route("/actual")
def actual():
    """Endpoint JSON con los 4 campos: lat, lon, fecha, hora."""
    datos = obtener_ultima_coordenada(NOMBRE_BD)
    if datos is None:
        return jsonify({"lat": "-", "lon": "-", "fecha": "-", "hora": "-"})
    return jsonify(datos)


@app.route("/")
def pagina_principal():
    """
    Página mínima con 4 campos (Lat, Long, Fecha, Hora) y un botón que
    los refresca manualmente llamando a /actual, sin recargar la página.
    """
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Última ubicación</title>
        <style>
            body { font-family: monospace; font-size: 1.1rem; padding: 2rem; }
            p { margin: 4px 0; }
            button { margin-top: 1rem; padding: 6px 16px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>Última ubicación registrada</h1>
        <p>Lat: <span id="lat">-</span></p>
        <p>Long: <span id="lon">-</span></p>
        <p>Fecha: <span id="fecha">-</span></p>
        <p>Hora: <span id="hora">-</span></p>

        <button onclick="actualizar()">Actualizar</button>

        <script>
            async function actualizar() {
                const respuesta = await fetch('/actual');
                const datos = await respuesta.json();
                document.getElementById('lat').textContent = datos.lat;
                document.getElementById('lon').textContent = datos.lon;
                document.getElementById('fecha').textContent = datos.fecha;
                document.getElementById('hora').textContent = datos.hora;
            }
            actualizar();  // primera carga al abrir la página
            setInterval(actualizar, 1000);  // recarga automática cada 1 segundo
        </script>
    </body>
    </html>
    """
    return html


if __name__ == "__main__":
    # host="0.0.0.0" para que Nginx (u otro proceso) pueda alcanzarlo.
    app.run(host="0.0.0.0", port=5001)
