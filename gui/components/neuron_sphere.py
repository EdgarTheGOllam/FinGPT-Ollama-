"""
Interaktive 3D-Neuronen-Kugel-Komponente für FinGPT News Tab Dashboard

Features:
- 500+ neuronale Punkte in sphärischer Anordnung (Fibonacci Sphere)
- Interaktive Punkte: Klick zeigt vollständigen Handelsverlauf
- Hover-Effekte und Smooth-Transition-Animationen
- Dark Theme kompatibel
- Streamlit-Integration

Author: FinGPT Team
Version: 1.0.0
"""

import math
import random
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np


# ============================================================
# FARBEN & KONFIGURATION
# ============================================================

class NeuronColors:
    """Dark Theme Farben für die Neuronen-Kugel"""
    
    # Background Colors
    BACKGROUND = "#0E1117"       # Streamlit Dark
    PAPER_BG = "#0E1117"
    PLOT_BG = "rgba(0,0,0,0)"
    
    # Primary Colors
    PRIMARY = "#2979FF"          # Blau
    NEURON_GLOW = "#00BFFF"     # Deep Sky Blue
    NEURON_CORE = "#4A90D9"     # Mittleres Blau
    
    # Sentiment Colors
    BULLISH = "#4CAF50"          # Grün
    BEARISH = "#F44336"          # Rot
    NEUTRAL = "#FFC107"         # Gelb
    
    # Impact Colors
    IMPACT_HIGH = "#F44336"       # Rot
    IMPACT_MEDIUM = "#FFC107"    # Gelb
    IMPACT_LOW = "#4CAF50"       # Grün
    
    # Text Colors
    TEXT = "#FAFAFA"             # Weiß
    TEXT_SECONDARY = "#8B949E"   # Grau
    
    # Particle Colors
    PARTICLE_CORE = "#FFFFFF"     # Weiß
    PARTICLE_GLOW = "#00BFFF"    # Cyan


class NeuronSphereConfig:
    """Konfiguration für die Neuronen-Kugel"""
    
    # Anzahl Punkte
    NUM_NEURONS = 500
    
    # Marker Sizes
    MARKER_SIZE_MIN = 4
    MARKER_SIZE_MAX = 12
    MARKER_SIZE_SELECTED = 18
    
    # Opacity
    OPACITY_MIN = 0.4
    OPACITY_MAX = 0.9
    
    # Animation
    ROTATION_DURATION = 30  # Sekunden für 360°
    TRANSITION_DURATION = 200  # ms
    
    # Sphere Radius
    SPHERE_RADIUS = 1.0


# ============================================================
# DATENSTRUKTUREN
# ============================================================

class NeuronData:
    """Datenstruktur für einen einzelnen Neuronen-Punkt"""
    
    def __init__(
        self,
        neuron_id: str,
        x: float,
        y: float,
        z: float,
        title: str = "",
        description: str = "",
        sentiment: str = "NEUTRAL",
        impact: str = "LOW",
        timestamp: Optional[datetime] = None,
        trade_data: Optional[Dict] = None
    ):
        self.id = neuron_id
        self.x = x
        self.y = y
        self.z = z
        self.title = title
        self.description = description
        self.sentiment = sentiment.upper()
        self.impact = impact.upper()
        self.timestamp = timestamp or datetime.now()
        self.trade_data = trade_data or {}
    
    @property
    def color(self) -> str:
        """Farbe basierend auf Sentiment"""
        colors = {
            "BULLISH": NeuronColors.BULLISH,
            "BEARISH": NeuronColors.BEARISH,
            "NEUTRAL": NeuronColors.NEUTRAL
        }
        return colors.get(self.sentiment, NeuronColors.NEUTRAL)
    
    @property
    def impact_color(self) -> str:
        """Farbe basierend auf Impact"""
        colors = {
            "HIGH": NeuronColors.IMPACT_HIGH,
            "MEDIUM": NeuronColors.IMPACT_MEDIUM,
            "LOW": NeuronColors.IMPACT_LOW
        }
        return colors.get(self.impact, NeuronColors.IMPACT_LOW)
    
    def to_dict(self) -> Dict:
        """Konvertiere zu Dictionary für Plotly"""
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "title": self.title,
            "description": self.description[:100] + "..." if len(self.description) > 100 else self.description,
            "sentiment": self.sentiment,
            "impact": self.impact,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M") if self.timestamp else "",
            "color": self.color,
            "trade_data": self.trade_data
        }


