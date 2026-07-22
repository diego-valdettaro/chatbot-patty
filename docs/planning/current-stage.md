# Etapa actual - Etapa 5: Servicio de conversacion sin LLM

## Objetivo

Separar la logica conversacional de Streamlit y preparar el terreno para conectar el LLM sin romper el dominio.

## Principio de trabajo

Cada sub-tarea requiere aprobacion explicita del usuario antes de ejecutarse.

Antes de pedir aprobacion para una sub-tarea, siempre se debe explicar:

- Que se va a hacer.
- Por que existe la sub-tarea.
- Que rol cumple en el entregable final.
- Que queda fuera para no mezclar responsabilidades.
- Como se va a validar.

## Estado

- Estado Etapa 1: `Cerrada`
- Estado Etapa 2: `Cerrada`
- Estado Etapa 3: `Cerrada`
- Estado Etapa 4: `Cerrada`
- Etapa activa: `Etapa 5 - Servicio de conversacion sin LLM`
- Estado general: `Pendiente de aprobacion de sub-tareas`
- Sub-tarea actual: `Definir y aprobar sub-tareas de Etapa 5`

## Cierre de Etapa 4

### Sub-tareas completadas

- [x] 4.1 Definir schema SQLite minimo
- [x] 4.2 Implementar inicializacion de base de datos
- [x] 4.3 Implementar guardado transaccional de pedidos
- [x] 4.4 Validar que solo se guarden pedidos completos
- [x] 4.5 Conectar boton de confirmacion a Streamlit
- [x] 4.6 Bloquear modificaciones despues de confirmar
- [x] 4.7 Agregar tests de persistencia y confirmacion
- [x] 4.8 Validar Etapa 4 y registrar cierre

### Validaciones ejecutadas

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `81 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.
- OK: SQLite se inicializa con tablas `orders` y `order_items`.
- OK: pedidos validos se guardan con items y totales.
- OK: pedidos incompletos o carrito vacio se rechazan.

### Criterios cumplidos

- Completar un pedido valido y confirmar desde boton.
- Guardar filas en SQLite.
- Guardar snapshot de items con nombre, precio, cantidad y subtotal.
- Guardar estado inicial `Pendiente de pago y revision`.
- Bloquear modificaciones despues de confirmar.
- Rechazar guardado de pedidos incompletos.
- `pytest` cubre schema, guardado y rechazos.

### Decisiones cerradas

- La base local vive en `data/patty.sqlite3`.
- La persistencia vive en `src/patty_bot/repository.py`.
- `save_confirmed_order` valida carrito y datos antes de escribir.
- El guardado de `orders` y `order_items` ocurre en una transaccion SQLite.
- El ID interno del pedido se guarda en sesion pero no se muestra al cliente.
- El estado inicial del pedido es `Pendiente de pago y revision`.

## Sub-tareas propuestas para Etapa 5

- [ ] 5.1 Definir estado conversacional minimo
- [ ] 5.2 Crear servicio de conversacion deterministico
- [ ] 5.3 Implementar respuestas para saludo y ayuda
- [ ] 5.4 Implementar respuestas para busqueda de productos
- [ ] 5.5 Implementar respuestas para resumen del pedido
- [ ] 5.6 Implementar solicitud de atencion humana
- [ ] 5.7 Conectar servicio de conversacion a Streamlit
- [ ] 5.8 Agregar tests de conversacion
- [ ] 5.9 Validar Etapa 5 y registrar cierre

## Alcance propuesto para Etapa 5

- Centralizar estado minimo de conversacion.
- Responder de forma deterministica sin LLM.
- Usar servicios de catalogo, carrito y pedido ya existentes.
- Registrar derivacion humana.
- Mantener bloqueo despues de confirmar.

## Fuera de alcance de Etapa 5

- LLM.
- Tools para agente.
- WhatsApp.
- Pagos.
- Edicion post-confirmacion.

## Validaciones esperadas para cerrar Etapa 5

- Saludar al bot.
- Pedir ver productos.
- Pedir resumen.
- Pedir hablar con una persona.
- Confirmar que el bot deja de responder cuando requiere atencion humana.
- `pytest` cubre estados y respuestas deterministicas.

## Proxima accion

Esperar aprobacion del usuario sobre la lista de sub-tareas de Etapa 5.
