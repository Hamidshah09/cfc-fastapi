from fastapi import FastAPI
from app.routes import auth_routes, used_by_laravel_routes
# idp_routes, noc_routes, report_routes, domicile_routes, arms_routes, noc_ict_routes, verification_letter_routes
# ,noc_routes
from app.nitb import nitb_get
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Approval Service API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cfc-ict.com",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @app.on_event("startup")
# async def startup_event():
#     nitb_get() 
# Include routers
app.include_router(auth_routes.router, prefix="/auth", tags=["Auth"])
# app.include_router(idp_routes.router, prefix="/idp", tags=["Idp"])
# app.include_router(report_routes.router, prefix="/reports", tags=["Reports"])
# app.include_router(domicile_routes.router, prefix="/domicile", tags=["Domicile"])
# app.include_router(noc_ict_routes.router)
# app.include_router(noc_routes.router)
# app.include_router(verification_letter_routes.router)
app.include_router(used_by_laravel_routes.router, prefix="/domicile", tags=["Domicile"])
