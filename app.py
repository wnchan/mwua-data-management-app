"""MWUA Data Management App - Full UI with lazy SQL loading."""
import sys
import os
print('APP: Starting', flush=True)

try:
    import dash
    from dash import html, dcc, dash_table, callback, Input, Output, State, ctx
    import dash_bootstrap_components as dbc
    import pandas as pd
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
    TBL_SENSOR_DQ = f'{CATALOG}.silver.ops_silver_sensor_dq'
    TBL_QUARANTINE = f'{CATALOG}.silver.ops_quarantine_billing'
    TBL_BILLING_DQ = f'{CATALOG}.silver.ops_silver_billing_dq_metrics'
    TBL_ZONE = f'{CATALOG}.governance.zone_master'
    TBL_RULES = f'{CATALOG}.governance.config_business_rules'
    TBL_CORRECTIONS = f'{CATALOG}.governance.data_corrections'
    TBL_AUDIT = f'{CATALOG}.governance.audit_changes'

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

    print('APP: SQL funcs defined', flush=True)

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
    app.title = 'MWUA Data Management'

    sidebar = dbc.Nav([
        dbc.NavLink('Overview', href='/', active='exact'),
        dbc.NavLink('Zone Management', href='/zones', active='exact'),
        dbc.NavLink('Business Rules', href='/rules', active='exact'),
        dbc.NavLink('Data Quality', href='/dq', active='exact'),
        dbc.NavLink('Audit History', href='/audit', active='exact'),
    ], vertical=True, pills=True, className='bg-light p-3')

    app.layout = dbc.Container([
        dcc.Location(id='url'),
        dbc.Row([
            dbc.Col([html.H4('MWUA Data Mgmt', className='text-primary mb-3'), sidebar], width=2, className='bg-light vh-100 pt-3'),
            dbc.Col(html.Div(id='page-content'), width=10, className='pt-3'),
        ])
    ], fluid=True)
    print('APP: layout done', flush=True)

    def pg_overview():
        return html.Div([html.H3('Data Quality Overview'), html.P('Pipelines: uc1_billing_customer, uc3_network_sensor'),
            dbc.Button('Refresh', id='btn-ov', color='primary', className='mb-3'), html.Div(id='ov-out')])

    def pg_zones():
        return html.Div([
            html.H3('Zone Management'),
            html.P(f'Table: {TBL_ZONE}', className='text-muted'),
            dbc.ButtonGroup([dbc.Button('Refresh', id='btn-z', color='secondary'), dbc.Button('+ Add Zone', id='btn-z-add', color='primary')], className='mb-3'),
            html.Div(id='z-out'), html.Div(id='z-status'),
            dbc.Modal([dbc.ModalHeader('Add New Zone'), dbc.ModalBody([
                dbc.Row([dbc.Col(dbc.Input(id='z-id', placeholder='Zone ID'), width=6), dbc.Col(dbc.Input(id='z-name', placeholder='Zone Name'), width=6)], className='mb-2'),
                dbc.Input(id='z-desc', placeholder='Description', className='mb-2'), dbc.Input(id='z-region', placeholder='Region', className='mb-2'),
            ]), dbc.ModalFooter(dbc.Button('Save Zone', id='btn-z-save', color='primary'))], id='modal-z', is_open=False),
            dbc.Modal([dbc.ModalHeader('Deactivate Zone'), dbc.ModalBody([
                dbc.Input(id='z-deact-id', placeholder='Zone ID to deactivate', className='mb-2'),
                dbc.Input(id='z-deact-reason', placeholder='Reason', className='mb-2'),
            ]), dbc.ModalFooter(dbc.Button('Deactivate', id='btn-z-deact-confirm', color='danger'))], id='modal-z-deact', is_open=False),
            dbc.Button('Deactivate Zone', id='btn-z-deact', color='outline-danger', size='sm', className='mt-2'),
        ])

    def pg_rules():
        return html.Div([
            html.H3('Business Rules & Thresholds'),
            html.P(f'Table: {TBL_RULES}', className='text-muted'),
            dbc.ButtonGroup([dbc.Button('Refresh', id='btn-r', color='secondary'), dbc.Button('+ Add Rule', id='btn-r-add', color='primary')], className='mb-3'),
            html.Div(id='r-out'), html.Div(id='r-status'),
            dbc.Modal([dbc.ModalHeader('Add Business Rule'), dbc.ModalBody([
                dbc.Row([dbc.Col(dbc.Input(id='r-id', placeholder='Rule ID'), width=6), dbc.Col(dbc.Input(id='r-name', placeholder='Rule Name'), width=6)], className='mb-2'),
                dbc.Select(id='r-cat', options=[{'label':'Sensor Threshold','value':'sensor_threshold'},{'label':'Billing Validation','value':'billing_validation'},{'label':'DQ Check','value':'dq_check'}], placeholder='Category', className='mb-2'),
                dbc.Row([dbc.Col(dbc.Input(id='r-param', placeholder='Parameter'), width=6), dbc.Col(dbc.Input(id='r-value', placeholder='Value'), width=6)], className='mb-2'),
                dbc.Input(id='r-desc', placeholder='Description', className='mb-2'),
            ]), dbc.ModalFooter(dbc.Button('Save Rule', id='btn-r-save', color='primary'))], id='modal-r', is_open=False),
            dbc.Modal([dbc.ModalHeader('Edit Rule Value'), dbc.ModalBody([
                dbc.Input(id='r-edit-id', placeholder='Rule ID to edit', className='mb-2'),
                dbc.Input(id='r-edit-value', placeholder='New value', className='mb-2'),
                dbc.Input(id='r-edit-reason', placeholder='Reason for change', className='mb-2'),
            ]), dbc.ModalFooter(dbc.Button('Update', id='btn-r-edit-confirm', color='warning'))], id='modal-r-edit', is_open=False),
            dbc.Button('Edit Rule', id='btn-r-edit', color='outline-warning', size='sm', className='mt-2'),
        ])

    def pg_dq():
        return html.Div([
            html.H3('Data Quality & Corrections'),
            dbc.Tabs([dbc.Tab(label='Sensor DQ Issues', tab_id='sensor'), dbc.Tab(label='Billing Quarantine', tab_id='billing'), dbc.Tab(label='Submitted Corrections', tab_id='corrections')], id='dq-tabs', active_tab='sensor'),
            html.Div(id='dq-out', className='mt-3'), html.Hr(),
            html.H5('Submit Data Correction'),
            html.P('Corrections applied downstream, not to Bronze. Original values preserved.', className='text-muted'),
            dbc.Card(dbc.CardBody([
                dbc.Row([dbc.Col(dbc.Select(id='corr-source', options=[{'label':'Sensor DQ','value':TBL_SENSOR_DQ},{'label':'Billing Quarantine','value':TBL_QUARANTINE}], placeholder='Source Table'), width=3),
                    dbc.Col(dbc.Input(id='corr-rec-id', placeholder='Record ID'), width=3), dbc.Col(dbc.Input(id='corr-field', placeholder='Field'), width=3), dbc.Col(dbc.Input(id='corr-new-val', placeholder='Corrected value'), width=3)], className='mb-2'),
                dbc.Row([dbc.Col(dbc.Input(id='corr-reason', placeholder='Reason (required)'), width=9), dbc.Col(dbc.Button('Submit', id='btn-corr-submit', color='warning', className='w-100'), width=3)]),
            ]), className='mb-3'),
            html.Div(id='corr-status'),
        ])

    def pg_audit():
        return html.Div([html.H3('Audit History'), dbc.Button('Refresh', id='btn-a', color='secondary', className='mb-3'), html.Div(id='a-out')])

    @callback(Output('page-content','children'), Input('url','pathname'))
    def route(p):
        if p=='/zones': return pg_zones()
        if p=='/rules': return pg_rules()
        if p=='/dq': return pg_dq()
        if p=='/audit': return pg_audit()
        return pg_overview()

    @callback(Output('ov-out','children'), Input('btn-ov','n_clicks'), prevent_initial_call=False)
    def cb_ov(_):
        df = run_q(f'SELECT dq_status, COUNT(*) cnt FROM {TBL_SENSOR_DQ} GROUP BY dq_status')
        if df.empty: return html.P('No data or check grants/warehouse.')
        return dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([html.H5('Sensor DQ'),html.H2(f"{df["cnt"].sum():,}")])),width=4)])

    @callback(Output('modal-z','is_open'), Input('btn-z-add','n_clicks'), Input('btn-z-save','n_clicks'), State('modal-z','is_open'), prevent_initial_call=True)
    def toggle_z_modal(n1,n2,o): return not o

    @callback(Output('modal-z-deact','is_open'), Input('btn-z-deact','n_clicks'), Input('btn-z-deact-confirm','n_clicks'), State('modal-z-deact','is_open'), prevent_initial_call=True)
    def toggle_z_deact(n1,n2,o): return not o

    @callback(Output('z-out','children'), Output('z-status','children'),
        Input('btn-z','n_clicks'), Input('btn-z-save','n_clicks'), Input('btn-z-deact-confirm','n_clicks'),
        State('z-id','value'), State('z-name','value'), State('z-desc','value'), State('z-region','value'),
        State('z-deact-id','value'), State('z-deact-reason','value'), prevent_initial_call=False)
    def cb_z(ref, save, deact, zid, zname, zdesc, zregion, deact_id, deact_reason):
        status = ''
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        if ctx.triggered_id == 'btn-z-save' and zid and zname:
            ok = run_s(f"INSERT INTO {TBL_ZONE} VALUES ('{zid}','{zname}','{zdesc or ''}','{zregion or ''}',true,'app_user','{now}','{now}')")
            if ok:
                run_s(f"INSERT INTO {TBL_AUDIT} VALUES ('{now}_{zid}','{TBL_ZONE}','{zid}','ADD','zone_name','','{zname}','New zone added','app_user','{now}')")
                status = dbc.Alert('Zone added!', color='success', duration=4000)
            else: status = dbc.Alert('Failed to add zone.', color='danger', duration=4000)
        elif ctx.triggered_id == 'btn-z-deact-confirm' and deact_id:
            ok = run_s(f"UPDATE {TBL_ZONE} SET is_active=false, updated_at='{now}' WHERE zone_id='{deact_id}'")
            if ok:
                run_s(f"INSERT INTO {TBL_AUDIT} VALUES ('{now}_{deact_id}','{TBL_ZONE}','{deact_id}','DEACTIVATE','is_active','true','false','{deact_reason or 'Deactivated'}','app_user','{now}')")
                status = dbc.Alert(f'Zone {deact_id} deactivated.', color='warning', duration=4000)
            else: status = dbc.Alert('Failed to deactivate.', color='danger', duration=4000)
        df = run_q(f'SELECT * FROM {TBL_ZONE} ORDER BY zone_id LIMIT 50')
        if df.empty: return html.P('No zones yet. Click "+ Add Zone".'), status
        tbl = dash_table.DataTable(data=df.to_dict('records'), columns=[{'name':c,'id':c} for c in df.columns], page_size=10,
            style_data_conditional=[{'if':{'filter_query':'{is_active} eq false'},'backgroundColor':'#f8d7da'}])
        return tbl, status

    @callback(Output('modal-r','is_open'), Input('btn-r-add','n_clicks'), Input('btn-r-save','n_clicks'), State('modal-r','is_open'), prevent_initial_call=True)
    def toggle_r_modal(n1,n2,o): return not o

    @callback(Output('modal-r-edit','is_open'), Input('btn-r-edit','n_clicks'), Input('btn-r-edit-confirm','n_clicks'), State('modal-r-edit','is_open'), prevent_initial_call=True)
    def toggle_r_edit(n1,n2,o): return not o

    @callback(Output('r-out','children'), Output('r-status','children'),
        Input('btn-r','n_clicks'), Input('btn-r-save','n_clicks'), Input('btn-r-edit-confirm','n_clicks'),
        State('r-id','value'), State('r-name','value'), State('r-cat','value'),
        State('r-param','value'), State('r-value','value'), State('r-desc','value'),
        State('r-edit-id','value'), State('r-edit-value','value'), State('r-edit-reason','value'), prevent_initial_call=False)
    def cb_r(ref, save, edit, rid, rname, rcat, rparam, rval, rdesc, edit_id, edit_val, edit_reason):
        status = ''
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        if ctx.triggered_id == 'btn-r-save' and rid and rname:
            ok = run_s(f"INSERT INTO {TBL_RULES} VALUES ('{rid}','{rname}','{rcat or ''}','{rparam or ''}','{rval or ''}','string','{rdesc or ''}',true,'app_user','{now}')")
            if ok:
                run_s(f"INSERT INTO {TBL_AUDIT} VALUES ('{now}_{rid}','{TBL_RULES}','{rid}','ADD','rule_name','','{rname}','New rule added','app_user','{now}')")
                status = dbc.Alert('Rule saved!', color='success', duration=4000)
            else: status = dbc.Alert('Failed to save rule.', color='danger', duration=4000)
        elif ctx.triggered_id == 'btn-r-edit-confirm' and edit_id and edit_val:
            old_df = run_q(f"SELECT parameter_value FROM {TBL_RULES} WHERE rule_id='{edit_id}'")
            old_val = old_df.iloc[0]['parameter_value'] if not old_df.empty else ''
            ok = run_s(f"UPDATE {TBL_RULES} SET parameter_value='{edit_val}', updated_at='{now}', updated_by='app_user' WHERE rule_id='{edit_id}'")
            if ok:
                run_s(f"INSERT INTO {TBL_AUDIT} VALUES ('{now}_{edit_id}','{TBL_RULES}','{edit_id}','UPDATE','parameter_value','{old_val}','{edit_val}','{edit_reason or 'Updated'}','app_user','{now}')")
                status = dbc.Alert(f'Rule {edit_id} updated.', color='success', duration=4000)
            else: status = dbc.Alert('Failed to update.', color='danger', duration=4000)
        df = run_q(f'SELECT * FROM {TBL_RULES} ORDER BY rule_category, rule_name LIMIT 50')
        if df.empty: return html.P('No rules yet. Click "+ Add Rule".'), status
        return dash_table.DataTable(data=df.to_dict('records'), columns=[{'name':c,'id':c} for c in df.columns], page_size=10), status

    @callback(Output('dq-out','children'), Input('dq-tabs','active_tab'))
    def cb_dq(tab):
        if tab == 'corrections':
            df = run_q(f'SELECT * FROM {TBL_CORRECTIONS} ORDER BY submitted_at DESC LIMIT 50')
            if df.empty: return html.P('No corrections submitted yet.')
        else:
            tbl_name = TBL_SENSOR_DQ if tab=='sensor' else TBL_QUARANTINE
            df = run_q(f'SELECT * FROM {tbl_name} LIMIT 50')
            if df.empty: return html.P('No records.')
        return dash_table.DataTable(data=df.to_dict('records'),columns=[{'name':c,'id':c} for c in df.columns],page_size=10,filter_action='native',sort_action='native')

    @callback(Output('corr-status','children'), Input('btn-corr-submit','n_clicks'),
        State('corr-source','value'), State('corr-rec-id','value'), State('corr-field','value'),
        State('corr-new-val','value'), State('corr-reason','value'), prevent_initial_call=True)
    def cb_corr(_, source, rec_id, field, new_val, reason):
        if not all([source, rec_id, field, new_val, reason]):
            return dbc.Alert('All fields are required.', color='warning', duration=4000)
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        corr_id = f'CORR_{now}_{rec_id}'.replace(':','-')
        ok = run_s(f"INSERT INTO {TBL_CORRECTIONS} VALUES ('{corr_id}','{source}','{rec_id}','{field}','','{new_val}','{reason}','PENDING','app_user','{now}',NULL,NULL)")
        if ok:
            run_s(f"INSERT INTO {TBL_AUDIT} VALUES ('{now}_{corr_id}','{TBL_CORRECTIONS}','{corr_id}','CORRECTION_SUBMITTED','{field}','','{new_val}','{reason}','app_user','{now}')")
            return dbc.Alert(f'Correction {corr_id} submitted (PENDING).', color='success', duration=5000)
        return dbc.Alert('Failed to submit.', color='danger', duration=4000)

    @callback(Output('a-out','children'), Input('btn-a','n_clicks'), prevent_initial_call=False)
    def cb_a(_):
        df = run_q(f'SELECT * FROM {TBL_AUDIT} ORDER BY changed_at DESC LIMIT 100')
        if df.empty: return html.P('No audit records.')
        return dash_table.DataTable(data=df.to_dict('records'),columns=[{'name':c,'id':c} for c in df.columns],page_size=15)

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
