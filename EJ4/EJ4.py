from multiprocessing import Process, Pipe
import time
import os
import sys
from datetime import datetime

def proceso_filtrar_por_anyo(ruta_fichero, anyo_objetivo, conn_send):
    """
    Proceso 1:
      - ruta_fichero: fichero con líneas "Titulo;Año"
      - anyo_objetivo: int con el año a filtrar
      - conn_send: extremo send de la Pipe para enviar películas coincidentes
    Comportamiento:
      - Lee el fichero línea a línea.
      - Para cada línea válida que tenga el formato "titulo;anio" y cuyo año
        coincida con anyo_objetivo, envía la cadena "titulo;anio" por la Pipe.
      - Al finalizar envía None como sentinel y cierra su extremo de la Pipe.
      - Mide y muestra tiempo y número de películas enviadas.
    """
    pid = os.getpid()
    t0 = time.perf_counter()
    enviados = 0
    try:
        with open(ruta_fichero, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                # Separar por ';' y limpiar espacios
                partes = [p.strip() for p in linea.split(';')]
                if len(partes) != 2:
                    # Línea malformada: ignorar
                    # print(f"[P1 PID {pid}] Línea ignorada (formato): {linea!r}")
                    continue
                titulo, anyo_str = partes
                try:
                    anyo = int(anyo_str)
                except ValueError:
                    # Año no numérico: ignorar
                    # print(f"[P1 PID {pid}] Año no válido en línea: {linea!r}")
                    continue
                if anyo == anyo_objetivo:
                    # Enviar la línea tal cual (o solo el título si se prefiere)
                    conn_send.send(f"{titulo};{anyo}")
                    enviados += 1
    except FileNotFoundError:
        print(f"[P1 PID {pid}] Error: fichero no encontrado: {ruta_fichero}")
    except Exception as e:
        print(f"[P1 PID {pid}] Error leyendo fichero: {e}")

    # Enviar sentinel para indicar fin de datos
    try:
        conn_send.send(None)
    except Exception:
        pass

    t1 = time.perf_counter()
    dur = t1 - t0
    print(f"[P1 PID {pid}] Filtrado terminado. Enviadas: {enviados}. Tiempo: {dur:.6f} s")
    conn_send.close()


def proceso_escribir_peliculas(conn_recv, anyo_objetivo):
    """
    Proceso 2:
      - conn_recv: extremo recv de la Pipe para recibir películas (formato "titulo;anio")
      - anyo_objetivo: int con el año (se usa para construir el nombre de fichero)
    Comportamiento:
      - Crea/abre el fichero peliculasXXXX (modo escritura, sobrescribe si existe).
      - Lee de la Pipe hasta recibir None.
      - Por cada película recibida escribe una línea en el fichero (titulo;anio).
      - Mide y muestra tiempo y número de películas escritas.
    """
    pid = os.getpid()
    t0 = time.perf_counter()
    escritas = 0
    nombre_salida = f"peliculas{anyo_objetivo:04d}.txt"
    try:
        with open(nombre_salida, 'w', encoding='utf-8') as fout:
            while True:
                try:
                    item = conn_recv.recv()  # bloqueante
                except EOFError:
                    # Si el otro extremo se cerró inesperadamente
                    break
                if item is None:
                    break
                # item esperado: "titulo;anio"
                fout.write(f"{item}\n")
                escritas += 1
    except Exception as e:
        print(f"[P2 PID {pid}] Error escribiendo fichero {nombre_salida}: {e}")

    t1 = time.perf_counter()
    dur = t1 - t0
    print(f"[P2 PID {pid}] Escritura terminada. Fichero: {nombre_salida}. Escritas: {escritas}. Tiempo: {dur:.6f} s")
    conn_recv.close()


def validar_anyo_input(anyo_str):
    """
    Valida que anyo_str represente un entero menor que el año actual.
    Devuelve int si válido, o None si no lo es.
    """
    try:
        anyo = int(anyo_str)
    except ValueError:
        return None
    año_actual = datetime.now().year
    if anyo >= año_actual:
        return None
    if anyo <= 0:
        return None
    return anyo


if __name__ == '__main__':
    # -------------------------
    # Main: pedir año y ruta al usuario
    # -------------------------
    print("Filtrar películas por año y guardar en fichero peliculasXXXX.txt")
    # Pedir año por teclado y validar
    anyo = None
    while anyo is None:
        entrada = input("Introduce un año (entero, menor que el actual): ").strip()
        anyo = validar_anyo_input(entrada)
        if anyo is None:
            print("Año no válido. Inténtalo de nuevo.")

    # Pedir ruta al fichero de películas
    ruta = input("Introduce la ruta al fichero de películas (formato: Titulo;Año por línea): ").strip()
    if not ruta:
        print("Ruta vacía. Saliendo.")
        sys.exit(1)

    # Comprobar existencia del fichero antes de lanzar procesos (ayuda a detectar errores temprano)
    if not os.path.exists(ruta):
        print(f"Fichero no encontrado: {ruta}. Saliendo.")
        sys.exit(1)

    # -------------------------
    # Crear Pipe y procesos
    # -------------------------
    # Pipe unidireccional: recv para P2, send para P1
    conn_recv, conn_send = Pipe(duplex=False)

    # Crear procesos (no iniciar aún)
    p2 = Process(target=proceso_escribir_peliculas, args=(conn_recv, anyo))
    p1 = Process(target=proceso_filtrar_por_anyo, args=(ruta, anyo, conn_send))

    # Medición de tiempo total en el proceso principal
    t_inicio_total = time.perf_counter()

    # Iniciar P2 primero (estará esperando en recv), luego P1
    p2.start()
    p1.start()

    # En el proceso padre cerramos los extremos que no usamos para evitar referencias abiertas
    try:
        conn_send.close()
    except Exception:
        pass
    try:
        conn_recv.close()
    except Exception:
        pass

    # Esperar a que terminen ambos procesos
    p1.join()
    p2.join()

    t_fin_total = time.perf_counter()
    tiempo_total = t_fin_total - t_inicio_total
    print(f"\n[Padre] Ambos procesos han terminado. Tiempo total: {tiempo_total:.6f} s")
