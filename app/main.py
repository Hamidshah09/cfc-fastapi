from fastapi import FastAPI
from app.routes import auth_routes, idp_routes, report_routes, domicile_routes, arms_routes
from app.nitb import get_session

app = FastAPI(title="Approval Service API")

@app.on_event("startup")
async def startup_event():
    get_session()  # initialize session when FastAPI starts
# Include routers
app.include_router(auth_routes.router, prefix="/auth", tags=["Auth"])
app.include_router(idp_routes.router, prefix="/idp", tags=["Idp"])
app.include_router(report_routes.router, prefix="/reports", tags=["Reports"])
app.include_router(domicile_routes.router, prefix="/domicile", tags=["Domicile"])
app.include_router(arms_routes.router, prefix="/arms", tags=["Arms"])
