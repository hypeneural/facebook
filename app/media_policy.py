"""Regras puras de mídia: sem Facebook, sem token e sem acesso ao navegador."""
from pathlib import Path

IMAGE_EXTS={".jpg",".jpeg",".png",".webp"}
VIDEO_EXTS={".mp4",".mov"}

def media_kind(files):
    if not files:
        return "text"
    exts=[Path(f).suffix.lower() for f in files]
    if all(x in IMAGE_EXTS for x in exts):
        return "image"
    if len(exts)==1 and exts[0] in VIDEO_EXTS:
        return "video"
    raise ValueError("Envie apenas fotos OU um vídeo por publicação.")

def wait_budget_ms(kind,count,bytes_total=0):
    if kind=="video":
        # Tamanho ajuda a dimensionar limite, mas velocidade/codec são variáveis.
        # 28 MB mantém o orçamento homologado; 300 MB permite até 10 min.
        extra=max(0,int(bytes_total)-30*1024*1024)
        increments=(extra+50*1024*1024-1)//(50*1024*1024)
        return min(600000,240000+60000*increments)
    if kind=="image":
        return min(90000,25000+7000*max(0,count-1))
    return 15000

def preview_selector(kind):
    if kind=="video":
        return '[role="dialog"] video, [role="dialog"] img[src*="blob:"], [role="dialog"] [aria-label*="Remover"]'
    return '[role="dialog"] img[src*="blob:"], [role="dialog"] img[src*="scontent"], [role="dialog"] [aria-label*="Remover"], [role="dialog"] [aria-label*="Editar"]'

def input_file_count(locator):
    return locator.evaluate("(el) => el.files ? el.files.length : -1")

def remaining_budget_ms(deadline,now=None):
    """Reutiliza o MESMO orçamento de prontidão; não gasta 4 min por etapa."""
    import time
    if deadline is None:
        return 15000
    current=time.monotonic() if now is None else now
    return max(1000,int((deadline-current)*1000))
