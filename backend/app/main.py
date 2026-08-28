from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Entrelinhas API")

    @app.get("/api/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
