# Build log - Chatbot de pedidos Patty MVP

Este archivo registra el avance real del proyecto para poder retomar el trabajo en una nueva sesion sin perder contexto.

## 2026-07-21 - Sesion 1

### Objetivo

Iniciar el proceso de construccion interactiva, dejar creado el sistema de seguimiento del proyecto y completar la Etapa 0.

### Cambios realizados

- Se convirtio el PRD original a Markdown en `docs/planning/prd.md`.
- Se creo el plan maestro en `docs/planning/implementation-plan.md`.
- Se definio que las sub-tareas se crean justo antes de iniciar cada etapa, no por adelantado.
- Se creo el tablero operativo de la etapa activa en `docs/planning/current-stage.md`.
- Se creo este build log para registrar avances, decisiones, validaciones y proximos pasos.
- Se creo la estructura inicial del proyecto: `src/patty_bot`, `tests`, `data`.
- Se agrego `app.py` con una app Streamlit minima.
- Se agrego `src/patty_bot/config.py` con configuracion base.
- Se agrego `tests/test_smoke.py`.
- Se agrego `pyproject.toml`, `requirements.txt`, `.gitignore` y `README.md`.
- Se instalaron dependencias en `.venv`.

### Decisiones

- `implementation-plan.md` sera el mapa general del proyecto.
- `current-stage.md` sera el tablero operativo de la etapa activa.
- `build-log.md` sera el registro historico de sesiones y decisiones.
- Cada etapa se subdividira solo cuando vaya a empezar.
- Cada etapa debe cerrar con validaciones concretas.
- El proyecto usara layout `src/`.
- La Etapa 0 queda sin LLM, sin catalogo y sin SQLite.
- Pytest correra sin cache provider para evitar warnings de permisos locales.

### Validaciones

- OK: el repo contiene `PRD.docx`, `.venv`, `.git`, `.agents` y `docs`.
- OK: `.venv` existe y usa Python 3.14.6.
- OK: dependencias instaladas con `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `1 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.
- OK: app levantada durante esta sesion con PID `55616`.
- OK: el usuario valido visualmente la app en el navegador, envio un mensaje y vio la respuesta temporal.

### Ajuste de proceso

- El usuario indico que quiere aprobar la ejecucion de cada sub-tarea para poder revisar y aprender durante el proceso.
- A partir de la Etapa 1, el flujo sera:
  - Proponer sub-tareas de la etapa activa.
  - Esperar aprobacion o ajustes del usuario sobre la lista.
  - Antes de ejecutar cada sub-tarea, explicar que se hara y esperar aprobacion explicita.
  - Ejecutar solo la sub-tarea aprobada.
  - Validar, explicar resultados y actualizar `current-stage.md` y `build-log.md`.
- Antes de pedir aprobacion para cada sub-tarea, la explicacion debe incluir:
  - Que se va a hacer.
  - Por que existe la sub-tarea.
  - Que rol cumple en el entregable final.
  - Que queda fuera para no mezclar responsabilidades.
  - Como se va a validar.

### Proximo paso

Iniciar Etapa 1 solo cuando el usuario lo apruebe. Primero se propondran sub-tareas, luego se ejecutaran una por una con aprobacion explicita.

## 2026-07-21 - Sesion 2

### Objetivo

Iniciar la Etapa 1 y ejecutar solo la sub-tarea `1.1 Revisar alcance de catalogo y definir schema minimo`, aprobada por el usuario.

### Cambios realizados

- Se reemplazo `docs/planning/current-stage.md` para activar la Etapa 1.
- Se registraron las sub-tareas propuestas para la Etapa 1.
- Se ejecuto la sub-tarea 1.1 definiendo el schema minimo del catalogo MVP.

### Decisiones

