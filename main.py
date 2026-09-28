import csv
import json


def limpiar_texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def convertir_entero(valor):
    if valor is None or valor == "":
        return None

    texto = limpiar_texto(valor)
    if texto == "":
        return None

    try:
        if "." in texto or "," in texto:
            return None
        return int(texto)
    except (TypeError, ValueError):
        return None


def convertir_float(valor):
    if valor is None or valor == "":
        return None

    texto = limpiar_texto(valor).replace(",", ".")
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def cargar_json(ruta):
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def extraer_ventas_recursivas(objeto):
    ventas = []

    if isinstance(objeto, dict):
        if "id_venta" in objeto:
            ventas.append(objeto)
        for valor in objeto.values():
            ventas.extend(extraer_ventas_recursivas(valor))

    elif isinstance(objeto, list):
        for elemento in objeto:
            ventas.extend(extraer_ventas_recursivas(elemento))

    return ventas


def normalizar_inventario(inventario):
    productos = inventario.get("productos", [])
    productos_normalizados = []

    for producto in productos:
        if not isinstance(producto, dict):
            continue

        productos_normalizados.append({
            "id": convertir_entero(producto.get("id")),
            "nombre": limpiar_texto(producto.get("nombre")),
            "categoria": limpiar_texto(producto.get("categoria")) or "Sin categoría",
            "precio": convertir_float(producto.get("precio")),
            "stock": convertir_entero(producto.get("stock")),
            "activo": bool(producto.get("activo", True)),
        })

    return {
        "fecha_actualizacion": inventario.get("fecha_actualizacion"),
        "productos": productos_normalizados,
    }


def construir_inventario_por_id(inventario):
    inventario_por_id = {}
    for producto in inventario.get("productos", []):
        if isinstance(producto, dict) and producto.get("id") is not None:
            inventario_por_id[int(producto["id"])] = producto
    return inventario_por_id


def construir_vendedores_por_id(data_ventas):
    vendedores = {}
    for vendedor in data_ventas.get("vendedores", []):
        if isinstance(vendedor, dict):
            vendedor_id = convertir_entero(vendedor.get("id"))
            if vendedor_id is not None:
                vendedores[vendedor_id] = {
                    "nombre": limpiar_texto(vendedor.get("nombre")),
                    "activo": bool(vendedor.get("activo", False)),
                }
    return vendedores


def validar_venta(venta, inventario_por_id, vendedores_por_id, ids_venta_usados):
    errores = []

    if not isinstance(venta, dict):
        return False, ["La venta no es un diccionario válido"]

    id_venta = convertir_entero(venta.get("id_venta"))
    if id_venta is None:
        errores.append("ID de venta inválido")
    elif id_venta in ids_venta_usados:
        errores.append("ID de venta repetido")

    id_vendedor = convertir_entero(venta.get("id_vendedor"))
    if id_vendedor is None:
        errores.append("ID de vendedor inválido")
    elif id_vendedor not in vendedores_por_id:
        errores.append("Vendedor inexistente")
    elif not vendedores_por_id[id_vendedor].get("activo", False):
        errores.append("Vendedor inactivo")

    items = venta.get("items", [])
    if not isinstance(items, list) or len(items) == 0:
        errores.append("Lista de productos vacía")
        return False, errores

    productos_visitados = set()

    for item in items:
        if not isinstance(item, dict):
            errores.append("Item inválido")
            continue

        producto_id = convertir_entero(item.get("id_producto"))
        cantidad = convertir_entero(item.get("cantidad"))

        if producto_id is None:
            errores.append("Producto inexistente o inválido")
            continue

        if producto_id in productos_visitados:
            errores.append(f"Producto {producto_id} repetido dentro de la misma venta")
            continue

        productos_visitados.add(producto_id)

        if producto_id not in inventario_por_id:
            errores.append(f"Producto {producto_id} inexistente")
            continue

        producto = inventario_por_id[producto_id]
        if not producto.get("activo", False):
            errores.append(f"Producto {producto_id} inactivo")
            continue

        if cantidad is None or cantidad <= 0:
            errores.append(f"Cantidad inválida para el producto {producto_id}")
            continue

        if producto.get("stock") is None:
            errores.append(f"Stock no disponible para el producto {producto_id}")
            continue

        if producto["stock"] < cantidad:
            errores.append(f"Stock insuficiente para el producto {producto_id}")

    return (len(errores) == 0), errores


