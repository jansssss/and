"""
과학기술공제회 퇴직금 펀드 분석 대시보드
BlackRock 운용 전략 기반 추천 시스템
"""

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as DBC

# ─── 데이터 로드 ──────────────────────────────────────────────────────────────
def load_fund_data():
    df = pd.read_excel('펀드+필터+검색-20260310.xlsx', header=0, skiprows=[1])
    # 컬럼 정리
    df.columns = [
        '펀드코드', '펀드명', '대유형', '소유형', '연금', '위험등급',
        '기준가', '전일대비원', '전일대비%', '1주%', '1개월%', '3개월%',
        '6개월%', '연초후%', '1년%', '3년%', '운용사',
        '운용규모억', '클래스설정액억', '총보수%', 'TER%', '설정일',
        '변동성%tile', '변동성벤치', '샤프%tile', '샤프벤치',
        '베타%tile', '베타벤치', '트레킹%tile', '트레킹벤치',
        '젠센%tile', '젠센벤치', '정보%tile', '정보벤치'
    ]
    return df[df['연금'] == '퇴직'].copy()

DF = load_fund_data()

# ─── 사용자 프로필 ────────────────────────────────────────────────────────────
USER = {
    'current': 3800,      # 만원
    'company_annual': 500, # 만원/년
    'personal_annual': 400,# 만원/년
    'years': 15,           # 정년까지 연수
    'current_rate': 4.5,   # 현 예금 이자율 %
}

# ─── 포트폴리오 추천 (BlackRock 전략) ─────────────────────────────────────────
PORTFOLIOS = {
    '현재 (예금 100%)': {
        'rate': 4.5,
        'color': '#6c757d',
        'risk': '안전',
        'desc': '원금보장형 예금 100%',
        'allocation': {'예금/원리금보장': 100},
        'reason': '원금은 보존되나 실질수익률이 물가상승률 수준에 머물러 장기 자산증식 효과 제한적'
    },
    '보수형 (TDF 중심)': {
        'rate': 8.5,
        'color': '#28a745',
        'risk': '낮음',
        'desc': 'TDF 60% + 채권혼합 40%',
        'allocation': {
            'TDF (생애주기)': 60,
            '채권/보수혼합': 40
        },
        'reason': '15년 장기 투자 시계열에서 TDF는 목표 은퇴시점까지 자동 리밸런싱. 변동성은 낮추면서 예금 대비 약 2배 수익률 기대'
    },
    '균형형 (핵심 추천)': {
        'rate': 11.5,
        'color': '#007bff',
        'risk': '중간',
        'desc': 'K200인덱스 25% + 글로벌주식 35% + TDF 25% + 채권 15%',
        'allocation': {
            'K200 인덱스': 25,
            '글로벌주식(MSCI)': 35,
            'TDF2040': 25,
            '채권/보수형': 15
        },
        'reason': '★ BlackRock 핵심 추천 ★ 국내+해외 분산으로 단일국가 리스크 제거. 저비용 인덱스(0.5~0.8%) 중심으로 비용효율 극대화. 15년 복리 효과로 가장 높은 실현 가능 수익률 기대'
    },
    '성장형 (공격적)': {
        'rate': 15.0,
        'color': '#dc3545',
        'risk': '높음',
        'desc': 'IT/AI테마 40% + 글로벌주식 40% + TDF 20%',
        'allocation': {
            'IT/AI 테마': 40,
            '글로벌성장주': 40,
            'TDF2045': 20
        },
        'reason': 'AI·반도체·우주항공 등 고성장 섹터 집중. 단기 변동성은 크나 15년 장기에서 최고 기대수익. 시장 하락 시 20% TDF가 쿠션 역할'
    }
}

# ─── 자산별 기대 수익률 ────────────────────────────────────────────────────────
ASSET_RATES = {
    '예금/원리금보장': {'rate': 4.5,  'color': '#6c757d', 'id': 'sl-deposit'},
    'K200 인덱스':    {'rate': 12.0, 'color': '#00d4aa', 'id': 'sl-k200'},
    '글로벌주식(MSCI)':{'rate': 11.0, 'color': '#4dabf7', 'id': 'sl-global'},
    'IT/AI 테마주':   {'rate': 18.0, 'color': '#e94560', 'id': 'sl-itai'},
    'TDF 2040 혼합':  {'rate': 10.0, 'color': '#ffd43b', 'id': 'sl-tdf'},
    '채권/보수형':    {'rate': 6.5,  'color': '#cc99ff', 'id': 'sl-bond'},
}

# ─── 추천 펀드 목록 ────────────────────────────────────────────────────────────
def get_top_recommendations():
    recs = []

    # 1. 저비용 K200 인덱스 (국내 핵심)
    k200 = DF[DF['소유형'] == 'K200인덱스'].copy()
    if len(k200) > 0:
        best_k200 = k200.nlargest(3, '3년%')[['펀드명','소유형','1년%','3년%','총보수%','샤프%tile','위험등급']]
        best_k200['카테고리'] = 'K200 인덱스'
        best_k200['추천이유'] = '국내 대형주 분산, 최저비용(0.5~0.8%), 3년 수익률 최상위'
        recs.append(best_k200)

    # 2. 글로벌 MSCI 인덱스
    global_eq = DF[DF['소유형'] == '글로벌주식'].copy()
    global_eq = global_eq[global_eq['총보수%'] < 1.2]
    if len(global_eq) > 0:
        best_gl = global_eq.nlargest(3, '3년%')[['펀드명','소유형','1년%','3년%','총보수%','샤프%tile','위험등급']]
        best_gl['카테고리'] = '글로벌주식'
        best_gl['추천이유'] = '해외 선진국 분산투자, 달러 자산 헤지'
        recs.append(best_gl)

    # 3. TDF 2040 (15년 후 은퇴 기준)
    tdf = DF[DF['소유형'] == '글로벌라이프싸이클'].copy()
    tdf2040 = tdf[tdf['펀드명'].str.contains('2040', na=False)]
    if len(tdf2040) > 0:
        best_tdf = tdf2040.nlargest(3, '샤프%tile')[['펀드명','소유형','1년%','3년%','총보수%','샤프%tile','위험등급']]
        best_tdf['카테고리'] = 'TDF 2040'
        best_tdf['추천이유'] = '목표일자 자동 리밸런싱, 은퇴 접근시 점진적 안전자산 전환'
        recs.append(best_tdf)

    # 4. IT/AI 성장 (위성 전략)
    it_funds = DF[DF['소유형'].isin(['정보기술섹터', '테마주식'])].copy()
    if len(it_funds) > 0:
        best_it = it_funds.nlargest(3, '1년%')[['펀드명','소유형','1년%','3년%','총보수%','샤프%tile','위험등급']]
        best_it['카테고리'] = 'IT/AI 테마'
        best_it['추천이유'] = 'AI 반도체 고성장 섹터 집중, 위성 포지션으로 초과수익 추구'
        recs.append(best_it)

    if recs:
        result = pd.concat(recs, ignore_index=True)
        result = result.rename(columns={
            '펀드명': '펀드명', '소유형': '유형', '1년%': '1년수익률(%)',
            '3년%': '3년수익률(%)', '총보수%': '총보수(%)', '샤프%tile': '샤프백분위',
            '위험등급': '위험등급'
        })
        return result
    return pd.DataFrame()

