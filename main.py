from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from routers import auth_router, view_router

app = FastAPI(title="Ryowu Auth & Member System")

# 掛載靜態與路由
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth_router.router)
app.include_router(view_router.router)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)
