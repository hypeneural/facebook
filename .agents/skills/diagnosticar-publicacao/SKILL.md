---
name: diagnosticar-publicacao
description: Diagnostica erro real do Playwright ao abrir grupos, selecionar foto, preencher texto ou clicar publicar no Facebook, preservando sessão e evitando publicação duplicada.
---

# /diagnosticar-publicacao
1. Coletar mensagem de erro e estágio exato; consultar data/server-stderr.log sem reproduzir dados privados.
2. Identificar se o clique PUBLICAR pode ter ocorrido. Se sim, marcar SUBMITTED_UNVERIFIED, PARAR e verificar grupo; nunca repetir.
3. Se falhou antes do clique, observar a interface real em português no Chrome dedicado; isolar seletor incorreto em app/browser.py.
4. Alterar somente o seletor/espera que falhou, sem novas bibliotecas, bypass, proxies, múltiplas contas ou APIs privadas.
5. Executar /verificar-mvp; pedir nova autorização se um segundo teste real for necessário.
6. Entregar: erro, hipótese demonstrada, arquivo alterado, PASS/FAIL e situação da publicação. Não inventar link de post.