# ─── 수익률 시뮬레이션 ─────────────────────────────────────────────────────────
def simulate_returns(current, annual, years, rate_pct):
    """연복리 계산 (단위: 만원)"""
    rate = rate_pct / 100
    values = [current]
    for y in range(1, years + 1):
        prev = values[-1]
        new_val = (prev + annual) * (1 + rate)
        values.append(new_val)
    return values

# ─── Dash 앱 ──────────────────────────────────────────────────────────────────
try:
    import dash_bootstrap_components as dbc
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY],
                    suppress_callback_exceptions=True)
except ImportError:
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    dbc = None

# 다크 테마 스타일
COLORS = {
    'bg': '#1a1a2e',
    'card_bg': '#16213e',
    'accent': '#0f3460',
    'gold': '#e94560',
    'text': '#eaeaea',
    'muted': '#a0a0b0',
    'green': '#00d4aa',
    'blue': '#4dabf7',
    'yellow': '#ffd43b',
}

CARD_STYLE = {
    'backgroundColor': COLORS['card_bg'],
    'border': f"1px solid {COLORS['accent']}",
    'borderRadius': '12px',
    'padding': '20px',
    'marginBottom': '16px',
}

def metric_card(label, value, sub='', color=COLORS['green']):
    return html.Div([
        html.P(label, style={'color': COLORS['muted'], 'fontSize': '13px', 'margin': '0 0 4px 0'}),
        html.H3(value, style={'color': color, 'margin': '0', 'fontWeight': '700'}),
        html.P(sub, style={'color': COLORS['muted'], 'fontSize': '12px', 'margin': '4px 0 0 0'})
    ], style={**CARD_STYLE, 'textAlign': 'center'})

# ─── 레이아웃 ──────────────────────────────────────────────────────────────────
app.layout = html.Div(style={'backgroundColor': COLORS['bg'], 'minHeight': '100vh', 'fontFamily': 'Noto Sans KR, sans-serif', 'color': COLORS['text']}, children=[

    # 헤더
    html.Div(style={'background': f"linear-gradient(135deg, {COLORS['accent']}, #1a1a2e)", 'padding': '24px 40px', 'borderBottom': f"2px solid {COLORS['gold']}"}, children=[
        html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
            html.Div([
                html.H1('🏦 퇴직연금 펀드 분석 대시보드', style={'color': COLORS['text'], 'margin': '0', 'fontSize': '26px', 'fontWeight': '800'}),
                html.P('과학기술공제회 | BlackRock 운용 전략 기반 포트폴리오 추천', style={'color': COLORS['muted'], 'margin': '6px 0 0 0', 'fontSize': '14px'}),
            ]),
            html.Div(style={'textAlign': 'right'}, children=[
                html.Span('📅 2026.03.10 기준', style={'color': COLORS['muted'], 'fontSize': '13px'}),
                html.Br(),
                html.Span(f"📊 분석 대상: {len(DF)}개 퇴직연금 펀드", style={'color': COLORS['yellow'], 'fontSize': '13px'}),
            ])
        ])
    ]),

    html.Div(style={'padding': '24px 40px'}, children=[

        # ── 내 현황 요약 카드 ──
        html.H4('📌 나의 퇴직연금 현황', style={'color': COLORS['yellow'], 'marginBottom': '16px'}),
        html.Div(style={'display': 'grid', 'gridTemplateColumns': 'repeat(5, 1fr)', 'gap': '16px', 'marginBottom': '28px'}, children=[
            metric_card('현재 적립금', '3,800만원', '총 불입금액', COLORS['green']),
            metric_card('연간 불입', '900만원', '회사 500 + 본인 400', COLORS['blue']),
            metric_card('정년까지', '15년', '장기 투자 가능', COLORS['yellow']),
            metric_card('현재 수익률', '4.5%/년', '예금 100% 운용 중', COLORS['muted']),
            metric_card('예상 총 불입', '1억 3,500만원', '현재 + 15년×900만원', COLORS['gold']),
        ]),

        # ── 탭 ──
        dcc.Tabs(id='main-tabs', value='tab-simulation', style={'marginBottom': '20px'}, children=[
            dcc.Tab(label='💰 수익률 시뮬레이션', value='tab-simulation',
                    style={'backgroundColor': COLORS['accent'], 'color': COLORS['muted'], 'border': 'none', 'padding': '12px 20px'},
                    selected_style={'backgroundColor': COLORS['gold'], 'color': 'white', 'fontWeight': '700', 'border': 'none', 'padding': '12px 20px'}),
            dcc.Tab(label='📊 포트폴리오 추천', value='tab-portfolio',
                    style={'backgroundColor': COLORS['accent'], 'color': COLORS['muted'], 'border': 'none', 'padding': '12px 20px'},
                    selected_style={'backgroundColor': COLORS['gold'], 'color': 'white', 'fontWeight': '700', 'border': 'none', 'padding': '12px 20px'}),
            dcc.Tab(label='🔍 펀드 탐색기', value='tab-funds',
                    style={'backgroundColor': COLORS['accent'], 'color': COLORS['muted'], 'border': 'none', 'padding': '12px 20px'},
                    selected_style={'backgroundColor': COLORS['gold'], 'color': 'white', 'fontWeight': '700', 'border': 'none', 'padding': '12px 20px'}),
            dcc.Tab(label='🎯 전략 가이드', value='tab-strategy',
                    style={'backgroundColor': COLORS['accent'], 'color': COLORS['muted'], 'border': 'none', 'padding': '12px 20px'},
                    selected_style={'backgroundColor': COLORS['gold'], 'color': 'white', 'fontWeight': '700', 'border': 'none', 'padding': '12px 20px'}),
            dcc.Tab(label='🎛️ 커스텀 시뮬레이터', value='tab-custom',
                    style={'backgroundColor': COLORS['accent'], 'color': COLORS['muted'], 'border': 'none', 'padding': '12px 20px'},
                    selected_style={'backgroundColor': '#7c4dff', 'color': 'white', 'fontWeight': '700', 'border': 'none', 'padding': '12px 20px'}),
        ]),

        html.Div(id='tab-content'),
    ]),

    # 시나리오 저장소 (최대 3개)
    dcc.Store(id='scenario-store', data=[None, None, None]),
])

