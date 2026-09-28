import json


def cargar_json(ruta):
    """
    Lee un archivo JSON y devuelve su contenido.
    """
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def extraer_ventas_recursivas(objeto):
    """
    Busca ventas dentro de listas y diccionarios anidados.
    Si encuentra un diccionario con 'id_venta', lo agrega a la lista.
    """
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


def construir_inventario_por_id(inventario):
    """
    Crea un diccionario {id_producto: producto}
    para acceder al producto rápido por su ID.
    """
    productos = inventario.get("productos", [])
    inventario_por_id = {}

    for producto in productos:
        if isinstance(producto, dict) and "id" in producto:
            inventario_por_id[int(producto["id"])] = producto

    return inventario_por_id


if __name__ == "__main__":
    inventario = cargar_json("inventario.json")
    ventas_raw = cargar_json("ventas.json")

    ventas_planas = extraer_ventas_recursivas(ventas_raw)
    inventario_por_id = construir_inventario_por_id(inventario)

    print("Ventas encontradas:", len(ventas_planas))
    print("Primer venta:", ventas_planas[0])
    print("Inventario por ID:", inventario_por_id[1])