# ============================================================
# PUNKTGENERIERUNG
# ============================================================

def generate_fibonacci_sphere(n_points: int = 500) -> List[Tuple[float, float, float]]:
    """
    Generiere gleichmäßig verteilte Punkte auf einer Kugeloberfläche
    using Fibonacci Sphere Algorithmus
    
    Args:
        n_points: Anzahl der Punkte
        
    Returns:
        Liste von (x, y, z) Tupeln
    """
    points = []
    phi = math.pi * (3. - math.sqrt(5.))  # Golden Angle
    
    for i in range(n_points):
        y = 1 - (i / float(n_points - 1)) * 2  # y goes from 1 to -1
        radius = math.sqrt(1 - y * y)
        theta = phi * i
        
        x = math.cos(theta) * radius
        z = math.sin(theta) * radius
        
        points.append((x, y, z))
    
    return points


def generate_neuron_points(
    num_points: int = 500,
    news_data: Optional[List[Dict]] = None
) -> List[NeuronData]:
    """
    Generiere Neuronen-Punkte mit zufälligen oder News-Daten
    
    Args:
        num_points: Anzahl der Punkte
        news_data: Optionale Liste von News-Dicts für realistischere Daten
        
    Returns:
        Liste von NeuronData Objekten
    """
    # Generiere Fibonacci Sphere Punkte
    fib_points = generate_fibonacci_sphere(num_points)
    
    neurons = []
    
    if news_data and len(news_data) > 0:
        # Verwende News-Daten für die Punkte
        for i, (x, y, z) in enumerate(fib_points):
            news_item = news_data[i % len(news_data)]
            
            # Berechne zufällige Varianz für interessantere Verteilung
            variance = 0.1
            x += random.uniform(-variance, variance)
            y += random.uniform(-variance, variance)
            z += random.uniform(-variance, variance)
            
            # Normalisiere zurück auf Kugel
            length = math.sqrt(x*x + y*y + z*z)
            x, y, z = x/length, y/length, z/length
            
            neurons.append(NeuronData(
                neuron_id=f"neuron_{i}",
                x=x,
                y=y,
                z=z,
                title=news_item.get("title", f"News {i+1}")[:80],
                description=news_item.get("description", ""),
                sentiment=news_item.get("sentiment", "NEUTRAL"),
                impact=news_item.get("impact", "LOW"),
                timestamp=news_item.get("published_at"),
                trade_data={
                    "entry_price": random.uniform(1.08, 1.10),
                    "exit_price": random.uniform(1.08, 1.11),
                    "pnl_pips": random.uniform(-50, 100),
                    "duration_hours": random.uniform(0.5, 24),
                    "trade_type": random.choice(["BUY", "SELL"])
                }
            ))
    else:
        # Generiere zufällige Demo-Daten
        sentiments = ["BULLISH", "BEARISH", "NEUTRAL"]
        impacts = ["HIGH", "MEDIUM", "LOW"]
        
        for i, (x, y, z) in enumerate(fib_points):
            # Füge zufällige Varianz hinzu
            variance = 0.15
            x += random.uniform(-variance, variance)
            y += random.uniform(-variance, variance)
            z += random.uniform(-variance, variance)
            
            # Normalisiere zurück auf Kugel
            length = math.sqrt(x*x + y*y + z*z)
            x, y, z = x/length, y/length, z/length
            
            sentiment = random.choice(sentiments)
            impact = random.choice(impacts)
            
            neurons.append(NeuronData(
                neuron_id=f"neuron_{i}",
                x=x,
                y=y,
                z=z,
                title=f"EUR/USD Signal #{i+1}",
                description=f"Trading Signal generated at {datetime.now().strftime('%H:%M')}",
                sentiment=sentiment,
                impact=impact,
                timestamp=datetime.now(),
                trade_data={
                    "entry_price": round(random.uniform(1.08, 1.10), 4),
                    "exit_price": round(random.uniform(1.08, 1.11), 4),
                    "pnl_pips": round(random.uniform(-50, 100), 1),
                    "duration_hours": round(random.uniform(0.5, 24), 1),
                    "trade_type": random.choice(["BUY", "SELL"])
                }
            ))
    
    return neurons


