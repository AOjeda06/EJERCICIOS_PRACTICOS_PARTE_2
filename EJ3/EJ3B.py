from multiprocessing import Pool, Process
import random
import time
import os

def generar_notas_pool(args):
    """
    Worker para Pool: genera n_notas y guarda en ruta_fichero.
    args: (ruta_fichero, n_notas)
    """
    ruta_fichero, n_notas = args
    pid = os.getpid()
    t0 = time.perf_counter()
    with open(ruta_fichero, 'w', encoding='utf-8') as f:
        for _ in range(n_notas):
            nota = round(random.uniform(1.0, 10.0), 2)
            f.write(f"{nota}\n")
    t1 = time.perf_counter()
    return (ruta_fichero, t1 - t0, pid)

def calcular_media_pool(args):
    """
    Worker para Pool: lee fichero y devuelve (media, nombre_alumno).
    args: (ruta_fichero, nombre_alumno)
    """
    ruta_fichero, nombre_alumno = args
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
                    pass
    except FileNotFoundError:
        return (0.0, nombre_alumno, 0.0, pid)  # media 0 si no existe

    media = sum(notas) / len(notas) if notas else 0.0
    t1 = time.perf_counter()
    return (media, nombre_alumno, t1 - t0, pid)

def proceso_maximo_medias(ruta_medias):
    """
    Igual que en la versión for: lee medias.txt y muestra la nota máxima.
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
    random.seed()
    N_ALUMNOS = 10
    ruta_medias = 'medias.txt'
    N_NOTAS = 6

    # Empezar limpio
    try:
        os.remove(ruta_medias)
    except FileNotFoundError:
        pass

    # -------------------------
    # 1) Generar ficheros con Pool
    # -------------------------
    t0_total = time.perf_counter()
    t0_gen = time.perf_counter()
    tareas_gen = [(f"Alumno{i}.txt", N_NOTAS) for i in range(1, N_ALUMNOS + 1)]

    with Pool(processes=4) as pool:  # ajustar procesos según CPU
        resultados_gen = pool.map(generar_notas_pool, tareas_gen)

    t1_gen = time.perf_counter()
    print("\n[Padre] Resultados generación (ruta, tiempo, pid):")
    for r in resultados_gen:
        print(f"  {r[0]} (tiempo worker: {r[1]:.6f} s, PID worker: {r[2]})")
    print(f"[Padre] Tiempo generación total: {t1_gen - t0_gen:.6f} s\n")

    # -------------------------
    # 2) Calcular medias con Pool (los workers devuelven resultados al padre)
    # -------------------------
    t0_med = time.perf_counter()
    tareas_med = [(f"Alumno{i}.txt", f"Alumno{i}") for i in range(1, N_ALUMNOS + 1)]

    with Pool(processes=4) as pool:
        resultados_med = pool.map(calcular_media_pool, tareas_med)

    # El padre escribe medias.txt secuencialmente (evita concurrencia)
    with open(ruta_medias, 'w', encoding='utf-8') as fm:
        for media, nombre, dur, pid in resultados_med:
            fm.write(f"{media:.2f} {nombre}\n")

    t1_med = time.perf_counter()
    print("[Padre] Resultados medias (media, alumno, tiempo_worker, pid):")
    for media, nombre, dur, pid in resultados_med:
        print(f"  {nombre}: {media:.2f} (tiempo worker: {dur:.6f} s, PID: {pid})")
    print(f"[Padre] Tiempo cálculo medias total: {t1_med - t0_med:.6f} s\n")

    # -------------------------
    # 3) Proceso que obtiene la nota máxima
    # -------------------------
    t0_max = time.perf_counter()
    p_max = Process(target=proceso_maximo_medias, args=(ruta_medias,))
    p_max.start()
    p_max.join()
    t1_max = time.perf_counter()

    t1_total = time.perf_counter()
    print(f"\n[Padre] Tiempo etapa máximo: {t1_max - t0_max:.6f} s")
    print(f"[Padre] Tiempo total (todas las etapas): {t1_total - t0_total:.6f} s")
