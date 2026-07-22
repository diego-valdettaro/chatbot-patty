# PRD - Chatbot de pedidos Patty MVP

## 1. Resumen

Construir un chatbot local en español que permita a clientes B2C consultar un catálogo limitado, armar un pedido, elegir delivery o recojo, revisar el resumen y confirmar el pedido.

El MVP se probará mediante una interfaz local en Streamlit. Los pedidos confirmados se almacenarán en una base de datos SQLite.

El chatbot no procesará pagos ni registrará pedidos en Odoo.

## 2. Objetivo

Validar que un chatbot basado en LLM puede:

- Entender pedidos escritos en lenguaje natural.
- Identificar productos y cantidades.
- Resolver ambigüedades de producto o variante.
- Recopilar los datos necesarios para la entrega o recojo.
- Calcular correctamente el total.
- Permitir modificaciones antes de confirmar.
- Guardar pedidos confirmados en una base de datos.
- Derivar la conversación a una persona cuando no pueda resolverla.

## 3. Usuario objetivo

Clientes B2C de Patty que desean realizar un pedido.

### Idioma

El chatbot atenderá únicamente en español.

Si el cliente escribe en otro idioma, se le pedirá continuar en español.

## 4. Canal del MVP

### Incluido

- Aplicación local.
- Interfaz de chat construida con Streamlit.
- Botones para confirmar o modificar el pedido.

### Evolución posterior

La interfaz de Streamlit podrá reemplazarse por WhatsApp sin cambiar la lógica central del chatbot.

## 5. Alcance funcional

El chatbot podrá:

- Mostrar o buscar productos del catálogo.
- Interpretar pedidos escritos en lenguaje natural.
- Procesar varios productos en un mismo mensaje.
- Identificar cantidades.
- Asumir una unidad cuando no se indique cantidad.
- Preguntar cuando falte una variante necesaria.
- Agregar productos al pedido.
- Eliminar productos.
- Cambiar cantidades.
- Cambiar modalidad, fecha, dirección o tienda.
- Calcular subtotal, delivery y total.
- Mostrar un resumen completo.
- Permitir confirmar mediante un botón.
- Guardar el pedido confirmado en SQLite.
- Derivar a atención humana.

## 6. Fuera del alcance

El MVP no incluirá:

- WhatsApp real.
- Registro de pedidos en Odoo.
- Lectura directa de Odoo.
- Google Sheets.
- Procesamiento de pagos.
- Coordinación del pago.
- Disponibilidad real por fecha.
- Control de stock.
- Capacidad de producción.
- Horarios de entrega o recojo.
- Costos de delivery por distrito.
- Notificaciones automáticas al equipo.
- Ingredientes.
- Alérgenos.
- Información nutricional.
- Tamaño, rendimiento o número de porciones.
- Recomendaciones personalizadas.
- Promociones o cupones.
- Clientes B2B.
- Listas de precios múltiples.
- Memoria entre sesiones.
- Modificación de pedidos después de confirmarlos.
- Código de pedido visible para el cliente.

## 7. Catálogo del MVP

El catálogo contendrá una muestra de 30 productos obtenidos del archivo exportado de Odoo.

### Campos del catálogo

Pendiente de definir a partir del archivo exportado de Odoo.

### Reglas

- Solo se ofrecerán productos activos.
- El precio del catálogo será la única fuente válida del precio.
- El chatbot no podrá inventar productos ni precios.
- El chatbot no podrá modificar precios.
- Todos los clientes usarán la misma lista de precios.

## 8. Búsqueda y reconocimiento de productos

El chatbot debe identificar productos utilizando:

- Nombre exacto.
- Alias definidos en el catálogo.
- Coincidencia aproximada por nombre.
- Categoría.
- Sabor o variante cuando esté disponible en el nombre.

### Producto no encontrado

Cuando no exista una coincidencia exacta:

