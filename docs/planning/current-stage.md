# Etapa actual - Etapa 2: Carrito y calculo de totales

## Objetivo

Permitir armar y modificar un carrito con calculos deterministas, usando siempre productos y precios del catalogo.

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
- Etapa activa: `Etapa 2 - Carrito y calculo de totales`
- Estado general: `Pendiente de aprobacion de sub-tareas`
- Sub-tarea actual: `Definir y aprobar sub-tareas de Etapa 2`

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

## Sub-tareas propuestas para Etapa 2

- [ ] 2.1 Definir modelo minimo de carrito
- [ ] 2.2 Implementar agregar producto por `product_id`
- [ ] 2.3 Implementar cambio y validacion de cantidades
- [ ] 2.4 Implementar eliminar productos del carrito
- [ ] 2.5 Implementar calculo de subtotal, delivery y total
- [ ] 2.6 Conectar carrito minimo a Streamlit
- [ ] 2.7 Agregar tests de aceptacion de carrito
- [ ] 2.8 Validar Etapa 2 y registrar cierre

## Alcance propuesto para Etapa 2

- Crear una representacion determinista del carrito.
- Agregar productos usando IDs existentes del catalogo.
- Asumir cantidad `1` cuando no se especifique.
- Validar cantidades enteras mayores que cero.
- Cambiar cantidades.
- Eliminar productos.
- Calcular subtotal por producto.
- Calcular subtotal general.
- Calcular delivery fijo.
- Calcular total.
- Mostrar resumen del carrito en Streamlit.

## Fuera de alcance de Etapa 2

- Captura de nombre, telefono, modalidad y fecha.
- Validacion de fecha minima.
- Guardado en SQLite.
- Confirmacion real de pedido.
- LLM o interpretacion conversacional avanzada.
- Procesamiento de pagos.

## Validaciones esperadas para cerrar Etapa 2

- Agregar un producto.
- Agregar dos productos.
- Cambiar una cantidad.
- Rechazar cantidad invalida.
- Eliminar un producto.
- Confirmar que los subtotales cambian correctamente.
- Confirmar que el total usa precios del catalogo, no texto del usuario.
- `pytest` cubre modelo de carrito, operaciones y calculos.

## Notas abiertas

- El delivery fijo se definira en configuracion para poder reutilizarlo en etapas posteriores.
- En Etapa 2 el delivery puede calcularse como valor fijo base, aunque la modalidad delivery/recojo se modele en Etapa 3.
- La UI de carrito seguira siendo de validacion, no la experiencia conversacional final.

## Proxima accion

Esperar aprobacion del usuario sobre la lista de sub-tareas de Etapa 2. Si la lista se aprueba, explicar y pedir aprobacion especifica para ejecutar `2.1 Definir modelo minimo de carrito`.
