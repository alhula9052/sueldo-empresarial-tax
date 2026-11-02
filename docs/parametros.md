# Parámetros auditables

La aplicación inicia sin parámetros normativos. Un revisor debe verificar las fuentes oficiales y conservar el documento, extracto, artículo, fecha de verificación y vigencias. Seleccione esas fuentes al guardar el conjunto de parámetros. Cambie el estado a verificado solo después de contrastar cada campo. Ninguna tasa de esta documentación pretende representar el derecho vigente.

Objeto mínimo válido, todavía incapaz de calcular:

```json
{"apv": {}, "contributions": []}
```

## Esquema

| Ruta | Tipo | Significado |
| --- | --- | --- |
| `uf`, `utm` | cadena decimal opcional | Valor del período y criterio de conversión documentado en la fuente |
| `apv.dependent` | objeto opcional | Solo dependientes |
| `apv.independent` | objeto opcional | Solo independientes; verificar procedencia y límites propios |
| `apv.business` | objeto opcional | Solo receptores de sueldo empresarial; no hereda reglas de dependientes |
| `*.eligibility_verified` | booleano | Procedencia contrastada para esta calidad |
| `*.basis` | texto | Fuente, conversión UF/UTM, condiciones, coordinación y supuestos |
| `*.annual_cap_clp` | cadena decimal | Límite anual convertido conforme al criterio verificado |
| `*.monthly_payroll_cap_clp` | cadena decimal | Tope fijo de referencia; no se reutiliza por defecto |
| `*.monthly_payroll_caps_clp` | objeto mes → cadena decimal | Topes mensuales: claves `1` a `12`. Proporcionar cada mes usado |
| `*.monthly_cap_mode` | texto opcional | Solo `fixed_verified` permite reutilizar un tope constante, cuando se haya verificado que corresponde |
| `*.brackets.annual` / `*.brackets.monthly` | lista de objetos | Tramos del horizonte: `up_to`, `rate`, `deduction` |
| `*.withdrawals` | texto | Tratamiento verificado de retiros anticipados; no se calcula su impuesto |
| `*.coordination.APVC` / `*.coordination.DC` | texto opcional | `consume_cap_only` o `excluded_verified`, únicamente si existe respaldo específico |

Cada tramo usa `up_to` (cadena decimal o `null` en el último), `rate` (cadena decimal de 0 a 1) y `deduction` (cadena decimal CLP). Se calcula `max(0, base × rate − deduction)` y se redondea a CLP entero. Los umbrales deben ser crecientes y cubrir la base completa. Compruebe continuidad y vigencia con la tabla oficial antes de verificar. Las tablas mensuales no sirven automáticamente para un cálculo anual.

No ingrese un número de punto flotante JSON como `0.1`: use una cadena decimal. El simulador no decide elegibilidad leyendo un porcentaje societario. Sin `eligibility_verified`, fundamento, límites, tratamiento de retiros y tramos aplicables, la salida permanece parcial y no informa ahorro.

### Coordinación

APVC y depósitos convenidos no se agregan indiscriminadamente como APV. Si se registran, se exige una decisión de coordinación respaldada por fuentes. `consume_cap_only` reserva parte del límite para ese instrumento y calcula solo la rebaja adicional de APV. `excluded_verified` permite excluirlo del límite únicamente después de verificar su régimen. No estima el beneficio propio de APVC ni depósitos convenidos. La renta de entrada debe reflejar correctamente las rebajas externas ya utilizadas; evite duplicarlas en aportes registrados y campo externo.

## Matriz previsional

`contributions` es una lista de filas. Cada fila exige:

| Campo | Contenido |
| --- | --- |
| `concept` | Uno de los conceptos exactos de la matriz de la aplicación |
| `category` | `dependent`, `independent` o `business`, verificada individualmente |
| `status` | `Obligatorio`, `Voluntario`, `No corresponde` o `Pendiente` |
| `payer` / `cost` | Sujeto obligado / quién soporta el costo |
| `base` | Descripción de la base; `assignment` habilita estimación sobre la asignación registrada |
| `rate` / `cap` | Cadena decimal o `null` si no se ha determinado |
| `payment` | Mecanismo de pago |
| `coverage` | Cobertura |
| `requirements` | Requisitos para prestaciones y demás condiciones |
| `source_id` | ID numérico de una fuente verificada incluida en el conjunto |

Conceptos: `AFP y comisión`, `Salud`, `SIS`, `Seguro de cesantía`, `Accidentes del trabajo y enfermedades profesionales`, `SANNA`, `Nuevos aportes graduales`, `Otras obligaciones`.

Solo se estima importe si la obligación está configurada como obligatoria, con base `assignment`, tasa y tope definidos: `min(asignación, tope) × tasa`. Esta operación no decide por sí misma si esa base legal corresponde. Otros casos muestran la información verificada y dejan el importe pendiente. Un concepto compuesto puede requerir desglose profesional en su descripción; esta versión no liquida nóminas.

Cada conjunto tiene fechas de vigencia. Para tasas graduales, cree intervalos separados y no superpuestos. Si las fuentes faltan, no están verificadas, han expirado o hay conjuntos superpuestos, el motor no selecciona uno arbitrariamente. Los snapshots guardados conservan sus parámetros originales.
