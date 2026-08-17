#!/usr/bin/env node
/**
 * Bridge entre o backend Python (DinamoJsProvider) e o SDK JS oficial da
 * Dinamo (@dinamonetworks/hsm-dinamo, verificado contra a v4.27.0 instalada
 * em node_modules/). Uma chamada de processo por ação:
 *
 *   node hsm-helper.js <gen-key|gen-csr|import-cert|export-pfx|search>
 *
 * Request (JSON) via stdin, response (JSON) via stdout. Protocolo completo
 * em specs/001-integracao-hsm-dinamo/contracts/hsm-node-bridge.md.
 *
 * O SDK não expõe uma chave própria de "nome do certificado" ligada
 * automaticamente à chave — cada objeto no HSM tem seu próprio nome. Por
 * isso o certificado associado à chave `label` é sempre gravado sob o nome
 * `${label}.cert`, evitando colisão de nome com o objeto da chave.
 *
 * O SDK também não expõe exportação direta de PFX/PKCS#12 nem validação de
 * que um certificado importado corresponde à chave alvo — por isso o PFX é
 * montado aqui (node-forge) a partir de key.exportPKCS8 + key.exportCertClearText,
 * e a checagem de correspondência de chave pública (FR-006) é feita aqui
 * antes de chamar key.importCertificate.
 */
import { hsm } from '@dinamonetworks/hsm-dinamo';
import forge from 'node-forge';

const ERROR_CODES = new Set([
  'NOT_FOUND', 'ALREADY_EXISTS', 'KEY_MISMATCH', 'NOT_EXPORTABLE', 'CONN_FAILED', 'TIMEOUT',
]);

const CERT_SUFFIX = '.cert';

let responded = false;

/**
 * O SDK lança alguns erros de validação (ex.: host/porta ausente) de forma
 * síncrona dentro de um executor `async` de Promise — isso vira uma promise
 * rejeitada sem ninguém escutando (unhandled rejection) em vez de um reject()
 * chamado corretamente, então o `try/catch` ao redor do `await hsm.connect()`
 * não pega. Sem esses handlers globais o processo Node encerra sozinho e
 * despeja o stack trace cru no stdout/stderr, quebrando o protocolo JSON.
 */
process.on('unhandledRejection', (reason) => {
  if (!responded) respondFail(reason, reason && reason.code);
  process.exit(1);
});
process.on('uncaughtException', (err) => {
  if (!responded) respondFail(err, err && err.code);
  process.exit(1);
});

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

function respondOk(data) {
  responded = true;
  process.stdout.write(JSON.stringify({ ok: true, data }));
}

function respondFail(error, code) {
  responded = true;
  const safeCode = ERROR_CODES.has(code) ? code : 'CONN_FAILED';
  process.stdout.write(JSON.stringify({
    ok: false,
    error: (error && error.message) || String(error),
    code: safeCode,
  }));
  process.exitCode = 1;
}

function taggedError(message, code) {
  const err = new Error(message);
  err.code = code;
  return err;
}

/** Traduz um HsmError (errorCode numérico do firmware) pro nosso vocabulário de códigos. */
function mapHsmError(e, { accessDeniedAs = 'CONN_FAILED', fallback = 'CONN_FAILED' } = {}) {
  const code = e && e.errorCode;
  if (code === 5022) return 'ALREADY_EXISTS';   // ERR_OBJ_ALREADY_EXISTS
  if (code === 5004 || code === 5023) return 'NOT_FOUND'; // ERR_CANNOT_OPEN_OBJ / ERR_INVALID_OBJ_NAME
  if (code === 5002) return accessDeniedAs;     // ERR_ACCESS_DENIED
  if (code === 5001) return 'CONN_FAILED';      // ERR_NET_FAIL
  return fallback;
}

function algorithmFor(keyType) {
  const RSA = hsm.enums.RSA_ASYMMETRIC_KEYS;
  return { rsa2048: RSA.ALG_RSA_2048, rsa4096: RSA.ALG_RSA_4096 }[keyType] || RSA.ALG_RSA_2048;
}

function buildDn(params) {
  const dn = { CN: params.cn };
  if (params.org) dn.O = params.org;
  if (params.ou) dn.OU = [params.ou];
  if (params.country) dn.C = params.country;
  if (params.state) dn.ST = params.state;
  if (params.locality) dn.L = params.locality;
  if (params.email) dn.E = params.email;
  return dn;
}

function derToPem(der, label) {
  const lines = der.toString('base64').match(/.{1,64}/g) || [];
  return `-----BEGIN ${label}-----\n${lines.join('\n')}\n-----END ${label}-----\n`;
}

function pemToDer(pem) {
  const b64 = pem.replace(/-----BEGIN [^-]+-----/, '').replace(/-----END [^-]+-----/, '').replace(/\s+/g, '');
  return Buffer.from(b64, 'base64');
}

function toForgeBytes(buffer) {
  return buffer.toString('binary');
}

function certFromDer(der) {
  return forge.pki.certificateFromAsn1(forge.asn1.fromDer(toForgeBytes(der)));
}

async function genKey(conn, params) {
  try {
    await conn.key.create(params.label, algorithmFor(params.key_type), true);
  } catch (e) {
    throw taggedError(e.message, mapHsmError(e));
  }
  return { label: params.label, key_type: params.key_type };
}