- El catalogo inicial sera un CSV en `data/catalog.sample.csv`.
- El schema minimo tendra columnas: `id`, `name`, `aliases`, `category`, `price`, `active`.
- Los alias se separaran con `|`.
- Las busquedas se normalizaran con minusculas, espacios limpios y sin tildes.
- Solo productos activos podran aparecer como resultados ofrecibles.
- El precio siempre vendra del catalogo; nunca del LLM ni del usuario.

### Validaciones

- OK: sub-tarea 1.1 ejecutada como definicion documental del schema.
- Pendiente: crear catalogo sample en la sub-tarea 1.2.

### Proximo paso

Esperar aprobacion explicita del usuario para ejecutar `1.2 Crear catalogo sample`.

## 2026-07-21 - Sesion 3

### Objetivo

Ejecutar la sub-tarea `1.2 Crear catalogo sample`, aprobada por el usuario.

### Cambios realizados

- Se creo `data/catalog.sample.csv`.
- Se agregaron 30 productos sample.
- Se incluyeron productos activos e inactivos.
- Se incluyeron alias separados por `|`.
- Se incluyeron categorias para busqueda y agrupacion.
- Se incluyeron variantes ambiguas como `Red Velvet mediana` y `Red Velvet grande`.

### Decisiones

- Los precios del catalogo sample son datos fijos de prueba y deberan reemplazarse por el export real de Odoo cuando este disponible.
- Se mantuvo el catalogo como CSV editable manualmente.

### Validaciones

- Pendiente: validar lectura del CSV cuando se implemente la carga en Python.

### Proximo paso

Esperar aprobacion explicita del usuario para ejecutar `1.3 Implementar modelos de catalogo`.

## 2026-07-21 - Sesion 4

### Objetivo

Ejecutar la sub-tarea `1.3 Implementar modelos de catalogo`, aprobada por el usuario.

### Cambios realizados

- Se creo `src/patty_bot/catalog.py`.
- Se agrego el modelo `Product`.
- Se agrego el modelo `CatalogMatch`.
- Se agrego el modelo `CatalogSearchResult`.
- Se agregaron tests en `tests/test_catalog_models.py`.

### Decisiones

- Los precios del catalogo se representan con `Decimal`.
- Los modelos usan `dataclass(frozen=True)` para evitar mutaciones accidentales.
- `CatalogSearchResult` expone helpers simples: `found` y `products`.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `6 passed`.

### Proximo paso

Esperar aprobacion explicita para `1.4 Implementar carga del catalogo`.

## 2026-07-21 - Sesion 5

### Objetivo

Ejecutar la sub-tarea `1.4 Implementar carga del catalogo`, aprobada por el usuario.

### Cambios realizados

- Se agrego `load_catalog` en `src/patty_bot/catalog.py`.
- Se agrego `active_products`.
- Se agregaron validaciones de columnas requeridas.
- Se agrego parseo de aliases separados por `|`.
- Se agrego parseo de `price` como `Decimal`.
- Se agrego parseo estricto de `active` como `true` o `false`.
- Se agrego validacion de IDs duplicados.
- Se agregaron tests de carga en `tests/test_catalog_loading.py`.

### Decisiones

- La carga de catalogo usa la libreria estandar `csv`.
- El CSV se lee como `utf-8`.
- Los errores de fila incluyen el numero de fila para facilitar depuracion.

### Validaciones

- Primer intento de `pytest`: 9 tests pasaron y 4 fallaron por permisos de `tmp_path` en `C:\Users\dvald\AppData\Local\Temp\pytest-of-dvald`.
- Ajuste realizado: los tests que necesitan CSV temporales ahora escriben en `tests/.tmp/`, ignorado por git.
- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `13 passed`.

### Proximo paso

Esperar aprobacion explicita para `1.5 Implementar busqueda exacta y por alias`.

## 2026-07-22 - Sesion 6

### Objetivo

Ejecutar la sub-tarea `1.5 Implementar busqueda exacta y por alias`, aprobada por el usuario.

### Cambios realizados

