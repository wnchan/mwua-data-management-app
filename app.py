"""MWUA Data Management App - Full UI with lazy SQL loading."""
import sys
import os
print('APP: Starting', flush=True)

try:
    import dash
    from dash import html, dcc, dash_table, callback, Input, Output, State, ctx
    import dash_bootstrap_components as dbc
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime
    print('APP: core imports done', flush=True)

    # Lazy SQL imports
    _sql_mod = None
    _sdk_mod = None
    def _lazy_sql():
        global _sql_mod, _sdk_mod
        if _sql_mod is None:
            from databricks import sql
            from databricks.sdk import WorkspaceClient
            _sql_mod, _sdk_mod = sql, WorkspaceClient
        return _sql_mod, _sdk_mod

    # Config
    CATALOG = os.environ.get('CATALOG', 'mwua_capstone_team3')
    SQL_PATH = os.environ.get('DATABRICKS_WAREHOUSE_PATH', '')
    TBL_SENSOR_DQ = f'{CATALOG}.silver.ops_silver_quarantine_sensor'
    TBL_QUARANTINE = f'{CATALOG}.silver.ops_silver_quarantine_billing'
    TBL_BILLING_DQ = f'{CATALOG}.silver.ops_silver_billing_dq_metrics'
    TBL_ZONE = f'{CATALOG}.silver.shared_silver_dim_zone'
    TBL_RULES = f'{CATALOG}.governance.config_business_rules'
    TBL_CORRECTIONS = f'{CATALOG}.governance.data_corrections'
    TBL_AUDIT = f'{CATALOG}.governance.audit_changes'

    # UC2 Finance/Contractor tables
    TBL_UC2_REJECT_INVOICE = f'{CATALOG}.silver.corp_silver_quarantine_invoice'
    TBL_UC2_REJECT_CONTRACTOR = f'{CATALOG}.silver.corp_silver_quarantine_contractor'
    TBL_UC2_INVOICE_HEADER = f'{CATALOG}.silver.corp_silver_invoice_header'
    TBL_UC2_WORKORDER = f'{CATALOG}.silver.corp_silver_contractor_workorder'
    TBL_UC2_VENDOR = f'{CATALOG}.silver.corp_silver_dim_vendor'
    TBL_UC2_DQ_METRICS = f'{CATALOG}.gold.corp_gold_dq_metrics'
    TBL_UC2_DQ_REASONS = f'{CATALOG}.gold.corp_gold_dq_reject_reasons'

    def get_conn():
        sql, WSC = _lazy_sql()
        w = WSC()
        hdrs = w.config.authenticate()
        tok = hdrs.get('Authorization','').replace('Bearer ','')
        host = w.config.host.replace('https://','').replace('http://','')
        return sql.connect(server_hostname=host, http_path=SQL_PATH, access_token=tok)

    def run_q(q):
        try:
            with get_conn() as c:
                with c.cursor() as cur:
                    cur.execute(q)
                    return pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
        except Exception as e:
            print(f'Query err: {e}', flush=True)
            return pd.DataFrame()

    def run_s(s):
        try:
            with get_conn() as c:
                with c.cursor() as cur: cur.execute(s)
            return True
        except Exception as e:
            print(f'Stmt err: {e}', flush=True)
            return False

    # --- Input sanitisation & validation ---
    import re as _re

    def _esc(val):
        """Escape single quotes for SQL string literals. Returns empty string for None."""
        if val is None:
            return ''
        return str(val).replace("'", "''")

    def _valid_id(val, max_len=50):
        """Validate an ID field: non-empty, alphanumeric + underscore/hyphen, max length."""
        if not val or not val.strip():
            return False, 'ID is required.'
        v = val.strip()
        if len(v) > max_len:
            return False, f'ID must be {max_len} characters or fewer.'
        if not _re.match(r'^[A-Za-z0-9_\-]+$', v):
            return False, 'ID must contain only letters, digits, underscores, or hyphens.'
        return True, v

    def _valid_text(val, field_label='Field', required=True, max_len=255):
        """Validate a free-text field: optionally required, max length, no control chars."""
        if not val or not val.strip():
            if required:
                return False, f'{field_label} is required.'
            return True, ''
        v = val.strip()
        if len(v) > max_len:
            return False, f'{field_label} must be {max_len} characters or fewer.'
        if _re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', v):
            return False, f'{field_label} contains invalid characters.'
        return True, v

    print('APP: SQL funcs defined', flush=True)

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
    app.title = 'MWUA Data Management'

    # Custom CSS for table overflow and layout
    app.index_string = '''<!DOCTYPE html>
<html><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .sidebar { position: fixed; top: 0; left: 0; width: 220px; height: 100vh; background: #1a237e; padding-top: 1rem; overflow-y: auto; z-index: 100; }
    .sidebar .nav-link { color: rgba(255,255,255,0.8); border-radius: 8px; margin: 4px 12px; padding: 10px 16px; font-size: 0.9rem; }
    .sidebar .nav-link:hover { color: #fff; background: rgba(255,255,255,0.1); }
    .sidebar .nav-link.active { color: #fff; background: rgba(255,255,255,0.2); font-weight: 600; }
    .main-content { margin-left: 220px; padding: 24px 32px; min-height: 100vh; background: #f5f7fa; max-width: calc(100vw - 220px); overflow-x: hidden; }
    .page-header { margin-bottom: 1.5rem; padding-bottom: 0.75rem; border-bottom: 2px solid #e0e0e0; }
    .table-wrapper { max-height: 60vh; overflow-y: auto; overflow-x: auto; border: 1px solid #dee2e6; border-radius: 8px; background: #fff; max-width: calc(100vw - 290px); }
    .dash-table-container { font-size: 0.85rem; width: 100% !important; }
    .dash-spreadsheet-container { max-width: 100% !important; }
    .dash-header { position: sticky !important; top: 0; z-index: 10; }
    .card-stat { border: none; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: transform 0.2s; }
    .card-stat:hover { transform: translateY(-2px); }
    .brand-title { color: #fff; font-weight: 700; font-size: 1.1rem; padding: 12px 20px; margin-bottom: 0.5rem; }
    .brand-subtitle { color: rgba(255,255,255,0.6); font-size: 0.75rem; padding: 0 20px; margin-bottom: 1rem; }
</style>
</head><body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>'''

    sidebar = html.Div([
        html.Div('MWUA', className='brand-title'),
        html.Div('Data Management', className='brand-subtitle'),
        html.Hr(style={'borderColor':'rgba(255,255,255,0.2)','margin':'0 12px 8px'}),
        dbc.Nav([
            dbc.NavLink([html.I(className='me-2'), 'Overview'], href='/', active='exact'),
            dbc.NavLink([html.I(className='me-2'), 'Zones'], href='/zones', active='exact'),
            dbc.NavLink([html.I(className='me-2'), 'Vendors'], href='/vendors', active='exact'),
            dbc.NavLink([html.I(className='me-2'), 'Business Rules'], href='/rules', active='exact'),
            dbc.NavLink([html.I(className='me-2'), 'Data Quality'], href='/dq', active='exact'),
            dbc.NavLink([html.I(className='me-2'), 'Audit History'], href='/audit', active='exact'),
        ], vertical=True, pills=True),
    ], className='sidebar')

    app.layout = html.Div([
        dcc.Location(id='url'),
        dcc.Store(id='refresh-trigger', data=0),
        dcc.Store(id='rule-trigger', data=0),
        sidebar,
        html.Div(id='page-content', className='main-content'),
    ])
    print('APP: layout done', flush=True)

    # Helper to wrap DataTables in a scrollable container
    def wrap_table(table_component):
        return html.Div(table_component, className='table-wrapper')

    TABLE_STYLE = {'overflowX':'auto'}
    CELL_STYLE = {'textAlign':'left','padding':'8px 12px','fontSize':'0.85rem','whiteSpace':'normal','maxWidth':'250px','overflow':'hidden','textOverflow':'ellipsis'}
    HEADER_STYLE = {'backgroundColor':'#f8f9fa','fontWeight':'600','borderBottom':'2px solid #dee2e6','position':'sticky','top':'0'}

    def pg_overview():
        return html.Div([
            html.Div([
                html.H3('Data Quality Overview', className='mb-0'),
                html.P('Aggregated from: ops_silver_quarantine_sensor, ops_silver_quarantine_billing, ops_silver_billing_dq_metrics, corp_gold_dq_metrics, corp_gold_dq_reject_reasons', className='text-muted mb-0', style={'fontSize':'0.75rem'}),
            ], className='page-header'),
            dbc.Button('Refresh Metrics', id='btn-ov', color='primary', size='sm', className='mb-3'),
            html.Div(id='ov-out'),
        ])
    def pg_zones():
        return html.Div([
            html.Div([html.H3('Zones', className='mb-0'), html.P(f'Source: {TBL_ZONE} (read-only, derived from pipeline data)', className='text-muted mb-0')], className='page-header'),
            dbc.Button('Refresh', id='btn-z', color='secondary', className='mb-3'),
            html.Div(id='z-out'),
        ])

    def pg_vendors():
        return html.Div([
            html.Div([html.H3('Vendor Master', className='mb-0'), html.P(f'Source: {TBL_UC2_VENDOR} (read-only, pipeline-managed)', className='text-muted mb-0')], className='page-header'),
            dbc.Button('Refresh', id='btn-v', color='secondary', className='mb-3'),
            html.Div(id='v-out'),
        ])

    def pg_rules():
        return html.Div([
            html.Div([html.H3('Business Rules & Thresholds', className='mb-0'), html.P(f'Table: {TBL_RULES}', className='text-muted mb-0')], className='page-header'),
            dbc.ButtonGroup([
                dbc.Button('Refresh', id='btn-r', color='secondary'),
                dbc.Button('+ Add Rule', id='btn-r-add', color='primary'),
            ], className='mb-3'),
            html.Div(id='r-out'),
            html.Div(id='r-status'),
            # Add Rule Modal
            dbc.Modal([
                dbc.ModalHeader('Add Business Rule'),
                dbc.ModalBody([
                    dbc.Row([
                        dbc.Col(dbc.Input(id='r-id', placeholder='Rule ID (e.g. R001)'), width=6),
                        dbc.Col(dbc.Input(id='r-name', placeholder='Rule Name'), width=6),
                    ], className='mb-2'),
                    dbc.Select(id='r-cat', options=[
                        {'label':'Sensor Threshold','value':'sensor_threshold'},
                        {'label':'Billing Validation','value':'billing_validation'},
                        {'label':'DQ Check','value':'dq_check'},
                        {'label':'ERP Validation','value':'uc2_erp_validation'},
                        {'label':'UC2 Contractor Validation','value':'uc2_contractor_validation'},
                        {'label':'Contractor Mapping','value':'uc2_contractor_mapping'},
                    ], placeholder='Category', className='mb-2'),
                    dbc.Row([
                        dbc.Col(dbc.Input(id='r-param', placeholder='Parameter (e.g. max_flow_rate)'), width=6),
                        dbc.Col(dbc.Input(id='r-value', placeholder='Value (e.g. 150.0)'), width=6),
                    ], className='mb-2'),
                    dbc.Input(id='r-desc', placeholder='Description', className='mb-2'),
                ]),
                dbc.ModalFooter(dbc.Button('Save Rule', id='btn-r-save', color='primary')),
            ], id='modal-r', is_open=False),
            # Edit Rule Modal
            dbc.Modal([
                dbc.ModalHeader('Edit Rule Value'),
                dbc.ModalBody([
                    html.Label('Select Rule', className='fw-bold mb-1'),
                    dcc.Dropdown(id='r-edit-id', placeholder='Select rule to edit', className='mb-2'),
                    dbc.Input(id='r-edit-value', placeholder='New parameter value (required)', className='mb-2'),
                    dbc.Input(id='r-edit-reason', placeholder='Reason for change (required)', className='mb-2'),
                ]),
                dbc.ModalFooter(dbc.Button('Update', id='btn-r-edit-confirm', color='warning')),
            ], id='modal-r-edit', is_open=False),
            # Deactivate Rule Modal
            dbc.Modal([
                dbc.ModalHeader('Deactivate Rule'),
                dbc.ModalBody([
                    html.Label('Select Rule', className='fw-bold mb-1'),
                    dcc.Dropdown(id='r-deact-id', placeholder='Select rule to deactivate', className='mb-2'),
                    dbc.Input(id='r-deact-reason', placeholder='Reason for deactivation (required)', className='mb-2'),
                ]),
                dbc.ModalFooter(dbc.Button('Deactivate', id='btn-r-deact-confirm', color='danger')),
            ], id='modal-r-deact', is_open=False),
            dbc.ButtonGroup([
                dbc.Button('Edit Rule', id='btn-r-edit', color='outline-warning', size='sm', className='mt-2'),
                dbc.Button('Deactivate Rule', id='btn-r-deact', color='outline-danger', size='sm', className='mt-2'),
            ]),
        ])
    def pg_dq():
        return html.Div([
            html.Div([html.H3('Data Quality & Corrections', className='mb-0')], className='page-header'),
            dbc.Tabs([
                dbc.Tab(label='Sensor DQ Issues', tab_id='sensor'),
                dbc.Tab(label='Billing Quarantine', tab_id='billing'),
                dbc.Tab(label='ERP Rejected', tab_id='uc2_erp'),
                dbc.Tab(label='Contractor Rejected', tab_id='uc2_contractor'),
                dbc.Tab(label='Submitted Corrections', tab_id='corrections'),
            ], id='dq-tabs', active_tab='sensor'),
            html.Div(id='dq-out', className='mt-3'),
            html.Hr(),
            html.H5('Submit Data Correction'),
            html.P('Corrections are applied downstream (not to Bronze). Original values preserved for traceability.', className='text-muted'),
            dbc.Card(dbc.CardBody([
                dbc.Row([
                    dbc.Col(dbc.Select(id='corr-source', options=[
                        {'label':'Sensor DQ','value':TBL_SENSOR_DQ},
                        {'label':'Billing Quarantine','value':TBL_QUARANTINE},
                        {'label':'ERP Rejected','value':TBL_UC2_REJECT_INVOICE},
                        {'label':'Contractor Rejected','value':TBL_UC2_REJECT_CONTRACTOR},
                    ], placeholder='Source Table'), width=3),
                    dbc.Col(dcc.Dropdown(id='corr-rec-id', placeholder='Select Record ID', style={'width':'100%'}), width=3),
                    dbc.Col(dcc.Dropdown(id='corr-field', placeholder='Select Field to correct', style={'width':'100%'}), width=3),
                    dbc.Col(dbc.Input(id='corr-new-val', placeholder='Corrected value'), width=3),
                ], className='mb-2'),
                dbc.Row([
                    dbc.Col(dbc.Input(id='corr-reason', placeholder='Reason for correction (required)'), width=9),
                    dbc.Col(dbc.Button('Submit Correction', id='btn-corr-submit', color='warning', className='w-100'), width=3),
                ]),
            ]), className='mb-3'),
            html.Div(id='corr-status'),
        ])
    def pg_audit():
        return html.Div([html.H3('Audit History'), dbc.Button('Refresh', id='btn-a', color='secondary', className='mb-3'), html.Div(id='a-out')])

    @callback(Output('page-content','children'), Input('url','pathname'))
    def route(p):
        if p=='/zones': return pg_zones()
        if p=='/vendors': return pg_vendors()
        if p=='/rules': return pg_rules()
        if p=='/dq': return pg_dq()
        if p=='/audit': return pg_audit()
        return pg_overview()

    # --- Overview ---
    @callback(Output('ov-out','children'), Input('btn-ov','n_clicks'), prevent_initial_call=False)
    def cb_ov(_):
      try:
        # Sensor DQ counts
        sensor_df = run_q(f'SELECT dq_status, COUNT(*) as cnt FROM {TBL_SENSOR_DQ} GROUP BY dq_status')
        sensor_total = int(sensor_df['cnt'].sum()) if not sensor_df.empty else 0
        sensor_flagged = int(sensor_df[sensor_df['dq_status']!='OK']['cnt'].sum()) if not sensor_df.empty and 'dq_status' in sensor_df.columns else 0

        # Billing quarantine count
        billing_df = run_q(f'SELECT COUNT(*) cnt FROM {TBL_QUARANTINE}')
        billing_quarantine = int(billing_df.iloc[0]['cnt']) if not billing_df.empty else 0

        # Billing DQ metrics (latest run)
        metrics_df = run_q(f'SELECT * FROM {TBL_BILLING_DQ} ORDER BY run_date DESC LIMIT 1')
        valid_rows = int(metrics_df.iloc[0]['valid_row_count']) if not metrics_df.empty else 0
        source_rows = int(metrics_df.iloc[0]['source_row_count']) if not metrics_df.empty else 0
        dq_pass_rate = f"{(valid_rows/source_rows*100):.1f}%" if source_rows > 0 else 'N/A'

        # Corrections pending
        corr_df = run_q(f"SELECT COUNT(*) cnt FROM {TBL_CORRECTIONS} WHERE status='PENDING'")
        pending_corr = int(corr_df.iloc[0]['cnt']) if not corr_df.empty else 0

        # Zone count & rules
        zone_df = run_q(f"SELECT COUNT(*) cnt FROM {TBL_ZONE}")
        active_zones = int(zone_df.iloc[0]['cnt']) if not zone_df.empty else 0
        rule_df = run_q(f"SELECT COUNT(*) cnt FROM {TBL_RULES} WHERE is_active=true")
        active_rules = int(rule_df.iloc[0]['cnt']) if not rule_df.empty else 0

        # UC2 DQ metrics
        uc2_metrics_df = run_q(f'SELECT * FROM {TBL_UC2_DQ_METRICS}')
        uc2_erp_pass = 'N/A'
        uc2_con_pass = 'N/A'
        uc2_erp_rejected = 0
        uc2_con_rejected = 0
        if not uc2_metrics_df.empty:
            erp_row = uc2_metrics_df[uc2_metrics_df['domain']=='erp_invoice']
            con_row = uc2_metrics_df[uc2_metrics_df['domain']=='contractor_workorder']
            if not erp_row.empty:
                uc2_erp_pass = f"{erp_row.iloc[0]['pass_rate_pct']:.1f}%"
                uc2_erp_rejected = int(erp_row.iloc[0]['rejected_count'])
            if not con_row.empty:
                uc2_con_pass = f"{con_row.iloc[0]['pass_rate_pct']:.1f}%"
                uc2_con_rejected = int(con_row.iloc[0]['rejected_count'])

        # UC2 reject reasons
        uc2_reasons_df = run_q(f'SELECT domain, _dq_reason, cnt FROM {TBL_UC2_DQ_REASONS} ORDER BY cnt DESC')

        def stat_card(title, value, color='primary', subtitle=''):
            body = [html.P(title, className='text-muted mb-1', style={'fontSize':'0.8rem'}), html.H3(str(value), className=f'text-{color} mb-0')]
            if subtitle: body.append(html.Small(subtitle, className='text-muted'))
            return dbc.Card(dbc.CardBody(body), className='card-stat h-100')

        if sensor_df.empty and billing_df.empty:
            return html.P('No data available. Check grants and warehouse connection.')

        # --- DQ Trend Charts ---
        # Billing DQ trend over time
        trend_df = run_q(f'SELECT run_date, source_row_count, valid_row_count, quarantine_count, duplicate_count FROM {TBL_BILLING_DQ} ORDER BY run_date')
        billing_trend_chart = html.P('No billing DQ history for trend chart.')
        if not trend_df.empty:
            fig_billing = go.Figure()
            fig_billing.add_trace(go.Scatter(x=trend_df['run_date'], y=trend_df['valid_row_count'], name='Valid', mode='lines+markers', line=dict(color='#28a745', width=2)))
            fig_billing.add_trace(go.Scatter(x=trend_df['run_date'], y=trend_df['quarantine_count'], name='Quarantined', mode='lines+markers', line=dict(color='#dc3545', width=2)))
            fig_billing.add_trace(go.Scatter(x=trend_df['run_date'], y=trend_df['duplicate_count'], name='Duplicates', mode='lines+markers', line=dict(color='#ffc107', width=2)))
            fig_billing.update_layout(title='Billing DQ Trend', xaxis_title='Run Date', yaxis_title='Record Count', template='plotly_white', height=300, margin=dict(l=40,r=20,t=40,b=40), legend=dict(orientation='h',y=-0.2))
            billing_trend_chart = dcc.Graph(figure=fig_billing, config={'displayModeBar':False})

        # Sensor DQ breakdown by reason
        reason_df = run_q(f'SELECT dq_reason, COUNT(*) cnt FROM {TBL_SENSOR_DQ} GROUP BY dq_reason ORDER BY cnt DESC')
        sensor_reason_chart = html.P('No sensor DQ data for chart.')
        if not reason_df.empty:
            fig_sensor = go.Figure(data=[go.Bar(x=reason_df['dq_reason'], y=reason_df['cnt'], marker_color='#3498db')])
            fig_sensor.update_layout(title='Sensor DQ Issues by Reason', xaxis_title='DQ Reason', yaxis_title='Count', template='plotly_white', height=300, margin=dict(l=40,r=20,t=40,b=40))
            sensor_reason_chart = dcc.Graph(figure=fig_sensor, config={'displayModeBar':False})

        # Sensor DQ by zone
        zone_dq_df = run_q(f"SELECT zone, dq_status, COUNT(*) cnt FROM {TBL_SENSOR_DQ} GROUP BY zone, dq_status ORDER BY zone")
        sensor_zone_chart = html.P('')
        if not zone_dq_df.empty:
            zones = zone_dq_df['zone'].unique()
            fig_zone = go.Figure()
            for status in zone_dq_df['dq_status'].unique():
                subset = zone_dq_df[zone_dq_df['dq_status']==status]
                fig_zone.add_trace(go.Bar(x=subset['zone'], y=subset['cnt'], name=status))
            fig_zone.update_layout(title='Sensor DQ by Zone', xaxis_title='Zone', yaxis_title='Count', barmode='stack', template='plotly_white', height=300, margin=dict(l=40,r=20,t=40,b=40), legend=dict(orientation='h',y=-0.2))
            sensor_zone_chart = dcc.Graph(figure=fig_zone, config={'displayModeBar':False})

        # UC2 reject reasons chart
        uc2_reason_chart = html.P('No contractor or erp rejection data.')
        if not uc2_reasons_df.empty:
            color_map = {'erp_invoice':'#e74c3c','contractor_workorder':'#f39c12'}
            fig_uc2 = go.Figure(data=[go.Bar(x=uc2_reasons_df['_dq_reason'], y=uc2_reasons_df['cnt'], marker_color=[color_map.get(d,'#3498db') for d in uc2_reasons_df['domain']])])
            fig_uc2.update_layout(title='UC2 Rejection Reasons', xaxis_title='Reason', yaxis_title='Count', template='plotly_white', height=300, margin=dict(l=40,r=20,t=40,b=40))
            uc2_reason_chart = dcc.Graph(figure=fig_uc2, config={'displayModeBar':False})

        return html.Div([
            dbc.Row([
                dbc.Col(stat_card('Sensor DQ Records', f'{sensor_total:,}', 'primary', f'{sensor_flagged:,} flagged'), md=3, className='mb-3'),
                dbc.Col(stat_card('Billing Quarantined', f'{billing_quarantine:,}', 'danger'), md=3, className='mb-3'),
                dbc.Col(stat_card('Billing DQ Pass Rate', dq_pass_rate, 'success', f'{valid_rows:,} / {source_rows:,} valid'), md=3, className='mb-3'),
                dbc.Col(stat_card('Pending Corrections', str(pending_corr), 'warning'), md=3, className='mb-3'),
            ]),
            dbc.Row([
                dbc.Col(stat_card('ERP Pass Rate', uc2_erp_pass, 'success', f'{uc2_erp_rejected} rejected'), md=3, className='mb-3'),
                dbc.Col(stat_card('Contractor Pass Rate', uc2_con_pass, 'success', f'{uc2_con_rejected} rejected'), md=3, className='mb-3'),
                dbc.Col(stat_card('Zones', str(active_zones), 'info'), md=3, className='mb-3'),
                dbc.Col(stat_card('Active Rules', str(active_rules), 'info'), md=3, className='mb-3'),
            ]),
            html.Hr(),
            html.H5('DQ Trends', className='mt-3 mb-3'),
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody(billing_trend_chart), className='card-stat'), md=6, className='mb-3'),
                dbc.Col(dbc.Card(dbc.CardBody(sensor_reason_chart), className='card-stat'), md=6, className='mb-3'),
            ]),
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody(sensor_zone_chart), className='card-stat'), md=6, className='mb-3'),
                dbc.Col(dbc.Card(dbc.CardBody(uc2_reason_chart), className='card-stat'), md=6, className='mb-3'),
            ]),
        ])
      except Exception as ov_err:
        print(f'Overview callback error: {ov_err}', flush=True)
        import traceback; traceback.print_exc()
        return dbc.Alert(f'Error loading overview: {ov_err}', color='danger')

    # --- Vendor Master (read-only) ---
    @callback(Output('v-out','children'), Input('btn-v','n_clicks'), prevent_initial_call=False)
    def cb_v(_):
        df = run_q(f'SELECT vendor_id, vendor_name FROM {TBL_UC2_VENDOR} ORDER BY vendor_id')
        if df.empty:
            return html.P('No vendor data available. Run the UC2 pipeline to populate.')
        return html.Div([
            html.P(f'{len(df)} vendors loaded from pipeline.', className='text-muted mb-2'),
            wrap_table(dash_table.DataTable(
                data=df.to_dict('records'), columns=[{'name':c,'id':c} for c in df.columns],
                page_size=20, filter_action='native', sort_action='native',
                style_table=TABLE_STYLE, style_cell=CELL_STYLE, style_header=HEADER_STYLE)),
        ])

    # --- Zone (read-only from materialized view) ---
    @callback(Output('z-out','children'), Input('btn-z','n_clicks'), prevent_initial_call=False)
    def cb_z(_):
        df = run_q(f'SELECT zone_name FROM {TBL_ZONE} ORDER BY zone_name')
        if df.empty:
            return html.P('No zones found. Zones are auto-derived from pipeline data.')
        return html.Div([
            html.P(f'{len(df)} zones derived from Silver layer tables.', className='text-muted mb-2'),
            wrap_table(dash_table.DataTable(
                data=df.to_dict('records'), columns=[{'name':c,'id':c} for c in df.columns],
                page_size=20, filter_action='native', sort_action='native',
                style_table=TABLE_STYLE, style_cell=CELL_STYLE, style_header=HEADER_STYLE)),
        ])

    # --- Rules modal toggles ---
    @callback(Output('modal-r','is_open'), Input('btn-r-add','n_clicks'), Input('btn-r-save','n_clicks'), State('modal-r','is_open'), prevent_initial_call=True)
    def toggle_r_modal(n1,n2,o): return not o

    @callback(Output('modal-r-edit','is_open'), Output('r-edit-id','options'),
        Input('btn-r-edit','n_clicks'), Input('btn-r-edit-confirm','n_clicks'), State('modal-r-edit','is_open'), prevent_initial_call=True)
    def toggle_r_edit(n1,n2,o):
        if ctx.triggered_id == 'btn-r-edit':
            df = run_q(f"SELECT rule_id, rule_name FROM {TBL_RULES} WHERE is_active=true ORDER BY rule_id")
            opts = [{'label': f"{r['rule_id']} - {r['rule_name']}", 'value': r['rule_id']} for _, r in df.iterrows()] if not df.empty else []
            return True, opts
        return False, dash.no_update

    @callback(Output('modal-r-deact','is_open'), Output('r-deact-id','options'),
        Input('btn-r-deact','n_clicks'), Input('btn-r-deact-confirm','n_clicks'), State('modal-r-deact','is_open'), prevent_initial_call=True)
    def toggle_r_deact(n1,n2,o):
        if ctx.triggered_id == 'btn-r-deact':
            df = run_q(f"SELECT rule_id, rule_name FROM {TBL_RULES} WHERE is_active=true ORDER BY rule_id")
            opts = [{'label': f"{r['rule_id']} - {r['rule_name']}", 'value': r['rule_id']} for _, r in df.iterrows()] if not df.empty else []
            return True, opts
        return False, dash.no_update

    # --- Rules CRUD ---
    @callback(Output('r-out','children'), Output('r-status','children'),
        Input('btn-r','n_clicks'), Input('btn-r-save','n_clicks'), Input('btn-r-edit-confirm','n_clicks'), Input('btn-r-deact-confirm','n_clicks'),
        State('r-id','value'), State('r-name','value'), State('r-cat','value'),
        State('r-param','value'), State('r-value','value'), State('r-desc','value'),
        State('r-edit-id','value'), State('r-edit-value','value'), State('r-edit-reason','value'),
        State('r-deact-id','value'), State('r-deact-reason','value'),
        prevent_initial_call=False)
    def cb_r(ref, save, edit, deact, rid, rname, rcat, rparam, rval, rdesc, edit_id, edit_val, edit_reason, deact_id, deact_reason):
        status = ''
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        if ctx.triggered_id == 'btn-r-save':
            ok_id, clean_id = _valid_id(rid, max_len=30)
            if not ok_id:
                status = dbc.Alert(f'Rule ID: {clean_id}', color='warning', duration=4000)
            else:
                ok_name, clean_name = _valid_text(rname, 'Rule Name', required=True, max_len=100)
                if not ok_name:
                    status = dbc.Alert(clean_name, color='warning', duration=4000)
                elif not rcat:
                    status = dbc.Alert('Please select a category.', color='warning', duration=4000)
                else:
                    _, clean_param = _valid_text(rparam, 'Parameter', required=False, max_len=100)
                    _, clean_val = _valid_text(rval, 'Value', required=False, max_len=255)
                    _, clean_desc = _valid_text(rdesc, 'Description', required=False, max_len=500)
                    dup_df = run_q(f"SELECT 1 FROM {TBL_RULES} WHERE rule_id='{_esc(clean_id)}' LIMIT 1")
                    if not dup_df.empty:
                        status = dbc.Alert(f'Rule ID {clean_id} already exists.', color='danger', duration=4000)
                    else:
                        ok = run_s(f"INSERT INTO {TBL_RULES} VALUES ('{_esc(clean_id)}','{_esc(clean_name)}','{_esc(rcat)}','{_esc(clean_param)}','{_esc(clean_val)}','string','{_esc(clean_desc)}',true,'app_user','{now}')")
                        if ok:
                            run_s(f"INSERT INTO {TBL_AUDIT} VALUES ('{_esc(now + '_' + clean_id)}','{TBL_RULES}','{_esc(clean_id)}','ADD','rule_name','','{_esc(clean_name)}','New rule added','app_user','{now}')")
                            status = dbc.Alert('Rule saved!', color='success', duration=4000)
                        else:
                            status = dbc.Alert('Failed to save rule.', color='danger', duration=4000)
        elif ctx.triggered_id == 'btn-r-edit-confirm':
            ok_val, clean_val = _valid_text(edit_val, 'Parameter value', required=True, max_len=255)
            ok_reason, clean_reason = _valid_text(edit_reason, 'Reason', required=True, max_len=255)
            if not edit_id:
                status = dbc.Alert('Please select a rule.', color='warning', duration=4000)
            elif not ok_val:
                status = dbc.Alert(clean_val, color='warning', duration=4000)
            elif not ok_reason:
                status = dbc.Alert(clean_reason, color='warning', duration=4000)
            else:
                safe_id = _esc(edit_id)
                old_df = run_q(f"SELECT parameter_value FROM {TBL_RULES} WHERE rule_id='{safe_id}'")
                old_val = _esc(old_df.iloc[0]['parameter_value']) if not old_df.empty else ''
                ok = run_s(f"UPDATE {TBL_RULES} SET parameter_value='{_esc(clean_val)}', updated_at='{now}', updated_by='app_user' WHERE rule_id='{safe_id}'")
                if ok:
                    run_s(f"INSERT INTO {TBL_AUDIT} VALUES ('{_esc(now + '_' + edit_id)}','{TBL_RULES}','{safe_id}','UPDATE','parameter_value','{old_val} → {_esc(clean_val)}','{_esc(clean_reason)}','{_esc(clean_reason)}','app_user','{now}')")
                    status = dbc.Alert(f'Rule {edit_id} updated.', color='success', duration=4000)
                else:
                    status = dbc.Alert('Failed to update.', color='danger', duration=4000)
        elif ctx.triggered_id == 'btn-r-deact-confirm':
            ok_reason, clean_reason = _valid_text(deact_reason, 'Reason', required=True, max_len=255)
            if not deact_id:
                status = dbc.Alert('Please select a rule.', color='warning', duration=4000)
            elif not ok_reason:
                status = dbc.Alert(clean_reason, color='warning', duration=4000)
            else:
                safe_id = _esc(deact_id)
                ok = run_s(f"UPDATE {TBL_RULES} SET is_active=false, updated_at='{now}', updated_by='app_user' WHERE rule_id='{safe_id}'")
                if ok:
                    run_s(f"INSERT INTO {TBL_AUDIT} VALUES ('{_esc(now + '_' + deact_id)}','{TBL_RULES}','{safe_id}','DEACTIVATE','is_active','active → inactive','{_esc(clean_reason)}','{_esc(clean_reason)}','app_user','{now}')")
                    status = dbc.Alert(f'Rule {deact_id} deactivated.', color='warning', duration=4000)
                else:
                    status = dbc.Alert('Failed to deactivate rule.', color='danger', duration=4000)
        df = run_q(f'SELECT * FROM {TBL_RULES} WHERE is_active=true ORDER BY rule_category, rule_name LIMIT 50')
        if df.empty:
            return html.P('No active rules. Click "+ Add Rule" to create one.'), status
        tbl = wrap_table(dash_table.DataTable(data=df.to_dict('records'), columns=[{'name':c,'id':c} for c in df.columns], page_size=15,
            style_table=TABLE_STYLE, style_cell=CELL_STYLE, style_header=HEADER_STYLE))
        return tbl, status

    # --- DQ tab view ---
    @callback(Output('dq-out','children'), Input('dq-tabs','active_tab'), Input('refresh-trigger','data'))
    def cb_dq(tab, _refresh):
        if tab == 'corrections':
            df = run_q(f'SELECT * FROM {TBL_CORRECTIONS} ORDER BY submitted_at DESC LIMIT 50')
            if df.empty: return html.P('No corrections submitted yet.')
        elif tab == 'sensor':
            df = run_q(f'SELECT sensor_id, location_id, zone, reading_type, reading_value, unit, timestamp, dq_reason, dq_status FROM {TBL_SENSOR_DQ} LIMIT 50')
            if df.empty: return html.P('No sensor DQ records.')
        elif tab == 'uc2_erp':
            df = run_q(f'SELECT cost_center, vendor_id, vendor_name, site_zone, invoice_date, project_code, _dq_reason, _source_file, _ingest_ts, _rejected_at FROM {TBL_UC2_REJECT_INVOICE} ORDER BY _rejected_at DESC LIMIT 50')
            if df.empty: return html.P('No rejected ERP invoices.')
        elif tab == 'uc2_contractor':
            df = run_q(f'SELECT zone, description, contractor_id, _dq_reason, _source_file, _ingest_ts, _rejected_at FROM {TBL_UC2_REJECT_CONTRACTOR} ORDER BY _rejected_at DESC LIMIT 50')
            if df.empty: return html.P('No rejected contractor work orders.')
        else:
            df = run_q(f'SELECT account_id, meter_id, billing_period, original_consumption_value, original_consumption_unit, amount_billed, payment_status, dq_status, dq_reason FROM {TBL_QUARANTINE} LIMIT 50')
            if df.empty: return html.P('No quarantine records.')
        cond = [{'if':{'filter_query':'{status} eq "PENDING"'},'backgroundColor':'#fff3cd'}] if tab=='corrections' else []
        return wrap_table(dash_table.DataTable(data=df.to_dict('records'),columns=[{'name':c,'id':c} for c in df.columns],page_size=15,
            sort_action='native',style_table=TABLE_STYLE,style_cell=CELL_STYLE,style_header=HEADER_STYLE,
            style_data_conditional=cond,
            tooltip_data=[{c: {'value': str(row[c]), 'type': 'markdown'} for c in df.columns} for _, row in df.iterrows()],
            tooltip_duration=None))

    # --- Populate Record ID & Field dropdowns based on source table ---
    _SRC_ID_COL = {TBL_SENSOR_DQ: 'sensor_id', TBL_QUARANTINE: 'account_id', TBL_UC2_REJECT_INVOICE: 'vendor_id', TBL_UC2_REJECT_CONTRACTOR: 'contractor_id'}

    @callback(
        Output('corr-rec-id','options'), Output('corr-field','options'),
        Output('corr-rec-id','value'), Output('corr-field','value'),
        Input('corr-source','value'), prevent_initial_call=True)
    def populate_corr_dropdowns(source):
        if not source:
            return [], [], None, None
        # Record IDs
        id_col = _SRC_ID_COL.get(source, 'record_id')
        id_df = run_q(f'SELECT DISTINCT {id_col} FROM {source} ORDER BY {id_col} LIMIT 500')
        rec_opts = [{'label': str(v), 'value': str(v)} for v in id_df[id_col].tolist()] if not id_df.empty else []
        # Column names
        cols_df = run_q(f'DESCRIBE TABLE {source}')
        field_opts = [{'label': c, 'value': c} for c in cols_df['col_name'].tolist() if c and not c.startswith('#')] if not cols_df.empty else []
        return rec_opts, field_opts, None, None

    # --- Correction submit ---
    @callback(Output('corr-status','children'), Output('refresh-trigger','data'),
        Input('btn-corr-submit','n_clicks'),
        State('corr-source','value'), State('corr-rec-id','value'),
        State('corr-field','value'), State('corr-new-val','value'), State('corr-reason','value'),
        State('refresh-trigger','data'),
        prevent_initial_call=True)
    def cb_corr(_, source, rec_id, field, new_val, reason, cur_refresh):
        if not all([source, rec_id, field, new_val, reason]):
            return dbc.Alert('All fields are required.', color='warning', duration=4000), dash.no_update
        ok_val, clean_val = _valid_text(new_val, 'Corrected value', required=True, max_len=500)
        if not ok_val:
            return dbc.Alert(clean_val, color='warning', duration=4000), dash.no_update
        ok_reason, clean_reason = _valid_text(reason, 'Reason', required=True, max_len=500)
        if not ok_reason:
            return dbc.Alert(clean_reason, color='warning', duration=4000), dash.no_update
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        corr_id = f'CORR_{now}_{rec_id}'.replace(':','-')
        # Fetch the original value from the source table
        id_col = _SRC_ID_COL.get(source, 'record_id')
        orig_df = run_q(f"SELECT {_esc(field)} FROM {source} WHERE {id_col}='{_esc(rec_id)}' LIMIT 1")
        original_val = str(orig_df.iloc[0][field]) if not orig_df.empty else ''
        ok = run_s(f"INSERT INTO {TBL_CORRECTIONS} VALUES ('{_esc(corr_id)}','{_esc(source)}','{_esc(rec_id)}','{_esc(field)}','{_esc(original_val)}','{_esc(clean_val)}','{_esc(clean_reason)}','PENDING','app_user','{now}',NULL,NULL)")
        if ok:
            run_s(f"INSERT INTO {TBL_AUDIT} VALUES ('{_esc(now + '_' + corr_id)}','{TBL_CORRECTIONS}','{_esc(corr_id)}','CORRECTION_SUBMITTED','{_esc(field)}','{_esc(original_val)} → {_esc(clean_val)}','{_esc(clean_reason)}','{_esc(clean_reason)}','app_user','{now}')")
            return dbc.Alert(f'Correction {corr_id} submitted (status: PENDING).', color='success', duration=5000), (cur_refresh or 0) + 1
        return dbc.Alert('Failed to submit correction.', color='danger', duration=4000), dash.no_update

    # --- Audit ---
    @callback(Output('a-out','children'), Input('btn-a','n_clicks'), prevent_initial_call=False)
    def cb_a(_):
        df = run_q(f"""SELECT audit_id, table_name, record_id, action, field_name,
            CASE WHEN old_value = '' AND new_value = '' THEN reason
                 WHEN old_value = '' THEN CONCAT('Set to: ', new_value)
                 ELSE CONCAT(old_value, ' → ', new_value)
            END as changes_made,
            reason, changed_by, changed_at
            FROM {TBL_AUDIT} ORDER BY changed_at DESC LIMIT 100""")
        if df.empty: return html.P('No audit records.')
        return wrap_table(dash_table.DataTable(data=df.to_dict('records'),columns=[{'name':c,'id':c} for c in df.columns],page_size=20,
            sort_action='native', style_table=TABLE_STYLE, style_cell=CELL_STYLE, style_header=HEADER_STYLE))

    print('APP: callbacks done', flush=True)

    if __name__ == '__main__':
        port = int(os.environ.get('APP_PORT', 8050))
        print(f'APP: Starting on port {port}', flush=True)
        app.run(host='0.0.0.0', port=port, debug=False)

except Exception as e:
    print(f'APP ERROR: {e}', flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)