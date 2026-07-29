---
name: openssl-reference
description: |
  Skill de referência completa para OpenSSL 3.x, com comandos úteis, exemplos práticos
  e guias de segurança para certificados X.509. Use quando precisar de informações
  sobre operações OpenSSL, conversão de formatos, inspeção de certificados ou
  implementação de wrappers seguros via subprocess Python.
---

# OpenSSL Reference — Skill de Referência

## Versão e Verificação

```bash
openssl version              # versão instalada
openssl version -a           # informações completas
which openssl                # localização do binário
```

## Inspecionar Certificados e CSRs

```bash
# Certificado PEM (.cer/.crt/.pem)
openssl x509 -in cert.pem -noout -text       # detalhes completos
openssl x509 -in cert.pem -noout -subject    # subject DN
openssl x509 -in cert.pem -noout -issuer     # issuer DN
openssl x509 -in cert.pem -noout -dates      # validade (notBefore/notAfter)
openssl x509 -in cert.pem -noout -serial     # número de série
openssl x509 -in cert.pem -noout -fingerprint -sha1   # thumbprint SHA1
openssl x509 -in cert.pem -noout -fingerprint -sha256 # thumbprint SHA256
openssl x509 -in cert.pem -noout -modulus | openssl md5  # modulus (para match)

# Certificado DER
openssl x509 -inform DER -in cert.der -noout -text

# CSR
openssl req -in cert.csr -noout -text        # detalhes da CSR
openssl req -in cert.csr -noout -subject     # subject da CSR
openssl req -in cert.csr -noout -modulus | openssl md5  # modulus da CSR

# Chave privada
openssl rsa -in key.pem -noout -modulus | openssl md5   # modulus da chave
openssl rsa -in key.pem -noout -check                   # integridade

# PFX/PKCS12
openssl pkcs12 -info -in cert.pfx -noout    # listagem (OpenSSL 3.x)
openssl pkcs12 -info -in cert.pfx -noout -passin pass:SENHA
```

## Gerar Chave e CSR

```bash
# RSA 2048
openssl req -new -newkey rsa:2048 -nodes \
  -keyout dominio.key -out dominio.csr \
  -subj "/CN=www.exemplo.com.br/O=Empresa/C=BR"

# RSA 4096
openssl req -new -newkey rsa:4096 -nodes \
  -keyout dominio.key -out dominio.csr \
  -subj "/CN=www.exemplo.com.br/O=Empresa/C=BR"

# Com SANs (via config file)
cat > san.cnf << EOF
[req]
default_bits = 2048
prompt = no
distinguished_name = dn
req_extensions = req_ext

[dn]
CN = www.exemplo.com.br
O = Empresa
C = BR

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = www.exemplo.com.br
DNS.2 = exemplo.com.br
EOF

openssl req -new -newkey rsa:2048 -nodes \
  -keyout dominio.key -out dominio.csr \
  -config san.cnf
```

## Conversões de Formato

```bash
# PEM → DER
openssl x509 -in cert.pem -outform DER -out cert.der

# DER → PEM
openssl x509 -inform DER -in cert.der -out cert.pem

# PFX → PEM (certificado + chave juntos)
openssl pkcs12 -in cert.pfx -out cert.pem -nodes

# PFX → apenas o certificado
openssl pkcs12 -in cert.pfx -clcerts -nokeys -out cert.cer

# PFX → apenas a chave privada
openssl pkcs12 -in cert.pfx -nocerts -nodes -out chave.key

# PFX → certificados da CA (cadeia)
openssl pkcs12 -in cert.pfx -cacerts -nokeys -out cadeia.cer

# Montar PFX a partir de cert + chave + cadeia
openssl pkcs12 -export \
  -out cert.pfx \
  -inkey chave.key \
  -in cert.cer \
  -certfile cadeia.cer \
  -name "meu-alias"

# PEM PKCS8 → PEM tradicional RSA
openssl rsa -in chave-pkcs8.pem -out chave-rsa.pem
```

## Verificação de Correspondência (Match)