- Se agrego normalizacion de texto en `src/patty_bot/catalog.py`.
- Se agrego `search_exact_products`.
- La busqueda exacta compara contra `name` y `aliases`.
- La busqueda exacta filtra productos inactivos.
- Se agregaron tests en `tests/test_catalog_exact_search.py`.

### Decisiones

- La normalizacion elimina tildes, convierte a minusculas y colapsa espacios multiples.
- Los resultados exactos usan `match_type` `exact_name` o `exact_alias`.
- La busqueda aproximada y por categoria quedan fuera hasta la sub-tarea 1.6.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `19 passed`.

### Proximo paso

Esperar aprobacion explicita para `1.6 Implementar busqueda aproximada y por categoria`.

## 2026-07-22 - Sesion 7

### Objetivo

Ejecutar la sub-tarea `1.6 Implementar busqueda aproximada y por categoria`, aprobada por el usuario.

### Justificacion

La busqueda exacta solo cubre casos donde el cliente escribe un nombre o alias casi igual al catalogo. Esta sub-tarea permite que el catalogo responda a consultas mas naturales como categorias, errores tipograficos leves o nombres incompletos, sin permitir que el bot invente productos.

### Cambios realizados

- Se agrego `search_products` como funcion general de busqueda.
- Se agrego `search_products_by_category`.
- Se agrego `search_similar_products`.
- Se agrego ranking de similitud con `difflib.SequenceMatcher`.
- Se limito la busqueda por similitud a maximo dos productos por defecto.
- Se agregaron tests en `tests/test_catalog_search.py`.

### Decisiones

- La busqueda general prioriza exacto, luego categoria, luego similitud.
- La categoria puede devolver todos los productos activos de esa categoria.
- El limite de maximo dos aplica a sugerencias por similitud.
- La busqueda aproximada usa solo libreria estandar por ahora.

### Validaciones

- Primer intento de `pytest`: 25 tests pasaron y 1 fallo porque el test esperaba solo un resultado para `chesecake oreo`, pero la busqueda por similitud puede devolver hasta dos alternativas validas.
- Ajuste realizado: el test valida que `cheesecake-oreo` sea el primer resultado y que el total de sugerencias sea como maximo dos.
- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `26 passed`.

### Proximo paso

Esperar aprobacion explicita para `1.7 Conectar busqueda minima a Streamlit`.

## 2026-07-22 - Sesion 8

### Objetivo

Ejecutar juntas las sub-tareas `1.7 Conectar busqueda minima a Streamlit` y `1.8 Agregar tests de catalogo`, aprobadas por el usuario.

### Justificacion

La sub-tarea 1.7 convierte la logica de catalogo en algo visible y probale desde la app, que es necesario para tener un corte vertical tangible. La sub-tarea 1.8 agrega una capa de tests de aceptacion para proteger los comportamientos del PRD antes de avanzar hacia carrito o conversacion.

### Justificacion detallada faltante

#### 1.7 Conectar busqueda minima a Streamlit

- Que se hizo: se conecto la app Streamlit con `load_catalog` y `search_products`, y se agrego una seccion visual para consultar productos.
- Por que existe: hasta ese punto la busqueda solo vivia en tests y funciones Python. Esta sub-tarea convierte la logica en algo que una persona puede usar y revisar en la app.
- Rol en el entregable final: es el primer corte vertical visible del catalogo. Permite validar que la UI puede consumir servicios de dominio antes de sumar carrito, conversacion o LLM.
- Que quedo fuera: carrito, confirmacion, LLM, SQLite y experiencia conversacional real.
- Como se valida: abrir Streamlit y probar busquedas por nombre, alias, categoria, typo leve y producto inexistente.

#### 1.8 Agregar tests de catalogo

