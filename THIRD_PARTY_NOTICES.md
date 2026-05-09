# Avisos de Terceiros

## FFmpeg

Este projeto usa executáveis do FFmpeg e do FFprobe como dependência local de execução.

Os binários atuais estão em:

```text
ffmpeg/bin/ffmpeg.exe
ffmpeg/bin/ffprobe.exe
```

O FFmpeg é um projeto independente. A licença aplicável depende da configuração exata usada para compilar os binários copiados. Confira diretamente com:

```powershell
.\ffmpeg\bin\ffmpeg.exe -L
.\ffmpeg\bin\ffmpeg.exe -version
```

A cópia local atual é uma build completa da Gyan.dev com opções GPL habilitadas. Se o aplicativo for distribuído publicamente no futuro, revise as obrigações da licença do FFmpeg junto com a estratégia de empacotamento.

Site do projeto: https://ffmpeg.org/

