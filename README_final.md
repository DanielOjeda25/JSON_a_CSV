# Programa final: ventas e inventario

Este archivo reúne toda la lógica en un único programa ejecutable.

## Cómo ejecutarlo

```bash
python main.py
```

## Qué hace

- lee inventario.json y ventas.json
- aplanar ventas anidadas
- normaliza datos
- valida ventas
- rechaza ventas con errores
- actualiza stock solo para ventas válidas
- genera CSV por vendedor
- genera CSV de ventas rechazadas
- genera resumen por vendedor
- genera inventario_actualizado.json

## Entrada

- inventario.json
- ventas.json

## Salida

- ventas_101.csv
- ventas_202.csv
- ventas_rechazadas.csv
- resumen_vendedores.csv
- inventario_actualizado.json

## Desarrollo guiado

Los pasos previos se hicieron por bloques para entender cada parte del programa.
Este archivo final es el resultado integrado.
