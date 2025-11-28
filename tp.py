from socket import *
import sys
import os
from urllib.parse import parse_qs, urlparse
import qrcode
import gzip
import random

#FUNCIONES AUXILIARES

def imprimir_qr_en_terminal(url):
    # Dada una URL la imprime por terminal como un QR
    
    qr = qrcode.QRCode(border=4)
    qr.add_data(url)
    qr.make()
    qr.print_ascii()

def get_wifi_ip():
    """Obtiene la IP local asociada a la interfaz de red (por ejemplo, Wi-Fi)."""
    s = socket(AF_INET, SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip #Devuelve la IP como string

def parsear_multipart(body, boundary):
    """Función auxiliar (ya implementada) para parsear multipart/form-data."""
    try:
        # Se divide el cuerpo por el boundary para luego poder extraer el nombre y contenido del archivo
        parts = body.split(f'--{boundary}'.encode())
        for part in parts:
            if b'filename=' in part:
                # Se extrae el nombre del archivo
                filename_start = part.find(b'filename="') + len(b'filename="')
                filename_end = part.find(b'"', filename_start)
                filename = part[filename_start:filename_end].decode()

                # Se extrae el contenido del archivo que arranca después de los headers
                header_end = part.find(b'\r\n\r\n')
                if header_end == -1:
                    header_end = part.find(b'\n\n')
                    content_start = header_end + 2
                else:
                    content_start = header_end + 4

                # El contenido va hasta el último CRLF antes del boundary
                content_end = part.rfind(b'\r\n')
                if content_end <= content_start:
                    content_end = part.rfind(b'\n')

                file_content = part[content_start:content_end]
                if filename and file_content:
                    return filename, file_content
        return None, None
    except Exception as e:
        print(f"Error al parsear multipart: {e}")
        return None, None

def generar_html_interfaz(modo):
    """
    Genera el HTML de la interfaz principal:
    - Si modo == 'download': incluye un enlace o botón para descargar el archivo.
    - Si modo == 'upload': incluye un formulario para subir un archivo.
    """
    if modo == 'download':
        return """
<html>
  <head>
    <meta charset="utf-8">
    <title>Descargar archivo</title>
    <style>
      body { font-family: sans-serif; max-width: 500px; margin: 50px auto; }
      a { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
    </style>
  </head>
  <body>
    <h1>Descargar archivo</h1>
    <p>Haz click en el botón para descargar:</p>
    <a href="/download">Descargar archivo</a>
  </body>
</html>
"""
    
    else:  # upload
        return """
<html>
  <head>
    <meta charset="utf-8">
    <title>Subir archivo</title>
    <style>
      body { font-family: sans-serif; max-width: 500px; margin: 50px auto; }
      form { border: 2px dashed #ccc; padding: 20px; border-radius: 5px; }
      input[type="submit"] { padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; }
    </style>
  </head>
  <body>
    <h1>Subir archivo</h1>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file" required>
      <input type="submit" value="Subir">
    </form>
  </body>
</html>
"""

#CODIGO A COMPLETAR

def manejar_descarga(archivo, request_line, usar_gzip=False, cliente_acepta_gzip=False):
    """
    Genera una respuesta HTTP con el archivo solicitado. 
    Si el archivo no existe debe devolver un error.
    Debe incluir los headers: Content-Type, Content-Length y Content-Disposition.
    """

    if not os.path.isfile(archivo):
    # Si no está el archivo en la carpeta
        body = b"Archivo no encontrado"
        return (
            b"HTTP/1.1 404 Not Found\r\n"
            b"Content-Type: text/plain\r\n"
            + f"Content-Length: {len(body)}\r\n".encode()
            + b"\r\n"
            + body
        )
    
    # Sino, leemos el archivo y lo guardamos
    with open(archivo, "rb") as f:
        contenido = f.read()
    
    # Si usamos gzip
    if usar_gzip and cliente_acepta_gzip:
        contenido = gzip.compress(contenido)

    # Agregamos los headers
        headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/octet-stream\r\n"
            "Content-Encoding: gzip\r\n"
            f"Content-Length: {len(contenido)}\r\n"
            f"Content-Disposition: attachment; filename=\"{archivo}\"\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode()
    
    else:
        headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/octet-stream\r\n"
            f"Content-Length: {len(contenido)}\r\n"
            f"Content-Disposition: attachment; filename=\"{archivo}\"\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode()

    return headers + contenido


def manejar_carga(body, boundary, directorio_destino="."):
    """
    Procesa un POST con multipart/form-data, guarda el archivo y devuelve una página de confirmación.
    """
    try:
        # 1. Parsear multipart (función auxiliar)
        nombre_archivo, contenido = parsear_multipart(body, boundary)

        # 2. Guardar archivo
        ruta = os.path.join(directorio_destino, "archivos_servidor", nombre_archivo)
        
        with open(ruta, "wb") as f:
            f.write(contenido)

        # 3. Respuesta 200 OK con página de carga exitosa
        html = """
        <html>
        <head>
            <meta charset="utf-8">
            <title>Subida exitosa</title>
            <style>
            .notificacion {
                padding:15px; 
                background:#d4edda;
                color:#155724;
                border:1px solid #c3e6cb;
                border-radius:5px;
                margin:20px;
                font-family:sans-serif;
            }
            a { 
                font-family: sans-serif;
                padding:8px 12px; 
                background:#007bff; 
                color:white; 
                border-radius:4px; 
                text-decoration:none; 
            }
            </style>
        </head>
        <body>
            <div class="notificacion">
            Archivo subido correctamente ✔
            </div>
            <a href="/">Volver</a>
        </body>
        </html>
        """

        body = html.encode()
        
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/html\r\n"
            + f"Content-Length: {len(body)}\r\n".encode()
            + b"Connection: close\r\n\r\n"
            + body
        )

        return response

    except Exception as e:
        # 4. En caso de error (500)
        mensaje = b"Error al guardar archivo"
        return (
            b"HTTP/1.1 500 Internal Server Error\r\n"
            b"Content-Type: text/plain\r\n"
            + f"Content-Length: {len(mensaje)}\r\n".encode()
            + b"Connection: close\r\n"
            b"\r\n"
            + mensaje
        )

        print(f"Error en la carga: {e}")


