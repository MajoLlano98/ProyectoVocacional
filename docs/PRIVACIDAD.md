# Privacidad y protección de datos

El sistema trata datos de **estudiantes menores de edad** (calificaciones y respuestas a un test vocacional). En
Ecuador aplica la **Ley Orgánica de Protección de Datos Personales (LOPDP)**. Este documento resume cómo el sistema
reduce el riesgo y qué debe definir el colegio. *No es asesoría legal: validar con el área jurídica del colegio.*

## Qué datos guarda y cuáles no

| Dato | ¿Se guarda? | Cómo |
|---|---|---|
| ID del sistema académico | **No** | Solo su HMAC‑SHA256 (no reversible sin el secreto del servidor) |
| Nombre real | Solo si se carga la nómina | En pruebas se usan nombres ficticios |
| Calificaciones | Solo 9.º a 12.º | Lo anterior se descarta al cargar (minimización) |
| Respuestas al CHASIDE | Sí | Cada aplicación, con fecha, modalidad y quién la registró |
| Códigos de acceso | **No** en claro | Solo su HMAC; se muestran una única vez |
| Contraseñas | **No** en claro | Hash scrypt |
| Accesos y cambios | Sí | Bitácora: quién vio, cargó, exportó o cambió |

Los datos viven **solo en el servidor del colegio** (`datos/`), no en servicios de terceros. Cloudflare transporta el
tráfico cifrado pero no almacena la base de datos.

## Lo que debe definir el colegio

1. **Responsable del tratamiento** (el colegio) y **encargado** (quien administre el servidor).
2. **Base legal / consentimiento** de los representantes legales para tratar notas y respuestas con fines de orientación vocacional.
3. **Quién accede:** cuentas personales para cada orientador(a); nunca cuentas compartidas.
4. **Conservación:** por ejemplo, hasta un año después del egreso; luego desactivar/eliminar al estudiante.
5. **Derechos ARCO** (acceso, rectificación, eliminación, oposición): canal para que las familias los ejerzan.
6. **Incidentes:** a quién avisar si se sospecha un acceso indebido (revisar la Bitácora; cambiar contraseñas y el secreto).

## Texto sugerido para el consentimiento (adaptar)

> Autorizo a [COLEGIO] a tratar las calificaciones de secundaria y las respuestas al test vocacional CHASIDE de mi
> representado(a) con la única finalidad de brindarle orientación vocacional a través del DECE. Los datos se guardan
> en un servidor del colegio, con acceso restringido al personal del DECE, se usan de forma seudonimizada para
> mejorar el modelo del propio colegio y se conservarán hasta [PLAZO]. Puedo solicitar su acceso, rectificación o
> eliminación escribiendo a [CORREO].

## Buenas prácticas operativas

- Activar **Cloudflare Access** (ver guía de instalación) como segunda barrera.
- Guardar el archivo `.env` (contiene el secreto) en el gestor de contraseñas del colegio, no en correos ni chats.
- Copiar los respaldos fuera del servidor (`despliegue/respaldo_externo.sh`) y cifrar el destino.
- Revisar la Bitácora mensualmente.
- Las exportaciones CSV contienen datos personales: no enviarlas por correo ni guardarlas en carpetas compartidas.
