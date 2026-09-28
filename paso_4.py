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

    return {"fecha_actualizacion": inventario.get("fecha_actualizacion"), "productos": productos_normalizados}


def construir_inventario_por_id(inventario):
    inventario_por_id = {}
    for producto in inventario.get("productos", []):
        if isinstance(producto, dict) and producto.get("id") is not None:
            inventario_por_id[int(producto["id"])] = producto
    return inventario_por_id


def construir_vendedores_por_id(ventas):
    vendedores = {}
    for vendedor in ventas.get("vendedores", []):
        if isinstance(vendedor, dict):
            vendedor_id = convertir_entero(vendedor.get("id"))
            if vendedor_id is not None:
                vendedores[vendedor_id] = {
                    "nombre": limpiar_texto(vendedor.get("nombre")),
                    "activo": bool(vendedor.get("activo", False)),
                }
    return vendedores


def validar_venta(venta, inventario_por_id, vendedores_por_id, ids_venta_ya_usados):
    errores = []

    if not isinstance(venta, dict):
        return False, ["La venta no es un diccionario válido"]

    id_venta = convertir_entero(venta.get("id_venta"))
    if id_venta is None:
        errores.append("ID de venta inválido")
    elif id_venta in ids_venta_ya_usados:
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


def ordenar_lista_ventas(ventas, clave, ascendente=True):
    """
    Ordena la lista de ventas por la clave indicada.
    """
    return sorted(ventas, key=lambda v: v.get(clave, ""), reverse=not ascendente)


def exportar_csv_por_vendedor(ventas_vendedor, nombre_archivo, separador):
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

        for venta in ventas_vendedor:
            productos_unicos = set()
            unidades = 0

            for item in venta["items"]:
                producto_id = convertir_entero(item.get("id_producto"))
                cantidad = convertir_entero(item.get("cantidad"))
                if producto_id is not None and cantidad is not None:
                    productos_unicos.add(producto_id)
                    unidades += cantidad

            subtotal, porcentaje, descuento, total = calcular_total_venta(venta, venta["_inventario_por_id"])

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


def exportar_csv_rechazadas(rechazadas, nombre_archivo, separador):
    with open(nombre_archivo, "w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=["id_venta", "fecha", "id_vendedor", "motivo"],
            delimiter=separador,
        )
        writer.writeheader()

        for fila in rechazadas:
            writer.writerow(fila)


def exportar_resumen_vendedores(resumen, nombre_archivo, separador):
    with open(nombre_archivo, "w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=["id_vendedor", "nombre", "cantidad_ventas", "unidades_vendidas", "total_vendido"],
            delimiter=separador,
        )
        writer.writeheader()

        for fila in resumen:
            writer.writerow(fila)


# pruebas rápidas
if __name__ == "__main__":
    inventario = {
        "productos": [
            {"id": 1, "nombre": "Teclado", "categoria": "Periféricos", "precio": "10000", "stock": 10, "activo": True},
            {"id": 2, "nombre": "Mouse", "categoria": "Periféricos", "precio": "20000", "stock": 10, "activo": True},
            {"id": 3, "nombre": "Monitor", "categoria": "Pantallas", "precio": "50000", "stock": 10, "activo": True},
        ]
    }

    inv = construir_inventario_por_id(normalizar_inventario(inventario))
    venta = {"id_venta": 1001, "fecha": "2026-09-01", "id_vendedor": 101, "items": [{"id_producto": 1, "cantidad": 10}]}
    subtotal, porcentaje, descuento, total = calcular_total_venta(venta, inv)
    assert subtotal == 100000.0
    assert porcentaje == 5
    assert round(descuento, 2) == 5000.0
    assert round(total, 2) == 95000.0

    venta_2 = {"id_venta": 1002, "fecha": "2026-09-02", "id_vendedor": 101, "items": [{"id_producto": 2, "cantidad": 2}]}
    assert ordenar_lista_ventas([venta_2, venta], "id_venta", True)[0]["id_venta"] == 1001

    print("Pruebas del paso 4 OK")
