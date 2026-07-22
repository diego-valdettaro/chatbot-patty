# Etapa actual - Etapa 1: Catalogo local y busqueda deterministica

## Objetivo

Tener un catalogo consultable sin LLM, respetando las reglas de productos activos, precios validos y sugerencias limitadas.

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

- Etapa activa: `Etapa 1 - Catalogo local y busqueda deterministica`
- Estado general: `En progreso`
- Sub-tarea actual: `1.8 Agregar tests de catalogo`

## Sub-tareas

- [x] 1.1 Revisar alcance de catalogo y definir schema minimo
- [x] 1.2 Crear catalogo sample
- [x] 1.3 Implementar modelos de catalogo
- [x] 1.4 Implementar carga del catalogo
- [x] 1.5 Implementar busqueda exacta y por alias
- [x] 1.6 Implementar busqueda aproximada y por categoria
- [x] 1.7 Conectar busqueda minima a Streamlit
- [x] 1.8 Agregar tests de catalogo
- [ ] 1.9 Validar Etapa 1 y registrar cierre

## Detalle aprobado para 1.1

### Alcance

Definir el schema minimo del catalogo MVP y las reglas de normalizacion que usaremos antes de crear `data/catalog.sample.csv`.

### Schema minimo propuesto

El archivo inicial sera CSV para que sea facil de revisar y editar manualmente.

Columnas:

- `id`: identificador interno estable del producto. Texto corto, unico, no vacio.
- `name`: nombre comercial visible para el cliente. Texto, unico entre productos activos.
- `aliases`: alias separados por `|`. Puede estar vacio si no hay alias.
- `category`: categoria comercial simple para busqueda y agrupacion.
- `price`: precio unitario en soles. Numero decimal mayor o igual que cero.
- `active`: bandera booleana para decidir si el bot puede ofrecer el producto.

Ejemplo de fila:

```csv
id,name,aliases,category,price,active
cake-red-velvet-mediana,Red Velvet mediana,red velvet|torta red velvet,Tortas,85.00,true
```

### Reglas de normalizacion

- Todas las busquedas se comparan en minusculas.
- Se ignoran espacios extra al inicio, al final y entre palabras.
- Se ignoran tildes para comparar busquedas, nombres, alias y categorias.
- Los alias se separan con `|`.
- `active` aceptara inicialmente `true` o `false`.
- `price` se parseara como decimal desde el CSV; el LLM nunca podra enviar ni modificar precios.

### Reglas de negocio de catalogo

- Solo productos activos pueden aparecer como resultados ofrecibles.
- El precio del catalogo es la unica fuente valida del precio.
- El bot no puede inventar productos.
- El bot no puede inventar ni modificar precios.
- Las alternativas sugeridas deben existir en el catalogo activo.
- Una busqueda sin coincidencia suficiente debe responder que Patty no cuenta con ese producto.

## Validaciones esperadas para cerrar la etapa

- Buscar un producto por nombre exacto.
- Buscar un producto por alias.
- Buscar un producto con error tipografico leve.
- Buscar un producto por categoria.
- Buscar un producto inexistente con alternativa similar.
- Buscar un producto inexistente sin alternativa.
- Confirmar que productos inactivos no aparecen como ofrecibles.
- Confirmar que nunca se inventan productos ni precios.
- `pytest` cubre carga de catalogo y busqueda.

## Decisiones de la etapa

- El catalogo inicial sera `data/catalog.sample.csv`.
- El formato inicial sera CSV, no SQLite ni JSON, porque el catalogo debe ser facil de revisar durante el MVP.
- El schema minimo queda definido en la sub-tarea 1.1.
- Los precios se modelan con `Decimal`, no con `float`.
- Los modelos de catalogo usan `dataclass(frozen=True)` para mantener objetos simples e inmutables.
- La carga del catalogo usa CSV con `utf-8` y valida columnas requeridas.
- `active` acepta inicialmente solo `true` o `false`.
- La busqueda exacta normaliza minusculas, tildes y espacios.
- La busqueda exacta solo devuelve productos activos.
- Los tipos de match exacto son `exact_name` y `exact_alias`.
- La busqueda general prioriza exacto, luego categoria, luego similitud.
- La similitud devuelve como maximo dos alternativas activas por defecto.
- Los tipos de match nuevos son `category` y `similarity`.
- Streamlit carga `data/catalog.sample.csv` y expone una busqueda visible de catalogo.
- La suite de catalogo incluye tests de aceptacion alineados al PRD.

## Notas abiertas

- Mas adelante, si el export real de Odoo trae columnas distintas, se agregara una capa de adaptacion hacia este schema minimo.
- El catalogo sample contiene 30 productos, incluyendo variantes de Red Velvet, alias, categorias y un producto inactivo.
- Streamlit quedo reiniciado en el puerto `8501` con PID `22132`.
- Pendiente de revision visual por usuario: probar busquedas de catalogo desde el navegador.

## Proxima accion

Esperar aprobacion del usuario para ejecutar la sub-tarea `1.9 Validar Etapa 1 y registrar cierre`.
