import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ── Config ──
# Entete du dashboard #
st.set_page_config(page_title="Funnel Campagne IA", layout="wide")
st.title("📊 Vue d'ensemble du funnel — Campagne d'appels IA")

# ── Auth & Data ──
# Lien entre google sheet et mon local : appel à un API de google 
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
# Chargement de la Data Set
df = pd.DataFrame(gspread.authorize(creds).open("DATA SET").worksheet("DATASET").get_all_records())

# ── Calculs ──

NON_TROUVE = "non trouvé"
df["Classification_clean"] = df["Classification"].astype(str).str.strip().str.lower()
df["Resultat_clean"]       = df["Resultat"].astype(str).str.strip().str.lower()
df["Duration_seconds"] = pd.to_numeric(df["Duration_seconds"], errors="coerce")

total          = len(df)
passes         = (df["Classification_clean"] != NON_TROUVE).sum()
confirmateur   = (df["Resultat_clean"] != NON_TROUVE).sum()

# ── KPIs ──
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total appels",          f"{total:,}")
c2.metric("Passé le filtre",       f"{passes:,}",       f"{passes/total*100:.1f}%")
c3.metric("Atteint confirmateur",  f"{confirmateur:,}", f"{confirmateur/passes*100:.1f}%")
c4.metric("Taux global",           f"{confirmateur/total*100:.2f}%")

# ── Graphiques ──
# Les différentes valeurs de la colonne Classification (hors non trouvé)
classif_counts = (
    df[df["Classification_clean"] != NON_TROUVE]["Classification_clean"]
    .value_counts()
    .reset_index()
)
classif_counts.columns = ["Classification", "Nombre"]

fig = make_subplots(
    rows=1, cols=2,
    subplot_titles=("Funnel de conversion", "Répartition des classifications"),
    specs=[[{"type": "funnel"}, {"type": "bar"}]]
)

# ── Funnel ──
fig.add_trace(go.Funnel(
    y=["Total appels", "Passé le filtre", "Atteint confirmateur"],
    x=[total, passes, confirmateur],
    textinfo="value+percent initial",
    textfont=dict(size=12, color="#111827"),
    marker=dict(color=["#2F6FED", "#4EA8DE", "#F59E0B"]),
    connector=dict(line=dict(color="#888", width=1))

), row=1, col=1)

# ── Bar chart ──
fig.add_trace(go.Bar(
    x=classif_counts["Classification"],
    y=classif_counts["Nombre"],
    marker_color="#2F6FED",
    text=classif_counts["Nombre"],
    textposition="outside"
), row=1, col=2)

# ── Layout (dark theme) ──
fig.update_layout(
    height=500,
    showlegend=False,
    plot_bgcolor="#0F172A",   # fond des graphiques (gris très sombre)
    paper_bgcolor="#0B1220",  # fond global encore plus sombre
    font=dict(color="#E5E7EB")  # texte clair
)



st.plotly_chart(fig, use_container_width=True)

# ── Partie 2 ──
st.title("📋 Analyse par liste")

# Nettoyage list_name : supression des lignes avec un nom vide
df_clean = df[df["list_name"].astype(str).str.strip() != ""].copy()

# ── Calculs performance ──
def calcul_par_liste(d):
    total = len(d)
    passes = (d["Classification_clean"] != NON_TROUVE).sum()
    confirmateur = (d["Resultat_clean"] != NON_TROUVE).sum()
    return pd.Series({
        "Total appels": total,
        "Taux filtre (%)": round(passes / total * 100, 1) if total else 0,
        "Taux confirmateur (%)": round(confirmateur / passes * 100, 1) if passes else 0,
    })
# Cette fonction compare juste le code postale avant l'appel avec codigo postal après l'appel(direccion n'est pas incluse puisque on a juste 7 lignes sur à peu près 8000 lignes)

def coherence_cp(d):
    # Normalisation : convertir les deux en int pour éviter le problème float vs str
    cp_fourn = pd.to_numeric(d["code_postal"], errors="coerce")
    cp_prosp = pd.to_numeric(d["codigo_postal"], errors="coerce")
    
    # Garder uniquement les lignes où les deux sont valides
    valid_mask = cp_fourn.notna() & cp_prosp.notna()
    n_valid = valid_mask.sum()
    
    if n_valid == 0:
        return pd.Series({"Lignes comparables": 0, "Code postal cohérent (%)": None})
    
    match = (cp_fourn[valid_mask].astype(int) == cp_prosp[valid_mask].astype(int)).sum()
    
    return pd.Series({
        "Lignes comparables": int(n_valid),
        "Code postal cohérent (%)": round(match / n_valid * 100, 1)
    })
