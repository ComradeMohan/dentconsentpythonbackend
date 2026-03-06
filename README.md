# DentConsent Python Backend

This is the FastAPI-based backend for the DentConsent application.

## Prerequisites

- Python 3.8 or higher
- [wkhtmltopdf](https://wkhtmltopdf.org/downloads.html) (0.12.6 or higher recommended)

## Installation

### 1. Set up Virtual Environment
It is recommended to use a virtual environment to manage dependencies.

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate
```

### 2. Install Dependencies
Install the required Python packages using `pip`.

```powershell
pip install -r requirements.txt
```

### 3. Setup wkhtmltopdf
The PDF generation requires `wkhtmltopdf`. 

#### Option A: Use existing binary (if available)
If you already have `wkhtmltox.exe` or the `wkhtmltox` folder in the project root:
1. Ensure `wkhtmltox/bin/wkhtmltopdf.exe` exists.
2. The application is configured to look for it at: `.\wkhtmltox\bin\wkhtmltopdf.exe`.

#### Option B: Manual Installation
1. Download the installer from [wkhtmltopdf.org](https://wkhtmltopdf.org/downloads.html).
2. Install it on your system.
3. If you install it to a different path, update the `wkhtmltopdf_path` in `utils/pdf_generator.py`.

## Running the Application

To start the FastAPI server with auto-reload:

```powershell
python main.py
```

The server will be available at `http://localhost:8000`.
You can access the interactive API documentation at `http://localhost:8000/docs`.

## Project Structure

- `main.py`: Entry point of the application.
- `routers/`: Contains API route definitions (auth, profile, education, etc.).
- `utils/`: Helper utilities like `pdf_generator.py`.
- `uploads/`: Directory where generated PDFs and uploaded files are stored.
- `database.py`: Database connection setup.