def calcular_total_venta(venta, inventario_por_id):
    subtotal = 0.0

    for item in venta.get("items", []):
        producto_id = convertir_entero(item.get("id_producto"))
        cantidad = convertir_entero(item.get("cantidad"))

        if producto_id is None or cantidad is None:
            continue

        precio = convertir_float(inventario_por_id[producto_id].get("precio"))
        subtotal += precio * cantidad

    if subtotal < 100000:
        porcentaje = 0
        descuento = 0.0
    elif subtotal < 300000:
        porcentaje = 5
        descuento = subtotal * 0.05
    else:
        porcentaje = 10
        descuento = subtotal * 0.10

    total = subtotal - descuento
    return subtotal, porcentaje, descuento, total


def descontar_stock_venta(venta, inventario_por_id):
    for item in venta.get("items", []):
        producto_id = convertir_entero(item.get("id_producto"))
        cantidad = convertir_entero(item.get("cantidad"))

        if producto_id is None or cantidad is None:
            continue

        inventario_por_id[producto_id]["stock"] -= cantidad


def procesar_ventas(data_inventario, data_ventas, separador, clave_orden, ascendente):
    inventario_normalizado = normalizar_inventario(data_inventario)
    inventario_por_id = construir_inventario_por_id(inventario_normalizado)
    vendedores_por_id = construir_vendedores_por_id(data_ventas)

    ventas_planas = extraer_ventas_recursivas(data_ventas)
    ventas_validas = []
    ventas_rechazadas = []
    ids_venta_usados = set()

    for venta in ventas_planas:
        venta_normalizada = {
            "id_venta": convertir_entero(venta.get("id_venta")),
            "fecha": limpiar_texto(venta.get("fecha")),
            "id_vendedor": convertir_entero(venta.get("id_vendedor")),
            "items": []
        }

        for item in venta.get("items", []):
            if not isinstance(item, dict):
                continue
            venta_normalizada["items"].append({
                "id_producto": convertir_entero(item.get("id_producto")),
                "cantidad": convertir_entero(item.get("cantidad")),
            })

        es_valida, errores = validar_venta(venta_normalizada, inventario_por_id, vendedores_por_id, ids_venta_usados)

        if not es_valida:
            ventas_rechazadas.append({
                "id_venta": venta_normalizada.get("id_venta"),
                "fecha": venta_normalizada.get("fecha"),
                "id_vendedor": venta_normalizada.get("id_vendedor"),
                "motivo": "; ".join(errores),
            })
            continue

        id_venta = venta_normalizada["id_venta"]
        ids_venta_usados.add(id_venta)

        subtotal, porcentaje, descuento, total = calcular_total_venta(venta_normalizada, inventario_por_id)
        venta_procesada = {
            "id_venta": id_venta,
            "fecha": venta_normalizada["fecha"],
            "id_vendedor": venta_normalizada["id_vendedor"],
            "items": venta_normalizada["items"],
            "subtotal": subtotal,
            "porcentaje_descuento": porcentaje,
            "descuento": descuento,
            "total": total,
            "_inventario_por_id": inventario_por_id,
        }
        ventas_validas.append(venta_procesada)
        descontar_stock_venta(venta_normalizada, inventario_por_id)

    ventas_validas_ordenadas = ordenar_ventas(ventas_validas, clave_orden, ascendente)

    for vendedor_id in sorted(vendedores_por_id):
        if not vendedores_por_id[vendedor_id].get("activo", False):
            continue
        ventas_del_vendedor = [
            venta for venta in ventas_validas_ordenadas
            if venta["id_vendedor"] == vendedor_id
        ]

        exportar_csv_ventas(vendedor_id, ventas_del_vendedor, separador)

    exportar_csv_rechazadas(ventas_rechazadas, separador)
    exportar_resumen_vendedores(ventas_validas_ordenadas, vendedores_por_id, separador)

    inventario_actualizado = {
        "fecha_actualizacion": inventario_normalizado.get("fecha_actualizacion"),
        "productos": sorted(inventario_normalizado["productos"], key=lambda p: p["id"]),
    }

    with open("inventario_actualizado.json", "w", encoding="utf-8") as archivo:
        json.dump(inventario_actualizado, archivo, ensure_ascii=False, indent=2)

    return ventas_validas_ordenadas, ventas_rechazadas, inventario_actualizado