async function genCsr(conn, params) {
  let der;
  try {
    der = await conn.key.generatePKCS10(params.label, buildDn(params));
  } catch (e) {
    throw taggedError(e.message, mapHsmError(e, { fallback: 'NOT_FOUND' }));
  }
  return { csr_pem: derToPem(der, 'CERTIFICATE REQUEST') };
}

async function importCert(conn, params) {
  const certName = `${params.label}${CERT_SUFFIX}`;
  const certDer = pemToDer(params.cert_pem);

  let keyPubDer;
  try {
    keyPubDer = await conn.key.exportAsymmetricPub(params.label, true);
  } catch (e) {
    throw taggedError(e.message, mapHsmError(e, { fallback: 'NOT_FOUND' }));
  }

  let certPubDer;
  try {
    const cert = certFromDer(certDer);
    const spkiAsn1 = forge.pki.publicKeyToAsn1(cert.publicKey);
    certPubDer = Buffer.from(forge.asn1.toDer(spkiAsn1).getBytes(), 'binary');
  } catch (e) {
    throw taggedError(`Certificado inválido: ${e.message}`, 'KEY_MISMATCH');
  }
  if (!keyPubDer.equals(certPubDer)) {
    throw taggedError('A chave pública do certificado não corresponde à chave no HSM.', 'KEY_MISMATCH');
  }

  try {
    await conn.key.importCertificate(certName, certDer);
  } catch (e) {
    throw taggedError(e.message, mapHsmError(e));
  }
  return { label: params.label, imported: true };
}

async function exportPfx(conn, params) {
  const certName = `${params.label}${CERT_SUFFIX}`;

  let keyDer;
  try {
    keyDer = await conn.key.exportPKCS8(params.label, params.password);
  } catch (e) {
    throw taggedError(e.message, mapHsmError(e, { accessDeniedAs: 'NOT_EXPORTABLE', fallback: 'NOT_FOUND' }));
  }

  let certDer;
  try {
    certDer = await conn.key.exportCertClearText(certName);
  } catch (e) {
    throw taggedError(e.message, mapHsmError(e, { fallback: 'NOT_FOUND' }));
  }

  const encryptedInfoAsn1 = forge.asn1.fromDer(toForgeBytes(keyDer));
  const privateKeyInfoAsn1 = forge.pki.decryptPrivateKeyInfo(encryptedInfoAsn1, params.password);
  if (!privateKeyInfoAsn1) {
    throw taggedError('Não foi possível decodificar a chave privada exportada do HSM.', 'CONN_FAILED');
  }
  const privateKey = forge.pki.privateKeyFromAsn1(privateKeyInfoAsn1);
  const certificate = certFromDer(certDer);

  const p12Asn1 = forge.pkcs12.toPkcs12Asn1(privateKey, certificate, params.password, { algorithm: '3des' });
  const p12Der = Buffer.from(forge.asn1.toDer(p12Asn1).getBytes(), 'binary');
  return { pfx_base64: p12Der.toString('base64') };
}

async function search(conn, params) {
  const query = (params.query || '').toLowerCase();
  const names = await conn.management.listObjs();
  const keyNames = names.filter((n) => !n.endsWith(CERT_SUFFIX));
  const certNames = new Set(names.filter((n) => n.endsWith(CERT_SUFFIX)));

  const results = [];
  for (const name of keyNames) {
    if (query && !name.toLowerCase().includes(query)) continue;

    let keyType = '';
    try {
      const info = await conn.management.getObjectInfo(name);
      keyType = info.type || '';
    } catch (_e) {
      // objeto listado mas sem info legível (ex.: tipo não suportado) — segue sem key_type
    }

    const certName = `${name}${CERT_SUFFIX}`;
    const hasCertificate = certNames.has(certName);
    let cn = null;
    let notAfter = null;
    if (hasCertificate) {
      try {
        const cert = certFromDer(await conn.key.exportCertClearText(certName));
        const cnField = cert.subject.getField('CN');
        cn = cnField ? cnField.value : null;
        notAfter = cert.validity.notAfter.toISOString();
      } catch (_e) {
        // certificado presente mas ilegível — resultado ainda aparece, só sem cn/validade
      }
    }
    results.push({ label: name, key_type: keyType, has_certificate: hasCertificate, cn, not_after: notAfter });
  }
  return { results };
}

const ACTIONS = {
  'gen-key': genKey,
  'gen-csr': genCsr,
  'import-cert': importCert,
  'export-pfx': exportPfx,
  search,
};

async function main() {
  const action = process.argv[2];
  const handler = ACTIONS[action];
  if (!handler) {
    return respondFail(`Ação desconhecida: ${action}`, 'CONN_FAILED');
  }

  let request;
  try {
    request = JSON.parse(await readStdin());
  } catch (e) {
    return respondFail(`Request JSON inválido: ${e.message}`, 'CONN_FAILED');
  }

  const { connection, params } = request;
  let conn;
  try {
    conn = await hsm.connect({
      host: connection.host,
      port: connection.port ? Number(connection.port) : undefined,
      authUsernamePassword: { username: connection.username, password: connection.password },
    });
  } catch (e) {
    return respondFail(`Falha ao conectar no HSM: ${e.message}`, 'CONN_FAILED');
  }

  try {
    const data = await handler(conn, params || {});
    respondOk(data);
  } catch (e) {
    respondFail(e, e.code);
  } finally {
    try { await conn.disconnect(); } catch (_e) { /* conexão já pode estar fechada */ }
  }
}

main();