stats = df_clean.groupby("list_name").apply(calcul_par_liste).reset_index()
coh   = df_clean.groupby("list_name").apply(coherence_cp).reset_index()
stats = stats.merge(coh, on="list_name")

# ── Tableau ──
st.subheader("Performance & qualité des données par liste")
st.dataframe(stats, use_container_width=True)
st.caption(" direccion quasi vide (~7 lignes) — seul le code postal est comparable.")

# ── Graphique ──
fig = go.Figure()
fig.add_trace(go.Bar(name="Taux filtre (%)",
    x=stats["list_name"], y=stats["Taux filtre (%)"],
    marker_color="#37B9F1", text=stats["Taux filtre (%)"],
    textposition="outside", textfont=dict(color="black")))
fig.add_trace(go.Bar(name="Taux confirmateur (%)",
    x=stats["list_name"], y=stats["Taux confirmateur (%)"],
    marker_color="#FFA94D", text=stats["Taux confirmateur (%)"],
    textposition="outside", textfont=dict(color="black")))
fig.add_trace(go.Bar(name="Code postal cohérent (%)",
    x=stats["list_name"], y=stats["Code postal cohérent (%)"],
    marker_color="#20C997", text=stats["Code postal cohérent (%)"],
    textposition="outside", textfont=dict(color="black")))
fig.update_layout(barmode="group", height=450,
                  plot_bgcolor="white", paper_bgcolor="#F8F9FA")
st.plotly_chart(fig, use_container_width=True)

# ── Partie 3 ──
st.title("👤 Profil des bons prospects: Histogrammes -> TRES INTERESSE,RDV LEAD")

BONS = ["TRES INTERESSE", "RDV LEAD"]

df["profil"] = df["Classification_clean"].str.upper().apply(
    lambda x: "Bon prospect" if x in BONS else "Autre"
)
df_bon = df[df["Classification_clean"].str.upper().isin(BONS)]

# ── Fonction réutilisable ──
def plot_or_warn(df_source, col, label, color, normalize_map=None):
    data = df_source[col].dropna()
    data = data[data.astype(str).str.strip() != ""]
    if data.empty:
        st.warning(f"⚠️ {label} : uniquement des valeurs inexploitables.")
        return

    if normalize_map:
        data = data.str.strip().str.lower().replace(normalize_map)
    counts = data.value_counts().reset_index()
    counts.columns = [label, "Nombre"]
    fig = go.Figure(go.Bar(
        x=counts[label], y=counts["Nombre"], marker_color=color,
        text=counts["Nombre"], textposition="outside", textfont=dict(color="black")
    ))
    fig.update_layout(height=500, plot_bgcolor="white", paper_bgcolor="#F8F9FA")
    st.plotly_chart(fig, use_container_width=True)



# ── Type de logement ──
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏠 Type de logement : bons prospects vs tous")
    df["piso_label"] = df["piso_casa"].astype(str).str.strip().replace("", pd.NA)
    piso_comp = df[df["piso_label"].notna()].groupby(["profil", "piso_label"]).size().reset_index(name="Nombre")
    piso_comp.columns = ["profil", "Type", "Nombre"]

    if piso_comp.empty:
        st.warning("⚠️ Type de logement : uniquement des valeurs inexploitables.")
    else:
        fig1 = go.Figure()
        for profil, color in [("Bon prospect", "#20C997"), ("Autre", "#ADB5BD")]:
            d = piso_comp[piso_comp["profil"] == profil]
            fig1.add_trace(go.Bar(name=profil, x=d["Type"], y=d["Nombre"],
                                  marker_color=color, text=d["Nombre"],
                                  textposition="outside", textfont=dict(color="black")))
        fig1.update_layout(barmode="group", height=500,
                           plot_bgcolor="white", paper_bgcolor="#F8F9FA")
        fig1.update_layout(
            xaxis_title="Type de logement",
            yaxis_title="Nombre de logement",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA"
        )                   
        st.plotly_chart(fig1, use_container_width=True)
        st.caption(f"⚠️ 1 valeur manquante exclue — {len(df_bon)} bons prospects au total, {piso_comp[piso_comp['profil']=='Bon prospect']['Nombre'].sum()} affichés.")

