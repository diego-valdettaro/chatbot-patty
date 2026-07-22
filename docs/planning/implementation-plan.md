# Plan de implementación - Chatbot de pedidos Patty MVP

## Principio de ejecución

Este plan está organizado en cortes verticales. Cada etapa debe dejar una versión ejecutable, observable y validable de la aplicación antes de pasar a la siguiente.

La regla práctica es: primero construir un flujo pequeño que funcione de punta a punta, luego ampliar capacidades. El LLM nunca debe ser la fuente de verdad para precios, totales, reglas de fecha, reglas de modalidad ni persistencia.

## Arquitectura objetivo

```text
Streamlit UI
  -> Conversation service
  -> Agent / intent interpreter
  -> Deterministic application services
       -> Catalog service
       -> Cart service
       -> Order validation service
       -> SQLite repository
```

## Estructura inicial propuesta

```text
chatbot-patty/
  app.py
  data/
    catalog.sample.csv
    patty.sqlite3
  docs/
    planning/
      prd.md
      implementation-plan.md
  src/
    patty_bot/
      __init__.py
      config.py
      catalog.py
      cart.py
      dates.py
      models.py
      orders.py
      validation.py
      conversation.py
      tools.py
  tests/
    test_catalog.py
    test_cart.py
    test_validation.py
    test_orders.py
```

## Etapa 0 - Base del proyecto ejecutable

### Objetivo

Tener una aplicación local mínima que arranque, una estructura de código clara y una forma repetible de correr pruebas.

### Alcance

- Crear estructura Python del proyecto.
- Definir dependencias mínimas.
- Crear `app.py` con una pantalla Streamlit básica.
- Crear configuración centralizada para rutas, moneda, delivery fijo y tiendas.
- Crear README mínimo con comandos de ejecución.
- Configurar pytest.

### Entregable tangible

Una app Streamlit que abre localmente y muestra:

- Título del chatbot.
- Estado de sesión vacío.
- Campo de chat o input simple.
- Mensaje fijo de respuesta temporal.

### Validación manual

- Ejecutar `streamlit run app.py`.
- Abrir la aplicación en el navegador.
- Enviar un mensaje y ver una respuesta temporal.

### Validación técnica

- Ejecutar `pytest`.
- Confirmar que existe al menos un test smoke.

### Criterio de salida

La app corre localmente y hay una base limpia para agregar dominio, catálogo y persistencia.

## Etapa 1 - Catálogo local y búsqueda determinística

### Objetivo

Tener un catálogo consultable sin LLM, respetando las reglas de productos activos, precios válidos y sugerencias limitadas.

### Alcance

- Crear `data/catalog.sample.csv` con 30 productos de prueba o una muestra representativa mientras se obtiene el export real.
- Definir campos mínimos del catálogo:
  - `id`
  - `name`
  - `aliases`
  - `category`
  - `price`
  - `active`
- Implementar carga del catálogo.
- Implementar búsqueda por:
  - nombre exacto
  - alias
  - similitud aproximada
  - categoría
- Limitar alternativas a máximo dos.
- Excluir productos inactivos.

### Entregable tangible

La app permite escribir una búsqueda y muestra productos reales del catálogo con precio.

### Validación manual

- Buscar un producto por nombre exacto.
- Buscar un producto por alias.
- Buscar un producto con error tipográfico leve.
- Buscar un producto inexistente con alternativa similar.
- Buscar un producto inexistente sin alternativa.

### Validación técnica

- Tests unitarios de carga de catálogo.
- Tests unitarios de búsqueda exacta.
- Tests unitarios de alias.
- Tests unitarios de productos inactivos.
- Tests unitarios de máximo dos sugerencias.

### Criterio de salida

La aplicación puede consultar productos válidos sin inventar nombres ni precios.

## Etapa 2 - Carrito y cálculo de totales

### Objetivo

Permitir armar y modificar un carrito con cálculos determinísticos.

### Alcance

- Implementar modelo de carrito.
- Agregar productos por `product_id`.
- Asumir cantidad `1` cuando no se especifique.
- Validar cantidades enteras mayores que cero.
- Cambiar cantidades.
- Eliminar productos.
- Calcular:
  - subtotal por producto
  - subtotal general
  - delivery
  - total
- Mostrar resumen del carrito en Streamlit.

### Entregable tangible

La app permite buscar productos, agregarlos al carrito, cambiar cantidades y ver totales recalculados.

### Validación manual

- Agregar un producto.
- Agregar dos productos.
- Cambiar una cantidad.
- Eliminar un producto.
- Confirmar que los subtotales y total cambian correctamente.

### Validación técnica

- Tests de agregar producto.
- Tests de cantidad por defecto.
- Tests de cantidad inválida.
- Tests de eliminar producto.
- Tests de subtotal y total.