def ordenar_ventas(ventas, clave, ascendente):
    if clave == "fecha":
        return sorted(ventas, key=lambda venta: venta["fecha"], reverse=not ascendente)
    if clave == "total":
        return sorted(ventas, key=lambda venta: venta["total"], reverse=not ascendente)
    return sorted(ventas, key=lambda venta: venta["id_venta"], reverse=not ascendente)


def exportar_csv_ventas(id_vendedor, ventas, separador):
    nombre_archivo = f"ventas_{id_vendedor}.csv"

    with open(nombre_archivo, "w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=[
                "id_venta",
                "fecha",
                "cantidad_productos",
                "unidades",
                "subtotal",
                "porcentaje_descuento",
                "descuento",
                "total",
            ],
            delimiter=separador,
        )
        writer.writeheader()

        for venta in ventas:
            productos_unicos = set()
            unidades = 0

            for item in venta["items"]:
                producto_id = item.get("id_producto")
                cantidad = item.get("cantidad")
                if producto_id is not None and cantidad is not None:
                    productos_unicos.add(producto_id)
                    unidades += cantidad

            subtotal = venta["subtotal"]
            porcentaje = venta["porcentaje_descuento"]
            descuento = venta["descuento"]
            total = venta["total"]

            writer.writerow({
                "id_venta": venta["id_venta"],
                "fecha": venta["fecha"],
                "cantidad_productos": len(productos_unicos),
                "unidades": unidades,
                "subtotal": round(subtotal, 2),
                "porcentaje_descuento": porcentaje,
                "descuento": round(descuento, 2),
                "total": round(total, 2),
            })


def exportar_csv_rechazadas(ventas_rechazadas, separador):
    with open("ventas_rechazadas.csv", "w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=["id_venta", "fecha", "id_vendedor", "motivo"],
            delimiter=separador,
        )
        writer.writeheader()

        for venta in ventas_rechazadas:
            writer.writerow(venta)


def exportar_resumen_vendedores(ventas_validas, vendedores_por_id, separador):
    resumen = []

    for vendedor_id in sorted(vendedores_por_id):
        if not vendedores_por_id[vendedor_id].get("activo", False):
            continue

        ventas_del_vendedor = [
            venta for venta in ventas_validas
            if venta["id_vendedor"] == vendedor_id
        ]

        cantidad_ventas = len(ventas_del_vendedor)
        unidades_vendidas = 0
        total_vendido = 0.0

        for venta in ventas_del_vendedor:
            for item in venta["items"]:
                unidades_vendidas += item.get("cantidad", 0)
            total_vendido += venta["total"]

        resumen.append({
            "id_vendedor": vendedor_id,
            "nombre": vendedores_por_id[vendedor_id]["nombre"],
            "cantidad_ventas": cantidad_ventas,
            "unidades_vendidas": unidades_vendidas,
            "total_vendido": round(total_vendido, 2),
        })

    with open("resumen_vendedores.csv", "w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=["id_vendedor", "nombre", "cantidad_ventas", "unidades_vendidas", "total_vendido"],
            delimiter=separador,
        )
        writer.writeheader()

        for fila in resumen:
            writer.writerow(fila)


def preguntar_separador():
    while True:
        print("¿Qué separador usar en los CSV?")
        print("1) coma")
        print("2) punto y coma")
        opcion = input("Elige una opción: ").strip()

        if opcion == "1":
            return ","
        if opcion == "2":
            return ";"
        print("Opción inválida. Intenta de nuevo.")


