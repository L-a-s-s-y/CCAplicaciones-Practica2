# Memoria Práctica 2
##### José Antonio Laserna Beltrán
## Entorno de desarrollo y producción
Se ha realizado la práctica en local en lugar de usar el servidor galeón. Por tanto el entorno de desarrollo y producción son el mismo.

**Características:**
- *Sistema Operativo*: Fedora Linux 40 (Workstation Edition)
- *CPU*: Intel® Core™ i7-8750H × 12
## Plataforma de desarrollo
Se ha utilizado Open FaaS como plataforma de Function as a Service. Como lenguaje de programación se ha utlizado Python.
## Puesta a punto de la plataforma
Para el proceso de instalación de `OpenFaaS`, la guía presenta en la sesión 7 de prácticas es bastante completa. Para la instalación de `Minikube` me remito a la guía presente en la sesión 4.

Como apunte adicional, si se va a usar `Docker`, hay que asegurarse que el servicio está corriendo. En mi caso:
~~~
sudo systemctl start docker
~~~
Una vez hecho esto debe lanzarse minikube:
~~~
minikube start --driver=docker --container-runtime=containerd
~~~
Y comprobar que está corriendo:
~~~
kubectl get nodes
~~~
Comprobar que OpenFaaS está corriendo en Minikube:
~~~
kubectl get pods -n openfaas
~~~
Hecho esto, hubo problemas para acceder a OpenFaaS. Se tuvo que hacer un port-foward para poder acceder:
~~~
kubectl port-forward -n openfaas svc/gateway 8080:8080
~~~
Esta terminal permanece abierta.

En otra terminal, si OpenFaaS pide autenticación:
~~~
PASSWORD=$(kubectl get secret -n openfaas basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode)
~~~
y
~~~
faas-cli login --username admin --password $PASSWORD --gateway http://127.0.0.1:8080
~~~
Hecho esto lanzar una de las funciones que trae OpenFaaS, por ejemplo, `face-detect-opencv` y comprobar que funciona correctamente como forma de testear que OpenFaaS está funcionando.

## Implementación
Para la implementación se ha partido de una de las plantillas que proporciona OpenFaaS. En primer lugar se ha de obtener esta plantilla:
~~~
faas-cli template store pull python3-http-debian
~~~
Se ha usado esta plantilla en lugar de la plantilla `python3-http` por defecto para evitar el proceso de instalación de `OpenCV`. Una vez se ha descargado se crea la plantilla:
~~~
faas-cli new --lang python3-http-debian deteccion-caras-python
~~~
La estructura del proyecto creado será la siguiente:
~~~
.
├── build
│   └── deteccion-caras-python
│       ├── Dockerfile
│       ├── function
│       │   ├── handler.py
│       │   ├── handler_test.py
│       │   ├── requirements.txt
│       │   └── tox.ini
│       ├── index.py
│       ├── requirements.txt
│       └── template.yml
├── deteccion-caras-python
│   ├── handler.py
│   ├── handler_test.py
│   ├── requirements.txt
│   └── tox.ini
├── stack.yaml
└── template
    └── python3-http-debian
        ├── Dockerfile
        ├── function
        │   ├── handler.py
        │   ├── handler_test.py
        │   ├── requirements.txt
        │   └── tox.ini
        ├── index.py
        ├── requirements.txt
        └── template.yml

~~~
Los archivos que se han de modificar son:
- **deteccion-caras-python/handler.py**: que alberga la funcionalidad principal.
- **deteccion-caras-python/requirements.txt**: que indica qué módulos deben instalarse.
- **stack.yaml**: indica a OpenFaaS como realizar el despliegue.
- **template/python3-http-debian/index.py**: no es *estrictamente* necesario modificarlo, pero en este caso debe hacerse para poder recuperar la imagen en el formato correcto.
#### stack.yaml
En este archivo debe modificarse el nombre de la imagen para que se suba correctamente a Docker Hub. En mi caso:
~~~
version: 1.0
provider:
  name: openfaas
  gateway: http://127.0.0.1:8080