### Criterio de salida

El carrito funciona sin LLM y los cálculos no dependen de texto generado.

## Etapa 3 - Datos obligatorios, modalidad y fecha

### Objetivo

Validar los datos necesarios para confirmar un pedido antes de introducir guardado o LLM.

### Alcance

- Capturar nombre y teléfono.
- Capturar modalidad:
  - delivery
  - recojo
- Para delivery, capturar dirección.
- Para recojo, capturar tienda:
  - Benavides
  - San Isidro
- Capturar fecha solicitada.
- Validar regla de anticipación:

```text
fecha solicitada >= fecha actual + 2 días
```

- Calcular delivery:
  - delivery: S/ 10
  - recojo: S/ 0
- Mostrar lista de campos faltantes o inválidos.
- Habilitar visualmente la confirmación solo cuando el pedido sea válido.

### Entregable tangible

La app muestra un formulario o panel lateral con los datos del pedido, valida campos y actualiza el resumen.

### Validación manual

- Intentar confirmar sin nombre.
- Intentar delivery sin dirección.
- Intentar recojo sin tienda.
- Usar fecha con menos de dos días.
- Usar fecha válida.
- Cambiar de delivery a recojo y verificar que el delivery pase a S/ 0.

### Validación técnica

- Tests de datos faltantes.
- Tests de regla de fecha.
- Tests de delivery vs recojo.
- Tests de tiendas permitidas.

### Criterio de salida

La app ya puede construir un pedido completo y validar si está listo para confirmarse, aunque todavía no lo persista.

## Etapa 4 - Persistencia SQLite y confirmación real

### Objetivo

Guardar pedidos confirmados en SQLite de forma transaccional y bloquear modificaciones posteriores.

### Alcance

- Crear esquema SQLite:
  - `orders`
  - `order_items`
- Definir campos mínimos de `orders`:
  - `id`
  - `customer_name`
  - `customer_phone`
  - `fulfillment_type`
  - `requested_date`
  - `delivery_address`
  - `pickup_store`
  - `subtotal`
  - `delivery_fee`
  - `total`
  - `status`
  - `created_at`
- Definir campos mínimos de `order_items`:
  - `id`
  - `order_id`
  - `product_id`
  - `product_name`
  - `unit_price`
  - `quantity`
  - `line_subtotal`
- Implementar guardado dentro de una transacción.
- Confirmar solo desde botón Streamlit.
- Mostrar mensaje exitoso solo si el guardado terminó bien.
- Bloquear cambios si `order_confirmed = true`.
- No mostrar código de pedido al cliente.

### Entregable tangible

La app permite confirmar un pedido válido y deja filas persistidas en SQLite.

### Validación manual

- Completar un pedido válido.
- Pulsar confirmar.
- Ver mensaje de confirmación.
- Verificar que el carrito queda bloqueado.
- Recargar la app y confirmar que la conversación no se recupera.
- Inspeccionar SQLite y confirmar que existen `orders` y `order_items`.

### Validación técnica

- Tests de creación de esquema.
- Tests de guardado transaccional.
- Tests de error de guardado sin falso positivo.
- Tests de estado inicial `Pendiente de pago y revisión`.

### Criterio de salida

Existe un flujo manual completo de pedido, desde catálogo hasta confirmación persistida.

## Etapa 5 - Servicio de conversación sin LLM

### Objetivo

Separar la lógica conversacional de Streamlit y preparar el terreno para conectar el LLM sin romper el dominio.

### Alcance

- Crear `conversation.py`.
- Centralizar estado mínimo de sesión:
  - `messages`
  - `cart`
  - `customer_name`
  - `customer_phone`
  - `fulfillment_type`
  - `requested_date`
  - `delivery_address`
  - `pickup_store`
  - `failed_attempts`
  - `requires_human`
  - `order_confirmed`
- Implementar respuestas determinísticas simples para:
  - saludo
  - búsqueda de productos
  - agregar por selección explícita
  - pedido de datos faltantes
  - resumen
  - solicitud de modificar
  - solicitud de atención humana
- Registrar eventos de desarrollo:
  - mensaje de usuario
  - acción ejecutada
  - errores
  - derivaciones
  - confirmaciones

### Entregable tangible

La app ya se comporta como chat básico aunque las interpretaciones complejas todavía sean limitadas.

### Validación manual

- Saludar al bot.
- Pedir ver productos.
- Seleccionar un producto.
- Pedir resumen.
- Pedir hablar con una persona.
- Ver que el bot deja de responder cuando requiere atención humana.

### Validación técnica

- Tests de inicialización de estado.
- Tests de transición a atención humana.
- Tests de bloqueo tras confirmación.
- Tests de respuesta con campos faltantes.

