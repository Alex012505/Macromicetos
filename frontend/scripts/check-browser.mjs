/** Browser QA against the running local application. Writes only marked QA data.
 * Reuses the same two artificial occurrences on later runs; never seeds on npm test.
 */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium, expect } from '@playwright/test';

if (!process.argv.includes('--seed-local')) throw new Error('Esta prueba modifica datos ficticios locales. Usa --seed-local explícitamente.');
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const python = join(root, 'Backend/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const fixtureScript = join(root, 'Backend/tests/browser_fixture.py');
const fixture = command => execFileSync(python, [fixtureScript, command], { cwd: root, encoding: 'utf8', windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
const base = 'http://127.0.0.1:5173/Macromicetos/';
const output = join(root, 'frontend/test-results/web-local');
await mkdir(output, { recursive: true });
const report = { checks: [], pageErrors: [], serverErrors: [], externalFailures: [], status: 'running' };
let browser; let page;
function passed(message) { report.checks.push(message); console.log('OK:', message); }
async function login(account) {
  await page.goto(base + '#/dashboard');
  await page.getByLabel('Correo electrónico').fill(account.email);
  await page.locator('input[name="password"]').fill(account.password);
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Cerrar sesión', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Registro de macromicetos.' })).toBeVisible();
}
async function logout() {
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Iniciar sesión', exact: true })).toBeVisible();
}
async function register(account) {
  await page.goto(base);
  await page.getByRole('button', { name: 'Crear una cuenta de visitante', exact: true }).click();
  await page.getByLabel('Nombre', { exact: true }).fill(account.firstName);
  await page.getByLabel('Apellido', { exact: true }).fill(account.lastName);
  await page.getByLabel('Correo electrónico').fill(account.email);
  await page.locator('input[name="password"]').fill(account.password);
  await page.getByLabel('Confirmar contraseña').fill('No-coincide-123');
  await page.getByRole('button', { name: 'Crear cuenta', exact: true }).click();
  await expect(page.getByText('Las contraseñas no coinciden.', { exact: true })).toBeVisible();
  await page.getByLabel('Confirmar contraseña').fill(account.password);
  await page.getByRole('button', { name: 'Crear cuenta', exact: true }).click();
  await expect(page.getByText(/Cuenta creada como visitante/)).toBeVisible();
}
async function createRecord(account, number, hasTaxon) {
  await page.getByRole('button', { name: 'Registros de campo', exact: true }).click();
  await page.getByRole('button', { name: 'Nuevo registro', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Registrar un nuevo hallazgo' });
  if (!hasTaxon) {
    await dialog.getByRole('button', { name: 'Añadir especie nueva', exact: true }).click();
    const species = page.getByRole('dialog', { name: 'Añadir especie nueva al catálogo' });
    await species.getByLabel('Nombre científico', { exact: false }).fill('Prueba artificialis');
    await species.getByLabel('Nombre común', { exact: true }).fill('PRUEBA ARTIFICIAL - no es una especie real');
    await species.getByLabel('Notas taxonómicas', { exact: true }).fill('DATO ARTIFICIAL para probar el aplicativo. No es un taxón científico real ni evidencia biológica.');
    await species.getByRole('button', { name: 'Añadir especie', exact: true }).click();
    await expect(species).not.toBeVisible();
  } else {
    await dialog.getByLabel(/^Especie o taxón/).selectOption({ label: 'Prueba artificialis · PRUEBA ARTIFICIAL - no es una especie real' });
  }
  await dialog.getByLabel('Identificador externo del hallazgo', { exact: true }).fill(`PRUEBA-WEB-0${number}`);
  await dialog.getByLabel('Identificado por', { exact: true }).fill('Persona ficticia de QA');
  await dialog.getByLabel('Fecha de identificación', { exact: true }).fill('2026-10-24');
  await dialog.getByLabel('Sustrato', { exact: true }).fill('Sustrato ficticio (PRUEBA)');
  await dialog.getByLabel('Notas del hallazgo', { exact: true }).fill(`REGISTRO ARTIFICIAL ${number}. Solo pruebas de software; NO es evidencia científica ni de presencia de una especie. Foto ilustrativa, no tomada en el sitio ficticio.`);
  const picker = dialog.getByLabel('Seleccionar fotografías', { exact: true });
  await picker.setInputFiles({ name: 'archivo-invalido.txt', mimeType: 'text/plain', buffer: Buffer.from('PRUEBA') });
  await expect(dialog.getByText(/usa JPG, PNG o WebP/)).toBeVisible();
  await picker.setInputFiles(join(root, `frontend/public/images/${number === 1 ? 'pleurotus' : 'trametes'}.jpg`));
  await expect(dialog.getByLabel('Fotógrafo/a', { exact: true })).toBeVisible();
  await dialog.getByLabel('Fotógrafo/a', { exact: true }).fill(number === 1 ? 'Jean-Pol GRANDMONT (imagen ilustrativa)' : 'National Park Service (imagen ilustrativa)');
  await dialog.getByLabel('Titular de derechos', { exact: true }).fill(number === 1 ? 'Jean-Pol GRANDMONT' : 'National Park Service');
  await dialog.getByLabel(/^Licencia o permiso de uso/).selectOption(number === 1 ? 'https://creativecommons.org/licenses/by/3.0/' : 'https://creativecommons.org/publicdomain/zero/1.0/');
  await dialog.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(dialog.getByText('Paso 2 de 4', { exact: false })).toBeVisible();
  await dialog.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(dialog.getByText('Paso 2 de 4', { exact: false })).toBeVisible();
  await dialog.getByRole('button', { name: 'Coordenadas', exact: true }).click();
  await dialog.getByLabel('Localidad o descripción del sitio', { exact: false }).fill(`SITIO ARTIFICIAL ${number} - no corresponde a un muestreo real`);
  await dialog.getByLabel('Departamento', { exact: false }).fill(number === 1 ? 'Meta' : 'Casanare');
  await dialog.getByLabel('Municipio', { exact: true }).fill('Municipio ficticio (PRUEBA)');
  await dialog.getByLabel('Hábitat', { exact: true }).fill('Hábitat ficticio (PRUEBA)');
  await dialog.getByLabel('Latitud', { exact: true }).fill('91');
  await dialog.getByLabel('Longitud', { exact: true }).fill(number === 1 ? '-73.63' : '-72.40');
  await dialog.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(dialog.getByText('Paso 2 de 4', { exact: false })).toBeVisible();
  await dialog.getByLabel('Latitud', { exact: true }).fill(number === 1 ? '4.14' : '5.30');
  await dialog.getByLabel('Incertidumbre de coordenadas (m)', { exact: true }).fill('0');
  await dialog.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect(dialog.getByText('Paso 3 de 4', { exact: false })).toBeVisible();
  await dialog.getByLabel('Fecha de observación / salida', { exact: false }).fill('2026-10-24');
  await dialog.getByLabel('Código de campo', { exact: true }).fill(`PRUEBA-WEB-0${number}`);
  await dialog.getByRole('button', { name: 'Continuar', exact: true }).click();
  await dialog.getByRole('button', { name: 'Añadir medida ambiental', exact: true }).click();
  await dialog.getByLabel('Variable', { exact: false }).fill('Temperatura ficticia');
  await dialog.getByLabel('Valor', { exact: false }).fill('0');
  await dialog.getByLabel('Unidad', { exact: true }).fill('°C');
  await dialog.getByRole('button', { name: 'Guardar registro', exact: true }).click();
  await expect(dialog).not.toBeVisible({ timeout: 20000 });
  await expect(page.getByText('Registro enviado al servidor.', { exact: true })).toBeVisible();
  passed(`Formulario completo: registro artificial ${number}, foto, validaciones, coordenadas y medida cero`);
}

try {
  const health = await fetch('http://127.0.0.1:5173/api/health').then(response => response.json());
  assert.equal(health.database, 'postgresql');
  fixture('prepare');
  const data = JSON.parse(await readFile(join(root, 'Backend/data/web-test-accounts.json'), 'utf8'));
  browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'es-CO', acceptDownloads: true });
  page = await context.newPage(); page.setDefaultTimeout(15000);
  page.on('pageerror', error => report.pageErrors.push(error.message));
  page.on('response', response => { if (response.url().startsWith('http://127.0.0.1:5173/api/') && response.status() >= 500) report.serverErrors.push({ url: response.url(), status: response.status() }); });
  page.on('requestfailed', request => { if (!request.url().startsWith('http://127.0.0.1:5173/')) report.externalFailures.push(request.url().split('?')[0]); });
  await page.goto(base + '#/usuarios');
  await expect(page.getByRole('button', { name: 'Iniciar sesión', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Gestión de usuarios', exact: true })).toHaveCount(0);
  await page.getByLabel('Correo electrónico').fill(data.accounts.viewer.email);
  await page.locator('input[name="password"]').fill('incorrecta-para-prueba');
  await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
  await expect(page.locator('.notice.error')).toBeVisible();
  passed('Acceso protegido y rechazo visible de credenciales incorrectas');
  for (const role of ['analyst', 'curator', 'viewer']) {
    if (!data.accounts[role].registered) await register(data.accounts[role]);
  }
  passed('Registro de cuentas y validación de confirmación de contraseña');
  await login(data.accounts.admin);
  await page.getByRole('button', { name: 'Gestión de usuarios', exact: true }).click();
  for (const role of ['analyst', 'curator']) {
    const account = data.accounts[role];
    const row = page.getByRole('row').filter({ hasText: account.email });
    await row.getByRole('button', { name: /Editar rol/ }).click();
    const modal = page.getByRole('dialog', { name: `Perfil de ${account.firstName} ${account.lastName}` });
    await modal.getByLabel(/^Perfil académico/).selectOption(role);
    await modal.getByRole('button', { name: 'Guardar perfil', exact: true }).click();
    await expect(modal).not.toBeVisible();
  }
  passed('Administrador asigna investigador y curador desde Gestión de usuarios');
  await logout(); await login(data.accounts.analyst);
  await expect(page.getByRole('button', { name: 'Gestión de usuarios', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /^Curaduría/ })).toHaveCount(0);
  for (const number of [1, 2]) {
    if (!data.records.some(record => record.externalId === `PRUEBA-WEB-0${number}`)) {
      await createRecord(data.accounts.analyst, number, number === 2 || data.records.length > 0);
    }
  }
  await page.getByRole('button', { name: 'Registros de campo', exact: true }).click();
  await page.getByLabel('Buscar registros').fill('Prueba artificialis');
  await expect(page.locator('tbody tr')).toHaveCount(2);
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Exportar CSV', exact: true }).click();
  const download = await downloadEvent;
  await download.saveAs(join(output, 'registros-artificiales.csv'));
  assert.match(await readFile(join(output, 'registros-artificiales.csv'), 'utf8'), /Prueba artificialis/);
  passed('Búsqueda de los dos registros y descarga CSV desde el navegador');
  await page.screenshot({ path: join(output, 'registros.png'), fullPage: true });
  await page.locator('tbody tr').filter({ hasText: 'Meta' }).getByRole('button', { name: 'Abrir Prueba artificialis', exact: true }).click();
  const edit = page.getByRole('dialog', { name: 'Editar registro de campo' });
  await edit.getByLabel('Notas del hallazgo', { exact: true }).fill(`REGISTRO ARTIFICIAL 1. Edición comprobada desde el navegador (${new Date().toISOString()}). NO es evidencia científica; foto ilustrativa, no tomada en el sitio ficticio.`);
  for (let step = 0; step < 3; step++) await edit.getByRole('button', { name: 'Continuar', exact: true }).click();
  await edit.getByRole('button', { name: 'Guardar cambios', exact: true }).click();
  await expect(edit).not.toBeVisible({ timeout: 20000 });
  await page.getByRole('button', { name: 'Catálogo de especies', exact: true }).click();
  await page.locator('.species-card').filter({ hasText: 'Prueba artificialis' }).click();
  await expect(page.getByRole('heading', { name: 'Prueba artificialis', exact: true })).toBeVisible();
  const pdfEvent = page.waitForEvent('download', { timeout: 45000 });
  await page.getByRole('button', { name: 'Descargar ficha PDF', exact: true }).click();
  const pdf = await pdfEvent; await pdf.saveAs(join(output, 'ficha-artificial.pdf'));
  assert.equal((await readFile(join(output, 'ficha-artificial.pdf'))).subarray(0, 4).toString(), '%PDF');
  await expect(page.getByText('Ficha PDF descargada con los datos y fotografías disponibles.', { exact: true })).toBeVisible();
  const excelEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Exportar Excel', exact: true }).click();
  const excel = await excelEvent; await excel.saveAs(join(output, 'ficha-artificial.xlsx'));
  assert.equal((await readFile(join(output, 'ficha-artificial.xlsx'))).subarray(0, 2).toString(), 'PK');
  passed('Edición del hallazgo sin duplicar fotos y descargas PDF con imágenes y Excel');
  await page.reload();
  await expect(page.getByRole('button', { name: 'Iniciar sesión', exact: true })).toBeVisible();
  await login(data.accounts.analyst);
  await page.getByRole('button', { name: 'Registros de campo', exact: true }).click();
  await expect(page.locator('tbody tr')).toHaveCount(2);
  passed('Los datos persisten tras recargar y volver a iniciar sesión');
  await logout(); await login(data.accounts.curator);
  await page.getByRole('button', { name: /^Curaduría/ }).click();
  await expect(page.getByRole('heading', { name: 'Revisión y curaduría.' })).toBeVisible();
  const pending = page.locator('.review-list-item').filter({ hasText: 'Prueba artificialis' }).filter({ hasText: 'Meta' });
  await expect(pending).toHaveCount(1);
  await pending.click();
  await page.getByRole('button', { name: 'Solicitar ajustes', exact: true }).click();
  await expect(page.getByText('Explica los ajustes necesarios con al menos 10 caracteres.', { exact: true })).toBeVisible();
  await page.getByLabel('Observaciones del curador', { exact: true }).fill('PRUEBA ARTIFICIAL: verificación técnica del software, sin validación científica.');
  const curationResponse = page.waitForResponse(response => response.request().method() === 'PATCH' && response.url().endsWith('/curation'));
  await page.getByRole('button', { name: 'Verificar registro', exact: true }).click();
  const reviewed = await curationResponse;
  assert.equal(reviewed.status(), 200); assert.equal((await reviewed.json()).status, 'verified');
  await expect(page.getByText('Registro verificado.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /^Verificado/ }).click();
  await expect(page.locator('.review-list-item').filter({ hasText: 'Meta' })).toHaveCount(1);
  passed('Curaduría: comentario obligatorio para ajustes y verificación del registro artificial');
  await page.screenshot({ path: join(output, 'curaduria.png'), fullPage: true });
  await logout(); await login(data.accounts.viewer);
  for (const name of ['Nuevo registro', 'Registros de campo', 'Gestión de usuarios']) await expect(page.getByRole('button', { name, exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /^Curaduría/ })).toHaveCount(0);
  await page.goto(base + '#/usuarios');
  await expect(page.getByRole('heading', { name: 'Este espacio requiere otro rol' })).toBeVisible();
  await page.getByRole('button', { name: 'Galería multimedia', exact: true }).click();
  await expect(page.locator('.gallery-card')).toHaveCount(2);
  await expect.poll(() => page.locator('.gallery-card img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0))).toBe(true);
  await page.screenshot({ path: join(output, 'galeria.png'), fullPage: true });
  passed('Visitante: consulta fotografías reales del servidor y no accede a módulos privilegiados');
  await page.getByRole('button', { name: 'Visor cartográfico', exact: true }).click();
  await expect(page.locator('.leaflet-container')).toBeVisible();
  await page.screenshot({ path: join(output, 'mapa.png'), fullPage: true });
  passed('Mapa carga y muestra las observaciones guardadas');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Abrir navegación', exact: true }).click();
  await page.getByRole('button', { name: 'Vista general', exact: true }).click();
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'Hay desbordamiento horizontal en móvil.');
  await page.screenshot({ path: join(output, 'movil.png'), fullPage: true });
  passed('Navegación móvil y ausencia de desbordamiento horizontal');
  console.log(fixture('verify').trim());
  assert.deepEqual(report.pageErrors, [], 'Errores JavaScript del navegador.');
  assert.deepEqual(report.serverErrors, [], 'Respuestas HTTP 500 del servidor.');
  report.status = 'passed';
  for (const stale of ['fallo.png', 'fallo-dom.txt']) await rm(join(output, stale), { force: true });
} catch (error) {
  report.status = 'failed'; report.error = error.message;
  if (page) { await page.screenshot({ path: join(output, 'fallo.png'), fullPage: true }).catch(() => {}); await writeFile(join(output, 'fallo-dom.txt'), await page.locator('body').innerText().catch(() => '')); }
  console.error('Prueba web fallida:', error.message); process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  try { console.log(fixture('cleanup').trim()); } catch (error) { console.error('Revisa la limpieza del administrador temporal de QA.'); report.cleanupError = error.message; process.exitCode = 1; }
  await writeFile(join(output, 'resultado.json'), JSON.stringify(report, null, 2));
}