- El chatbot podrá sugerir un máximo de dos alternativas similares.
- Las alternativas deberán existir en el catálogo.
- Si no existe suficiente similitud, deberá indicar que Patty no cuenta con ese producto.

### Ambigüedad

Si una solicitud puede referirse a más de un producto, el chatbot deberá pedir una aclaración.

Ejemplo:

```text
Cliente: Quiero una Red Velvet.

Bot: ¿Deseas la Red Velvet grande o mediana?
```

El producto no se agregará hasta resolver la ambigüedad.

## 9. Cantidades

- El cliente puede pedir varios productos en un mismo mensaje.
- El cliente puede indicar cantidades numéricas o en lenguaje natural.
- Si no especifica cantidad, se asumirá una unidad.
- La cantidad debe ser un número entero mayor que cero.
- Si la cantidad no puede interpretarse, se solicitará aclaración.

Ejemplo:

```text
Cliente: Quiero dos brownies y una torta de zanahoria.

Resultado esperado:
- Brownie: 2 unidades.
- Torta de zanahoria: 1 unidad.
```

## 10. Datos obligatorios

Antes de confirmar, el pedido debe contener:

### Datos generales

- Nombre del cliente.
- Teléfono.
- Al menos un producto.
- Cantidad de cada producto.
- Modalidad.
- Fecha solicitada.

### Delivery

- Dirección de entrega.

### Recojo en tienda

- Tienda seleccionada.

Tiendas disponibles:

- Benavides.
- San Isidro.

## 11. Modalidades

### Delivery

- Tarifa fija: S/ 10.
- Debe solicitarse una dirección.
- No se validará distrito ni cobertura.
- No se validará disponibilidad logística.

### Recojo en tienda

- Sin costo adicional.
- El cliente debe elegir Benavides o San Isidro.
- No se solicitará dirección.

## 12. Fecha del pedido

El cliente solo seleccionará el día de entrega o recojo.

No se seleccionará hora ni franja horaria.

### Regla de anticipación

La fecha debe tener como mínimo dos días de anticipación.

Condición:

```text
fecha solicitada >= fecha actual + 2 días
```

Si la fecha no cumple la regla:

- No se aceptará.
- El chatbot explicará que se necesitan al menos dos días de anticipación.
- Solicitará una nueva fecha.

### Disponibilidad

Toda fecha que cumpla la regla de anticipación se considerará disponible.

No se validará capacidad, stock ni disponibilidad real.

## 13. Carrito y modificaciones

El chatbot mantendrá un pedido en construcción durante la sesión.

El cliente podrá:

- Agregar productos.
- Eliminar productos.
- Cambiar cantidades.
- Cambiar la fecha.
- Cambiar entre delivery y recojo.
- Cambiar dirección.
- Cambiar tienda.

Después de cada modificación relevante:

- El subtotal debe recalcularse.
- El costo de delivery debe recalcularse.
- El total debe recalcularse.
- Debe mostrarse un resumen actualizado cuando corresponda.

## 14. Cálculo del pedido

### Subtotal por producto

```text
precio unitario x cantidad
```

### Subtotal del pedido

Suma de los subtotales de todos los productos.

### Delivery

- Delivery: S/ 10.
- Recojo: S/ 0.

### Total

```text
subtotal + delivery
```

Todos los cálculos deben realizarse mediante código determinístico, no por el LLM.

## 15. Resumen previo a la confirmación

Antes de confirmar, el chatbot debe mostrar:

- Nombre.
- Teléfono.
- Productos.
- Cantidad por producto.
- Precio unitario.
- Subtotal por producto.
- Subtotal general.
- Modalidad.
- Fecha.
- Dirección o tienda.
- Costo de delivery.
- Total.

Ejemplo:

