"""Classificação conservadora do pós-clique: somente sinais visíveis, sem rede."""
POST_UI_JS=r"""() => {
    const visible=el => {
        const r=el.getBoundingClientRect();
        const cs=getComputedStyle(el);
        return r.width>0 && r.height>0 && cs.visibility!=='hidden' && cs.display!=='none';
    };
    const dialogs=[...document.querySelectorAll('[role="dialog"]')].filter(visible);
    const leafTexts=(root) => [...root.querySelectorAll('*')]
        .filter(el => el.children.length===0 && visible(el))
        .map(el => (el.textContent||'').trim().replace(/\\s+/g,' '))
        .filter(s => s.length>0 && s.length<200);
    const dialogText=dialogs.flatMap(leafTexts);
    // Mesmo com texto de cliente no DOM, devolver APENAS booleanos.
    const posting=dialogText.some(s => /^(postando|publicando|posting|publishing)(?:[.!… ]*)$/i.test(s));
    const pending=dialogText.some(s => /(aguardando aprova[cç][aã]o|pending approval|aguardando an[aá]lise)/i.test(s));
    const warning=dialogText.some(s => /(n[aã]o foi poss[ií]vel publicar|couldn't post|could not publish|tente novamente|try again)/i.test(s));
    const statusRoots=[...document.querySelectorAll('[role="status"],[role="alert"]')].filter(visible);
    const bannerText=statusRoots.flatMap(leafTexts);
    const processing=bannerText.some(s => /(processando v[ií]deo|processing video|seu v[ií]deo est[aá] sendo processado|video is processing)/i.test(s));
    return {dialog_open:dialogs.length>0,posting,pending_review:pending,warning,video_processing:processing};
}"""

def classify_post_ui(flags):
    """Conservador: nunca inferir publicado a partir de diálogo fechado."""
    if not isinstance(flags,dict):
        return "OBSERVATION_UNAVAILABLE"
    if flags.get("warning"):
        return "FACEBOOK_WARNING"
    if flags.get("pending_review"):
        return "PENDING_REVIEW"
    if flags.get("posting"):
        return "POSTING_IN_PROGRESS"
    if flags.get("video_processing"):
        return "VIDEO_PROCESSING"
    if flags.get("dialog_open"):
        return "DIALOG_OPEN_UNVERIFIED"
    return "POST_UI_CLOSED_UNVERIFIED"
