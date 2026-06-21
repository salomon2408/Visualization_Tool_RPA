"""
Lancer avec :  streamlit run dashboard.py
"""

import os
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ──────────────────────────────────────────────────────────────
# CONFIGURATION DE LA PAGE
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RPA",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 2rem; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# CHARGEMENT DES DONNÉES
# ──────────────────────────────────────────────────────────────
@st.cache_data
def load_results(path: str):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    df = pd.DataFrame(raw["transactions"])
    for col in ("periode", "transaction", "robot", "qte_volume"):
        df[col] = df[col].astype(int)
    df = df[df["qte_volume"] > 0].copy()

    duree_periode = {int(k): v for k, v in raw["duree_periode"].items()}
    n_robots       = {int(k): int(v) for k, v in raw["nb_robot_periode"].items()}
    t_times        = {int(k): v for k, v in raw.get("duree_transaction", {}).items()}

    return df, duree_periode, n_robots, t_times


# ──────────────────────────────────────────────────────────────
# PALETTE DE COULEURS
# ──────────────────────────────────────────────────────────────
_PALETTE = (
    px.colors.qualitative.Plotly
    + px.colors.qualitative.Dark24
    + px.colors.qualitative.Alphabet
)

def robot_colors(robots: list[int]) -> dict[int, str]:
    return {r: _PALETTE[i % len(_PALETTE)] for i, r in enumerate(sorted(robots))}


# ──────────────────────────────────────────────────────────────
# GRAPHIQUE 1 — période × type, rectangles par robot)
# ──────────────────────────────────────────────────────────────
def make_gantt(df: pd.DataFrame, title: str = "Assignation des robots") -> go.Figure:
    """
    Axe X  = périodes   |  Axe Y = types de transactions
    Chaque cellule (k, p) est subdivisée verticalement par robot.
    Cliquer sur un robot dans la légende masque/affiche ses rectangles.
    """
    if df.empty:
        return go.Figure().update_layout(title=title)

    periods = sorted(df["periode"].unique())
    trans   = sorted(df["transaction"].unique())
    robots  = sorted(df["robot"].unique())
    clr     = robot_colors(robots)
    k_pos   = {k: i for i, k in enumerate(periods)} # période → position X
    p_pos   = {p: i for i, p in enumerate(trans)}   # type    → position Y

    fig = go.Figure()

    # Séparateurs de périodes
    for i in range(len(periods) + 1):
        fig.add_shape(
            type="line",
            x0=i - 0.5, x1=i - 0.5,
            y0=-0.5, y1=len(trans) - 0.5,
            line=dict(color="rgba(120,120,130,0.25)", width=0.8),
        )

    # ── Entrées de légende (une par robot) ────────────────────
    for r in robots:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=14, symbol="square", color=clr[r]),
            name=f"Robot {r}",
            legendgroup=f"r{r}",
            showlegend=True,
        ))

    # ── Rectangles ────────────────────────────────────────────
    CW, CH = 1, 1   # largeur / hauteur de la cellule (en unités d'axe)

    for k in periods:
        for p in trans:
            sub = df[(df["periode"] == k) & (df["transaction"] == p)].sort_values("robot")
            n   = len(sub)
            if n == 0:
                continue

            ki, pi_ = k_pos[k], p_pos[p]
            sh = CH / n          # hauteur d'un sous-rectangle

            for i, (_, row) in enumerate(sub.iterrows()):
                r, q = int(row["robot"]), int(row["qte_volume"])
                c = clr[r]

                x0, x1 = ki - CW / 2, ki + CW / 2
                y0 = pi_ - CH / 2 + i * sh + 0.01
                y1 = y0 + sh - 0.02
                xm, ym = (x0 + x1) / 2, (y0 + y1) / 2

                # Rectangle rempli (scatter fill = togglable via légende)
                fig.add_trace(go.Scatter(
                    x=[x0, x1, x1, x0, x0],
                    y=[y0, y0, y1, y1, y0],
                    fill="toself",
                    fillcolor=c,
                    line=dict(color="white", width=0.9),
                    mode="lines",
                    showlegend=False,
                    legendgroup=f"r{r}",
                    hoverinfo="skip",
                ))

                # Étiquette + tooltip
                label = str(q) if sh > 0.14 else ""
                fig.add_trace(go.Scatter(
                    x=[xm], y=[ym],
                    mode="text",
                    text=[label],
                    textfont=dict(size=8, color="white"),
                    hovertemplate=(
                        f"<b>Période P{k} | Type {p} | Robot {r}</b><br>"
                        f"Transactions : <b>{q}</b><extra></extra>"
                    ),
                    showlegend=False,
                    legendgroup=f"r{r}",
                ))

    fig.update_layout(
        title=dict(text=title, font_size=15),
        xaxis=dict(
            title="Période",
            tickmode="array",
            tickvals=list(range(len(periods))),
            ticktext=[f"P{k}" for k in periods],
            showgrid=False, zeroline=False,
            range=[-0.55, len(periods) - 0.45],
        ),
        yaxis=dict(
            title="Type de transaction",
            tickmode="array",
            tickvals=list(range(len(trans))),
            ticktext=[f"Type {p}" for p in trans],
            showgrid=False, zeroline=False,
            range=[-0.55, len(trans) - 0.45],
        ),
        legend=dict(title="Robots", traceorder="grouped"),
        plot_bgcolor="rgba(250,251,254,1)",
        height=max(420, len(trans) * 58 + 120),
        margin=dict(l=95, r=125, t=60, b=65),
    )
    return fig


