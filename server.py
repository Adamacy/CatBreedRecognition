from fastapi import FastAPI, File, UploadFile
from main import check_image
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/image')
async def get_image(image: UploadFile = File()):
    return {"res": check_image(image.file)}