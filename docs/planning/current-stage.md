# Etapa actual - Etapa 3: Datos obligatorios, modalidad y fecha

## Objetivo

Validar los datos necesarios para confirmar un pedido antes de introducir guardado o LLM.

## Principio de trabajo

Cada sub-tarea requiere aprobacion explicita del usuario antes de ejecutarse.

Las sub-tareas de etapas futuras se definiran recien al iniciar cada etapa.

Antes de pedir aprobacion para una sub-tarea, siempre se debe explicar:

- Que se va a hacer.
- Por que existe la sub-tarea.
- Que rol cumple en el entregable final.
- Que queda fuera para no mezclar responsabilidades.
- Como se va a validar.

## Estado

- Etapa anterior: `Etapa 1 - Catalogo local y busqueda deterministica`
- Estado Etapa 1: `Cerrada`
- Estado Etapa 2: `Cerrada`
- Etapa activa: `Etapa 3 - Datos obligatorios, modalidad y fecha`
- Estado general: `Pendiente de aprobacion de sub-tareas`
- Sub-tarea actual: `Definir y aprobar sub-tareas de Etapa 3`

## Cierre de Etapa 1

### Validaciones ejecutadas

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `32 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.
- OK: la app carga busqueda de catalogo desde `data/catalog.sample.csv`.
- OK: los tests cubren carga de catalogo, modelos, busqueda exacta, alias, categoria, similitud, productos inactivos y escenarios de aceptacion.

### Criterios cumplidos

- Buscar un producto por nombre exacto.
- Buscar un producto por alias.
- Buscar un producto con error tipografico leve.
- Buscar un producto por categoria.
- Buscar un producto inexistente con alternativa similar.
- Buscar un producto inexistente sin alternativa.
- Confirmar que productos inactivos no aparecen como ofrecibles.
- Confirmar que nunca se inventan productos ni precios.
- `pytest` cubre carga de catalogo y busqueda.

### Decisiones cerradas

- El catalogo inicial es `data/catalog.sample.csv`.
- El formato inicial es CSV, no SQLite ni JSON.
- Los precios se modelan con `Decimal`.
- Solo productos activos pueden aparecer como ofrecibles.
- La busqueda general prioriza exacto, luego categoria, luego similitud.
- La similitud devuelve como maximo dos alternativas activas por defecto.
- Streamlit expone una busqueda visible de catalogo como herramienta de validacion.

## Sub-tareas de Etapa 2

- [x] 2.1 Definir modelo minimo de carrito
- [x] 2.2 Implementar agregar producto por `product_id`
- [x] 2.3 Implementar cambio y validacion de cantidades
- [x] 2.4 Implementar eliminar productos del carrito
- [x] 2.5 Implementar calculo de subtotal, delivery y total
- [x] 2.6 Conectar carrito minimo a Streamlit
- [x] 2.7 Agregar tests de aceptacion de carrito
- [x] 2.8 Validar Etapa 2 y registrar cierre

## Cierre de Etapa 2

### Validaciones ejecutadas

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `61 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.
- OK: la app permite buscar productos y agregarlos al carrito.
- OK: la app muestra items del carrito, cantidades, subtotales, delivery y total.
- OK: los tests cubren modelo de carrito, agregar producto, cambiar cantidad, eliminar producto, totales y escenarios de aceptacion.

### Criterios cumplidos

- Agregar un producto.
- Agregar dos productos.
- Cambiar una cantidad.
- Rechazar cantidad invalida.
- Eliminar un producto.
- Confirmar que los subtotales cambian correctamente.
- Confirmar que el total usa precios del catalogo, no texto del usuario.
- `pytest` cubre modelo de carrito, operaciones y calculos.

### Decisiones cerradas

- El carrito vive en `src/patty_bot/cart.py`.
- Los modelos de carrito usan `dataclass(frozen=True)`.
- El carrito reutiliza `Product` para mantener precios desde catalogo.
- Agregar un producto repetido incrementa la cantidad existente.
- Cambiar cantidad exige entero mayor que cero.
- Eliminar producto es una operacion explicita; cantidad `0` sigue siendo invalida.
- El delivery fijo se expone como `Cart.delivery_fee`.
- El total se calcula como `subtotal + delivery_fee`.
- La UI de Streamlit de Etapa 2 es una herramienta de validacion, no la conversacion final.

## Sub-tareas propuestas para Etapa 3

- [ ] 3.1 Definir modelo minimo de datos del pedido
- [ ] 3.2 Implementar modalidad delivery/recojo
- [ ] 3.3 Implementar validacion de datos obligatorios
- [ ] 3.4 Implementar validacion de fecha minima
- [ ] 3.5 Ajustar delivery segun modalidad
- [ ] 3.6 Conectar formulario minimo a Streamlit
- [ ] 3.7 Agregar tests de aceptacion de datos del pedido
- [ ] 3.8 Validar Etapa 3 y registrar cierre

## Alcance propuesto para Etapa 3

- Capturar nombre y telefono.
- Capturar modalidad: delivery o recojo.
- Para delivery, capturar direccion.
- Para recojo, capturar tienda permitida.
- Capturar fecha solicitada.
- Validar fecha solicitada con al menos dos dias de anticipacion.
- Calcular delivery segun modalidad.
- Mostrar campos faltantes o invalidos.

## Fuera de alcance de Etapa 3

- Guardado en SQLite.
- Confirmacion real de pedido.
- LLM o interpretacion conversacional avanzada.
- Procesamiento de pagos.

## Validaciones esperadas para cerrar Etapa 3

- Intentar confirmar sin nombre.
- Intentar delivery sin direccion.
- Intentar recojo sin tienda.
- Usar fecha con menos de dos dias.
- Usar fecha valida.
- Cambiar de delivery a recojo y verificar delivery S/ 0.
- `pytest` cubre datos faltantes, reglas de fecha y modalidad.

## Notas abiertas

- El modelo inicial de carrito vive en `src/patty_bot/cart.py`.
- `CartItem` valida cantidad entera mayor que cero y calcula subtotal de linea desde el precio del catalogo.
- `Cart` expone `is_empty` y `subtotal`.
- `add_product_to_cart` agrega productos activos por `product_id` desde el catalogo.
- Agregar un producto ya existente incrementa su cantidad en una unidad.
- Los productos inactivos o inexistentes se rechazan.
- `change_cart_item_quantity` cambia la cantidad de un producto existente por `product_id`.
- Cambiar cantidad reutiliza la validacion de `CartItem`: entero mayor que cero.
- Un producto ausente en el carrito se rechaza al cambiar cantidad.
- `remove_product_from_cart` elimina productos por `product_id`.
- `Cart` expone `delivery_fee` y `total`.
- En Etapa 2 el delivery es fijo; la modalidad delivery/recojo se modelara en Etapa 3.

## Proxima accion

Esperar aprobacion del usuario sobre la lista de sub-tareas de Etapa 3. Si la lista se aprueba, explicar y pedir aprobacion especifica para ejecutar `3.1 Definir modelo minimo de datos del pedido`.