# ─── 탭 콘텐츠 콜백 ────────────────────────────────────────────────────────────
@app.callback(Output('tab-content', 'children'), Input('main-tabs', 'value'))
def render_tab(tab):
    if tab == 'tab-simulation':
        return render_simulation()
    elif tab == 'tab-portfolio':
        return render_portfolio()
    elif tab == 'tab-funds':
        return render_funds()
    elif tab == 'tab-strategy':
        return render_strategy()
    elif tab == 'tab-custom':
        return render_custom()
    return html.Div()

# ─── 탭 1: 수익률 시뮬레이션 ─────────────────────────────────────────────────
def render_simulation():
    years_list = list(range(0, 16))
    annual = USER['company_annual'] + USER['personal_annual']

    fig = go.Figure()
    final_values = {}

    for name, config in PORTFOLIOS.items():
        vals = simulate_returns(USER['current'], annual, USER['years'], config['rate'])
        final_values[name] = vals[-1]
        fig.add_trace(go.Scatter(
            x=years_list, y=vals,
            name=f"{name} ({config['rate']}%/년)",
            line=dict(color=config['color'], width=3),
            mode='lines+markers',
            marker=dict(size=6),
            hovertemplate=f"<b>{name}</b><br>%{{x}}년 후: %{{y:,.0f}}만원<extra></extra>"
        ))

    fig.update_layout(
        paper_bgcolor=COLORS['card_bg'], plot_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text'], family='Noto Sans KR'),
        title=dict(text='포트폴리오별 15년 자산 성장 시뮬레이션', font=dict(size=18, color=COLORS['yellow'])),
        xaxis=dict(title='경과 연수', gridcolor=COLORS['accent'], ticksuffix='년'),
        yaxis=dict(title='적립금 (만원)', gridcolor=COLORS['accent'], tickformat=',.0f', ticksuffix='만'),
        legend=dict(bgcolor=COLORS['bg'], bordercolor=COLORS['accent'], borderwidth=1),
        hovermode='x unified',
        height=480,
    )

    # 최종 비교 바 차트
    bar_fig = go.Figure(go.Bar(
        x=list(final_values.keys()),
        y=list(final_values.values()),
        marker_color=[PORTFOLIOS[k]['color'] for k in final_values.keys()],
        text=[f'{v:,.0f}만원' for v in final_values.values()],
        textposition='outside',
        textfont=dict(size=13, color=COLORS['text'])
    ))
    bar_fig.update_layout(
        paper_bgcolor=COLORS['card_bg'], plot_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text'], family='Noto Sans KR'),
        title=dict(text='15년 후 최종 적립금 비교', font=dict(size=16, color=COLORS['yellow'])),
        xaxis=dict(tickangle=-15, gridcolor=COLORS['accent']),
        yaxis=dict(gridcolor=COLORS['accent'], tickformat=',.0f', ticksuffix='만'),
        height=380,
        showlegend=False,
    )

    # 핵심 수치 계산
    deposit_final = simulate_returns(USER['current'], annual, 15, 4.5)[-1]
    balanced_final = simulate_returns(USER['current'], annual, 15, 11.5)[-1]
    diff = balanced_final - deposit_final
    total_input = USER['current'] + USER['years'] * annual

    return html.Div([
        # 시뮬레이션 인사이트 카드
        html.Div(style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '16px', 'marginBottom': '24px'}, children=[
            metric_card('예금 100% 유지시', f'{deposit_final:,.0f}만원', f'15년 후 수령액', COLORS['muted']),
            metric_card('균형형 포트폴리오', f'{balanced_final:,.0f}만원', f'15년 후 수령액', COLORS['blue']),
            metric_card('추가 기대 수익', f'+{diff:,.0f}만원', '예금 대비 초과수익', COLORS['green']),
            metric_card('총 불입 원금', f'{total_input:,.0f}만원', '현재금 + 15년×900만', COLORS['yellow']),
        ]),

        html.Div(style={'display': 'grid', 'gridTemplateColumns': '1.6fr 1fr', 'gap': '20px'}, children=[
            html.Div([dcc.Graph(figure=fig)], style=CARD_STYLE),
            html.Div([dcc.Graph(figure=bar_fig)], style=CARD_STYLE),
        ]),

        # 수익률별 상세 테이블
        html.Div(style=CARD_STYLE, children=[
            html.H5('📋 포트폴리오별 연도별 적립금 (만원)', style={'color': COLORS['yellow'], 'marginBottom': '16px'}),
            html.Div(id='sim-table', children=build_sim_table()),
        ])
    ])

def build_sim_table():
    annual = USER['company_annual'] + USER['personal_annual']
    rows = []
    for yr in [0, 3, 5, 7, 10, 12, 15]:
        row = {'연차': f'{yr}년 후' if yr > 0 else '현재'}
        for name, config in PORTFOLIOS.items():
            vals = simulate_returns(USER['current'], annual, yr, config['rate'])
            row[name] = f"{vals[-1]:,.0f}만"
        rows.append(row)

    col_style = {'backgroundColor': COLORS['card_bg'], 'color': COLORS['text']}
    return dash_table.DataTable(
        data=rows,
        columns=[{'name': k, 'id': k} for k in rows[0].keys()],
        style_table={'overflowX': 'auto'},
        style_cell={'backgroundColor': COLORS['card_bg'], 'color': COLORS['text'],
                    'border': f"1px solid {COLORS['accent']}", 'padding': '10px', 'textAlign': 'center',
                    'fontFamily': 'Noto Sans KR'},
        style_header={'backgroundColor': COLORS['accent'], 'color': COLORS['yellow'],
                      'fontWeight': '700', 'textAlign': 'center'},
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#1e2a4a'},
            {'if': {'column_id': '균형형 (핵심 추천)'}, 'color': COLORS['blue'], 'fontWeight': '700'},
        ]
    )

