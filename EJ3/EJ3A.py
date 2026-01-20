from multiprocessing import Process, Manager
import random
import time
import os

def generar_notas(ruta_fichero, n_notas=6):
    """
    Proceso 1: genera n_notas números aleatorios entre 1 y 10 (decimales)
    y los guarda en ruta_fichero, una nota por línea.
    """
    pid = os.getpid()
    t0 = time.perf_counter()
    with open(ruta_fichero, 'w', encoding='utf-8') as f:
        for _ in range(n_notas):
            nota = round(random.uniform(1.0, 10.0), 2)  # dos decimales
            f.write(f"{nota}\n")
    t1 = time.perf_counter()
    print(f"[P-GEN PID {pid}] Generado {ruta_fichero} en {t1-t0:.6f} s")

def calcular_media_y_apendar(ruta_fichero, nombre_alumno, ruta_medias, lock):
    """
    Proceso 2: lee las notas de ruta_fichero, calcula la media y apenda
    'media nombre_alumno' a ruta_medias. Usa lock (Manager().Lock()) para
    sincronizar la escritura.
    """
    pid = os.getpid()
    t0 = time.perf_counter()
    notas = []
    try:
        with open(ruta_fichero, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    notas.append(float(linea))
                except ValueError:
                    # ignorar líneas no numéricas
                    pass
    except FileNotFoundError:
        print(f"[P-MED PID {pid}] Error: fichero {ruta_fichero} no encontrado.")
        return

    if notas:
        media = sum(notas) / len(notas)
    else:
        media = 0.0

    # Apendar a medias.txt con lock para evitar condiciones de carrera
    with lock:
        with open(ruta_medias, 'a', encoding='utf-8') as fm:
            fm.write(f"{media:.2f} {nombre_alumno}\n")

    t1 = time.perf_counter()
    print(f"[P-MED PID {pid}] Calculada media {media:.2f} para {nombre_alumno} en {t1-t0:.6f} s")

def proceso_maximo_medias(ruta_medias):
    """
    Proceso 3: lee medias.txt y obtiene la nota máxima junto con el alumno.
    Imprime el resultado por pantalla.
    """
    pid = os.getpid()
    t0 = time.perf_counter()
    max_nota = None
    alumno_max = None

    try:
        with open(ruta_medias, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                partes = linea.split(maxsplit=1)
                if len(partes) != 2:
                    continue
                try:
                    nota = float(partes[0])
                except ValueError:
                    continue
                nombre = partes[1]
                if (max_nota is None) or (nota > max_nota):
                    max_nota = nota
                    alumno_max = nombre
    except FileNotFoundError:
        print(f"[P-MAX PID {pid}] Error: {ruta_medias} no encontrado.")
        return

    t1 = time.perf_counter()
    if max_nota is not None:
        print(f"[P-MAX PID {pid}] Nota máxima: {max_nota:.2f} - Alumno: {alumno_max} (tiempo: {t1-t0:.6f} s)")
    else:
        print(f"[P-MAX PID {pid}] No se encontraron medias en {ruta_medias} (tiempo: {t1-t0:.6f} s)")

if __name__ == '__main__':
    random.seed()  # semilla por defecto
    N_ALUMNOS = 10
    ruta_medias = 'medias.txt'

    # Borrar medias.txt si existe para empezar limpio
    try:
        os.remove(ruta_medias)
    except FileNotFoundError:
        pass

    manager = Manager()
    lock = manager.Lock()

    # -------------------------
    # 1) Lanzar 10 procesos generadores (concurrentes) — Proceso 1
    # -------------------------
    procesos_gen = []
    t0_total = time.perf_counter()
    t0_gen = time.perf_counter()
    for i in range(1, N_ALUMNOS + 1):
        ruta = f"Alumno{i}.txt"
        p = Process(target=generar_notas, args=(ruta,))
        procesos_gen.append(p)
        p.start()

    # Esperar a que terminen generadores
    for p in procesos_gen:
        p.join()
    t1_gen = time.perf_counter()
    print(f"\n[Padre] Generación de {N_ALUMNOS} ficheros finalizada. Tiempo generación: {t1_gen - t0_gen:.6f} s\n")

    # -------------------------
    # 2) Lanzar 10 procesos que calculan la media y apendan a medias.txt — Proceso 2
    # -------------------------
    procesos_med = []
    t0_med = time.perf_counter()
    for i in range(1, N_ALUMNOS + 1):
        ruta = f"Alumno{i}.txt"
        nombre = f"Alumno{i}"
        p = Process(target=calcular_media_y_apendar, args=(ruta, nombre, ruta_medias, lock))
        procesos_med.append(p)
        p.start()

    # Esperar a que terminen calculadores
    for p in procesos_med:
        p.join()
    t1_med = time.perf_counter()
    print(f"\n[Padre] Cálculo de medias finalizado. Tiempo cálculo (todos): {t1_med - t0_med:.6f} s\n")

    # -------------------------
    # 3) Lanzar proceso que obtiene la nota máxima — Proceso 3
    # -------------------------
    t0_max = time.perf_counter()
    p_max = Process(target=proceso_maximo_medias, args=(ruta_medias,))
    p_max.start()
    p_max.join()
    t1_max = time.perf_counter()

    t1_total = time.perf_counter()
    print(f"\n[Padre] Tiempo etapa máximo: {t1_max - t0_max:.6f} s")
    print(f"[Padre] Tiempo total (todas las etapas): {t1_total - t0_total:.6f} s")
