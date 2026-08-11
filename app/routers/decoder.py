"""Decoder geral: auto-detecta e decodifica certificado, CSR, chave privada ou PFX."""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..services import decoder

router = APIRouter(tags=["decoder"])


@router.post("/decode")
async def decode_general(file: UploadFile | None = File(None),
                          pem_text: str = Form(""),
                          password: str = Form("")):
    if pem_text and pem_text.strip():
        data = pem_text.strip().encode("utf-8")
        filename = ""
    elif file and file.filename:
        data = await file.read()
        filename = file.filename
    else:
        raise HTTPException(400, "Envie um arquivo ou cole o conteúdo (PEM ou base64).")

    try:
        return decoder.detect_and_decode(data, password or None, filename=filename)
    except ValueError as e:
        raise HTTPException(400, str(e))
