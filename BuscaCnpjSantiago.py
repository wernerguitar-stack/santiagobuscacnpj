import streamlit as st
import streamlit.components.v1 as components
import requests
import re
import os

# ==========================================
# CONFIGURAÇÃO DO BITRIX24 - SANTIAGO SAÚDE
# ==========================================
BITRIX_WEBHOOK_URL = "https://santiago.bitrix24.com.br/rest/1/38fsdnfve8a3qdst/"

# Mapeamento dos Campos Personalizados (UF_CRM_) do Bitrix24 Santiago
CAMPOS_BITRIX = {
    "RAZAO_SOCIAL": "UF_CRM_1791289760212",
    "NOME_FANTASIA": "UF_CRM_1791289775210",
    "ENDERECO": "UF_CRM_1791289817779",
    "CIDADE": "UF_CRM_1791291751638",
    "UF": "UF_CRM_1791291764340",
    "BAIRRO": "UF_CRM_1791291784140",
    "CEP": "UF_CRM_1791291796011",
    "CNAE_PRINCIPAL": "UF_CRM_1791291822995",
    "DESCRICAO_ATIVIDADE": "UF_CRM_1791291839076",
    "TELEFONE": "UF_CRM_1791291868923",
    "EMAIL": "UF_CRM_1791291879826",
    "CNPJ": "UF_CRM_1791292252521",
    "OBSERVACOES": "UF_CRM_1791292759"
}

# Mapeamento dos Consultores / Responsáveis (Nome -> ID do Usuário)
CONSULTORES = {
    "Marcelo Brito": 23,
    "Jolly Bueno": 33,
    "Valeria Oliveira": 27
}

# Mapeamento dos Processos / Funis (Nome -> CATEGORY_ID)
FUNIS_NEGOCIO = {
    "SDR Negócios": 0,        # Funil Padrão
    "Contratos Negócios": 1   # ID do Funil de Contratos
}

def limpar_cnpj(cnpj_raw):
    """Remove qualquer caractere que não seja número do CNPJ."""
    return re.sub(r'\D', '', cnpj_raw)

def consultar_cnpj(cnpj):
    """Consulta a API pública da ReceitaWS."""
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            dados = response.json()
            if dados.get("status") != "ERROR":
                return dados, None
            return None, dados.get("message", "CNPJ não encontrado.")
        elif response.status_code == 429:
            return None, "Limite de requisições atingido na ReceitaWS. Aguarde um instante e tente novamente."
        return None, f"Erro na API (Status {response.status_code})"
    except Exception as e:
        return None, f"Erro de conexão: {str(e)}"

