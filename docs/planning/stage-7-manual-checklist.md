# Checklist manual — Etapa 7: experiencia centrada en el chat

## Preparación

1. Configura `.env` con las credenciales locales requeridas por el chat.
2. Inicia la aplicación con `./.venv/Scripts/python.exe -m streamlit run app.py`.
3. Abre la URL local que muestre Streamlit y comienza una sesión nueva.

## Casos de validación

| Caso | Acción | Resultado esperado |
| --- | --- | --- |
| Primer contacto | Abrir una sesión sin historial. | El chat ocupa el panel principal y muestra el saludo de Patty; a la derecha aparece `Tu pedido`. |
| Pedido por chat | Pedir un producto disponible, por ejemplo: `Quiero una Red Velvet mediana`. | La respuesta se muestra en el chat y el producto aparece en el carrito lateral con el precio del catálogo. |
| Modificación contextual | Después de añadir un producto, escribir: `agrega dos más`. | La cantidad y los montos del carrito cambian de forma coherente. |
| Datos y resumen | Indicar nombre, teléfono, modalidad, fecha válida y tienda/dirección; pedir el resumen. | El panel lateral refleja los datos y los totales se calculan desde el dominio. |
| Alternativa manual | Abrir `Buscar productos manualmente` y agregar un producto. | El producto se incorpora al mismo carrito que usa el chat. |
| Confirmación protegida | Escribir: `confirma el pedido`. | El chat no confirma ni guarda el pedido; la confirmación solo queda disponible mediante el botón. |
| Bloqueo posterior | Confirmar con el botón y luego intentar editar o enviar un mensaje de cambio. | El pedido permanece confirmado y los controles de modificación quedan bloqueados. |

## Registro del resultado

Para cada caso, anota `OK` o `Incidencia`, el mensaje enviado y una captura si el resultado difiere del esperado. No incluyas credenciales, trazas ni datos personales reales en el registro.
