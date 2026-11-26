# Reproduzir a compilação do Advanced Launcher legado no Windows

## Estado verificado
- Origem: https://github.com/GoldRenard/DMOAdvancedLauncher (GPL-3.0-or-later nos cabeçalhos), revisão f27b9f3.
- Submódulos BugTrap e Locale-Emulator inicializados.
- Ambiente do teste: MSBuild 18.12.3, .NET Framework 4.8, toolset C++ v145 e Windows SDK 10.
- Compilação Release concluída com código 0.
- Executável gerado: AdvancedLauncher/bin/Release/AdvancedLauncher.exe (2.330.624 bytes no teste).
- Correção de inicialização: copiar System.Data.SqlServerCe.dll do pacote Microsoft.SqlServer.Compact.4.0.8876.1 e seus NativeBinaries x86/amd64 para a saída.
- Interface e configurações de perfil abriram; modo de jogo local ainda não implementado.

## Reproduzir
A partir da raiz de uma cópia separada do Advanced Launcher, com dependências restauradas:
```powershell
$rc = Join-Path (Get-Location) "packages\BugTrap\source\Client\BugTrap.rc"
if (!(Test-Path "$rc.bak")) { Copy-Item $rc "$rc.bak" }
$enc = [System.Text.Encoding]::GetEncoding(28591)
$txt = [System.IO.File]::ReadAllText($rc, $enc).Replace("afxres.h", "winres.h")
[System.IO.File]::WriteAllText($rc, $txt, $enc)
$msbuild = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products '*' -find 'MSBuild\**\Bin\MSBuild.exe' | Select-Object -First 1
$sln = Get-ChildItem -Filter "*.sln" -File | Select-Object -First 1
if (!$sln -or !$msbuild) { throw "Solucao ou MSBuild ausente" }
$opts = @('/p:Configuration=Release','/p:TargetFrameworkVersion=v4.8','/p:TargetFrameworkProfile=','/p:PlatformToolset=v145','/p:WindowsTargetPlatformVersion=10.0','/m:4','/v:minimal')
& $msbuild $sln.FullName /t:Restore /p:RestorePackagesConfig=true @opts
if ($LASTEXITCODE -ne 0) { throw "Restore falhou" }
& $msbuild $sln.FullName /t:Build @opts
if ($LASTEXITCODE -ne 0) { throw "Build falhou" }
$dest = Join-Path (Get-Location) 'AdvancedLauncher\bin\Release'
$pkg = Join-Path (Get-Location) 'packages\Microsoft.SqlServer.Compact.4.0.8876.1'
$dll = Get-ChildItem $pkg -Recurse -File -Filter System.Data.SqlServerCe.dll | Select-Object -First 1
if (!$dll) { throw "SQL Compact ausente" }
Copy-Item $dll.FullName $dest -Force
foreach ($arch in @('x86','amd64')) {
    $src = Join-Path $pkg "NativeBinaries\$arch"
    if (!(Test-Path $src)) { throw "NativeBinaries $arch ausente" }
    New-Item "$dest\$arch" -ItemType Directory -Force | Out-Null
    Copy-Item "$src\*" "$dest\$arch" -Recurse -Force
}
```
A sequência consolida comandos testados separadamente; a sequência completa ainda não foi executada como uma única rotina. Não inicia o launcher nem altera o firewall.

## Bloqueio de compatibilidade
A interface oferece GDMO/GameKing, KDMO/IMBC, ADMO/Aeria e KDMO/DigimonMasters.com. Não há perfil ODMO local nativo. O launcher não é o cliente 3D. O servidor Rust foi escrito para o cliente ODMO 2.0, cuja distribuição pública ainda não está disponível segundo https://odmo.dev/ (consulta de 26/11/2026). Não presumir compatibilidade com outro executável, não substituir controles de autenticação de terceiros e não importar arquivos de origem/licença desconhecida.

Manter a instalação original e o ambiente de servidor atual intactos. A próxima etapa depende de um cliente autorizado com suporte documentado a servidor local; testar login, seleção de personagem, entrada no mundo e jogabilidade antes de afirmar compatibilidade.
