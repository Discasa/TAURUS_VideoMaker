# Documentação do TAURUS Video Maker

## Objetivo

O TAURUS Video Maker monta vídeos lo-fi longos combinando uma mídia visual base, uma sequência de músicas, áudio de fundo opcional, textos, marca d'água e efeitos de introdução. O processamento de mídia é feito com FFmpeg.

## Versão do Script

A versão atual do script é `8.0.72`.

O projeto segue versionamento incremental para o script. A versão 8 é a base atual; mudanças menores e correções devem avançar a partir da versão publicada atual, por exemplo `8.0.73`, `8.0.74` e assim por diante. Mudanças maiores podem avançar a versão secundária ou principal quando fizer sentido.

Sempre que a versão do script mudar, atualize:

- a constante `APP_VERSION` em [engine.py](engine.py);
- esta seção da documentação;
- o [CHANGELOG.md](CHANGELOG.md).

## Execução em Modo Fonte

Use PowerShell na pasta do projeto:

```powershell
cd F:\scripts\GitHub\TAURUS_VideoMaker
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\VideoMaker.py
```

Repositório oficial no GitHub: [Discasa/TAURUS_VideoMaker](https://github.com/Discasa/TAURUS_VideoMaker).

Não há mais `start.bat`. O ponto de entrada oficial do projeto é o arquivo [VideoMaker.py](VideoMaker.py).

## Organização do Código

O projeto agora separa interface e backend:

- [VideoMaker.py](VideoMaker.py) contém somente a interface PySide6, o mapeamento da UI para a configuração e os controles de tela.
- [engine.py](engine.py) contém o backend: dataclasses de configuração, persistência em INI, controle de processo, chamadas de FFmpeg/FFprobe, `RenderEngine` e `WorkerRender`.

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

## Textos no Vídeo

Os textos de títulos das músicas, frases de introdução e marca d'água em texto compartilham os mesmos controles principais:

- fonte, tamanho e cor;
- opacidade da fonte;
- sombra ativável, cor da sombra, tamanho da sombra e opacidade da sombra;
- fundo ativável, cor do fundo, tamanho do fundo e opacidade do fundo.

O tamanho padrão do fundo usa 6 px como base: 4 px acima do texto, 6 px abaixo e 6 px nas laterais. Esse valor pode ser ajustado pelo slider `Tam. fundo`.

## Zoom da Interface

A seção `Renderização` inclui o controle `Zoom da interface`, com faixa de 50% a 200%.

Na primeira abertura, sem arquivo de configuração salvo, o aplicativo calcula um zoom inicial pela área útil da tela. Isso evita que a janela nasça maior que monitores pequenos ou ambientes Windows com escala alta, como 1366x768 em 150%.

Depois que o usuário ajusta o slider, o valor é salvo em `%LOCALAPPDATA%\TAURUS_VideoMaker\settings.ini` e reutilizado nas próximas aberturas.

## Arquivos Gerados Localmente

As configurações da interface ficam em:

```text
%LOCALAPPDATA%\TAURUS_VideoMaker\settings.ini
```

O cache de renderização, preview e fontes fica em:

```text
%LOCALAPPDATA%\TAURUS_VideoMaker\cache\
```

Logs de erro do FFmpeg ficam em:

```text
%LOCALAPPDATA%\TAURUS_VideoMaker\logs\
```

Estes arquivos e pastas são estado local da máquina e não devem ser versionados:

- `video_creator_config.json` antigo, se ainda existir de versões anteriores;
- `_temp_audio_processado/` antigo, se ainda existir de versões anteriores;
- `erro_ffmpeg_log.txt` antigo, se ainda existir de versões anteriores;
- `build/`
- `dist/`
- pastas de saída de renderização

Quando a pasta de saída fica vazia, o aplicativo salva o vídeo automaticamente na Área de Trabalho do usuário atual. O nome do arquivo final continua usando data e hora para evitar sobrescrever vídeos gerados anteriormente.

O cache de renderização é limpo antes e depois de cada render. Além disso, itens antigos dentro de `cache` são removidos automaticamente, evitando crescimento indefinido em disco.

## Distribuição Atual

O repositório atual mantém o aplicativo como execução pelo código-fonte. O empacotamento com PyInstaller não faz parte do layout ativo deste projeto.

O script usa dois conceitos diferentes de caminho:

- pasta de dados do usuário: `%LOCALAPPDATA%\TAURUS_VideoMaker`, onde ficam configurações, logs e cache;
- pasta de recursos: onde ficam arquivos empacotados, como `ffmpeg.exe` e `ffprobe.exe`.

Em modo fonte, os recursos apontam para a pasta do projeto. O FFmpeg local deve permanecer em `ffmpeg/bin/`, enquanto configurações, logs e cache continuam no AppData local do usuário.

## Janelas de Console do FFmpeg

O aplicativo principal é uma interface gráfica. Mesmo assim, programas externos chamados pelo aplicativo, como `ffmpeg.exe` e `ffprobe.exe`, podem abrir janelas próprias se forem iniciados sem flags específicas do Windows.

A partir da versão `8.0.1`, todas as chamadas internas de FFmpeg e FFprobe usam `CREATE_NO_WINDOW` e `STARTF_USESHOWWINDOW` para ocultar janelas de console dos subprocessos. Isso vale para a execução pelo código-fonte.

## Validação Recomendada

Depois de alterar o código:

```powershell
.\.venv\Scripts\python.exe -m py_compile .\engine.py .\VideoMaker.py
.\ffmpeg\bin\ffmpeg.exe -hide_banner -encoders
```

Antes de publicar uma versão empacotada, faça pelo menos uma renderização curta de teste e confira se o modo CPU e o modo NVENC continuam funcionando.
