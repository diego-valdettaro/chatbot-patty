# Etapa actual - Etapa 4: Persistencia SQLite y confirmacion real

## Objetivo

Guardar pedidos confirmados en SQLite de forma transaccional y bloquear modificaciones posteriores.

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
- Etapa activa: `Etapa 4 - Persistencia SQLite y confirmacion real`
- Estado general: `Pendiente de aprobacion de sub-tareas`
- Sub-tarea actual: `Definir y aprobar sub-tareas de Etapa 4`

## Cierre de Etapa 3

### Sub-tareas completadas

- [x] 3.1 Definir modelo minimo de datos del pedido
- [x] 3.2 Implementar modalidad delivery/recojo
- [x] 3.3 Implementar validacion de datos obligatorios
- [x] 3.4 Implementar validacion de fecha minima
- [x] 3.5 Ajustar delivery segun modalidad
- [x] 3.6 Conectar formulario minimo a Streamlit
- [x] 3.7 Agregar tests de aceptacion de datos del pedido
- [x] 3.8 Validar Etapa 3 y registrar cierre

### Validaciones ejecutadas

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `76 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.
- OK: la app muestra formulario de datos del pedido.
- OK: la app valida nombre, telefono, modalidad, direccion/tienda y fecha.
- OK: el total visible usa delivery S/ 10 para delivery y S/ 0 para recojo.

### Criterios cumplidos

- Intentar delivery sin direccion.
- Intentar recojo sin tienda.
- Usar fecha con menos de dos dias.
- Usar fecha valida.
- Cambiar de delivery a recojo y verificar delivery S/ 0.
- `pytest` cubre datos faltantes, reglas de fecha y modalidad.

### Decisiones cerradas

- Los datos del pedido viven en `src/patty_bot/orders.py`.
- `OrderDetails` modela nombre, telefono, modalidad, fecha, direccion y tienda.
- `validate_order_details` devuelve campos faltantes e invalidos.
- La fecha minima es `fecha actual + 2 dias`.
- Delivery cuesta S/ 10 para delivery y S/ 0 para recojo.
- El formulario de Streamlit es una herramienta de validacion, no la experiencia conversacional final.

## Sub-tareas propuestas para Etapa 4

- [ ] 4.1 Definir schema SQLite minimo
- [ ] 4.2 Implementar inicializacion de base de datos
- [ ] 4.3 Implementar guardado transaccional de pedidos
- [ ] 4.4 Validar que solo se guarden pedidos completos
- [ ] 4.5 Conectar boton de confirmacion a Streamlit
- [ ] 4.6 Bloquear modificaciones despues de confirmar
- [ ] 4.7 Agregar tests de persistencia y confirmacion
- [ ] 4.8 Validar Etapa 4 y registrar cierre

## Alcance propuesto para Etapa 4

- Crear tablas `orders` y `order_items`.
- Guardar pedido confirmado en SQLite.
- Guardar items con snapshot de nombre, precio, cantidad y subtotal.
- Guardar totales calculados.
- Confirmar solo con accion explicita de boton.
- Mostrar exito solo si el guardado termina bien.
- Bloquear cambios despues de confirmar.

## Fuera de alcance de Etapa 4

- Recuperar conversaciones despues de recargar la app.
- Procesamiento de pagos.
- LLM o interpretacion conversacional avanzada.
- Integracion con WhatsApp.

## Validaciones esperadas para cerrar Etapa 4

- Completar un pedido valido y confirmar.
- Ver mensaje de confirmacion.
- Verificar filas en SQLite.
- Confirmar que el carrito queda bloqueado.
- Rechazar guardado de pedidos incompletos.
- `pytest` cubre schema, guardado transaccional y estado inicial.

## Proxima accion

Esperar aprobacion del usuario sobre la lista de sub-tareas de Etapa 4. Si la lista se aprueba, explicar y pedir aprobacion especifica para ejecutar `4.1 Definir schema SQLite minimo`.