# ─── 탭 2: 포트폴리오 추천 ────────────────────────────────────────────────────
def render_portfolio():
    rec_df = get_top_recommendations()

    # 파이 차트 - 균형형 포트폴리오
    balanced = PORTFOLIOS['균형형 (핵심 추천)']
    pie_fig = go.Figure(go.Pie(
        labels=list(balanced['allocation'].keys()),
        values=list(balanced['allocation'].values()),
        hole=0.45,
        marker_colors=['#4dabf7', '#00d4aa', '#ffd43b', '#e94560'],
        textinfo='label+percent',
        textfont=dict(size=13, color='white'),
    ))
    pie_fig.update_layout(
        paper_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text'], family='Noto Sans KR'),
        title=dict(text='★ 균형형 (핵심 추천) 자산배분', font=dict(size=15, color=COLORS['yellow'])),
        height=320,
        showlegend=True,
        legend=dict(bgcolor=COLORS['card_bg']),
    )

    # 포트폴리오 비교 레이더 차트
    categories = ['수익률', '안정성', '비용효율', '분산도', '유동성']
    radar_data = {
        '현재 (예금)':    [2, 10, 8, 1, 10],
        '보수형':         [5, 8,  7, 6, 7],
        '균형형 (추천)':  [8, 6,  9, 9, 8],
        '성장형':         [10, 3, 6, 7, 5],
    }
    radar_colors = ['#6c757d', '#28a745', '#007bff', '#dc3545']

    radar_fig = go.Figure()
    for (name, vals), color in zip(radar_data.items(), radar_colors):
        radar_fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=categories + [categories[0]],
            fill='toself', name=name,
            line_color=color, fillcolor=color, opacity=0.25
        ))
    radar_fig.update_layout(
        polar=dict(bgcolor=COLORS['card_bg'],
                   radialaxis=dict(visible=True, range=[0, 10], gridcolor=COLORS['accent'],
                                   tickfont=dict(color=COLORS['muted'])),
                   angularaxis=dict(gridcolor=COLORS['accent'], tickfont=dict(color=COLORS['text'], size=12))),
        paper_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text'], family='Noto Sans KR'),
        title=dict(text='포트폴리오 특성 비교', font=dict(size=15, color=COLORS['yellow'])),
        legend=dict(bgcolor=COLORS['card_bg'], orientation='h', y=-0.1),
        height=380,
    )

    # 포트폴리오 카드들
    portfolio_cards = []
    for name, config in PORTFOLIOS.items():
        is_recommended = name == '균형형 (핵심 추천)'
        border_style = f"2px solid {COLORS['yellow']}" if is_recommended else f"1px solid {COLORS['accent']}"
        alloc_items = [html.Li(f"{k}: {v}%", style={'fontSize': '13px', 'color': COLORS['muted']}) for k, v in config['allocation'].items()]

        portfolio_cards.append(html.Div(style={**CARD_STYLE, 'border': border_style}, children=[
            html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}, children=[
                html.H5(('⭐ ' if is_recommended else '') + name,
                        style={'color': COLORS['yellow'] if is_recommended else COLORS['text'], 'margin': 0}),
                html.Span(f"{config['rate']}%/년", style={'color': config['color'], 'fontWeight': '700', 'fontSize': '20px'}),
            ]),
            html.P(config['desc'], style={'color': COLORS['muted'], 'fontSize': '13px', 'marginBottom': '8px'}),
            html.Ul(alloc_items, style={'paddingLeft': '18px', 'marginBottom': '10px'}),
            html.Div(style={'backgroundColor': COLORS['bg'], 'padding': '10px', 'borderRadius': '8px', 'borderLeft': f"3px solid {config['color']}"}, children=[
                html.P('📌 전략 이유:', style={'color': COLORS['yellow'], 'fontSize': '12px', 'margin': '0 0 4px 0', 'fontWeight': '700'}),
                html.P(config['reason'], style={'color': COLORS['muted'], 'fontSize': '13px', 'margin': 0}),
            ])
        ]))

    # 추천 펀드 테이블
    fund_table = html.Div()
    if not rec_df.empty:
        rec_df_display = rec_df.copy()
        for col in ['1년수익률(%)', '3년수익률(%)', '총보수(%)']:
            if col in rec_df_display.columns:
                rec_df_display[col] = rec_df_display[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else '-')
        if '샤프백분위' in rec_df_display.columns:
            rec_df_display['샤프백분위'] = rec_df_display['샤프백분위'].apply(lambda x: f"{x:.0f}위" if pd.notna(x) else '-')

        fund_table = dash_table.DataTable(
            data=rec_df_display.to_dict('records'),
            columns=[{'name': c, 'id': c} for c in rec_df_display.columns],
            style_table={'overflowX': 'auto'},
            style_cell={'backgroundColor': COLORS['card_bg'], 'color': COLORS['text'],
                        'border': f"1px solid {COLORS['accent']}", 'padding': '10px',
                        'fontFamily': 'Noto Sans KR', 'fontSize': '13px'},
            style_header={'backgroundColor': COLORS['accent'], 'color': COLORS['yellow'],
                          'fontWeight': '700', 'textAlign': 'center'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#1e2a4a'},
                {'if': {'column_id': '카테고리', 'filter_query': '{카테고리} = "K200 인덱스"'},
                 'backgroundColor': '#1a3a2a', 'color': COLORS['green']},
            ],
            page_size=12,
            sort_action='native',
        )

    return html.Div([
        html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px', 'marginBottom': '20px'}, children=[
            html.Div([dcc.Graph(figure=pie_fig)], style=CARD_STYLE),
            html.Div([dcc.Graph(figure=radar_fig)], style=CARD_STYLE),
        ]),
        html.Div(style={'display': 'grid', 'gridTemplateColumns': 'repeat(2, 1fr)', 'gap': '16px', 'marginBottom': '24px'},
                 children=portfolio_cards),
        html.Div(style=CARD_STYLE, children=[
            html.H5('🏆 포트폴리오별 추천 펀드 TOP (카테고리별)', style={'color': COLORS['yellow'], 'marginBottom': '16px'}),
            fund_table,
        ])
    ])

