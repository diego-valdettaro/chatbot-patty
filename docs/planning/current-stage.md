# Etapa actual - Estabilización antes de integrar canales

## Seguimiento oficial

El plan ejecutable, sus dependencias y el estado de cada corte viven en
[`stabilization-roadmap.md`](stabilization-roadmap.md). Cada tarea se gestiona
en un único Issue y un único PR con `Closes #<issue>`. GitHub actualiza sus
labels cuando un PR recibe aprobación, cambios solicitados o se fusiona.

Estado inmediato: **Ola 0 / P00 — Tracking y Action de PRs: en progreso**.
La siguiente tarea solo se considera lista cuando su dependencia figure como
fusionada en el roadmap y en GitHub.

# Historial - Etapa 8: Derivación humana y límites conversacionales

## Objetivo

Evitar que el bot continúe cuando el pedido requiere atención humana, está fuera de alcance o no puede interpretarse con seguridad.

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
- Estado Etapa 5: `Cerrada`
- Estado Etapa 6: `Cerrada`
- Estado Etapa 7: `Cerrada`
- Etapa activa: `Etapa 8 - Derivación humana y límites conversacionales`
- Estado Etapa 8: `Pendiente de aprobación de sub-tareas`
- Estado general: `En progreso`
- Sub-tarea actual: `Definir y aprobar 8.1`

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

- [x] 5.1 Definir contratos de entrada y salida comunes para tools
- [x] 5.2 Exponer tool de busqueda de catalogo
- [x] 5.3 Exponer tools de lectura y modificacion del carrito
- [x] 5.4 Exponer tools de validacion, calculo y confirmacion del pedido
- [x] 5.4.1 Modelar pedido confirmado con `Order` y `OrderItem`
- [x] 5.5 Crear registro explicito de tools disponible para el agente
- [x] 5.6 Agregar tests de contratos, resultados y errores controlados
- [x] 5.7 Validar Etapa 5 y registrar cierre

## Alcance propuesto para Etapa 5

- Reutilizar catalogo, carrito, pedido y persistencia ya implementados.
- Definir entradas y salidas serializables para cada operacion.
- Devolver resultados de negocio y errores controlados, no texto conversacional.
- Representar el pedido confirmado como un snapshot inmutable distinto del carrito editable.
- Mantener una lista explicita de tools que el futuro agente podra invocar.
- Cubrir las tools con tests directos, sin depender de un proveedor LLM.

## Fuera de alcance de Etapa 5

- Interpretacion de mensajes de usuario, keywords o clasificacion de intenciones.
- Saludos, ayuda y redaccion de respuestas conversacionales.
- LLM, proveedor, credenciales, prompt y bucle agente-tool.
- WhatsApp, pagos y edicion post-confirmacion.

## Validaciones esperadas para cerrar Etapa 5

- Cada tool acepta entradas validas y produce una salida estructurada esperada.
- Errores de dominio se devuelven como resultados controlados, sin excepciones de interfaz.
- Las tools no duplican calculos, validaciones ni escrituras ya existentes.
- `pytest` cubre casos validos y rechazos de cada tool.
- Un pedido confirmado conserva detalles, items, totales, estado, fecha e ID interno como `Order`.

## Proxima accion

Explicar y solicitar aprobacion de las sub-tareas de Etapa 6.

## Cierre de Etapa 5

### Sub-tareas completadas

- [x] 5.1 Definir contratos de entrada y salida comunes para tools
- [x] 5.2 Exponer tool de busqueda de catalogo
- [x] 5.3 Exponer tools de lectura y modificacion del carrito
- [x] 5.4 Exponer tools de validacion, calculo y confirmacion del pedido
- [x] 5.4.1 Modelar pedido confirmado con `Order` y `OrderItem`
- [x] 5.5 Crear registro explicito de tools disponible para el agente
- [x] 5.6 Agregar tests de contratos, resultados y errores controlados
- [x] 5.7 Validar Etapa 5 y registrar cierre

### Validaciones ejecutadas

