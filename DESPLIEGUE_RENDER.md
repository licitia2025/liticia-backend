# Guía de Despliegue en Render - Liticia Backend

Esta guía te llevará paso a paso para desplegar el backend de Liticia en Render (plan gratuito).

## 📋 Prerrequisitos

Antes de empezar, asegúrate de tener:

- ✅ URL de PostgreSQL de Supabase
- ✅ UPSTASH_REDIS_REST_URL de Upstash
- ✅ UPSTASH_REDIS_REST_TOKEN de Upstash  
- ✅ OPENAI_API_KEY de OpenAI
- ✅ Cuenta de GitHub (para subir el código)

---

## Paso 1: Subir el Código a GitHub

### 1.1 Crear repositorio en GitHub

1. Ve a https://github.com/new
2. Nombre del repositorio: `liticia-backend`
3. Visibilidad: **Private** (recomendado)
4. NO marques "Initialize this repository with a README"
5. Haz clic en **"Create repository"**

### 1.2 Subir el código

En tu terminal/consola, ejecuta estos comandos desde la carpeta `liticia/backend`:

```bash
cd /ruta/a/liticia/backend

# Inicializar git
git init

# Crear .gitignore
echo "__pycache__/" > .gitignore
echo "*.pyc" >> .gitignore
echo ".env" >> .gitignore
echo "*.db" >> .gitignore

# Añadir archivos
git add .

# Hacer commit
git commit -m "Initial commit - Liticia backend"

# Conectar con GitHub (reemplaza TU_USUARIO con tu usuario de GitHub)
git remote add origin https://github.com/TU_USUARIO/liticia-backend.git

# Subir código
git branch -M main
git push -u origin main
```

---

## Paso 2: Crear Cuenta en Render

1. Ve a https://render.com
2. Haz clic en **"Get Started"**
3. Regístrate con **GitHub** (más fácil para conectar repositorios)
4. Autoriza a Render para acceder a tus repositorios

---

## Paso 3: Desplegar Backend API

### 3.1 Crear Web Service

1. En el dashboard de Render, haz clic en **"New +"** → **"Web Service"**

2. Conecta tu repositorio:
   - Busca `liticia-backend`
   - Haz clic en **"Connect"**

3. Configura el servicio:
   - **Name**: `liticia-backend`
   - **Region**: Frankfurt (Europe)
   - **Branch**: `main`
   - **Root Directory**: (déjalo vacío)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free

4. Haz clic en **"Advanced"** para añadir variables de entorno

5. Añade estas variables de entorno (haz clic en "Add Environment Variable" para cada una):

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | Tu URL de Supabase (postgresql://...) |
   | `REDIS_URL` | Tu UPSTASH_REDIS_REST_URL |
   | `OPENAI_API_KEY` | Tu API key de OpenAI (sk-proj-...) |
   | `ENVIRONMENT` | `production` |
   | `MIN_PRESUPUESTO_ANALISIS_IA` | `50000` |
   | `SCRAPING_INTERVALO_HORAS` | `3` |
   | `ANALISIS_IA_INTERVALO_HORAS` | `6` |

6. Haz clic en **"Create Web Service"**

7. Espera 5-10 minutos mientras Render despliega tu backend

8. Una vez completado, verás una URL como: `https://liticia-backend.onrender.com`

9. **Guarda esta URL** - la necesitarás para el frontend

### 3.2 Verificar que funciona

1. Ve a: `https://liticia-backend.onrender.com/health`
2. Deberías ver algo como:
   ```json
   {
     "status": "healthy",
     "timestamp": "2025-10-18T10:30:00",
     "service": "liticia-backend"
   }
   ```

3. Ve a: `https://liticia-backend.onrender.com/docs`
4. Deberías ver la documentación interactiva de la API (Swagger UI)

---

## Paso 4: Ejecutar Migraciones de Base de Datos

Una vez desplegado el backend, necesitas crear las tablas en la base de datos:

### 4.1 Usar Shell de Render

1. En Render, ve a tu servicio `liticia-backend`
2. Haz clic en **"Shell"** en el menú superior
3. Ejecuta estos comandos:

```bash
# Crear migración inicial
alembic revision --autogenerate -m "Initial migration"

# Aplicar migración
alembic upgrade head
```

4. Deberías ver mensajes de éxito indicando que las tablas se crearon

---

## Paso 5: Desplegar Celery Worker (Opcional para MVP)

Si quieres scraping automático, necesitas desplegar el worker de Celery:

1. En Render, haz clic en **"New +"** → **"Background Worker"**

2. Selecciona el mismo repositorio: `liticia-backend`

3. Configura:
   - **Name**: `liticia-worker`
   - **Region**: Frankfurt
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `celery -A app.core.celery_app worker --loglevel=info`
   - **Instance Type**: Free

4. Añade las mismas variables de entorno que en el backend API

5. Haz clic en **"Create Background Worker"**

---

## Paso 6: Desplegar Celery Beat (Opcional para MVP)

Para programar el scraping automático:

1. En Render, haz clic en **"New +"** → **"Background Worker"**

2. Selecciona el mismo repositorio: `liticia-backend`

3. Configura:
   - **Name**: `liticia-scheduler`
   - **Region**: Frankfurt
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `celery -A app.core.celery_app beat --loglevel=info`
   - **Instance Type**: Free

4. Añade las mismas variables de entorno

5. Haz clic en **"Create Background Worker"**

---

## ✅ Verificación Final

### Backend API funcionando:
- [ ] `https://TU-BACKEND.onrender.com/health` devuelve status "healthy"
- [ ] `https://TU-BACKEND.onrender.com/docs` muestra la documentación
- [ ] Las tablas están creadas en Supabase (puedes verificar en Database → Tables)

### Servicios opcionales:
- [ ] Worker de Celery corriendo (si lo desplegaste)
- [ ] Scheduler de Celery corriendo (si lo desplegaste)

---

## 🎯 Siguiente Paso

Una vez que el backend esté funcionando, necesitas:

1. **Actualizar el frontend** con la URL del backend
2. **Desplegar el frontend** en Vercel o Netlify

---

## ⚠️ Notas Importantes

### Limitaciones del Plan Gratuito de Render:

- **Inactividad**: El servicio se "duerme" después de 15 minutos sin uso
- **Primer arranque**: Puede tardar 30-60 segundos en responder la primera vez
- **Horas mensuales**: 750 horas/mes por servicio (suficiente para 24/7)

### Optimizaciones:

- El backend se "despertará" automáticamente cuando reciba una petición
- Puedes usar un servicio como UptimeRobot (gratuito) para hacer ping cada 5 minutos y mantenerlo activo

---

## 🆘 Solución de Problemas

### Error: "Build failed"
- Verifica que `requirements.txt` esté en la raíz del repositorio
- Revisa los logs de build en Render

### Error: "Application failed to respond"
- Verifica que las variables de entorno estén correctamente configuradas
- Revisa los logs del servicio en Render

### Error de base de datos:
- Verifica que la URL de PostgreSQL sea correcta
- Asegúrate de haber ejecutado las migraciones (`alembic upgrade head`)

---

## 📞 Soporte

Si tienes problemas, revisa:
1. Los logs en Render (pestaña "Logs")
2. La documentación de Render: https://render.com/docs
3. El estado de los servicios: https://status.render.com

---

¡Listo! Tu backend de Liticia debería estar funcionando en producción. 🎉

