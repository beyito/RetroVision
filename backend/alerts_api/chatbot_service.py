import os
import json
import logging
import requests
import secrets
from django.utils.text import slugify
from django.db import transaction
from .models import Tenant, Store, EdgeNode, Camera

logger = logging.getLogger("RetroVision.Chatbot")

AI_TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "listar_tiendas",
                "description": "Lista todas las tiendas físicas (sucursales) registradas para la empresa (tenant) del usuario.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "crear_tienda",
                "description": "Crea una nueva tienda física (sucursal) en la empresa actual.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "nombre": {
                            "type": "STRING",
                            "description": "Nombre de la tienda o sucursal (ej. 'Sucursal Centro')"
                        },
                        "direccion": {
                            "type": "STRING",
                            "description": "Dirección física opcional de la tienda (ej. 'Calle 24 #120')"
                        }
                    },
                    "required": ["nombre"]
                }
            },
            {
                "name": "listar_nodos_edge",
                "description": "Lista todos los dispositivos procesadores locales (nodos edge) de la empresa actual, opcionalmente filtrados por tienda.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "tienda_id": {
                            "type": "INTEGER",
                            "description": "ID numérico de la tienda para filtrar los nodos (opcional)."
                        }
                    }
                }
            },
            {
                "name": "crear_nodo_edge",
                "description": "Crea un nuevo dispositivo procesador (nodo edge) asociado a una tienda de la empresa actual.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "tienda_id": {
                            "type": "INTEGER",
                            "description": "ID numérico de la tienda donde se registrará el nodo edge."
                        },
                        "node_id": {
                            "type": "STRING",
                            "description": "Identificador único de hardware en minúsculas y sin espacios (ej. 'nodo_bodega_01'). Si el usuario no lo da, invéntalo usando el nombre o slug."
                        },
                        "nombre_mostrar": {
                            "type": "STRING",
                            "description": "Nombre descriptivo para mostrar del nodo edge (ej. 'Servidor Central Bodega')"
                        },
                        "control_api_base_url": {
                            "type": "STRING",
                            "description": "URL base de la API de control del nodo. Opcional, por defecto 'http://host.docker.internal:8081'"
                        }
                    },
                    "required": ["tienda_id", "node_id"]
                }
            },
            {
                "name": "listar_camaras",
                "description": "Lista todas las cámaras registradas en la empresa actual, opcionalmente filtradas por tienda o por nodo edge.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "tienda_id": {
                            "type": "INTEGER",
                            "description": "ID numérico de la tienda para filtrar cámaras (opcional)."
                        },
                        "nodo_edge_id": {
                            "type": "INTEGER",
                            "description": "ID numérico de base de datos del nodo edge para filtrar cámaras (opcional)."
                        }
                    }
                }
            },
            {
                "name": "crear_camara",
                "description": "Crea una nueva cámara de monitoreo inteligente vinculada a una tienda y opcionalmente a un nodo edge.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "tienda_id": {
                            "type": "INTEGER",
                            "description": "ID numérico de la tienda a la que pertenece la cámara."
                        },
                        "camera_id": {
                            "type": "STRING",
                            "description": "Identificador único de la cámara en minúsculas y sin espacios (ej. 'cam_caja_01'). Si el usuario no lo proporciona, invéntalo."
                        },
                        "nombre_mostrar": {
                            "type": "STRING",
                            "description": "Nombre descriptivo de la cámara (ej. 'Cámara Entrada Principal')"
                        },
                        "video_source": {
                            "type": "STRING",
                            "description": "Origen del stream de video (ej. 'rtsp://...' o un path de video). Opcional, por defecto '0'."
                        },
                        "nodo_edge_id": {
                            "type": "INTEGER",
                            "description": "ID de base de datos del nodo edge al que se asignará la cámara (opcional)."
                        }
                    },
                    "required": ["tienda_id", "camera_id"]
                }
            }
        ]
    }
]

SYSTEM_INSTRUCTION = """
Eres RetroVision AI Assistant, el asistente virtual oficial de RetroVision, una plataforma SaaS premium de analítica retail y monitoreo inteligente con cámaras. 
Tu objetivo es guiar y ayudar a los administradores a configurar su infraestructura: registrar tiendas, nodos edge (servidores locales) y cámaras.

Siempre debes usar las herramientas provistas para realizar listados y creaciones.
IMPORTANTE:
- Solo puedes gestionar recursos correspondientes a la empresa (tenant) del usuario autenticado. La base de datos local filtra automáticamente todo.
- Si el usuario te pide crear un nodo edge o una cámara pero no te da el ID de la tienda (o menciona una tienda por nombre), primero busca las tiendas registradas usando 'listar_tiendas' para ver si existe y obtener su ID.
- Si la tienda no existe, sugiérele crear la tienda primero o hazlo tú si te lo ha pedido.
- Si te piden crear un nodo edge o cámara y te proporcionan nombres en lugar de IDs únicos sin espacios (node_id, camera_id), puedes generar un ID limpio en minúsculas, usando guiones bajos, a partir del nombre descriptivo.
- Responde siempre en español, de forma muy atenta, educada y profesional. Usa emojis sutilmente para que la conversación sea interactiva.
- Cuando crees un recurso con éxito, indícalo de manera clara destacando sus detalles (nombres, IDs, etc.).
"""

