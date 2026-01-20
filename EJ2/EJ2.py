from multiprocessing import Process, Pipe
import random
import time
import os

def generar_ips(n, conn_send):
    """
    Proceso 1: genera n direcciones IPv4 aleatorias y las envía por conn_send.
    Envía None al final como sentinel.
    """
    pid = os.getpid()
    t0 = time.perf_counter()
    enviados = 0

    for _ in range(n):
        # Generar 4 octetos válidos (0-255). Evitamos direcciones especiales 0.x y 255.x en la práctica.
        octetos = [str(random.randint(1, 254)) for _ in range(4)]
        ip = '.'.join(octetos)
        conn_send.send(ip)
        enviados += 1
        # Pequeña pausa opcional para simular trabajo (descomentar si se desea)
        # time.sleep(0.01)

    # Indicar fin de datos
    conn_send.send(None)

    t1 = time.perf_counter()
    dur = t1 - t0
    print(f"[P1 PID {pid}] Generador terminó. IPs enviadas: {enviados}. Tiempo: {dur:.6f} s")
    conn_send.close()


def clase_ip(ip):
    """
    Determina la clase de una dirección IPv4 por su primer octeto.
    Devuelve 'A', 'B', 'C', 'D', 'E' o None si la IP no es válida.
    Reglas simplificadas:
      - A: 1..126
      - B: 128..191
      - C: 192..223
      - D: 224..239 (multicast)
      - E: 240..254 (experimental)
    Nota: 127.x se considera reservada (loopback) y se ignora (devuelve None).
    """
    try:
        primer = int(ip.split('.')[0])
    except Exception:
        return None

    if 1 <= primer <= 126 and primer != 127:
        return 'A'
    if 128 <= primer <= 191:
        return 'B'
    if 192 <= primer <= 223:
        return 'C'
    if 224 <= primer <= 239:
        return 'D'
    if 240 <= primer <= 254:
        return 'E'
    return None


def filtrar_ips(conn_recv, conn_send):
    """
    Proceso 2: recibe IPs por conn_recv, filtra las que son de clase A/B/C
    y las reenvía por conn_send. Recibe sentinel None para terminar y reenvía None.
    """
    pid = os.getpid()
    t0 = time.perf_counter()
    recibidas = 0
    reenviadas = 0

    while True:
        ip = conn_recv.recv()  # bloqueante
        if ip is None:
            break
        recibidas += 1
        cl = clase_ip(ip)
        if cl in ('A', 'B', 'C'):
            conn_send.send((ip, cl))
            reenviadas += 1
        else:
            # Opcional: log de IPs descartadas
            # print(f"[P2 PID {pid}] IP descartada: {ip} (clase {cl})")
            pass

    # Indicar fin al siguiente proceso
    conn_send.send(None)

    t1 = time.perf_counter()
    dur = t1 - t0
    print(f"[P2 PID {pid}] Filtro terminó. Recibidas: {recibidas}. Reenviadas: {reenviadas}. Tiempo: {dur:.6f} s")
    conn_recv.close()
    conn_send.close()


def imprimir_ips(conn_recv):
    """
    Proceso 3: recibe tuplas (ip, clase) por conn_recv hasta recibir None.
    Imprime cada IP y su clase. Mide tiempo y número de impresiones.
    """
    pid = os.getpid()
    t0 = time.perf_counter()
    procesadas = 0

    while True:
        item = conn_recv.recv()
        if item is None:
            break
        ip, cl = item
        procesadas += 1
        # Imprimir desde el proceso consumidor
        print(f"[P3 PID {pid}] {ip} -> Clase {cl}")

    t1 = time.perf_counter()
    dur = t1 - t0
    print(f"[P3 PID {pid}] Imprimir terminó. IPs procesadas: {procesadas}. Tiempo: {dur:.6f} s")
    conn_recv.close()


if __name__ == '__main__':
    # -------------------------
    # Configuración
    # -------------------------
    N_IPS = 10
    # Pipes: P1 -> P2 y P2 -> P3 (unidireccionales)
    recv_p2, send_p1 = Pipe(duplex=False)   # padre usará send_p1 para pasar al proceso P1
    recv_p3, send_p2 = Pipe(duplex=False)

    # Crear procesos (no iniciar aún)
    p1 = Process(target=generar_ips, args=(N_IPS, send_p1))
    p2 = Process(target=filtrar_ips, args=(recv_p2, send_p2))
    p3 = Process(target=imprimir_ips, args=(recv_p3,))

    # Medición de tiempo total en el proceso principal
    t_inicio = time.perf_counter()

    # Iniciar en orden: P1, P2, P3 (aunque pueden ejecutarse concurrentemente)
    # Importante: cerrar en el padre los extremos que no se usan para evitar bloqueos
    p2.start()
    p3.start()
    p1.start()

    # En el proceso padre cerramos los extremos que no vamos a usar:
    # send_p1 ya está en uso por P1, el padre no lo necesita; recv_p2 lo usa P2; recv_p3 lo usa P3
    # cerramos los extremos locales que no se usan en el padre para evitar referencias abiertas
    try:
        send_p1.close()
    except Exception:
        pass
    try:
        recv_p2.close()
    except Exception:
        pass
    try:
        send_p2.close()
    except Exception:
        pass
    try:
        recv_p3.close()
    except Exception:
        pass

    # Esperar a que terminen los procesos
    p1.join()
    p2.join()
    p3.join()

    t_fin = time.perf_counter()
    tiempo_total = t_fin - t_inicio
    print(f"\n[Padre] Todos los procesos han terminado. Tiempo total: {tiempo_total:.6f} s")