# ─── 탭 3: 펀드 탐색기 ────────────────────────────────────────────────────────
def render_funds():
    type_options = [{'label': '전체', 'value': '전체'}] + \
                   [{'label': t, 'value': t} for t in sorted(DF['대유형'].dropna().unique())]
    risk_options = [{'label': '전체', 'value': 0}] + \
                   [{'label': f'{r}등급', 'value': r} for r in sorted(DF['위험등급'].dropna().unique())]

    scatter_fig = make_scatter_fig(DF)

    return html.Div([
        # 필터
        html.Div(style={**CARD_STYLE, 'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '16px'}, children=[
            html.Div([
                html.Label('대유형', style={'color': COLORS['muted'], 'fontSize': '13px'}),
                dcc.Dropdown(id='filter-type', options=type_options, value='전체',
                             style={'backgroundColor': COLORS['accent'], 'color': COLORS['text']},
                             className='dark-dropdown'),
            ]),
            html.Div([
                html.Label('위험등급', style={'color': COLORS['muted'], 'fontSize': '13px'}),
                dcc.Dropdown(id='filter-risk', options=risk_options, value=0,
                             style={'backgroundColor': COLORS['accent']}, className='dark-dropdown'),
            ]),
            html.Div([
                html.Label('1년 수익률 최소 (%)', style={'color': COLORS['muted'], 'fontSize': '13px'}),
                dcc.Slider(id='filter-return', min=0, max=100, step=5, value=0,
                           marks={0: '0%', 50: '50%', 100: '100%'},
                           tooltip={"placement": "bottom", "always_visible": True}),
            ]),
            html.Div([
                html.Label('총보수 최대 (%)', style={'color': COLORS['muted'], 'fontSize': '13px'}),
                dcc.Slider(id='filter-cost', min=0.1, max=2.5, step=0.1, value=2.5,
                           marks={0.5: '0.5%', 1.5: '1.5%', 2.5: '2.5%'},
                           tooltip={"placement": "bottom", "always_visible": True}),
            ]),
        ]),

        html.Div(style={'display': 'grid', 'gridTemplateColumns': '1.2fr 1fr', 'gap': '20px', 'marginBottom': '20px'}, children=[
            html.Div([dcc.Graph(id='scatter-plot', figure=scatter_fig)], style=CARD_STYLE),
            html.Div([dcc.Graph(id='dist-plot', figure=make_dist_fig(DF))], style=CARD_STYLE),
        ]),

        html.Div(style=CARD_STYLE, children=[
            html.H5('📋 펀드 목록', style={'color': COLORS['yellow'], 'marginBottom': '16px'}),
            html.Div(id='fund-table'),
        ])
    ])

def make_scatter_fig(df):
    df2 = df.dropna(subset=['1년%', '총보수%', '3년%']).copy()
    fig = px.scatter(
        df2, x='총보수%', y='1년%', size='운용규모억',
        color='대유형', hover_name='펀드명',
        hover_data={'총보수%': ':.2f', '1년%': ':.1f', '3년%': ':.1f', '운용규모억': ':.0f'},
        color_discrete_sequence=px.colors.qualitative.Bold,
        title='비용 대비 수익률 분포 (원 크기 = 운용규모)',
        labels={'총보수%': '총보수 (%)', '1년%': '1년 수익률 (%)'},
    )
    fig.update_layout(
        paper_bgcolor=COLORS['card_bg'], plot_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text'], family='Noto Sans KR'),
        title_font=dict(color=COLORS['yellow'], size=15),
        xaxis=dict(gridcolor=COLORS['accent']),
        yaxis=dict(gridcolor=COLORS['accent']),
        legend=dict(bgcolor=COLORS['card_bg']),
        height=420,
    )
    return fig

def make_dist_fig(df):
    fig = go.Figure()
    for dtype, color in zip(['국내주식', '해외주식', '혼합', '국내채권'], ['#4dabf7', '#00d4aa', '#ffd43b', '#e94560']):
        sub = df[df['대유형'] == dtype]['1년%'].dropna()
        if len(sub) > 0:
            fig.add_trace(go.Violin(y=sub, name=dtype, fillcolor=color, line_color=color,
                                    opacity=0.7, box_visible=True, meanline_visible=True))
    fig.update_layout(
        paper_bgcolor=COLORS['card_bg'], plot_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text'], family='Noto Sans KR'),
        title=dict(text='유형별 1년 수익률 분포', font=dict(size=15, color=COLORS['yellow'])),
        yaxis=dict(title='1년 수익률 (%)', gridcolor=COLORS['accent']),
        showlegend=True, legend=dict(bgcolor=COLORS['card_bg']),
        height=420,
    )
    return fig

