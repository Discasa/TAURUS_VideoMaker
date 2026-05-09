# FFmpeg Local

Esta pasta guarda a cópia local do FFmpeg usada pelo aplicativo.

Arquivos esperados:

```text
bin/ffmpeg.exe
bin/ffprobe.exe
```

O aplicativo procura esses arquivos primeiro neste caminho local. No empacotamento futuro, eles devem ser incluídos no mesmo caminho interno `ffmpeg/bin/`.