- OK: `pytest` pasa con `110 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.
- OK: tools y schemas son JSON serializables.
- OK: entradas invalidas y errores de persistencia devuelven errores controlados.
- OK: `confirm_order` requiere una confirmacion explicita en su metadata.

### Criterios cumplidos

- Catalogo, carrito y pedido estan expuestos como adaptadores finos sobre el dominio.
- El registro es una allowlist explicita; no existe acceso arbitrario a funciones internas.
- Los resultados usan un contrato uniforme con datos o errores controlados.
- Carrito editable y pedido confirmado se representan con modelos diferentes.
- El ID interno y datos privados no se entregan al agente.

### Decisiones cerradas

- El LLM recibira metadata del registro, no referencias ejecutables a funciones Python.
- El futuro ejecutor mantendra el estado de sesion en servidor y despachara solo handlers permitidos.
- `confirm_order` no debe ejecutarse por una interpretacion automatica: requiere accion explicita del cliente/UI.
- La Etapa 6 se encarga de adaptar este registro al proveedor LLM y de implementar el ejecutor controlado.

## Sub-tareas propuestas para Etapa 6

- [x] 6.1 Definir configuracion local del proveedor LLM y variables de entorno
- [x] 6.2 Adaptar el registro a los schemas del proveedor elegido
- [x] 6.3 Implementar ejecutor de tools con estado de sesion y proteccion de confirmacion
- [x] 6.4 Implementar prompt de sistema y bucle agente-tool
- [x] 6.5 Conectar chat de Streamlit al agente
- [x] 6.6 Agregar tests con proveedor LLM simulado
- [x] 6.7 Validar Etapa 6 y registrar cierre

### Etapa 6.2 completada - Adaptador de schemas OpenAI

- Se creo `src/patty_bot/openai_tools.py` para traducir el registro allowlist a funciones del formato Responses API de OpenAI.
- Cada definicion publica solo `type`, `name`, `description`, `parameters` y `strict`; handlers internos y metadata de confirmacion no se exponen al proveedor.
- Los schemas se normalizan para modo estricto: todos los campos se declaran requeridos y los opcionales del dominio se representan como anulables.
- `confirm_order` sigue siendo una accion protegida; el futuro ejecutor en servidor aplicara esa regla.
- Se agregaron pruebas de formato, serializacion, aislamiento de metadata y schemas con objetos anidados.

### Etapa 6.3 completada - Ejecutor controlado de tools

- Se creo `src/patty_bot/tool_executor.py` con `AgentSession`, que mantiene catalogo, carrito, datos del pedido, pedido confirmado y contexto de fecha exclusivamente en servidor.
- `execute_tool_call` resuelve cada llamada mediante el registro allowlist y nunca importa ni invoca handlers arbitrarios desde texto del modelo.
- El ejecutor conserva el estado actualizado de carrito y pedido entre llamadas; los resultados para el agente siguen usando `ToolResult`.
- `confirm_order` se rechaza salvo que la capa de UI entregue `explicit_confirmation=True`; despues de confirmar, cualquier nueva llamada queda bloqueada.
- Los `null` requeridos por el schema estricto de OpenAI se traducen a campos omitidos para actualizaciones incrementales, excepto la fecha que puede limpiarse explicitamente.
- Se agregaron pruebas para allowlist, estado de sesion, compatibilidad strict, proteccion de confirmacion y bloqueo post-confirmacion.

### Etapa 6.4 completada - Router LLM y bucle agente-tool

- Se creo `src/patty_bot/agent_router.py` con el prompt de sistema en espanol, el cliente perezoso de OpenAI y un bucle acotado de Responses API.
- El router entrega al modelo el schema de tools, reinyecta las llamadas y sus resultados, y deja que el modelo redacte la respuesta final.
- Las llamadas se despachan exclusivamente por `execute_tool_call`; el router nunca concede la confirmacion explicita al modelo.
- El prompt prohíbe inventar datos de negocio, procesar pagos o confirmar pedidos.
- Se agregaron pruebas con cliente Responses simulado para llamadas de tool, replay de resultados, limite de rondas y rechazo de confirmacion desde el modelo.

### Etapa 6.5 completada - Chat de Streamlit

- El input de chat de `app.py` ahora usa el router LLM y sincroniza de regreso carrito, datos del pedido y pedido confirmado con el estado de Streamlit.
- La aplicacion conserva un mensaje seguro cuando falta configuracion, SDK o hay un fallo del proveedor; no expone detalles operativos al cliente.
- El boton de confirmacion existente se mantiene como la unica accion de UI que puede persistir un pedido.

## Etapa 7.1 completada - Estructura chat-first

- El chat es ahora la superficie principal de la página y muestra un saludo inicial cuando no existe historial.
- El carrito, los datos de entrega y la confirmación permanecen visibles en un panel de apoyo llamado `Tu pedido`.
- La búsqueda y adición manual de catálogo se conserva como alternativa dentro de un desplegable, sin competir con el flujo conversacional.
- No se modificaron el dominio, las tools, SQLite ni la regla de confirmación exclusiva por botón.
- Validación: `pytest` ejecutó correctamente 130 pruebas; tres pruebas que usan `tmp_path` no se pudieron iniciar por permisos del entorno sobre directorios temporales de Pytest. La comprobación de la interfaz queda pendiente de validación manual local.

## Próxima acción

Explicar y solicitar aprobación de la sub-tarea 8.1.

## Etapa 7.2 completada - Escenarios conversacionales de aceptación

- Se agregó `tests/test_conversation_acceptance.py` con un cliente Responses simulado, sin red ni claves reales.
- Los escenarios cubren: creación de un pedido válido para recojo y consulta de su resumen; cambio de cantidades con contexto conversacional previo; y producto sin disponibilidad sin alteración del carrito.
- Las pruebas verifican herramientas, estado final de carrito/pedido y datos estructurados devueltos por las tools, sin depender del texto libre generado por el LLM.
- También se mantiene comprobada la protección existente: el agente no puede confirmar un pedido por chat.
- Validación: `133 passed, 3 deselected`. Los tres casos omitidos usan `tmp_path`, inaccesible en este entorno por permisos de Pytest.

## Etapa 7.3 completada - Checklist de validación manual

- Se creó `docs/planning/stage-7-manual-checklist.md` con los recorridos de revisión visual y funcional de la interfaz centrada en el chat.
- La guía cubre primer contacto, pedido y modificación conversacionales, datos y resumen, búsqueda manual, confirmación protegida y bloqueo posterior.
- La ejecución de esta checklist requiere una sesión local de Streamlit con las credenciales del proveedor configuradas; queda pendiente para cerrar la etapa.
- Comprobación disponible: Streamlit respondió HTTP 200 en `http://localhost:8501`. La inspección visual automatizada no pudo realizarse porque el navegador integrado no está disponible en esta sesión.