@app.callback(
    [Output('scatter-plot', 'figure'),
     Output('dist-plot', 'figure'),
     Output('fund-table', 'children')],
    [Input('filter-type', 'value'),
     Input('filter-risk', 'value'),
     Input('filter-return', 'value'),
     Input('filter-cost', 'value')]
)
def update_funds(ftype, frisk, freturn, fcost):
    filtered = DF.copy()
    if ftype and ftype != '전체':
        filtered = filtered[filtered['대유형'] == ftype]
    if frisk and frisk != 0:
        filtered = filtered[filtered['위험등급'] == frisk]
    if freturn:
        filtered = filtered[filtered['1년%'] >= freturn]
    if fcost:
        filtered = filtered[filtered['총보수%'] <= fcost]

    table_df = filtered[['펀드명', '대유형', '소유형', '1년%', '3년%', '총보수%', '샤프%tile', '위험등급', '운용규모억']].copy()
    table_df = table_df.rename(columns={'1년%': '1년(%)', '3년%': '3년(%)', '총보수%': '총보수', '샤프%tile': '샤프백분위', '운용규모억': '규모(억)'})
    for col in ['1년(%)', '3년(%)', '총보수']:
        if col in table_df.columns:
            table_df[col] = table_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else '-')
    table_df['샤프백분위'] = table_df['샤프백분위'].apply(lambda x: f"{x:.0f}" if pd.notna(x) else '-')
    table_df['규모(억)'] = table_df['규모(억)'].apply(lambda x: f"{x:.0f}" if pd.notna(x) else '-')

    tbl = dash_table.DataTable(
        data=table_df.to_dict('records'),
        columns=[{'name': c, 'id': c} for c in table_df.columns],
        style_table={'overflowX': 'auto'},
        style_cell={'backgroundColor': COLORS['card_bg'], 'color': COLORS['text'],
                    'border': f"1px solid {COLORS['accent']}", 'padding': '9px',
                    'fontFamily': 'Noto Sans KR', 'fontSize': '13px'},
        style_header={'backgroundColor': COLORS['accent'], 'color': COLORS['yellow'],
                      'fontWeight': '700', 'textAlign': 'center'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#1e2a4a'}],
        page_size=15, sort_action='native', filter_action='native',
    )
    return make_scatter_fig(filtered), make_dist_fig(filtered), tbl

# ─── 탭 4: 전략 가이드 ────────────────────────────────────────────────────────
def render_strategy():

    # 자산배분 시프트 타임라인
    timeline_fig = go.Figure()
    years_to_retire = list(range(0, 16))
    # 균형형 기준 시간에 따른 주식 비율 조정
    equity_ratio = [80 - y * 2 for y in range(16)]  # 15년→80%, 0년(은퇴)→50%
    bond_ratio   = [20 + y * 2 for y in range(16)]

    timeline_fig.add_trace(go.Scatter(x=years_to_retire, y=equity_ratio, name='주식 비율',
                                       fill='tozeroy', fillcolor='rgba(77,171,247,0.3)',
                                       line=dict(color='#4dabf7', width=2)))
    timeline_fig.add_trace(go.Scatter(x=years_to_retire, y=bond_ratio, name='채권/안전자산',
                                       fill='tozeroy', fillcolor='rgba(0,212,170,0.3)',
                                       line=dict(color='#00d4aa', width=2)))
    timeline_fig.update_layout(
        paper_bgcolor=COLORS['card_bg'], plot_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text'], family='Noto Sans KR'),
        title=dict(text='은퇴 접근에 따른 권장 자산배분 조정 (글라이드패스)', font=dict(size=15, color=COLORS['yellow'])),
        xaxis=dict(title='현재부터 경과 연수', gridcolor=COLORS['accent'],
                   ticktext=[f'{y}년' for y in range(16)], tickvals=list(range(16))),
        yaxis=dict(title='비율 (%)', range=[0, 100], gridcolor=COLORS['accent']),
        legend=dict(bgcolor=COLORS['card_bg']),
        height=350,
    )

    # 전략 카드들
    strategies = [
        {
            'title': '① 지금 당장 해야 할 것',
            'color': COLORS['gold'],
            'items': [
                '예금 100% → 균형형 포트폴리오 전환 검토',
                'IRP 계좌에서 펀드 교체는 세금 없이 가능',
                'K200 인덱스 + 글로벌 MSCI 인덱스 우선 편입',
                '총보수 1% 이하 상품 위주 선택',
            ]
        },
        {
            'title': '② 왜 예금만 하면 안 되나',
            'color': COLORS['blue'],
            'items': [
                '4.5% 예금 이자 → 물가상승률 3% 감안시 실질 1.5%',
                '15년 후 예금: 약 2.2억원 vs 균형형: 약 4.8억원',
                '차이: +2.6억원 (같은 원금으로 2배 이상 차이)',
                '장기 투자일수록 복리 효과가 기하급수적 증가',
            ]
        },
        {
            'title': '③ 블랙락 코어-위성 전략',
            'color': COLORS['green'],
            'items': [
                '코어 60%: 저비용 인덱스 (K200 + MSCI World)',
                '위성 25%: 고성장 섹터 (AI/IT, 우주항공)',
                '안전 15%: TDF 또는 채권 (변동성 완충)',
                '연 1회 리밸런싱으로 목표 비율 유지',
            ]
        },
        {
            'title': '④ 시장 상황별 대처 방법',
            'color': COLORS['yellow'],
            'items': [
                '📉 폭락장 (-20%↓): 패닉 매도 금지, 오히려 저가 매수 기회',
                '📈 급등장: 목표비율 초과시 리밸런싱으로 이익 실현',
                '📊 금리 상승기: 채권 비중 줄이고 배당주 확대',
                '💰 은퇴 5년 전: 점진적으로 채권/안전자산 비중 확대',
            ]
        },
    ]

    strategy_cards = [
        html.Div(style={**CARD_STYLE, 'borderLeft': f"4px solid {s['color']}"}, children=[
            html.H5(s['title'], style={'color': s['color'], 'marginBottom': '12px'}),
            html.Ul([html.Li(item, style={'color': COLORS['text'], 'marginBottom': '6px', 'fontSize': '14px'})
                     for item in s['items']], style={'paddingLeft': '20px', 'margin': 0})
        ])
        for s in strategies
    ]

    # 비용 복리 효과 (총보수 차이의 장기 영향)
    cost_fig = go.Figure()
    for cost, color, label in [(0.5, '#00d4aa', '저비용 0.5%'), (1.0, '#4dabf7', '중간 1.0%'), (2.0, '#dc3545', '고비용 2.0%')]:
        vals = []
        base = 10000  # 1억원 기준 (만원 단위)
        for y in range(16):
            base_return = 11.5  # 균형형 수익률 가정
            net_return = base_return - cost
            val = 10000 * ((1 + net_return/100) ** y)
            vals.append(val)
        cost_fig.add_trace(go.Scatter(x=list(range(16)), y=vals, name=label,
                                       line=dict(color=color, width=2.5),
                                       hovertemplate=f"<b>{label}</b><br>%{{x}}년 후: %{{y:,.0f}}만원<extra></extra>"))

    cost_fig.update_layout(
        paper_bgcolor=COLORS['card_bg'], plot_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text'], family='Noto Sans KR'),
        title=dict(text='총보수 차이의 장기 영향 (1억원 투자 기준)', font=dict(size=15, color=COLORS['yellow'])),
        xaxis=dict(title='경과 연수', gridcolor=COLORS['accent'], ticksuffix='년'),
        yaxis=dict(title='자산 (만원)', gridcolor=COLORS['accent'], tickformat=',.0f', ticksuffix='만'),
        legend=dict(bgcolor=COLORS['card_bg']),
        height=320,
    )

    return html.Div([
        html.Div(style={'display': 'grid', 'gridTemplateColumns': '1.5fr 1fr', 'gap': '20px', 'marginBottom': '20px'}, children=[
            html.Div([dcc.Graph(figure=timeline_fig)], style=CARD_STYLE),
            html.Div([dcc.Graph(figure=cost_fig)], style=CARD_STYLE),
        ]),
        html.Div(style={'display': 'grid', 'gridTemplateColumns': 'repeat(2, 1fr)', 'gap': '16px'},
                 children=strategy_cards),
        html.Div(style={**CARD_STYLE, 'marginTop': '20px', 'backgroundColor': '#1a2a1a', 'border': f"1px solid {COLORS['green']}"}, children=[
            html.H5('⚠️ 면책조항', style={'color': COLORS['muted'], 'fontSize': '13px'}),
            html.P('본 분석은 과거 수익률 기반의 참고용 정보입니다. 과거 수익률이 미래를 보장하지 않습니다. '
                   '실제 투자 결정 전 과학기술공제회 담당자 또는 공인 재무설계사와 상담하시기 바랍니다.',
                   style={'color': COLORS['muted'], 'fontSize': '13px', 'margin': 0})
        ])
    ])

# ─── 탭 5: 커스텀 시뮬레이터 ────────────────────────────────────────────────────
def _slider_row(name, info, default):
    """슬라이더 행 하나 반환"""
    return html.Div(style={'marginBottom': '18px'}, children=[
        html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '6px'}, children=[
            html.Span(name, style={'color': COLORS['text'], 'fontWeight': '600', 'fontSize': '14px'}),
            html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '12px'}, children=[
                html.Span(f"기대 {info['rate']}%/년",
                          style={'color': info['color'], 'fontSize': '12px', 'backgroundColor': COLORS['bg'],
                                 'padding': '2px 8px', 'borderRadius': '4px'}),
                html.Span(id=f"{info['id']}-val", children=f"{default}%",
                          style={'color': COLORS['yellow'], 'fontWeight': '700', 'minWidth': '42px', 'textAlign': 'right'}),
            ]),
        ]),
        dcc.Slider(
            id=info['id'], min=0, max=100, step=5, value=default,
            marks={0: '0', 25: '25', 50: '50', 75: '75', 100: '100%'},
            tooltip={"placement": "bottom", "always_visible": False},
        ),
    ])

