# Guía de instalación en el servidor

Resultado final: la aplicación queda en `https://vocacional.tudominio.com`, con HTTPS de Cloudflare, sin abrir
puertos en el servidor, con respaldo diario y lista para instalarse en el teléfono.

```
Teléfono / computador ──HTTPS──▶ Cloudflare ──túnel cifrado──▶ servidor: cloudflared ──▶ app (Python) ──▶ datos/ (SQLite)
```

## 0. Lo que necesitas

| Qué | Detalle |
|---|---|
| Servidor | Ubuntu 22.04/24.04, 2 GB de RAM, 20 GB de disco (un VPS de USD 5–12/mes alcanza para varios cientos de estudiantes) |
| Dominio | Administrado en Cloudflare (plan gratuito) |
| Acceso | SSH al servidor con un usuario con `sudo` |

## 1. Instalar Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER     # cierra la sesión SSH y vuelve a entrar
docker compose version            # debe mostrar la versión
```

## 2. Copiar el proyecto

Con Git (recomendado):
```bash
git clone https://github.com/TU_USUARIO/vocacional.git
cd vocacional
```
O subiendo el zip: `scp vocacional.zip usuario@servidor:` y luego `unzip vocacional.zip && cd vocacional`.

## 3. Configurar

```bash
cp .env.ejemplo .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"    # copia el resultado
nano .env
```
Completa en `.env`:
- `VOCACIONAL_SECRETO` → el valor generado. **Guárdalo también fuera del servidor** (gestor de contraseñas del colegio):
  sin él, el sistema no reconoce a los estudiantes al cargar nuevos reportes.
- `VOCACIONAL_HOSTS` → tu subdominio, ej. `vocacional.colegio.edu.ec,localhost,127.0.0.1,app`
- `VOCACIONAL_COLEGIO` → nombre del colegio.
- `CLOUDFLARE_TUNNEL_TOKEN` → lo obtienes en el paso 5.

```bash
mkdir -p datos && sudo chown -R 1000:1000 datos && chmod 700 datos
chmod 600 .env
```

## 4. Levantar la aplicación (sin túnel todavía) y crear el primer administrador

```bash
docker compose up -d --build app
docker compose ps                         # app debe quedar "healthy"
docker compose exec app python -m servidor.admin crear-usuario \
    --usuario dece@colegio.edu.ec --nombre "Nombre Apellido" --rol admin
```
Prueba local desde el servidor: `curl http://127.0.0.1:8000/api/salud` → `{"ok":true,...}`

## 5. Publicar con Cloudflare Tunnel

1. En el panel de Cloudflare: **Zero Trust → Networks → Tunnels → Create a tunnel** → tipo *Cloudflared* → nombre `vocacional`.
2. En *Install connector* elige **Docker** y copia solo el token (la cadena larga después de `--token`). Pégalo en `.env` como `CLOUDFLARE_TUNNEL_TOKEN`.
3. En *Public Hostnames* → **Add a public hostname**:
   - Subdomain: `vocacional` · Domain: `tudominio.com`
   - Service: **HTTP** · URL: `app:8000`
4. En el servidor:
   ```bash
   docker compose up -d
   docker compose logs -f tunel        # debe decir "Registered tunnel connection"
   ```
5. Abre `https://vocacional.tudominio.com` → pantalla de ingreso.

### Recomendado: capa extra con Cloudflare Access (gratis hasta 50 usuarios)

Así, antes de ver la pantalla de ingreso, Cloudflare pide un código enviado al correo institucional.
**Zero Trust → Access → Applications → Add → Self-hosted**:
- Application domain: `vocacional.tudominio.com`
- Policy *Allow* → *Emails ending in* `@colegio.edu.ec` (o la lista de correos del DECE).
- **Importante** — agrega una segunda aplicación con política **Bypass / Everyone** para que los estudiantes
  puedan responder el test sin cuenta, con estas rutas:
  `vocacional.tudominio.com/chaside`, `/chaside.js`, `/estilo.css`, `/api/chaside/*`, `/icono*`, `/manifest.json`, `/sw.js`.

## 6. Instalar en el teléfono

- **Android (Chrome):** abrir el sitio → menú ⋮ → *Instalar aplicación*.
- **iPhone (Safari):** abrir el sitio → botón Compartir → *Agregar a pantalla de inicio*.

Los estudiantes pueden hacer lo mismo con `https://vocacional.tudominio.com/chaside`.

## 7. Respaldos

- **Automático:** cada noche a las 02:00 se guarda `datos/respaldos/vocacional_FECHA_diario.db` (+ configuración). Se conservan 30.
- **Fuera del servidor (muy recomendado):** ver `despliegue/respaldo_externo.sh` (copia diaria a otro equipo o a la nube con rclone).
- **Restaurar:**
  ```bash
  docker compose stop app
  cp datos/respaldos/vocacional_XXXX.db datos/vocacional.db
  rm -f datos/vocacional.db-wal datos/vocacional.db-shm
  docker compose start app
  ```

## 8. Actualizar a una nueva versión

```bash
./despliegue/actualizar.sh        # respaldo + git pull + reconstruir + reiniciar
```

## 9. Comandos útiles

| Para | Comando |
|---|---|
| Ver estado | `docker compose ps` |
| Ver registros | `docker compose logs -f app` |
| Crear usuario | `docker compose exec app python -m servidor.admin crear-usuario --usuario X --nombre "Y" --rol orientador` |
| Restablecer contraseña | `docker compose exec app python -m servidor.admin clave --usuario X` |
| Respaldo inmediato | `docker compose exec app python -m servidor.admin respaldo` |
| Reiniciar | `docker compose restart app` |
| Datos de demostración (¡solo en un servidor de pruebas!) | `docker compose exec app python -m servidor.admin demo` |

## Solución de problemas

| Síntoma | Causa probable |
|---|---|
| `Invalid host header` | Falta el dominio en `VOCACIONAL_HOSTS` |
| No se mantiene la sesión | Entrando por `http://` con `VOCACIONAL_COOKIE_SEGURA=true`: usa la dirección `https://` |
| `app` no queda *healthy* | `docker compose logs app`; revisa permisos de `datos/` (`sudo chown -R 1000:1000 datos`) |
| Túnel sin conexión | Token mal copiado en `.env`, o el servicio del hostname no es `http://app:8000` |
