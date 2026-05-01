# create_test_cert.ps1
# Cria um certificado de assinatura de código AUTOASSINADO para testes locais.
#
# USO:
#   .\scripts\create_test_cert.ps1
#
# IMPORTANTE: certificados autoassinados NÃO eliminam o aviso do SmartScreen.
# Para distribuição real, use um certificado OV ou EV de uma CA reconhecida:
#   Sectigo, DigiCert, GlobalSign, SSL.com (EV ~USD 300-500/ano)
#
# RESULTADO:
#   - Instala o cert em Cert:\CurrentUser\My
#   - Exporta certs\ExcelDiff_test.pfx (senha: test1234)
#   - Imprime o thumbprint para usar como SIGN_THUMBPRINT

$ErrorActionPreference = 'Stop'

$certSubject = "CN=ExcelDiff Test, O=ExcelDiff, C=BR"
$pfxPassword  = ConvertTo-SecureString -String "test1234" -Force -AsPlainText
$pfxPath      = Join-Path $PSScriptRoot "..\certs\ExcelDiff_test.pfx"

# Cria pasta certs/ se não existir
$certsDir = Split-Path $pfxPath
if (-not (Test-Path $certsDir)) { New-Item -ItemType Directory -Path $certsDir | Out-Null }

# Gera o certificado
$cert = New-SelfSignedCertificate `
    -Type CodeSigning `
    -Subject $certSubject `
    -KeyAlgorithm RSA `
    -KeyLength 4096 `
    -HashAlgorithm SHA256 `
    -KeyUsage DigitalSignature `
    -FriendlyName "ExcelDiff Code Signing (TEST)" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears(2) `
    -TextExtension @(
        "2.5.29.37={text}1.3.6.1.5.5.7.3.3",
        "2.5.29.19={text}"
    )

# Exporta para PFX
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pfxPassword | Out-Null

Write-Host ""
Write-Host "Certificado criado com sucesso!" -ForegroundColor Green
Write-Host "  Thumbprint : $($cert.Thumbprint)"
Write-Host "  PFX        : $pfxPath  (senha: test1234)"
Write-Host ""
Write-Host "Para assinar o build, execute:" -ForegroundColor Cyan
Write-Host "  `$env:SIGN_THUMBPRINT='$($cert.Thumbprint)'; python build.py"
Write-Host ""
Write-Host "LEMBRETE: Este certificado e autoassinado e NAO elimina o aviso do SmartScreen." -ForegroundColor Yellow
Write-Host "          Para distribuicao publica, adquira um certificado OV ou EV." -ForegroundColor Yellow