# ──────────────────────────────────────────────────────────────
# GRAPHIQUE 2 — HEATMAP RÉSUMÉ (total transactions)
# ──────────────────────────────────────────────────────────────
def make_heatmap(df: pd.DataFrame) -> go.Figure:
    pivot = (
        df.groupby(["periode", "transaction"])["qte_volume"]
          .sum().reset_index()
          .pivot(index="transaction", columns="periode", values="qte_volume")
          .fillna(0).astype(int)
    )

    y_labels = [f"Type {p}" for p in pivot.index]
    x_labels = [f"P{k}"    for k in pivot.columns]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=x_labels,
        y=y_labels,
        colorscale="Blues",
        text=pivot.values,
        texttemplate="%{text}",
        textfont=dict(size=11),
        hovertemplate="<b>%{y} | %{x}</b><br>Transactions : %{z}<extra></extra>",
        colorbar=dict(title="Transactions"),
        xgap=3,   # ← séparateur visible entre colonnes
        ygap=3,   # ← séparateur visible entre lignes / transactions
    ))

    fig.update_layout(
        title="Total des transactions par (période × type) — tous robots",
        xaxis=dict(title="Période", side="bottom"),
        yaxis=dict(title="Type de transaction", autorange="reversed"),
        height=max(300, len(pivot.index) * 55 + 100),
        margin=dict(t=55, l=110),
    )
    return fig


# ──────────────────────────────────────────────────────────────
# GRAPHIQUE 3 — BARRES EMPILÉES (transactions par période)
# ──────────────────────────────────────────────────────────────
def make_bar_stacked(df: pd.DataFrame) -> go.Figure:
    summary = (
        df.groupby(["periode", "transaction"])["qte_volume"]
          .sum().reset_index()
    )
    summary["transaction"] = "Type " + summary["transaction"].astype(str)
    periods_ordered = sorted(summary["periode"].unique())

    fig = px.bar(
        summary, x="periode", y="qte_volume", color="transaction",
        barmode="stack",
        title="Transactions totales par période (empilées par type)",
        labels={"periode": "Période", "qte_volume": "Transactions", "transaction": "Type"},
        category_orders={"periode": periods_ordered},
        text_auto=True,
    )
    fig.update_xaxes(
        tickmode="array",
        tickvals=periods_ordered,
        ticktext=[f"P{k}" for k in periods_ordered],
    )
    fig.update_layout(
        height=420,
        legend_title_text="Type",
        margin=dict(t=55),
    )
    return fig


# ──────────────────────────────────────────────────────────────
# GRAPHIQUE 4 — PIE (répartition pour un robot)
# ──────────────────────────────────────────────────────────────
def make_pie(df: pd.DataFrame, robot: int) -> go.Figure:
    rdf = (
        df[df["robot"] == robot]
          .groupby("transaction")["qte_volume"].sum()
          .reset_index()
    )
    rdf["transaction"] = "Type " + rdf["transaction"].astype(str)
    fig = px.pie(
        rdf, names="transaction", values="qte_volume",
        title=f"Répartition des types — Robot {robot}",
        hole=0.4,
    )
    fig.update_layout(height=360, margin=dict(t=55))
    return fig