def preguntar_orden():
    while True:
        print("¿Cómo quieres ordenar las ventas de cada vendedor?")
        print("1) por fecha")
        print("2) por total")
        print("3) por ID de venta")
        clave = input("Elige una opción: ").strip()

        if clave == "1":
            campo = "fecha"
            break
        if clave == "2":
            campo = "total"
            break
        if clave == "3":
            campo = "id_venta"
            break
        print("Opción inválida. Intenta de nuevo.")

    while True:
        print("¿En qué orden?")
        print("1) ascendente")
        print("2) descendente")
        orden = input("Elige una opción: ").strip()

        if orden == "1":
            return campo, True
        if orden == "2":
            return campo, False
        print("Opción inválida. Intenta de nuevo.")


def ejecutar_pruebas():
    assert limpiar_texto("  Notebook básica  ") == "Notebook básica"
    assert convertir_entero("15") == 15
    assert convertir_entero("2.5") is None
    assert convertir_float("25000.50") == 25000.5

    inventario = {
        "productos": [
            {"id": 1, "nombre": "Teclado", "categoria": "Periféricos", "precio": "10000", "stock": 10, "activo": True},
            {"id": 2, "nombre": "Mouse", "categoria": "Periféricos", "precio": "20000", "stock": 5, "activo": True},
            {"id": 3, "nombre": "Monitor", "categoria": "Pantallas", "precio": "50000", "stock": 2, "activo": False},
        ]
    }

    inv = construir_inventario_por_id(normalizar_inventario(inventario))
    vendedores = {
        101: {"nombre": "Ana", "activo": True},
        202: {"nombre": "Carlos", "activo": False},
    }

    venta_ok = {"id_venta": 1001, "fecha": "2026-09-01", "id_vendedor": 101, "items": [{"id_producto": 1, "cantidad": 2}]}
    venta_mala = {"id_venta": 1002, "fecha": "2026-09-02", "id_vendedor": 202, "items": [{"id_producto": 3, "cantidad": 1}]}

    assert validar_venta(venta_ok, inv, vendedores, set())[0] is True
    assert validar_venta(venta_mala, inv, vendedores, set())[0] is False

    venta_total = {"id_venta": 1003, "fecha": "2026-09-03", "id_vendedor": 101, "items": [{"id_producto": 1, "cantidad": 10}]}
    subtotal, porcentaje, descuento, total = calcular_total_venta(venta_total, inv)
    assert subtotal == 100000.0
    assert porcentaje == 5
    assert round(descuento, 2) == 5000.0
    assert round(total, 2) == 95000.0

    venta_duplicada = {"id_venta": 1002, "fecha": "2026-09-04", "id_vendedor": 101, "items": [{"id_producto": 2, "cantidad": 1}]}
    assert validar_venta(venta_duplicada, inv, vendedores, {1002})[0] is False

    assert extraer_ventas_recursivas({"ventas": [{"id_venta": 1}, [{"id_venta": 2}]]})[0]["id_venta"] == 1


if __name__ == "__main__":
    try:
        ejecutar_pruebas()
        print("Pruebas OK")

        separador = preguntar_separador()
        clave_orden, ascendente = preguntar_orden()

        inventario_data = cargar_json("inventario.json")
        ventas_data = cargar_json("ventas.json")

        ventas_validas, ventas_rechazadas, inventario_actualizado = procesar_ventas(
            inventario_data,
            ventas_data,
            separador,
            clave_orden,
            ascendente,
        )

        print(f"Ventas válidas: {len(ventas_validas)}")
        print(f"Ventas rechazadas: {len(ventas_rechazadas)}")
        print("Archivos generados: ventas_101.csv, ventas_202.csv, ventas_rechazadas.csv, resumen_vendedores.csv, inventario_actualizado.json")

    except FileNotFoundError as error:
        print(f"No se encontró el archivo: {error}")
    except json.JSONDecodeError as error:
        print(f"El JSON está mal formado: {error}")
    except Exception as error:
        print(f"Error inesperado: {error}")