# ------- Présence du grenier -------- 
with col2:
    st.subheader("🏚️ Présence du grenier : bons prospects vs tous")
    # Normaliser en string "Oui"/"Non" peu importe le type
    df["tiene_desvan_label"] = df["tiene_desvan"].astype(str).str.strip().str.upper().map(
    {"TRUE": "Oui", "FALSE": "Non"}
)  # les '' deviennent NaN automatiquement → filtrés ensuite

    for_desvan = df[df["tiene_desvan_label"].notna()].copy()
    desvan_comp = for_desvan.groupby(["profil", "tiene_desvan_label"]).size().reset_index(name="Nombre")
    desvan_comp.columns = ["profil", "Grenier", "Nombre"]

    if desvan_comp.empty:
        st.warning("⚠️ Grenier : uniquement des valeurs inexploitables.")
    else:
        fig2 = go.Figure()
        for profil, color in [("Bon prospect", "#20C997"), ("Autre", "#ADB5BD")]:
            d = desvan_comp[desvan_comp["profil"] == profil]
            fig2.add_trace(go.Bar(name=profil, x=d["Grenier"], y=d["Nombre"],
                                  marker_color=color, text=d["Nombre"],
                                  textposition="outside", textfont=dict(color="black")))
        fig2.update_layout(barmode="group", height=500,
                           plot_bgcolor="white", paper_bgcolor="#F8F9FA")
        fig2.update_layout(
            xaxis_title="Présence de grenier",
            yaxis_title="Nombre de logement",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA"
        )                   
        st.plotly_chart(fig2, use_container_width=True)

# ── Propriétaire──
col3, col4 = st.columns(2)

with col3:
    st.subheader("🔑 Propriétaire ?")
    prop = (df_bon["proprietad"].dropna()
            .map({True: "Propriétaire", False: "Locataire"})
            .value_counts().reset_index())
    prop.columns = ["Statut", "Nombre"]
    if prop.empty:
        st.warning("⚠️ Propriétaire : uniquement des valeurs inexploitables.")
    else:
        fig3 = go.Figure(go.Bar(
            x=prop["Statut"], y=prop["Nombre"],
            marker_color=["#4C6EF5", "#FFA94D"],
            text=prop["Nombre"], textposition="outside", textfont=dict(color="black")
        ))
        fig3.update_layout(height=500, plot_bgcolor="white", paper_bgcolor="#F8F9FA")
        st.plotly_chart(fig3, use_container_width=True)

# ---- Durée d'appel ----
with col4:
    st.subheader("⏱️ Durée d'appel (secondes)")
    df_dur = df[df["Duration_seconds"].notna() & (df["Duration_seconds"] > 0)]
    df_dur = df_dur[df_dur["Classification_clean"] != NON_TROUVE]
    if df_dur.empty:
        st.warning("⚠️ Durée d'appel : uniquement des valeurs inexploitables.")
    else:
        fig4 = go.Figure()
        for label, color in [("Bon prospect", "#20C997"), ("Autre", "#ADB5BD")]:
            subset = df_dur[df_dur["profil"] == label]["Duration_seconds"]
            fig4.add_trace(go.Box(y=subset, name=label, marker_color=color, boxmean=True))
        fig4.update_layout(height=500, plot_bgcolor="white", paper_bgcolor="#F8F9FA")
        fig4.update_layout(
            xaxis_title="Type de prospect",
            yaxis_title="Durée d'appel",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA"
        )                   
        st.plotly_chart(fig4, use_container_width=True)
        st.caption("On peut remarquer que le temps de l'appel et la qualité du lead sont positivement corrélés")

col5, col6 = st.columns(2)