# ──────────────────────────────────────────────────────────────
# EXPORT LATEX
# ──────────────────────────────────────────────────────────────
def gen_latex(df: pd.DataFrame, max_cols_per_row: int = 14) -> str:
    """
    Génère un tableau LaTeX.
    Si le tableau est trop large, il est scindé en blocs de max_cols_per_row.
    """
    # Structure : période → [types de transactions présents]
    pm: dict[int, list[int]] = {}
    for k in sorted(df["periode"].unique()):
        pm[k] = sorted(df[df["periode"] == k]["transaction"].unique())

    columns = [(k, p) for k in sorted(pm) for p in pm[k]]   # liste ordonnée (k, p)
    robots  = sorted(df["robot"].unique())

    def _block(cols: list[tuple]) -> str:
        """Génère un tableau LaTeX pour un sous-ensemble de colonnes."""
        # Identifie les périodes concernées et leurs spans
        from itertools import groupby
        periods_in_block = list(dict.fromkeys(k for k, _ in cols))
        col_spec = "l|" + "|".join(
            "c" * len([c for c in cols if c[0] == k]) for k in periods_in_block
        )

        L = []
        L.append(r"\begin{table}[ht]")
        L.append(r"\centering\small\setlength{\tabcolsep}{4pt}")
        L.append(r"\caption{Transactions exécutées par période et par robot}")
        L.append(r"\label{tab:rpa}")
        L.append(f"\\begin{{tabular}}{{{col_spec}}}")
        L.append(r"\toprule")

        # Ligne « Période »
        period_cells = []
        for k in periods_in_block:
            n = len([c for c in cols if c[0] == k])
            mc = f"\\multicolumn{{{n}}}{{c|}}{{{k}}}" if n > 1 else str(k)
            period_cells.append(mc)
        L.append("Période & " + " & ".join(period_cells) + r" \\")

        # Ligne « Transaction »
        L.append("Transaction & " + " & ".join(str(p) for _, p in cols) + r" \\")
        L.append(r"\midrule")

        # Ligne par robot
        for r in robots:
            cells = []
            for k, p in cols:
                v = df[
                    (df["periode"] == k) &
                    (df["transaction"] == p) &
                    (df["robot"] == r)
                ]["qte_volume"].sum()
                cells.append("--" if v == 0 else str(int(v)))
            L.append(f"Robot {r} & " + " & ".join(cells) + r" \\")

        L.append(r"\midrule")

        # Ligne Totaux
        totals = [
            str(int(df[(df["periode"] == k) & (df["transaction"] == p)]["qte_volume"].sum()))
            for k, p in cols
        ]
        L.append(r"\textbf{Total} & " + " & ".join(totals) + r" \\")

        L.append(r"\bottomrule")
        L.append(r"\end{tabular}")
        L.append(r"\end{table}")
        return "\n".join(L)

    # Découpe en blocs si trop large
    blocks = [columns[i:i + max_cols_per_row] for i in range(0, len(columns), max_cols_per_row)]
    return "\n\n% --- Bloc suivant ---\n\n".join(_block(b) for b in blocks)


#region APPLICATION PRINCIPALE
st.title("RPA — Dashboard d'optimisation")
st.caption("Visualisation des résultats de donnée")
st.divider()

#region --- Sidebar ---
with st.sidebar:
    st.header("Configuration")

    results_file = st.text_input("Fichiers JSON à comparer", value="resultats.json")

    if not os.path.exists(results_file):
        st.error(f"Fichier `{results_file}` introuvable.\nLancez d'abord `main.py` pour générer les résultats.")
        st.stop()

    df_all, duree_periode, n_robots_pp, t_times = load_results(results_file)

    st.header("Filtres")

    all_p = sorted(df_all["periode"].unique())
    all_t = sorted(df_all["transaction"].unique())
    all_r = sorted(df_all["robot"].unique())

    sel_p = st.multiselect("Périodes",               all_p, default=all_p, format_func=lambda x: f"P{x}")
    sel_t = st.multiselect("Types de transactions",  all_t, default=all_t, format_func=lambda x: f"Type {x}")
    sel_r = st.multiselect("Robots",                 all_r, default=all_r, format_func=lambda x: f"Robot {x}")
#endregion --- Sidebar ---

#region --- DataFrame filtré ---

# Change la dataframe en fonction des filtre appliquer dans la sidebar
df = df_all[
    df_all["periode"].isin(sel_p) &
    df_all["transaction"].isin(sel_t) &
    df_all["robot"].isin(sel_r) &
    (df_all["qte_volume"] > 0)
].copy()
#endregion --- DataFrame filtré ---

