import streamlit as st
import pandas as pd
import numpy as np

from duckdb import query as fastsqldf
def sqldf(query):
    return fastsqldf(query).to_df()


df = pd.read_csv("./summary.csv")
df = sqldf("""
SELECT *
FROM df
WHERE Ano != 2018 AND Codigo != 'C891'
""")


dfEstacoes = sqldf("""
SELECT Codigo, MEAN(lat) AS lat, MEAN(lon) AS lon
FROM df
GROUP BY Codigo
""")



estados = sqldf("""
SELECT DISTINCT uf
FROM df
ORDER BY uf
""")["uf"].tolist()

if "estados" not in st.session_state:
    st.session_state["estados"] = estados


estadosSelecionados = st.multiselect("Estados a serem considerados", st.session_state["estados"])
#st.write(estadosSelecionados)
dfEstadosSelecionados = pd.DataFrame({
    "ufSelecionado": estadosSelecionados
})

#st.dataframe(dfEstadosSelecionados)

coluna = st.columns(2)
periodos = sqldf("""
SELECT DISTINCT Mes, Ano
FROM df
ORDER BY Ano, Mes
""").values.tolist()
with coluna[0]:
    periodoInicio = st.selectbox("Período de início", periodos)
with coluna[1]:
    periodoFim = st.selectbox("Período de fim", periodos)



todosDados = st.checkbox("Usar todos os dados")
todosEstados = st.checkbox("Usar todos os estados")
maxMinGlobal = st.checkbox("Maximo e minimo global")

if todosEstados:
    estadosSelecionados = st.session_state["estados"]

# condicoes de parada
if not todosDados and len(estadosSelecionados) == 0:
    st.write("Estados inválidos")
    st.stop()
if not todosDados and (periodoFim[1] < periodoInicio[1] or (periodoFim[1] == periodoInicio[1] and periodoFim[0] < periodoInicio[0])):
    st.write("Período inválido")
    st.stop()



if todosDados:
    dfRelevante = df.copy()
else:
    anoMin = periodoInicio[1]
    anoMax = periodoFim[1]
    mesMin = periodoInicio[0]
    mesMax = periodoFim[0]

    valorMin = 12*mesMin + anoMax
    valorMax = 12*mesMax + anoMax

    dfRelevante = sqldf("""
SELECT t1.*
FROM df AS t1, dfEstadosSelecionados AS t2
WHERE
    (12*t1.Mes + t1.Ano >= %d
    AND
    12*t1.Mes + t1.Ano <= %d )
    AND t1.uf = t2.ufSelecionado       
"""%(valorMin, valorMax))


if maxMinGlobal:
    dfMinMax=df.copy()
else:
    dfMinMax=dfRelevante.copy()

dfMinMax = sqldf("""
SELECT Codigo, MEAN("Umidade média mensal") AS "Umidade média mensal", MEAN("Temperatura média mensal") AS "Temperatura média mensal"
FROM dfMinMax
GROUP BY Codigo
""")

maxUmidade = max(dfMinMax["Umidade média mensal"].tolist())
minUmidade = min(dfMinMax["Umidade média mensal"].tolist())
maxTemp = max(dfMinMax["Temperatura média mensal"].tolist())
minTemp = min(dfMinMax["Temperatura média mensal"].tolist())

st.text("Max umidade: %f, min umidade: %f"%(maxUmidade, minUmidade))
st.text("Max temp: %f, min temp: %f"%(maxTemp, minTemp))

#st.dataframe(df)
#st.dataframe(dfEstacoes)

dfRelevante = sqldf("""
SELECT Codigo, MEAN("Umidade média mensal") AS Umidade,
                    MEAN("Temperatura média mensal") AS Temperatura
FROM dfRelevante
GROUP BY Codigo 
""")


def gradienteTemperatura(linha):
    return (linha["Temperatura"] - minTemp) / (maxTemp - minTemp)

def gradienteUmidade(linha):
    return (linha["Umidade"] - minUmidade) / (maxUmidade - minUmidade)


dfRelevante["GradTemp"] = dfRelevante.apply(gradienteTemperatura, axis=1)
dfRelevante["GradUmi"] = dfRelevante.apply(gradienteUmidade, axis=1)



def corTemp(linha):

    vermelho = np.array([1.0, 0.0, 0.0, 0.5])
    azul = np.array([0.0, 0.0, 1.0, 0.5])

    p = linha["GradTemp"]

    valor = p*vermelho + (1-p)*azul
    valor = list(valor)

    #return [1.0, 1.0, 1.0, 0.5]

    return valor

def corUmid(linha):

    azul = np.array([31/255, 184/255, 240/255, 0.5])
    vermelho = np.array([237/255, 55/255, 52/255, 0.5])

    p = linha["GradUmi"]

    valor = p*azul + (1-p)*vermelho
    valor = list(valor)

    return valor


dfRelevante["CorTemp"] = dfRelevante.apply(corTemp, axis=1)
dfRelevante["CorUmi"] = dfRelevante.apply(corUmid, axis=1)



dfRelevante = sqldf("""
SELECT t1.*, t2.lat, t2.lon
FROM dfRelevante as t1, dfEstacoes as t2
WHERE t1.Codigo = t2.Codigo
""")

st.dataframe(dfRelevante)


#st.write(dfRelevante["CorTemp"].tolist())


escolha = st.radio("O que plotar?", options=["Observatórios", "Temperatura", "Umidade"])

aux = ""
if escolha == "Observatórios":
    aux = "#808080"
elif escolha == "Temperatura":
    aux = "CorTemp"
elif escolha == "Umidade":
    aux = "CorUmi"



# plotando estacoes
st.map(data=dfRelevante, latitude="lat", longitude="lon", color=aux)
#st.dataframe(dfEstacoes)