# ── Type de chauffage ──
with col5:
    st.subheader("🔥 Type de chauffage : bons prospects vs tous")
    df["calef_label"] = df["calefaccion"].astype(str).str.strip().str.lower().replace(
        {"gas oil": "gazoil", "gas": "gaz", "electricidad": "électricité", "caldera": "chaudière"}
    ).replace("nan", pd.NA)
    df["calef_label"] = df["calef_label"][df["calef_label"].astype(str).str.strip() != ""]
    
    calef_comp = df[df["calef_label"].notna()].groupby(["profil", "calef_label"]).size().reset_index(name="Nombre")
    calef_comp.columns = ["profil", "Chauffage", "Nombre"]
    if calef_comp.empty:
        st.warning("⚠️ Chauffage : uniquement des valeurs inexploitables.")
    else:
        fig5 = go.Figure()
        for profil, color in [("Bon prospect", "#20C997"), ("Autre", "#ADB5BD")]:
            d = calef_comp[calef_comp["profil"] == profil]
            fig5.add_trace(go.Bar(name=profil, x=d["Chauffage"], y=d["Nombre"],
                                  marker_color=color, text=d["Nombre"],
                                  textposition="outside", textfont=dict(color="black")))
        fig5.update_layout(barmode="group", height=500, plot_bgcolor="white", paper_bgcolor="#F8F9FA")
        fig5.update_layout(
            xaxis_title="Type de chauffage",
            yaxis_title="Nombre de logement",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA"
        )                   
        st.plotly_chart(fig5, use_container_width=True)
        st.caption("⚠️ 4 valeurs manquantes exclues — 9 affichées --> Bon  prospect.")


# ── Type de sol ──
with col6:
    st.subheader("🪵 Type de sol : bons prospects vs tous")
    df["suelo_label"] = df["suelo"].astype(str).str.strip().str.lower().replace("nan", pd.NA)
    df["suelo_label"] = df["suelo_label"][df["suelo_label"].astype(str).str.strip() != ""]
    
    suelo_comp = df[df["suelo_label"].notna()].groupby(["profil", "suelo_label"]).size().reset_index(name="Nombre")
    suelo_comp.columns = ["profil", "Sol", "Nombre"]
    if suelo_comp.empty:
        st.warning("⚠️ Sol : uniquement des valeurs inexploitables.")
    else:
        fig6 = go.Figure()
        for profil, color in [("Bon prospect", "#20C997"), ("Autre", "#ADB5BD")]:
            d = suelo_comp[suelo_comp["profil"] == profil]
            fig6.add_trace(go.Bar(name=profil, x=d["Sol"], y=d["Nombre"],
                                  marker_color=color, text=d["Nombre"],
                                  textposition="outside", textfont=dict(color="black")))
        fig6.update_layout(barmode="group", height=500, plot_bgcolor="white", paper_bgcolor="#F8F9FA")
        fig6.update_layout(
            xaxis_title="Type de sol",
            yaxis_title="Nombre de logement",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA"
        )                   
        st.plotly_chart(fig6, use_container_width=True)
        st.caption("⚠️ 1 valeur manquante exclue — 12 affichées--> Bon prospect.")

col7, col8 = st.columns(2)

# ── Superficie ──
with col7:
    st.subheader("📐 Superficie : bons prospects vs tous")
    df["superf_label"] = df["superfici_vivienda"].astype(str).str.strip().replace("nan", pd.NA)
    df["superf_label"] = df["superf_label"][df["superf_label"].astype(str).str.strip() != ""]
    
    superf_comp = df[df["superf_label"].notna()].groupby(["profil", "superf_label"]).size().reset_index(name="Nombre")
    superf_comp.columns = ["profil", "Superficie", "Nombre"]
    if superf_comp.empty:
        st.warning("⚠️ Superficie : uniquement des valeurs inexploitables.")
    else:
        fig7 = go.Figure()
        for profil, color in [("Bon prospect", "#20C997"), ("Autre", "#ADB5BD")]:
            d = superf_comp[superf_comp["profil"] == profil]
            fig7.add_trace(go.Bar(name=profil, x=d["Superficie"], y=d["Nombre"],
                                  marker_color=color, text=d["Nombre"],
                                  textposition="outside", textfont=dict(color="black")))
        fig7.update_layout(barmode="group", height=500, plot_bgcolor="white", paper_bgcolor="#F8F9FA")
        fig7.update_layout(
            xaxis_title="Type de superficie",
            yaxis_title="Nombre de logement",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA"
        )                   
        st.plotly_chart(fig7, use_container_width=True)
        st.caption("⚠️ 8 valeurs manquantes exclues — 5 affichées --> Bon prospect.")


