import socket
import psycopg2
from datetime import datetime

# Configuración de la base de datos
DB_HOST = "TU_ENDPOINT_AQUI"
DB_PORT = 5432
DB_NAME = "gpsdb"
DB_USER = "gpstracker"
DB_PASS = "TU_CONTRASEÑA_AQUI"

# Configuración del socket UDP
UDP_IP = "0.0.0.0"
UDP_PORT = 5000

def conectar_db():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def crear_tabla(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ubicaciones (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(20),
                latitud DOUBLE PRECISION NOT NULL,
                longitud DOUBLE PRECISION NOT NULL,
                timestamp BIGINT NOT NULL,
                fecha_recepcion TIMESTAMP DEFAULT NOW(),
                ip_origen VARCHAR(50)
            );
        """)
        conn.commit()

def parsear_trama(mensaje):
    campos = {}
    try:
        partes = mensaje.split(",")
        for parte in partes:
            clave, valor = parte.split("=")
            campos[clave.strip()] = valor.strip()
        return campos
    except Exception:
        return None

def iniciar_sniffer():
    print(f"Iniciando sniffer UDP en puerto {UDP_PORT}...")
    conn = conectar_db()
    crear_tabla(conn)
    print("Conectado a la base de datos. Esperando paquetes...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            mensaje = data.decode("utf-8").strip()
            ip_origen = addr[0]
            print(f"Paquete recibido de {ip_origen}: {mensaje}")

            campos = parsear_trama(mensaje)

            if campos and all(k in campos for k in ["TIPO", "LAT", "LON", "TS"]):
                tipo = campos["TIPO"]
                latitud = float(campos["LAT"])
                longitud = float(campos["LON"])
                timestamp = int(campos["TS"])

                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO ubicaciones (tipo, latitud, longitud, timestamp, ip_origen)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (tipo, latitud, longitud, timestamp, ip_origen))
                    conn.commit()
                print(f"Guardado: tipo={tipo}, lat={latitud}, lon={longitud}, ts={timestamp}")
            else:
                print(f"Trama inválida o incompleta: {mensaje}")

        except Exception as e:
            print(f"Error: {e}")
            try:
                conn = conectar_db()
            except Exception as e2:
                print(f"Error reconectando a DB: {e2}")

if __name__ == "__main__":
    iniciar_sniffer()