def criar_empresa_bitrix(dados_empresa, id_consultor):
    """Cria o cadastro da Empresa no CRM da Santiago."""
    url = f"{BITRIX_WEBHOOK_URL}crm.company.add.json"
    
    razao_social = dados_empresa.get('nome', '')
    nome_fantasia = dados_empresa.get('fantasia', '') or razao_social
    cnpj_formatado = dados_empresa.get('cnpj', '')
    telefone = dados_empresa.get('telefone_editado', '')
    email = dados_empresa.get('email_editado', '')
    observacoes = dados_empresa.get('observacoes_editadas', '')
    
    logradouro = dados_empresa.get('logradouro', '')
    numero = dados_empresa.get('numero', '')
    bairro = dados_empresa.get('bairro', '')
    endereco_completo = f"{logradouro}, {numero}".strip(", ")
    
    cidade = dados_empresa.get('municipio', '')
    uf = dados_empresa.get('uf', '')
    cep = dados_empresa.get('cep', '')
    
    atividades = dados_empresa.get('atividade_principal', [])
    cnae_codigo = atividades[0].get('code', '') if atividades else ''
    cnae_descricao = atividades[0].get('text', '') if atividades else ''
    
    payload = {
        "fields": {
            "TITLE": razao_social,
            "COMPANY_TYPE": "CUSTOMER",
            "ASSIGNED_BY_ID": id_consultor,
            "PHONE": [{"VALUE": telefone, "VALUE_TYPE": "WORK"}] if telefone else [],
            "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}] if email else [],
            CAMPOS_BITRIX["RAZAO_SOCIAL"]: razao_social,
            CAMPOS_BITRIX["NOME_FANTASIA"]: nome_fantasia,
            CAMPOS_BITRIX["CNPJ"]: cnpj_formatado,
            CAMPOS_BITRIX["TELEFONE"]: telefone,
            CAMPOS_BITRIX["EMAIL"]: email,
            CAMPOS_BITRIX["ENDERECO"]: endereco_completo,
            CAMPOS_BITRIX["BAIRRO"]: bairro,
            CAMPOS_BITRIX["CIDADE"]: cidade,
            CAMPOS_BITRIX["UF"]: uf,
            CAMPOS_BITRIX["CEP"]: cep,
            CAMPOS_BITRIX["CNAE_PRINCIPAL"]: cnae_codigo,
            CAMPOS_BITRIX["DESCRICAO_ATIVIDADE"]: cnae_descricao,
            CAMPOS_BITRIX["OBSERVACOES"]: observacoes
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_json = response.json()
        if "result" in res_json:
            return res_json["result"], None
        return None, res_json.get("error_description", "Erro ao criar Empresa no Bitrix.")
    except Exception as e:
        return None, f"Falha ao cadastrar empresa: {str(e)}"

def criar_contato_bitrix(dados_empresa, id_consultor, company_id=None):
    """Cria o Contato individual no Bitrix24 e vincula à Empresa se existir."""
    url = f"{BITRIX_WEBHOOK_URL}crm.contact.add.json"
    
    nome_contato = dados_empresa.get('socio_editado', '') or "Sócio / Responsável"
    telefone = dados_empresa.get('telefone_editado', '')
    email = dados_empresa.get('email_editado', '')
    
    payload = {
        "fields": {
            "NAME": nome_contato,
            "COMPANY_ID": company_id if company_id else "",
            "ASSIGNED_BY_ID": id_consultor,
            "PHONE": [{"VALUE": telefone, "VALUE_TYPE": "WORK"}] if telefone else [],
            "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}] if email else []
        },
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_json = response.json()
        if "result" in res_json:
            return res_json["result"], None
        return None, res_json.get("error_description", "Erro ao criar Contato no Bitrix.")
    except Exception as e:
        return None, f"Falha ao cadastrar contato: {str(e)}"

def criar_negocio_bitrix(dados_empresa, category_id, id_consultor, company_id=None, contact_id=None):
    """Cria o Negócio no Bitrix24 vinculando Empresa, Contato e o Funil escolhido."""
    url = f"{BITRIX_WEBHOOK_URL}crm.deal.add.json"
    
    razao_social = dados_empresa.get('nome', '')
    nome_fantasia = dados_empresa.get('fantasia', '') or 'Não informado'
    cnpj_formatado = dados_empresa.get('cnpj', '')
    
    telefone = dados_empresa.get('telefone_editado', '')
    email = dados_empresa.get('email_editado', '')
    socio_proprietario = dados_empresa.get('socio_editado', '')
    observacoes = dados_empresa.get('observacoes_editadas', '')
    situacao_cadastral = dados_empresa.get('situacao', 'Não informada')
    
    logradouro = dados_empresa.get('logradouro', '')
    numero = dados_empresa.get('numero', '')
    bairro = dados_empresa.get('bairro', '')
    endereco_completo = f"{logradouro}, {numero}".strip(", ")
    
    cidade = dados_empresa.get('municipio', '')
    uf = dados_empresa.get('uf', '')
    cep = dados_empresa.get('cep', '')
    
    atividades = dados_empresa.get('atividade_principal', [])
    cnae_codigo = atividades[0].get('code', '') if atividades else ''
    cnae_descricao = atividades[0].get('text', '') if atividades else ''
    
    comentarios = (
        f"<b>Razão Social:</b> {razao_social}<br>"
        f"<b>Nome Fantasia:</b> {nome_fantasia}<br>"
        f"<b>CNPJ:</b> {cnpj_formatado}<br>"
        f"<b>Sócio Proprietário:</b> {socio_proprietario}<br>"
        f"<b>Situação Cadastral:</b> {situacao_cadastral}<br>"
        f"<b>Telefone:</b> {telefone}<br>"
        f"<b>E-mail:</b> {email}<br>"
        f"<b>Endereço:</b> {endereco_completo} - {bairro}<br>"
        f"<b>Cidade/UF:</b> {cidade} / {uf}<br>"
        f"<b>CEP:</b> {cep}<br>"
        f"<b>CNAE:</b> {cnae_codigo} - {cnae_descricao}<br>"
        f"<b>Observações:</b> {observacoes}"
    )
    
    fields = {
        "TITLE": f"Novo Cliente: {razao_social}",
        "STAGE_ID": "NEW",
        "CATEGORY_ID": category_id,
        "OPENED": "Y",
        "ASSIGNED_BY_ID": id_consultor,
        "COMMENTS": comentarios,
        "COMPANY_ID": company_id if company_id else "",
        "CONTACT_ID": contact_id if contact_id else "",
        
        CAMPOS_BITRIX["RAZAO_SOCIAL"]: razao_social,
        CAMPOS_BITRIX["NOME_FANTASIA"]: nome_fantasia,
        CAMPOS_BITRIX["CNPJ"]: cnpj_formatado,
        CAMPOS_BITRIX["TELEFONE"]: telefone,
        CAMPOS_BITRIX["EMAIL"]: email,
        CAMPOS_BITRIX["ENDERECO"]: endereco_completo,
        CAMPOS_BITRIX["BAIRRO"]: bairro,
        CAMPOS_BITRIX["CIDADE"]: cidade,
        CAMPOS_BITRIX["UF"]: uf,
        CAMPOS_BITRIX["CEP"]: cep,
        CAMPOS_BITRIX["CNAE_PRINCIPAL"]: cnae_codigo,
        CAMPOS_BITRIX["DESCRICAO_ATIVIDADE"]: cnae_descricao,
        CAMPOS_BITRIX["OBSERVACOES"]: observacoes
    }
    
    payload = {
        "fields": fields,
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_json = response.json()
        if "result" in res_json:
            return res_json["result"], None
        return None, res_json.get("error_description", "Erro ao criar Negócio no Bitrix.")
    except Exception as e:
        return None, f"Falha na comunicação com o Bitrix: {str(e)}"

# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.set_page_config(page_title="Gerador de Negócios - Santiago Saúde", page_icon="🏥", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__106mG, .viewerBadge_link__1S137 {display: none !important;}
    [data-testid="stHeader"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {visibility: hidden; height: 0px; display: none !important;}
    .stAppDeployButton {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

# Busca do caminho da logo com verificação de segurança
diretorio_script = os.path.dirname(os.path.abspath(__file__))
caminho_logo = os.path.join(diretorio_script, "logo.png")

col_esq, col_centro, col_dir = st.columns([1, 2, 1])

with col_centro:
    if os.path.exists(caminho_logo):
        st.image(caminho_logo, use_container_width=True)
    else:
        st.markdown("<h2 style='text-align: center; color: #008080;'>Santiago Saúde</h2>", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center; margin-top: -10px;'>Crie novos leads no Bitrix24</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Santiago Saúde e Segurança Ocupacional</p>", unsafe_allow_html=True)

st.write("---")

if 'dados_cnpj' not in st.session_state:
    st.session_state['dados_cnpj'] = None

cnpj_input = st.text_input("Digite o CNPJ da empresa (com ou sem pontuação):", placeholder="00.000.000/0000-00")

if st.button("Buscar CNPJ", type="secondary", use_container_width=True):
    if not cnpj_input:
        st.warning("Por favor, digite um CNPJ para continuar.")
        st.session_state['dados_cnpj'] = None
    else:
        cnpj_limpo = limpar_cnpj(cnpj_input)
        if len(cnpj_limpo) != 14:
            st.error("Um CNPJ válido deve conter exatamente 14 algarismos.")
            st.session_state['dados_cnpj'] = None
        else:
            with st.spinner("Buscando dados cadastrais na ReceitaWS..."):
                dados, erro_api = consultar_cnpj(cnpj_limpo)
            if erro_api:
                st.error(f"Não foi possível consultar o CNPJ: {erro_api}")
                st.session_state['dados_cnpj'] = None
            else:
                st.success("Dados cadastrais localizados!")
                st.session_state['dados_cnpj'] = dados

if st.session_state['dados_cnpj'] is not None:
    dados = st.session_state['dados_cnpj']
    
    st.write("---")
    
    qsa = dados.get('qsa', [])
    socio_padrao = qsa[0].get('nome', '') if qsa else ''
    telefone_padrao = dados.get('telefone', '')
    email_padrao = dados.get('email', '')
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Razão Social:** {dados.get('nome')}")
        st.write(f"**CNPJ:** {dados.get('cnpj')}")
    with col2:
        st.write(f"**Nome Fantasia:** {dados.get('fantasia') or 'Não informado'}")
        st.write(f"**Situação Cadastral:** {dados.get('situacao')}")
    
    st.write("---")
    st.caption("✏️ **Campos de contato e atribuição:**")
    
    nome_socio = st.text_input("Sócio / Responsável:", value=socio_padrao)
    telefone = st.text_input("Telefone de Contato:", value=telefone_padrao)
    email = st.text_input("E-mail de Contato:", value=email_padrao)
    
    # Seleção do Processo / Funil
    processo_selecionado = st.selectbox("Selecione o Processo / Funil de Negócio:", list(FUNIS_NEGOCIO.keys()))
    category_id = FUNIS_NEGOCIO[processo_selecionado]
    
    # Seleção de Consultor responsável
    consultor_selecionado = st.selectbox("Selecione o Consultor Responsável:", list(CONSULTORES.keys()))
    id_consultor = CONSULTORES[consultor_selecionado]
    
    st.write("---")
    st.caption("🎙️ **Observações (Digite ou grave por áudio):**")
    
    # Gravação e transcrição por áudio no navegador com solicitação de áudio para Android/WebView
    speech_component = """
    <div style="font-family: sans-serif; margin-bottom: 10px;">
        <button id="recordBtn" style="
            background-color: #ff4b4b; 
            color: white; 
            border: none; 
            padding: 8px 16px; 
            border-radius: 4px; 
            cursor: pointer;
            font-weight: bold;
        ">🎙️ Gravar por Áudio</button>
        <span id="status" style="margin-left: 10px; font-size: 14px; color: gray;"></span>
    </div>
    <script>
        const btn = document.getElementById('recordBtn');
        const status = document.getElementById('status');
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        btn.onclick = async () => {
            // Solicitação explícita de áudio para o Android WebView
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                try {
                    await navigator.mediaDevices.getUserMedia({ audio: true });
                } catch (err) {
                    status.innerText = "Permissão de microfone negada no app.";
                    return;
                }
            }

            if (!SpeechRecognition) {
                status.innerText = "Navegador não suporta transcrição direta.";
                return;
            }

            const recognition = new SpeechRecognition();
            recognition.lang = 'pt-BR';
            recognition.continuous = false;
            recognition.interimResults = false;

            recognition.onstart = () => {
                status.innerText = "Ouvindo... Fale agora!";
                btn.style.backgroundColor = "#28a745";
            };

            recognition.onresult = (event) => {
                const text = event.results[0][0].transcript;
                status.innerText = "Transcrito com sucesso!";
                btn.style.backgroundColor = "#ff4b4b";
                
                const textArea = window.parent.document.querySelector('textarea[aria-label="Observações:"]');
                if (textArea) {
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                    nativeInputValueSetter.call(textArea, (textArea.value ? textArea.value + ' ' : '') + text);
                    textArea.dispatchEvent(new Event('input', { bubbles: true }));
                }
            };

            recognition.onerror = (event) => {
                status.innerText = "Erro: " + event.error;
                btn.style.backgroundColor = "#ff4b4b";
            };

            recognition.onend = () => {
                btn.style.backgroundColor = "#ff4b4b";
            };

            try {
                recognition.start();
            } catch (e) {
                status.innerText = "Erro ao iniciar gravação.";
            }
        };
    </script>
    """
    components.html(speech_component, height=50)
    
    observacoes_input = st.text_area("Observações:", value="", placeholder="Digite observações adicionais ou use o botão de áudio acima...")
    
    st.write("---")
    
    if st.button("📌 Cadastrar no Bitrix24", type="primary", use_container_width=True):
        dados['socio_editado'] = nome_socio
        dados['telefone_editado'] = telefone
        dados['email_editado'] = email
        dados['observacoes_editadas'] = observacoes_input
        
        with st.spinner("Cadastrando Empresa, Contato e Negócio na Santiago Saúde..."):
            company_id, erro_empresa = criar_empresa_bitrix(dados, id_consultor)
            contact_id, erro_contato = criar_contato_bitrix(dados, id_consultor, company_id=company_id)
            deal_id, erro_bitrix = criar_negocio_bitrix(
                dados, 
                category_id, 
                id_consultor, 
                company_id=company_id, 
                contact_id=contact_id
            )
            
        if erro_bitrix:
            st.error(f"Erro ao criar registro no Bitrix24: {erro_bitrix}")
        else:
            st.balloons()
            st.success("🎉 **Empresa, Contato e Negócio criados e vinculados com sucesso!**")
            
            url_desktop = f"https://santiago.bitrix24.com.br/crm/deal/details/{deal_id}/"
            url_mobile = f"https://santiago.bitrix24.com.br/company/personal/user/0/tasks/task/view/0/?PATH_TO_DEAL=https://santiago.bitrix24.com.br/crm/deal/details/{deal_id}/"
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.link_button("💻 Abrir no Computador", url_desktop, use_container_width=True)
            with col_b2:
                st.link_button("📱 Abrir no App Celular", url_mobile, use_container_width=True)
            
            st.info(f"ID Negócio: **{deal_id}** | ID Empresa: **{company_id}** | ID Contato: **{contact_id}**")
            
            st.session_state['dados_cnpj'] = None
