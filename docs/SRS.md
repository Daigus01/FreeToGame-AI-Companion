# Especificación de Requisitos de Software (SRS)
## Proyecto: FreeToGame AI Companion & Recommendation Platform
**Versión:** 1.0  
**Fecha:** 27 de octubre de 2026  
**Estado:** Borrador de Arquitectura Inicial  

---

## 1. Introducción y Alcance

### 1.1 Propósito
Este documento establece la especificación completa y detallada de requisitos para el desarrollo de un portal web interactivo de videojuegos *Free-to-Play* (F2P). La plataforma combina:
1. Una biblioteca interactiva alimentada por la API pública de **FreeToGame**.
2. Un **Chatbot Asistente con LLM** que implementa *Tool Calling / Function Calling* para consultar la API dinámicamente según las consultas de los usuarios.
3. Un **Motor de Recomendación de Machine Learning** que predice y selecciona un "Top 5 diario" de juegos recomendados para cada usuario, utilizando su historial de navegación y las preferencias expresadas en el chat.

### 1.2 Alcance del Sistema
* **Frontend Web:** Interfaz moderna e interactiva con catálogo de juegos, filtros estáticos, interfaz de chat conversacional en tiempo real (con streaming) y un widget para las recomendaciones diarias.
* **Backend Orchestrator:** API REST/WebSocket que coordina la comunicación entre la UI, la base de datos local, la API externa de FreeToGame y el proveedor del LLM.
* **Agente LLM (Chatbot):** Modelo de lenguaje con soporte nativo de *Function Calling* encargado de interpretar intenciones, invocar endpoints de la API y sintetizar respuestas con componentes enriquecidos en la UI.
* **Pipeline de Machine Learning:** Proceso en lote (*batch pipeline*) que procesa eventos de usuario y extractos de chat para recalcular diariamente el ranking de 5 juegos recomendados por usuario.

---

## 2. Arquitectura General y Stack Tecnológico

### 2.1 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js)                            │
│    [Biblioteca / Filtros]    [Widget Top 5]     [Chatbot Component]     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP / Server-Sent Events (SSE)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI / Node.js)                     │
│  ┌──────────────────────────┬─────────────────────────┬──────────────┐  │
│  │   Auth & User Service    │   LLM Orchestrator      │  Rec Engine  │  │
│  └────────────┬─────────────┴────────────┬────────────┴──────┬───────┘  │
└───────────────┼──────────────────────────┼───────────────────┼──────────┘
                │                          │                   │
                ▼                          ▼                   ▼
    ┌──────────────────────┐   ┌──────────────────────┐  ┌──────────────┐
    │  PostgreSQL / Redis  │   │  LLM (OpenAI/Groq)   │  │ FreeToGame   │
    │ (Datos & Historial)  │   │   (Tool Calling)     │  │  API External│
    └──────────────────────┘   └──────────────────────┘  └──────────────┘