# ── Âge ──
with col8:
    st.subheader("👤 Âge du prospect : bons prospects vs tous")
    df["edad_label"] = pd.to_numeric(df["Edad"], errors="coerce")
    df["edad_label"] = df["edad_label"][df["edad_label"].astype(str).str.strip() != ""]
    
    edad_comp = df[df["edad_label"].notna()].groupby(["profil", "edad_label"]).size().reset_index(name="Nombre")
    edad_comp.columns = ["profil", "Âge", "Nombre"]
    if edad_comp.empty:
        st.warning("⚠️ Âge : uniquement des valeurs inexploitables.")
    else:
        fig8 = go.Figure()
        for profil, color in [("Bon prospect", "#20C997"), ("Autre", "#ADB5BD")]:
            d = edad_comp[edad_comp["profil"] == profil]
            fig8.add_trace(go.Bar(name=profil, x=d["Âge"], y=d["Nombre"],
                                  marker_color=color, text=d["Nombre"],
                                  textposition="outside", textfont=dict(color="black")))
        fig8.update_layout(barmode="group", height=500, plot_bgcolor="white", paper_bgcolor="#F8F9FA")
        st.plotly_chart(fig8, use_container_width=True)


# ── Partie 4 ──
st.title("⏰ Disponibilités — Meilleures plages horaires")

# Parsing Timestamp
df["Timestamp_dt"] = pd.to_datetime(df["Timestamp"], dayfirst=True, errors="coerce")
df["heure"] = df["Timestamp_dt"].dt.hour

col9, col10 = st.columns(2)

# ── Volume d'appels par heure ──
with col9:
    st.subheader("📊 Volume d'appels par heure")
    vol_heure = (
        df[df["heure"].notna()]
        .groupby("heure")
        .size()
        .reset_index(name="Nombre")
    )
    vol_heure["heure_label"] = vol_heure["heure"].astype(int).astype(str) + "h"

    if vol_heure.empty:
        st.warning("⚠️ Heure : uniquement des valeurs inexploitables.")
    else:
        fig9 = go.Figure(go.Bar(
            x=vol_heure["heure_label"],
            y=vol_heure["Nombre"],
            marker_color="#4C9BE8",
            text=vol_heure["Nombre"],
            textposition="outside",
            textfont=dict(color="black")
        ))
        fig9.update_layout(
            height=500,
            xaxis_title="Heure",
            yaxis_title="Nombre d'appels",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA"
        )
        st.plotly_chart(fig9, use_container_width=True)

# ── Taux de bons leads par heure ──
with col10:
    st.subheader("🎯 Taux de bons leads par heure")
    df["bon_lead"] = df["Classification_clean"].str.upper().isin(BONS)

    taux_heure = (
        df[df["heure"].notna()]
        .groupby("heure")
        .agg(total=("bon_lead", "count"), bons=("bon_lead", "sum"))
        .reset_index()
    )
    taux_heure["taux"] = (taux_heure["bons"] / taux_heure["total"] * 100).round(1)
    taux_heure["heure_label"] = taux_heure["heure"].astype(int).astype(str) + "h"

    if taux_heure.empty:
        st.warning("⚠️ Taux horaire : uniquement des valeurs inexploitables.")
    else:
        fig10 = go.Figure(go.Bar(
            x=taux_heure["heure_label"],
            y=taux_heure["taux"],
            marker_color="#20C997",
            text=taux_heure["taux"].astype(str) + "%",
            textposition="outside",
            textfont=dict(color="black")
        ))
        fig10.update_layout(
            height=500,
            xaxis_title="Heure",
            yaxis_title="% bons leads",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA",
            yaxis=dict(range=[0, taux_heure["taux"].max() * 1.4 + 1])
        )
        st.plotly_chart(fig10, use_container_width=True)

        meilleure = taux_heure.loc[taux_heure["taux"].idxmax()]
        st.caption(
            f"💡 Meilleure plage : {int(meilleure['heure'])}h "
            f"— {meilleure['taux']}% de bons leads "
            f"({int(meilleure['bons'])} sur {int(meilleure['total'])} appels)"
        )

# ── Partie 5 -------------
st.title("🗺️ Géographie — Répartition et qualité par zone")

