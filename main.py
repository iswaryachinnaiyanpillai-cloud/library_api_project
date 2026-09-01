from fastapi import FastAPI

app = FastAPI(title="Library Book Lending API")


@app.get("/health")
def health_check():
    return {"status": "healthy"}