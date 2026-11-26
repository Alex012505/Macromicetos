# =============================================================================
# importar_datos_reales.ps1
# Carga los datos reales (Corte 1) en la base del aplicativo Macromicetos.
#
# REQUISITOS
#   1. Copiar este archivo Y import_corte1.py a la raíz del repo Macromicetos.
#   2. Sincronizar en OneDrive la carpeta de SharePoint:
#        https://livejaverianaedu.sharepoint.com/sites/Proyecto-Orquideas-2026-1/Shared%20Documents/General/Actividades_Equipo_de_Trabajo/Actividades_Productos_Macromicetos
#   3. Descargar los archivos de Capas_BD (clic derecho -> "Conservar siempre en este dispositivo").
#   4. Backend configurado + administrador creado (Backend/README.md).
#
# USO
#   Validar (sin escribir en la BD):
#       powershell -ExecutionPolicy Bypass -File .\importar_datos_reales.ps1 -DryRun
#   Importar de verdad:
#       powershell -ExecutionPolicy Bypass -File .\importar_datos_reales.ps1 -OwnerEmail TU_CORREO
#   Si OneDrive está en otra ruta:
#       ... -Datos "C:\ruta\a\Actividades_Productos_Macromicetos"
# =============================================================================

param(
    [string]$OwnerEmail = "",
    [switch]$DryRun,
    [string]$Datos = ""
)

$RepoRoot = $PSScriptRoot

# Carpeta de SharePoint sincronizada con OneDrive (ajústala con -Datos si tu ruta es distinta)
if (-not $Datos) {
    $Datos = Join-Path $env:USERPROFILE "OneDrive - Pontificia Universidad Javeriana\Proyecto-Orquideas-2026-1 - General\Actividades_Equipo_de_Trabajo\Actividades_Productos_Macromicetos"
}

$ImportScript = Join-Path $RepoRoot "import_corte1.py"
$Python       = Join-Path $RepoRoot "Backend\.venv\Scripts\python.exe"

# --- Datos reales (carpeta Capas_BD) -----------------------------------------
$TaxonMaster = Join-Path $Datos "Capas_BD\Base_Datos_Nuclear.xlsx"                       # 802 especies (hoja 'sp')
$TaxonRef    = Join-Path $Datos "Capas_BD\Lista_especies_macrohongos_orinoquia.xlsx"     # 330 especies curadas
$GbifDir     = Join-Path $Datos "Capas_BD\ocurrencias_images_orinoquia_GBIF0007586-260221153910048_filtrada_macromicetos"
$Occurrence  = Join-Path $GbifDir "occurrence.txt"                                        # 1.319 ocurrencias
$Multimedia  = Join-Path $GbifDir "multimedia.txt"                                        # 3.063 fotos
$Biblio      = Join-Path $Datos "Capas_BD\Capa_bibliografica.xlsx"                        # 31 fuentes / 1.301 vínculos
$Morphology  = Join-Path $Datos "Capas_BD\Capa_morfologica.xlsx"                          # 332 especies / 18 rasgos (opcional)
$Ethno       = Join-Path $Datos "Capas_BD\Capa_etnomicologica.xlsx"                       # 4 fuentes / 15 conoc. / 9 usos (opcional)

# Verificación de rutas (avisa antes de arrancar si falta algo)
$requeridos = @($TaxonMaster, $TaxonRef, $Occurrence, $Multimedia, $Biblio)
$faltan = $requeridos | Where-Object { -not (Test-Path -LiteralPath $_) }
if ($faltan) {
    Write-Host "No se encontraron estos archivos:" -ForegroundColor Yellow
    $faltan | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "Ajusta -Datos a tu ruta de OneDrive, o descarga los archivos en OneDrive" -ForegroundColor Yellow
    Write-Host "(clic derecho sobre la carpeta Capas_BD -> 'Conservar siempre en este dispositivo')." -ForegroundColor Yellow
}
if (-not (Test-Path -LiteralPath $Morphology)) {
    Write-Host "Aviso: Capa_morfologica.xlsx no está en SharePoint (solo en la carpeta local). Se omitirá la morfología." -ForegroundColor Yellow
}
if (-not (Test-Path -LiteralPath $Ethno)) {
    Write-Host "Aviso: Capa_etnomicologica.xlsx no está en SharePoint (solo en la carpeta local). Se omitirá la etnomicología." -ForegroundColor Yellow
}

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "No se encontró $Python. Ejecuta primero Backend\setup_postgres.py." -ForegroundColor Red
    exit 1
}

$args = @(
    "--backend-src", (Join-Path $RepoRoot "Backend\src"),
    "--taxon-master", $TaxonMaster, "--taxon-master-sheet", "sp",
    "--taxon-ref", $TaxonRef,
    "--occurrence", $Occurrence,
    "--multimedia", $Multimedia,
    "--biblio", $Biblio,
    "--morphology", $Morphology,
    "--ethno", $Ethno
)
if ($OwnerEmail) { $args += @("--owner-email", $OwnerEmail) }
if ($DryRun) { $args += @("--dry-run") }

Write-Host "Ejecutando importación..." -ForegroundColor Cyan
& $Python $ImportScript @args
exit $LASTEXITCODE