- Que se hizo: se agrego una suite de aceptacion de catalogo en `tests/test_catalog_acceptance.py`.
- Por que existe: los tests unitarios cubren piezas pequenas, pero esta sub-tarea verifica comportamientos completos del PRD sobre el catalogo.
- Rol en el entregable final: protege reglas criticas como no ofrecer inactivos, no inventar productos y limitar sugerencias por similitud.
- Que quedo fuera: pruebas de UI, pruebas de carrito, pruebas de persistencia y pruebas con LLM.
- Como se valida: ejecutar `pytest` y confirmar que la suite completa pasa.

### Ajuste de proceso

- El usuario marco que faltaron las justificaciones completas antes de ejecutar 1.7 y 1.8.
- Se registro la regla en `current-stage.md` y `build-log.md` para que sea parte del contexto que debe leerse al retomar.

### Cambios realizados

- Se agrego `CATALOG_SAMPLE_PATH` en `src/patty_bot/config.py`.
- Se conecto `app.py` con `load_catalog` y `search_products`.
- Se agrego una seccion visible de busqueda de catalogo en Streamlit.
- La app muestra producto, categoria, precio, tipo de coincidencia y score.
- Se agrego `tests/test_catalog_acceptance.py`.
- Se agrego `.streamlit/config.toml` para desactivar usage stats y evitar escrituras fuera del workspace.

### Decisiones

- La busqueda de catalogo se muestra como una seccion separada del chat temporal.
- La UI de esta etapa es una herramienta de validacion, no la experiencia final del chatbot.
- Los tests de aceptacion cubren exacto, alias, inactivos, categoria, similitud limitada y producto inexistente.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `32 passed`.
- Parcial: Streamlit responde con HTTP 200, pero el proceso anterior registro un error de permisos al intentar escribir usage stats en `C:\Users\dvald\.streamlit`.
- Ajuste realizado: se agrego configuracion local de Streamlit con `gatherUsageStats = false`.
- OK: se reinicio Streamlit con PID `22132`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501` despues del reinicio.
- OK: el log actual ya no muestra el error de permisos por usage stats.
- Pendiente de revision visual por usuario: probar busquedas desde el navegador.

### Proximo paso

Ejecutar validaciones y luego esperar aprobacion explicita para `1.9 Validar Etapa 1 y registrar cierre`.

## 2026-07-22 - Sesion 9

### Objetivo

Ejecutar la sub-tarea `1.9 Validar Etapa 1 y registrar cierre`, aprobada por el usuario.

### Cambios realizados

- Se valido tecnicamente la Etapa 1.
- Se verifico que Streamlit responde localmente.
- Se cerro la Etapa 1 en `docs/planning/current-stage.md`.
- Se activo la Etapa 2 como siguiente etapa de trabajo.
- Se propuso la lista inicial de sub-tareas para Etapa 2.

### Decisiones

- La Etapa 1 queda cerrada porque cumple los criterios de catalogo local, busqueda deterministica, filtros de activos, precios desde catalogo y sugerencias limitadas.
- La Etapa 2 se enfocara solo en carrito y calculo de totales.
- La captura de datos obligatorios, modalidad y fecha queda fuera hasta Etapa 3.
- La persistencia SQLite queda fuera hasta Etapa 4.
- El LLM queda fuera hasta etapas posteriores.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `32 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.
- OK: el repo ya tenia commit inicial y push a `origin/master` antes de este cierre documental.

### Proximo paso

Esperar aprobacion del usuario sobre las sub-tareas propuestas de Etapa 2. Si se aprueban, explicar y pedir aprobacion especifica para ejecutar `2.1 Definir modelo minimo de carrito`.

## 2026-07-22 - Sesion 10

### Objetivo

Ejecutar la sub-tarea `2.1 Definir modelo minimo de carrito`, aprobada por el usuario.

### Justificacion

Esta sub-tarea crea la base del dominio de carrito antes de implementar operaciones. El carrito debe tener una estructura propia para que agregar, cambiar cantidades, eliminar productos y calcular totales se apoyen en objetos testeables y no en estado de Streamlit.

### Cambios realizados

