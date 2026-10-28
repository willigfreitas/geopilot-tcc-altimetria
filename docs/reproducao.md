# Reprodução do experimento

## Requisitos

- Windows 10/11 ou Linux;
- Python 3.12 recomendado;
- QGIS 3.44.1 para repetir o fluxo manual;
- rota vetorial linear com SRC definido;
- MDE raster com SRC definido e cobertura integral da rota.

## Preparação do ambiente

### Windows PowerShell

```powershell
git clone https://github.com/willigfreitas/geopilot-tcc-altimetria.git
cd geopilot-tcc-altimetria
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se houver conflito entre instalações PROJ do QGIS e do ambiente Python:

```powershell
Remove-Item Env:PROJ_LIB -ErrorAction SilentlyContinue
$env:PROJ_DATA = & .\.venv\Scripts\python.exe -c "import pyproj; print(pyproj.datadir.get_data_dir())"
```

## Execução

```powershell
python .\tools\geopilot_geo_route.py `
  --routes "C:\dados\rota.gpkg" `
  --dem "C:\dados\mde.tif" `
  --output "C:\dados\resultado" `
  --crs "EPSG:31983" `
  --sample-spacing 30
```

## Conferência

```powershell
Get-Content "C:\dados\resultado\resumo_rota.json"
Import-Csv "C:\dados\resultado\perfil_altimetrico.csv" |
  Select-Object -Last 3 |
  Format-Table -AutoSize
python -m pytest -q
```

O último registro do CSV deve coincidir com o comprimento da rota apresentado no JSON, deixando `terminal_remainder_m` igual ou muito próximo de zero.

## Repetição no QGIS

1. Reprojetar a rota para EPSG:31983.
2. Executar **Pontos ao longo da geometria** com intervalo de 30 m.
3. Extrair o último vértice da rota com índice `-1`.
4. Amostrar o MDE nos pontos regulares e no ponto terminal.
5. Mesclar as camadas e ordenar pela distância.
6. Calcular média móvel, variações, declividade, subida e descida usando as mesmas regras descritas em `docs/metodologia.md`.
