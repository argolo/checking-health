# Checking Health

CLI para execução de **healthcheck em múltiplos endpoints HTTP/HTTPS**, com saída rica, colorida e orientada a diagnóstico.

---

## ✨ Features

* ✅ Execução sequencial com **feedback em tempo real**
* 🌐 Suporte a múltiplos endpoints via arquivo
* 🎯 Identificação do tipo de endpoint (`TYPE`) baseada na URL
* 📊 Métricas detalhadas por requisição:

  * Status (OK / FAIL)
  * Código HTTP
  * Domain
  * IP
  * Content-Type
  * Tamanho do download
  * Tempo de resposta (`REQ`)
  * Tempo total (`TIME`)
  * Title (quando HTML)
* 🎨 Saída colorida (verde/vermelho)
* 📈 Resumo final com métricas agregadas
* 🧪 Testável com `pytest`

---

## 📦 Instalação

Instale diretamente do PyPI:

```bash
pip install checking-health
```

🔗 Projeto no PyPI:
[https://pypi.org/project/checking-health](https://pypi.org/project/checking-health)

---

## ▶️ Uso

```bash
checking-health endpoints.txt --timeout 3
```

---

## 📄 Formato do arquivo de entrada

Arquivo `.txt` com **uma URL por linha**:

```txt
https://google.com/health
https://api.exemplo.com/status
api.interna.local/metrics
```

Regras:

* Linhas vazias são ignoradas
* Linhas iniciadas com `#` são ignoradas
* URLs sem esquema recebem `https://` automaticamente

---

## 📊 Exemplo de saída

```txt
TYPE         STATUS   HTTP   DOMAIN                IP              CONTENT-TYPE        SIZE     REQ(ms)  TIME(ms)  TITLE
---------------------------------------------------------------------------------------------------------------------------
healthcheck  OK       200    google.com.br         142.250.0.1     text/html           14.2KB        23        41  Google
status       OK       200    api.exemplo.com       10.0.0.1        application/json      512B        18        19  -
metrics      FAIL     -      api.interna.local     -               -                       0B        10        10  -
```

---

## 🧠 Conceitos importantes

### TYPE

Último segmento da URL:

| URL                   | TYPE          |
| --------------------- | ------------- |
| `/healthcheck`        | `healthcheck` |
| `/healthcheck/status` | `status`      |
| `/`                   | `root`        |

---

### REQ(ms)

Tempo até o servidor responder (latência).

---

### TIME(ms)

Tempo total da requisição, incluindo download do conteúdo.

---

### SIZE

Tamanho real baixado (body da resposta).

---

### TITLE

Extraído do HTML (`<title>`), quando disponível.

---

## 📈 Resumo final

```txt
Resumo
------------------------------
Total        : 3
Success      : 2
Failure      : 1
REQ average  : 17ms
TIME average : 23ms
```

---

## 🧪 Testes

Instale pytest:

```bash
pip install pytest
```

Execute:

```bash
pytest -q
```

---

## 🔍 Casos de uso

* Monitoramento rápido de APIs
* Diagnóstico de latência
* Verificação de ambientes (dev/sandbox/alpha/beta/prod)
* Debug de problemas DNS / rede / conteúdo

---

## ⚠️ Limitações

* Não separa tempo de DNS / TCP / TLS (tempo agregado)
* Download completo do body pode impactar performance em respostas grandes
* Execução sequencial (sem paralelismo)

---

## 🔮 Possíveis melhorias

* Execução paralela (threads/async)
* Retry automático
* Exportação para CSV/JSON
* Limite de download (`--max-size`)
* Breakdown detalhado de latência (DNS, TLS, TTFB)
* Agrupamento por TYPE

---

## 👤 Author

**André Argôlo**
CTO • Software Architect • DevOps

* 🌐 Website: [https://argolo.dev](https://argolo.dev)
* 🐙 GitHub: [https://github.com/argolo](https://github.com/argolo)

---

## 📜 Licença

MIT License
