from multiprocessing import Process, Pipe
import time
import os
import sys

def contar_vocal_pipe(vocal, ruta_fichero, conn_send):
    """
    Proceso que cuenta las apariciones de una vocal en el fichero y envía el resultado.
    Parámetros:
      - vocal: carácter (string) con la vocal a contar (ej. 'a').
      - ruta_fichero: ruta al fichero de texto.
      - conn_send: extremo de la Pipe usado para enviar (send).
    Comportamiento:
      - Abre el fichero en modo lectura (utf-8).
      - Recorre línea a línea y suma las apariciones de la vocal (case-insensitive).
      - Envía una tupla (vocal, conteo, pid, dur_proceso) por conn_send.
      - Cierra su extremo de la Pipe al finalizar.
    """
    pid = os.getpid()
    t0 = time.perf_counter()
    conteo = 0

    try:
        with open(ruta_fichero, 'r', encoding='utf-8') as f:
            for linea in f:
                conteo += linea.lower().count(vocal.lower())
    except FileNotFoundError:
        # señal de error con conteo -1
        conteo = -1

    t1 = time.perf_counter()
    dur = t1 - t0

    # Enviar resultado estructurado al padre
    conn_send.send((vocal, conteo, pid, dur))

    # Cerrar extremo de envío
    conn_send.close()

def crear_fichero_ejemplo(ruta, repeticiones=2000):
    """
    Crea un fichero de ejemplo si no existe para que el script sea autocontenido.
    """
    ejemplo = (
        "Este es un fichero de ejemplo. Contiene varias vocales: "
        "aaaa eeee iiii oooo uuuu. Además algunas palabras en mayúsculas: AEIOU.\n"
        "Multiprocessing permite ejecutar tareas en paralelo y acelerar ciertos trabajos.\n"
    )
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(ejemplo * repeticiones)

if __name__ == '__main__':
    # -------------------------
    # Configuración y fichero
    # -------------------------
    ruta = 'texto.txt'  # fichero a analizar (una sola ruta para todos los procesos)

    # Si no existe, crear fichero de ejemplo (autocontenido)
    if not os.path.exists(ruta):
        print("Fichero de ejemplo no encontrado. Creando 'texto.txt' para pruebas...")
        crear_fichero_ejemplo(ruta, repeticiones=2000)

    vocales = ['a', 'e', 'i', 'o', 'u']

    # Guardaremos pares (conn_recv, proceso) para cada vocal
    conexiones = {}   # vocal -> conn_recv
    procesos = []     # lista de procesos lanzados

    # Medición de tiempo total en el proceso principal (incluye creación, ejecución y join)
    t_inicio_total = time.perf_counter()

    # Crear y arrancar un proceso por cada vocal, con su propia Pipe (unidireccional)
    for v in vocales:
        conn_recv, conn_send = Pipe(duplex=False)
        p = Process(target=contar_vocal_pipe, args=(v, ruta, conn_send))
        procesos.append((v, p, conn_recv))
        p.start()
        # cerrar el extremo de envío en el padre (no lo usará)
        conn_send.close()

    # Esperar a que terminen todos los procesos
    for v, p, conn_recv in procesos:
        p.join()

    # Recoger resultados desde cada Pipe (no bloqueante tras join)
    resultados = {}
    for v, p, conn_recv in procesos:
        # Si el proceso encontró el fichero, recibiremos la tupla; si no, puede lanzar EOFError
        try:
            if conn_recv.poll(timeout=0.5):
                vocal, conteo, pid, dur = conn_recv.recv()
                resultados[vocal] = {'conteo': conteo, 'pid': pid, 'dur': dur}
            else:
                # Si no hay nada en la pipe, marcar como error
                resultados[v] = {'conteo': -1, 'pid': None, 'dur': None}
        except EOFError:
            resultados[v] = {'conteo': -1, 'pid': None, 'dur': None}
        finally:
            conn_recv.close()

    t_fin_total = time.perf_counter()
    tiempo_total = t_fin_total - t_inicio_total

    # Imprimir resultados ordenados por vocal
    print("\nResultados (vocal: conteo) y tiempos por proceso:")
    for v in sorted(resultados.keys()):
        info = resultados[v]
        if info['conteo'] == -1:
            print(f"  {v}: Error leyendo el fichero (PID proceso: {info['pid']})")
        else:
            print(f"  {v}: {info['conteo']} (PID: {info['pid']}, tiempo proceso: {info['dur']:.6f} s)")

    print(f"\nTiempo total de ejecución (proceso principal): {tiempo_total:.6f} s")