```text
Resumen del pedido
Cliente: Diego
Teléfono: 999 999 999
Productos:
- 1 x Torta de zanahoria grande - S/ 95
- 2 x Brownie de chocolate belga - S/ 16
Modalidad: Delivery
Fecha: 25/07/2026
Dirección: Av. Ejemplo 123
Subtotal: S/ 111
Delivery: S/ 10
Total: S/ 121
```

## 16. Confirmación

La interfaz mostrará dos acciones:

- Modificar pedido.
- Confirmar pedido.

El botón **Confirmar pedido** solo debe estar disponible cuando todos los datos obligatorios sean válidos.

Al confirmar:

- Se guarda el pedido en SQLite.
- Se guardan sus productos asociados.
- El estado inicial será **Pendiente de pago y revisión**.
- El chatbot informa que el pedido fue recibido.
- El chatbot indica que una persona coordinará posteriormente el pago.
- El pedido ya no podrá modificarse desde esa conversación.

Mensaje sugerido:

```text
Tu pedido fue confirmado correctamente. El equipo de Patty lo revisará y se comunicará contigo para coordinar el pago.
```

No se mostrará un código de pedido al cliente.

## 17. Pago

El chatbot no gestionará pagos.

No solicitará:

- Número de tarjeta.
- Comprobante.
- Transferencia.
- Yape o Plin.
- Datos bancarios.

El pago será coordinado posteriormente por una persona.

## 18. Atención humana

El chatbot debe derivar la conversación cuando:

- El cliente solicite hablar con una persona.
- El chatbot no pueda entender la solicitud después de dos intentos.
- Exista un caso fuera del alcance.
- No pueda resolver una ambigüedad.
- Se produzca un error que impida completar el pedido.

Al derivar:

- Informará al cliente.
- Marcará la conversación como **Atención humana requerida**.
- Dejará de responder automáticamente.
- La conversación continuará en el mismo canal cuando se implemente WhatsApp.

Mensaje sugerido:

```text
Voy a derivar tu conversación a una persona del equipo para que pueda ayudarte.
```

En el MVP local, la derivación quedará registrada visualmente en la sesión.

## 19. Horario

El chatbot se considerará disponible las 24 horas.

No se implementarán horarios de atención ni respuestas fuera de horario.

## 20. Persistencia

### Conversación

- La conversación existirá únicamente durante la sesión de Streamlit.
- Al cerrar o recargar la aplicación, se iniciará una nueva conversación.
- No se recuperarán conversaciones anteriores.

### Pedidos

Los pedidos confirmados sí permanecerán almacenados en SQLite.

## 21. Modelo de datos

### Tabla `orders`

Pendiente de definir en implementación.

### Tabla `order_items`

Pendiente de definir en implementación.

### Relación

Un pedido puede contener varios productos.

```text
orders.id -> order_items.order_id
```

## 22. Arquitectura propuesta

```text
Streamlit
  ↓
Servicio de conversación
  ↓
LangChain create_agent
  ↓
Tools
  ├── search_products
  ├── get_product
  ├── update_cart
  ├── validate_order
  └── save_order
  ↓
Catálogo local + SQLite
```

### Responsabilidad del LLM

- Entender el mensaje.
- Detectar intención.
- Extraer productos y cantidades.
- Pedir información faltante.
- Formular respuestas naturales.
- Decidir qué herramienta consultar.

### Responsabilidad del código

- Buscar productos válidos.
- Resolver coincidencias.
- Validar cantidades.
- Validar fechas.
- Calcular precios.
- Calcular delivery.
- Verificar campos obligatorios.
- Guardar pedidos.
- Bloquear modificaciones posteriores.
- Gestionar el estado del pedido.

## 23. Estado mínimo de la sesión

La sesión debe mantener:

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

La información puede mantenerse en `st.session_state`.

No necesita persistirse entre sesiones.

## 24. Tools iniciales

### `search_products`

Busca productos por nombre, alias o similitud.

Entrada:

- Texto de búsqueda.

Salida:

- Coincidencias encontradas.
- Máximo dos sugerencias alternativas.