# ============================================================
# PLOTLY VISUALISIERUNG
# ============================================================

def create_neuron_sphere_figure(
    neurons: List[NeuronData],
    selected_neuron_id: Optional[str] = None,
    show_rotation: bool = True
) -> go.Figure:
    """
    Erstelle die interaktive 3D-Neuronen-Kugel Visualisierung
    
    Args:
        neurons: Liste von NeuronData Objekten
        selected_neuron_id: ID des ausgewählten Neurons
        show_rotation: Ob die Kugel rotieren soll
        
    Returns:
        Plotly Figure Objekt
    """
    fig = go.Figure()
    
    # Sortiere Neuronen nach Sentiment für Layering
    sentiment_order = {"BEARISH": 0, "NEUTRAL": 1, "BULLISH": 2}
    sorted_neurons = sorted(neurons, key=lambda n: sentiment_order.get(n.sentiment, 1))
    
    # Farben und Größen für jeden Neuron
    colors = []
    sizes = []
    opacities = []
    hover_texts = []
    
    for neuron in sorted_neurons:
        is_selected = neuron.id == selected_neuron_id
        
        if is_selected:
            colors.append(NeuronColors.NEURON_GLOW)
            sizes.append(NeuronSphereConfig.MARKER_SIZE_SELECTED)
            opacities.append(1.0)
        else:
            colors.append(neuron.color)
            sizes.append(random.randint(
                NeuronSphereConfig.MARKER_SIZE_MIN,
                NeuronSphereConfig.MARKER_SIZE_MAX
            ))
            opacities.append(random.uniform(
                NeuronSphereConfig.OPACITY_MIN,
                NeuronSphereConfig.OPACITY_MAX
            ))
        
        # Hover Text
        hover_text = (
            f"<b>{neuron.title}</b><br>"
            f"📊 Sentiment: {neuron.sentiment}<br>"
            f"⚡ Impact: {neuron.impact}<br>"
            f"🕐 {neuron.timestamp.strftime('%H:%M')}<br>"
            f"<i>Klicken für Details →</i>"
        )
        hover_texts.append(hover_text)
    
    # Füge Glow-Layer hinzu (größere, transparentere Punkte)
    fig.add_trace(go.Scatter3d(
        x=[n.x * 1.02 for n in sorted_neurons],
        y=[n.y * 1.02 for n in sorted_neurons],
        z=[n.z * 1.02 for n in sorted_neurons],
        mode='markers',
        marker=dict(
            size=[s * 1.5 for s in sizes],
            color=colors,
            opacity=[o * 0.3 for o in opacities],
            line=dict(width=0)
        ),
        hoverinfo='text',
        hovertext=hover_texts,
        name='Glow'
    ))
    
    # Füge Haupt-Layer hinzu
    fig.add_trace(go.Scatter3d(
        x=[n.x for n in sorted_neurons],
        y=[n.y for n in sorted_neurons],
        z=[n.z for n in sorted_neurons],
        mode='markers',
        marker=dict(
            size=sizes,
            color=colors,
            opacity=opacities,
            line=dict(
                width=1,
                color='rgba(255,255,255,0.3)'
            ),
            symbol='circle'
        ),
        text=[n.title for n in sorted_neurons],
        hovertemplate=(
            "<b>%{text}</b><br>"
            "<extra></extra>"
        ),
        customdata=hover_texts,
        name='Neurons'
    ))
    
    # Füge Core-Punkte hinzu (kleine weiße Punkte im Zentrum)
    fig.add_trace(go.Scatter3d(
        x=[n.x * 0.95 for n in sorted_neurons],
        y=[n.y * 0.95 for n in sorted_neurons],
        z=[n.z * 0.95 for n in sorted_neurons],
        mode='markers',
        marker=dict(
            size=2,
            color=NeuronColors.PARTICLE_CORE,
            opacity=0.8
        ),
        hoverinfo='skip',
        name='Core'
    ))
    
    # Layout konfigurieren
    camera = dict(
        eye=dict(x=1.5, y=1.5, z=1.5),
        center=dict(x=0, y=0, z=0)
    )
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                visible=False,
                showgrid=False,
                showbackground=False,
                showspikes=False,
                showline=False,
                zeroline=False,
                range=[-1.5, 1.5]
            ),
            yaxis=dict(
                visible=False,
                showgrid=False,
                showbackground=False,
                showspikes=False,
                showline=False,
                zeroline=False,
                range=[-1.5, 1.5]
            ),
            zaxis=dict(
                visible=False,
                showgrid=False,
                showbackground=False,
                showspikes=False,
                showline=False,
                zeroline=False,
                range=[-1.5, 1.5]
            ),
            bgcolor=NeuronColors.PLOT_BG,
            camera=camera,
            aspectmode='cube'
        ),
        paper_bgcolor=NeuronColors.PAPER_BG,
        plot_bgcolor=NeuronColors.PLOT_BG,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                y=0.95,
                x=0.02,
                xanchor="left",
                yanchor="top",
                bgcolor=NeuronColors.BACKGROUND,
                bordercolor=NeuronColors.TEXT_SECONDARY,
                font=dict(color=NeuronColors.TEXT),
                buttons=[
                    dict(
                        label="▶ Play",
                        method="animate",
                        args=[
                            None,
                            dict(
                                frame=dict(duration=100, redraw=True),
                                fromcurrent=True,
                                transition=dict(duration=0)
                            )
                        ]
                    ),
                    dict(
                        label="⏸ Pause",
                        method="animate",
                        args=[
                            [None],
                            dict(
                                frame=dict(duration=0, redraw=False),
                                mode="immediate",
                                transition=dict(duration=0)
                            )
                        ]
                    )
                ]
            )
        ]
    )
    
    # Auto-rotation konfigurieren
    if show_rotation:
        fig.update_layout(
            scene=dict(
                camera=dict(
                    eye=dict(
                        x=1.5 * math.cos(datetime.now().timestamp() / 10),
                        y=1.5 * math.sin(datetime.now().timestamp() / 10),
                        z=1.5
                    )
                )
            )
        )
    
    return fig


