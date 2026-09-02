"""
Sniffer UDP propietario.

Escucha en un puerto UDP, recibe las tramas de texto que manda la app
(formato: TIPO=GPS,LAT=...,LON=...,TS=...) y las decodifica en un
diccionario listo para guardar en base de datos.

Uso:
    python3 sniffer_udp.py
    python3 sniffer_udp.py --host 0.0.0.0 --port 5000
"""

import argparse
import socket
import sqlite3
from datetime import datetime, timezone

NOMBRE_BD = "coordenadas.db"


def preparar_base_de_datos(ruta_bd: str) -> None:
    """
    Crea el archivo de base de datos y la tabla si todavía no existen.
    Se llama una sola vez al arrancar el sniffer.
    """
    conexion = sqlite3.connect(ruta_bd)
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS coordenadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            ts_fix INTEGER NOT NULL,
            origen_ip TEXT NOT NULL,
            recibido_en TEXT NOT NULL
        )
        """
    )
    conexion.commit()
    conexion.close()


def guardar_en_bd(ruta_bd: str, trama: dict, origen_ip: str, recibido_en: str) -> None:
    """
    Inserta una coordenada ya decodificada en la base de datos.
    Abre y cierra la conexión en cada llamada: para la tasa de envío de
    este proyecto (cada varios segundos) no hay problema de rendimiento,
    y evita dejar conexiones abiertas colgadas si el sniffer corre días.
    """
    conexion = sqlite3.connect(ruta_bd)
    conexion.execute(
        "INSERT INTO coordenadas (lat, lon, ts_fix, origen_ip, recibido_en) "
        "VALUES (?, ?, ?, ?, ?)",
        (trama["lat"], trama["lon"], trama["ts"], origen_ip, recibido_en),
    )
    conexion.commit()
    conexion.close()


def parsear_trama(texto: str) -> dict | None:
    """
    Convierte una trama tipo:
        TIPO=GPS,LAT=11.023383,LON=-74.8464518,TS=1787714213131
    en un diccionario:
        {"tipo": "GPS", "lat": 11.023383, "lon": -74.8464518, "ts": 1787714213131}

    Devuelve None si la trama no tiene el formato esperado, para que el
    sniffer pueda ignorar paquetes basura o corruptos sin caerse.
    """
    campos = {}
    try:
        for par in texto.strip().split(","):
            clave, valor = par.split("=", 1)
            campos[clave.strip().upper()] = valor.strip()

        if campos.get("TIPO") != "GPS":
            return None

        return {
            "tipo": campos["TIPO"],
            "lat": float(campos["LAT"]),
            "lon": float(campos["LON"]),
            "ts": int(campos["TS"]),
            # Si más adelante agregan un número de secuencia (SEQ=...)
            # a la trama, descomenta la siguiente línea:
            # "seq": int(campos["SEQ"]),
        }
    except (KeyError, ValueError):
        # Trama incompleta, mal formada, o con un valor no numérico.
        return None


def iniciar_sniffer(host: str, port: int, ruta_bd: str) -> None:
    preparar_base_de_datos(ruta_bd)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"[sniffer] escuchando UDP en {host}:{port} ... (Ctrl+C para salir)")
    print(f"[sniffer] guardando en base de datos: {ruta_bd}")

    ultimo_ts = None

    while True:
        try:
            datos, direccion = sock.recvfrom(1024)
        except KeyboardInterrupt:
            print("\n[sniffer] detenido por el usuario")
            break

        recibido_en = datetime.now(timezone.utc).isoformat()

        try:
            texto = datos.decode("utf-8")
        except UnicodeDecodeError:
            print(f"[sniffer] paquete no legible desde {direccion}, descartado")
            continue

        trama = parsear_trama(texto)

        if trama is None:
            print(f"[sniffer] trama inválida desde {direccion}: {texto!r}")
            continue

        # Aviso simple de fuera de orden: si el timestamp del fix es menor
        # al último que procesamos, probablemente llegó desordenado (algo
        # esperable en UDP, sin garantías de orden).
        fuera_de_orden = ultimo_ts is not None and trama["ts"] < ultimo_ts
        ultimo_ts = trama["ts"]

        print(
            f"[sniffer] {recibido_en} | origen={direccion[0]}:{direccion[1]} "
            f"| lat={trama['lat']} lon={trama['lon']} ts={trama['ts']}"
            + (" | ¡FUERA DE ORDEN!" if fuera_de_orden else "")
        )

        guardar_en_bd(ruta_bd, trama, direccion[0], recibido_en)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sniffer UDP propietario para tramas GPS")
    parser.add_argument("--host", default="0.0.0.0", help="IP donde escuchar (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Puerto UDP a escuchar (default: 5000)")
    parser.add_argument("--db", default=NOMBRE_BD, help=f"Ruta del archivo SQLite (default: {NOMBRE_BD})")
    args = parser.parse_args()

    iniciar_sniffer(args.host, args.port, args.db)