Os três modulus devem ser iguais:
```bash
openssl rsa  -in dominio.key -noout -modulus | openssl md5
openssl req  -in dominio.csr -noout -modulus | openssl md5
openssl x509 -in cert.cer    -noout -modulus | openssl md5
```

## Verificar Cadeia

```bash
# Verificar cert contra CA
openssl verify -CAfile cadeia.pem cert.pem

# Verificar com CA raiz + intermediária separadas
openssl verify -CAfile ca-raiz.pem -untrusted ca-int.pem cert.pem

# Verificar certificado de um servidor
openssl s_client -connect host:443 -servername host
openssl s_client -connect host:443 -servername host < /dev/null 2>/dev/null | \
  openssl x509 -noout -text
```

## Wrapper Python Seguro (subprocess)

```python
import subprocess
import tempfile
import os
from pathlib import Path

def run_openssl(*args, input_data: bytes = None, timeout: int = 30) -> dict:
    """Executa openssl de forma segura e retorna stdout/stderr."""
    cmd = ["openssl", *args]
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout.decode("utf-8", errors="replace"),
            "stderr": result.stderr.decode("utf-8", errors="replace"),
            "returncode": result.returncode,
            "command_display": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        raise ValueError(f"Operação OpenSSL excedeu timeout de {timeout}s")
    except FileNotFoundError:
        raise ValueError("openssl não encontrado no PATH")

# Uso com arquivo temporário (nunca passar dados sensíveis pela linha de comando)
def inspect_cert(cert_bytes: bytes) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
        f.write(cert_bytes)
        tmp = f.name
    try:
        return run_openssl("x509", "-in", tmp, "-noout", "-text")
    finally:
        os.unlink(tmp)
```

## Segurança — Boas Práticas

### O que NUNCA fazer
```python
# ❌ NUNCA: injeção de comandos
subprocess.run(f"openssl x509 -in {filename}", shell=True)

# ❌ NUNCA: dados sensíveis na linha de comando
subprocess.run(["openssl", "pkcs12", "-passin", f"pass:{password}"])
```

### O que SEMPRE fazer
```python
# ✅ Sempre: lista de argumentos
subprocess.run(["openssl", "x509", "-in", filename, "-noout", "-text"])

# ✅ Para senhas: usar arquivo temporário ou stdin
subprocess.run(
    ["openssl", "pkcs12", "-in", pfx_file, "-nodes", "-passin", "stdin"],
    input=password.encode(),
    capture_output=True,
)

# ✅ Sempre: timeout
subprocess.run([...], timeout=30)

# ✅ Sempre: capture_output para não vazar ao terminal
subprocess.run([...], capture_output=True)
```

## Extensões e OIDs Comuns

| OID | Nome | Descrição |
|-----|------|-----------|
| 2.5.29.17 | subjectAltName | SANs (DNS, IP, email) |
| 2.5.29.19 | basicConstraints | CA: TRUE/FALSE |
| 2.5.29.15 | keyUsage | Uso da chave |
| 2.5.29.37 | extendedKeyUsage | TLS Server Auth, Client Auth |
| 1.3.6.1.5.5.7.1.1 | authorityInfoAccess | OCSP e CA Issuers URL |
| 2.5.29.31 | cRLDistributionPoints | URL da CRL |
| 2.5.29.32 | certificatePolicies | OIDs de política (DV/OV/EV) |

## Formatos de Arquivo

| Extensão | Formato | Conteúdo |
|----------|---------|----------|
| `.pem` | PEM (base64) | Cert, chave, CSR ou cadeia |
| `.cer` | PEM ou DER | Certificado |
| `.crt` | PEM ou DER | Certificado |
| `.der` | DER (binário) | Certificado |
| `.pfx` / `.p12` | PKCS#12 | Cert + chave + cadeia |
| `.csr` | PEM | Certificate Signing Request |
| `.key` | PEM | Chave privada |
| `.jks` | Java KeyStore | KeyStore Java (não OpenSSL nativo) |
