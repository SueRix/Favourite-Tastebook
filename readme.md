# Django Project

This is a Django-based web application.

## Prerequisites

Ensure you have the following installed:

- **Python** (version 3.x recommended)
- **pip** (Python package manager)
- **virtualenv** (recommended for dependency management)
- **Git**

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SueRix/Favourite-Tastebook.git
   ```
   ```bash
   cd Favourite_Tastebook #To general project directory
   ```
   ```bash
   cd favourite_fastebook #To running of project directory
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**


   - **On Windows:**
     ```bash
     venv\Scripts\activate
     ```
   - **On macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Set up the environment variables:**
   - Create a `.env` file in the project root and add necessary variables, e.g.:
     ```
     SECRET_KEY=<your_secret_key>
     DEBUG=<true_or_false>
     DB_ENGINE=<database_backend>
     DB_NAME=<database_name>
     DB_PASSWORD=<database_password>
     DB_USER=<database_user>
     DB_HOST=<database_host>
     DB_PORT=<database_port>
     ```

2. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

3. **Create a superuser (optional, for admin access):**
   ```bash
   python manage.py createsuperuser
   ```

## Running the Application

To start the development server, run:

```bash
python manage.py runserver
```

The application will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Project at this moment have these working urls:
```
http://127.0.0.1:8000/accounts/register
```
```
http://127.0.0.1:8000/accounts/login
```
```
http://127.0.0.1:8000/accounts/home
```




## Additional Commands

- **Run tests of app:**
  ```bash
  python manage.py test <PATH_OF_APP.test>

## Deployment

For deployment instructions, follow Django's official guide on deploying to production servers such as Gunicorn, Nginx, or cloud platforms like AWS, Heroku, etc.

## Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Open a pull request.


**Happy coding!** 🚀

