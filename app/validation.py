import re
from pathlib import Path
from urllib.parse import urlsplit
FORMATS={".jpg",".jpeg",".png",".webp",".mp4",".mov"}
def group_url(value):
    u=urlsplit((value or "").strip())
    if u.scheme!="https" or u.hostname not in {"facebook.com","www.facebook.com","m.facebook.com","web.facebook.com"} or u.port or u.username or u.password: raise ValueError("Informe URL HTTPS de um grupo Facebook.")
    m=re.fullmatch(r"/groups/([A-Za-z0-9_.-]{2,150})/?",u.path)
    if not m: raise ValueError("Destino deve ser facebook.com/groups/ID.")
    return "https://www.facebook.com/groups/"+m.group(1)+"/"
def validate(url,caption,names):
    url=group_url(url)
    if not caption.strip() and not names: raise ValueError("Digite legenda ou selecione arquivo.")
    if len(caption)>5000: raise ValueError("Legenda excede 5000 caracteres.")
    if len(names)>10: raise ValueError("Máximo de 10 imagens.")
    exts=[Path(n).suffix.lower() for n in names]
    if any(x not in FORMATS for x in exts): raise ValueError("Mídia deve ser JPG, PNG, WEBP, MP4 ou MOV.")
    if any(x in {".mp4",".mov"} for x in exts) and len(exts)!=1: raise ValueError("Vídeo deve ser arquivo único.")
    return url
