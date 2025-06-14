from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.auth import get_current_user

app = FastAPI()

# Mount static files directory for CSS, JS, and images.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates directory for HTML files.
templates = Jinja2Templates(directory="templates")

# Routes for rendering HTML pages
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/index", response_class=HTMLResponse)
async def dashboard(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/add-items", response_class=HTMLResponse)
async def add_items_page(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("add_items.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/waste", response_class=HTMLResponse)
async def waste_page(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("waste.html", {"request": request})
