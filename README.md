# TAURUS Video Maker

TAURUS Video Maker é um aplicativo de desktop para Windows que cria vídeos lo-fi a partir de uma mídia visual base e uma pasta de músicas. A interface é feita em PySide6 e a renderização é executada pelo FFmpeg local incluído no projeto.

## Versão Atual

O script está na versão `8.0.74`.

A versão 8 marca a base atual do projeto. A partir daqui, alterações incrementais no script devem subir a versão em formato semântico, como `8.0.74`, `8.0.75` e assim por diante.

## Recursos

- Seleção de vídeo, GIF ou imagem base.
- Seleção de uma pasta com músicas.
- Áudio de fundo opcional.
- Renderização por CPU/libx264 ou GPU NVIDIA/NVENC.
- Normalização de loudness com `loudnorm`.
- Fade in e fade out configuráveis.
- Texto com nome das faixas, marca d'água e frases de introdução, com controles de fonte, cor, sombra e fundo.
- Reordenação manual das músicas antes do render.
- Preview estático com textos e marca d'água reposicionáveis por arraste.
- Preview em qualidade reduzida, sem processamento de áudio, para revisar o vídeo dentro da interface.
- Exportação final sempre gerada em 1920x1080.
- Crossfade e silêncio configuráveis entre faixas.
- Undo com `Ctrl+Z` para desfazer alterações de configuração na interface.
- Zoom da interface entre 50% e 200% para telas pequenas ou com escala alta do Windows.
- Configurações salvas automaticamente em `%LOCALAPPDATA%\TAURUS_VideoMaker\settings.ini`.

## Requisitos

- Windows 10 ou mais recente.
- Python 3.10 ou mais recente.
- Dependências Python de execução em [requirements.txt](requirements.txt).
- Git LFS para clonar os binários do FFmpeg quando o repositório vier de um remoto.

## Como Rodar Pelo Código-Fonte

```powershell
cd F:\scripts\GitHub\TAURUS_VideoMaker
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\VideoMaker.py
```

Repositório oficial: [Discasa/TAURUS_VideoMaker](https://github.com/Discasa/TAURUS_VideoMaker).

O script espera encontrar o FFmpeg nestes caminhos dentro do projeto:

```text
ffmpeg/bin/ffmpeg.exe
ffmpeg/bin/ffprobe.exe
```

Esses arquivos são rastreados com Git LFS porque são grandes. Depois de clonar o repositório, execute `git lfs pull` se os executáveis não estiverem presentes.

Se a pasta de saída ficar vazia na interface, o vídeo será salvo automaticamente na Área de Trabalho do usuário atual.

## Estrutura

```text
Pasta do projeto/
  VideoMaker.py               Ponto de entrada do aplicativo
  core/                       Backend de renderização
    engine.py                 Fachada de compatibilidade dos imports antigos
    constants.py              Versão, caminhos, extensões e pesos de progresso
    models.py                 Dataclasses de configuração e tracks
    config_store.py           Leitura e gravação do settings.ini
    profiles.py               Perfis de preview e exportação final
    render_engine.py          Orquestração do render e WorkerRender
    audio_pipeline.py         Detecção, fades, crossfade, silêncio e loudnorm
    video_filters.py          Drawtext, watermark e filter_complex de vídeo
    ffmpeg_runner.py          Execução FFmpeg, progresso, logs e teste NVENC
    ffmpeg_env.py             Fontconfig e ambiente FFmpeg
    files.py                  Limpeza de cache e arquivos temporários
    text_utils.py             Helpers de texto, cores, tempo e nomes
  ui/                         Interface PySide6 dividida em módulos
    main_window.py            Janela principal, autosave e orquestração
    left_panel.py             Entradas, saída e opções de render
    center_panel.py           Preview, player, progresso e log
    right_panel.py            Container das abas de ajustes
    preview_canvas.py         Preview estático arrastável
    common.py                 Widgets, helpers e constantes visuais
  requirements.txt            Dependências de execução
  ffmpeg/bin/                 FFmpeg local usado pelo aplicativo
  img/                        Ícone e imagens do aplicativo
  README.md                   Visão geral
  documentation.md            Documentação detalhada
  CHANGELOG.md                Histórico de mudanças
  LICENSE                     Licença do código do projeto
  THIRD_PARTY_NOTICES.md      Avisos sobre dependências de terceiros
```

## Distribuição Atual

O fluxo mantido neste repositório é a execução pelo código-fonte com Python e FFmpeg local. Configurações, logs, cache e previews ficam em `%LOCALAPPDATA%\TAURUS_VideoMaker`, enquanto os binários `ffmpeg.exe` e `ffprobe.exe` permanecem em `ffmpeg/bin/` dentro do projeto.
