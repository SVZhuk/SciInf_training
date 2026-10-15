# Testing the API from the terminal with HTTPie

Swagger UI (`/docs`) is a FastAPI bonus. Many real APIs have no UI at all, and then you test
them from the command line. [HTTPie](https://httpie.io/docs/cli) is curl with readable syntax:
JSON by default, colored output, and request items that look like the data you send.

## 1. Setup

```bash
uv run uvicorn app.main:app --reload   # terminal 1: start the API
uv tool install httpie                 # terminal 2: once, puts `http` on PATH
http --version                         # 3.2.4 or newer
```

Any way of starting the API works here, since HTTPie just talks to whatever is listening on
`:8000`: `docker compose --profile prod up --build` (see [README.md](../README.md)) works just
as well as `uv run uvicorn ...`.

No install? Prefix every command with `uvx --from httpie`, e.g. `uvx --from httpie http :8000/health`.
HTTPie is a tool, not a project dependency, so it is not in `pyproject.toml`.

## 2. Syntax in one table

| You type | Meaning |
|---|---|
| `http :8000/api/v1/samples` | `GET http://localhost:8000/api/v1/samples` (`:port` is localhost shorthand) |
| `http POST :8000/api/v1/samples ...` | Method goes before the URL; GET is the default, POST if you send data |
| `name=TP53` | JSON body field, string: `{"name": "TP53"}` |
| `count:=5`, `tags:='["a"]'` | JSON body field, raw JSON (numbers, booleans, lists) |
| `organism==homo_sapiens` | Query parameter: `?organism=homo_sapiens` |
| `X-API-Key:secret` | Request header |

| Flag | Shows |
|---|---|
| (none) | Response headers + body in a terminal; body only when piped |
| `-v` | The request you sent and the response |
| `-h` / `-b` | Response headers only / body only |
| `--offline` | Builds and prints the request without sending it |
| `--check-status` | Exit code 3 on 3xx, 4 on 4xx, 5 on 5xx (for scripts) |

## 3. Walk through every endpoint

### Health check

```bash
http :8000/health
```
```json
{"status": "ok"}
```

### Create: POST, 201 + Location

```bash
http -v POST :8000/api/v1/samples name=TP53-exon5 organism=homo_sapiens sequence=taccTGCCGG
```

```
POST /api/v1/samples HTTP/1.1
Content-Type: application/json
...
{"name": "TP53-exon5", "organism": "homo_sapiens", "sequence": "taccTGCCGG"}

HTTP/1.1 201 Created
location: /api/v1/samples/5f083a2f-4166-4f14-8435-caaf159fd12d
...
{
    "name": "TP53-exon5",
    "organism": "homo_sapiens",
    "sequence": "TACCTGCCGG",
    "id": "5f083a2f-4166-4f14-8435-caaf159fd12d",
    "created_at": "2026-09-23T19:11:25.502912Z",
    "length": 10,
    "gc_content": 0.7
}
```

Things to point out:

- `-v` shows that HTTPie turned `key=value` pairs into a JSON body and set `Content-Type`.
- `201 Created` plus a `location` header: where the new resource lives.
- The server normalized the sequence to uppercase and computed `length` and `gc_content`.
  We never sent `id` or `created_at`: the server owns them.

### Keep the id in a variable

Copy it from the `location` header, or capture it:

```bash
# bash (needs jq)
ID=$(http -b POST :8000/api/v1/samples name=BRCA1-exon11 organism=homo_sapiens sequence=ATGCGC | jq -r .id)
```

```powershell
# PowerShell
$ID = (http -b POST :8000/api/v1/samples name=BRCA1-exon11 organism=homo_sapiens sequence=ATGCGC | ConvertFrom-Json).id
```

Use `$ID` in the commands below (same syntax in both shells).

### List: filter and paginate with query parameters

```bash
http :8000/api/v1/samples organism==homo_sapiens limit==1 offset==0
```
```json
{"items": [{"name": "TP53-exon5", "...": "..."}], "total": 2, "limit": 1, "offset": 0}
```

`total` tells the client how many pages exist; `limit` and `offset` choose one.

### Read one: hypermedia links

```bash
http :8000/api/v1/samples/$ID
```
```json
{
    "name": "BRCA1-exon11",
    "...": "...",
    "_links": {
        "self":       {"href": "http://localhost:8000/api/v1/samples/<id>", "method": "GET"},
        "update":     {"href": "http://localhost:8000/api/v1/samples/<id>", "method": "PATCH"},
        "delete":     {"href": "http://localhost:8000/api/v1/samples/<id>", "method": "DELETE"},
        "collection": {"href": "http://localhost:8000/api/v1/samples", "method": "GET"}
    }
}
```

The response tells you what you can do next. A client follows `_links.delete` (method + href)
instead of building the URL itself: `http DELETE <href from _links.delete>`.

### Partial update: PATCH

```bash
http PATCH :8000/api/v1/samples/$ID name=BRCA1-exon11-v2
```

Only `name` changes; everything else stays as it was.

### Delete: 204, no body

```bash
http DELETE :8000/api/v1/samples/$ID
```
```
HTTP/1.1 204 No Content
```

## 4. Error cases: make the API say no

| Command | Status | Why |
|---|---|---|
| `http POST :8000/api/v1/samples name=bad organism=homo_sapiens sequence=ATGXYZ` | 422 | Not a DNA alphabet |
| `http POST :8000/api/v1/samples name=bad organism=alien sequence=ACGT` | 422 | Not an allowed organism |
| `http :8000/api/v1/samples limit==500` | 422 | `limit` is capped at 100 |
| `http :8000/api/v1/samples/not-a-uuid` | 422 | Path id must be a UUID |
| Run the same POST twice with the same `name` | 409 | Duplicate name |
| `http :8000/api/v1/samples/00000000-0000-0000-0000-000000000000` | 404 | No such sample |

Validation errors (422) say exactly which field failed and why:

```json
{"detail": [{
    "type": "value_error",
    "loc": ["body", "sequence"],
    "msg": "Value error, invalid nucleotides: ['X', 'Y', 'Z']",
    "input": "ATGXYZ"
}]}
```

`loc` says where the problem is: `body`, `query` or `path`, then the field name.
Business errors are simpler: `{"detail": "Sample name already exists"}` (409),
`{"detail": "Sample not found"}` (404).

## 5. Useful tricks

**Preview a request without sending it**, handy while learning the syntax:

```bash
http --offline POST :8000/api/v1/samples name=x organism=mus_musculus sequence=ACGT
```

**Fail a script on an error status**: HTTPie exits 0 even on 404 unless you ask:

```bash
http --check-status :8000/api/v1/samples/00000000-0000-0000-0000-000000000000
echo $?   # 4 (4xx); in PowerShell: $LASTEXITCODE
```

**Send a JSON file** when the body is large:

```bash
http POST :8000/api/v1/samples < sample.json
```

```powershell
Get-Content -Raw sample.json | http POST :8000/api/v1/samples
```

**Sessions** remember headers and cookies between calls. Useful once the API needs a key
(README exercise 2):

```bash
http --session=demo :8000/api/v1/samples X-API-Key:secret   # stored
http --session=demo :8000/api/v1/samples                     # sent again automatically
```

**PowerShell quoting**: raw JSON with inner quotes (`tags:='["a"]'`) can lose its quotes in
Windows PowerShell 5. Prefer a JSON file there, or use PowerShell 7.3+.

## 6. Exploring an API with no Swagger UI

1. Try `http :8000/openapi.json`. Many frameworks publish the machine-readable spec even
   without a UI.
2. Start from a resource you know and follow its `_links`.
3. Send something deliberately wrong and read the 422 `detail`: it lists required fields and
   allowed values (for example, all valid `organism` values).
