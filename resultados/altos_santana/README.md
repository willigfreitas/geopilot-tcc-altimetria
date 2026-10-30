# Resultados — Centro–Altos de Santana

Esta pasta reúne os resultados produzidos no Google Colab para a rota entre o Centro de São José dos Campos e Altos de Santana.

## Parâmetros do processamento

- Sistema de referência: **SIRGAS 2000 / UTM zona 23S (EPSG:31983)**
- Modelo Digital de Elevação: **MDE SRTM com resolução espacial de 30 m**
- Espaçamento entre amostras: **30 m**
- Quantidade de amostras: **190**

## Indicadores altimétricos

- Distância da rota: **5,647 km**
- Elevação inicial: **606,50 m**
- Elevação final: **580,50 m**
- Variação líquida de elevação: **−26,00 m**
- Subida acumulada: **79,00 m**
- Descida acumulada: **105,00 m**
- Declividade absoluta média: **3,31%**
- Declividade máxima de subida: **14,44%**
- Declividade máxima de descida: **−17,78%**

## Arquivos

- `parametros_execucao.json`: parâmetros utilizados na execução;
- `perfil_altimetrico.csv`: perfil altimétrico amostrado ao longo da rota;
- `pontos_perfil.gpkg`: pontos georreferenciados do perfil;
- `resumo_rota.json`: síntese dos indicadores calculados.

## Observação metodológica

A rota foi amostrada em intervalos regulares de 30 m. O ponto final exato foi incluído no processamento, garantindo que a extensão total da geometria fosse considerada. Os indicadores foram calculados automaticamente pelo script disponibilizado neste repositório.
