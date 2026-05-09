# TAURUS Video Maker

TAURUS Video Maker é um aplicativo de desktop para Windows que cria vídeos lo-fi a partir de uma mídia visual base e uma pasta de músicas. A interface é feita em PySide6 e a renderização é executada pelo FFmpeg local incluído no projeto.

## Versão Atual

O script está na versão `8.0.38`.

A versão 8 marca a base atual do projeto. A partir daqui, alterações incrementais no script devem subir a versão em formato semântico, como `8.0.1`, `8.0.2` e assim por diante.

## Recursos

- Seleção de vídeo, GIF ou imagem base.
- Seleção de uma pasta com músicas.
- Áudio de fundo opcional.
- Renderização por CPU/libx264 ou GPU NVIDIA/NVENC.
- Normalização de loudness com `loudnorm`.
- Fade in e fade out configuráveis.
- Texto com nome das faixas, marca d'água e frases de introdução.
- Configurações salvas automaticamente em JSON ao lado do aplicativo.

## Requisitos

- Windows 10 ou mais recente.
- Python 3.10 ou mais recente.
- Dependências Python em [requirements.txt](requirements.txt).
- Git LFS para clonar os binários do FFmpeg quando o repositório vier de um remoto.

## Como Rodar Pelo Código-Fonte

```powershell
cd F:\scripts\GitHub\LoFi_VideoMaker
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\VideoMaker.py
```

O script espera encontrar o FFmpeg nestes caminhos dentro do projeto:

```text
ffmpeg/bin/ffmpeg.exe
ffmpeg/bin/ffprobe.exe
```

Esses arquivos são rastreados com Git LFS porque são grandes. Depois de clonar o repositório, execute `git lfs pull` se os executáveis não estiverem presentes.

Se a pasta de saída ficar vazia na interface, o vídeo será salvo automaticamente ao lado do script em uma subpasta `render_AAAA-MM-DD_HH-MM-SS`.

## Estrutura

```text
Pasta do projeto/
  VideoMaker.py               Interface principal em PySide6
  engine.py                   Backend de renderização, FFmpeg e worker
  requirements.txt            Dependências de execução
  requirements-dev.txt        Dependências de empacotamento
  build_executable.ps1        Preparação futura do executável
  packaging/                  Arquivos do PyInstaller
  ffmpeg/bin/                 FFmpeg local usado pelo aplicativo
  README.md                   Visão geral
  documentation.md            Documentação detalhada
  CHANGELOG.md                Histórico de mudanças
  LICENSE                     Licença do código do projeto
  THIRD_PARTY_NOTICES.md      Avisos sobre dependências de terceiros
```

## Futuro Executável

O código já separa a pasta do aplicativo da pasta de recursos empacotados. Isso permite que um executável futuro salve configurações e logs ao lado do `.exe`, enquanto `ffmpeg.exe` e `ffprobe.exe` ficam embutidos como recursos do pacote.

O arquivo [packaging/TAURUS_Video_Maker.spec](packaging/TAURUS_Video_Maker.spec) já inclui os binários do FFmpeg no caminho interno `ffmpeg/bin/`.