### Criterio de salida

Streamlit ya es principalmente una interfaz; la lógica de conversación vive en servicios testeables.

## Etapa 6 - Tools iniciales y contrato para el agente

### Objetivo

Exponer las operaciones del dominio como tools controladas, con entradas y salidas explícitas, antes de conectar el LLM.

### Alcance

- Implementar tools como funciones puras o adaptadores finos:
  - `search_products`
  - `get_product`
  - `update_cart`
  - `validate_order`
  - `save_order`
- Definir schemas de entrada y salida.
- Garantizar que las tools:
  - no aceptan precios desde el usuario
  - no ejecutan SQL arbitrario
  - no guardan pedidos sin validación
  - no guardan pedidos si no hay acción explícita de confirmación
- Agregar logging de tool llamada y resultado.

### Entregable tangible

Una consola de pruebas, endpoint interno o pantalla de debug permite ejecutar tools y ver resultados.

### Validación manual

- Ejecutar `search_products` desde la app o debug panel.
- Ejecutar `update_cart` con producto válido.
- Ejecutar `validate_order` con datos incompletos.
- Intentar pasar precio manipulado y confirmar que se ignora o rechaza.

### Validación técnica

- Tests por tool.
- Tests de contrato de entrada y salida.
- Tests contra manipulación de precio.
- Tests de que `save_order` no corre sin confirmación explícita.

### Criterio de salida

El dominio está listo para ser usado por un agente sin cederle reglas críticas.

## Etapa 7 - Integración LLM para interpretación de pedidos

### Objetivo

Permitir que el usuario escriba pedidos en lenguaje natural y que el agente use las tools para resolverlos.

### Alcance

- Configurar proveedor LLM con variable de entorno.
- Integrar LangChain `create_agent` o equivalente vigente del stack elegido.
- Crear prompt de sistema con reglas del PRD:
  - responder solo en español
  - no inventar productos
  - no inventar precios
  - no procesar pagos
  - pedir aclaración ante ambigüedad
  - derivar en casos fuera de alcance
- Conectar tools.
- Procesar varios productos en un mismo mensaje.
- Reconocer cantidades numéricas y en lenguaje natural.
- Resolver producto sin cantidad como cantidad `1`.
- Preguntar por variante cuando haya más de una coincidencia plausible.

### Entregable tangible

La app acepta mensajes como:

```text
Quiero dos brownies y una torta de zanahoria para delivery el viernes.
```

Y responde con productos agregados, datos faltantes o aclaraciones.

### Validación manual

- Pedido simple de un producto.
- Pedido con varios productos.
- Producto sin cantidad.
- Producto con variantes.
- Producto inexistente con alternativa.
- Producto inexistente sin alternativa.
- Mensaje en otro idioma.
- Intento de cambiar el precio.

### Validación técnica

- Tests unitarios siguen cubriendo dominio determinístico.
- Agregar tests de integración con LLM mockeado.
- Guardar transcripciones manuales de escenarios críticos.

### Criterio de salida

El chatbot ya puede tomar pedidos en lenguaje natural sin comprometer reglas de negocio.

## Etapa 8 - Modificaciones conversacionales y resumen previo

### Objetivo

Completar el flujo de edición del pedido antes de confirmar.

### Alcance

- Soportar por conversación:
  - agregar productos
  - eliminar productos
  - cambiar cantidades
  - cambiar fecha
  - cambiar delivery/recojo
  - cambiar dirección
  - cambiar tienda
- Mostrar resumen actualizado después de modificaciones relevantes.
- Mantener botón `Modificar pedido`.
- Mantener botón `Confirmar pedido` solo si el pedido es válido.
- Evitar modificaciones después de confirmar.

### Entregable tangible

Una persona puede construir, corregir y revisar un pedido completo desde el chat antes de confirmarlo.

### Validación manual

- Modificación de cantidades.
- Cambio de delivery a recojo.
- Cambio de recojo a delivery.
- Eliminación de producto.
- Cambio de fecha inválida a válida.
- Resumen completo antes de confirmar.

### Validación técnica

- Tests de modificaciones del carrito.
- Tests de recálculo al cambiar modalidad.
- Tests de bloqueo post-confirmación.

### Criterio de salida

El flujo conversacional principal está completo antes del guardado final.

## Etapa 9 - Derivación humana y casos fuera de alcance

### Objetivo

Implementar correctamente los límites del bot y evitar respuestas automáticas cuando corresponde escalar.

### Alcance

- Detectar solicitud explícita de atención humana.
- Contar intentos fallidos.
- Derivar después de dos intentos no entendidos.
- Derivar ante casos fuera del alcance:
  - pagos
  - stock
  - alérgenos
  - promociones
  - horarios
  - modificación post-confirmación
  - B2B