- Se creo `src/patty_bot/cart.py`.
- Se agrego `CartItem`.
- Se agrego `Cart`.
- `CartItem` referencia un `Product` del catalogo.
- `CartItem` valida que la cantidad sea un entero mayor que cero.
- `CartItem` calcula `line_subtotal` desde `product.price * quantity`.
- `Cart` mantiene items como tupla inmutable.
- `Cart` expone `is_empty`.
- `Cart` expone `subtotal`.
- Se agregaron tests en `tests/test_cart_models.py`.

### Decisiones

- El carrito reutiliza el modelo `Product` para garantizar que precios y nombres vienen del catalogo.
- Los modelos de carrito usan `dataclass(frozen=True)`, siguiendo el patron de catalogo.
- Los calculos monetarios usan `Decimal`.
- Las operaciones de agregar, cambiar cantidad y eliminar quedan separadas para las siguientes sub-tareas.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `39 passed`.

### Proximo paso

Esperar aprobacion explicita para `2.2 Implementar agregar producto por product_id`.

## 2026-07-22 - Sesion 11

### Objetivo

Ejecutar la sub-tarea `2.2 Implementar agregar producto por product_id`, aprobada por el usuario.

### Justificacion

Esta sub-tarea permite que el carrito empiece a modificarse desde una operacion determinista. Agregar por `product_id` evita depender de texto libre o precios enviados por el usuario, y prepara la UI para usar resultados reales del catalogo.

### Cambios realizados

- Se agrego `add_product_to_cart` en `src/patty_bot/cart.py`.
- La funcion busca productos activos por `product_id`.
- Si el carrito esta vacio, agrega una linea con cantidad `1`.
- Si el producto ya existe en el carrito, incrementa su cantidad en una unidad.
- Si el producto no existe o esta inactivo, lanza `ValueError`.
- La funcion devuelve un nuevo `Cart` y no muta el carrito original.
- Se agregaron tests en `tests/test_cart_add_product.py`.

### Decisiones

- Agregar el mismo producto no crea una linea duplicada; incrementa la cantidad existente.
- La busqueda por ID exige productos activos para mantener la misma regla del catalogo ofrecible.
- La cantidad explicita queda fuera hasta `2.3`.
- La conexion con Streamlit queda fuera hasta `2.6`.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `45 passed`.

### Proximo paso

Esperar aprobacion explicita para `2.3 Implementar cambio y validacion de cantidades`.

## 2026-07-22 - Sesion 12

### Objetivo

Ejecutar la sub-tarea `2.3 Implementar cambio y validacion de cantidades`, aprobada por el usuario.

### Justificacion

Esta sub-tarea permite corregir cantidades directamente sin depender de agregar el mismo producto varias veces. Es necesaria para que el pedido sea editable antes de confirmar.

### Alcance ejecutado

- Se agrego `change_cart_item_quantity` en `src/patty_bot/cart.py`.
- La funcion identifica el item por `product_id`.
- La funcion devuelve un nuevo `Cart`.
- La funcion conserva los demas items del carrito.
- La funcion recalcula subtotales a traves de `CartItem` y `Cart`.
- La funcion reutiliza la validacion de cantidad de `CartItem`.
- Se agregaron tests en `tests/test_cart_change_quantity.py`.

### Fuera de alcance

- Eliminar productos del carrito.
- Interpretar cantidad cero como eliminacion.
- Conectar el cambio de cantidad a Streamlit.
- Calcular delivery y total final.
- Guardar pedidos.
- Interpretar texto libre con LLM.

### Decisiones

- Cantidad `0` sigue siendo invalida; eliminar un producto sera una operacion explicita en `2.4`.
- Cambiar cantidad de un producto ausente lanza `ValueError`.
- El carrito original no se muta.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `51 passed`.

### Proximo paso

Esperar aprobacion explicita para `2.4 Implementar eliminar productos del carrito`.

## 2026-07-22 - Sesion 13

