"""Nombres ficticios estables (mismo algoritmo y listas que el notebook 9.1): mismo ID → mismo nombre."""
import hashlib

NOMBRES_F = ['Camila', 'Valentina', 'Isabella', 'Sofía', 'Daniela', 'Mariana', 'Gabriela', 'Emilia', 'Paula', 'Andrea',
             'Doménica', 'Ariana', 'Nicole', 'Fernanda', 'Melanie', 'Antonella', 'Ana Paula', 'Juliana', 'Renata', 'Victoria',
             'Carolina', 'Alejandra', 'Micaela', 'Dayana', 'Paulina', 'Rafaela', 'Sara', 'Elena', 'Martina', 'Josefina']
NOMBRES_M = ['Mateo', 'Santiago', 'Sebastián', 'Nicolás', 'Martín', 'Daniel', 'Alejandro', 'Joaquín', 'Diego', 'Gabriel',
             'Emilio', 'Juan Pablo', 'Andrés', 'David', 'Samuel', 'Tomás', 'Benjamín', 'Felipe', 'Esteban', 'Leonardo',
             'Carlos', 'José', 'Adrián', 'Ricardo', 'Matías', 'Francisco', 'Pedro', 'Bruno', 'Iván', 'Josué']
APELLIDOS = ['Andrade', 'Vásconez', 'Salazar', 'Cevallos', 'Paredes', 'Guerrero', 'Rivadeneira', 'Zambrano', 'Mora', 'Espinosa',
             'Benítez', 'Villacís', 'Jaramillo', 'Proaño', 'Carrión', 'Ortiz', 'Chávez', 'Molina', 'Rivas', 'Torres',
             'Naranjo', 'Erazo', 'Pazmiño', 'Montalvo', 'Cordero', 'Aguirre', 'Bustamante', 'Calderón', 'Escobar', 'Flores',
             'Herrera', 'León', 'Maldonado', 'Navarrete', 'Ponce', 'Quintana', 'Rosero', 'Suárez', 'Tapia', 'Unda',
             'Valencia', 'Yépez', 'Arias', 'Burbano', 'Coronel', 'Dávila', 'Endara', 'Freire', 'Garcés', 'Hidalgo']


def nombre_ficticio(id_est: str):
    """→ (nombre, genero 'F'|'M')."""
    h = int(hashlib.sha256(id_est.encode()).hexdigest(), 16)
    genero = 'F' if h % 2 else 'M'
    nombres = NOMBRES_F if genero == 'F' else NOMBRES_M
    return f'{nombres[(h >> 8) % len(nombres)]} {APELLIDOS[(h >> 20) % len(APELLIDOS)]} {APELLIDOS[(h >> 40) % len(APELLIDOS)]}', genero