# ============================================================
# TRADE HISTORY PANEL
# ============================================================

def render_trade_history_panel(neuron: NeuronData) -> None:
    """
    Render das Trade History Panel für einen ausgewählten Neuron
    
    Args:
        neuron: Das NeuronData Objekt mit Trade-Details
    """
    trade = neuron.trade_data
    
    # Berechne PnL
    pnl_pips = trade.get("pnl_pips", 0)
    pnl_color = NeuronColors.BULLISH if pnl_pips > 0 else NeuronColors.BEARISH
    pnl_icon = "📈" if pnl_pips > 0 else "📉"
    
    # Trade Type
    trade_type = trade.get("trade_type", "BUY")
    trade_icon = "🟢" if trade_type == "BUY" else "🔴"
    
    # CSS für das Panel
    st.markdown(f"""
    <style>
        .trade-panel {{
            background: linear-gradient(135deg, #1E2A38 0%, #2C3E50 100%);
            border-radius: 16px;
            padding: 24px;
            margin: 20px 0;
            border-left: 4px solid {neuron.color};
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        .trade-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .trade-title {{
            color: {NeuronColors.TEXT};
            font-size: 18px;
            font-weight: bold;
            margin: 0;
        }}
        .trade-close {{
            color: {NeuronColors.TEXT_SECONDARY};
            cursor: pointer;
            font-size: 20px;
        }}
        .trade-row {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .trade-label {{
            color: {NeuronColors.TEXT_SECONDARY};
            font-size: 13px;
        }}
        .trade-value {{
            color: {NeuronColors.TEXT};
            font-size: 14px;
            font-weight: 600;
        }}
        .trade-pnl {{
            font-size: 24px;
            font-weight: bold;
            color: {pnl_color};
            text-align: center;
            padding: 20px 0;
        }}
        .trade-sentiment {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }}
        .sentiment-bullish {{
            background-color: {NeuronColors.BULLISH}22;
            color: {NeuronColors.BULLISH};
            border: 1px solid {NeuronColors.BULLISH};
        }}
        .sentiment-bearish {{
            background-color: {NeuronColors.BEARISH}22;
            color: {NeuronColors.BEARISH};
            border: 1px solid {NeuronColors.BEARISH};
        }}
        .sentiment-neutral {{
            background-color: {NeuronColors.NEUTRAL}22;
            color: {NeuronColors.NEUTRAL};
            border: 1px solid {NeuronColors.NEUTRAL};
        }}
    </style>
    
    <div class="trade-panel">
        <div class="trade-header">
            <div>
                <h3 class="trade-title">🧠 Trade Details</h3>
                <p style="color: #8B949E; font-size: 12px; margin: 5px 0 0 0;">
                    {neuron.id} • {neuron.timestamp.strftime('%Y-%m-%d %H:%M')}
                </p>
            </div>
            <span class="trade-sentiment sentiment-{neuron.sentiment.lower()}">
                {neuron.sentiment}
            </span>
        </div>
        
        <div class="trade-row">
            <span class="trade-label">📊 Trade Type</span>
            <span class="trade-value">{trade_icon} {trade_type}</span>
        </div>
        
        <div class="trade-row">
            <span class="trade-label">💰 Entry Price</span>
            <span class="trade-value">{trade.get('entry_price', 0):.4f}</span>
        </div>
        
        <div class="trade-row">
            <span class="trade-label">🎯 Exit Price</span>
            <span class="trade-value">{trade.get('exit_price', 0):.4f}</span>
        </div>
        
        <div class="trade-row">
            <span class="trade-label">⏱️ Duration</span>
            <span class="trade-value">{trade.get('duration_hours', 0):.1f} hours</span>
        </div>
        
        <div class="trade-row">
            <span class="trade-label">⚡ Impact</span>
            <span class="trade-value" style="color: {neuron.impact_color};">
                {neuron.impact}
            </span>
        </div>
        
        <div class="trade-pnl">
            {pnl_icon} {pnl_pips:+.1f} pips
        </div>
        
        <p style="color: #8B949E; font-size: 12px; text-align: center; margin-top: 15px;">
            📝 {neuron.title}<br>
            {neuron.description[:100]}...
        </p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# HAUPTKOMPONENTE FÜR STREAMLIT
# ============================================================

def render_neuron_sphere(
    news_data: Optional[List[Dict]] = None,
    key: str = "neuron_sphere"
) -> Optional[str]:
    """
    Hauptfunktion zum Rendern der interaktiven 3D Neuronen-Kugel
    
    Args:
        news_data: Optionale Liste von News-Daten
        key: Streamlit session state key
        
    Returns:
        ID des ausgewählten Neurons oder None
    """
    # Initialisiere Session State
    if f"{key}_selected" not in st.session_state:
        st.session_state[f"{key}_selected"] = None
    
    if f"{key}_neurons" not in st.session_state or news_data:
        # Generiere Neuronen
        neurons = generate_neuron_points(
            num_points=NeuronSphereConfig.NUM_NEURONS,
            news_data=news_data
        )
        st.session_state[f"{key}_neurons"] = neurons
    
    neurons = st.session_state[f"{key}_neurons"]
    selected_id = st.session_state[f"{key}_selected"]
    
    # Layout: 2 Spalten (Kugel + Details)
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Erstelle und rendere die 3D Kugel
        fig = create_neuron_sphere_figure(
            neurons=neurons,
            selected_neuron_id=selected_id,
            show_rotation=True
        )
        
        # Rendere Plotly Chart
        selected_neuron = st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['sendDataToCloud', 'lasso2d', 'select2d'],
                'modeBarButtonsToAdd': ['toggleSpikelines'],
                'scrollZoom': True,
                'responsive': True
            }
        )
    
    with col2:
        # Zeige selected neuron details
        if selected_id:
            selected_neuron = next((n for n in neurons if n.id == selected_id), None)
            if selected_neuron:
                render_trade_history_panel(selected_neuron)
                
                # Close Button
                if st.button("❌ Schließen", key=f"{key}_close"):
                    st.session_state[f"{key}_selected"] = None
                    st.rerun()
        else:
            # Zeige Anleitung wenn nichts ausgewählt
            st.markdown(f"""
            <div style="
                background: rgba(41, 121, 255, 0.1);
                border: 1px solid {NeuronColors.PRIMARY};
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                margin-top: 20px;
            ">
                <h4 style="color: {NeuronColors.TEXT}; margin: 0 0 10px 0;">
                    🧠 FinGPT Neural Network
                </h4>
                <p style="color: {NeuronColors.TEXT_SECONDARY}; font-size: 13px; margin: 0;">
                    Klicke auf einen Neuronen-Punkt<br>
                    um die Trade-Details anzuzeigen
                </p>
                <div style="margin-top: 15px; font-size: 12px; color: {NeuronColors.TEXT_SECONDARY};">
                    <span style="color: {NeuronColors.BULLISH};">●</span> Bullish
                    <span style="margin: 0 10px;"></span>
                    <span style="color: {NeuronColors.NEUTRAL};">●</span> Neutral
                    <span style="margin: 0 10px;"></span>
                    <span style="color: {NeuronColors.BEARISH};">●</span> Bearish
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    return selected_id


def render_loading_sphere(
    message: str = "Analysiere News... 🧠",
    key: str = "loading_sphere"
) -> None:
    """
    Rendere die 3D Kugel als Loading-Animation
    
    Args:
        message: Nachricht die angezeigt wird
        key: Streamlit session state key
    """
    # Generiere "pulsierende" Neuronen für Loading
    if f"{key}_loading" not in st.session_state:
        loading_neurons = generate_neuron_points(
            num_points=NeuronSphereConfig.NUM_NEURONS,
            news_data=None
        )
        st.session_state[f"{key}_loading"] = loading_neurons
    
    loading_neurons = st.session_state[f"{key}_loading"]
    
    # Erstelle Figur mit Animation
    fig = create_neuron_sphere_figure(
        neurons=loading_neurons,
        selected_neuron_id=None,
        show_rotation=True
    )
    
    # Füge Animation Frames hinzu
    frames = []
    for t in range(60):  # 60 frames, ~10 sekunden
        angle = t * (2 * math.pi / 60)
        
        # Rotiere Punkte
        rotated_x = [n.x * math.cos(angle) - n.z * math.sin(angle) for n in loading_neurons]
        rotated_z = [n.x * math.sin(angle) + n.z * math.cos(angle) for n in loading_neurons]
        
        frame = go.Frame(
            data=[
                go.Scatter3d(
                    x=rotated_x,
                    y=[n.y for n in loading_neurons],
                    z=rotated_z
                )
            ],
            name=str(t)
        )
        frames.append(frame)
    
    fig.frames = frames
    
    # Layout mit Nachricht
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 20px;
    ">
        <h2 style="color: {NeuronColors.TEXT}; margin-bottom: 10px;">
            {message}
        </h2>
        <p style="color: {NeuronColors.TEXT_SECONDARY}; font-size: 14px;">
            FinGPT AI analysiert Marktbedingungen...
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Rendere mit Animation
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            'displayModeBar': False,
            'staticPlot': False
        }
    )


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def create_sample_news_data() -> List[Dict]:
    """Erstelle Beispieldaten für News"""
    import random
    from datetime import datetime, timedelta
    
    sample_titles = [
        "ECB Rate Decision: Interest Rates Hold at 4.50%",
        "EUR/USD Rises to 1.0950 on Strong German GDP",
        "Fed Powell: Inflation Still a Concern",
        "US Non-Farm Payrolls Beat at 275K",
        "USD/JPY Tests 150 Level",
        "EUR/GBP Breaks Key Resistance at 0.8650",
        "German ZEW Index Shows Recovery",
        "US Retail Sales Exceed Expectations",
        "BoE Signals Potential Rate Cut",
        "Gold Surges on Safe Haven Demand"
    ]
    
    sentiments = ["BULLISH", "BEARISH", "NEUTRAL"]
    impacts = ["HIGH", "MEDIUM", "LOW"]
    
    news_data = []
    for i, title in enumerate(sample_titles):
        news_data.append({
            "id": f"news_{i}",
            "title": title,
            "description": f"Full analysis for {title}. Market impact expected.",
            "sentiment": random.choice(sentiments),
            "impact": random.choice(impacts),
            "published_at": datetime.now() - timedelta(hours=i*2),
            "source": random.choice(["Reuters", "Bloomberg", "FX Street", "Investing.com"])
        })
    
    return news_data


# ============================================================
# TEST / DEMO
# ============================================================

if __name__ == "__main__":
    # Demo: Standalone Test
    st.set_page_config(
        page_title="FinGPT 3D Neuron Sphere",
        page_icon="🧠",
        layout="wide"
    )
    
    st.title("🧠 FinGPT 3D Neural Network Demo")
    
    # News Data (Demo)
    news_data = create_sample_news_data()
    
    # Render Sphere
    selected = render_neuron_sphere(news_data=news_data)
    
    if selected:
        st.success(f"Ausgewählter Neuron: {selected}")