functions:
  deteccion-caras-python:
    lang: python3-http-debian
    handler: ./deteccion-caras-python
    image: iamlassy/deteccion-caras-python:latest
    environment:
      write_debug: true
~~~

#### requirements.txt
Aquí simplemente escribir los módulos de Python necesarios para que funcione el programa:
~~~
opencv-python-headless
numpy
requests
~~~

#### handler.py
Aquí debe modificarse el código de ejemplo para que obtenga la imagen vía una URL:
~~~
import json
import cv2
import numpy as np
import requests

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def handle(req):
    """
    req: bytes o str conteniendo un JSON {"url": "<URL de la imagen>"}
    Devuelve: (body_bytes, status_code, headers_dict)
    """
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
~~~

Se carga el clasificador y se guarda como instancia:
~~~
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)
~~~

Recibe la respuesta HTTP, la convierte a JSON y extrae la URL:
~~~
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
~~~

Descarga la imagen de la URL y la procesa para que pueda ser leída por OpenCV:
~~~
    resp = requests.get(url, timeout=5)
    if resp.status_code != 200:
        msg = f"Error al descargar la imagen: HTTP {resp.status_code}"
        return (
            msg.encode('utf-8'),
            400,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    img_arr = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    if img is None:
        msg = "No se pudo decodificar la imagen."
        return (
            msg.encode('utf-8'),
            400,
            {"Content-Type": "text/plain; charset=utf-8"},
        )
~~~

Realiza la detección de caras y devuelve la imagen como un JPEG vía HTTP:
~~~
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
~~~

#### index.py
Este archivo es parte de la plantilla de OpenFaaS. La principal diferencia respecto al archivo original es la función `format_body`. Se ha modificado para que tenga en cuenta el tipo del body con el que se trabaja para asegurar que los datos sean devueltos correctamente, pues había problemas al devolver la imagen, ya que ésta se devolvía como texto aun guardándose como `.jpg`:
~~~
def format_body(res, content_type):
    # Handler returned dict
    body = res.get('body', None)

    # If raw bytes (images, etc.), return directly
    if isinstance(body, (bytes, bytearray)):
        return body

    # If explicitly octet-stream, return raw
    if content_type == 'application/octet-stream':
        return body or b''

    # If no body, return empty
    if 'body' not in res:
        return ''

    # If JSON object, jsonify
    if isinstance(body, dict):
        return jsonify(body)

    # Otherwise, convert to string
    return str(body)
~~~

## Despliegue
Previo a desplegar la aplicación, es necesario disponer de una cuenta en **`Docker Hub`** y estar loggeado desde la terminal. No es competencia de esta práctica explicar como crear esta cuenta ni como realizar el proceso para disponer de estas credenciales en la terminal. Si se tiene hecho esto habrá que hacer:
~~~
docker login
~~~
Hecho esto lanzar el servicio mediante:
~~~
faas-cli up -f stack.yaml
~~~
***Nota:*** *Conviene comprobar que no haya un servicio con el mismo nombre levantado o puede haber errores a la hora de invocar el servicio.*

Una vez lanzado el servicio se puede comprobar su estado vía la UI de OpenFaaS o mediante la orden:
~~~
faas-cli describe deteccion-caras-python
~~~
Si hubiese algún problema se puede usar la siguiente orden para obtener información de posibles errores:
~~~
faas-cli logs deteccion-caras-python
~~~
Para probar la función se ha usado:
~~~
curl -X POST \
  http://127.0.0.1:8080/function/deteccion-caras-python \
  -d '{"url":"https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSCdio_Sf9aON6NjLHo5fXjG1HNZzWCaTsUjQ"}' \
  --header "Content-Type: application/json" \
  --output resultado.jpg
~~~
Por último, para eliminar el servicio:
~~~
faas-cli remove deteccion-caras-python
~~~