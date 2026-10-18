# Manual para el DECE

> El sistema **apoya** la orientación vocacional; **no decide** por el estudiante. Sus resultados son un punto de
> partida para la conversación con el estudiante y su familia.

## Quién puede hacer qué

| | Orientación | Administración |
|---|:---:|:---:|
| Ver estudiantes, plano, carreras y cohorte | ✓ | ✓ |
| Generar códigos para el test en línea | ✓ | ✓ |
| Registrar un CHASIDE respondido en papel o anularlo | ✓ | ✓ |
| Cargar notas, nómina y CHASIDE por archivo | | ✓ |
| Editar las reglas de materias | | ✓ |
| Recalibrar el modelo, respaldos, exportar | | ✓ |
| Crear usuarios y ver la bitácora | | ✓ |

## Ciclo de cada año lectivo

1. **Cargar notas** — *Gestión → Cargar datos → Reporte de notas.* Sube el export del sistema académico (el mismo
   formato de `Report_7.csv`). Solo se guardan 9.º a 12.º. Si aparecen *materias sin clasificar*, ve al paso 2.
2. **Revisar materias** — *Gestión → Materias.* Toda materia nueva necesita una regla: a qué áreas aporta y con qué
   peso (1 = poco, 3 = mucho), o si se excluye (conducta, deportes, clubes…). Usa *Probar con un nombre de materia*
   antes de guardar.
3. **Generar códigos** — *Gestión → Estudiantes y códigos* → filtro **Falta CHASIDE** → marcar todos →
   **Generar códigos**. Elige si lo responderán *en el aula* (más confiable) o *en casa*. Imprime las tarjetas o copia
   la lista. **Los códigos solo se muestran una vez.**
4. **Aplicar el test** — Cada estudiante entra a `https://…/chaside`, escribe su código y responde las 98 preguntas
   (unos 10 minutos). Si se corta la conexión, su avance queda guardado en el teléfono.
   - ¿Lo respondió en papel? Abre su ficha → **Tomar el test CHASIDE** y copia las respuestas, o carga un CSV.
5. **Revisar resultados** — Pestaña **Estudiante**: aparecen quienes tienen notas **y** CHASIDE.
6. **Recalibrar** (una vez al año, cuando la mayoría ya respondió) — *Gestión → Modelo → Recalibrar con los datos del
   colegio.* El sistema aprende de su propia cohorte. Necesita al menos 100 estudiantes con notas y CHASIDE para
   aprender todos los parámetros; con menos, ajusta lo que puede y conserva el resto.

## Cómo leer la ficha de un estudiante

**Plano interés × rendimiento.** Cada área es un punto: hacia arriba, cuánto le atrae; hacia la derecha, qué tan bien
le va. La nube alrededor del punto es la **incertidumbre**: más grande = menos evidencia.

| Zona | Significa | Conversación sugerida |
|---|---|---|
| 🟢 Vocación consolidada | Le gusta y le va bien | Confirmar y explorar carreras del área |
| 🟡 Interés a fortalecer | Le gusta, pero aún no le va tan bien | ¿Qué apoyo académico necesita? |
| 🔵 Talento no explorado | Le va bien, aunque no le atrae tanto | ¿Lo conoce de verdad? Mostrar opciones |
| ⚪ Área no prioritaria | Ni le atrae ni destaca | — |
| ▧ Indeterminado | Falta evidencia para decidir | Entrevista u otra prueba |

**Certeza.** La zona solo se asigna si el modelo está al menos 60 % seguro. Es preferible decir "falta evidencia"
que equivocarse.

**Alertas.** Avisan cuando la evidencia es débil: CHASIDE incompleto, respondido sin supervisión, de hace más de un
año, con respuestas poco diferenciadas (posible respuesta al azar), o pocas notas. Ante una alerta crítica, conversar
con el estudiante antes de usar el resultado.

**Carreras.** Afinidad 0–100 = qué tan bien encaja el perfil del estudiante con el de la carrera, comparado con su
curso. **Estabilidad P(top 5)** = en cuántas de 1 000 simulaciones la carrera queda entre las 5 primeras: si es baja,
la recomendación es frágil. El selector **Enfoque** cambia el peso entre interés y rendimiento (50/50 por defecto).

**Autopercepción.** Compara lo que el estudiante cree de sí mismo (aptitudes del CHASIDE) con sus notas: "se percibe
por debajo de sus notas" es una señal para trabajar la confianza.

## Preguntas frecuentes

- **Un estudiante perdió su código.** Genera uno nuevo: el anterior se anula automáticamente.
- **Respondió mal o al azar.** En su ficha → **Repetir el test CHASIDE** (o un código nuevo). La prueba más reciente
  reemplaza a la anterior; si fue un error, **Anular esta prueba** vuelve a la anterior.
- **Los nombres dicen "ficticio".** En la fase de pruebas el sistema inventa nombres. Para ver los reales, la
  administración carga la **nómina** (`id_colegio, nombre, genero, grado_actual, paralelo`).
- **Las preguntas del test son "de prototipo".** Antes del uso real, reemplazar su texto por el oficial del CHASIDE en
  `config/chaside_preguntas.csv` del servidor (manteniendo el número de cada ítem).
- **¿Quién vio la ficha de un estudiante?** *Gestión → Bitácora* (administración).
