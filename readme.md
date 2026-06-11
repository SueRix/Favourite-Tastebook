# Favourite Tastebook

Favourite Tastebook is an advanced Django-based web application for recipe management. It goes beyond simple recipe storage by integrating AI tools (Gemini API) and cosine similarity algorithms to provide a personalized culinary experience based on user taste preferences.

🟢 **Live Deployment:** [http://34.158.233.87:8000/home/](http://34.158.233.87:8000/home/)

## Core Features

- **Smart Recipe Database**: Search, filter, and view detailed recipe cards.
- **Taste Profiling Engine**: Like/dislike recipes and ingredients to dynamically build your unique taste profile.
- **AI Image Analyzer**: Upload images to process and extract recipe data using AI models.
- **Saved Collections**: Easily bookmark and manage your favorite culinary discoveries.
- **User Management**: Secure registration, login, password management, and profile customization.

## Prerequisites

Ensure you have the following installed on your system:

- **Python** (version 3.13 recommended)
- **pip** (Python package manager)
- **virtualenv** (recommended for dependency management)
- **Git**

## Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/SueRix/Favourite-Tastebook.git](https://github.com/SueRix/Favourite-Tastebook.git)
   cd Favourite_Tastebook
   cd favourite_fastebook
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Set up environment variables:**
   Create a `.env` file in the project root and add the necessary variables:
   ```env
   SECRET_KEY=<your_secret_key>
   DEBUG=True
   
   # Database settings
   DB_ENGINE=<database_backend>
   DB_NAME=<database_name>
   DB_USER=<database_user>
   DB_PASSWORD=<database_password>
   DB_HOST=<database_host>
   DB_PORT=<database_port>
   
   # AI Integration
   GEMINI_API_KEY=<your_api_key_here>
   ```

2. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

3. **Create a superuser (for admin panel access):**
   ```bash
   python manage.py createsuperuser
   ```

## Running the Application

To start the local development server, run:
```bash
python manage.py runserver
```
The application will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Application URL Structure

The project currently supports the following working URLs, divided by functional modules:

### 1. Main & Recipe Manager (`/home/`)
- `GET /home/` - Main Tastebook dashboard.
- `GET /home/database/` - Full recipes database search.
- `GET /home/saved/` - List of user's saved recipes.
- `POST /home/saved/<int:recipe_id>/` - Add/remove a recipe from saved.
- **HTMX Partials:** `/home/partials/ingredients/`, `/home/partials/recipes/`, `/home/partials/database/search/`, `/home/partials/database/card/<int:recipe_id>/`.

### 2. AI Integration (`/home/ai/`)
- `GET/POST /home/ai/upload-form/` - Form for uploading images for AI analysis.
- `POST /home/ai/process/` - Trigger AI image processing.
- `GET /home/ai/status/<str:task_id>/` - Check the status of the background AI task.

### 3. Taste Profiling API (`/home/tastes/` & `/home/api/`)
- `GET /home/tastes/` - Tastes profile management page.
- `POST /home/api/tastes/recipe/<int:recipe_id>/like/` - Like a recipe.
- `POST /home/api/tastes/recipe/<int:recipe_id>/dislike/` - Dislike a recipe.
- `POST /home/api/tastes/ingredient/update/` - Update ingredient preferences.
- `POST /home/api/taste/cuisine/update/` - Update cuisine preferences.
- `POST /home/api/tastes/toggle-global/` - Toggle global taste filtering.

### 4. Authentication (`/accounts/`)
- `GET/POST /accounts/login/` - User login.
- `GET/POST /accounts/register/` - New user registration.
- `POST /accounts/logout/` - User logout.
- `GET/POST /accounts/password-change/` - Change account password.
- `POST /accounts/delete/` - Delete user account.

### 5. User Profile (`/profile/`)
- `GET/POST /profile/` - Edit user profile details.

---

## Additional Commands

- **Run unit tests for a specific app:**
  ```bash
  python manage.py test <app_name>.tests
  ```

## Deployment

For deployment instructions, follow Django's official guide on deploying to production servers using WSGI/ASGI servers (like Gunicorn or Uvicorn) combined with a reverse proxy (like Nginx). The current live version is hosted remotely. 

## Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Open a pull request.
