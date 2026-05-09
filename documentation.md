# Documentação do TAURUS Video Maker

## Objetivo

O TAURUS Video Maker monta vídeos lo-fi longos combinando uma mídia visual base, uma sequência de músicas, áudio de fundo opcional, textos, marca d'água e efeitos de introdução. O processamento de mídia é feito com FFmpeg.

## Versão do Script

A versão atual do script é `8.0.44`.

O projeto passa a seguir versionamento incremental para o script. A versão 8 é a base atual; mudanças menores e correções devem avançar para `8.0.1`, `8.0.2`, `8.0.3` e assim por diante. Mudanças maiores podem avançar a versão secundária ou principal quando fizer sentido.

Sempre que a versão do script mudar, atualize:

- a constante `APP_VERSION` em [engine.py](engine.py);
- esta seção da documentação;
- o [CHANGELOG.md](CHANGELOG.md).

## Execução em Modo Fonte

Use PowerShell na pasta do projeto:

```powershell
cd F:\scripts\GitHub\LoFi_VideoMaker
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\VideoMaker.py
```

Não há mais `start.bat`. O ponto de entrada oficial do projeto é o arquivo [VideoMaker.py](VideoMaker.py).

## Organização do Código

O projeto agora separa interface e backend:

- [VideoMaker.py](VideoMaker.py) contém somente a interface PySide6, o mapeamento da UI para a configuração e os controles de tela.
- [engine.py](engine.py) contém o backend: dataclasses de configuração, persistência em JSON, controle de processo, chamadas de FFmpeg/FFprobe, `RenderEngine` e `WorkerRender`.

## FFmpeg Local

O aplicativo usa a cópia local do FFmpeg:

```text
ffmpeg/bin/ffmpeg.exe
ffmpeg/bin/ffprobe.exe
```

O `ffmpeg.exe` faz a renderização e o `ffprobe.exe` mede duração e metadados das mídias. Os dois precisam permanecer juntos.

Os binários são versionados com Git LFS. Se eles aparecerem como arquivos pequenos de texto depois de um clone, instale o Git LFS e execute:

```powershell
git lfs install
git lfs pull
```

## Entradas Aceitas

Mídia visual base:

- `.mp4`
- `.mov`
- `.mkv`
- `.avi`
- `.webm`
- `.gif`
- imagens compatíveis com o fluxo do aplicativo

Áudios:

- `.mp3`
- `.wav`
- `.m4a`
- `.aac`
- `.flac`
- `.ogg`
- `.opus`
- `.wma`

## Arquivos Gerados Localmente

Estes arquivos e pastas são estado local da máquina e não devem ser versionados:

- `_temp_audio_processado/`
- `video_creator_config.json`
- `erro_ffmpeg_log.txt`
- `render_AAAA-MM-DD_HH-MM-SS/`
- `build/`
- `dist/`
- pastas de saída de renderização

Quando a pasta de saída fica vazia, o aplicativo cria automaticamente uma subpasta ao lado do script com o formato `render_AAAA-MM-DD_HH-MM-SS`. Isso evita sobrescrever vídeos gerados anteriormente.

## Preparação Para Executável

O script agora usa dois conceitos diferentes de caminho:

- pasta do aplicativo: onde ficam configurações, logs e arquivos temporários;
- pasta de recursos: onde ficam arquivos empacotados, como `ffmpeg.exe` e `ffprobe.exe`.

Em modo fonte, as duas apontam para a pasta do projeto. Em modo executável empacotado com PyInstaller, a pasta de recursos aponta para o diretório temporário interno extraído pelo pacote, enquanto configurações e logs continuam ao lado do executável final.

O arquivo [packaging/TAURUS_Video_Maker.spec](packaging/TAURUS_Video_Maker.spec) já declara os binários do FFmpeg como recursos internos no caminho `ffmpeg/bin/`.

Quando chegar a hora de gerar o executável, o comando esperado é:

```powershell
.\build_executable.ps1
```

O resultado será gerado em `dist/TAURUS Video Maker.exe`.

## Janelas de Console do FFmpeg

O aplicativo principal é uma interface gráfica e o executável futuro está configurado para ser gerado sem console. Mesmo assim, programas externos chamados pelo aplicativo, como `ffmpeg.exe` e `ffprobe.exe`, podem abrir janelas próprias se forem iniciados sem flags específicas do Windows.

A partir da versão `8.0.1`, todas as chamadas internas de FFmpeg e FFprobe usam `CREATE_NO_WINDOW` e `STARTF_USESHOWWINDOW` para ocultar janelas de console dos subprocessos. Isso vale tanto para execução como `.py`, `.pyw` quanto para o executável futuro gerado pelo PyInstaller.

## Validação Recomendada

Depois de alterar o código:

```powershell
.\.venv\Scripts\python.exe -m py_compile .\engine.py .\VideoMaker.py
.\ffmpeg\bin\ffmpeg.exe -hide_banner -encoders
```

Antes de publicar uma versão empacotada, faça pelo menos uma renderização curta de teste e confira se o modo CPU e o modo NVENC continuam funcionando.