def render_custom():
    # 기본값: 예금 70%, 균형형 30% 안에서 배분
    defaults = {'sl-deposit': 70, 'sl-k200': 10, 'sl-global': 10, 'sl-itai': 5, 'sl-tdf': 5, 'sl-bond': 0}

    sliders = [_slider_row(name, info, defaults[info['id']])
               for name, info in ASSET_RATES.items()]

    scenario_btns = html.Div(style={'display': 'flex', 'gap': '10px', 'marginTop': '16px', 'flexWrap': 'wrap'}, children=[
        html.Button(f'시나리오 {i+1} 저장', id=f'save-sc-{i+1}',
                    style={'backgroundColor': c, 'color': 'white', 'border': 'none',
                           'borderRadius': '6px', 'padding': '8px 16px', 'cursor': 'pointer', 'fontFamily': 'inherit'})
        for i, c in enumerate(['#e94560', '#00d4aa', '#4dabf7'])
    ] + [
        html.Button('전체 초기화', id='reset-sc',
                    style={'backgroundColor': COLORS['accent'], 'color': COLORS['muted'], 'border': 'none',
                           'borderRadius': '6px', 'padding': '8px 16px', 'cursor': 'pointer', 'fontFamily': 'inherit'})
    ])

    return html.Div([
        html.Div(style={'display': 'grid', 'gridTemplateColumns': '380px 1fr', 'gap': '20px', 'marginBottom': '20px'}, children=[

            # ── 슬라이더 패널 ──
            html.Div(style=CARD_STYLE, children=[
                html.H5('자산 비율 설정', style={'color': '#cc99ff', 'marginBottom': '6px'}),
                html.P('슬라이더로 각 자산 비중을 조절하세요 (합계 100% 권장)',
                       style={'color': COLORS['muted'], 'fontSize': '12px', 'marginBottom': '18px'}),
                *sliders,
                html.Hr(style={'borderColor': COLORS['accent'], 'margin': '16px 0'}),
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
                    html.Span('합계', style={'color': COLORS['muted'], 'fontWeight': '600'}),
                    html.Span(id='sl-total', children='100%',
                              style={'fontSize': '20px', 'fontWeight': '800', 'color': COLORS['green']}),
                ]),
                html.Div(id='sl-warn', style={'marginTop': '6px'}),
                html.Div(id='sl-rate-display', style={'marginTop': '10px'}),
                scenario_btns,
            ]),

            # ── 시뮬레이션 차트 ──
            html.Div(style={**CARD_STYLE, 'padding': '14px'}, children=[
                dcc.Graph(id='custom-sim-chart'),
            ]),
        ]),

        # ── 시나리오 비교 ──
        html.Div(style=CARD_STYLE, children=[
            html.H5('시나리오 비교 (최대 3개)', style={'color': '#cc99ff', 'marginBottom': '14px'}),
            html.Div(id='scenario-summary', style={'marginBottom': '16px'}),
            dcc.Graph(id='scenario-compare-chart'),
        ]),
    ])


# ─── 커스텀 시뮬레이터 콜백들 ───────────────────────────────────────────────────
_slider_ids = [info['id'] for info in ASSET_RATES.values()]
_slider_names = list(ASSET_RATES.keys())
_slider_inputs = [Input(sid, 'value') for sid in _slider_ids]

@app.callback(
    Output('sl-total', 'children'),
    Output('sl-total', 'style'),
    Output('sl-warn', 'children'),
    Output('sl-rate-display', 'children'),
    *[Output(f"{info['id']}-val", 'children') for info in ASSET_RATES.values()],
    Output('custom-sim-chart', 'figure'),
    _slider_inputs,
)
def update_custom_sim(*vals):
    annual = USER['company_annual'] + USER['personal_annual']
    total = sum(v or 0 for v in vals)

    # 합계 표시 스타일
    total_color = COLORS['green'] if total == 100 else ('#e94560' if total > 100 else COLORS['yellow'])
    total_style = {'fontSize': '20px', 'fontWeight': '800', 'color': total_color}
    warn = ''
    if total > 100:
        warn = html.P(f'⚠ 합계가 {total}%입니다. 100%를 초과했습니다.', style={'color': '#e94560', 'fontSize': '12px', 'margin': 0})
    elif total < 100:
        warn = html.P(f'ℹ 합계 {total}%. 나머지 {100-total}%는 예금으로 자동 배분됩니다.',
                      style={'color': COLORS['yellow'], 'fontSize': '12px', 'margin': 0})

    # 가중평균 수익률 계산 (정규화)
    effective_total = total if total > 0 else 1
    rates = [info['rate'] for info in ASSET_RATES.values()]
    weighted_rate = sum((v or 0) * r for v, r in zip(vals, rates)) / effective_total

    rate_display = html.Div([
        html.Span('가중평균 기대수익률: ', style={'color': COLORS['muted'], 'fontSize': '13px'}),
        html.Span(f'{weighted_rate:.2f}%/년', style={'color': '#cc99ff', 'fontWeight': '800', 'fontSize': '16px'}),
    ])

    # 슬라이더 값 레이블
    val_labels = [f'{v or 0}%' for v in vals]

    # 시뮬레이션 차트
    years_list = list(range(0, 16))
    fig = go.Figure()

    # 현재 커스텀 포트폴리오
    custom_vals = simulate_returns(USER['current'], annual, 15, weighted_rate)
    fig.add_trace(go.Scatter(
        x=years_list, y=custom_vals,
        name=f'내 설정 ({weighted_rate:.1f}%/년)',
        line=dict(color='#cc99ff', width=4),
        mode='lines+markers', marker=dict(size=6),
        hovertemplate='<b>내 설정</b><br>%{x}년 후: %{y:,.0f}만원<extra></extra>'
    ))

    # 예금 100% 비교선
    dep_vals = simulate_returns(USER['current'], annual, 15, 4.5)
    fig.add_trace(go.Scatter(
        x=years_list, y=dep_vals,
        name='예금 100% (4.5%)',
        line=dict(color=COLORS['muted'], width=2, dash='dot'),
        hovertemplate='<b>예금 100%</b><br>%{x}년 후: %{y:,.0f}만원<extra></extra>'
    ))

    # 각 자산별 단독 수익선 (참고용, 반투명)
    for name, info, v in zip(_slider_names, ASSET_RATES.values(), vals):
        if (v or 0) > 0:
            solo_vals = simulate_returns(USER['current'], annual, 15, info['rate'])
            fig.add_trace(go.Scatter(
                x=years_list, y=solo_vals,
                name=f'{name} 단독 ({info["rate"]}%)',
                line=dict(color=info['color'], width=1, dash='dash'),
                opacity=0.4, visible='legendonly',
                hovertemplate=f'<b>{name}</b><br>%{{x}}년: %{{y:,.0f}}만원<extra></extra>'
            ))

    final_custom = custom_vals[-1]
    final_dep = dep_vals[-1]
    diff = final_custom - final_dep

    fig.update_layout(
        paper_bgcolor=COLORS['card_bg'], plot_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text'], family='Noto Sans KR'),
        title=dict(
            text=f'15년 후 예상: {final_custom:,.0f}만원 (예금 대비 {diff:+,.0f}만원)',
            font=dict(size=15, color='#cc99ff')
        ),
        xaxis=dict(title='경과 연수', gridcolor=COLORS['accent'], ticksuffix='년'),
        yaxis=dict(title='적립금 (만원)', gridcolor=COLORS['accent'], tickformat=',.0f', ticksuffix='만'),
        legend=dict(bgcolor=COLORS['bg'], bordercolor=COLORS['accent'], borderwidth=1),
        hovermode='x unified', height=460,
        margin=dict(t=60, r=20, b=50, l=80),
    )

    return (f'{total}%', total_style, warn, rate_display, *val_labels, fig)