- Marcar `requires_human = true`.
- Mostrar estado visual de derivación en Streamlit.
- Detener respuestas automáticas después de derivar.

### Entregable tangible

La app muestra que la conversación requiere atención humana y el bot deja de continuar el flujo.

### Validación manual

- Escribir "quiero hablar con una persona".
- Enviar dos mensajes consecutivos incomprensibles.
- Preguntar por pagos, stock o alérgenos.
- Confirmar que el bot informa la derivación y se detiene.

### Validación técnica

- Tests de intentos fallidos.
- Tests de temas fuera de alcance.
- Tests de bloqueo de respuesta automática.

### Criterio de salida

El bot tiene límites claros y no intenta resolver lo que el MVP no cubre.

## Etapa 10 - Endurecimiento, métricas y suite de aceptación

### Objetivo

Cerrar el MVP con trazabilidad, pruebas mínimas de aceptación y revisión contra el PRD.

### Alcance

- Implementar logging estructurado de desarrollo.
- Crear checklist ejecutable o documentado de los 20 escenarios mínimos.
- Agregar pantalla o archivo de métricas de validación:
  - pedidos completados
  - productos identificados correctamente
  - aclaraciones por pedido
  - derivaciones
  - errores de cálculo
  - errores de guardado
  - tiempo promedio para completar pedido
  - casos de invención o interpretación incorrecta
- Revisar seguridad:
  - API key por variable de entorno
  - sin secretos en código
  - sin SQL arbitrario del LLM
  - precios solo desde catálogo
- Revisar comportamiento de recarga de la app.

### Entregable tangible

Una versión MVP candidata que se puede probar contra todos los criterios de aceptación del PRD.

### Validación manual

Ejecutar los 20 escenarios mínimos del PRD:

- Pedido simple de un producto.
- Pedido con varios productos.
- Producto sin cantidad.
- Producto con varias variantes.
- Producto inexistente con alternativa similar.
- Producto inexistente sin alternativa.
- Delivery válido.
- Recojo en Benavides.
- Recojo en San Isidro.
- Fecha con menos de dos días.
- Modificación de cantidades.
- Cambio de delivery a recojo.
- Eliminación de producto.
- Confirmación correcta.
- Error al guardar en la base de datos.
- Solicitud explícita de atención humana.
- Dos mensajes consecutivos que no puedan entenderse.
- Mensaje en otro idioma.
- Intento de cambiar el precio.
- Recarga de la aplicación después de confirmar un pedido.

### Validación técnica

- Ejecutar toda la suite `pytest`.
- Ejecutar revisión manual de SQLite después de confirmaciones.
- Revisar logs de tool calls y errores.

### Criterio de salida

El MVP cumple la definición de hecho del PRD o deja documentadas las brechas pendientes.

## Orden recomendado de construcción

1. Base del proyecto ejecutable.
2. Catálogo local y búsqueda.
3. Carrito y cálculo.
4. Datos obligatorios, modalidad y fecha.
5. SQLite y confirmación.
6. Servicio de conversación sin LLM.
7. Tools para el agente.
8. Integración LLM.
9. Modificaciones conversacionales.
10. Derivación humana.
11. Endurecimiento y aceptación.

## Decisiones técnicas iniciales

- Usar SQLite como persistencia local para pedidos confirmados.
- Mantener conversación solo en `st.session_state`.
- Separar dominio de UI desde el inicio.
- Mantener tests unitarios sobre servicios determinísticos.
- Usar LLM solo para interpretación y generación de respuesta natural.
- Usar botones de Streamlit para acciones irreversibles como confirmación.

## Riesgos principales

### Ambigüedad de catálogo

Si el catálogo exportado de Odoo no tiene campos claros de variante, alias o categoría, habrá que normalizar una versión de catálogo para el MVP.

### Interpretación de lenguaje natural

El LLM puede interpretar de más. Por eso los cambios reales al carrito deben pasar por tools validadas y por reglas determinísticas.

### Confirmación accidental

La confirmación debe estar desacoplada del chat. El LLM puede preparar el resumen, pero guardar en SQLite solo debe ocurrir por botón.

### Fechas relativas

Mensajes como "pasado mañana" o "el viernes" requieren una referencia clara a la fecha actual del sistema. La validación final debe ser determinística.

### Evolución a WhatsApp

Streamlit no debe contener lógica crítica. Si la conversación y el dominio quedan separados, WhatsApp podrá reemplazar la UI más adelante.

## Próximo paso recomendado

Empezar por la Etapa 0 y Etapa 1 en una primera iteración corta. Eso deja una app local visible y un catálogo consultable, que es la base necesaria para validar todas las etapas siguientes.
