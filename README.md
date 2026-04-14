# Checking Health

**Checking Health** is a command-line tool for performing HTTP/HTTPS endpoint health checks with clean, real-time, and highly readable output.

It helps you quickly validate APIs, services, and environments with useful diagnostics like latency, response size, content type, and more.

---

## ✨ Features

* ⚡ Real-time execution (results printed as they complete)
* 🎯 Endpoint identification via URL path (`TYPE`)
* 📊 Rich metrics per request:

  * Status (OK / FAIL)
  * HTTP status code
  * Domain & IP
  * Content-Type
  * Response size
  * Request time (`REQ`)
  * Total time (`TIME`)
  * HTML `<title>` (when available)
* 🎨 Clean and colorful terminal output
* 📈 Summary with aggregated metrics
* 🧪 Fully testable with `pytest`
* 📦 Distributed via PyPI

---

## 📦 Installation

Install directly from PyPI:

```bash
pip install checking-health
```

🔗 https://pypi.org/project/checking-health

---

## ▶️ Usage

```bash
checking-health endpoints.txt --timeout 3
```

---

## 📄 Input File Format

Provide a `.txt` file with one endpoint per line:

```txt
# success example
google.com

# failure example
google.comm

https://api.example.com/status
```

### Rules

* Empty lines are ignored
* Lines starting with `#` are ignored
* URLs without scheme default to `https://`

---

## 📊 Example Output

```txt
TYPE         STATUS   HTTP   DOMAIN                                   IP              CONTENT-TYPE        SIZE   REQ(ms)  TIME(ms)  TITLE
-------------------------------------------------------------------------------------------------------------------------------
health       OK       200    google.com                               142.250.191.78  text/html           17.4KB       31        53  Google
status       FAIL     -      google.comm                              -               -                    0B          14        14  -

Summary
------------------------------
Total        : 2
Success      : 1
Failure      : 1
REQ average  : 22ms
TIME average : 33ms
```

---

## 🧠 Concepts

### TYPE

Derived from the last segment of the URL path:

| URL                   | TYPE          |
| --------------------- | ------------- |
| `/healthcheck`        | `healthcheck` |
| `/healthcheck/status` | `status`      |
| `/`                   | `root`        |

---

### REQ(ms)

Time until the server starts responding (latency).

---

### TIME(ms)

Total time including response download.

---

### SIZE

Actual size of the response body.

---

### TITLE

Extracted from HTML responses (`<title>` tag), when available.

---

## 🔍 Use Cases

* API health validation
* Deployment smoke tests
* Environment verification (dev/staging/prod)
* Quick debugging of network or DNS issues
* Bulk endpoint checking

---

## ⚠️ Limitations

* Does not break down DNS / TCP / TLS timings
* Downloads full response body (can impact large responses)
* Runs sequentially (no parallel execution)

---

## 🧪 Testing

Install pytest:

```bash
pip install pytest
```

Run tests:

```bash
pytest -q
```

---

## 👤 Author

**André Argôlo**
CTO • Software Architect • DevOps

* 🌐 Website: [https://argolo.dev](https://argolo.dev)
* 🐙 GitHub: [https://github.com/argolo](https://github.com/argolo)

---

## 📜 Licença

MIT License
