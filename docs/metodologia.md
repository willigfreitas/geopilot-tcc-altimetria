# Metodologia computacional

## Entradas comuns

Os dois fluxos utilizam as mesmas geometrias de rota, o mesmo MDE SRTM, o mesmo sistema projetado SIRGAS 2000 / UTM zona 23S (EPSG:31983) e espaçamento nominal de 30 m.

## Sequência de processamento

1. Ler e validar a geometria linear.
2. Reprojetar a rota para EPSG:31983.
3. Consolidar as feições em uma única `LineString` contínua.
4. Criar pontos a cada 30 m, iniciando na distância zero.
5. Incluir o ponto terminal exato quando o comprimento não for múltiplo de 30 m.
6. Amostrar a banda 1 do MDE em cada ponto.
7. Aplicar média móvel centrada de três amostras, com `min_periods=1`.
8. Calcular a distância e a variação de cota de cada segmento.
9. Calcular a declividade percentual: `100 × variação de cota / distância do segmento`.
10. Somar separadamente as variações positivas e negativas.
11. Exportar o perfil, os pontos e o resumo auditável.

## Tratamento do segmento terminal

O ponto terminal é incluído para que a distância amostrada seja igual ao comprimento vetorial. O último segmento pode, portanto, ter menos de 30 m. Essa regra deve ser repetida no QGIS para que os resultados sejam diretamente comparáveis.

## Indicadores

- distância da rota;
- quantidade de amostras;
- cotas inicial e final suavizadas;
- variação altimétrica líquida;
- subida acumulada;
- descida acumulada;
- declividade absoluta média;
- declividades máxima de subida e máxima de descida.

## Critério de comparação

Para comparar as cotas produzidas pelos fluxos, são empregados o erro absoluto médio (MAE), a raiz do erro quadrático médio (RMSE) e a diferença máxima absoluta. O MAE expressa a magnitude média das diferenças em unidade original; o RMSE atribui maior peso a diferenças maiores; e a diferença máxima evidencia o maior desvio pontual. O uso conjunto evita que uma única métrica oculte padrões relevantes.

Essas métricas foram escolhidas com base em Hyndman e Koehler (2006), Willmott e Matsuura (2005) e Chai e Draxler (2014), trabalhos que discutem interpretação, vantagens e limitações de medidas de erro. Neste estudo, elas avaliam equivalência computacional, não acurácia absoluta do MDE.
