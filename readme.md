# Guía de Despliegue: Django en AWS EC2 con GitHub Actions

> **Contexto:** Esta guía cubre el despliegue de una aplicación Django en una instancia EC2 de AWS, usando Nginx como servidor web, Gunicorn como servidor WSGI, y GitHub Actions para automatizar el proceso de CI/CD cada vez que se hace push a `main`.



## Arquitectura General

```
Internet
   │
   ▼
[GitHub Actions]
   │  SCP (copia archivos)
   │  SSH (ejecuta comandos)
   ▼
[EC2 – Amazon Linux]
   │
   ├── Nginx (puerto 80) ──► proxy inverso
   │       │
   │       ▼
   ├── Gunicorn (socket Unix) ──► servidor WSGI
   │       │
   │       ▼
   └── Django App ──► Base de datos
```

**¿Por qué esta arquitectura?**

- **Nginx** maneja las conexiones entrantes, sirve archivos estáticos de forma eficiente y actúa como proxy hacia Gunicorn.
- **Gunicorn** es el servidor que "habla" con Django a través del estándar WSGI, permitiendo múltiples workers concurrentes.
- **GitHub Actions** automatiza el despliegue: cada push a `main` copia el código al servidor y reinicia los servicios.

---

## Requisitos Previos

- Cuenta de AWS con una instancia EC2 corriendo **Amazon Linux 2023**
- Par de llaves `.pem` descargado para conectarte por SSH
- Repositorio en GitHub con tu proyecto Django
- Python 3.11 y un `requirements.txt` en tu proyecto

---

## Paso 1 – Configuración de la VPC y EC2

En la consola de AWS, crea o usa una VPC con una subred pública. Al lanzar tu instancia EC2, asegúrate de:

- Asociarla a la VPC creada
- Habilitar la asignación de IP pública
- Configurar el **Security Group** para permitir:
  - Puerto **22** (SSH) – para administración
  - Puerto **80** (HTTP) – para el tráfico web

---

## Paso 2 – Configurar permisos de la llave SSH

Al descargar el archivo `.pem` desde AWS, Windows no restringe sus permisos automáticamente. SSH rechazará la llave si otros usuarios pueden leerla, por lo que debes corregir esto manualmente.

Ejecuta los siguientes comandos en **PowerShell** o **CMD** (reemplaza `llave.pem` con el nombre de tu archivo):

```cmd
# Elimina los permisos heredados de la carpeta que contiene el archivo
icacls "llave.pem" /inheritance:r

# Otorga acceso de solo lectura únicamente a tu usuario actual
icacls "llave.pem" /grant:r "%USERNAME%":R
```

Ahora puedes conectarte al servidor con:

```bash
ssh -i "llave.pem" ec2-user@<IP_DE_TU_EC2>
```

---

## Paso 3 – Instalar dependencias en el servidor

Una vez conectado por SSH, actualiza el sistema e instala los paquetes necesarios:

```bash
# Actualiza todos los paquetes del sistema operativo
sudo dnf update -y && sudo dnf upgrade -y

# Instala Python, pip, herramientas de compilación, PostgreSQL dev y Nginx
sudo dnf install python3 python3-pip python3-devel postgresql-devel nginx gcc -y
```

**¿Por qué estos paquetes?**
- `python3-devel` y `gcc` son necesarios para compilar dependencias de Python que tienen extensiones en C.
- `postgresql-devel` es necesario si tu app usa PostgreSQL (psycopg2 lo requiere para compilarse).
- `nginx` es el servidor web que usaremos como proxy.

Luego, crea el directorio donde vivirá tu proyecto y agrega Nginx al grupo de tu usuario para que pueda acceder al socket:

```bash
# Crea el directorio del proyecto
mkdir -p /home/ec2-user/ot

# Permite que el proceso de Nginx acceda a los archivos del usuario ec2-user
sudo usermod -a -G ec2-user nginx

# Permite al grupo nginx "cruzar" tu carpeta home
sudo chmod 710 /home/ec2-user

# Permite leer y cruzar la carpeta de tu proyecto
sudo chmod 750 /home/ec2-user/ot
```

---

## Paso 4 – Configurar Gunicorn como servicio

Gunicorn necesita correr como un proceso del sistema que se inicie automáticamente. Para eso, usamos **systemd**, el gestor de servicios de Linux.

Crea el archivo de configuración del servicio:

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Pega el siguiente contenido:

```ini
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=ec2-user
Group=nginx
WorkingDirectory=/home/ec2-user/ot
ExecStart=/home/ec2-user/ot/venv/bin/gunicorn \
    --access-logfile - \
    --workers 3 \
    --bind unix:/home/ec2-user/ot/ot.sock \
    saas_ot.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Explicación de las opciones de Gunicorn:**
- `--workers 3`: lanza 3 procesos paralelos para atender peticiones. Una regla común es `(2 × núcleos_CPU) + 1`.
- `--bind unix:/...ot.sock`: en lugar de un puerto TCP, usa un socket Unix, que es más rápido para comunicación interna.
- `saas_ot.wsgi:application`: apunta al módulo WSGI de tu proyecto Django (reemplaza `saas_ot` con el nombre de tu proyecto).

Activa e inicia el servicio:

```bash
# Inicia Gunicorn ahora
sudo systemctl start gunicorn