## Cierre de Etapa 7

- La interfaz queda centrada en el chat, con el pedido como panel de apoyo y la búsqueda manual como alternativa.
- Los escenarios automatizados cubren pedido válido, edición contextual y falta de disponibilidad mediante un proveedor simulado.
- La checklist manual queda disponible como evidencia de revisión futura. El cierre se realiza por aprobación expresa del usuario, sin ejecutar la inspección visual automatizada.

## Sub-tarea propuesta para Etapa 8

- [ ] 8.1 Definir el estado y el contrato de derivación humana

## Cierre de Etapa 6

### Validaciones ejecutadas

- OK: configuración del proveedor mediante `.env`, sin secretos versionados.
- OK: schemas OpenAI estrictos y registro allowlist de tools.
- OK: ejecutor con estado de sesión, errores controlados, bloqueo post-confirmación y confirmación exclusiva de la UI.
- OK: router con proveedor simulado, bucle tool-result y contexto conversacional reciente.
- OK: pruebas de configuración, router y ejecutor pasan con `16 passed`.
- OK: validación manual del usuario con OpenAI real: conversación, búsqueda, selección de producto y cambios visibles en la app.

### Criterios cumplidos

- El LLM interpreta lenguaje natural y responde en español, sin ser fuente de verdad de negocio.
- Las operaciones de catálogo, carrito y pedido pasan solo por tools deterministas permitidas.
- El estado del pedido permanece en el servidor y se sincroniza con Streamlit.
- La confirmación no puede ser emitida por el LLM; requiere la acción explícita del botón.
- El contexto reciente permite resolver referencias breves entre mensajes, como "sí".

### Siguiente etapa sugerida

Rediseñar Streamlit a una experiencia chat-first y ampliar la batería de escenarios conversacionales de aceptación.
