# Roadmap: estabilización antes de integrar canales

## Objetivo de salida

Ejecutar un piloto manual de Patty en Streamlit con pedidos confiables,
persistencia, límites conversacionales, derivación humana y trazabilidad
segura. Quedan fuera WhatsApp, web pública, PostgreSQL, tablero, pagos y Odoo
en tiempo real.

## Convención operativa

- Una tarea corresponde a un Issue y un PR; el PR contiene `Closes #<id>`.
- Solo un PR fusionado desbloquea sus dependencias. Una aprobación es
  informativa, no una señal de inicio.
- Las labels reflejan estado cuando la Action de GitHub se ejecute:
  `patty:ready`, `patty:in-progress`, `patty:review-approved`,
  `patty:merged` y `patty:blocked`.
- El siguiente agente toma únicamente la primera tarea marcada `listo`.

## Trabajo fusionado

| ID | Entregable | Issue | PR | Estado | Resultado verificado |
| --- | --- | --- | --- | --- | --- |
| P00 | Tracking, plantillas y Action de PRs | [#6](https://github.com/diego-valdettaro/chatbot-patty/issues/6) | [#14](https://github.com/diego-valdettaro/chatbot-patty/pull/14) | fusionado | Roadmap, plantillas y workflow de sincronización incorporados. |
| P01 | Redacción de PII en observabilidad | [#7](https://github.com/diego-valdettaro/chatbot-patty/issues/7) | [#15](https://github.com/diego-valdettaro/chatbot-patty/pull/15) | fusionado | LangSmith recibe metadatos seguros, sin mensajes, datos de pedido ni argumentos crudos. |
| P02 | Contrato de derivación humana | [#3](https://github.com/diego-valdettaro/chatbot-patty/issues/3) | [#3](https://github.com/diego-valdettaro/chatbot-patty/pull/3) | fusionado | Motivos tipados y transición terminal explícita a `human_handoff`. |
| P03 | Persistencia SQLite y lectura de derivaciones | [#4](https://github.com/diego-valdettaro/chatbot-patty/issues/4) | [#4](https://github.com/diego-valdettaro/chatbot-patty/pull/4) | fusionado | Migración aditiva conserva motivo, fecha y datos de conversación para continuidad. |
| P04 | Servicio de conversación con derivación | [#5](https://github.com/diego-valdettaro/chatbot-patty/issues/5) | [#5](https://github.com/diego-valdettaro/chatbot-patty/pull/5) | fusionado | El servicio persiste la derivación y bloquea la automatización posterior. |
| P05 | Detectar y clasificar derivaciones humanas | [#8](https://github.com/diego-valdettaro/chatbot-patty/issues/8) | [#18](https://github.com/diego-valdettaro/chatbot-patty/pull/18) | fusionado | Política determinista cubre solicitud humana, dos entradas no resueltas, fuera de alcance y error irrecuperable, sin invocar el LLM. |
| P11 | Reconciliar roadmap tras merges iniciales | [#16](https://github.com/diego-valdettaro/chatbot-patty/issues/16) | [#17](https://github.com/diego-valdettaro/chatbot-patty/pull/17) | fusionado | Una sola fuente de verdad: merges, dependencias e Issues pendientes correctos. |

## Backlog ejecutable

| ID | Tarea | Dependencias | Issue | PR | Estado | Criterio de aceptación |
| --- | --- | --- | --- | --- | --- | --- |
| P06 | Integrar derivación humana en Streamlit | P05 | [#9](https://github.com/diego-valdettaro/chatbot-patty/issues/9) | pendiente de enlace | en revisión | UI clara, controles y bot automático bloqueados; mensajes posteriores conservados sin modificar pedido. |
| P07 | Endurecer límites e instrucciones maliciosas | P05 | [#10](https://github.com/diego-valdettaro/chatbot-patty/issues/10) | pendiente de enlace | en revisión | Precios, reglas y confirmación siguen inmutables ante inyección; cobertura automatizada. |
| P08 | Robustecer fallos y estado corrupto | P07 | [#11](https://github.com/diego-valdettaro/chatbot-patty/issues/11) | — | bloqueado | Fallos de LLM, tools, SQLite y JSON corrupto devuelven respuestas seguras sin pérdida silenciosa. |
| P09 | Checklist y piloto de estabilización | P06, P08 | [#12](https://github.com/diego-valdettaro/chatbot-patty/issues/12) | — | bloqueado | Evidencia reproducible del piloto y brechas documentadas contra el PRD. |
| P10 | Validar e incorporar catálogo real | fuente de catálogo real | [#13](https://github.com/diego-valdettaro/chatbot-patty/issues/13) | — | bloqueado externamente | Fuente real recibida, validada y cargada; no iniciar ni hacer pruebas externas hasta contar con ella. |

## Próxima acción

Revisar P06 y P07, ambos en revisión. Tras fusionar P07, P08 queda lista;
P09 requiere además el merge de P06. P10 está explícitamente bloqueada por
la entrega del catálogo real y no depende de un PR técnico.

## Mantenimiento

Al abrir un PR, añadir su URL a la fila correspondiente y cambiar el estado a
`en revisión`. Tras el merge, moverla a **Trabajo fusionado**, anotar la
evidencia y recalcular qué tarea queda `listo`.
