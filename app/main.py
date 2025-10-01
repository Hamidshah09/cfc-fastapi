from fastapi import FastAPI
from app.routes import auth_routes, approval_routes, report_routes

app = FastAPI(title="Approval Service API")

# Include routers
app.include_router(auth_routes.router, prefix="/auth", tags=["Auth"])
app.include_router(approval_routes.router, prefix="/idp", tags=["Idp"])
app.include_router(report_routes.router, prefix="/reports", tags=["Reports"])