### `get_product`

Obtiene información de un producto exacto.

Salida:

- ID.
- Nombre.
- Precio.
- Categoría.

### `update_cart`

Agrega, elimina o modifica productos.

El carrito debe validarse mediante código.

### `validate_order`

Comprueba:

- Existencia de productos.
- Cantidades válidas.
- Datos del cliente.
- Modalidad.
- Fecha.
- Dirección o tienda.
- Anticipación mínima.

### `save_order`

Guarda el pedido y sus productos dentro de una transacción SQLite.

Solo puede ejecutarse después de que el cliente pulse **Confirmar pedido**.

## 25. Requisitos no funcionales

### Seguridad

- No almacenar secretos directamente en el código.
- La API key del proveedor LLM debe cargarse mediante variables de entorno.
- No aceptar instrucciones del cliente que intenten modificar precios o reglas.
- No permitir que el LLM escriba consultas SQL arbitrarias.

### Confiabilidad

- Los precios deben provenir siempre del catálogo.
- Los totales deben calcularse mediante código.
- El pedido y sus productos deben guardarse en una única transacción.
- Si el guardado falla, no debe mostrarse una confirmación exitosa.

### Rendimiento

Para una prueba local, la respuesta debería aparecer en pocos segundos bajo condiciones normales.

### Trazabilidad

Durante desarrollo deben registrarse:

- Mensaje del usuario.
- Tool llamada.
- Resultado de la tool.
- Errores.
- Derivaciones.
- Confirmaciones.

## 26. Criterios de aceptación

### Catálogo

- El bot encuentra productos por nombre exacto.
- El bot reconoce alias.
- El bot no muestra productos inactivos.
- El bot no inventa productos.
- El bot no inventa precios.

### Pedido

- Puede procesar varios productos en un mensaje.
- Asume cantidad uno cuando no se indica.
- Pregunta cuando falta una variante.
- Permite modificar el carrito.
- Recalcula correctamente los totales.

### Datos

- Solicita nombre y teléfono.
- Solicita modalidad.
- Para delivery, solicita dirección.
- Para recojo, solicita tienda.
- Solicita fecha.
- Rechaza fechas con menos de dos días de anticipación.

### Confirmación

- Muestra un resumen completo.
- Permite modificar antes de confirmar.
- Solo guarda mediante el botón de confirmación.
- Guarda una fila en `orders`.
- Guarda las líneas correspondientes en `order_items`.
- Muestra un mensaje exitoso únicamente después de guardar.
- El estado inicial es **Pendiente de pago y revisión**.

### Derivación

- Deriva cuando el cliente lo solicita.
- Deriva después de dos intentos fallidos.
- El bot deja de responder automáticamente después de derivar.

## 27. Escenarios mínimos de prueba

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

## 28. Métricas de validación del MVP

Durante las pruebas se deberá medir:

- Porcentaje de pedidos completados sin intervención.
- Porcentaje de productos identificados correctamente.
- Número promedio de aclaraciones por pedido.
- Porcentaje de conversaciones derivadas.
- Errores de cálculo.
- Errores de guardado.
- Tiempo promedio para completar un pedido.
- Casos donde el bot inventó o interpretó incorrectamente información.

## 29. Definición de hecho

El MVP estará terminado cuando:

- La aplicación pueda ejecutarse localmente.
- El catálogo de 30 productos se cargue correctamente.
- El usuario pueda conversar desde Streamlit.
- Se puedan agregar y modificar productos.
- Todas las reglas de fecha y modalidad funcionen.
- Se muestre un resumen correcto.
- El botón de confirmación guarde el pedido.
- Las tablas `orders` y `order_items` mantengan consistencia.
- La derivación a atención humana funcione.
- Los 20 escenarios mínimos hayan sido probados.
- No existan errores conocidos que permitan confirmar un pedido incompleto o con un total incorrecto.
