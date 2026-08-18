# Roadmap: estabilización antes de integrar canales

## Objetivo de salida

Poder ejecutar un piloto manual de Patty en Streamlit con pedidos confiables,
persistencia, límites conversacionales, derivación humana y trazabilidad
segura. No incluye WhatsApp, web pública, PostgreSQL, tablero, pagos ni Odoo
en tiempo real.

## Convención operativa

- Cada fila es un único Issue y un único PR; el PR debe contener `Closes #<id>`.
- `ready` significa que todas sus dependencias están fusionadas; `en revisión`
  significa que el PR está abierto; `fusionado` es la única señal que desbloquea
  dependientes.
- Las labels GitHub reflejan el estado: `patty:ready`, `patty:in-progress`,
  `patty:review-approved`, `patty:merged` y `patty:blocked`.
- Un agente toma solo una tarea `ready`, crea su rama y abre un PR borrador.
  No combina tareas ni modifica cambios ajenos.

## Backlog ejecutable

| ID | Tarea | Dependencias | Issue | PR | Estado | Criterio de aceptación |
| --- | --- | --- | --- | --- | --- | --- |
| P00 | Tracking, plantillas y Action de PRs | — | #6 | pendiente | en progreso | Roadmap versionado y labels sincronizadas por review/merge. |
| P01 | Política de datos para observabilidad | — | por crear | — | listo tras crear Issue | LangSmith recibe IDs/categorías y datos redactados, nunca PII. |
| P02 | Modelo de derivación humana | P00 | #3 (fusionado) | #3 | fusionado | Estado irreversible, motivo y fecha forman parte del contrato. |
| P03 | Persistencia SQLite de derivaciones | P02 | #4 (fusionado) | #4 | fusionado | Migración aditiva persiste y recupera motivo/fecha. |
| P04 | Detector determinista de límites | P02, P03 | #5 | pendiente | listo | Solicitud humana, dos mensajes no entendidos, temas fuera de alcance y fallos irrecuperables derivan. |
| P05 | Servicio y UI de derivación | P03, P04 | por crear | — | bloqueado | Streamlit muestra el caso y bloquea agente, tools y edición, preservando mensajes. |
| P06 | Consultas administrativas SQLite | P03 | por crear | — | listo tras crear Issue | Lectura fiable de pedidos y casos derivados, sin tablero. |
| P07 | Protección contra instrucciones maliciosas | P04 | por crear | — | bloqueado | Precios, reglas y confirmación no se alteran desde mensajes. |
| P08 | Pruebas de fallos y corrupción | P05, P06, P07 | por crear | — | bloqueado | LLM, tools, SQLite y estado corrupto fallan de modo seguro. |
| P09 | Checklist y evidencia de piloto | P05, P06, P07, P08 | por crear | — | bloqueado | Checklist ejecutada y resultados registrados; catálogo real confirmado antes de pruebas externas. |

## Orden de ejecución

P00 y P01 pueden desarrollarse en paralelo. P04 comienza después de P03;
P05 necesita P03 y P04. P06 puede avanzar tras P03. P07 necesita P04. P08 y
P09 cierran la integración según sus dependencias. Al empezar una sesión,
revisar este archivo, Issues y PRs abiertos antes de crear trabajo nuevo.

## Cómo se actualiza

- El autor del PR actualiza la fila con su URL al abrirlo.
- La Action `.github/workflows/pr-tracking.yml` refleja aprobación y merge en
  GitHub; no desbloquea trabajo por una mera aprobación.
- Tras cada merge, actualizar esta tabla en el siguiente PR de tracking o de la
  tarea desbloqueada: Issue, PR, estado y criterio validado.