#region --- recap ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Robots actifs", df["robot"].nunique())
c2.metric("Périodes", df["periode"].nunique())
c3.metric("Types de transactions", df["transaction"].nunique())
c4.metric("Transactions au total", int(df["qte_volume"].sum()))
st.divider()
#endregion --- recap ---

# Pour ajouter un onglet, ajouter dans on nouveau tabX dans le tableau puis créer une nouvelle section with tabX
tab1, tab2, tab3, tab4 = st.tabs(
    ["Vue Générale", "Par Robot", "Résumé Charge", "Export LaTeX"]
)

#region TAB 1 : Vue générale
with tab1:
    st.subheader("Assignation des robots par période et type de transaction")
    st.caption(
        "Chaque rectangle = un robot pour un type de transaction à une période donnée. "
        "La hauteur du rectangle est proportionnelle au nombre de robots dans la cellule."
    )

    if df.empty:
        st.info("Aucune donnée à afficher avec les filtres sélectionnés.")
    else:
        fig1 = make_gantt(df)
        st.plotly_chart(fig1, use_container_width=True)

        with st.expander("Données brutes filtrées"):
            st.dataframe(
                df.sort_values(["periode", "transaction", "robot"]),
                hide_index=True, use_container_width=True,
            )
#endregion TAB 1 : Vue générale

#region TAB 2 : Par robot
with tab2:
    st.subheader("Activité détaillée par robot")

    robots_dispo = sorted(df["robot"].unique())
    if not robots_dispo:
        st.info("Aucun robot disponible avec les filtres actuels.")
    else:
        sel_robot = st.selectbox(
            "Sélectionner un robot", robots_dispo,
            format_func=lambda x: f"Robot {x}",
        )

        robot_df = df[df["robot"] == sel_robot]

        col_g, col_p = st.columns([3, 2])
        with col_g:
            fig_r = make_gantt(robot_df, title=f"Activité — Robot {sel_robot}")
            st.plotly_chart(fig_r, use_container_width=True)

        with col_p:
            st.plotly_chart(make_pie(df, sel_robot), use_container_width=True)

        st.subheader(f"Détail des transactions — Robot {sel_robot}")
        stats = (
            robot_df.groupby(["periode", "transaction"])["qte_volume"]
                    .sum().reset_index()
                    .rename(columns={"periode": "Période", "transaction": "Type", "qte_volume": "Transactions"})
        )
        # Ajout durée période et temps total utilisé
        stats["Durée période (s)"] = stats["Période"].map(duree_periode)
        stats["Temps utilisé (s)"] = stats["Transactions"] * stats["Type"].map(t_times)
        st.dataframe(stats, hide_index=True, use_container_width=True)
#endregion TAB 2 : Par robot

#region TAB 3 : Résumé charge
with tab3:
    st.subheader("Résumé de la charge — tous robots confondus")

    if df.empty:
        st.info("Aucune donnée.")
    else:
        col_h, col_b = st.columns(2)
        with col_h:
            st.plotly_chart(make_heatmap(df), use_container_width=True)
        with col_b:
            st.plotly_chart(make_bar_stacked(df), use_container_width=True)

        # Tableau pivot complet
        st.subheader("Tableau croisé : robots × (période, type)")
        pivot_full = df.pivot_table(
            index="robot",
            columns=["periode", "transaction"],
            values="qte_volume",
            aggfunc="sum",
            fill_value=0,
        )
        pivot_full.index = [f"Robot {r}" for r in pivot_full.index]
        st.dataframe(pivot_full, use_container_width=True)
#endregion TAB 3 : Résumé charge

#region TAB 4 : LaTeX
with tab4:
    st.subheader("Export du tableau LaTeX")

    if df_all.empty:
        st.info("Aucune donnée.")
    else:
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            use_filtered = st.checkbox("Utiliser les données filtrées", value=False)
        with col_opt2:
            max_cols = st.number_input("Colonnes max par bloc", min_value=5, max_value=30, value=14, step=1)

        target_df = df if use_filtered else df_all
        latex_str  = gen_latex(target_df, max_cols_per_row=int(max_cols))

        st.code(latex_str, language="latex")
#endregion TAB 4 : LaTeX

#endregion APPLICATION PRINCIPALE