def start_server(archivo_descarga=None, modo_upload=False, usar_gzip=False):
    """
    Inicia el servidor TCP.
    - Si se especifica archivo_descarga, se inicia en modo 'download'.
    - Si modo_upload=True, se inicia en modo 'upload'.
    """

    # 1. Obtener IP local y poner al servidor a escuchar en un puerto aleatorio

    ip_server = get_wifi_ip()
    puerto = random.randint(1024, 8192) # Ponemos como limite 8192 para no complejizar

    server_socket = socket(AF_INET, SOCK_STREAM) # IPv4 y TCP
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # Saltear el TIME_WAIT de dos minutos para reiniciar más rápido

    server_socket.bind((ip_server, puerto)) # Asocio el server a su ip y puerto
    server_socket.listen(1) # Pone el server a escuchar con 1 conexión

    # 2. Mostrar información del servidor y el código QR
    
    #   i. Imprimo URL y QR
    imprimir_qr_en_terminal(f"http://{ip_server}:{puerto}")
    print(f"Servidor escuchando en http://{ip_server}:{puerto}")

    #   ii. Imprimo modo de operación
    print("Operando en modo " + sys.argv[1].lower())

    # 3. Esperar conexiones y atender un cliente
    # COMPLETAR:
    # - aceptar la conexión (accept) - HECHO
    # - recibir los datos (recv) - HECHO
    # - decodificar la solicitud HTTP - HECHO
    # - determinar método (GET/POST) y ruta (/ o /download) - HECHO
    # - generar la respuesta correspondiente (HTML o archivo) - HECHO
    # - enviar la respuesta al cliente - HECHO
    # - cerrar la conexión - HECHO

    while True:
        # 1. Aceptamos la conexión
        conn, addr = server_socket.accept()
        print("Conexión recibida de", addr)

        # 2. Recibimos los datos
        request = conn.recv(4096) # Lee el mensaje del cliente (4096 B) y lo guarda
        texto = request.decode(errors="ignore") # Paso el mensaje a string
        
        # Si por alguna razón llega un mensaje vacío
        if not texto:
            conn.close()
            continue
        
        # Si llegan requests incompletos / favicon
        if "\r\n\r\n" not in texto:
            conn.close()
            continue
        
        headers_raw, body_inicial = texto.split("\r\n\r\n", 1) # Separo headers del body
        
        # 3. Decodificamos la solicitud. Armamos un diccionarito con los headers del mensaje para facilitar
        headers = {}
        lineas = headers_raw.split("\r\n")
        request_line = lineas[0]
        for linea in lineas[1:]:
            if ":" in linea:
                k, v = linea.split(":", 1)
                headers[k.strip()] = v.strip()
        
        # i. Vemos si el cliente acepta gzip en los headers
        accept_encoding = headers.get("Accept-Encoding", "")
        cliente_acepta_gzip = "gzip" in accept_encoding

        method, path, version = request_line.split(" ") # "version" no usado pero guardado igualmente 
        
        # 4. Determinamos el método, generamos la respuesta acordemente y enviamos
        
        if method == "GET":
            # i. Página inicial
            if path == "/":
                html = generar_html_interfaz(sys.argv[1].lower())

                # HTML -> Bytes
                body = html.encode()

                # Armado de headers HTTP
                headers = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                ).encode()
                
                conn.sendall(headers + body)
            
            #   ii. Descarga
            elif not modo_upload and path == "/download":
                resp = manejar_descarga(archivo_descarga, request_line, usar_gzip, cliente_acepta_gzip)
                conn.sendall(resp)
            
            #   iii. Error
            else:
                conn.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")

        elif method == "POST" and modo_upload:
            content_type = headers.get("Content-Type", "")
            
            boundary = content_type.split("boundary=", 1)[1].strip('"')

            content_length = int(headers.get("Content-Length", "0"))

            # El servidor solo lee los primeros 4096 bytes. Si el mensaje es mayor a eso, no lo lee
            # -> Content-Length indica, justamente, el tamaño (largo) en bytes del contenido, entonces
            body_bytes = body_inicial.encode() # Es lo que ya llegó

            # Y, si hace falta, sigue leyendo hasta completar el Content-Length:
            faltan = content_length - len(body_bytes)

            while faltan > 0:
                chunk = conn.recv(min(4096, faltan))
                if not chunk:
                    break
                body_bytes += chunk
                faltan -= len(chunk)
            
            response = manejar_carga(body_bytes, boundary)
            conn.sendall(response)
        
        #   Error
        else:
            conn.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")

        # 5. Cerrar la conexión
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python tp.py upload [--gzip]                   # Servidor para subir archivos")
        print("  python tp.py download archivo.txt [--gzip]     # Servidor para descargar un archivo")
        sys.exit(1)
    
    comando = sys.argv[1]
      
    # Tomamos todo lo que sigue después del comando
    args = sys.argv[2:]

    # Detectamos flag de gzip
    quiere_gzip = "--gzip" in args

    if comando == "upload":
        start_server(archivo_descarga=None, modo_upload=True, usar_gzip=quiere_gzip)

    elif comando == "download" and len(sys.argv) > 2:

        # El nombre del archivo es la unión de los argumentos sin --gzip
        archivo = " ".join(a for a in args if a != "--gzip")
        
        ruta_archivo = os.path.join("archivos_servidor", archivo)
        start_server(archivo_descarga=ruta_archivo, modo_upload=False, usar_gzip=quiere_gzip)

    else:
        print("Comando no reconocido o archivo faltante")
        sys.exit(1)