### Objetivo

Ejecutar las sub-tareas `2.4` a `2.8`, aprobadas por el usuario.

### Justificacion

El objetivo fue completar el corte vertical de carrito: eliminar productos, calcular totales, mostrarlo en Streamlit, agregar tests de aceptacion y cerrar formalmente la etapa.

### Cambios realizados

#### 2.4 Implementar eliminar productos del carrito

- Se agrego `remove_product_from_cart` en `src/patty_bot/cart.py`.
- La funcion elimina items por `product_id`.
- La funcion devuelve un nuevo `Cart`.
- La funcion rechaza productos que no estan en el carrito.
- Se agregaron tests en `tests/test_cart_remove_product.py`.

#### 2.5 Implementar calculo de subtotal, delivery y total

- `Cart` ya calculaba `subtotal`.
- Se agrego `Cart.delivery_fee`.
- Se agrego `Cart.total`.
- El delivery usa `DELIVERY_FEE` desde `src/patty_bot/config.py`.
- Se agregaron tests en `tests/test_cart_totals.py`.

#### 2.6 Conectar carrito minimo a Streamlit

- Se inicializa `st.session_state.cart`.
- La busqueda de catalogo permite agregar productos al carrito.
- La app muestra items del carrito.
- La app permite cambiar cantidades con un input numerico.
- La app permite quitar productos.
- La app muestra subtotal, delivery y total.

#### 2.7 Agregar tests de aceptacion de carrito

- Se agrego `tests/test_cart_acceptance.py`.
- Se cubrio agregar dos productos.
- Se cubrio cambiar cantidad.
- Se cubrio rechazar cantidad invalida.
- Se cubrio eliminar producto y recalcular subtotal.
- Se cubrio rechazar producto inactivo del catalogo.

#### 2.8 Validar Etapa 2 y registrar cierre

- Se ejecuto la suite completa de tests.
- Se verifico que Streamlit responde localmente.
- Se actualizo `docs/planning/current-stage.md` para cerrar Etapa 2.
- Se dejo propuesta la Etapa 3.

### Decisiones

- Eliminar productos es una operacion explicita; cantidad `0` sigue siendo invalida.
- El delivery en Etapa 2 es fijo para permitir calcular total; la modalidad delivery/recojo se implementara en Etapa 3.
- La UI de carrito en Streamlit es una herramienta de validacion, no la experiencia conversacional final.
- Los tests de aceptacion usan precios reales de `data/catalog.sample.csv`.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `61 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.

### Proximo paso

Esperar aprobacion del usuario sobre las sub-tareas propuestas de Etapa 3. Si se aprueban, explicar y pedir aprobacion especifica para ejecutar `3.1 Definir modelo minimo de datos del pedido`.

## 2026-07-22 - Sesion 14

### Objetivo

Corregir bug visual del carrito detectado por el usuario despues del cierre de Etapa 2.

### Problema

Al agregar varias unidades del mismo producto, el dominio sumaba bien la cantidad, pero el control de cantidad de Streamlit podia volver a escribir `1` en el carrito. El problema ocurria porque `st.number_input` conservaba estado interno con una key fija por producto.

### Cambios realizados

- Se cambio la key del `number_input` de cantidad para incluir la cantidad actual del item.
- Esto fuerza a Streamlit a resincronizar el widget cuando el carrito cambia por agregar o quitar productos.
- Se reemplazo el separador visual de caption de catalogo por ASCII para evitar problemas de codificacion.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `61 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.
- Pendiente: validacion visual manual por usuario en navegador, porque el navegador integrado no estuvo disponible en esta sesion.

## 2026-07-22 - Sesion 15

### Objetivo

Ejecutar completa la Etapa 3: datos obligatorios, modalidad y fecha.

### Comentario de sub-etapas

