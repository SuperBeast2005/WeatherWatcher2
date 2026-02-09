import uvicorn
from fastapi import FastAPI

from backend.routers import measurement, ideal_value

app = FastAPI()

app.include_router(measurement.router)
app.include_router(ideal_value.router)
@app.get("/")
def read_root():
    return {"Hello": "World"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)