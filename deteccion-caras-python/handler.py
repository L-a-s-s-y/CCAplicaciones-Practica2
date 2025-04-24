import json
import cv2
import numpy as np
import requests

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def handle(req):
    # Parsear el JSON
    try:
        payload = json.loads(req)
        url = payload.get('url')
    except Exception:
        msg = "Payload inválido. Envía JSON: {\"url\": \"<imagen_url>\"}"
        return (
            msg.encode('utf-8'),
            400,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    if not url:
        msg = "Falta el parámetro 'url' en el JSON."
        return (
            msg.encode('utf-8'),
            400,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    # Descarga la imagen
    resp = requests.get(url, timeout=5)
    if resp.status_code != 200:
        msg = f"Error al descargar la imagen: HTTP {resp.status_code}"
        return (
            msg.encode('utf-8'),
            400,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    # Prepara la imagen para OpenCV
    img_arr = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    if img is None:
        msg = "No se pudo decodificar la imagen."
        return (
            msg.encode('utf-8'),
            400,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    # Realiza la detección de caras
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)

    # Envía la imagen como JPEG mediante HTTP
    success, img_encoded = cv2.imencode('.jpg', img)
    if not success:
        msg = "Error al codificar la imagen de salida."
        return (
            msg.encode('utf-8'),
            500,
            {"Content-Type": "text/plain; charset=utf-8"},
        )
    return (
        img_encoded.tobytes(),
        200,
        {"Content-Type": "image/jpeg"}
    )

