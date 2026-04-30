from fastapi import FastAPI
cxy = FastAPI()


@cxy.get("/search/")
def search(keyword: str, page: int = None):
    return {"keyword": keyword, "page": page}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("practise:cxy", host="127.0.0.1", port=8000, reload=True)   

