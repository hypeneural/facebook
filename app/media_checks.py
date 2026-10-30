"""Políticas de prontidão da mídia: determinísticas, sem bibliotecas externas."""
from __future__ import annotations
import re

def pick_file_input_index(accepts,kind):
    """Retorna índice único compatível. Não seleciona campo de comentário nem input ambíguo."""
    if kind not in ("image","video"):
        raise ValueError("Tipo de mídia inválido.")
    if not accepts:
        return None
    scored=[]
    for index,raw in enumerate(accepts):
        accept=(raw or "").lower()
        if not accept.strip() or "*/*" in accept:
            score=1
        elif kind=="image" and ("image" in accept or any(s in accept for s in (".jpg",".jpeg",".png",".webp"))):
            score=3
        elif kind=="video" and ("video" in accept or any(s in accept for s in (".mp4",".mov"))):
            score=3
        else:
            score=0
        if score:scored.append((score,index))
    if not scored:
        raise ValueError("Nenhum input do diálogo aceita o tipo de mídia.")
    best=max(s for s,_ in scored)
    candidates=[index for s,index in scored if s==best]
    if len(candidates)!=1:
        raise ValueError("Múltiplos inputs de mídia equivalentes no diálogo; escolha ambígua.")
    return candidates[0]

def gallery_complete(expected,visible,overflow=None,assigned_count=0):
    """Uma colagem só está completa com prova quantitativa, jamais só botão 'Editar'."""
    if expected<1 or visible<0:
        return False
    if visible>=expected:
        return True
    return (
        expected>3 and visible>=2 and assigned_count==expected
        and isinstance(overflow,int) and overflow>0
        and visible+overflow==expected
    )

def normalize_caption(text):
    return re.sub(r"\s+"," ",(text or "").replace("\u00a0"," ")).strip()

def caption_matches(expected,actual):
    return normalize_caption(expected)==normalize_caption(actual)