# Hace que Gunicorn se inicie automáticamente al reiniciar el servidor
sudo systemctl enable gunicorn
```

Verifica que esté corriendo:

```bash
sudo systemctl status gunicorn
```

---

## Paso 5 – Configurar Nginx como proxy inverso

Nginx recibirá las peticiones HTTP del exterior y las redirigirá a Gunicorn a través del socket Unix.

Crea el archivo de configuración:

```bash
sudo nano /etc/nginx/conf.d/ot.conf
```

Pega el siguiente bloque:

```nginx
server {
    listen 80;
    server_name IP_DE_TU_EC2;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        root /home/ec2-user/ot;
    }
    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/home/ec2-user/ot/ot.sock;
    }
}
```

**¿Por qué los `proxy_set_header`?** Django necesita conocer la IP real del cliente y el protocolo (HTTP/HTTPS). Sin estos headers, `request.META` en Django tendría información incorrecta.

Activa Nginx, verifica la configuración y reinícialo:

```bash
# Habilita Nginx para que inicie automáticamente
sudo systemctl enable nginx

# Verifica que el archivo de configuración no tenga errores de sintaxis
sudo nginx -t

# Aplica los cambios reiniciando Nginx
sudo systemctl restart nginx
```

---

## Paso 6 – Configurar GitHub Actions para CI/CD

Crea el archivo `.github/workflows/deploy.yml` en tu repositorio:

```yaml
name: Deploy Django to EC2

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Copy files via SCP
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USER }}
          key: ${{ secrets.KEY }}
          source: "."
          target: "/home/${{ secrets.USER }}/ot/"
          rm: false

      - name: Execute remote commands via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USER }}
          key: ${{ secrets.KEY }}
          envs: >
            DEBUG,SECRET_KEY,ALLOWED_HOSTS,DB_NAME,DB_USER,DB_PASSWORD,DB_HOST,DB_PORT
          script: |
            set -e

            cd /home/${{ secrets.USER }}/ot

            cat <<EOT > .env
            DEBUG=${DEBUG}
            SECRET_KEY=${SECRET_KEY}
            ALLOWED_HOSTS=${ALLOWED_HOSTS}
            DB_NAME=${DB_NAME}
            DB_USER=${DB_USER}
            DB_PASSWORD=${DB_PASSWORD}
            DB_HOST=${DB_HOST}
            DB_PORT=${DB_PORT}
            EOT

            sudo dnf install python3.11 python3.11-devel mariadb105-devel pkgconfig gcc -y

            if [ ! -f "venv/bin/python3.11" ]; then
              rm -rf venv
              python3.11 -m venv venv
            fi

            source venv/bin/activate

            pip install --upgrade pip
            pip install -r requirements.txt

            # Aplica las migraciones de base de datos
            python manage.py migrate --noinput

            # Recopila los archivos estáticos para que Nginx los sirva
            python manage.py collectstatic --noinput

            # Reinicia Gunicorn para cargar el nuevo código
            sudo systemctl restart gunicorn

        env:
          DEBUG: ${{ secrets.DEBUG }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          ALLOWED_HOSTS: ${{ secrets.ALLOWED_HOSTS }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
```

---

## Paso 7 – Configurar Secrets en GitHub

Los datos sensibles (contraseñas, llaves, IPs) **nunca deben subirse al repositorio**. GitHub Actions los lee desde su sistema de Secrets.

Ve a tu repositorio → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** y agrega:

| Secret | Descripción |
|---|---|
| `HOST` | IP pública de tu instancia EC2 |
| `USER` | Usuario SSH (normalmente `ec2-user`) |
| `KEY` | Contenido completo de tu archivo `.pem` |
| `DEBUG` | `False` en producción |
| `SECRET_KEY` | La secret key de Django |
| `ALLOWED_HOSTS` | Tu IP o dominio |
| `DB_NAME` | Nombre de la base de datos |
| `DB_USER` | Usuario de la base de datos |
| `DB_PASSWORD` | Contraseña de la base de datos |
| `DB_HOST` | Host de la base de datos (ej: RDS endpoint) |
| `DB_PORT` | Puerto (por defecto `5432` para PostgreSQL) |

> ⚠️ Para el secret `KEY`, copia el contenido **completo** del archivo `.pem`, incluyendo las líneas `-----BEGIN RSA PRIVATE KEY-----` y `-----END RSA PRIVATE KEY-----`.

---

## Flujo Completo del Despliegue

Una vez configurado todo, el flujo de trabajo es el siguiente:

```
1. Desarrollas en local y haces commit de tus cambios
        │
        ▼
2. git push origin main
        │
        ▼
3. GitHub Actions se activa automáticamente
        │
        ├── Copia el código al servidor (SCP)
        │
        └── Conecta por SSH y:
              ├── Escribe el archivo .env
              ├── Instala/actualiza dependencias
              ├── Ejecuta migraciones
              ├── Recopila archivos estáticos
              └── Reinicia Gunicorn
                      │
                      ▼
4. Tu aplicación está actualizada en producción ✅
```

---

## 🔧 Comandos útiles de administración

```bash
# Ver logs de Gunicorn en tiempo real
sudo journalctl -u gunicorn -f

# Ver logs de Nginx
sudo tail -f /var/log/nginx/error.log

# Reiniciar ambos servicios manualmente
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# Verificar estado de los servicios
sudo systemctl status gunicorn
sudo systemctl status nginx
```