- `3.1`: se creo el modelo deterministico `OrderDetails`.
- `3.2`: se modelaron modalidades `delivery` y `pickup`.
- `3.3`: se implemento validacion de campos faltantes e invalidos.
- `3.4`: se implemento regla de fecha minima con dos dias de anticipacion.
- `3.5`: se ajusto delivery segun modalidad: S/ 10 para delivery y S/ 0 para recojo.
- `3.6`: se conecto formulario minimo a Streamlit.
- `3.7`: se agregaron tests de aceptacion de pedido.
- `3.8`: se valido, documento y cerro la etapa.

### Cambios realizados

- Se creo `src/patty_bot/orders.py`.
- Se agrego `OrderDetails`.
- Se agrego `OrderValidationResult`.
- Se agrego `validate_order_details`.
- Se agrego `minimum_requested_date`.
- Se agrego `delivery_fee_for_order`.
- Se agrego `total_for_order`.
- Se agregaron tests unitarios en `tests/test_order_details.py`.
- Se agregaron tests de aceptacion en `tests/test_order_acceptance.py`.
- Se conecto a Streamlit un formulario minimo de datos del pedido.
- La app ahora permite capturar nombre, telefono, modalidad, direccion o tienda y fecha solicitada.
- La app muestra faltantes e invalidos.
- La app muestra delivery y total segun modalidad.

### Decisiones

- La fecha minima se calcula como `fecha actual + 2 dias`.
- `delivery` requiere direccion.
- `pickup` requiere tienda permitida.
- Las tiendas permitidas siguen viniendo de `PICKUP_STORES`.
- La confirmacion real y SQLite quedan fuera hasta Etapa 4.
- El formulario actual sigue siendo una herramienta de validacion, no la experiencia final de chatbot.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `76 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.

### Proximo paso

Esperar aprobacion del usuario sobre las sub-tareas propuestas de Etapa 4.

## 2026-07-22 - Sesion 16

### Objetivo

Ejecutar completa la Etapa 4: persistencia SQLite y confirmacion real.

### Comentario de sub-etapas

- `4.1`: se definio schema SQLite minimo con `orders` y `order_items`.
- `4.2`: se implemento inicializacion idempotente de base de datos.
- `4.3`: se implemento guardado transaccional de pedido e items.
- `4.4`: se bloqueo guardado con carrito vacio o datos invalidos.
- `4.5`: se conecto boton explicito de confirmacion en Streamlit.
- `4.6`: se deshabilitaron modificaciones despues de confirmar.
- `4.7`: se agregaron tests de persistencia y confirmacion.
- `4.8`: se valido, documento y cerro la etapa.

### Cambios realizados

- Se agrego `DATABASE_PATH` en `src/patty_bot/config.py`.
- Se creo `src/patty_bot/repository.py`.
- Se agrego `initialize_database`.
- Se agrego `save_confirmed_order`.
- Se agrego estado inicial `Pendiente de pago y revision`.
- Se agrego boton `Confirmar pedido` en Streamlit.
- La confirmacion guarda el pedido en `data/patty.sqlite3`.
- La app bloquea agregar, cambiar cantidad, quitar productos y editar datos despues de confirmar.
- Se agregaron tests en `tests/test_repository.py`.
- Se actualizo `docs/planning/current-stage.md` para cerrar Etapa 4 y proponer Etapa 5.

### Decisiones

- El ID interno del pedido no se muestra al cliente.
- El guardado usa snapshots de producto: ID, nombre, precio unitario, cantidad y subtotal.
- Los valores monetarios se guardan como texto decimal con dos digitos.
- La confirmacion solo ocurre por boton de Streamlit.
- Recuperar pedidos al recargar la app queda fuera de esta etapa.

### Validaciones

- OK: `.\.venv\Scripts\python.exe -m pytest` pasa con `81 passed`.
- OK: Streamlit responde con HTTP 200 en `http://localhost:8501`.

### Proximo paso

Esperar aprobacion del usuario sobre las sub-tareas propuestas de Etapa 5.