# Extraction ville depuis adress_origine (format fournisseur : "CP VILLE")
df["ville_fourn"] = (
    df["adress_origine"].astype(str).str.strip()
    .str.extract(r'^\d+\s+(.+)$')[0]
    .str.normalize("NFKD")
    .str.encode("ascii", errors="ignore")
    .str.decode("ascii")
    .str.strip()
)
df["ville_fourn"] = df["ville_fourn"].replace("", pd.NA)

col11, col12 = st.columns(2)

# ── Volume d'appels par ville ──
with col11:
    st.subheader("🏙️ Volume d'appels par ville")
    vol_ville = (
        df[df["ville_fourn"].notna()]
        .groupby("ville_fourn")
        .size()
        .reset_index(name="Nombre")
        .sort_values("Nombre", ascending=False)
        .head(15)
    )
    if vol_ville.empty:
        st.warning("⚠️ Ville : uniquement des valeurs inexploitables.")
    else:
        fig11 = go.Figure(go.Bar(
            x=vol_ville["ville_fourn"],
            y=vol_ville["Nombre"],
            marker_color="#4C9BE8",
            text=vol_ville["Nombre"],
            textposition="outside",
            textfont=dict(color="black")
        ))
        fig11.update_layout(
            height=600,
            xaxis_title="Ville",
            yaxis_title="Nombre d'appels",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA"
        )
        st.plotly_chart(fig11, use_container_width=True)
        st.caption("Source : adress_origine (fournisseur) — Ciudad prospect quasi vide.")

# ── Volume par code postal fournisseur ──
with col12:
    st.subheader("📮 Volume d'appels par code postal (fournisseur)")
    df["cp_fourn_label"] = df["code_postal"].astype(str).str.strip().replace("nan", pd.NA)
    df["cp_fourn_label"] = df["cp_fourn_label"][df["cp_fourn_label"].astype(str).str.strip() != ""]

    vol_cp = (
        df[df["cp_fourn_label"].notna()]
        .groupby("cp_fourn_label")
        .size()
        .reset_index(name="Nombre")
        .sort_values("Nombre", ascending=False)
        .head(15)
    )
    if vol_cp.empty:
        st.warning("⚠️ Code postal : uniquement des valeurs inexploitables.")
    else:
        fig12 = go.Figure(go.Bar(
            x=vol_cp["cp_fourn_label"],
            y=vol_cp["Nombre"],
            marker_color="#FFA94D",
            text=vol_cp["Nombre"],
            textposition="outside",
            textfont=dict(color="black")
        ))
        fig12.update_layout(
            height=500,
            xaxis_title="Code postal",
            yaxis_title="Nombre d'appels",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA"
        )
        st.plotly_chart(fig12, use_container_width=True)
        st.caption("Top 15 codes postaux par volume — source fournisseur (code_postal).")


# ── Taux de passage du filtre par ville ──
col13 = st.columns(1)[0]

with col13:
    st.subheader("📈 Taux de passage du filtre par ville")
    ville_stats = (
        df[df["ville_fourn"].notna()]
        .groupby("ville_fourn")
        .agg(
            total=("Classification_clean", "count"),
            filtres=("Classification_clean", lambda x: (x != NON_TROUVE).sum())
        )
        .reset_index()
    )
    ville_stats["taux_filtre"] = (ville_stats["filtres"] / ville_stats["total"] * 100).round(1)
    ville_stats = ville_stats[ville_stats["total"] >= 30].sort_values("taux_filtre", ascending=False)

    if ville_stats.empty:
        st.warning("⚠️ Taux filtre par ville : données insuffisantes.")
    else:
        fig13 = go.Figure(go.Bar(
            x=ville_stats["ville_fourn"],
            y=ville_stats["taux_filtre"],
            marker_color="#20C997",
            text=ville_stats["taux_filtre"].astype(str) + "%",
            textposition="outside",
            textfont=dict(color="black")
        ))
        fig13.update_layout(
            height=500,
            xaxis_title="Ville",
            yaxis_title="% passé le filtre",
            plot_bgcolor="white",
            paper_bgcolor="#F8F9FA",
            yaxis=dict(range=[0, ville_stats["taux_filtre"].max() * 1.4 + 1])
        )
        st.plotly_chart(fig13, use_container_width=True)
        st.caption("Villes avec au moins 30 appels --> Avila et Burgos en tête du taux de filtrage.")