```

### 2.2 Stack Tecnológico Recomendado
* **Frontend:** Next.js (React), TailwindCSS, Vercel AI SDK (manejo de streaming y Tool UI).
* **Backend Framework:** Python (FastAPI) o TypeScript (NestJS / Express).
* **LLM Engine:** OpenAI (GPT-4o-mini / GPT-4o) o Anthropic (Claude 3.5 Sonnet). Framework orquestador: **Instructor** (Python/Pydantic) o **LangGraph**.
* **Bases de Datos:**
  * **PostgreSQL:** Persistencia de usuarios, catálogo sincronizado, interacciones y recomendaciones precalculadas.
  * **Redis:** Caché de respuestas de la API de FreeToGame y gestión de sesiones/historial del chat.
* **Pipeline de Machine Learning:** Python (`scikit-learn`, `LightGBM` / `implicit`), ejecutado mediante tareas programadas (*APScheduler* / *Celery*).

---

## 3. Requisitos Funcionales (RF)

### Módulo 1: Catálogo y Biblioteca de Juegos (UI)
* **RF-1.1 (Exploración del Catálogo):** La plataforma mostrará un catálogo en cuadrícula (*grid*) con los juegos F2P obtenidos de FreeToGame, incluyendo imagen de portada, título, género, plataforma y descripción corta.
* **RF-1.2 (Filtros Estáticos de la UI):**
  * **Plataforma:** `pc`, `browser`, `all`.
  * **Categoría / Género:** `mmorpg`, `shooter`, `pvp`, `moba`, `anime`, `strategy`, `fantasy`, `sci-fi`, `card`, `racing`, `fighting`, `social`, `sports`.
  * **Criterios de Ordenamiento:** `release-date`, `popularity`, `alphabetical`, `relevance`.
* **RF-1.3 (Detalle del Juego):** Vista modal o página dedicada con información detallada: capturas de pantalla, requisitos del sistema, desarrollador, editor, fecha de lanzamiento y enlace directo de descarga/play.
* **RF-1.4 (Biblioteca del Usuario):** Los usuarios registrados podrán clasificar juegos como *"Guardados"*, *"Jugados"* o *"No me interesa"*.

### Módulo 2: Chatbot Inteligente (LLM + Tool Calling)
* **RF-2.1 (Atención en Lenguaje Natural):** El usuario podrá realizar consultas abiertas (ej. *"Busco un MMORPG de fantasía para PC que no sea muy antiguo"*).
* **RF-2.2 (Ejecución de Herramientas / Function Calling):** El orquestador pasará los esquemas de herramientas al LLM. El LLM determinará cuando invocar las siguientes funciones:
  * `get_games_by_filter(category, platform, sort_by)`
  * `get_game_details(game_id)`
* **RF-2.3 (Respuestas Enriquecidas):** Cuando el LLM devuelva recomendaciones, el frontend no mostrará solo texto; renderizará tarjetas interactivas de los juegos sugeridos dentro del flujo del chat.
* **RF-2.4 (Persistencia del Contexto Conversacional):** Mantener el historial del chat en Redis/PostgreSQL para responder preguntas de seguimiento (ej. *"¿Y de esos, cuál es el más reciente?"*).

### Módulo 3: Motor de Recomendación Diario (ML Pipeline)
* **RF-3.1 (Generación Batch del Top 5 Diario):** Tarea automatizada que se ejecuta diariamente a las 00:00 UTC para precalcular exactamente 5 juegos recomendados por usuario.
* **RF-3.2 (Extracción de Atributos del Usuario):**
  * Interacciones directas (clics, guardados, juegos marcados como *"no me interesa"*).
  * Intenciones extraídas de las conversaciones del chat (resúmenes de preferencias de género/plataforma generados por el LLM).
* **RF-3.3 (Reglas de Diversidad y Exclusión):**
  * Excluir juegos previamente marcados como *"Jugado"* o *"No me interesa"*.
  * Garantizar diversidad: Máximo 2 juegos del mismo subgénero en el Top 5 diario.
* **RF-3.4 (Widget de Recomendaciones en UI):** Un componente destacado en la página de inicio que muestra los 5 juegos del día asignados al usuario.

---

## 4. Requisitos No Funcionales (RNF)

* **RNF-1 (Latencia del Chatbot):** El primer token de la respuesta conversacional debe enviarse en $T < 1.5\text{ segundos}$ mediante Server-Sent Events (SSE). La ejecución completa de herramientas y consulta a la API de FreeToGame debe responder en $T < 3.0\text{ segundos}$.
* **RNF-2 (Caché de API Externa):** Almacenar las respuestas de la API de FreeToGame en Redis con un Time-To-Live (TTL) de 12 horas para minimizar la latencia y evitar rebasar límites de tasa (*rate limits*).
* **RNF-3 (Disponibilidad y Fallback):** Disponibilidad mínima del $99.5\%$. Si la API externa no responde, el sistema debe operar en modo degradado utilizando los datos del catálogo guardados en PostgreSQL/Redis.
* **RNF-4 (Seguridad):** Las credenciales y claves de API (OpenAI, Anthropic, etc.) deben residir únicamente en variables de entorno del backend (`.env`) y no exponerse jamás al frontend.

---

## 5. Especificación de Herramientas del LLM (Tool Schemas)

El backend proveerá al modelo LLM la siguiente estructura JSON Schema para el *Tool Calling*:

```json
[
  {
    "name": "get_games_by_filter",
    "description": "Consulta el catálogo de juegos de FreeToGame aplicando filtros por categoría, plataforma o criterio de ordenamiento.",
    "parameters": {
      "type": "object",
      "properties": {
        "category": {
          "type": "string",
          "description": "Categoría o género principal del juego (ej. 'shooter', 'mmorpg', 'pvp', 'strategy', 'racing', 'anime', 'fantasy')."
        },
        "platform": {
          "type": "string",
          "enum": ["pc", "browser", "all"],
          "description": "Plataforma en la que se ejecuta el juego."
        },
        "sort_by": {
          "type": "string",
          "enum": ["release-date", "popularity", "alphabetical", "relevance"],
          "description": "Criterio de ordenamiento de los resultados."
        }
      },
      "required": []
    }
  },
  {
    "name": "get_game_details",
    "description": "Obtiene la información detallada e id de un videojuego específico.",
    "parameters": {
      "type": "object",
      "properties": {
        "game_id": {
          "type": "integer",
          "description": "ID único del videojuego en FreeToGame."
        }
      },
      "required": ["game_id"]
    }
  }
]
```

---

## 6. Esquema de Base de Datos (DDL SQL)

```sql
-- Usuarios
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Catálogo Local de Juegos (Sincronizado desde FreeToGame API)
CREATE TABLE games (
    id INT PRIMARY KEY, -- ID original de FreeToGame
    title VARCHAR(255) NOT NULL,
    thumbnail TEXT,
    short_description TEXT,
    genre VARCHAR(100),
    platform VARCHAR(50),
    publisher VARCHAR(100),
    developer VARCHAR(100),
    release_date DATE,
    freetogame_profile_url TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Biblioteca de Usuarios e Interacciones
CREATE TABLE user_game_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    game_id INT REFERENCES games(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL, -- 'view', 'click', 'saved', 'played', 'disliked'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Sesiones e Historial de Chat
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system', 'tool'
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Recomendaciones Diarias de Machine Learning
CREATE TABLE daily_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    recommendation_date DATE NOT NULL,
    game_ids INT[] NOT NULL, -- Matriz de 5 IDs de juegos recomendados
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, recommendation_date)
);
```

---

## 7. Plan de Implementación por Fases

| Fase | Alcance y Entregables |
| :--- | :--- |
| **Fase 1: MVP Catálogo + API** | • Backend FastAPI/Node integrando FreeToGame API + Caché Redis.<br>• Base de datos PostgreSQL configurada con tablas iniciales.<br>• Frontend Next.js con catálogo grid, filtros y modal de detalle. |
| **Fase 2: Chatbot LLM + Tool Calling** | • Orquestador LLM implementando Tool Calling para la API.<br>• Componente de chat en frontend con streaming (Vercel AI SDK).<br>• Renderizado de tarjetas de juego interactivas dentro del chat. |
| **Fase 3: ML Engine & Top 5 Diario** | • Registro continuo de eventos de interacción del usuario.<br>• Proceso batch de recomendación y cálculo de perfil de preferencias.<br>• Widget del Top 5 diario en la página principal. |