def execute_tool(user, func_name, args, actions_logged):
    """
    Ejecuta la llamada de la función localmente en Django, validando que todo
    pertenezca al tenant del usuario autenticado.
    """
    tenant = user.tenant
    if not tenant:
        return {"error": "El usuario no tiene una empresa (tenant) asociada."}

    try:
        if func_name == "listar_tiendas":
            stores = Store.objects.filter(tenant=tenant)
            return {
                "stores": [
                    {"id": s.id, "name": s.name, "code": s.code, "address": s.address}
                    for s in stores
                ]
            }

        elif func_name == "crear_tienda":
            nombre = args.get("nombre")
            direccion = args.get("direccion") or ""
            if not nombre:
                return {"error": "El parámetro 'nombre' es requerido para crear una tienda."}

            if Store.objects.filter(tenant=tenant, name__iexact=nombre).exists():
                return {"error": f"Ya existe una tienda con el nombre '{nombre}' para tu empresa."}

            code = slugify(nombre)
            if Store.objects.filter(code=code).exists():
                code = f"{code}-{secrets.token_hex(2)}"

            with transaction.atomic():
                store = Store.objects.create(tenant=tenant, name=nombre, code=code, address=direccion)

            actions_logged.append({
                "type": "store_created",
                "id": store.id,
                "name": store.name,
                "code": store.code
            })
            return {
                "status": "success",
                "id": store.id,
                "name": store.name,
                "code": store.code,
                "address": store.address
            }

        elif func_name == "listar_nodos_edge":
            tienda_id = args.get("tienda_id")
            nodes = EdgeNode.objects.filter(store__tenant=tenant)
            if tienda_id:
                nodes = nodes.filter(store_id=tienda_id)
            return {
                "edge_nodes": [
                    {
                        "id": n.id,
                        "node_id": n.node_id,
                        "display_name": n.display_name,
                        "store_id": n.store_id,
                        "store_name": n.store.name
                    }
                    for n in nodes
                ]
            }

        elif func_name == "crear_nodo_edge":
            tienda_id = args.get("tienda_id")
            node_id = args.get("node_id")
            nombre_mostrar = args.get("nombre_mostrar") or ""
            control_api_base_url = args.get("control_api_base_url") or "http://host.docker.internal:8081"

            if not tienda_id or not node_id:
                return {"error": "Los parámetros 'tienda_id' y 'node_id' son obligatorios."}

            store = Store.objects.filter(id=tienda_id, tenant=tenant).first()
            if not store:
                return {"error": f"No se encontró una tienda activa con ID {tienda_id} vinculada a tu empresa."}

            if EdgeNode.objects.filter(node_id=node_id).exists():
                return {"error": f"El ID de dispositivo (Node ID) '{node_id}' ya está registrado globalmente. Elige uno diferente."}

            with transaction.atomic():
                node = EdgeNode.objects.create(
                    store=store,
                    node_id=node_id,
                    display_name=nombre_mostrar or node_id,
                    control_api_base_url=control_api_base_url
                )

            actions_logged.append({
                "type": "edgenode_created",
                "id": node.id,
                "node_id": node.node_id,
                "display_name": node.display_name,
                "store_name": store.name
            })
            return {
                "status": "success",
                "id": node.id,
                "node_id": node.node_id,
                "display_name": node.display_name,
                "api_key": node.api_key
            }

        elif func_name == "listar_camaras":
            tienda_id = args.get("tienda_id")
            nodo_edge_id = args.get("nodo_edge_id")
            cameras = Camera.objects.filter(store__tenant=tenant)
            if tienda_id:
                cameras = cameras.filter(store_id=tienda_id)
            if nodo_edge_id:
                cameras = cameras.filter(edge_node_id=nodo_edge_id)
            return {
                "cameras": [
                    {
                        "id": c.id,
                        "camera_id": c.camera_id,
                        "display_name": c.display_name,
                        "video_source": c.video_source,
                        "store_id": c.store_id,
                        "store_name": c.store.name if c.store else "",
                        "edge_node_id": c.edge_node_id,
                        "edge_node_name": c.edge_node.display_name if c.edge_node else ""
                    }
                    for c in cameras
                ]
            }

        elif func_name == "crear_camara":
            tienda_id = args.get("tienda_id")
            camera_id = args.get("camera_id")
            nombre_mostrar = args.get("nombre_mostrar") or ""
            video_source = args.get("video_source") or "0"
            nodo_edge_id = args.get("nodo_edge_id")

            if not tienda_id or not camera_id:
                return {"error": "Los parámetros 'tienda_id' y 'camera_id' son requeridos."}

            store = Store.objects.filter(id=tienda_id, tenant=tenant).first()
            if not store:
                return {"error": f"No se encontró una tienda activa con ID {tienda_id} vinculada a tu empresa."}

            # Validar límite de cámaras del Tenant
            existing_count = Camera.objects.filter(store__tenant=tenant).count()
            if existing_count >= tenant.max_cameras:
                return {"error": f"Límite de cámaras ({tenant.max_cameras}) alcanzado para tu plan de suscripción."}

            if Camera.objects.filter(camera_id=camera_id).exists():
                return {"error": f"El ID de cámara '{camera_id}' ya está registrado. Elige otro ID."}

            edge_node = None
            if nodo_edge_id:
                edge_node = EdgeNode.objects.filter(id=nodo_edge_id, store__tenant=tenant).first()
                if not edge_node:
                    return {"error": f"No se encontró un nodo edge activo con ID {nodo_edge_id} vinculado a tu empresa."}

            with transaction.atomic():
                camera = Camera.objects.create(
                    store=store,
                    camera_id=camera_id,
                    display_name=nombre_mostrar or camera_id,
                    video_source=video_source,
                    edge_node=edge_node
                )

            actions_logged.append({
                "type": "camera_created",
                "id": camera.id,
                "camera_id": camera.camera_id,
                "display_name": camera.display_name,
                "store_name": store.name
            })
            return {
                "status": "success",
                "id": camera.id,
                "camera_id": camera.camera_id,
                "display_name": camera.display_name
            }

        else:
            return {"error": f"La herramienta '{func_name}' no está implementada."}

    except Exception as e:
        logger.error(f"Error al ejecutar herramienta {func_name}: {e}", exc_info=True)
        return {"error": f"Excepción interna al ejecutar {func_name}: {str(e)}"}