@app.callback(
    Output('scenario-store', 'data'),
    Input('save-sc-1', 'n_clicks'),
    Input('save-sc-2', 'n_clicks'),
    Input('save-sc-3', 'n_clicks'),
    Input('reset-sc', 'n_clicks'),
    State('scenario-store', 'data'),
    *[State(sid, 'value') for sid in _slider_ids],
    prevent_initial_call=True,
)
def save_scenario(_s1, _s2, _s3, _reset, store, *slider_vals):
    triggered = ctx.triggered_id
    if triggered == 'reset-sc':
        return [None, None, None]

    slot = {'save-sc-1': 0, 'save-sc-2': 1, 'save-sc-3': 2}.get(triggered)
    if slot is None:
        return store

    rates = [info['rate'] for info in ASSET_RATES.values()]
    total = sum(v or 0 for v in slider_vals)
    effective = total if total > 0 else 1
    weighted = sum((v or 0) * r for v, r in zip(slider_vals, rates)) / effective

    scenario = {
        'alloc': {name: (v or 0) for name, v in zip(_slider_names, slider_vals)},
        'rate': round(weighted, 2),
        'total': total,
        'label': f'시나리오 {slot+1}',
    }
    new_store = list(store)
    new_store[slot] = scenario
    return new_store


@app.callback(
    Output('scenario-summary', 'children'),
    Output('scenario-compare-chart', 'figure'),
    Input('scenario-store', 'data'),
)
def update_scenario_compare(store):
    annual = USER['company_annual'] + USER['personal_annual']
    years_list = list(range(0, 16))
    sc_colors = ['#e94560', '#00d4aa', '#4dabf7']

    # 요약 카드
    cards = []
    for i, (sc, color) in enumerate(zip(store, sc_colors)):
        if sc:
            alloc_text = ' / '.join(f"{k} {v}%" for k, v in sc['alloc'].items() if v > 0)
            final = simulate_returns(USER['current'], annual, 15, sc['rate'])[-1]
            cards.append(html.Div(style={
                **CARD_STYLE, 'borderLeft': f'3px solid {color}',
                'marginBottom': 0, 'padding': '14px'
            }, children=[
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between'}, children=[
                    html.Span(sc['label'], style={'color': color, 'fontWeight': '700'}),
                    html.Span(f"{sc['rate']}%/년", style={'color': color, 'fontSize': '18px', 'fontWeight': '800'}),
                ]),
                html.P(alloc_text, style={'color': COLORS['muted'], 'fontSize': '12px', 'margin': '4px 0'}),
                html.Span(f'15년 후: {final:,.0f}만원', style={'color': COLORS['text'], 'fontWeight': '600'}),
            ]))
        else:
            cards.append(html.Div(style={**CARD_STYLE, 'borderLeft': f'3px solid {COLORS["accent"]}',
                                         'marginBottom': 0, 'padding': '14px', 'textAlign': 'center'}, children=[
                html.P(f'시나리오 {i+1}', style={'color': COLORS['muted'], 'margin': '0 0 4px 0'}),
                html.P('저장된 시나리오 없음', style={'color': COLORS['accent'], 'fontSize': '13px', 'margin': 0}),
            ]))

    summary = html.Div(style={'display': 'grid', 'gridTemplateColumns': 'repeat(3, 1fr)', 'gap': '14px'},
                       children=cards)

    # 비교 차트
    fig = go.Figure()

    # 예금 기준선
    dep_vals = simulate_returns(USER['current'], annual, 15, 4.5)
    fig.add_trace(go.Scatter(
        x=years_list, y=dep_vals, name='예금 100% (기준)',
        line=dict(color=COLORS['muted'], width=2, dash='dot'),
    ))

    saved_count = 0
    for sc, color in zip(store, sc_colors):
        if sc:
            saved_count += 1
            sc_vals = simulate_returns(USER['current'], annual, 15, sc['rate'])
            fig.add_trace(go.Scatter(
                x=years_list, y=sc_vals,
                name=f"{sc['label']} ({sc['rate']}%/년)",
                line=dict(color=color, width=3),
                mode='lines+markers', marker=dict(size=6),
                hovertemplate=f"<b>{sc['label']}</b><br>%{{x}}년 후: %{{y:,.0f}}만원<extra></extra>"
            ))

    if saved_count == 0:
        fig.add_annotation(
            text='슬라이더로 설정 후 [시나리오 저장] 버튼을 눌러 비교하세요',
            xref='paper', yref='paper', x=0.5, y=0.5, showarrow=False,
            font=dict(size=15, color=COLORS['muted'])
        )

    fig.update_layout(
        paper_bgcolor=COLORS['card_bg'], plot_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text'], family='Noto Sans KR'),
        title=dict(text='시나리오별 15년 자산 성장 비교', font=dict(size=15, color='#cc99ff')),
        xaxis=dict(title='경과 연수', gridcolor=COLORS['accent'], ticksuffix='년'),
        yaxis=dict(title='적립금 (만원)', gridcolor=COLORS['accent'], tickformat=',.0f', ticksuffix='만'),
        legend=dict(bgcolor=COLORS['bg']),
        hovermode='x unified', height=420,
        margin=dict(t=50, r=20, b=50, l=80),
    )

    return summary, fig


# ─── 실행 ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("=" * 60)
    print("[퇴직연금 펀드 분석 대시보드]")
    print("=" * 60)
    print("펀드 데이터 로드 완료:", len(DF), "개 퇴직연금 펀드")
    print()
    print("브라우저에서 접속: http://localhost:8050")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=8050)