def run_chatbot_session(user, message: str, history: list) -> tuple:
    """
    Gestiona la sesión con Gemini ejecutando las herramientas de base de datos
    de manera iterativa en un bucle si el modelo realiza Tool Calling.
    
    Retorna: (respuesta_texto, historial_actualizado, acciones_realizadas)
    """
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise ValueError("La variable de entorno AI_API_KEY no está configurada en el servidor.")

    model = os.getenv("AI_MODEL", "gemini-3.1-flash-lite-preview")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    # Mapear el historial del cliente al formato de contenido de Gemini
    contents = []
    for turn in history:
        role = "user" if turn.get("role") == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": turn.get("text", "")}]
        })

    # Agregar el mensaje actual del usuario
    contents.append({
        "role": "user",
        "parts": [{"text": message}]
    })

    actions_logged = []
    max_loops = 5
    loop_count = 0

    while loop_count < max_loops:
        loop_count += 1
        payload = {
            "contents": contents,
            "tools": AI_TOOLS,
            "systemInstruction": {
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=40)
            response.raise_for_status()
            resp_json = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini API request failed: {e}")
            raise ValueError(f"Error al conectar con la API de Gemini: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise ValueError("La API de Gemini devolvió una respuesta con formato inválido.")

        # Verificar si hay contenido
        candidates = resp_json.get("candidates", [])
        if not candidates:
            raise ValueError("No se recibió respuesta del modelo de IA.")

        candidate = candidates[0]
        content = candidate.get("content")
        if not content:
            raise ValueError("No se recibió contenido de la IA.")

        parts = content.get("parts", [])
        
        # Buscar llamadas a funciones
        function_calls = [p.get("functionCall") for p in parts if p.get("functionCall")]

        if function_calls:
            # 1. Conservar la llamada del modelo en el historial de conversación
            contents.append(content)

            # 2. Ejecutar todas las llamadas de función y recopilar las respuestas
            response_parts = []
            for fc in function_calls:
                name = fc.get("name")
                args = fc.get("args") or {}
                logger.info(f"Chatbot Tool Call: {name} con argumentos {args}")
                
                result = execute_tool(user, name, args, actions_logged)
                
                response_parts.append({
                    "functionResponse": {
                        "name": name,
                        "response": {
                            "output": result
                        }
                    }
                })

            # 3. Añadir la respuesta del usuario (con los resultados de las funciones) al historial
            contents.append({
                "role": "user",
                "parts": response_parts
            })
            
            # Continuar con la siguiente iteración del loop
            continue

        else:
            # Si no hay llamadas a funciones, este es el mensaje final
            text_resp = "".join([p.get("text", "") for p in parts if p.get("text")])
            
            # Formatear el historial para devolverlo al cliente en formato simplificado
            simplified_history = []
            # Tomamos el historial original
            simplified_history.extend(history)
            # Agregamos el mensaje del usuario
            simplified_history.append({"role": "user", "text": message})
            # Agregamos la respuesta final del asistente
            simplified_history.append({"role": "model", "text": text_resp})

            return text_resp, simplified_history, actions_logged

    # En caso de que se alcance el límite de loops sin un texto final
    fallback_text = "Disculpa, el procesamiento tomó más pasos de lo esperado. ¿Podrías simplificar tu solicitud?"
    simplified_history = list(history)
    simplified_history.append({"role": "user", "text": message})
    simplified_history.append({"role": "model", "text": fallback_text})
    
    return fallback_text, simplified_history, actions_logged
